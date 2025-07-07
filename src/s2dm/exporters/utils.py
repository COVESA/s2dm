import os
from dataclasses import dataclass
from enum import Enum
from itertools import product
from pathlib import Path
from typing import Any

from ariadne import load_schema_from_path
from graphql import (
    GraphQLEnumType,
    GraphQLString,
    build_schema,
    get_named_type,
    is_list_type,
    is_non_null_type,
)
from graphql.type import GraphQLField, GraphQLNamedType, GraphQLObjectType, GraphQLSchema, GraphQLWrappingType
from graphql.utilities import print_schema

from s2dm import log


def read_file(file_path: Path) -> str:
    """
    Read the content of a file.
    Args:
        file_path (str): The path to the file.
    Returns:
        str: The content of the file.
    Raises:
        Exception: If the file does not exist.
    """
    if not os.path.exists(file_path):
        raise Exception(f"The provided file does not exist: {file_path}")

    with open(file_path, encoding="utf-8") as file:
        return file.read()


def build_schema_str(graphql_schema_path: Path) -> str:
    """Build a GraphQL schema from a file or folder."""
    # Load and merge schemas from the directory
    schema_str = load_schema_from_path(graphql_schema_path)

    # Read custom directives from file
    custom_directives_file = os.path.join(os.path.dirname(__file__), "..", "spec", "custom_directives.graphql")
    custom_directives_str = read_file(Path(custom_directives_file))

    # Read common types from file
    common_types_file = os.path.join(os.path.dirname(__file__), "..", "spec", "common_types.graphql")
    common_types_str = read_file(Path(common_types_file))

    # Read custom scalar types from file
    custom_scalar_types_file = os.path.join(os.path.dirname(__file__), "..", "spec", "custom_scalars.graphql")
    custom_scalar_types_str = read_file(Path(custom_scalar_types_file))

    # Read unit enums from file
    unit_enums_file = os.path.join(os.path.dirname(__file__), "..", "spec", "unit_enums.graphql")
    unit_enums_str = read_file(Path(unit_enums_file))

    # Build schema with custom directives
    # TODO: Improve this part with schema merge function with a whole directory.
    # TODO: For example: with Ariadne https://ariadnegraphql.org/docs/modularization#defining-schema-in-graphql-files
    schema_str = (
        custom_directives_str
        + "\n"
        + common_types_str
        + "\n"
        + custom_scalar_types_str
        + "\n"
        + schema_str
        + "\n"
        + unit_enums_str
    )
    return schema_str


def load_schema(graphql_schema_path: Path) -> GraphQLSchema:
    """Load and build a GraphQL schema from a file or folder."""
    schema_str = build_schema_str(graphql_schema_path)
    schema = build_schema(schema_str)  # Convert GraphQL SDL to a GraphQLSchema object
    log.info("Successfully loaded the given GraphQL schema file.")
    log.debug(f"Read schema: \n{print_schema(schema)}")
    return ensure_query(schema)


def ensure_query(schema: GraphQLSchema) -> GraphQLSchema:
    """
    Ensures that the provided GraphQL schema has a Query type. If the schema does not have a Query type,
    a generic Query type is added.

    Args:
        schema (GraphQLSchema): The GraphQL schema to check and potentially modify.

    Returns:
        GraphQLSchema: The original schema if it already has a Query type, otherwise a new schema with a
        generic Query type added.
    """
    if not schema.query_type:
        log.info("The provided schema has no Query type.")
        query_fields = {"ping": GraphQLField(GraphQLString)}  # Add here other generic fields if needed
        query_type = GraphQLObjectType(name="Query", fields=query_fields)
        new_schema = GraphQLSchema(
            query=query_type,
            types=schema.type_map.values(),
            directives=schema.directives,
        )
        log.info("A generic Query type to the schema was added.")
        log.debug(f"New schema: \n{print_schema(new_schema)}")

        return new_schema

    return schema


