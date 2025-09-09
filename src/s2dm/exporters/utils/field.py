from dataclasses import dataclass
from enum import Enum

from graphql import GraphQLField, is_list_type, is_non_null_type

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


def get_field_case(field: GraphQLField) -> FieldCase:
    """
    Determine the case of a field in a GraphQL schema.

    Returns:
        FieldCase: The case of the field as one of the 6 possible cases that are possible with the GraphQL SDL.
        without custom directives.
    """
    t = field.type

    if is_non_null_type(t):
        t = t.of_type  # type: ignore[union-attr]
        if is_list_type(t):
            if is_non_null_type(t.of_type):
                return FieldCase.NON_NULL_LIST_NON_NULL
            return FieldCase.NON_NULL_LIST
        return FieldCase.NON_NULL

    if is_list_type(t):
        if is_non_null_type(t.of_type):  # type: ignore[union-attr]
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
    if has_given_directive(field, "noDuplicates"):
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


def get_cardinality(field: GraphQLField) -> Cardinality | None:
    """
    Extracts the @cardinality directive arguments from a GraphQL field, if present.

    Args:
        field (GraphQLField): The field to extract cardinality from.

    Returns:
        Cardinality | None: The Cardinality if the directive is present, otherwise None.
    """
    if has_given_directive(field, "cardinality"):
        args = get_directive_arguments(field, "cardinality")
        min_val = None
        max_val = None
        if args:
            min_val = int(args["min"]) if "min" in args and args["min"] is not None else None
            max_val = int(args["max"]) if "max" in args and args["max"] is not None else None
        return Cardinality(min=min_val, max=max_val)
    else:
        return None


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
