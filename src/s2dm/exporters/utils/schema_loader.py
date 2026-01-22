import re
import tempfile
from pathlib import Path
from typing import Any, cast

from ariadne import load_schema_from_path
from graphql import (
    DocumentNode,
    GraphQLEnumType,
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
    Undefined,
    build_schema,
    get_named_type,
    is_input_object_type,
    is_interface_type,
    is_list_type,
    is_non_null_type,
    is_object_type,
    is_union_type,
    parse,
    print_schema,
    validate_schema,
)
from graphql import validate as graphql_validate
from graphql.language.ast import DirectiveNode, EnumValueNode, SelectionSetNode

from s2dm import log
from s2dm.exporters.utils.annotated_schema import (
    AnnotatedSchema,
    FieldMetadata,
    TypeMetadata,
)
from s2dm.exporters.utils.directive import (
    GRAPHQL_TYPE_DEFINITION_PATTERN,
    add_directives_to_schema,
    build_directive_map,
    has_given_directive,
)
from s2dm.exporters.utils.graphql_type import is_introspection_or_root_type
from s2dm.exporters.utils.instance_tag import expand_instances_in_schema
from s2dm.exporters.utils.naming import (
    apply_naming_to_schema,
    convert_name,
    get_target_case_for_element,
    load_naming_config,
)

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

    return list(resolved_files)


def build_schema_str_with_optional_source_map(
    graphql_schema_paths: list[Path], with_source_map: bool, naming_config: dict[str, Any] | None = None
) -> tuple[str, dict[str, str]]:
    """Build a GraphQL schema from a file or folder, returning also a source map."""
    schema_str = ""
    source_map: dict[str, str] = {}
    S2DM_SPEC_SOURCE = "S2DM Spec"

    type_case = get_target_case_for_element("type", "object", naming_config) if naming_config else None

    for graphql_file in graphql_schema_paths:
        content = load_schema_from_path(graphql_file)
        schema_str += content + "\n"
        if with_source_map:
            type_names = _extract_type_names_from_content(content)
            for type_name in type_names:
                transformed_name = convert_name(type_name, type_case) if type_case else type_name
                source_map[transformed_name] = graphql_file.name

    spec_contents = []
    for spec_file in SPEC_FILES:
        content = spec_file.read_text()
        spec_contents.append(content)
        if with_source_map:
            type_names = _extract_type_names_from_content(content)
            for type_name in type_names:
                transformed_name = convert_name(type_name, type_case) if type_case else type_name
                source_map[transformed_name] = S2DM_SPEC_SOURCE

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


def load_schema_with_source_map(
    graphql_schema_paths: list[Path], naming_config: dict[str, Any] | None = None
) -> tuple[GraphQLSchema, dict[str, str]]:
    """Load and build a GraphQL schema from files or folders, returning schema and source map."""
    schema_str, source_map = build_schema_str_with_optional_source_map(
        graphql_schema_paths, with_source_map=True, naming_config=naming_config
    )
    schema = build_schema_with_query(schema_str)
    return schema, source_map


def load_schema_with_naming(schema_paths: list[Path], naming_config: dict[str, Any] | None = None) -> GraphQLSchema:
    """Load schema and apply naming conversion."""
    schema = load_schema(schema_paths)
    if naming_config:
        apply_naming_to_schema(schema, naming_config)
    return schema


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


def create_tempfile_to_composed_schema(graphql_schema_paths: list[Path]) -> Path:
    """Load, build, and create temp file for schema to feed to e.g. GraphQL inspector."""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".graphql", delete=False) as temp_file:
        temp_path: str = temp_file.name
        temp_file.write(load_schema_as_str(graphql_schema_paths))
        temp_file.flush()

    return Path(temp_path)


def _check_directive_usage_on_node(schema: GraphQLSchema, directive_node: DirectiveNode, context: str) -> list[str]:
    """Check enum values in directive usage on a specific node."""
    errors: list[str] = []

    directive_def = schema.get_directive(directive_node.name.value)
    if not directive_def:
        return errors

    for arg_node in directive_node.arguments:
        arg_name = arg_node.name.value
        arg_def = directive_def.args[arg_name]
        named_type = get_named_type(arg_def.type)

        if not isinstance(named_type, GraphQLEnumType):
            continue

        if not isinstance(arg_node.value, EnumValueNode):
            continue

        enum_value = arg_node.value.value
        if enum_value not in named_type.values:
            errors.append(
                f"{context} uses directive '@{directive_node.name.value}({arg_name})' "
                f"with invalid enum value '{enum_value}'. Valid values are: {list(named_type.values.keys())}"
            )

    return errors


