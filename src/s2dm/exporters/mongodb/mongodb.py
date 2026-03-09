import json
from typing import Any

from graphql import GraphQLSchema

from s2dm import log
from s2dm.exporters.utils.annotated_schema import AnnotatedSchema

from .transformer import MongoDBTransformer


def transform(graphql_schema: GraphQLSchema) -> dict[str, dict[str, Any]]:
    """Return a bare BSON schema dict for every exportable type in the schema."""
    log.info(f"Transforming GraphQL schema to MongoDB BSON validators ({len(graphql_schema.type_map)} types)")
    result = MongoDBTransformer(graphql_schema).transform()
    log.info(f"Generated {len(result)} MongoDB BSON schema(s)")
    return result


def translate_to_mongodb(annotated_schema: AnnotatedSchema) -> dict[str, dict[str, Any]]:
    """Unwrap an ``AnnotatedSchema`` and delegate to :func:`transform`."""
    return transform(annotated_schema.schema)


def to_json_string(schemas: dict[str, dict[str, Any]]) -> str:
    """Serialize the full validator map to a pretty-printed JSON string."""
    return json.dumps(schemas, indent=2)
