import logging
import os
from dataclasses import dataclass
from enum import Enum
from itertools import product
from pathlib import Path
from typing import Any

from graphql import (
    GraphQLEnumType,
    GraphQLString,
    build_schema,
    is_list_type,
    is_non_null_type,
)
from graphql.type import GraphQLField, GraphQLNamedType, GraphQLObjectType, GraphQLSchema
from graphql.utilities import print_schema


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


def load_schema(graphql_schema_file: Path) -> GraphQLSchema:
    """
    Load and build a GraphQL schema from a file.
    This function reads a GraphQL schema definition from a file, converts it
    into a GraphQLSchema object, and ensures that the schema supports queries.
    Args:
        graphql_schema_file (str): The path to the GraphQL schema file.
    Returns:
        GraphQLSchema: The constructed GraphQL schema object.
    """
    # Read custom directives from file
    custom_directives_file = os.path.join(os.path.dirname(__file__), "..", "spec", "custom_directives.graphql")
    custom_directives_str = read_file(custom_directives_file)

    # Read common types from file
    common_types_file = os.path.join(os.path.dirname(__file__), "..", "spec", "common_types.graphql")
    common_types_str = read_file(common_types_file)

    # Build schema with custom directives
    # TODO: Improve this part with schema merge function with a whole directory.
    # TODO: For example: with Ariadne https://ariadnegraphql.org/docs/modularization#defining-schema-in-graphql-files
    schema_str = custom_directives_str + "\n" + common_types_str + "\n" + read_file(graphql_schema_file)

    schema = build_schema(schema_str)  # Convert GraphQL SDL to a GraphQLSchema object
    logging.info("Successfully loaded the given GraphQL schema file.")
    logging.debug(f"Read schema: \n{print_schema(schema)}")
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
        logging.info("The provided schema has no Query type.")
        query_fields = {"ping": GraphQLField(GraphQLString)}  # Add here other generic fields if needed
        query_type = GraphQLObjectType(name="Query", fields=query_fields)
        new_schema = GraphQLSchema(query=query_type, types=schema.type_map.values(), directives=schema.directives)
        logging.info("A generic Query type to the schema was added.")
        logging.debug(f"New schema: \n{print_schema(new_schema)}")

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
    return [
        type_
        for type_ in schema.type_map.values()
        if isinstance(type_, GraphQLNamedType) and not type_.name.startswith("__")
    ]


def get_all_object_types(named_types: list[GraphQLNamedType]) -> list[GraphQLObjectType]:
    """
    Extracts all object types from the provided GraphQL schema.
    Args:
        schema (GraphQLSchema): The GraphQL schema to extract object types from.
    Returns:
        list[GraphQLObjectType]: A list of all object types in the schema.
    """
    return [type_ for type_ in named_types if isinstance(type_, GraphQLObjectType)]

def get_all_objects_with_directive(objects: list[GraphQLObjectType], directive_name: str) -> list[GraphQLObjectType]:
    # TODO: Extend this function to return all objects that have any directive is directive_name is None
    return [o for o in objects if has_directive(o, directive_name)]

def get_all_expanded_instance_tags(schema: GraphQLSchema) -> dict[GraphQLObjectType, list[str]]:
    all_expanded_instance_tags: dict[GraphQLObjectType, list[str]] = {}
    for object in get_all_objects_with_directive(get_all_object_types(get_all_named_types(schema)), "instanceTag"):
        all_expanded_instance_tags[object] = expand_instance_tag(object)
    
    return all_expanded_instance_tags

def expand_instance_tag(object: GraphQLObjectType) -> list[str]:
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
        logging.debug(f"Tags per enum field: {tags_per_enum_field}")
        
        # Combine tags from different enum fields
        for combination in product(*tags_per_enum_field):
            expanded_tags.append(".".join(combination))  # <-- Character separator can be changed HERE

        logging.debug(f"Expanded tags: {expanded_tags}")

        return expanded_tags

