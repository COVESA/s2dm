import re
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
from s2dm.exporters.utils.directive import add_directives_to_schema, build_directive_map, has_given_directive
from s2dm.exporters.utils.graphql_type import is_introspection_or_root_type

SPEC_DIR_PATH = Path(__file__).parent.parent.parent / "spec"
SPEC_FILES = [
    SPEC_DIR_PATH / "custom_directives.graphql",
    SPEC_DIR_PATH / "common_types.graphql",
    SPEC_DIR_PATH / "custom_scalars.graphql",
    SPEC_DIR_PATH / "unit_enums.graphql",
]


def _extract_type_names_from_content(content: str) -> list[str]:
    """Extract type names from GraphQL schema content."""
    type_names: list[str] = []
    type_patterns = [
        r"^\s*type\s+(\w+)",
        r"^\s*interface\s+(\w+)",
        r"^\s*union\s+(\w+)",
        r"^\s*enum\s+(\w+)",
        r"^\s*scalar\s+(\w+)",
        r"^\s*input\s+(\w+)",
    ]

    for pattern in type_patterns:
        matches = re.finditer(pattern, content, re.MULTILINE)
        type_names.extend(match.group(1) for match in matches)

    return type_names


def _build_source_map(graphql_schema_paths: list[Path]) -> dict[str, str]:
    """Build mapping of type names to source URIs.

    Args:
        graphql_schema_paths: List of paths to GraphQL schema files or directories

    Returns:
        Dictionary mapping type name to URI (filename or "S2DM Spec")
    """
    source_map: dict[str, str] = {}
    S2DM_SPEC_SOURCE = "S2DM Spec"

    for path in graphql_schema_paths:
        if path.is_file():
            content = path.read_text()
            type_names = _extract_type_names_from_content(content)
            for type_name in type_names:
                source_map[type_name] = path.name
        elif path.is_dir():
            for graphql_file in sorted(path.rglob("*.graphql")):
                content = graphql_file.read_text()
                type_names = _extract_type_names_from_content(content)
                for type_name in type_names:
                    source_map[type_name] = graphql_file.name

    for spec_file in SPEC_FILES:
        if spec_file.exists():
            content = spec_file.read_text()
            type_names = _extract_type_names_from_content(content)
            for type_name in type_names:
                source_map[type_name] = S2DM_SPEC_SOURCE

    return source_map


def build_schema_str(graphql_schema_paths: list[Path], add_references: bool = False) -> str:
    """Build a GraphQL schema from a file or folder."""
    # Load and merge schemas from the directory
    schema_str = ""

    for path in graphql_schema_paths:
        log.debug(f"Loading schema from path: {path}")
        schema_str += load_schema_from_path(path)
        schema_str += "\n"

    # Read spec files
    spec_contents = []
    for spec_file in SPEC_FILES:
        if spec_file.exists():
            spec_contents.append(spec_file.read_text())

    # Build schema with spec files
    schema_str = "\n".join(spec_contents) + "\n" + schema_str
    return schema_str


def load_schema(graphql_schema_paths: list[Path], add_references: bool = False) -> GraphQLSchema:
    """Load and build a GraphQL schema from files or folders."""
    schema_str = build_schema_str(graphql_schema_paths)
    schema = build_schema(schema_str)  # Convert GraphQL SDL to a GraphQLSchema object
    log.info("Successfully loaded the given GraphQL schema file.")
    log.debug(f"Read schema: \n{print_schema(schema)}")
    return ensure_query(schema)


def load_schema_filtered(
    graphql_schema_paths: list[Path], root_type: str, add_references: bool = False
) -> GraphQLSchema:
    """Load and build GraphQL schema filtered by root type.

    Args:
        graphql_schema_paths: List of paths to the GraphQL schema files or directories
        root_type: Root type name to filter the schema
        add_references: Whether to add @reference directives to types
    Returns:
        Filtered GraphQL schema as GraphQLSchema object
    Raises:
        ValueError: If root type is not found in schema
    """
    graphql_schema = load_schema(graphql_schema_paths, add_references)

    if root_type not in graphql_schema.type_map:
        raise ValueError(f"Root type '{root_type}' not found in schema")

    log.info(f"Filtering schema with root type: {root_type}")

    referenced_types = get_referenced_types(graphql_schema, root_type)
    named_types = [t for t in referenced_types if isinstance(t, GraphQLNamedType)]

    filtered_query_type = None

    if root_type == "Query":
        filtered_query_type = graphql_schema.query_type
    elif graphql_schema.query_type:
        query_field = {}
        for field_name, field in graphql_schema.query_type.fields.items():
            field_type = field.type
            while hasattr(field_type, "of_type"):
                field_type = field_type.of_type

            if getattr(field_type, "name", "") == root_type:
                query_field[field_name] = field
                break

        if query_field:
            filtered_query_type = GraphQLObjectType(name="Query", fields=query_field)

    mutation_type = graphql_schema.mutation_type if root_type == "Mutation" else None
    subscription_type = graphql_schema.subscription_type if root_type == "Subscription" else None

    filtered_schema = GraphQLSchema(
        query=filtered_query_type,
        mutation=mutation_type,
        subscription=subscription_type,
        types=named_types,
        directives=graphql_schema.directives,
        description=graphql_schema.description,
        extensions=graphql_schema.extensions,
    )

    log.info(f"Filtered schema from {len(graphql_schema.type_map)} to {len(referenced_types)} types")

    return ensure_query(filtered_schema)


def print_schema_with_directives_preserved(schema: GraphQLSchema, source_map: dict[str, str] | None = None) -> str:
    """Print schema while preserving custom directives.

    Args:
        schema: The GraphQL schema to print
        source_map: Optional mapping of type names to URIs for @reference directives

    Returns:
        Schema string with all directives preserved
    """
    directive_map = build_directive_map(schema)

    if source_map:
        for type_name, uri in source_map.items():
            if type_name in schema.type_map:
                existing_directives = directive_map.get(type_name, [])

                has_reference = any(d.startswith("@reference") for d in existing_directives)

                if not has_reference:
                    existing_directives.append(f'@reference(source: "{uri}")')
                    directive_map[type_name] = existing_directives

    base_schema = print_schema(schema)
    return add_directives_to_schema(base_schema, directive_map)


def load_schema_as_str(graphql_schema_paths: list[Path], add_references: bool = False) -> str:
    """Load and build GraphQL schema but return as str."""
    schema = load_schema(graphql_schema_paths)
    source_map = _build_source_map(graphql_schema_paths) if add_references else None
    return print_schema_with_directives_preserved(schema, source_map)


def load_schema_as_str_filtered(graphql_schema_paths: list[Path], root_type: str, add_references: bool = False) -> str:
    """Load and build GraphQL schema filtered by root type, return as str.

    Args:
        graphql_schema_paths: List of paths to the GraphQL schema files or directories
        root_type: Root type name to filter the schema
        add_references: Whether to add @reference directives to types

    Returns:
        Filtered GraphQL schema as string

    Raises:
        ValueError: If root type is not found in schema
    """
    schema = load_schema_filtered(graphql_schema_paths, root_type)
    source_map = _build_source_map(graphql_schema_paths) if add_references else None
    return print_schema_with_directives_preserved(schema, source_map)


def create_tempfile_to_composed_schema(graphql_schema_paths: list[Path]) -> Path:
    """Load, build, and create temp file for schema to feed to e.g. GraphQL inspector."""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".graphql", delete=False) as temp_file:
        temp_path: str = temp_file.name
        temp_file.write(load_schema_as_str(graphql_schema_paths))

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
