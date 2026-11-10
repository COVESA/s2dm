"""Read and apply the @pick directive of a selection query."""

import re
from collections import defaultdict
from dataclasses import dataclass, field, replace
from typing import Any, NamedTuple, TypeVar, cast

from graphql import (
    DocumentNode,
    GraphQLEnumType,
    GraphQLField,
    GraphQLNamedType,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    TypeInfo,
    TypeInfoVisitor,
    Visitor,
    get_named_type,
    parse,
    visit,
)
from graphql.error import GraphQLSyntaxError
from graphql.language.ast import DirectiveNode, FieldNode, OperationDefinitionNode, OperationType

from s2dm.constants.directive import Directive
from s2dm.exporters.utils.directive import get_directive_node_arguments
from s2dm.exporters.utils.graphql_type import is_introspection_type
from s2dm.exporters.utils.instance_tag import (
    get_defined_instance_names,
    get_field_coordinate,
    get_instance_tag_type,
    get_kept_instance_names,
    is_valid_instance_tag_field,
    pick_instances,
)
from s2dm.utils.sequence import get_sequence_or_empty

DIRECTIVE_NAME = Directive.PICK.value

ENUMS_ARGUMENT = "enums"
SCALARS_ARGUMENT = "scalars"
DIRECTIVES_ARGUMENT = "directives"
OPERATION_ARGUMENTS = (ENUMS_ARGUMENT, SCALARS_ARGUMENT, DIRECTIVES_ARGUMENT)
ARGUMENT_FOR_KIND = ((GraphQLEnumType, ENUMS_ARGUMENT), (GraphQLScalarType, SCALARS_ARGUMENT))

INSTANCES_ARGUMENT = "instances"
FIELD_ARGUMENTS = frozenset({INSTANCES_ARGUMENT})

# GraphQL requires a non-empty selection set, which a schema of only definitions has nothing to fill.
EMPTY_SELECTION_SET = re.compile(r"\{\s*\}\s*$")
NOTHING_SELECTED = "{ __typename }"

TagFieldKey = tuple[str, str]

_PickKey = TypeVar("_PickKey")
_PickableNode = TypeVar("_PickableNode", FieldNode, OperationDefinitionNode)


class EveryDefinition:
    """Stands for an empty list, which names every definition of its kind."""

    def __repr__(self) -> str:
        return "ALL"


ALL = EveryDefinition()

PickedNames = list[str] | EveryDefinition


@dataclass(frozen=True)
class PickedDefinitions:
    """What @pick asks for in a selection query.

    On the query operation, @pick keeps definitions beyond the ones the selected fields reference:

    - `enums`, `scalars`, `directives`: the names to keep. None means the argument was absent, so the
      existing dependency-based behavior applies. Enums are always kept whole.

    On a field, @pick narrows an instance tag field. Both maps use the tag field as the key:
    (type name, field name). A field is in one map only.

    - `instances`: the instances picked on the tag field.
    - `dimension_values`: the values picked on each dimension of the tag field.

    ALL means the list was empty, so everything of that kind is kept.
    """

    enums: PickedNames | None = None
    scalars: PickedNames | None = None
    directives: PickedNames | None = None
    instances: dict[TagFieldKey, PickedNames] = field(default_factory=dict)
    dimension_values: dict[TagFieldKey, dict[str, PickedNames]] = field(default_factory=dict)


def parse_selection_query(text: str) -> DocumentNode:
    """Parse a selection query, reading an empty selection set as selecting no fields.

    A query that only picks definitions has no fields to name, but GraphQL rejects an empty
    selection set. Such a query is read as selecting `__typename`, which every type carries and
    which names nothing in the model.

    Args:
        text: The contents of the selection query file.

    Returns:
        The parsed document.

    Raises:
        GraphQLSyntaxError: If the query does not parse for any other reason.
    """
    try:
        return parse(text)
    except GraphQLSyntaxError:
        stripped = text.rstrip()
        repaired = EMPTY_SELECTION_SET.sub(NOTHING_SELECTED, stripped, count=1)
        if repaired == stripped:
            raise
        return parse(repaired)


