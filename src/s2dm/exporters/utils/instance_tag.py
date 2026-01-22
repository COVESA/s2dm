from itertools import product
from typing import Any, cast

from graphql import (
    GraphQLEnumType,
    GraphQLField,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLSchema,
    get_named_type,
    is_list_type,
    is_non_null_type,
)

from s2dm import log
from s2dm.exporters.utils.annotated_schema import FieldMetadata, TypeMetadata
from s2dm.exporters.utils.directive import has_given_directive
from s2dm.exporters.utils.extraction import get_all_object_types, get_all_objects_with_directive
from s2dm.exporters.utils.naming import apply_naming_to_instance_values, convert_name, get_target_case_for_element


def is_instance_tag_field(field_name: str) -> bool:
    return field_name == "instanceTag"


def get_all_expanded_instance_tags(
    schema: GraphQLSchema,
    naming_config: dict[str, Any] | None = None,
) -> dict[GraphQLObjectType, list[str]]:
    all_expanded_instance_tags: dict[GraphQLObjectType, list[str]] = {}
    for object in get_all_objects_with_directive(get_all_object_types(schema), "instanceTag"):
        all_expanded_instance_tags[object] = expand_instance_tag(object, naming_config)

    log.debug(f"All expanded tags in the spec: {all_expanded_instance_tags}")

    return all_expanded_instance_tags


def expand_instance_tag(object: GraphQLObjectType, naming_config: dict[str, Any] | None = None) -> list[str]:
    log.debug(f"Expanding instanceTag for object: {object.name}")
    expanded_tags = []
    if not has_given_directive(object, "instanceTag"):
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

            enum_values = apply_naming_to_instance_values(list(field_type.values.keys()), naming_config)
            tags_per_enum_field.append(enum_values)
        log.debug(f"Tags per field: {tags_per_enum_field}")

        # Combine tags from different enum fields
        for combination in product(*tags_per_enum_field):
            expanded_tags.append(".".join(combination))  # <-- Character separator can be changed HERE

        log.debug(f"Expanded tags: {expanded_tags}")

        return expanded_tags


def is_valid_instance_tag_field(field: GraphQLField, schema: GraphQLSchema) -> bool:
    """
    Check if the output type of the given field is a valid instanceTag.
    A valid instanceTag is an object type with the @instanceTag directive.

    Args:
        field (GraphQLField): The field to check.
        schema (GraphQLSchema): The GraphQL schema to validate against.

    Returns:
        bool: True if the field's output type is a valid instanceTag, False otherwise.
    """
    output_type = schema.get_type(get_named_type(field.type).name)
    return isinstance(output_type, GraphQLObjectType) and has_given_directive(output_type, "instanceTag")


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

    instance_tag_field_name = "instanceTag"
    if instance_tag_field_name in object_type.fields:
        field = object_type.fields[instance_tag_field_name]
        instance_tag_type = schema.get_type(get_named_type(field.type).name)
        if isinstance(
            instance_tag_type, GraphQLObjectType
        ):  # and has_given_directive(instance_tag_type, instance_tag_field_name):
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
        field_type = field.type
        if is_non_null_type(field_type):
            field_type = cast(GraphQLNonNull[Any], field_type).of_type

        if isinstance(field_type, GraphQLEnumType):
            instance_tag_dict[field_name] = list(field_type.values.keys())
        else:
            raise TypeError(f"Field '{field_name}' in object '{instance_tag_object.name}' is not an enum.")

    return instance_tag_dict


def is_expandable_field(field: GraphQLField, schema: GraphQLSchema) -> bool:
    """
    Check if a field is expandable (has a base type that has instanceTag).

    Args:
        field: The GraphQL field to check
        schema: The GraphQL schema to validate against

    Returns:
        True if the field is expandable, False otherwise
    """
    base_type = get_named_type(field.type)
    if isinstance(base_type, GraphQLObjectType):
        return has_valid_instance_tag_field(base_type, schema)

    return False


def _collect_expandable_fields(
    schema: GraphQLSchema,
) -> list[tuple[GraphQLObjectType, str]]:
    """
    Collect all fields in the schema that need instance expansion.

    Args:
        schema: The GraphQL schema to scan

    Returns:
        List of tuples: (parent_type, field_name)
    """
    expandable_fields = []
    all_object_types = get_all_object_types(schema)

    for object_type in all_object_types:
        for field_name, field in object_type.fields.items():
            if is_expandable_field(field, schema):
                expandable_fields.append((object_type, field_name))

    return expandable_fields


def _create_intermediate_types(
    base_type: GraphQLObjectType,
    instance_tag_dict: dict[str, list[str]],
    list_item_nullable: bool,
) -> list[GraphQLObjectType]:
    """
    Create intermediate GraphQL types for instance expansion.

    Args:
        base_type: The base type (e.g., Door)
        instance_tag_dict: Dict of enum field names to their values
        list_item_nullable: Whether the original list items were nullable

    Returns:
        List of intermediate types, with first intermediate type at the end
    """
    enum_fields = list(instance_tag_dict.keys())
    intermediate_types: list[GraphQLObjectType] = []

    for i in range(len(enum_fields) - 1, -1, -1):
        enum_field_name = enum_fields[i]
        enum_values = instance_tag_dict[enum_field_name]

        intermediate_type_name = f"{base_type.name}_{enum_field_name.capitalize()}"

        is_leaf_level = i == len(enum_fields) - 1
        target_type = base_type if is_leaf_level else intermediate_types[-1]

        intermediate_fields = {}
        for enum_value in enum_values:
            field_type: GraphQLObjectType | GraphQLNonNull[GraphQLObjectType] = (
                target_type if is_leaf_level and list_item_nullable else GraphQLNonNull(target_type)
            )
            intermediate_fields[enum_value] = GraphQLField(field_type)

        intermediate_type = GraphQLObjectType(
            name=intermediate_type_name,
            fields=intermediate_fields,
        )

        intermediate_types.append(intermediate_type)
        log.debug(f"Created intermediate type '{intermediate_type_name}' with fields: {list(enum_values)}")

    return intermediate_types