def check_enum_defaults(schema: GraphQLSchema) -> list[str]:
    """Check that all enum default values exist in their enum definitions.

    Args:
        schema: The GraphQL schema to validate

    Returns:
        List of error messages for invalid enum defaults
    """
    errors = []

    for type_name, type_obj in schema.type_map.items():
        # Validate directive usage on types
        if type_obj.ast_node and type_obj.ast_node.directives:
            for directive_node in type_obj.ast_node.directives:
                errors.extend(_check_directive_usage_on_node(schema, directive_node, f"Type '{type_name}'"))

        # Validate input object field defaults
        if isinstance(type_obj, GraphQLInputObjectType):
            for field_name, field in type_obj.fields.items():
                named_type = get_named_type(field.type)
                if not isinstance(named_type, GraphQLEnumType):
                    continue

                has_default_in_ast = field.ast_node and field.ast_node.default_value is not None
                if not (has_default_in_ast and field.default_value is Undefined):
                    continue

                invalid_value = field.ast_node.default_value.value
                errors.append(
                    f"Input type '{type_name}.{field_name}' has invalid enum default value '{invalid_value}'. "
                    f"Valid values are: {list(named_type.values.keys())}"
                )

        # Validate field argument defaults and directive usage on fields
        if isinstance(type_obj, GraphQLObjectType | GraphQLInterfaceType | GraphQLInputObjectType):
            for field_name, field in type_obj.fields.items():
                # Validate directive usage on fields
                if field.ast_node and field.ast_node.directives:
                    for directive_node in field.ast_node.directives:
                        errors.extend(
                            _check_directive_usage_on_node(schema, directive_node, f"Field '{type_name}.{field_name}'")
                        )

                # Validate field argument defaults
                if isinstance(type_obj, GraphQLObjectType | GraphQLInterfaceType):
                    for arg_name, arg in field.args.items():
                        named_type = get_named_type(arg.type)
                        if not isinstance(named_type, GraphQLEnumType):
                            continue

                        has_default_in_ast = arg.ast_node and arg.ast_node.default_value is not None
                        if not (has_default_in_ast and arg.default_value is Undefined):
                            continue

                        invalid_value = arg.ast_node.default_value.value
                        errors.append(
                            f"Field argument '{type_name}.{field_name}({arg_name})' "
                            f"has invalid enum default value '{invalid_value}'. "
                            f"Valid values are: {list(named_type.values.keys())}"
                        )

    # Validate directive definition defaults
    for directive in schema.directives:
        for arg_name, arg in directive.args.items():
            named_type = get_named_type(arg.type)
            if not isinstance(named_type, GraphQLEnumType):
                continue

            if not arg.ast_node or not arg.ast_node.default_value:
                continue

            if arg.default_value is not Undefined:
                continue

            if not isinstance(arg.ast_node.default_value, EnumValueNode):
                continue

            invalid_value = arg.ast_node.default_value.value
            errors.append(
                f"Directive definition '@{directive.name}({arg_name})' "
                f"has invalid enum default value '{invalid_value}'. Valid values are: {list(named_type.values.keys())}"
            )

    return errors


def check_correct_schema(schema: GraphQLSchema) -> list[str]:
    """Assert that the schema conforms to GraphQL specification and has valid enum defaults.

    Args:
        schema: The GraphQL schema to validate

    Returns:
        list[str]: List of error messages if any validation errors are found

    Exits:
        Calls sys.exit(1) if the schema has validation errors
    """
    spec_errors = validate_schema(schema)
    enum_errors = check_enum_defaults(schema)

    all_errors: list[str] = []

    if spec_errors:
        for spec_error in spec_errors:
            all_errors.append(f"  - {spec_error.message}")

    if enum_errors:
        for enum_error in enum_errors:
            all_errors.append(f"  - {enum_error}")

    return all_errors


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


