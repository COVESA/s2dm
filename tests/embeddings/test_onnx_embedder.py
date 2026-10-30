import os
from pathlib import Path

import numpy as np
import pytest

from s2dm.tools.embeddings import onnx_embedder as onnx_embedder_module
from s2dm.tools.embeddings.errors import EmbeddingsFileError
from s2dm.tools.embeddings.file import FORMAT_VERSION, EmbeddingsFile
from s2dm.tools.embeddings.model import MODEL_CACHE_ROOT, QUANTIZED_ONNX_FILE, load_model, open_model
from s2dm.tools.embeddings.model_spec import ModelSpec, TokenPooling
from s2dm.tools.embeddings.onnx_embedder import OnnxEmbedder, load_query_embedder
from s2dm.tools.embeddings.sources.huggingface_source import (
    DEFAULT_MODEL_REPO,
    DEFAULT_MODEL_REVISION,
    HuggingFaceReference,
    HuggingFaceSource,
)
from tests.embeddings.tiny_model import LOCAL_MODEL_REFERENCE, PROMPT, write_model_dir

CACHED_MODEL_REFERENCE = HuggingFaceReference(repo="test/tiny-model", revision="0")


def _load_local_embedder(directory: Path) -> OnnxEmbedder:
    model = open_model(directory, QUANTIZED_ONNX_FILE, LOCAL_MODEL_REFERENCE)
    return OnnxEmbedder(model)


def _embeddings_file(model_spec: ModelSpec) -> EmbeddingsFile:
    return EmbeddingsFile(format_version=FORMAT_VERSION, model=model_spec, elements=[], vectors="")


@pytest.fixture
def cached_model_spec(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModelSpec:
    """Put the tiny model where the Hugging Face source finds it already cached, and return its spec."""
    monkeypatch.setattr(onnx_embedder_module, "MODEL_CACHE_ROOT", tmp_path)
    model_directory = tmp_path / CACHED_MODEL_REFERENCE.repo / CACHED_MODEL_REFERENCE.revision
    write_model_dir(model_directory)
    source_reference = CACHED_MODEL_REFERENCE.to_source_reference()
    model = open_model(model_directory, QUANTIZED_ONNX_FILE, source_reference)
    return model.spec


def test_embed_documents_normalized(tmp_path: Path) -> None:
    write_model_dir(tmp_path)
    embedder = _load_local_embedder(tmp_path)

    vectors = embedder.embed_documents(["door open", "tire pressure", "a b c"])

    assert vectors.shape == (3, embedder.spec.settings.dim)
    assert vectors.dtype == np.float32
    norms = np.linalg.norm(vectors, axis=1)
    assert np.allclose(norms, 1.0)


def test_embed_query_applies_query_prompt(tmp_path: Path) -> None:
    write_model_dir(tmp_path, query_prompt=PROMPT)
    embedder = _load_local_embedder(tmp_path)

    query_vector = embedder.embed_query("x")
    prompted_document_vectors = embedder.embed_documents([f"{PROMPT}x"])

    assert np.allclose(query_vector, prompted_document_vectors[0])


def test_embed_documents_applies_document_prompt(tmp_path: Path) -> None:
    write_model_dir(tmp_path, document_prompt=PROMPT)
    embedder = _load_local_embedder(tmp_path)

    document_vectors = embedder.embed_documents(["x"])
    prompted_query_vector = embedder.embed_query(f"{PROMPT}x")

    assert np.allclose(document_vectors[0], prompted_query_vector)


@pytest.mark.parametrize("pooling_mode", ["cls", "mean"])
def test_pooling_ignores_padding(tmp_path: Path, pooling_mode: TokenPooling) -> None:
    write_model_dir(tmp_path, with_sentence_embedding=False, pooling_mode=pooling_mode)
    embedder = _load_local_embedder(tmp_path)

    alone = embedder.embed_documents(["a"])
    batched = embedder.embed_documents(["a", "door open tire pressure a b c"])

    assert np.allclose(alone[0], batched[0], atol=1e-5)


def test_embed_documents_keeps_input_order(tmp_path: Path) -> None:
    write_model_dir(tmp_path, with_sentence_embedding=False, pooling_mode="mean")
    embedder = _load_local_embedder(tmp_path)
    texts = ["door open tire pressure", "a", "b c"]

    batched = embedder.embed_documents(texts)
    one_by_one = np.vstack([embedder.embed_documents([text]) for text in texts])

    assert np.allclose(batched, one_by_one, atol=1e-5)


def test_load_query_embedder_loads_the_file_model(cached_model_spec: ModelSpec) -> None:
    embeddings = _embeddings_file(cached_model_spec)

    embedder = load_query_embedder(embeddings)

    assert embedder.spec == cached_model_spec


def test_load_query_embedder_rejects_changed_model(cached_model_spec: ModelSpec) -> None:
    stored_settings = cached_model_spec.settings
    other_settings = stored_settings.model_copy(update={"dim": stored_settings.dim + 1})
    other_spec = cached_model_spec.model_copy(update={"settings": other_settings})
    embeddings = _embeddings_file(other_spec)

    with pytest.raises(EmbeddingsFileError):
        load_query_embedder(embeddings)


@pytest.mark.skipif(os.environ.get("S2DM_RUN_MODEL_TESTS") != "1", reason="downloads the real model")
def test_real_model_ranks_paraphrase() -> None:
    reference = HuggingFaceReference(repo=DEFAULT_MODEL_REPO, revision=DEFAULT_MODEL_REVISION)
    source_reference = reference.to_source_reference()
    source = HuggingFaceSource(source_reference, MODEL_CACHE_ROOT)
    model = load_model(source, False)
    embedder = OnnxEmbedder(model)
    documents = [
        "vehicle cabin door driver is open (Boolean): Driver-side door status (open or closed).",
        "vehicle chassis axle row1 wheel left tire pressure (Float): Tire pressure in kilo-Pascal.",
    ]

    document_vectors = embedder.embed_documents(documents)
    query_vector = embedder.embed_query("is the driver's door ajar")
    scores = document_vectors @ query_vector

    assert scores[0] > scores[1]