def expand_instances_in_schema(
    schema: GraphQLSchema,
    naming_config: dict[str, Any] | None = None,
) -> tuple[GraphQLSchema, dict[str, "TypeMetadata"], dict[tuple[str, str], "FieldMetadata"]]:
    """
    Expand instance-tagged fields in a GraphQL schema into nested object structures.

    For fields with types that contain instanceTag fields, this function creates intermediate
    GraphQL types representing each level of the instance tag hierarchy and modifies the
    parent field to use the singular type name.

    Args:
        schema: The GraphQL schema to modify
        naming_config: Optional naming configuration for transforming type and field names

    Returns:
        Tuple of (modified schema, type metadata dict, field metadata dict)
    """
    log.info("Starting instance expansion in schema")

    expandable_fields = _collect_expandable_fields(schema)
    log.info(f"Found {len(expandable_fields)} expandable fields")

    base_types_to_clean: set[GraphQLObjectType] = set()
    instance_tag_types_to_remove: set[str] = set()
    new_types: dict[str, GraphQLObjectType] = {}
    type_metadata: dict[str, TypeMetadata] = {}
    field_metadata: dict[tuple[str, str], FieldMetadata] = {}

    # TODO: Optimization - Cache expanded types to avoid creating duplicate intermediate types
    # When multiple fields reference the same base type (e.g., Cabin.doors and Vehicle.doors both reference [Door]),
    # we currently create intermediate types twice. Instead, maintain a cache:
    # expanded_types_cache: dict[str, GraphQLObjectType] = {}  # Maps base_type.name -> first_intermediate_type
    # Check cache before creating, reuse if exists, otherwise create once and cache.

    for parent_type, field_name in expandable_fields:
        original_field = parent_type.fields[field_name]
        base_type = cast(GraphQLObjectType, get_named_type(original_field.type))

        log.debug(f"Processing field '{field_name}' in type '{parent_type.name}' with base type '{base_type.name}'")

        unwrapped_type = original_field.type
        if is_non_null_type(unwrapped_type):
            unwrapped_type = unwrapped_type.of_type

        target_type = unwrapped_type.of_type if is_list_type(unwrapped_type) else unwrapped_type
        list_item_nullable = not is_non_null_type(target_type)

        instance_tag_object = cast(GraphQLObjectType, get_instance_tag_object(base_type, schema))
        instance_tag_dict = get_instance_tag_dict(instance_tag_object)
        instance_tag_types_to_remove.add(instance_tag_object.name)

        intermediate_types = _create_intermediate_types(base_type, instance_tag_dict, list_item_nullable)
        first_intermediate_type = intermediate_types[-1]

        type_case = get_target_case_for_element("type", "object", naming_config) if naming_config else None
        field_case = get_target_case_for_element("field", "object", naming_config) if naming_config else None

        for intermediate_type in intermediate_types:
            type_name = convert_name(intermediate_type.name, type_case) if type_case else intermediate_type.name
            intermediate_type.name = type_name
            new_types[type_name] = intermediate_type
            type_metadata[type_name] = TypeMetadata(source=None, is_intermediate_type=True)

        base_name = base_type.name if is_list_type(unwrapped_type) else field_name
        new_field_name = convert_name(base_name, field_case) if field_case else base_name

        resolved_names = [
            f"{new_field_name}.{'.'.join(instance_product)}"
            for instance_product in product(*instance_tag_dict.values())
        ]

        instances = list(instance_tag_dict.values())

        new_field = GraphQLField(
            type_=GraphQLNonNull(first_intermediate_type),
            description=original_field.description,
        )

        field_metadata[(parent_type.name, new_field_name)] = FieldMetadata(
            resolved_names=resolved_names,
            resolved_type=base_type.name,
            is_expanded=True,
            original_field=original_field,
            instances=instances,
        )

        del parent_type.fields[field_name]
        parent_type.fields[new_field_name] = new_field

        log.debug(f"Replaced field '{field_name}' with '{new_field_name}' in type '{parent_type.name}'")

        base_types_to_clean.add(base_type)

    all_types_to_remove = set(instance_tag_types_to_remove)
    all_instance_tag_types = get_all_objects_with_directive(get_all_object_types(schema), "instanceTag")
    all_types_to_remove.update(t.name for t in all_instance_tag_types)

    for base_type in base_types_to_clean:
        del base_type.fields["instanceTag"]
        log.debug(f"Removed 'instanceTag' field from type '{base_type.name}'")

    for type_name in all_types_to_remove:
        if type_name in schema.type_map:
            del schema.type_map[type_name]
            log.debug(f"Removed type '{type_name}' with @instanceTag directive from schema")

    for type_name, new_type in new_types.items():
        schema.type_map[type_name] = new_type

    log.info(f"Instance expansion complete. Created {len(new_types)} intermediate types")

    return schema, type_metadata, field_metadata