def _read_name_list(value: Any, argument_name: str) -> PickedNames:
    """Read a [String!] argument into deduplicated names, where an empty list stands for all of them.

    Args:
        value: The argument value as untyped AST.
        argument_name: The argument being read, used to report where a problem is.

    Returns:
        The names in the order given, or ALL when the list is empty.

    Raises:
        ValueError: If the value is not a list, or holds anything other than names.
    """
    if not isinstance(value, list):
        raise ValueError(f"@{DIRECTIVE_NAME}: '{argument_name}' must be a list of names")
    if not value:
        return ALL
    if any(not isinstance(entry, str) for entry in value):
        raise ValueError(f"@{DIRECTIVE_NAME}: '{argument_name}' must contain only names")
    unique_names = dict.fromkeys(value)
    return list(unique_names)


def _read_operation_arguments(directive_node: DirectiveNode) -> PickedDefinitions:
    """Read the arguments of a @pick on the query operation.

    Args:
        directive_node: The @pick directive.

    Returns:
        The definitions it names, with an absent argument left as None.

    Raises:
        ValueError: If the directive carries an argument that @pick on the operation does not define.
    """
    arguments = get_directive_node_arguments(directive_node)

    unknown_arguments = arguments.keys() - OPERATION_ARGUMENTS
    unknown = sorted(unknown_arguments)
    if unknown:
        raise ValueError(f"@{DIRECTIVE_NAME}: unknown argument(s) {unknown}")

    picked_by_argument = {
        name: _read_name_list(arguments[name], name) for name in OPERATION_ARGUMENTS if name in arguments
    }
    return PickedDefinitions(
        enums=picked_by_argument.get(ENUMS_ARGUMENT),
        scalars=picked_by_argument.get(SCALARS_ARGUMENT),
        directives=picked_by_argument.get(DIRECTIVES_ARGUMENT),
    )


def _read_field_arguments(directive_node: DirectiveNode, query_path: str) -> PickedNames:
    """Read the `instances` argument of a @pick on a field.

    Args:
        directive_node: The @pick directive.
        query_path: The field, as a path in the query such as `a.b.c`. Used in error messages.

    Returns:
        The picked names, or ALL if the list is empty.

    Raises:
        ValueError: If an argument other than `instances` is given, or `instances` is missing.
    """
    arguments = get_directive_node_arguments(directive_node)

    unknown_arguments = arguments.keys() - FIELD_ARGUMENTS
    unknown = sorted(unknown_arguments)
    if unknown:
        raise ValueError(f"@{DIRECTIVE_NAME} on '{query_path}': unknown argument(s) {unknown}")
    if INSTANCES_ARGUMENT not in arguments:
        raise ValueError(f"@{DIRECTIVE_NAME} on '{query_path}': '{INSTANCES_ARGUMENT}' is required")

    return _read_name_list(arguments[INSTANCES_ARGUMENT], INSTANCES_ARGUMENT)


def _is_same_selection(first: PickedNames, second: PickedNames) -> bool:
    """Return True if both selections pick the same names, in any order.

    Args:
        first: The names that one place picks, or ALL.
        second: The names that another place picks, or ALL.

    Returns:
        True if both are ALL, or both list the same names.
    """
    if isinstance(first, list) and isinstance(second, list):
        return set(first) == set(second)
    return first is second


def _both_forms_error(query_path: str) -> ValueError:
    """Build the error for a tag field that is picked directly and through its dimensions.

    Args:
        query_path: The tag field, as a path in the query.

    Returns:
        The error to raise.
    """
    return ValueError(f"@{DIRECTIVE_NAME} on '{query_path}': use @pick on the field or on its dimensions, not both")


def _record_same_selection(
    picked_by_key: dict[_PickKey, PickedNames],
    first_paths: dict[_PickKey, str],
    key: _PickKey,
    picked: PickedNames,
    query_path: str,
    target: str,
) -> None:
    """Record what one place in the query picks, and check that it matches the first place with the same key.

    Both maps are changed in place.

    Args:
        picked_by_key: What the first place picks, for each key.
        first_paths: The query path of the first place, for each key.
        key: What the @pick narrows, such as a tag field or one of its dimensions.
        picked: What this place picks, or ALL.
        query_path: This place, as a path in the query.
        target: What the key stands for, such as `'Type.field'`. Used in the error message.

    Raises:
        ValueError: If the first place picks different names.
    """
    first_path = first_paths.setdefault(key, query_path)
    previous_picked = picked_by_key.setdefault(key, picked)
    if _is_same_selection(previous_picked, picked):
        return

    raise ValueError(
        f"@{DIRECTIVE_NAME} on '{query_path}' picks {picked}, but '{first_path}' picks {previous_picked}. "
        f"Both lead to {target}, so they must pick the same names."
    )


