import re
import tempfile
from pathlib import Path
from typing import Any, cast

from ariadne import load_schema_from_path
from graphql import (
    DocumentNode,
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
    get_named_type,
    is_input_object_type,
    is_interface_type,
    is_list_type,
    is_non_null_type,
    is_object_type,
    is_union_type,
    print_schema,
)
from graphql import validate as graphql_validate
from graphql.language.ast import SelectionSetNode

from s2dm import log
from s2dm.exporters.utils.directive import (
    GRAPHQL_TYPE_DEFINITION_PATTERN,
    add_directives_to_schema,
    build_directive_map,
    has_given_directive,
)
from s2dm.exporters.utils.graphql_type import is_introspection_or_root_type

SPEC_DIR_PATH = Path(__file__).parent.parent.parent / "spec"
SPEC_FILES = [
    SPEC_DIR_PATH / "custom_directives.graphql",
    SPEC_DIR_PATH / "common_types.graphql",
    SPEC_DIR_PATH / "custom_scalars.graphql",
]


def _extract_type_names_from_content(content: str) -> list[str]:
    """Extract type names from GraphQL schema content."""
    type_names: list[str] = []
    matches = re.finditer(GRAPHQL_TYPE_DEFINITION_PATTERN, content, re.MULTILINE)
    type_names.extend(match.group(2) for match in matches)
    return type_names


def resolve_graphql_files(paths: list[Path]) -> list[Path]:
    """Resolve a list of paths (files and directories) into a flat list of unique GraphQL files.

    Args:
        paths: List of file or directory paths

    Returns:
        Flat list of unique GraphQL file paths (deduplicated and sorted)
    """
    resolved_files: set[Path] = set()

    for path in paths:
        if path.is_file():
            resolved_files.add(path)
        elif path.is_dir():
            for file in path.rglob("*.graphql"):
                resolved_files.add(file)

    return sorted(resolved_files)


def build_schema_str_with_optional_source_map(
    graphql_schema_paths: list[Path], with_source_map: bool
) -> tuple[str, dict[str, str]]:
    """Build a GraphQL schema from a file or folder, returning also a source map."""
    schema_str = ""
    source_map: dict[str, str] = {}
    S2DM_SPEC_SOURCE = "S2DM Spec"

    for graphql_file in graphql_schema_paths:
        content = load_schema_from_path(graphql_file)
        schema_str += content + "\n"
        if with_source_map:
            type_names = _extract_type_names_from_content(content)
            for type_name in type_names:
                source_map[type_name] = graphql_file.name

    # Read spec files
    spec_contents = []
    for spec_file in SPEC_FILES:
        content = spec_file.read_text()
        spec_contents.append(content)
        if with_source_map:
            type_names = _extract_type_names_from_content(content)
            for type_name in type_names:
                source_map[type_name] = S2DM_SPEC_SOURCE

    schema_str = "\n".join(spec_contents) + "\n" + schema_str

    return schema_str, source_map


def build_schema_str(graphql_schema_paths: list[Path]) -> str:
    """Build a GraphQL schema from a file or folder."""
    schema_str, _ = build_schema_str_with_optional_source_map(graphql_schema_paths, with_source_map=False)
    return schema_str


def build_schema_with_query(schema_str: str) -> GraphQLSchema:
    """Build a GraphQL schema from a schema string, ensuring it has a Query type."""
    schema = build_schema(schema_str)  # Convert GraphQL SDL to a GraphQLSchema object
    log.info("Successfully built the given GraphQL schema string.")
    log.debug(f"Read schema: \n{print_schema(schema)}")
    return ensure_query(schema)


def load_schema(graphql_schema_paths: Path | list[Path]) -> GraphQLSchema:
    """Load and build a GraphQL schema from files or folders."""

    if isinstance(graphql_schema_paths, Path):
        graphql_schema_paths = [graphql_schema_paths]

    schema_str = build_schema_str(graphql_schema_paths)
    return build_schema_with_query(schema_str)


def filter_schema(graphql_schema: GraphQLSchema, root_type: str) -> GraphQLSchema:
    """Filter a GraphQL schema by root type.

    Args:
        graphql_schema: The GraphQL schema to filter
        root_type: Root type name to filter the schema

    Returns:
        Filtered GraphQL schema as GraphQLSchema object

    Raises:
        ValueError: If root type is not found in schema
    """
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


def load_schema_filtered(graphql_schema_paths: list[Path], root_type: str) -> GraphQLSchema:
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
    graphql_schema = load_schema(graphql_schema_paths)
    return filter_schema(graphql_schema, root_type)


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
    schema_str, source_map = build_schema_str_with_optional_source_map(graphql_schema_paths, add_references)
    schema = build_schema_with_query(schema_str)
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
    schema_str, source_map = build_schema_str_with_optional_source_map(graphql_schema_paths, add_references)
    schema = build_schema_with_query(schema_str)
    filtered_schema = filter_schema(schema, root_type)
    return print_schema_with_directives_preserved(filtered_schema, source_map)


