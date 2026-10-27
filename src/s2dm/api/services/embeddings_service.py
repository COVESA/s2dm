"""Build and search cached schema embeddings for the playground.

Embeddings files are cached on disk under the API workspace and never sent to the browser;
the playground searches them through the API.
"""

import functools
from pathlib import Path

import numpy as np
from graphql import GraphQLSchema, print_schema

from s2dm.api.config import get_api_workspace
from s2dm.api.errors import ResourceNotFoundError
from s2dm.api.models.base import SchemaInput
from s2dm.api.services.schema_service import load_validated_schema
from s2dm.tools.embeddings.embedder import Embedder
from s2dm.tools.embeddings.file import EmbeddingsFile, build_embeddings_file, decode_vectors
from s2dm.tools.embeddings.model import MODEL_CACHE_ROOT, QUANTIZED_ONNX_FILE, load_model
from s2dm.tools.embeddings.onnx_embedder import OnnxEmbedder, load_query_embedder
from s2dm.tools.embeddings.search import SearchHit, rank_table
from s2dm.tools.embeddings.sources.factory import ModelSourceFactory
from s2dm.tools.embeddings.sources.huggingface_source import DEFAULT_MODEL_REFERENCE
from s2dm.utils.file import write_text_atomically
from s2dm.utils.hashing import sha256_hex
from s2dm.utils.pydantic_file import read_json_model

EMBEDDINGS_CACHE_DIRECTORY = "embeddings"
MODEL_SOURCE_REFERENCE = DEFAULT_MODEL_REFERENCE.to_source_reference()


def _load_schema(schemas: list[SchemaInput]) -> GraphQLSchema:
    annotated_schema, _ = load_validated_schema(
        schemas=schemas,
        naming_config_input=None,
        selection_query_input=None,
        root_type=None,
        expanded_instances=False,
    )
    return annotated_schema.schema


def _embeddings_id(schema_id: str) -> str:
    """Hash the schema id together with the model, so a change to either gives a new id."""
    source_key = MODEL_SOURCE_REFERENCE.model_dump_json()
    model_key = f"{source_key}/{QUANTIZED_ONNX_FILE}"
    embeddings_key = f"{model_key}\n{schema_id}"
    return sha256_hex(embeddings_key)


def _cache_path(embeddings_id: str) -> Path:
    return get_api_workspace() / EMBEDDINGS_CACHE_DIRECTORY / f"{embeddings_id}.json"


def build_schema_embeddings(schemas: list[SchemaInput]) -> str:
    """Make sure the embeddings of a schema are cached, building them if needed.

    Args:
        schemas: The schema inputs to compose.

    Returns:
        The embeddings id, used to search the cached embeddings.
    """
    schema = _load_schema(schemas)
    schema_sdl = print_schema(schema)
    schema_id = sha256_hex(schema_sdl)

    embeddings_id = _embeddings_id(schema_id)
    cache_path = _cache_path(embeddings_id)
    if cache_path.is_file():
        return embeddings_id

    source = ModelSourceFactory.create_source(MODEL_SOURCE_REFERENCE, MODEL_CACHE_ROOT)
    model = load_model(source, False)
    embedder = OnnxEmbedder(model)
    embeddings_file = build_embeddings_file(schema, embedder, verbose=False)
    # TODO: add a cleanup policy for cached embeddings files
    write_text_atomically(cache_path, embeddings_file.to_json())
    return embeddings_id


@functools.lru_cache(maxsize=1)
def _load_search_resources(cache_path: Path) -> tuple[EmbeddingsFile, np.ndarray, Embedder]:
    """Load, decode, and keep the most recently searched embeddings file with its model."""
    embeddings_file = read_json_model(cache_path, EmbeddingsFile)
    table = decode_vectors(embeddings_file)
    embedder = load_query_embedder(embeddings_file)
    return embeddings_file, table, embedder


def search_schema_embeddings(embeddings_id: str, query: str, limit: int) -> list[SearchHit]:
    """Search the cached embeddings of a schema.

    Args:
        embeddings_id: Id returned by :func:`build_schema_embeddings`.
        query: Free-text search query.
        limit: Maximum number of results.

    Returns:
        Up to ``limit`` hits, best first.

    Raises:
        ResourceNotFoundError: When no embeddings are cached under the id.
    """
    cache_path = _cache_path(embeddings_id)
    if not cache_path.is_file():
        raise ResourceNotFoundError(f"No embeddings cached under id '{embeddings_id}'")
    embeddings_file, table, embedder = _load_search_resources(cache_path)
    query_vector = embedder.embed_query(query)
    return rank_table(embeddings_file.elements, table, query_vector, limit)
