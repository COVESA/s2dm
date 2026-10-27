"""Rank schema elements against a query vector by cosine similarity."""

import numpy as np
from pydantic import BaseModel

from s2dm.tools.embeddings.elements import ElementKind
from s2dm.tools.embeddings.errors import EmbeddingsFileError
from s2dm.tools.embeddings.file import EmbeddingsFile, StoredElement, decode_vectors


class SearchHit(BaseModel):
    """One ranked search result; ``kind`` and ``description`` are set only for verbose embeddings files."""

    rank: int
    score: float
    id: str
    kind: ElementKind | None
    description: str | None


def rank_table(
    elements: list[StoredElement], table: np.ndarray, query_vector: np.ndarray, limit: int
) -> list[SearchHit]:
    """Rank already-decoded vectors by cosine similarity to the query and keep the best ``limit``.

    Stored and query vectors are normalized, so cosine similarity is their dot product.

    Args:
        elements: The stored elements, one per row of ``table``.
        table: The decoded vectors, shape ``(len(elements), dim)``.
        query_vector: The normalized query vector, embedded with the same model as ``table``.
        limit: Maximum number of results.

    Returns:
        Up to ``limit`` hits, best first; ties keep element order.

    Raises:
        EmbeddingsFileError: When the query vector's size differs from the table's vectors.
    """
    vector_size = table.shape[1]
    if query_vector.shape != (vector_size,):
        raise EmbeddingsFileError(f"Query vector has shape {query_vector.shape}, expected ({vector_size},)")

    scores = table @ query_vector
    negated_scores = -scores
    best_indices = np.argsort(negated_scores, kind="stable")[:limit]

    hits: list[SearchHit] = []
    for position, element_index in enumerate(best_indices):
        element = elements[element_index]
        score = float(scores[element_index])
        hit = SearchHit(
            rank=position + 1, score=score, id=element.id, kind=element.kind, description=element.description
        )
        hits.append(hit)

    return hits


def rank_elements(embeddings: EmbeddingsFile, query_vector: np.ndarray, limit: int) -> list[SearchHit]:
    """Decode an embeddings file and rank its elements against the query.

    Args:
        embeddings: The embeddings file to search.
        query_vector: The normalized query vector, embedded with the file's model.
        limit: Maximum number of results.

    Returns:
        Up to ``limit`` hits, best first; ties keep element order.

    Raises:
        EmbeddingsFileError: When the file cannot be decoded or the query vector's size differs from its vectors.
    """
    table = decode_vectors(embeddings)
    return rank_table(embeddings.elements, table, query_vector, limit)
