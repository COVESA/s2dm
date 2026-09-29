"""Parsing, extraction and validation of the @pick selection query directive."""

import re
from dataclasses import dataclass
from typing import Any

from graphql import (
    DocumentNode,
    GraphQLEnumType,
    GraphQLNamedType,
    GraphQLScalarType,
    GraphQLSchema,
    parse,
)
from graphql.error import GraphQLSyntaxError
from graphql.language.ast import DirectiveNode, OperationDefinitionNode
from graphql.utilities import value_from_ast_untyped

from s2dm import log
from s2dm.constants.directive import Directive

DIRECTIVE_NAME = Directive.PICK.value

ENUMS_ARGUMENT = "enums"
SCALARS_ARGUMENT = "scalars"
DIRECTIVES_ARGUMENT = "directives"
ARGUMENTS = (ENUMS_ARGUMENT, SCALARS_ARGUMENT, DIRECTIVES_ARGUMENT)
ARGUMENT_FOR_KIND = ((GraphQLEnumType, ENUMS_ARGUMENT), (GraphQLScalarType, SCALARS_ARGUMENT))

# GraphQL requires a non-empty selection set, which a schema of only definitions has nothing to fill.
EMPTY_SELECTION_SET = re.compile(r"\{\s*\}\s*$")
NOTHING_SELECTED = "{ __typename }"


class EveryDefinition:
    """Stands for an empty list, which names every definition of its kind."""

    def __repr__(self) -> str:
        return "ALL"


ALL = EveryDefinition()

PickSelection = list[str] | EveryDefinition | None


@dataclass(frozen=True)
class PickedDefinitions:
    """Definitions a selection query asks to keep beyond the ones its fields reference.

    None means the argument was absent, so the existing dependency-based behavior applies.
    ALL means an empty list was given, which keeps every definition of that kind. Enums are
    always kept whole; there is no way to select a subset of their values.
    """

    enums: PickSelection = None
    scalars: PickSelection = None
    directives: PickSelection = None


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


def _read_name_list(value: Any, argument_name: str) -> list[str] | EveryDefinition:
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
    return list(dict.fromkeys(value))


def _read_directive_arguments(directive_node: DirectiveNode) -> PickedDefinitions:
    """Read the arguments applied to one @pick directive.

    Args:
        directive_node: The applied directive node.

    Returns:
        The definitions it named, with an absent argument left as None.

    Raises:
        ValueError: If the directive carries an argument @pick does not define.
    """
    arguments = {argument.name.value: value_from_ast_untyped(argument.value) for argument in directive_node.arguments}

    unknown = sorted(set(arguments) - set(ARGUMENTS))
    if unknown:
        raise ValueError(f"@{DIRECTIVE_NAME}: unknown argument(s) {unknown}")

    picked_arguments = {name: _read_name_list(arguments[name], name) for name in ARGUMENTS if name in arguments}
    return PickedDefinitions(**picked_arguments)


def _without_pick(definition: OperationDefinitionNode) -> OperationDefinitionNode:
    """Return the operation with @pick removed from the directives applied to it."""
    remaining = tuple(node for node in definition.directives if node.name.value != Directive.PICK)
    return OperationDefinitionNode(
        operation=definition.operation,
        name=definition.name,
        variable_definitions=definition.variable_definitions,
        directives=remaining,
        selection_set=definition.selection_set,
        loc=definition.loc,
    )


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

        applied_directives = [node for node in definition.directives if node.name.value == Directive.PICK]
        is_query = definition.operation.value == "query"

        if applied_directives and is_query and not seen_first_query:
            if len(applied_directives) > 1:
                raise ValueError(f"@{DIRECTIVE_NAME} is applied more than once on one operation")
            picked = _read_directive_arguments(applied_directives[0])
        elif applied_directives:
            log.warning(f"Ignoring @{DIRECTIVE_NAME} outside the first query operation")

        seen_first_query = seen_first_query or is_query

        if applied_directives:
            definition = _without_pick(definition)
        definitions.append(definition)

    return DocumentNode(definitions=tuple(definitions), loc=document.loc), picked


def validate_picked_definitions(schema: GraphQLSchema, picked: PickedDefinitions) -> None:
    """Check every name and definition kind in the selection against the source model.

    A name given under the wrong argument is reported as such, since a directive and a type can
    share a name and neither is found where the other is looked up.

    Args:
        schema: The unfiltered schema the selection is written against.
        picked: The definitions the selection query asked to keep.

    Raises:
        ValueError: If any name is missing from the model or is of the wrong kind.
    """
    errors: list[str] = []
    directive_names = {directive.name for directive in schema.directives}

    def argument_for_type(type_definition: GraphQLNamedType | None) -> str | None:
        """The argument that would accept this type, or None when no argument does."""
        for kind, argument_name in ARGUMENT_FOR_KIND:
            if isinstance(type_definition, kind):
                return argument_name
        return None

    def actual_argument(name: str) -> str | None:
        """The argument the name belongs under, or None when the model does not define it."""
        if name in directive_names:
            return DIRECTIVES_ARGUMENT
        type_definition = schema.type_map.get(name)
        return argument_for_type(type_definition)

    def collect_errors(picked_names: PickSelection, argument_name: str, label: str) -> None:
        """Record an error for every name that does not belong under the given argument."""
        if not isinstance(picked_names, list):
            return
        for name in picked_names:
            belongs_under = actual_argument(name)
            if belongs_under == argument_name:
                continue
            if belongs_under is not None:
                errors.append(f"'{name}' is not {label}; list it under '{belongs_under}'")
                continue
            if name in schema.type_map:
                errors.append(f"'{name}' is not {label}")
                continue
            subject = f"directive '@{name}'" if argument_name == DIRECTIVES_ARGUMENT else f"'{name}'"
            errors.append(f"{subject} is not defined in the model")

    collect_errors(picked.scalars, SCALARS_ARGUMENT, "a scalar")
    collect_errors(picked.enums, ENUMS_ARGUMENT, "an enum")
    collect_errors(picked.directives, DIRECTIVES_ARGUMENT, "a directive")

    if errors:
        raise ValueError(f"@{DIRECTIVE_NAME} validation failed:\n" + "\n".join(f"  - {error}" for error in errors))


def picked_type_names(schema: GraphQLSchema, picked: PickedDefinitions) -> list[str]:
    """Names of the scalar and enum types the selection keeps regardless of references."""
    type_names: list[str] = []

    for picked_names, kind in ((picked.scalars, GraphQLScalarType), (picked.enums, GraphQLEnumType)):
        if picked_names is ALL:
            type_names += [
                name for name, type_definition in schema.type_map.items() if isinstance(type_definition, kind)
            ]
        elif isinstance(picked_names, list):
            type_names += picked_names

    return [name for name in type_names if not name.startswith("__")]


def picked_directive_names(schema: GraphQLSchema, picked: PickedDefinitions) -> list[str]:
    """Names of the directives the selection keeps regardless of use."""
    if picked.directives is ALL:
        return [directive.name for directive in schema.directives]
    if isinstance(picked.directives, list):
        return list(picked.directives)
    return []
