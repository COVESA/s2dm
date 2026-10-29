"""Parsing, extraction and validation of the @pick selection query directive."""

import re
from copy import copy
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
from graphql.language.ast import DirectiveNode, OperationDefinitionNode, OperationType
from graphql.utilities import value_from_ast_untyped

from s2dm.constants.directive import Directive
from s2dm.exporters.utils.graphql_type import is_introspection_type

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
    """Return a copy of the operation with @pick removed from the directives applied to it."""
    stripped_definition = copy(definition)
    stripped_definition.directives = tuple(
        directive for directive in definition.directives if directive.name.value != DIRECTIVE_NAME
    )
    return stripped_definition


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
        directive for directive in query_operation.directives if directive.name.value == DIRECTIVE_NAME
    ]
    if not applied_directives:
        return document, PickedDefinitions()
    if len(applied_directives) > 1:
        raise ValueError(f"@{DIRECTIVE_NAME} is applied more than once on one operation")

    picked = _read_directive_arguments(applied_directives[0])
    stripped_query = _without_pick(query_operation)
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

    def collect_errors(picked_names: PickSelection, argument_name: str, label: str) -> list[str]:
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


def extract_and_validate_picks(schema: GraphQLSchema, document: DocumentNode) -> tuple[DocumentNode, PickedDefinitions]:
    """Remove @pick from the document and check the definitions it names against the model.

    Args:
        schema: The unfiltered schema the selection is written against.
        document: The parsed selection query.

    Returns:
        The document without @pick, and the definitions @pick asked to keep.

    Raises:
        ValueError: If @pick is malformed or names a definition the model does not have.
    """
    stripped_document, picked = _extract_picked_definitions(document)
    _validate_picked_definitions(schema, picked)
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