def get_all_named_types(schema: GraphQLSchema) -> list[GraphQLNamedType]:
    """
    Extracts all named types (ScalarType, ObjectType, InterfaceType, UnionType, EnumType, and InputObjectType)
    from the provided GraphQL schema.

    Args:
        schema (GraphQLSchema): The GraphQL schema to extract named types from.
    Returns:
        list[GraphQLNamedType]: A list of all named types in the schema.
    """
    return [type_ for type_ in schema.type_map.values() if not type_.name.startswith("__")]


def get_all_object_types(
    schema: GraphQLSchema,
) -> list[GraphQLObjectType]:
    """
    Extracts all object types from the provided GraphQL schema.
    Args:
        schema (GraphQLSchema): The GraphQL schema to extract object types from.
    Returns:
        list[GraphQLObjectType]: A list of all object types in the schema.
    """
    named_types = get_all_named_types(schema)
    return [type_ for type_ in named_types if isinstance(type_, GraphQLObjectType)]


def get_all_objects_with_directive(objects: list[GraphQLObjectType], directive_name: str) -> list[GraphQLObjectType]:
    # TODO: Extend this function to return all objects that have any directive is directive_name is None
    return [o for o in objects if has_directive(o, directive_name)]


def get_all_expanded_instance_tags(
    schema: GraphQLSchema,
) -> dict[GraphQLObjectType, list[str]]:
    all_expanded_instance_tags: dict[GraphQLObjectType, list[str]] = {}
    for object in get_all_objects_with_directive(get_all_object_types(schema), "instanceTag"):
        all_expanded_instance_tags[object] = expand_instance_tag(object)

    log.debug(f"All expanded tags in the spec: {all_expanded_instance_tags}")

    return all_expanded_instance_tags


def expand_instance_tag(object: GraphQLObjectType) -> list[str]:
    log.debug(f"Expanding instanceTag for object: {object.name}")
    expanded_tags = []
    if not has_directive(object, "instanceTag"):
        raise ValueError(f"Object '{object.name}' does not have an instance tag directive.")
    else:
        tags_per_enum_field = []
        for field_name, field in object.fields.items():
            if not isinstance(field.type, GraphQLEnumType):
                # TODO: Move this check to a validation function for the @instanceTag directive
                raise TypeError(f"Field '{field_name}' in object '{object.name}' is not an enum.")
            tags_per_enum_field.append(list(field.type.values.keys()))
        log.debug(f"Tags per field: {tags_per_enum_field}")

        # Combine tags from different enum fields
        for combination in product(*tags_per_enum_field):
            expanded_tags.append(".".join(combination))  # <-- Character separator can be changed HERE

        log.debug(f"Expanded tags: {expanded_tags}")

        return expanded_tags


def get_directive_arguments(element: GraphQLField | GraphQLObjectType, directive_name: str) -> dict[str, Any]:
    """
    Extracts the arguments of a specified directive from a GraphQL field.
    Args:
        field (GraphQLField): The GraphQL field from which to extract the directive arguments.
        directive_name (str): The name of the directive whose arguments are to be extracted.
    Returns:
        dict[str, Any]: A dictionary containing the directive arguments as key-value pairs.
                        Returns an empty dictionary if the directive is not found.
    Logs:
        Logs a debug message if the specified directive is not found in the field.
    """
    if has_directive(element, directive_name) and element.ast_node is not None:
        directive = next(d for d in element.ast_node.directives if d.name.value == directive_name)
        return {arg.name.value: arg.value.value for arg in directive.arguments if hasattr(arg.value, "value")}
    else:
        log.debug(f"Directive '{directive_name}' not found in element '{element}'.")
        return {}


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
    if is_non_null_type(field.type):
        if is_list_type(field.type) and isinstance(field.type, GraphQLWrappingType):
            if is_non_null_type(field.type.of_type) and isinstance(field.type.of_type, GraphQLWrappingType):
                return FieldCase.NON_NULL_LIST_NON_NULL
            return FieldCase.NON_NULL_LIST
        return FieldCase.NON_NULL
    if is_list_type(field.type):
        if isinstance(field.type, GraphQLWrappingType) and is_non_null_type(field.type.of_type):
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
    if has_directive(field, "noDuplicates"):
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


