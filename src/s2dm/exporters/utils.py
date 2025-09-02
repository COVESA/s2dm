import os
import tempfile
from dataclasses import dataclass
from enum import Enum
from itertools import product
from pathlib import Path
from typing import Any, cast

from ariadne import load_schema_from_path
from graphql import (
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLList,
    GraphQLNonNull,
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
)
from graphql.language.ast import FloatValueNode, IntValueNode
from graphql.type import (
    GraphQLField,
    GraphQLNamedType,
    GraphQLObjectType,
    GraphQLSchema,
)
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
            field_type = field.type
            if isinstance(field.type, GraphQLNonNull):
                field_type = get_named_type(field.type)
            if not isinstance(field_type, GraphQLEnumType):
                # TODO: Move this check to a validation function for the @instanceTag directive
                raise TypeError(f"Field '{field_name}' in object '{object.name}' is not an enum.")
            tags_per_enum_field.append(list(field_type.values.keys()))
        log.debug(f"Tags per field: {tags_per_enum_field}")

        # Combine tags from different enum fields
        for combination in product(*tags_per_enum_field):
            expanded_tags.append(".".join(combination))  # <-- Character separator can be changed HERE

        log.debug(f"Expanded tags: {expanded_tags}")

        return expanded_tags


def get_directive_arguments(element: GraphQLField | GraphQLObjectType, directive_name: str) -> dict[str, Any]:
    """
    Extracts the arguments of a specified directive from a GraphQL element.
    Args:
        element: The GraphQL element from which to extract the directive arguments.
        directive_name: The name of the directive whose arguments are to be extracted.
    Returns:
        dict[str, Any]: A dictionary containing the directive arguments with proper type conversion.
    """
    if not has_directive(element, directive_name) or not element.ast_node:
        return {}

    directive = next(d for d in element.ast_node.directives if d.name.value == directive_name)
    args: dict[str, Any] = {}

    for arg in directive.arguments:
        arg_name = arg.name.value
        if hasattr(arg.value, "value"):
            if isinstance(arg.value, IntValueNode):
                args[arg_name] = int(arg.value.value)
            elif isinstance(arg.value, FloatValueNode):
                args[arg_name] = float(arg.value.value)
            else:
                args[arg_name] = arg.value.value
        else:
            args[arg_name] = arg.value

    return args


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


def search_schema(
    schema: GraphQLSchema,
    type_name: str | None = None,
    field_name: str | None = None,
    partial: bool = False,
    case_insensitive: bool = False,
) -> dict[str, list[Any] | None]:
    """
    Search for types and/or fields in a GraphQL schema.

    Args:
        schema (GraphQLSchema): The schema to search.
        type_name (str, optional): The name (or partial name) of the type to search for.
        field_name (str, optional): The name (or partial name) of the field to search for within the type(s).
        partial (bool): If True, allows partial (substring) matches for type and field names.
        case_insensitive (bool): If True, search is case-insensitive.

    Returns:
        dict: {type_name: [field_names]} for matches, or just type names if field_name is None.
    """
    results: dict[str, list[Any] | None] = {}
    for tname, t in schema.type_map.items():
        if tname.startswith("__"):
            continue
        tname_cmp = tname.lower() if case_insensitive else tname
        type_name_cmp = type_name.lower() if (type_name and case_insensitive) else type_name
        type_match = (
            type_name is None
            or (partial and type_name_cmp is not None and type_name_cmp in tname_cmp)
            or (not partial and type_name_cmp is not None and tname_cmp == type_name_cmp)
        )
        if type_match:
            fields = getattr(t, "fields", None)
            if callable(fields):
                fields = fields()
            if isinstance(fields, dict):
                if field_name:
                    field_name_cmp = field_name.lower() if case_insensitive else field_name
                    matched_fields = [
                        fname
                        for fname in fields
                        if (partial and field_name_cmp in (fname.lower() if case_insensitive else fname))
                        or (not partial and (fname.lower() if case_insensitive else fname) == field_name_cmp)
                    ]
                    if matched_fields:
                        results[tname] = matched_fields
                else:
                    results[tname] = list(fields)
            else:
                continue

    return results


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

        if type_name.startswith("__"):
            return

        if type_name in {"Query", "Mutation", "Subscription"}:
            return

        type_def = graphql_schema.type_map.get(type_name)
        if not type_def:
            return

        referenced.add(type_def)

        if is_object_type(type_def) and not has_directive(cast(GraphQLObjectType, type_def), "instanceTag"):
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
