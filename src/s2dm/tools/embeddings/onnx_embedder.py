"""Embed texts with an ONNX model opened by :mod:`s2dm.tools.embeddings.model`."""

import numpy as np
from tokenizers import Encoding

from s2dm.tools.embeddings.embedder import Embedder, normalize
from s2dm.tools.embeddings.errors import EmbeddingsFileError
from s2dm.tools.embeddings.file import EmbeddingsFile
from s2dm.tools.embeddings.model import FULL_SIZE_ONNX_FILE, MODEL_CACHE_ROOT, LoadedModel, load_model
from s2dm.tools.embeddings.sources.factory import ModelSourceFactory

BATCH_SIZE = 64


class OnnxEmbedder:
    """Runs an ONNX sentence-embedding model with its Hugging Face tokenizer."""

    def __init__(self, model: LoadedModel) -> None:
        self.spec = model.spec
        self._session = model.session
        self._tokenizer = model.tokenizer

        model_inputs = self._session.get_inputs()
        self._input_names = {model_input.name for model_input in model_inputs}

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        prompted_texts = [self.spec.settings.document_prompt + text for text in texts]
        return self._embed(prompted_texts)

    def embed_query(self, text: str) -> np.ndarray:
        vectors = self._embed([self.spec.settings.query_prompt + text])
        query_vector: np.ndarray = vectors[0]
        return query_vector

    def _embed(self, texts: list[str]) -> np.ndarray:
        """Embed texts in length-sorted batches, so each batch pads to similar lengths, and keep input order."""
        vectors = np.zeros((len(texts), self.spec.settings.dim), dtype=np.float32)
        order_by_length = sorted(range(len(texts)), key=lambda index: len(texts[index]))

        for start in range(0, len(order_by_length), BATCH_SIZE):
            batch_indices = order_by_length[start : start + BATCH_SIZE]
            batch_texts = [texts[index] for index in batch_indices]
            vectors[batch_indices] = self._embed_batch(batch_texts)

        return normalize(vectors)

    def _model_inputs(self, encodings: list[Encoding]) -> dict[str, np.ndarray]:
        model_inputs = {
            "input_ids": np.array([encoding.ids for encoding in encodings], dtype=np.int64),
            "attention_mask": np.array([encoding.attention_mask for encoding in encodings], dtype=np.int64),
        }
        if "token_type_ids" in self._input_names:
            model_inputs["token_type_ids"] = np.array([encoding.type_ids for encoding in encodings], dtype=np.int64)

        return model_inputs

    def _embed_batch(self, texts: list[str]) -> np.ndarray:
        encodings = self._tokenizer.encode_batch(texts)
        model_inputs = self._model_inputs(encodings)
        pooling = self.spec.settings.pooling

        if pooling == "sentence_embedding":
            outputs = self._session.run(["sentence_embedding"], model_inputs)
            return np.asarray(outputs[0])

        outputs = self._session.run(["last_hidden_state"], model_inputs)
        hidden_states = np.asarray(outputs[0])
        if pooling == "cls":
            return hidden_states[:, 0, :]

        attention_mask = model_inputs["attention_mask"][:, :, np.newaxis].astype(np.float32)
        token_counts = np.clip(attention_mask.sum(axis=1), 1e-9, None)
        return (hidden_states * attention_mask).sum(axis=1) / token_counts


def load_query_embedder(embeddings: EmbeddingsFile) -> Embedder:
    """Load the model that built an embeddings file, for embedding queries to search it.

    Args:
        embeddings: The embeddings file to search.

    Returns:
        An embedder for the model recorded in the file.

    Raises:
        ModelResolutionError: When no registered source serves the recorded model, or it cannot be downloaded
            or is no longer usable.
        EmbeddingsFileError: When the recorded model now resolves to settings other than the file's.
    """
    stored_model = embeddings.model
    full_size = stored_model.settings.onnx_file == FULL_SIZE_ONNX_FILE
    source = ModelSourceFactory.create_source(stored_model.source, MODEL_CACHE_ROOT)
    model = load_model(source, full_size)

    if model.spec != stored_model:
        raise EmbeddingsFileError("The file's model now resolves to settings other than the file's")

    return OnnxEmbedder(model)
