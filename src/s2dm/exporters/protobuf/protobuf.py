from typing import Any

from graphql import DocumentNode, GraphQLSchema

from s2dm import log

from .transformer import ProtobufTransformer


def transform(
    graphql_schema: GraphQLSchema,
    root_type: str | None = None,
    flatten_naming: bool = False,
    package_name: str | None = None,
    naming_config: dict[str, Any] | None = None,
    expanded_instances: bool = False,
    selection_query: DocumentNode | None = None,
) -> str:
    """
    Transform a GraphQL schema object to Protocol Buffers format.

    Args:
        graphql_schema: The GraphQL schema object to transform
        root_type: Optional root type name for the protobuf schema
        flatten_naming: If True, flatten nested field names
        package_name: Optional package name for the .proto file
        naming_config: Optional naming configuration
        expanded_instances: If True, expand instance tags into nested structures
        selection_query: Optional selection query document to determine root-level types

    Returns:
        str: Protocol Buffers representation as a string
    """
    log.info(f"Transforming GraphQL schema to Protobuf with {len(graphql_schema.type_map)} types")

    if root_type:
        if root_type not in graphql_schema.type_map:
            raise ValueError(f"Root type '{root_type}' not found in schema")
        log.info(f"Using root type: {root_type}")

    transformer = ProtobufTransformer(
        graphql_schema, root_type, flatten_naming, package_name, naming_config, expanded_instances, selection_query
    )
    proto_content = transformer.transform()

    log.info("Successfully converted GraphQL schema to Protobuf")

    return proto_content


def translate_to_protobuf(
    schema: GraphQLSchema,
    root_type: str | None = None,
    flatten_naming: bool = False,
    package_name: str | None = None,
    naming_config: dict[str, Any] | None = None,
    expanded_instances: bool = False,
    selection_query: DocumentNode | None = None,
) -> str:
    """
    Translate a GraphQL schema to Protocol Buffers format.

    Args:
        schema: The GraphQL schema object
        root_type: Optional root type name for the protobuf schema
        flatten_naming: If True, flatten nested field names
        package_name: Optional package name for the .proto file
        naming_config: Optional naming configuration
        expanded_instances: If True, expand instance tags into nested structures
        selection_query: Optional selection query document to determine root-level types

    Returns:
        str: Protocol Buffers (.proto) representation as a string
    """
    return transform(
        schema, root_type, flatten_naming, package_name, naming_config, expanded_instances, selection_query
    )