def _strip_pick(node: _PickableNode) -> _PickableNode:
    """Return a copy of a query field or operation without its @pick directives.

    Args:
        node: The query field or operation.

    Returns:
        The copy.
    """
    node_directives = get_sequence_or_empty(node.directives)
    kept_directives = tuple(directive for directive in node_directives if directive.name.value != DIRECTIVE_NAME)
    return replace(node, directives=kept_directives)


def _extract_picked_definitions(document: DocumentNode) -> tuple[DocumentNode, PickedDefinitions]:
    """Remove @pick from the query operation and read the definitions it asks to keep.

    The directive is defined by S2DM rather than by the model, so it is taken out of the document
    before the document is validated against the schema.

    Args:
        document: The parsed selection query document.

    Returns:
        The document without the directive, and the definitions it asked to keep.

    Raises:
        ValueError: If @pick is applied more than once, or carries an argument it does not define.
    """
    query_operations = (
        definition
        for definition in document.definitions
        if isinstance(definition, OperationDefinitionNode) and definition.operation == OperationType.QUERY
    )
    query_operation = next(query_operations, None)
    if query_operation is None:
        return document, PickedDefinitions()

    applied_directives = [
        directive
        for directive in get_sequence_or_empty(query_operation.directives)
        if directive.name.value == DIRECTIVE_NAME
    ]
    if not applied_directives:
        return document, PickedDefinitions()
    if len(applied_directives) > 1:
        raise ValueError(f"@{DIRECTIVE_NAME} is applied more than once on one operation")

    picked = _read_operation_arguments(applied_directives[0])
    stripped_query = _strip_pick(query_operation)
    definitions = tuple(
        stripped_query if definition is query_operation else definition for definition in document.definitions
    )
    return DocumentNode(definitions=definitions, loc=document.loc), picked


def _validate_picked_definitions(schema: GraphQLSchema, picked: PickedDefinitions) -> None:
    """Check every name and definition kind in the selection against the source model.

    A name given under the wrong argument is reported as such, since a directive and a type can
    share a name and neither is found where the other is looked up.

    Args:
        schema: The unfiltered schema the selection is written against.
        picked: The definitions the selection query asked to keep.

    Raises:
        ValueError: If any name is missing from the model or is of the wrong kind.
    """
    directive_names = {directive.name for directive in schema.directives}

    def argument_for_type(type_definition: GraphQLNamedType | None) -> str | None:
        """The argument that would accept this type, or None when no argument does."""
        for kind, argument_name in ARGUMENT_FOR_KIND:
            if isinstance(type_definition, kind):
                return argument_name
        return None

    def defining_arguments(name: str) -> set[str]:
        """Every argument whose namespace defines this name.

        Types and directives occupy separate namespaces, so one name can be defined in both.
        """
        type_definition = schema.type_map.get(name)
        type_argument = argument_for_type(type_definition)
        arguments = {type_argument} if type_argument is not None else set()
        if name in directive_names:
            arguments.add(DIRECTIVES_ARGUMENT)
        return arguments

    def collect_errors(picked_names: PickedNames | None, argument_name: str, label: str) -> list[str]:
        """Every name under the given argument that does not belong there, as an error."""
        if not isinstance(picked_names, list):
            return []
        collected: list[str] = []
        for name in picked_names:
            if is_introspection_type(name):
                collected.append(f"'{name}' starts with '__', which GraphQL reserves for introspection")
                continue
            defined_under = defining_arguments(name)
            if argument_name in defined_under:
                continue
            if defined_under:
                elsewhere = sorted(defined_under)[0]
                collected.append(f"'{name}' is not {label}; list it under '{elsewhere}'")
                continue
            if name in schema.type_map:
                collected.append(f"'{name}' is not {label}")
                continue
            subject = f"directive '@{name}'" if argument_name == DIRECTIVES_ARGUMENT else f"'{name}'"
            collected.append(f"{subject} is not defined in the model")
        return collected

    errors = [
        *collect_errors(picked.scalars, SCALARS_ARGUMENT, "a scalar"),
        *collect_errors(picked.enums, ENUMS_ARGUMENT, "an enum"),
        *collect_errors(picked.directives, DIRECTIVES_ARGUMENT, "a directive"),
    ]

    if errors:
        raise ValueError(f"@{DIRECTIVE_NAME} validation failed:\n" + "\n".join(f"  - {error}" for error in errors))


