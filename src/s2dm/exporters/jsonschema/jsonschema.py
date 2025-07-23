import json
from pathlib import Path

from graphql import GraphQLSchema

from s2dm import log
from s2dm.exporters.utils import load_schema

from .transformer import transform_to_json_schema


def transform(graphql_schema: GraphQLSchema, root_node: str | None = None) -> str:
    """
    Transform a GraphQL schema object to JSON Schema format.

    Args:
        graphql_schema: The GraphQL schema object to transform
        root_node: Optional root node type name for the JSON schema

    Returns:
        str: JSON Schema representation as a string
    """
    log.info(f"Transforming GraphQL schema to JSON Schema with {len(graphql_schema.type_map)} types")

    if root_node:
        if root_node not in graphql_schema.type_map:
            raise ValueError(f"Root node '{root_node}' not found in schema")
        log.info(f"Using root node: {root_node}")

    json_schema = transform_to_json_schema(graphql_schema, root_node)

    json_schema_str = json.dumps(json_schema, indent=2)

    log.info("Successfully converted GraphQL schema to JSON Schema")

    return json_schema_str


def translate_to_jsonschema(schema_path: Path, root_node: str | None = None) -> str:
    """
    Translate a GraphQL schema file to JSON Schema format.

    Args:
        schema_path: Path to a GraphQL schema file or directory containing schema files
        root_node: Optional root node type name for the JSON schema

    Returns:
        str: JSON Schema representation as a string
    """
    log.info(f"Loading GraphQL schema from: {schema_path}")

    graphql_schema = load_schema(schema_path)
    log.info(f"Successfully loaded GraphQL schema with {len(graphql_schema.type_map)} types")

    return transform(graphql_schema, root_node)