def create_tempfile_to_composed_schema(graphql_schema_paths: list[Path]) -> Path:
    """Load, build, and create temp file for schema to feed to e.g. GraphQL inspector."""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".graphql", delete=False) as temp_file:
        temp_path: str = temp_file.name
        temp_file.write(load_schema_as_str(graphql_schema_paths))
        temp_file.flush()

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


def validate_schema(schema: GraphQLSchema, document: DocumentNode) -> GraphQLSchema | None:
    log.debug("Validating schema against the provided document")

    errors = graphql_validate(schema, document)
    if errors:
        log.error("Schema validation failed:")
        for error in errors:
            log.error(f" - {error}")
        return None

    log.debug("Schema validation succeeded")

    return schema


def prune_schema_using_query_selection(schema: GraphQLSchema, document: DocumentNode) -> GraphQLSchema:
    """
    Filter schema by pruning unselected fields and types based on query selections.

    Args:
        schema: The original GraphQL schema
        document: Parsed query document

    Returns:
        The modified schema with only the selected fields and types
    """
    if not schema.query_type:
        raise ValueError("Schema has no query type defined")

    if validate_schema(schema, document) is None:
        raise ValueError("Schema validation failed")

    fields_to_keep: dict[str, set[str]] = {}
    types_to_keep: set[str] = set()

    def collect_selections(type_name: str, selection_set: SelectionSetNode) -> None:
        """Recursively collect field names and type names to keep."""
        type_obj = schema.type_map.get(type_name)
        if not type_obj:
            return

        types_to_keep.add(type_name)

        if not (is_object_type(type_obj) or is_interface_type(type_obj)):
            return

        if type_name not in fields_to_keep:
            fields_to_keep[type_name] = set()

        obj_type = cast(GraphQLObjectType | GraphQLInterfaceType, type_obj)

        for selection in selection_set.selections:
            if hasattr(selection, "name"):
                field_name = selection.name.value
                fields_to_keep[type_name].add(field_name)

                if field_name in obj_type.fields:
                    field = obj_type.fields[field_name]
                    field_type = get_named_type(field.type)

                    if field_type and hasattr(field_type, "name"):
                        types_to_keep.add(field_type.name)

                    if hasattr(field, "args"):
                        for _, arg in field.args.items():
                            arg_type = get_named_type(arg.type)
                            if arg_type and hasattr(arg_type, "name"):
                                types_to_keep.add(arg_type.name)

                    if (
                        hasattr(selection, "selection_set")
                        and selection.selection_set
                        and field_type
                        and hasattr(field_type, "name")
                    ):
                        collect_selections(field_type.name, selection.selection_set)

    query_operations = [
        definition
        for definition in document.definitions
        if hasattr(definition, "operation") and definition.operation.value == "query"
    ]

    if not query_operations:
        raise ValueError("No query operation found in selection document")

    log.debug("Composing filtered schema based on query selections")

    query_operation = query_operations[0]
    if hasattr(query_operation, "selection_set"):
        collect_selections(schema.query_type.name, query_operation.selection_set)

    for type_name, fields_to_keep_set in fields_to_keep.items():
        type_obj = schema.type_map.get(type_name)
        if type_obj and (is_object_type(type_obj) or is_interface_type(type_obj)):
            obj_type = cast(GraphQLObjectType | GraphQLInterfaceType, type_obj)
            fields_to_delete = [fname for fname in obj_type.fields if fname not in fields_to_keep_set]
            for fname in fields_to_delete:
                del obj_type.fields[fname]

    types_to_delete = [
        type_name
        for type_name in list(schema.type_map.keys())
        if type_name not in types_to_keep and not type_name.startswith("__")
    ]
    for type_name in types_to_delete:
        del schema.type_map[type_name]

    directives_used: set[str] = set()

    for type_name in types_to_keep:
        type_obj = schema.type_map.get(type_name)
        if not type_obj:
            continue

        if hasattr(type_obj, "ast_node") and type_obj.ast_node and hasattr(type_obj.ast_node, "directives"):
            for directive in type_obj.ast_node.directives:
                directives_used.add(directive.name.value)

        if is_object_type(type_obj) or is_interface_type(type_obj):
            obj_type = cast(GraphQLObjectType | GraphQLInterfaceType, type_obj)
            for field in obj_type.fields.values():
                if hasattr(field, "ast_node") and field.ast_node and hasattr(field.ast_node, "directives"):
                    for directive in field.ast_node.directives:
                        directives_used.add(directive.name.value)

    schema.directives = tuple(directive for directive in schema.directives if directive.name in directives_used)

    log.debug(f"Composed filtered schema with {len(fields_to_keep)} object types")

    return schema