class _QueryField(NamedTuple):
    """A query field: its key (type name, field name), its schema definition, and its path in the query."""

    key: tuple[str, str]
    definition: GraphQLField
    path: str


class _FieldPickExtractor(Visitor):
    """Remove @pick from each field of a query and record what it picks.

    @pick goes on an instance tag field (whole instances) or on its dimensions (values). The picked
    instances belong to the type that declares the tag field, not to the query path. So every place in
    the query that selects the same tag field must pick the same thing.
    """

    def __init__(self, schema: GraphQLSchema, type_info: TypeInfo) -> None:
        super().__init__()
        self.schema = schema
        self.type_info = type_info
        self.field_stack: list[_QueryField | None] = []
        self.picked_instances: dict[TagFieldKey, PickedNames] = {}
        self.picked_dimension_values: dict[TagFieldKey, dict[str, PickedNames]] = {}
        self.selected_fields: defaultdict[str, set[str]] = defaultdict(set)
        self.tag_field_paths: dict[TagFieldKey, str] = {}
        self.dimension_paths: dict[TagFieldKey, dict[str, str]] = {}

    def enter_field(self, node: FieldNode, *_args: Any) -> FieldNode | None:
        """Track the field, then remove its @pick and record what the @pick picks.

        Args:
            node: The query field.

        Returns:
            A copy of the field without @pick, or None when the field has no @pick.

        Raises:
            ValueError: If @pick is used more than once on the field, is not valid, or is not on an instance
                tag field or one of its dimensions.
        """
        enclosing_field = None
        if self.field_stack:
            enclosing_field = self.field_stack[-1]
        current_field = self._push_query_field(node, enclosing_field)

        pick_directives = [
            directive for directive in get_sequence_or_empty(node.directives) if directive.name.value == DIRECTIVE_NAME
        ]
        if not pick_directives:
            return None

        stripped_node = _strip_pick(node)
        # GraphQL validation reports unknown fields later, so only remove @pick here.
        if current_field is None:
            return stripped_node

        if len(pick_directives) > 1:
            raise ValueError(f"@{DIRECTIVE_NAME} is used more than once on '{current_field.path}'")
        picked = _read_field_arguments(pick_directives[0], current_field.path)

        if is_valid_instance_tag_field(current_field.definition, self.schema):
            self._record_instances(current_field, picked)
        elif enclosing_field is not None and is_valid_instance_tag_field(enclosing_field.definition, self.schema):
            self._record_dimension_values(enclosing_field, current_field, picked)
        else:
            raise ValueError(
                f"@{DIRECTIVE_NAME} on '{current_field.path}': the field must be an instance tag field or one of "
                "its dimensions"
            )
        return stripped_node

    def leave_field(self, *_args: Any) -> None:
        self.field_stack.pop()

    def _push_query_field(self, node: FieldNode, enclosing_field: _QueryField | None) -> _QueryField | None:
        """Push the field on the field stack, and record it as selected on its parent type.

        Args:
            node: The query field.
            enclosing_field: The field that holds this field, or None at the top of the query.

        Returns:
            The field, or None when the schema does not define it.
        """
        parent_type = self.type_info.get_parent_type()
        field_definition = self.type_info.get_field_def()
        field_name = node.name.value
        current_field = None
        if parent_type is not None and field_definition is not None:
            query_path = field_name
            if enclosing_field is not None:
                query_path = f"{enclosing_field.path}.{field_name}"
            field_key = (parent_type.name, field_name)
            current_field = _QueryField(key=field_key, definition=field_definition, path=query_path)
            self.selected_fields[parent_type.name].add(field_name)
        self.field_stack.append(current_field)
        return current_field

    def _record_instances(self, tag_field: _QueryField, instances: PickedNames) -> None:
        """Record the instances picked on a tag field.

        Args:
            tag_field: The tag field that has the @pick.
            instances: The picked instances, or ALL.

        Raises:
            ValueError: If the field's dimensions are also picked, an instance is not defined by the field,
                or another place picks different instances.
        """
        if tag_field.key in self.picked_dimension_values:
            raise _both_forms_error(tag_field.path)
        object_type_name, tag_field_name = tag_field.key
        if isinstance(instances, list):
            defined_names = get_defined_instance_names(self.schema, object_type_name, tag_field_name)
            undefined_names = [name for name in instances if name not in defined_names]
            if undefined_names:
                raise ValueError(
                    f"@{DIRECTIVE_NAME} on '{tag_field.path}': {undefined_names} are not defined. "
                    f"Defined instances: {defined_names}"
                )

        tag_coordinate = get_field_coordinate(object_type_name, tag_field_name)
        _record_same_selection(
            self.picked_instances,
            self.tag_field_paths,
            tag_field.key,
            instances,
            tag_field.path,
            f"'{tag_coordinate}'",
        )

    def _record_dimension_values(self, tag_field: _QueryField, dimension: _QueryField, values: PickedNames) -> None:
        """Record the values picked on one dimension of a tag field.

        Args:
            tag_field: The tag field above the dimension.
            dimension: The dimension field that has the @pick.
            values: The picked values, or ALL.

        Raises:
            ValueError: If the tag field itself is also picked, the field is not an enum, a value is not in
                the enum, or another place picks different values.
        """
        if tag_field.key in self.picked_instances:
            raise _both_forms_error(tag_field.path)

        dimension_type = get_named_type(dimension.definition.type)
        if not isinstance(dimension_type, GraphQLEnumType):
            raise ValueError(f"@{DIRECTIVE_NAME} on '{dimension.path}': a dimension must be an enum field")
        if isinstance(values, list):
            unknown_values = set(values) - dimension_type.values.keys()
            unknown = sorted(unknown_values)
            if unknown:
                allowed_values = list(dimension_type.values)
                raise ValueError(
                    f"@{DIRECTIVE_NAME} on '{dimension.path}': {unknown} are not values of "
                    f"'{dimension_type.name}'. Allowed values: {allowed_values}"
                )

        object_type_name, tag_field_name = tag_field.key
        tag_coordinate = get_field_coordinate(object_type_name, tag_field_name)
        _, dimension_name = dimension.key
        self.tag_field_paths.setdefault(tag_field.key, tag_field.path)
        picked_dimensions = self.picked_dimension_values.setdefault(tag_field.key, {})
        dimension_paths = self.dimension_paths.setdefault(tag_field.key, {})
        _record_same_selection(
            picked_dimensions,
            dimension_paths,
            dimension_name,
            values,
            dimension.path,
            f"'{dimension_name}' of '{tag_coordinate}'",
        )