def has_directive(element: GraphQLObjectType | GraphQLField, directive_name: str) -> bool:
    """Check whether a GraphQL element (field, object type) has a particular specified directive."""
    if element.ast_node and element.ast_node.directives:
        for directive in element.ast_node.directives:
            if directive.name.value == directive_name:
                return True
    return False


def get_argument_content(
    element: GraphQLObjectType | GraphQLField, directive_name: str, argument_name: str
) -> Any | None:
    """
    Extracts the comment from a GraphQL element (field or named type).

    Args:
        element (GraphQLNamedType | GraphQLField): The GraphQL element to extract the comment from.

    Returns:
        str | None: The comment if present, otherwise None.
    """
    args = get_directive_arguments(element, directive_name)
    return args.get(argument_name) if args and argument_name in args else None


def get_cardinality(field: GraphQLField) -> Cardinality | None:
    """
    Extracts the @cardinality directive arguments from a GraphQL field, if present.

    Args:
        field (GraphQLField): The field to extract cardinality from.

    Returns:
        Cardinality | None: The Cardinality if the directive is present, otherwise None.
    """
    if has_directive(field, "cardinality"):
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


def is_valid_instance_tag_field(field: GraphQLField, schema: GraphQLSchema) -> bool:
    """
    Check if the output type of a given field is a valid instanceTag.
    A valid instanceTag is an object type with the @instanceTag directive.

    Args:
        field (GraphQLField): The field to check.
        schema (GraphQLSchema): The GraphQL schema to validate against.

    Returns:
        bool: True if the field's output type is a valid instanceTag, False otherwise.
    """
    output_type = schema.get_type(get_named_type(field.type).name)
    return isinstance(output_type, GraphQLObjectType) and has_directive(output_type, "instanceTag")


def has_valid_instance_tag_field(object_type: GraphQLObjectType, schema: GraphQLSchema) -> bool:
    """
    Check if a given object type has a field named 'instanceTag' and if the field's output type
    is a valid instanceTag.

    Args:
        object_type (GraphQLObjectType): The object type to check.
        schema (GraphQLSchema): The GraphQL schema to validate against.

    Returns:
        bool: True if the object type has a valid instanceTag field, False otherwise.
    """
    if "instanceTag" in object_type.fields:
        log.debug(f"instanceTag? {True}")
        field = object_type.fields["instanceTag"]
        return is_valid_instance_tag_field(field, schema)
    else:
        log.debug(f"instanceTag? {False}")
        return False


def get_instance_tag_object(object_type: GraphQLObjectType, schema: GraphQLSchema) -> GraphQLObjectType | None:
    """
    Get the valid instance tag object type used in a valid instance tag field.

    Args:
        object_type (GraphQLObjectType): The object type to check.
        schema (GraphQLSchema): The GraphQL schema to validate against.

    Returns:
        GraphQLObjectType | None: The valid instance tag object type if found, None otherwise.
    """
    if has_valid_instance_tag_field(object_type, schema):
        field = object_type.fields["instanceTag"]
        instance_tag_type = schema.get_type(get_named_type(field.type).name)
        if isinstance(instance_tag_type, GraphQLObjectType):
            return instance_tag_type
    return None


def get_instance_tag_dict(
    instance_tag_object: GraphQLObjectType,
) -> dict[str, list[str]]:
    """
    Given a valid instance tag object type, return the list of all enum values by level.

    Args:
        instance_tag_object (GraphQLObjectType): The instance tag object type to process.

    Returns:
        dict[str, list[str]]: A dictionary where keys are field names and values are lists of enum values.
    """
    instance_tag_dict = {}

    for field_name, field in instance_tag_object.fields.items():
        if isinstance(field.type, GraphQLEnumType):
            instance_tag_dict[field_name] = list(field.type.values.keys())
        else:
            raise TypeError(f"Field '{field_name}' in object '{instance_tag_object.name}' is not an enum.")

    return instance_tag_dict
