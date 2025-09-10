import tempfile
from pathlib import Path
from typing import Any, cast

from ariadne import load_schema_from_path
from graphql import (
    GraphQLField,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLList,
    GraphQLNamedType,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLSchema,
    GraphQLString,
    GraphQLType,
    GraphQLUnionType,
    build_schema,
    is_input_object_type,
    is_interface_type,
    is_list_type,
    is_non_null_type,
    is_object_type,
    is_union_type,
    print_schema,
)

from s2dm import log
from s2dm.exporters.utils.directive import has_given_directive
from s2dm.exporters.utils.graphql_type import is_introspection_or_root_type

SPEC_DIR_PATH = Path(__file__).parent.parent.parent / "spec"


def build_schema_str(graphql_schema_path: Path) -> str:
    """Build a GraphQL schema from a file or folder."""
    # Load and merge schemas from the directory
    schema_str = load_schema_from_path(graphql_schema_path)

    # Read custom directives from file
    custom_directives_file = SPEC_DIR_PATH / "custom_directives.graphql"
    custom_directives_str = custom_directives_file.read_text()

    # Read common types from file
    common_types_file = SPEC_DIR_PATH / "common_types.graphql"
    common_types_str = common_types_file.read_text()

    # Read custom scalar types from file
    custom_scalar_types_file = SPEC_DIR_PATH / "custom_scalars.graphql"
    custom_scalar_types_str = custom_scalar_types_file.read_text()

    # Read unit enums from file
    unit_enums_file = SPEC_DIR_PATH / "unit_enums.graphql"
    unit_enums_str = unit_enums_file.read_text()

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


def load_schema_filtered(graphql_schema_path: Path, root_type: str) -> GraphQLSchema:
    """Load and build GraphQL schema filtered by root type.

    Args:
        graphql_schema_path: Path to the GraphQL schema file or directory
        root_type: Root type name to filter the schema
    Returns:
        Filtered GraphQL schema as GraphQLSchema object
    Raises:
        ValueError: If root type is not found in schema
    """
    graphql_schema = load_schema(graphql_schema_path)

    if root_type not in graphql_schema.type_map:
        raise ValueError(f"Root type '{root_type}' not found in schema")

    log.info(f"Filtering schema with root type: {root_type}")

    referenced_types = get_referenced_types(graphql_schema, root_type)
    named_types = [t for t in referenced_types if isinstance(t, GraphQLNamedType)]

    filtered_schema = GraphQLSchema(
        query=graphql_schema.query_type,
        mutation=graphql_schema.mutation_type,
        subscription=graphql_schema.subscription_type,
        types=named_types,
        directives=graphql_schema.directives,
        description=graphql_schema.description,
        extensions=graphql_schema.extensions,
    )

    log.info(f"Filtered schema from {len(graphql_schema.type_map)} to {len(referenced_types)} types")

    return filtered_schema


def load_schema_as_str(graphql_schema_path: Path) -> str:
    """Load and build GraphQL schema but return as str."""
    return print_schema(load_schema(graphql_schema_path))


def load_schema_as_str_filtered(graphql_schema_path: Path, root_type: str) -> str:
    """Load and build GraphQL schema filtered by root type, return as str.

    Args:
        graphql_schema_path: Path to the GraphQL schema file or directory
        root_type: Root type name to filter the schema

    Returns:
        Filtered GraphQL schema as string

    Raises:
        ValueError: If root type is not found in schema
    """
    return print_schema(load_schema_filtered(graphql_schema_path, root_type))


def create_tempfile_to_composed_schema(graphql_schema_path: Path) -> Path:
    """Load, build, and create temp file for schema to feed to e.g. GraphQL inspector."""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".graphql", delete=False) as temp_file:
        temp_path: str = temp_file.name
        temp_file.write(load_schema_as_str(graphql_schema_path))

    return Path(temp_path)


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


def get_referenced_types(graphql_schema: GraphQLSchema, root_type: str) -> set[GraphQLType]:
    """
    Find all GraphQL types referenced from the root type through graph traversal.

    Args:
        graphql_schema: The GraphQL schema
        root_type: The root type to start traversal from

    Returns:
        Set[GraphQLType]: Set of referenced GraphQL type objects
    """
    visited: set[str] = set()
    referenced: set[GraphQLType] = set()

    def visit_type(type_name: str) -> None:
        if type_name in visited:
            return

        visited.add(type_name)

        if is_introspection_or_root_type(type_name):
            return

        type_def = graphql_schema.type_map.get(type_name)
        if not type_def:
            return

        referenced.add(type_def)

        if is_object_type(type_def) and not has_given_directive(cast(GraphQLObjectType, type_def), "instanceTag"):
            visit_object_type(cast(GraphQLObjectType, type_def))
        elif is_interface_type(type_def):
            visit_interface_type(cast(GraphQLInterfaceType, type_def))
        elif is_union_type(type_def):
            visit_union_type(cast(GraphQLUnionType, type_def))
        elif is_input_object_type(type_def):
            visit_input_object_type(cast(GraphQLInputObjectType, type_def))
        # Scalar and enum types don't reference other types

    def visit_object_type(obj_type: GraphQLObjectType) -> None:
        for field in obj_type.fields.values():
            visit_field_type(field.type)

        for interface in obj_type.interfaces:
            visit_type(interface.name)

    def visit_interface_type(interface_type: GraphQLInterfaceType) -> None:
        for field in interface_type.fields.values():
            visit_field_type(field.type)

    def visit_union_type(union_type: GraphQLUnionType) -> None:
        for member_type in union_type.types:
            visit_type(member_type.name)

    def visit_input_object_type(input_type: GraphQLInputObjectType) -> None:
        for field in input_type.fields.values():
            visit_field_type(field.type)

    def visit_field_type(field_type: GraphQLType) -> None:
        unwrapped_type = field_type
        while is_non_null_type(unwrapped_type) or is_list_type(unwrapped_type):
            if is_non_null_type(unwrapped_type):
                unwrapped_type = cast(GraphQLNonNull[Any], unwrapped_type).of_type
            elif is_list_type(unwrapped_type):
                unwrapped_type = cast(GraphQLList[Any], unwrapped_type).of_type

        if hasattr(unwrapped_type, "name"):
            visit_type(unwrapped_type.name)

    visit_type(root_type)

    log.info(f"Found {len(referenced)} referenced types from root type '{root_type}'")
    return referenced
