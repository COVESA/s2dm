import json

from graphql import DocumentNode

from s2dm import log
from s2dm.exporters.utils.annotated_schema import AnnotatedSchema

from .schema_transformer import AvroSchemaTransformer


def transform(
    annotated_schema: AnnotatedSchema,
    namespace: str,
    selection_query: DocumentNode,
) -> str:
    """
    Transform an annotated GraphQL schema to Avro schema format.

    Args:
        annotated_schema: The annotated GraphQL schema object
        namespace: Namespace for Avro types (required for valid cross-type references)
        selection_query: Required selection query document to determine root-level types

    Returns:
        str: Avro schema representation as a JSON string
    """
    log.info(f"Transforming GraphQL schema to Avro schema with {len(annotated_schema.schema.type_map)} types")

    transformer = AvroSchemaTransformer(annotated_schema, namespace, selection_query)
    avro_schema = transformer.transform()

    avro_schema_str = json.dumps(avro_schema, indent=2)

    log.info("Successfully converted GraphQL schema to Avro schema")

    return avro_schema_str


def translate_to_avro_schema(
    annotated_schema: AnnotatedSchema,
    namespace: str,
    selection_query: DocumentNode,
) -> str:
    """
    Translate a GraphQL schema to Avro schema format.

    Args:
        annotated_schema: The annotated GraphQL schema object
        namespace: Namespace for Avro types (required for valid cross-type references)
        selection_query: Required selection query document to determine root-level types

    Returns:
        str: Avro schema representation as a JSON string
    """
    return transform(annotated_schema, namespace, selection_query)
