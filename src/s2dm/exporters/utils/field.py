from dataclasses import dataclass
from enum import Enum
from typing import Any

from graphql import GraphQLArgument, GraphQLField, GraphQLInputField, Undefined, is_list_type, is_non_null_type
from graphql.utilities import coerce_input_literal

from s2dm.constants.directive import Directive, DirectiveArgument
from s2dm.exporters.utils.directive import get_directive_arguments, has_given_directive


@dataclass
class Cardinality:
    min: int | None
    max: int | None


@dataclass
class FieldCaseMetadata:
    description: str
    value_cardinality: Cardinality
    list_cardinality: Cardinality


class FieldCase(Enum):
    """Enum representing the different cases of a field in a GraphQL schema."""

    DEFAULT = FieldCaseMetadata(
        description="A singular element that can also be null. EXAMPLE -> field: NamedType",
        value_cardinality=Cardinality(min=0, max=1),
        list_cardinality=Cardinality(min=None, max=None),
    )
    NON_NULL = FieldCaseMetadata(
        description="A singular element that cannot be null. EXAMPLE -> field: NamedType!",
        value_cardinality=Cardinality(min=1, max=1),
        list_cardinality=Cardinality(min=None, max=None),
    )
    LIST = FieldCaseMetadata(
        description="An array of elements. The array itself can be null. EXAMPLE -> field: [NamedType]",
        value_cardinality=Cardinality(min=0, max=None),
        list_cardinality=Cardinality(min=0, max=1),
    )
    NON_NULL_LIST = FieldCaseMetadata(
        description="An array of elements. The array itself cannot be null. EXAMPLE -> field: [NamedType]!",
        value_cardinality=Cardinality(min=0, max=None),
        list_cardinality=Cardinality(min=1, max=1),
    )
    LIST_NON_NULL = FieldCaseMetadata(
        description=(
            "An array of elements. The array itself can be null but the elements cannot. EXAMPLE -> field: [NamedType!]"
        ),
        value_cardinality=Cardinality(min=1, max=None),
        list_cardinality=Cardinality(min=0, max=1),
    )
    NON_NULL_LIST_NON_NULL = FieldCaseMetadata(
        description="List and elements in the list cannot be null. EXAMPLE -> field: [NamedType!]!",
        value_cardinality=Cardinality(min=1, max=None),
        list_cardinality=Cardinality(min=1, max=1),
    )
    SET = FieldCaseMetadata(
        description="A set of elements. EXAMPLE -> field: [NamedType] @noDuplicates",
        value_cardinality=Cardinality(min=0, max=None),
        list_cardinality=Cardinality(min=0, max=1),
    )
    SET_NON_NULL = FieldCaseMetadata(
        description="A set of elements. The elements cannot be null. EXAMPLE -> field: [NamedType!] @noDuplicates",
        value_cardinality=Cardinality(min=1, max=None),
        list_cardinality=Cardinality(min=0, max=1),
    )


# Mapping of FieldCase to s2dm TypeWrapperPattern for RDF materialization.
# See: https://covesa.global/models/s2dm#
FIELD_CASE_TO_TYPE_WRAPPER_PATTERN: dict[FieldCase, str] = {
    FieldCase.DEFAULT: "bare",
    FieldCase.NON_NULL: "nonNull",
    FieldCase.LIST: "list",
    FieldCase.LIST_NON_NULL: "listOfNonNull",
    FieldCase.NON_NULL_LIST: "nonNullList",
    FieldCase.NON_NULL_LIST_NON_NULL: "nonNullListOfNonNull",
    # SET and SET_NON_NULL are directive-based; map to underlying list variants
    FieldCase.SET: "list",
    FieldCase.SET_NON_NULL: "listOfNonNull",
}


def field_case_to_type_wrapper_pattern(field_case: FieldCase) -> str:
    """Map a GraphQL FieldCase to s2dm TypeWrapperPattern for RDF materialization.

    Args:
        field_case: The GraphQL field case (DEFAULT, NON_NULL, LIST, etc.).

    Returns:
        The s2dm ontology TypeWrapperPattern name (bare, nonNull, list,
        listOfNonNull, nonNullList, nonNullListOfNonNull).
    """
    return FIELD_CASE_TO_TYPE_WRAPPER_PATTERN[field_case]