def get_directive_arguments(field: GraphQLField, directive_name: str) -> dict[str, Any]:
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
    if field.ast_node and field.ast_node.directives:
        for directive in field.ast_node.directives:
            if directive.name.value == directive_name:
                return {arg.name.value: arg.value.value for arg in directive.arguments}
    logging.debug(f"Directive '{directive_name}' not found in field '{field.ast_node.name.value}'.")
    return {}


@dataclass
class Cardinality:
    min: int
    max: int


@dataclass
class FieldCaseMetadata:
    description: str
    value_cardinality: Cardinality
    list_cardinality: Cardinality


class FieldCase(Enum):
    """Enum representing the different cases of a field in a GraphQL schema."""
    DEFAULT = FieldCaseMetadata(description="A singular element that can also be null. EXAMPLE -> field: NamedType",
                                value_cardinality=Cardinality(min=0, max=1), list_cardinality=Cardinality(min=None, max=None))
    NON_NULL = FieldCaseMetadata(description="A singular element that cannot be null. EXAMPLE -> field: NamedType!",
                                 value_cardinality=Cardinality(min=1, max=1), list_cardinality=Cardinality(min=None, max=None))
    LIST = FieldCaseMetadata(description="An array of elements. The array itself can be null. EXAMPLE -> field: [NamedType]",
                             value_cardinality=Cardinality(min=0, max=None), list_cardinality=Cardinality(min=0, max=1))
    NON_NULL_LIST = FieldCaseMetadata(description="An array of elements. The array itself cannot be null. EXAMPLE -> field: [NamedType]!",
                                      value_cardinality=Cardinality(min=0, max=None), list_cardinality=Cardinality(min=1, max=1))
    LIST_NON_NULL = FieldCaseMetadata(description="An array of elements. The array itself can be null but the elements cannot. EXAMPLE -> field: [NamedType!]",
                                      value_cardinality=Cardinality(min=1, max=None), list_cardinality=Cardinality(min=0, max=1))
    NON_NULL_LIST_NON_NULL = FieldCaseMetadata(description="List and elements in the list cannot be null. EXAMPLE -> field: [NamedType!]!",
                                               value_cardinality=Cardinality(min=1, max=None), list_cardinality=Cardinality(min=1, max=1))
    SET = FieldCaseMetadata(description="A set of elements. EXAMPLE -> field: [NamedType] @noDuplicates",
                            value_cardinality=Cardinality(min=0, max=None), list_cardinality=Cardinality(min=0, max=1))
    SET_NON_NULL = FieldCaseMetadata(description="A set of elements. The elements cannot be null. EXAMPLE -> field: [NamedType!] @noDuplicates",
                                     value_cardinality=Cardinality(min=0, max=1), list_cardinality=Cardinality(min=0, max=1))


def get_field_case(field: GraphQLField) -> FieldCase:
    """
    Determine the case of a field in a GraphQL schema.

    Returns:
        FieldCase: The case of the field as one of the 6 possible cases that are possible with the GraphQL SDL.
        without custom directives.
    """
    if is_non_null_type(field.type):
        if is_list_type(field.type.of_type):
            if is_non_null_type(field.type.of_type.of_type):
                return FieldCase.NON_NULL_LIST_NON_NULL
            return FieldCase.NON_NULL_LIST
        return FieldCase.NON_NULL
    if is_list_type(field.type):
        if is_non_null_type(field.type.of_type):
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
                f"Wrong output type and/or modifiers specified for the field:\n"
                f"{field.ast_node.name.value}: {field.type}\n"
                f"Please, correct the GraphQL schema."
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


def has_valid_cardinality(field: GraphQLField) -> bool:
    """Check possible missmatch between GraphQL not null and custom @cardinality directive."""
    # TODO: Add a check to avoid discrepancy between GraphQL not null and custom @cardinality directive.
    pass
