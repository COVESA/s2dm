"""Extraction and validation of the @retainedDefinitions selection query directive."""

from dataclasses import dataclass
from typing import Any, cast

from graphql import (
    DocumentNode,
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    get_named_type,
)
from graphql.language.ast import EnumValueNode, ListValueNode, OperationDefinitionNode, StringValueNode
from graphql.utilities import value_from_ast_untyped

from s2dm import log
from s2dm.constants.directive import Directive, DirectiveArgument
from s2dm.exporters.utils.directive import has_given_directive

DIRECTIVE_NAME = Directive.RETAINED_DEFINITIONS.value
ALL = "__all__"


@dataclass(frozen=True)
class RetainedDefinitions:
    """Definitions a selection query asks to retain beyond the ones its fields reference.

    A value of None means the argument was absent and the existing dependency-based behavior
    applies. A value of ALL means an empty list was given, which retains every definition of
    that kind.
    """

    enums: dict[str, list[str] | str] | str | None = None
    scalars: list[str] | str | None = None
    directives: list[str] | str | None = None

    @property
    def is_empty(self) -> bool:
        return self.enums is None and self.scalars is None and self.directives is None


def _name_list(value: Any, argument: str) -> list[str] | str:
    """Read a [String!] argument, where an empty list stands for every definition of that kind."""
    if not isinstance(value, list):
        raise ValueError(f"@{DIRECTIVE_NAME}: '{argument}' must be a list of names")
    if not value:
        return ALL
    non_strings = [entry for entry in value if not isinstance(entry, str)]
    if non_strings:
        raise ValueError(f"@{DIRECTIVE_NAME}: '{argument}' must contain only names")
    return list(dict.fromkeys(value))


def _enum_selection(value: Any) -> dict[str, list[str] | str] | str:
    """Read the enums argument, which maps an enum name to the values to retain."""
    if isinstance(value, list):
        if value:
            raise ValueError(f"@{DIRECTIVE_NAME}: 'enums' must map enum names to values")
        return ALL
    if not isinstance(value, dict):
        raise ValueError(f"@{DIRECTIVE_NAME}: 'enums' must map enum names to values")
    if not value:
        return ALL

    selection: dict[str, list[str] | str] = {}
    for enum_name, values in value.items():
        selection[enum_name] = _name_list(values, f"enums.{enum_name}")
    return selection


def _read_directive_arguments(node: Any) -> RetainedDefinitions:
    arguments = {argument.name.value: value_from_ast_untyped(argument.value) for argument in node.arguments}

    unknown = sorted(set(arguments) - {"enums", "scalars", "directives"})
    if unknown:
        raise ValueError(f"@{DIRECTIVE_NAME}: unknown argument(s) {unknown}")

    return RetainedDefinitions(
        enums=_enum_selection(arguments["enums"]) if "enums" in arguments else None,
        scalars=_name_list(arguments["scalars"], "scalars") if "scalars" in arguments else None,
        directives=_name_list(arguments["directives"], "directives") if "directives" in arguments else None,
    )


def extract_retained_definitions(document: DocumentNode) -> tuple[DocumentNode, RetainedDefinitions]:
    """Remove @retainedDefinitions from every operation and read it from the first query operation.

    The directive is defined by S2DM rather than by the model, so it is taken out of the document
    before the document is validated against the schema. Later operations are stripped as well,
    since only the first query operation is read.

    Args:
        document: The parsed selection query document.

    Returns:
        The document without the directive, and the definitions it asked to retain.
    """
    retained = RetainedDefinitions()
    seen_first_query = False
    definitions = []

    for definition in document.definitions:
        if not isinstance(definition, OperationDefinitionNode):
            definitions.append(definition)
            continue

        applied = [d for d in definition.directives if d.name.value == Directive.RETAINED_DEFINITIONS]
        is_query = definition.operation.value == "query"

        if applied and is_query and not seen_first_query:
            if len(applied) > 1:
                raise ValueError(f"@{DIRECTIVE_NAME} is applied more than once on one operation")
            retained = _read_directive_arguments(applied[0])
        elif applied:
            log.warning(f"Ignoring @{DIRECTIVE_NAME} outside the first query operation")

        seen_first_query = seen_first_query or is_query

        if applied:
            remaining = tuple(d for d in definition.directives if d.name.value != Directive.RETAINED_DEFINITIONS)
            definition = OperationDefinitionNode(
                operation=definition.operation,
                name=definition.name,
                variable_definitions=definition.variable_definitions,
                directives=remaining,
                selection_set=definition.selection_set,
                loc=definition.loc,
            )
        definitions.append(definition)

    return DocumentNode(definitions=tuple(definitions), loc=document.loc), retained