def _validate_selected_dimensions(
    schema: GraphQLSchema,
    picked: PickedDefinitions,
    selected_fields: dict[str, set[str]],
    tag_field_paths: dict[TagFieldKey, str],
) -> None:
    """Check that the query selects every dimension of each tag field that @pick narrows.

    Pruning removes the dimensions that the query does not select. The `exclude` entries that @pick
    writes name every dimension, so they would then match no instance. ALL narrows nothing, so it is
    not checked.

    Args:
        schema: The full schema that the query is written for.
        picked: What @pick picks.
        selected_fields: The fields that the query selects, for each type.
        tag_field_paths: The first path in the query of each picked tag field. Used in error messages.

    Raises:
        ValueError: If the query does not select a dimension of a narrowed tag field.
    """
    narrowed_tag_fields = [tag_key for tag_key, instances in picked.instances.items() if isinstance(instances, list)]
    narrowed_tag_fields += [
        tag_key
        for tag_key, values_by_dimension in picked.dimension_values.items()
        if any(isinstance(values, list) for values in values_by_dimension.values())
    ]

    for tag_key in narrowed_tag_fields:
        object_type_name, tag_field_name = tag_key
        named_type = schema.get_type(object_type_name)
        object_type = cast(GraphQLObjectType, named_type)
        tag_field = object_type.fields[tag_field_name]
        tag_type = get_instance_tag_type(tag_field, schema)
        if not isinstance(tag_type, GraphQLObjectType):
            continue

        selected_dimensions = selected_fields.get(tag_type.name, set())
        unselected_dimensions = [dimension for dimension in tag_type.fields if dimension not in selected_dimensions]
        if unselected_dimensions:
            raise ValueError(
                f"@{DIRECTIVE_NAME} on '{tag_field_paths[tag_key]}' needs every dimension of "
                f"'{tag_type.name}'. The query does not select: {unselected_dimensions}"
            )


def _listed_dimension_values(values_by_dimension: dict[str, PickedNames]) -> dict[str, list[str]]:
    """Leave out the dimensions picked with ALL, which keep every value.

    Args:
        values_by_dimension: The values picked on each dimension, or ALL.

    Returns:
        The values picked on each dimension that has a list.
    """
    return {dimension: values for dimension, values in values_by_dimension.items() if isinstance(values, list)}


