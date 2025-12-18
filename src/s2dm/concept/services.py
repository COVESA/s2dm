from graphql import (
    GraphQLEnumType,
    GraphQLList,
    GraphQLNamedType,
    GraphQLObjectType,
    GraphQLScalarType,
    get_named_type,
    is_scalar_type,
)

from s2dm import log
from s2dm.concept.models import Concepts, FieldMetadata
from s2dm.exporters.utils.graphql_type import is_id_type, is_introspection_or_root_type


def iter_all_concepts(named_types: list[GraphQLNamedType]) -> Concepts:
    """Extract all concepts from GraphQL named types with enhanced metadata.

    This function extracts all concepts and captures additional GraphQL
    field definitions for enhanced functionality (like SKOS generation),
    while maintaining backward compatibility.

    Args:
        named_types: List of GraphQL named types to process

    Returns:
        Concepts object containing all extracted concepts plus field metadata
    """
    concepts = Concepts()
    for named_type in named_types:
        if is_introspection_or_root_type(named_type.name):
            continue

        if isinstance(named_type, GraphQLEnumType):
            log.debug(f"Processing enum: {named_type.name}")
            concepts.enums.append(named_type.name)

        elif isinstance(named_type, GraphQLObjectType):
            log.debug(f"Processing object: {named_type.name}")
            # Get the ID of all fields in the object
            for field_name, field in named_type.fields.items():
                # Check if field's type is ID scalar - skip ID fields
                field_type = get_named_type(field.type)
                if (
                    is_scalar_type(field_type)
                    and isinstance(field_type, GraphQLScalarType)
                    and is_id_type(field_type.name)
                ):
                    continue

                field_fqn = f"{named_type.name}.{field_name}"

                if isinstance(field.type, GraphQLObjectType):
                    # field uses the object type
                    concepts.nested_objects[field_fqn] = field.type.name
                elif isinstance(field.type, GraphQLList):
                    # field uses a list of the object type
                    internal_type = field.type
                    while hasattr(internal_type, "of_type"):
                        internal_type = internal_type.of_type
                    # Get the name from the internal type if it has one
                    internal_type_name = getattr(internal_type, "name", None)
                    if internal_type_name:
                        concepts.nested_objects[field_fqn] = internal_type_name
                else:
                    # field uses a scalar type or enum type
                    concepts.objects[named_type.name].append(field_fqn)
                    concepts.fields.append(field_fqn)
                    # Enhanced metadata for advanced functionality (SKOS generation, etc.)
                    concepts.field_metadata[field_fqn] = FieldMetadata(
                        object_name=named_type.name, field_name=field_name, field_definition=field
                    )

    return concepts