def validate_retained_definitions(schema: GraphQLSchema, retained: RetainedDefinitions) -> None:
    """Check every name, kind and enum value in the selection against the source model.

    Args:
        schema: The unfiltered schema the selection is written against.
        retained: The definitions the selection query asked to retain.

    Raises:
        ValueError: If any name is missing, is of the wrong kind, or names an absent enum value.
    """
    errors: list[str] = []

    def check_kind(names: list[str] | str, kind: type, label: str) -> None:
        if isinstance(names, str):
            return
        for name in names:
            type_definition = schema.type_map.get(name)
            if type_definition is None:
                errors.append(f"'{name}' is not defined in the model")
            elif not isinstance(type_definition, kind):
                errors.append(f"'{name}' is not {label}")

    check_kind(retained.scalars or [], GraphQLScalarType, "a scalar")

    if isinstance(retained.enums, dict):
        check_kind(list(retained.enums), GraphQLEnumType, "an enum")
        for enum_name, values in retained.enums.items():
            enum_type = schema.type_map.get(enum_name)
            if not isinstance(enum_type, GraphQLEnumType) or isinstance(values, str):
                continue
            missing = [value for value in values if value not in enum_type.values]
            if missing:
                errors.append(f"enum '{enum_name}' has no value(s) {sorted(missing)}")

    if isinstance(retained.directives, list):
        defined = {directive.name for directive in schema.directives}
        errors.extend(
            f"directive '@{name}' is not defined in the model" for name in retained.directives if name not in defined
        )

    if errors:
        raise ValueError(f"@{DIRECTIVE_NAME} validation failed:\n" + "\n".join(f"  - {error}" for error in errors))


def retained_type_names(schema: GraphQLSchema, retained: RetainedDefinitions) -> list[str]:
    """Names of the scalar and enum types the selection asks to retain regardless of references."""
    names: list[str] = []

    if retained.scalars == ALL:
        names += [name for name, t in schema.type_map.items() if isinstance(t, GraphQLScalarType)]
    elif retained.scalars:
        names += list(retained.scalars)

    if retained.enums == ALL:
        names += [name for name, t in schema.type_map.items() if isinstance(t, GraphQLEnumType)]
    elif isinstance(retained.enums, dict):
        names += list(retained.enums)

    return [name for name in names if not name.startswith("__")]


def retained_directive_names(schema: GraphQLSchema, retained: RetainedDefinitions) -> list[str]:
    """Names of the directives the selection asks to retain regardless of use."""
    if retained.directives == ALL:
        return [directive.name for directive in schema.directives]
    return list(retained.directives or [])


def _removed_values(schema: GraphQLSchema, retained: RetainedDefinitions) -> dict[str, set[str]]:
    if not isinstance(retained.enums, dict):
        return {}

    removed: dict[str, set[str]] = {}
    for enum_name, values in retained.enums.items():
        enum_type = schema.type_map.get(enum_name)
        if not isinstance(enum_type, GraphQLEnumType) or isinstance(values, str):
            continue
        dropped = {name for name in enum_type.values if name not in values}
        if dropped:
            removed[enum_name] = dropped
    return removed


def _reject_values_in_use(schema: GraphQLSchema, removed: dict[str, set[str]]) -> None:
    """Refuse a selection that removes a value a retained default or directive argument needs."""
    conflicts: list[str] = []

    def check_default(owner: str, value_type: Any, default: Any) -> None:
        if not isinstance(value_type, GraphQLEnumType) or not isinstance(default, str):
            return
        if default in removed.get(value_type.name, set()):
            conflicts.append(f"{owner} defaults to '{default}'")

    for type_name, type_definition in schema.type_map.items():
        if type_name.startswith("__"):
            continue
        if isinstance(type_definition, GraphQLObjectType | GraphQLInterfaceType):
            for field_name, field in type_definition.fields.items():
                for argument_name, argument in field.args.items():
                    owner = f"{type_name}.{field_name}({argument_name}:)"
                    check_default(owner, get_named_type(argument.type), argument.default_value)
        elif isinstance(type_definition, GraphQLInputObjectType):
            for field_name, input_field in type_definition.fields.items():
                owner = f"{type_name}.{field_name}"
                check_default(owner, get_named_type(input_field.type), input_field.default_value)

    argument_types = {
        directive.name: {name: get_named_type(argument.type) for name, argument in directive.args.items()}
        for directive in schema.directives
    }
    for directive in schema.directives:
        for argument_name, argument in directive.args.items():
            owner = f"@{directive.name}({argument_name}:)"
            check_default(owner, get_named_type(argument.type), argument.default_value)

    for owner, node in _directive_carriers(schema):
        for applied in node.directives:
            for argument in applied.arguments:
                value_type = argument_types.get(applied.name.value, {}).get(argument.name.value)
                if not isinstance(value_type, GraphQLEnumType) or not isinstance(argument.value, EnumValueNode):
                    continue
                if argument.value.value in removed.get(value_type.name, set()):
                    conflicts.append(f"@{applied.name.value}({argument.name.value}:) on {owner}")

    if conflicts:
        raise ValueError(
            f"@{DIRECTIVE_NAME} removes enum values that are still in use:\n"
            + "\n".join(f"  - {conflict}" for conflict in sorted(conflicts))
        )


