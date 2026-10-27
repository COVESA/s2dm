"""The embedder interface: what turns texts into vectors, without depending on any model runtime."""

from typing import Protocol

import numpy as np

from s2dm.tools.embeddings.model_spec import ModelSpec


class Embedder(Protocol):
    """Turns texts into L2-normalized float32 vectors of size ``spec.settings.dim``."""

    spec: ModelSpec

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        """Embed searchable texts, prefixed with the model's document prompt.

        Args:
            texts: Texts to embed.

        Returns:
            One normalized vector per text, shape ``(len(texts), spec.settings.dim)``.
        """
        ...

    def embed_query(self, text: str) -> np.ndarray:
        """Embed a search query, prefixed with the model's query prompt.

        Args:
            text: The query.

        Returns:
            One normalized vector, shape ``(spec.settings.dim,)``.
        """
        ...


def normalize(vectors: np.ndarray) -> np.ndarray:
    """Scale each vector to length 1, as the ``Embedder`` contract requires.

    Args:
        vectors: Vectors, one per row.

    Returns:
        The vectors divided by their L2 norms; all-zero rows stay zero.
    """
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    safe_norms = np.clip(norms, 1e-12, None)
    normalized_vectors: np.ndarray = vectors / safe_norms
    return normalized_vectors
