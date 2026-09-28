"""Extraction and validation of the @pick selection query directive."""

from dataclasses import dataclass
from typing import Any

from graphql import (
    DocumentNode,
    GraphQLEnumType,
    GraphQLScalarType,
    GraphQLSchema,
)
from graphql.language.ast import OperationDefinitionNode
from graphql.utilities import value_from_ast_untyped

from s2dm import log
from s2dm.constants.directive import Directive

DIRECTIVE_NAME = Directive.PICK.value
ALL = "__all__"
ARGUMENTS = ("enums", "scalars", "directives")


@dataclass(frozen=True)
class PickedDefinitions:
    """Definitions a selection query asks to keep beyond the ones its fields reference.

    None means the argument was absent, so the existing dependency-based behavior applies.
    ALL means an empty list was given, which keeps every definition of that kind. Enums are
    always kept whole; there is no way to select a subset of their values.
    """

    enums: list[str] | str | None = None
    scalars: list[str] | str | None = None
    directives: list[str] | str | None = None


def _name_list(value: Any, argument: str) -> list[str] | str:
    """Read a [String!] argument, where an empty list stands for every definition of that kind."""
    if not isinstance(value, list):
        raise ValueError(f"@{DIRECTIVE_NAME}: '{argument}' must be a list of names")
    if not value:
        return ALL
    if any(not isinstance(entry, str) for entry in value):
        raise ValueError(f"@{DIRECTIVE_NAME}: '{argument}' must contain only names")
    return list(dict.fromkeys(value))


def _read_directive_arguments(node: Any) -> PickedDefinitions:
    arguments = {argument.name.value: value_from_ast_untyped(argument.value) for argument in node.arguments}

    unknown = sorted(set(arguments) - set(ARGUMENTS))
    if unknown:
        raise ValueError(f"@{DIRECTIVE_NAME}: unknown argument(s) {unknown}")

    picked = {name: _name_list(arguments[name], name) for name in ARGUMENTS if name in arguments}
    return PickedDefinitions(**picked)


def extract_picked_definitions(document: DocumentNode) -> tuple[DocumentNode, PickedDefinitions]:
    """Remove @pick from every operation and read it from the first query operation.

    The directive is defined by S2DM rather than by the model, so it is taken out of the document
    before the document is validated against the schema. Later operations are stripped as well,
    since only the first query operation is read.

    Args:
        document: The parsed selection query document.

    Returns:
        The document without the directive, and the definitions it asked to keep.
    """
    picked = PickedDefinitions()
    seen_first_query = False
    definitions = []

    for definition in document.definitions:
        if not isinstance(definition, OperationDefinitionNode):
            definitions.append(definition)
            continue

        applied = [node for node in definition.directives if node.name.value == Directive.PICK]
        is_query = definition.operation.value == "query"

        if applied and is_query and not seen_first_query:
            if len(applied) > 1:
                raise ValueError(f"@{DIRECTIVE_NAME} is applied more than once on one operation")
            picked = _read_directive_arguments(applied[0])
        elif applied:
            log.warning(f"Ignoring @{DIRECTIVE_NAME} outside the first query operation")

        seen_first_query = seen_first_query or is_query

        if applied:
            remaining = tuple(node for node in definition.directives if node.name.value != Directive.PICK)
            definition = OperationDefinitionNode(
                operation=definition.operation,
                name=definition.name,
                variable_definitions=definition.variable_definitions,
                directives=remaining,
                selection_set=definition.selection_set,
                loc=definition.loc,
            )
        definitions.append(definition)

    return DocumentNode(definitions=tuple(definitions), loc=document.loc), picked


def validate_picked_definitions(schema: GraphQLSchema, picked: PickedDefinitions) -> None:
    """Check every name and definition kind in the selection against the source model.

    Args:
        schema: The unfiltered schema the selection is written against.
        picked: The definitions the selection query asked to keep.

    Raises:
        ValueError: If any name is missing from the model or is of the wrong kind.
    """
    errors: list[str] = []

    def check_kind(names: list[str] | str | None, kind: type, label: str) -> None:
        if not isinstance(names, list):
            return
        for name in names:
            type_definition = schema.type_map.get(name)
            if type_definition is None:
                errors.append(f"'{name}' is not defined in the model")
            elif not isinstance(type_definition, kind):
                errors.append(f"'{name}' is not {label}")

    check_kind(picked.scalars, GraphQLScalarType, "a scalar")
    check_kind(picked.enums, GraphQLEnumType, "an enum")

    if isinstance(picked.directives, list):
        defined = {directive.name for directive in schema.directives}
        errors.extend(
            f"directive '@{name}' is not defined in the model" for name in picked.directives if name not in defined
        )

    if errors:
        raise ValueError(f"@{DIRECTIVE_NAME} validation failed:\n" + "\n".join(f"  - {error}" for error in errors))


def picked_type_names(schema: GraphQLSchema, picked: PickedDefinitions) -> list[str]:
    """Names of the scalar and enum types the selection keeps regardless of references."""
    names: list[str] = []

    for selection, kind in ((picked.scalars, GraphQLScalarType), (picked.enums, GraphQLEnumType)):
        if selection == ALL:
            names += [name for name, t in schema.type_map.items() if isinstance(t, kind)]
        elif isinstance(selection, list):
            names += selection

    return [name for name in names if not name.startswith("__")]


def picked_directive_names(schema: GraphQLSchema, picked: PickedDefinitions) -> list[str]:
    """Names of the directives the selection keeps regardless of use."""
    if picked.directives == ALL:
        return [directive.name for directive in schema.directives]
    return list(picked.directives or [])
