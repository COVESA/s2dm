import json
from typing import Any

from graphql import GraphQLSchema

from s2dm import log

from .transformer import JsonSchemaTransformer


def transform(
    graphql_schema: GraphQLSchema,
    root_type: str | None = None,
    strict: bool = False,
    expanded_instances: bool = False,
    naming_config: dict[str, Any] | None = None,
) -> str:
    """
    Transform a GraphQL schema object to JSON Schema format.

    Args:
        graphql_schema: The GraphQL schema object to transform
        root_type: Optional root type name for the JSON schema
        strict: Enforce strict field nullability translation from GraphQL to JSON Schema
        expanded_instances: Expand instance tags into nested structure instead of arrays
        naming_config: Optional naming configuration for instance tag expansion

    Returns:
        str: JSON Schema representation as a string
    """
    log.info(f"Transforming GraphQL schema to JSON Schema with {len(graphql_schema.type_map)} types")

    if root_type:
        if root_type not in graphql_schema.type_map:
            raise ValueError(f"Root type '{root_type}' not found in schema")
        log.info(f"Using root type: {root_type}")

    transformer = JsonSchemaTransformer(graphql_schema, root_type, strict, expanded_instances, naming_config)
    json_schema = transformer.transform()

    json_schema_str = json.dumps(json_schema, indent=2)

    log.info("Successfully converted GraphQL schema to JSON Schema")

    return json_schema_str


def translate_to_jsonschema(
    schema: GraphQLSchema,
    root_type: str | None = None,
    strict: bool = False,
    expanded_instances: bool = False,
    naming_config: dict[str, Any] | None = None,
) -> str:
    """
    Translate a GraphQL schema file to JSON Schema format.

    Args:
        schema_paths: List of paths to GraphQL schema files or directories
        root_type: Optional root type name for the JSON schema
        strict: Enforce strict field nullability translation from GraphQL to JSON Schema
        expanded_instances: Expand instance tags into nested structure instead of arrays

    Returns:
        str: JSON Schema representation as a string
    """
    return transform(schema, root_type, strict, expanded_instances, naming_config)