def get_field_case(field: GraphQLField) -> FieldCase:
    """
    Determine the case of a field in a GraphQL schema.

    Returns:
        FieldCase: The case of the field as one of the 6 possible cases that are possible with the GraphQL SDL.
        without custom directives.
    """
    field_type = field.type

    if is_non_null_type(field_type):
        field_type = field_type.of_type
        if is_list_type(field_type):
            if is_non_null_type(field_type.of_type):
                return FieldCase.NON_NULL_LIST_NON_NULL
            return FieldCase.NON_NULL_LIST
        return FieldCase.NON_NULL

    if is_list_type(field_type):
        if is_non_null_type(field_type.of_type):
            return FieldCase.LIST_NON_NULL
        return FieldCase.LIST

    return FieldCase.DEFAULT


def get_field_case_extended(field: GraphQLField) -> FieldCase:
    """
    Same as get_field_case but extended to include the custom cases labeled with directives.

    Current extensions:
    @noDuplicates
    - SET = LIST + @noDuplicates
    - SET_NON_NULL = LIST_NON_NULL + @noDuplicates

    Returns:
        FieldCase: The case of the field as one of (6 base + custom ones).
    """
    base_case = get_field_case(field)
    if has_given_directive(field, Directive.NO_DUPLICATES):
        if base_case == FieldCase.LIST:
            return FieldCase.SET
        elif base_case == FieldCase.LIST_NON_NULL:
            return FieldCase.SET_NON_NULL
        else:
            raise ValueError(
                f"Wrong output type and/or modifiers specified for the field: {field}. "
                "Please, correct the GraphQL schema."
            )
    else:
        return base_case


def get_cardinality(field: GraphQLField | GraphQLInputField) -> Cardinality | None:
    """
    Extracts the @cardinality directive arguments from a GraphQL field, if present.

    Args:
        field (GraphQLField | GraphQLInputField): The field to extract cardinality from.

    Returns:
        Cardinality | None: The Cardinality if the directive is present, otherwise None.
    """
    if has_given_directive(field, Directive.CARDINALITY):
        args = get_directive_arguments(field, Directive.CARDINALITY)
        min_val = None
        max_val = None
        if args:
            min_val = (
                int(args[DirectiveArgument.MIN])
                if DirectiveArgument.MIN in args and args[DirectiveArgument.MIN] is not None
                else None
            )
            max_val = (
                int(args[DirectiveArgument.MAX])
                if DirectiveArgument.MAX in args and args[DirectiveArgument.MAX] is not None
                else None
            )
        return Cardinality(min=min_val, max=max_val)
    else:
        return None


def get_argument_or_input_field_default(input_value: GraphQLArgument | GraphQLInputField) -> Any:
    """
    Return the default value of an argument or input field, coerced to its Python value.

    Args:
        input_value (GraphQLArgument | GraphQLInputField): The argument or input field to read.

    Returns:
        Any: The coerced default value, or Undefined when the default is missing or not valid for the type.
    """
    default_input = input_value.default
    if default_input is None or default_input.literal is None:
        return Undefined
    return coerce_input_literal(default_input.literal, input_value.type)


def has_valid_cardinality(field: GraphQLField) -> bool:
    """Check possible missmatch between GraphQL not null and custom @cardinality directive."""
    # TODO: Add a check to avoid discrepancy between GraphQL not null and custom @cardinality directive.
    return False  # Placeholder for future implementation


def print_field_sdl(field: GraphQLField) -> str:
    """Print the field definition as it appears in the GraphQL SDL."""
    field_sdl = ""
    if field.ast_node:
        field_sdl = f"{field.ast_node.name.value}: {field.type}"
        if field.ast_node.directives:
            directives = " ".join([f"@{directive.name.value}" for directive in field.ast_node.directives])
            field_sdl += f" {directives}"
    return field_sdl
