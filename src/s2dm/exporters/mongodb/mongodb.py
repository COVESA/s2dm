import json
from pathlib import Path
from typing import Any

import yaml
from graphql import GraphQLSchema

from s2dm import log
from s2dm.exporters.utils.annotated_schema import AnnotatedSchema

from .transformer import MongoDBTransformer


def load_properties_config(config_path: Path) -> frozenset[str]:
    """Load a YAML properties-config file and return a frozenset of keys.

    The file is a YAML sequence of strings.  Each entry is either a bare type
    name (``"Address"``) or a ``Parent.field`` path
    (``"ChargingStation.address"``).  Only entries of those two forms are
    accepted; anything else raises ``ValueError``.

    Example file::

        - Address
        - Address.street
        - ChargingStation.address

    """
    raw = yaml.safe_load(config_path.read_text())
    if not isinstance(raw, list):
        raise ValueError(f"Properties config '{config_path}' must be a YAML sequence, got {type(raw).__name__}.")
    entries: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            raise ValueError(f"Properties config entries must be strings, got {type(item).__name__!r}: {item!r}")
        parts = item.split(".")
        if len(parts) not in (1, 2) or any(p == "" for p in parts):
            raise ValueError(
                f"Invalid properties-config entry {item!r}. " "Expected 'TypeName' or 'TypeName.fieldName'."
            )
        entries.add(item)
    return frozenset(entries)


def transform(
    graphql_schema: GraphQLSchema,
    additional_props_false: frozenset[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Return a bare BSON schema dict for every exportable type in the schema.

    Parameters
    ----------
    graphql_schema:
        The compiled GraphQL schema.
    additional_props_false:
        Keys for which ``additionalProperties: false`` should be emitted.
        See :class:`~.transformer.MongoDBTransformer` for the key format.
    """
    log.info(f"Transforming GraphQL schema to MongoDB BSON validators ({len(graphql_schema.type_map)} types)")
    result = MongoDBTransformer(graphql_schema, additional_props_false).transform()
    log.info(f"Generated {len(result)} MongoDB BSON schema(s)")
    return result


def translate_to_mongodb(
    annotated_schema: AnnotatedSchema,
    additional_props_false: frozenset[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Unwrap an ``AnnotatedSchema`` and delegate to :func:`transform`."""
    return transform(annotated_schema.schema, additional_props_false)


def wrap_validator(schema: dict[str, Any]) -> dict[str, Any]:
    """Wrap a bare BSON schema in the MongoDB collection validator envelope.

    Produces ``{"$jsonSchema": schema}`` for direct use with
    ``db.createCollection(name, {validator: {$jsonSchema: ...}})``.
    """
    return {"$jsonSchema": schema}


def to_json_string(schemas: dict[str, dict[str, Any]]) -> str:
    """Serialize the full validator map to a pretty-printed JSON string."""
    return json.dumps(schemas, indent=2)
