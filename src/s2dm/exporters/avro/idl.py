from typing import cast

from graphql import GraphQLNamedType, GraphQLObjectType, is_named_type
from graphql.language.ast import ListValueNode, ObjectValueNode, StringValueNode

from s2dm import log
from s2dm.exporters.utils.annotated_schema import AnnotatedSchema
from s2dm.exporters.utils.directive import get_argument_content
from s2dm.exporters.utils.extraction import get_all_object_types, get_all_objects_with_directive
from s2dm.exporters.utils.schema_loader import get_referenced_types

from .idl_transformer import AvroIDLTransformer

VSPEC_DIRECTIVE = "vspec"
STRUCT_ELEMENT = "STRUCT"


def _get_namespace_from_metadata(object_type: GraphQLObjectType, global_namespace: str) -> str:
    """Extract namespace from @vspec metadata key-value pairs, fallback to global."""
    metadata = get_argument_content(object_type, VSPEC_DIRECTIVE, "metadata")

    if not metadata or not isinstance(metadata, ListValueNode):
        return global_namespace

    for item in metadata.values:
        if not isinstance(item, ObjectValueNode):
            continue

        key_field = None
        value_field = None
        for field in item.fields:
            if not isinstance(field.value, StringValueNode):
                continue

            if field.name.value == "key":
                key_field = field.value.value
            elif field.name.value == "value":
                value_field = field.value.value

        if key_field == "namespace" and value_field:
            return value_field

    return global_namespace


def generate_idl_for_struct_types(
    annotated_schema: AnnotatedSchema,
    namespace: str,
    strict: bool = False,
) -> dict[str, str]:
    """
    Generate Avro IDL protocols for types marked with @vspec(element: STRUCT) directive.

    Args:
        annotated_schema: The annotated GraphQL schema object
        namespace: Namespace for Avro types
        strict: Enforce strict type translation (enums as enums, nullability enforced)

    Returns:
        dict[str, str]: Mapping of type names to their IDL protocol definitions
    """
    schema = annotated_schema.schema
    all_objects = get_all_object_types(schema)
    vspec_types = get_all_objects_with_directive(all_objects, VSPEC_DIRECTIVE)
    struct_types = [
        vspec_type
        for vspec_type in vspec_types
        if get_argument_content(vspec_type, VSPEC_DIRECTIVE, "element") == STRUCT_ELEMENT
    ]

    log.info(f"Found {len(struct_types)} types with @{VSPEC_DIRECTIVE}(element: {STRUCT_ELEMENT}) directive")

    idl_protocols: dict[str, str] = {}

    for struct_type in struct_types:
        type_name = struct_type.name
        log.info(f"Generating IDL protocol for {type_name}")

        type_namespace = _get_namespace_from_metadata(struct_type, namespace)

        referenced_types = get_referenced_types(schema, type_name, include_instance_tag_fields=False)
        referenced_named_types: set[GraphQLNamedType] = {
            cast(GraphQLNamedType, graphql_type) for graphql_type in referenced_types if is_named_type(graphql_type)
        }

        transformer = AvroIDLTransformer(annotated_schema, type_namespace, type_name, referenced_named_types, strict)
        idl_content = transformer.transform()

        idl_protocols[type_name] = idl_content

    log.info(f"Successfully generated {len(idl_protocols)} IDL protocols")

    return idl_protocols


def translate_to_avro_idl(
    annotated_schema: AnnotatedSchema,
    namespace: str,
    strict: bool = False,
) -> dict[str, str]:
    """
    Translate a GraphQL schema to Avro IDL format for types with @vspec(element: STRUCT) directive.

    Args:
        annotated_schema: The annotated GraphQL schema object
        namespace: Namespace for Avro types
        strict: Enforce strict type translation (enums as enums, nullability enforced)

    Returns:
        dict[str, str]: Mapping of type names to their IDL protocol definitions
    """
    return generate_idl_for_struct_types(annotated_schema, namespace, strict)