def get_referenced_types(
    graphql_schema: GraphQLSchema, root_type: str, include_instance_tag_fields: bool = False
) -> set[GraphQLType]:
    """
    Find all GraphQL types referenced from the root type through graph traversal.

    Args:
        graphql_schema: The GraphQL schema
        root_type: The root type to start traversal from
        include_instance_tag_fields: Whether to traverse fields of @instanceTag types to find their dependencies

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

        if is_object_type(type_def):
            object_type = cast(GraphQLObjectType, type_def)
            if not has_given_directive(object_type, "instanceTag") or include_instance_tag_fields:
                visit_object_type(object_type)
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


def _validate_schema(schema: GraphQLSchema, document: DocumentNode) -> GraphQLSchema | None:
    log.debug("Validating schema against the provided document")

    errors = graphql_validate(schema, document)
    if errors:
        log.error("Schema validation failed:")
        for error in errors:
            log.error(f" - {error}")
        return None

    log.debug("Schema validation succeeded")

    return schema


def prune_schema_using_query_selection(
    schema: GraphQLSchema, document: DocumentNode, include_instance_tag_fields: bool = False
) -> GraphQLSchema:
    """
    Filter schema by pruning unselected fields and types based on query selections.

    Args:
        schema: The original GraphQL schema
        document: Parsed query document
        include_instance_tag_fields: Whether to preserve instanceTag fields

    Returns:
        The modified schema with only the selected fields and types
    """
    if not schema.query_type:
        raise ValueError("Schema has no query type defined")

    if _validate_schema(schema, document) is None:
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

        if include_instance_tag_fields and "instanceTag" in obj_type.fields:
            fields_to_keep[type_name].add("instanceTag")
            instance_tag_field = obj_type.fields["instanceTag"]
            instance_tag_type = get_named_type(instance_tag_field.type)
            if instance_tag_type:
                types_to_keep.add(instance_tag_type.name)

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


def build_annotated_schema(
    schema: GraphQLSchema,
    source_map: dict[str, str],
    expansion_type_meta: dict[str, TypeMetadata],
    expansion_field_meta: dict[tuple[str, str], FieldMetadata],
) -> AnnotatedSchema:
    """Build an annotated schema by combining source map and expansion metadata."""
    source_type_metadata = {
        name: TypeMetadata(source=source_map[name], is_intermediate_type=False)
        for name in schema.type_map
        if name in source_map and name not in expansion_type_meta
    }

    type_metadata = {**source_type_metadata, **expansion_type_meta}

    non_expanded_field_metadata = {}
    for type_name, type_obj in schema.type_map.items():
        if is_introspection_or_root_type(type_name):
            continue

        if not is_object_type(type_obj) and not is_interface_type(type_obj):
            continue

        obj_type = cast(GraphQLObjectType | GraphQLInterfaceType, type_obj)
        for field_name, field in obj_type.fields.items():
            if (type_name, field_name) in expansion_field_meta:
                continue

            field_type = get_named_type(field.type)
            non_expanded_field_metadata[(type_name, field_name)] = FieldMetadata(
                resolved_names=[field_name],
                resolved_type=field_type.name,
                is_expanded=False,
                instances=[],
            )

    field_metadata = {**non_expanded_field_metadata, **expansion_field_meta}

    return AnnotatedSchema(schema=schema, type_metadata=type_metadata, field_metadata=field_metadata)


def process_schema(
    schema: GraphQLSchema,
    source_map: dict[str, str],
    naming_config: dict[str, Any] | None = None,
    query_document: DocumentNode | None = None,
    root_type: str | None = None,
    expanded_instances: bool = False,
) -> AnnotatedSchema:
    """Apply transformations to a GraphQL schema.

    Args:
        schema: The GraphQL schema to process
        source_map: Mapping of type names to their source files
        naming_config: Optional naming configuration dict
        query_document: Optional parsed GraphQL query document for filtering
        root_type: Optional root type name to filter the schema
        expanded_instances: Whether to expand instance tags into nested structures

    Returns:
        Annotated schema with metadata
    """
    if query_document:
        schema = prune_schema_using_query_selection(schema, query_document, expanded_instances)

    if root_type:
        schema = filter_schema(schema, root_type)

    if naming_config:
        apply_naming_to_schema(schema, naming_config)

    expansion_type_meta: dict[str, TypeMetadata] = {}
    expansion_field_meta: dict[tuple[str, str], FieldMetadata] = {}

    if expanded_instances:
        schema, expansion_type_meta, expansion_field_meta = expand_instances_in_schema(schema, naming_config)

    return build_annotated_schema(schema, source_map, expansion_type_meta, expansion_field_meta)


def load_and_process_schema(
    schema_paths: list[Path],
    naming_config_path: Path | None = None,
    selection_query_path: Path | None = None,
    root_type: str | None = None,
    expanded_instances: bool = False,
) -> tuple[AnnotatedSchema, dict[str, Any] | None, DocumentNode | None]:
    """Load schema with naming config and apply filtering based on selection query and root type.

    Args:
        schema_paths: List of paths to GraphQL schema files or directories
        naming_config_path: Optional path to naming configuration YAML file
        selection_query_path: Optional path to GraphQL query file for filtering
        root_type: Optional root type name to filter the schema
        expanded_instances: Whether to include instance tag fields when filtering by root type

    Returns:
        Tuple of (annotated schema, naming config dict, selection query document)
    """
    naming_config = load_naming_config(naming_config_path)

    schema, source_map = load_schema_with_source_map(schema_paths, naming_config)

    query_document = None
    if selection_query_path:
        query_document = parse(selection_query_path.read_text())

    annotated_schema = process_schema(schema, source_map, naming_config, query_document, root_type, expanded_instances)

    return annotated_schema, naming_config, query_document
