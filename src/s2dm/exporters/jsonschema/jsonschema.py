import json

from graphql import GraphQLSchema

from s2dm import log

from .transformer import JsonSchemaTransformer


def transform(
    graphql_schema: GraphQLSchema,
    root_type: str | None = None,
    strict: bool = False,
) -> str:
    """
    Transform a GraphQL schema object to JSON Schema format.

    Args:
        graphql_schema: The GraphQL schema object to transform
        strict: Enforce strict field nullability translation from GraphQL to JSON Schema
        root_type: Optional root type name for the JSON schema

    Returns:
        str: JSON Schema representation as a string
    """
    log.info(f"Transforming GraphQL schema to JSON Schema with {len(graphql_schema.type_map)} types")

    transformer = JsonSchemaTransformer(graphql_schema, root_type, strict)
    json_schema = transformer.transform()

    json_schema_str = json.dumps(json_schema, indent=2)

    log.info("Successfully converted GraphQL schema to JSON Schema")

    return json_schema_str


def translate_to_jsonschema(
    schema: GraphQLSchema,
    root_type: str | None = None,
    strict: bool = False,
) -> str:
    """
    Translate a GraphQL schema file to JSON Schema format.

    Args:
        schema: The GraphQL schema object to transform
        strict: Enforce strict field nullability translation from GraphQL to JSON Schema
        root_type: Optional root type name for the JSON schema

    Returns:
        str: JSON Schema representation as a string
    """
    return transform(schema, root_type, strict)
