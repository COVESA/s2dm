import json
from pathlib import Path
from typing import Any

from graphql import GraphQLSchema

from s2dm import log
from s2dm.exporters.utils import load_schema_with_naming

from .transformer import JsonSchemaTransformer


def transform(
    graphql_schema: GraphQLSchema, root_type: str | None = None, strict: bool = False, expanded_instances: bool = False
) -> str:
    """
    Transform a GraphQL schema object to JSON Schema format.

    Args:
        graphql_schema: The GraphQL schema object to transform
        root_type: Optional root type name for the JSON schema
        strict: Enforce strict field nullability translation from GraphQL to JSON Schema
        expanded_instances: Expand instance tags into nested structure instead of arrays

    Returns:
        str: JSON Schema representation as a string
    """
    log.info(f"Transforming GraphQL schema to JSON Schema with {len(graphql_schema.type_map)} types")

    if root_type:
        if root_type not in graphql_schema.type_map:
            raise ValueError(f"Root type '{root_type}' not found in schema")
        log.info(f"Using root type: {root_type}")

    transformer = JsonSchemaTransformer(graphql_schema, root_type, strict, expanded_instances)
    json_schema = transformer.transform()

    json_schema_str = json.dumps(json_schema, indent=2)

    log.info("Successfully converted GraphQL schema to JSON Schema")

    return json_schema_str


def translate_to_jsonschema(
    schema_path: Path,
    root_type: str | None = None,
    strict: bool = False,
    expanded_instances: bool = False,
    naming_config: dict[str, Any] | None = None,
) -> str:
    """
    Translate a GraphQL schema file to JSON Schema format.

    Args:
        schema_path: Path to a GraphQL schema file or directory containing schema files
        root_type: Optional root type name for the JSON schema
        strict: Enforce strict field nullability translation from GraphQL to JSON Schema
        expanded_instances: Expand instance tags into nested structure instead of arrays

    Returns:
        str: JSON Schema representation as a string
    """
    log.info(f"Loading GraphQL schema from: {schema_path}")

    graphql_schema = load_schema_with_naming(schema_path, naming_config)
    log.info(f"Successfully loaded GraphQL schema with {len(graphql_schema.type_map)} types")

    return transform(graphql_schema, root_type, strict, expanded_instances)
