"""The embeddings file: schema elements with one stored vector each, plus the model that produced them."""

import base64
import binascii

import numpy as np
from graphql import GraphQLSchema
from pydantic import BaseModel

from s2dm.tools.embeddings.elements import ElementKind, SchemaElement, extract_elements
from s2dm.tools.embeddings.embedder import Embedder
from s2dm.tools.embeddings.errors import EmbeddingsFileError
from s2dm.tools.embeddings.model_spec import ModelSpec

FORMAT_VERSION = 1
STORED_VECTOR_DTYPE = "<f2"


class StoredElement(BaseModel):
    """An element as stored in the embeddings file.

    Lean files store only ``id``; verbose files also store ``kind`` and ``description``.
    """

    id: str
    kind: ElementKind | None = None
    description: str | None = None


class EmbeddingsFile(BaseModel):
    """Contents of ``embeddings.json``.

    ``vectors`` is base64 of little-endian float16 values, row-major, one row per entry of ``elements``.
    """

    format_version: int
    model: ModelSpec
    elements: list[StoredElement]
    vectors: str

    def to_json(self) -> str:
        """Serialize compactly, leaving out element fields a lean file does not store.

        Returns:
            The file's JSON text.
        """
        return self.model_dump_json(exclude_none=True)


def encode_vectors(matrix: np.ndarray) -> str:
    """Encode a vector table for storage.

    Args:
        matrix: Vectors, one row per element.

    Returns:
        Base64 of the table as little-endian float16, row-major.
    """
    stored_matrix = matrix.astype(STORED_VECTOR_DTYPE)
    raw_bytes = stored_matrix.tobytes()
    return base64.b64encode(raw_bytes).decode("ascii")


def decode_vectors(embeddings: EmbeddingsFile) -> np.ndarray:
    """Decode the stored vector table of an embeddings file.

    Args:
        embeddings: The embeddings file.

    Returns:
        The vectors as float32, shape ``(len(embeddings.elements), embeddings.model.settings.dim)``.

    Raises:
        EmbeddingsFileError: When the format version is unsupported or the stored vectors do not match
            the number of elements and the model's vector size.
    """
    if embeddings.format_version != FORMAT_VERSION:
        raise EmbeddingsFileError(f"Unsupported embeddings format version {embeddings.format_version}")

    try:
        raw_bytes = base64.b64decode(embeddings.vectors, validate=True)
    except binascii.Error as error:
        raise EmbeddingsFileError(f"Stored vectors are not valid base64: {error}") from error

    element_count = len(embeddings.elements)
    vector_size = embeddings.model.settings.dim
    expected_byte_count = element_count * vector_size * np.dtype(STORED_VECTOR_DTYPE).itemsize
    if len(raw_bytes) != expected_byte_count:
        raise EmbeddingsFileError(
            f"Stored vectors hold {len(raw_bytes)} bytes, expected {expected_byte_count} "
            f"for {element_count} elements of size {vector_size}"
        )

    stored_matrix = np.frombuffer(raw_bytes, dtype=STORED_VECTOR_DTYPE)
    return stored_matrix.astype(np.float32).reshape(element_count, vector_size)


def _stored_element(element: SchemaElement, verbose: bool) -> StoredElement:
    if not verbose:
        return StoredElement(id=element.id)

    return StoredElement(id=element.id, kind=element.kind, description=element.description)


def build_embeddings_file(schema: GraphQLSchema, embedder: Embedder, verbose: bool) -> EmbeddingsFile:
    """Embed every element of a schema.

    Args:
        schema: The composed GraphQL schema.
        embedder: The model to embed element texts with.
        verbose: Also store each element's kind and description, e.g. for inspecting search results.

    Returns:
        The embeddings file for the schema.
    """
    elements = extract_elements(schema)
    texts = [element.text for element in elements]
    vectors = embedder.embed_documents(texts)

    encoded_vectors = encode_vectors(vectors)
    stored_elements = [_stored_element(element, verbose) for element in elements]

    return EmbeddingsFile(
        format_version=FORMAT_VERSION,
        model=embedder.spec,
        elements=stored_elements,
        vectors=encoded_vectors,
    )
