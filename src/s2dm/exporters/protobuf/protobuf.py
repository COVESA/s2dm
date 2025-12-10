from graphql import DocumentNode

from s2dm import log
from s2dm.exporters.utils.annotated_schema import AnnotatedSchema

from .transformer import ProtobufTransformer


def transform(
    annotated_schema: AnnotatedSchema,
    selection_query: DocumentNode,
    package_name: str | None = None,
    flatten_root_types: list[str] | None = None,
) -> str:
    """
    Transform an annotated GraphQL schema to Protocol Buffers format.

    Args:
        annotated_schema: The annotated GraphQL schema object
        selection_query: Required selection query document to determine root-level types
        package_name: Optional package name for the .proto file
        flatten_root_types: Optional list of root type names for flatten mode

    Returns:
        str: Protocol Buffers representation as a string

    Raises:
        ValueError: If selection_query is not provided
    """
    log.info(f"Transforming GraphQL schema to Protobuf with {len(annotated_schema.schema.type_map)} types")

    transformer = ProtobufTransformer(annotated_schema, selection_query, package_name, flatten_root_types)
    proto_content = transformer.transform()

    log.info("Successfully converted GraphQL schema to Protobuf")

    return proto_content


def translate_to_protobuf(
    annotated_schema: AnnotatedSchema,
    selection_query: DocumentNode,
    package_name: str | None = None,
    flatten_root_types: list[str] | None = None,
) -> str:
    """
    Translate a GraphQL schema to Protocol Buffers format.

    Args:
        annotated_schema: The annotated GraphQL schema object
        selection_query: Required selection query document to determine root-level types
        package_name: Optional package name for the .proto file
        flatten_root_types: Optional list of root type names for flatten mode

    Returns:
        str: Protocol Buffers (.proto) representation as a string

    Raises:
        ValueError: If selection_query is not provided
    """
    return transform(annotated_schema, selection_query, package_name, flatten_root_types)