def _validate_kept_instances(
    schema: GraphQLSchema,
    picked: PickedDefinitions,
    tag_field_paths: dict[TagFieldKey, str],
) -> None:
    """Check that the values picked on the dimensions of each tag field keep at least one defined instance.

    Each value is a value of its dimension, but together the values can name only combinations that the
    model excludes. ALL narrows nothing, so it is not checked.

    Args:
        schema: The full schema that the query is written for.
        picked: What @pick picks.
        tag_field_paths: The first path in the query of each picked tag field. Used in error messages.

    Raises:
        ValueError: If the values picked on the dimensions of a tag field keep no defined instance.
    """
    for tag_key, values_by_dimension in picked.dimension_values.items():
        listed_values = _listed_dimension_values(values_by_dimension)
        if not listed_values:
            continue

        object_type_name, tag_field_name = tag_key
        kept_names = get_kept_instance_names(schema, object_type_name, tag_field_name, listed_values)
        if not kept_names:
            raise ValueError(
                f"@{DIRECTIVE_NAME} on the dimensions of '{tag_field_paths[tag_key]}' keeps no defined instance. "
                f"The model excludes every combination of {listed_values}"
            )


def apply_picks(schema: GraphQLSchema, picked: PickedDefinitions) -> None:
    """Add the instances that are not picked to the `exclude` list of each picked tag field.

    ALL keeps everything, so it changes nothing. This changes the schema in place.

    Args:
        schema: The full schema that the query is written for.
        picked: What @pick picks, as checked by `extract_and_validate_picks`.
    """
    for (object_type_name, tag_field_name), instances in picked.instances.items():
        if isinstance(instances, list):
            pick_instances(schema, object_type_name, tag_field_name, instances)

    for (object_type_name, tag_field_name), values_by_dimension in picked.dimension_values.items():
        listed_values = _listed_dimension_values(values_by_dimension)
        if not listed_values:
            continue
        kept_names = get_kept_instance_names(schema, object_type_name, tag_field_name, listed_values)
        pick_instances(schema, object_type_name, tag_field_name, kept_names)


def extract_and_validate_picks(schema: GraphQLSchema, document: DocumentNode) -> tuple[DocumentNode, PickedDefinitions]:
    """Remove @pick from the query operation and its fields, and check what each @pick names.

    Args:
        schema: The full schema that the query is written for.
        document: The parsed query.

    Returns:
        The query without @pick, and what @pick picks.

    Raises:
        ValueError: If a @pick is not valid. On the operation, this covers a name that the model does not
            define or that is of the wrong kind. On a field, this covers a @pick that is not on a tag field
            or one of its dimensions, names an instance or value that the tag field does not define, is
            used in both forms on one tag field, picks different things for the same field, narrows a tag
            field whose dimensions the query does not all select, or picks dimension values that keep no
            defined instance.
    """
    document_without_operation_pick, operation_picked = _extract_picked_definitions(document)
    _validate_picked_definitions(schema, operation_picked)

    type_info = TypeInfo(schema)
    extractor = _FieldPickExtractor(schema, type_info)
    type_info_visitor = TypeInfoVisitor(type_info, extractor)
    stripped_document = visit(document_without_operation_pick, type_info_visitor)
    picked = replace(
        operation_picked,
        instances=extractor.picked_instances,
        dimension_values=extractor.picked_dimension_values,
    )
    _validate_selected_dimensions(schema, picked, extractor.selected_fields, extractor.tag_field_paths)
    _validate_kept_instances(schema, picked, extractor.tag_field_paths)
    return stripped_document, picked


def picked_type_names(schema: GraphQLSchema, picked: PickedDefinitions) -> list[str]:
    """Names of the scalar and enum types the selection keeps regardless of references."""
    type_names: list[str] = []

    selections_by_kind = ((picked.scalars, GraphQLScalarType), (picked.enums, GraphQLEnumType))
    for picked_names, kind in selections_by_kind:
        if picked_names is ALL:
            type_names += [
                name for name, type_definition in schema.type_map.items() if isinstance(type_definition, kind)
            ]
        elif isinstance(picked_names, list):
            type_names += picked_names

    return [name for name in type_names if not is_introspection_type(name)]


def picked_directive_names(schema: GraphQLSchema, picked: PickedDefinitions) -> list[str]:
    """Names of the directives the selection keeps regardless of use."""
    if picked.directives is ALL:
        return [directive.name for directive in schema.directives]
    if isinstance(picked.directives, list):
        return list(picked.directives)
    return []
