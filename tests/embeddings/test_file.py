import base64
import json

import numpy as np
import pytest
from graphql import GraphQLSchema

from s2dm.tools.embeddings.elements import extract_elements
from s2dm.tools.embeddings.errors import EmbeddingsFileError
from s2dm.tools.embeddings.file import FORMAT_VERSION, EmbeddingsFile, decode_vectors
from tests.embeddings.fake_embedder import FakeEmbedder

FLOAT16_TOLERANCE = 1e-3
FLOAT16_BYTES = 2


def test_build_file_rows_align_with_elements(embeddings_schema: GraphQLSchema, lean_embeddings: EmbeddingsFile) -> None:
    schema_elements = extract_elements(embeddings_schema)
    texts = [element.text for element in schema_elements]
    expected_vectors = FakeEmbedder().embed_documents(texts)

    vectors = decode_vectors(lean_embeddings)

    assert [element.id for element in lean_embeddings.elements] == [element.id for element in schema_elements]
    assert np.allclose(vectors, expected_vectors, atol=FLOAT16_TOLERANCE)
    stored_bytes = base64.b64decode(lean_embeddings.vectors)
    assert len(stored_bytes) == vectors.size * FLOAT16_BYTES
    assert lean_embeddings.model == FakeEmbedder.spec


def test_lean_file_stores_ids_only(lean_embeddings: EmbeddingsFile) -> None:
    stored = json.loads(lean_embeddings.to_json())

    assert all(set(element) == {"id"} for element in stored["elements"])


def test_verbose_file_stores_kind_and_description(
    embeddings_schema: GraphQLSchema, verbose_embeddings: EmbeddingsFile
) -> None:
    schema_elements = extract_elements(embeddings_schema)

    stored_details = [(element.id, element.kind, element.description) for element in verbose_embeddings.elements]
    expected_details = [(element.id, element.kind, element.description) for element in schema_elements]
    assert stored_details == expected_details


def test_decode_rejects_wrong_format_version(lean_embeddings: EmbeddingsFile) -> None:
    future_file = lean_embeddings.model_copy(update={"format_version": FORMAT_VERSION + 1})

    with pytest.raises(EmbeddingsFileError):
        decode_vectors(future_file)


def test_decode_rejects_wrong_byte_length(lean_embeddings: EmbeddingsFile) -> None:
    truncated_file = lean_embeddings.model_copy(update={"elements": lean_embeddings.elements[:-1]})

    with pytest.raises(EmbeddingsFileError):
        decode_vectors(truncated_file)


def test_decode_rejects_invalid_base64(lean_embeddings: EmbeddingsFile) -> None:
    corrupted_file = lean_embeddings.model_copy(update={"vectors": "not base64!"})

    with pytest.raises(EmbeddingsFileError):
        decode_vectors(corrupted_file)
