"""An in-memory embedder for tests that need vectors but no model."""

import hashlib
import re

import numpy as np

from s2dm.tools.embeddings.embedder import normalize
from s2dm.tools.embeddings.model import QUANTIZED_ONNX_FILE
from s2dm.tools.embeddings.model_spec import ModelSettings, ModelSpec
from s2dm.tools.embeddings.sources.huggingface_source import HuggingFaceReference

FAKE_EMBEDDER_DIM = 32
FAKE_MODEL_REFERENCE = HuggingFaceReference(repo="test/fake-model", revision="0")


def _count_words(text: str) -> np.ndarray:
    vector = np.zeros(FAKE_EMBEDDER_DIM, dtype=np.float32)
    lowercase_text = text.lower()
    words = re.findall(r"[a-z0-9]+", lowercase_text)
    for word in words:
        word_bytes = word.encode()
        digest = hashlib.md5(word_bytes).digest()
        vector[digest[0] % FAKE_EMBEDDER_DIM] += 1.0
    return vector


class FakeEmbedder:
    """Bag-of-words embedder: each lowercase word adds 1 to a hashed bucket, so shared words raise the score.

    Its spec names a Hugging Face source, so searching a file it built resolves a registered source.
    """

    spec = ModelSpec(
        source=FAKE_MODEL_REFERENCE.to_source_reference(),
        settings=ModelSettings(
            onnx_file=QUANTIZED_ONNX_FILE,
            pooling="mean",
            query_prompt="",
            document_prompt="",
            dim=FAKE_EMBEDDER_DIM,
        ),
    )

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        word_counts = [_count_words(text) for text in texts]
        text_count = len(texts)
        vectors = np.array(word_counts, dtype=np.float32).reshape(text_count, FAKE_EMBEDDER_DIM)
        return normalize(vectors)

    def embed_query(self, text: str) -> np.ndarray:
        vectors = self.embed_documents([text])
        query_vector: np.ndarray = vectors[0]
        return query_vector