def _directive_carriers(schema: GraphQLSchema) -> list[tuple[str, Any]]:
    """Every AST node in the schema that can carry applied directives, with a label for messages."""
    carriers: list[tuple[str, Any]] = []
    for type_name, type_definition in schema.type_map.items():
        if type_name.startswith("__"):
            continue
        if type_definition.ast_node is not None:
            carriers.append((type_name, type_definition.ast_node))
        fields = getattr(type_definition, "fields", None)
        if not fields:
            continue
        for field_name, field in fields.items():
            if field.ast_node is not None:
                carriers.append((f"{type_name}.{field_name}", field.ast_node))
    return carriers


def _tag_dimensions(source_type: Any) -> list[str] | None:
    """Enum type name per instance tag dimension, in the order the instances are built in."""
    if isinstance(source_type, GraphQLEnumType):
        return [source_type.name]
    if not isinstance(source_type, GraphQLObjectType):
        return None

    dimensions: list[str] = []
    for field in source_type.fields.values():
        enum_type = get_named_type(field.type)
        if not isinstance(enum_type, GraphQLEnumType):
            return None
        dimensions.append(enum_type.name)
    return dimensions


def _exclude_nodes(schema: GraphQLSchema, source_name: str) -> list[Any]:
    """Every AST node carrying an @instanceTag exclude list for the given instance tag source."""
    nodes: list[Any] = []
    source_type = schema.type_map.get(source_name)
    if source_type is not None and source_type.ast_node is not None:
        nodes.append(source_type.ast_node)

    for type_definition in schema.type_map.values():
        fields = getattr(type_definition, "fields", None)
        if not fields:
            continue
        for field in fields.values():
            if field.ast_node is None or get_named_type(field.type).name != source_name:
                continue
            nodes.append(field.ast_node)
    return nodes


def _prune_instance_tag_excludes(schema: GraphQLSchema, removed: dict[str, set[str]]) -> None:
    """Drop the exclude entries that name a removed value, since they can no longer match.

    An exclude entry asserts that one instance is absent rather than consuming a value, so
    removing a value it names leaves the entry vacuous rather than broken.
    """
    for source_name, source_type in list(schema.type_map.items()):
        if source_name.startswith("__") or not isinstance(source_type, GraphQLObjectType | GraphQLEnumType):
            continue
        if not has_given_directive(source_type, Directive.INSTANCE_TAG):
            continue
        dimensions = _tag_dimensions(source_type)
        if dimensions is None:
            continue

        for node in _exclude_nodes(schema, source_name):
            for applied in node.directives:
                if applied.name.value != Directive.INSTANCE_TAG:
                    continue
                for argument in applied.arguments:
                    if argument.name.value != DirectiveArgument.EXCLUDE:
                        continue
                    if not isinstance(argument.value, ListValueNode):
                        continue
                    kept = tuple(
                        entry for entry in argument.value.values if not _entry_is_vacuous(entry, dimensions, removed)
                    )
                    if len(kept) != len(argument.value.values):
                        log.debug(f"Dropping vacuous @{Directive.INSTANCE_TAG.value} exclude entries on {source_name}")
                        argument.value = ListValueNode(values=kept, loc=argument.value.loc)


def _entry_is_vacuous(entry: Any, dimensions: list[str], removed: dict[str, set[str]]) -> bool:
    if not isinstance(entry, StringValueNode):
        return False
    segments = entry.value.split(".")
    if len(segments) != len(dimensions):
        return False
    pairs = zip(segments, dimensions, strict=True)
    return any(segment in removed.get(enum_name, set()) for segment, enum_name in pairs)


def apply_enum_value_selection(schema: GraphQLSchema, retained: RetainedDefinitions) -> None:
    """Narrow the retained enums to their selected values and drop the exclude entries that follow.

    Args:
        schema: The schema being filtered, modified in place.
        retained: The definitions the selection query asked to retain.

    Raises:
        ValueError: If a removed value is still needed by a retained default or directive argument.
    """
    removed = _removed_values(schema, retained)
    if not removed:
        return

    _reject_values_in_use(schema, removed)

    for enum_name, dropped in removed.items():
        enum_type = cast(GraphQLEnumType, schema.type_map[enum_name])
        for value_name in dropped:
            del enum_type.values[value_name]
        log.debug(f"Retained {len(enum_type.values)} of {len(enum_type.values) + len(dropped)} {enum_name} values")

    _prune_instance_tag_excludes(schema, removed)
