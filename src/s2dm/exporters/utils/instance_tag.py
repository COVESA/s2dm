from itertools import product
from typing import Any

from graphql import GraphQLEnumType, GraphQLField, GraphQLNonNull, GraphQLObjectType, GraphQLSchema, get_named_type

from s2dm import log
from s2dm.exporters.utils.directive import has_given_directive
from s2dm.exporters.utils.extraction import get_all_object_types, get_all_objects_with_directive
from s2dm.exporters.utils.naming import apply_naming_to_instance_values


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
