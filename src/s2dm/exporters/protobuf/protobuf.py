from graphql import GraphQLSchema

from s2dm import log

from .transformer import ProtobufTransformer


def transform(
    graphql_schema: GraphQLSchema,
    package_name: str | None = None,
    flatten_root_types: list[str] | None = None,
) -> str:
    """
    Transform a GraphQL schema object to Protocol Buffers format.

    Args:
        graphql_schema: The GraphQL schema object to transform
        package_name: Optional package name for the .proto file
        flatten_root_types: Optional list of root type names for flatten mode

    Returns:
        str: Protocol Buffers representation as a string
    """
    log.info(f"Transforming GraphQL schema to Protobuf with {len(graphql_schema.type_map)} types")

    transformer = ProtobufTransformer(graphql_schema, package_name, flatten_root_types)
    proto_content = transformer.transform()

    log.info("Successfully converted GraphQL schema to Protobuf")

    return proto_content


def translate_to_protobuf(
    schema: GraphQLSchema,
    package_name: str | None = None,
    flatten_root_types: list[str] | None = None,
) -> str:
    """
    Translate a GraphQL schema to Protocol Buffers format.

    Args:
        schema: The GraphQL schema object
        package_name: Optional package name for the .proto file
        flatten_root_types: Optional list of root type names for flatten mode

    Returns:
        str: Protocol Buffers (.proto) representation as a string
    """
    return transform(schema, package_name, flatten_root_types)
