from pathlib import Path

import pytest

from s2dm.tools.embeddings.errors import ModelResolutionError
from s2dm.tools.embeddings.model import (
    FULL_SIZE_ONNX_FILE,
    QUANTIZED_ONNX_FILE,
    load_model,
    model_files,
    open_model,
)
from s2dm.tools.embeddings.model_spec import ModelSettings, ModelSourceReference, TokenPooling
from s2dm.tools.embeddings.sentence_transformers.pooling import MODULE_CONFIG_FILE, MODULES_FILE
from s2dm.tools.embeddings.sources.source import ModelFiles, ModelSource
from tests.embeddings.tiny_model import (
    HIDDEN_SIZE,
    LOCAL_MODEL_REFERENCE,
    PROMPT,
    SENTENCE_EMBEDDING_SIZE,
    write_model_dir,
)

CUSTOM_POOLING_PATH = "2_CustomPooling"


class _FolderSource(ModelSource):
    """Serves a local folder that already holds the model's files, recording which files were asked for."""

    def __init__(self, directory: Path) -> None:
        reference = ModelSourceReference.model_validate({"kind": "folder", "path": str(directory)})
        super().__init__(reference, directory)
        self.requested_files: list[ModelFiles] = []

    @classmethod
    def matches(cls, reference: ModelSourceReference) -> bool:
        return False

    def download(self, files: ModelFiles) -> Path:
        self.requested_files.append(files)
        return self.cache_root


def _open_settings(directory: Path, onnx_file: str = QUANTIZED_ONNX_FILE) -> ModelSettings:
    model = open_model(directory, onnx_file, LOCAL_MODEL_REFERENCE)
    return model.spec.settings


def test_open_model_prefers_sentence_embedding_output(tmp_path: Path) -> None:
    write_model_dir(tmp_path, pooling_mode="mean")

    settings = _open_settings(tmp_path)

    assert settings.pooling == "sentence_embedding"
    assert settings.dim == SENTENCE_EMBEDDING_SIZE


@pytest.mark.parametrize("pooling_mode", ["cls", "mean"])
def test_open_model_uses_pooling_config_when_no_sentence_embedding(tmp_path: Path, pooling_mode: TokenPooling) -> None:
    write_model_dir(tmp_path, with_sentence_embedding=False, pooling_mode=pooling_mode)

    settings = _open_settings(tmp_path)

    assert settings.pooling == pooling_mode
    assert settings.dim == HIDDEN_SIZE


def test_open_model_rejects_model_without_known_outputs(tmp_path: Path) -> None:
    unknown_output = "token_embeddings"
    write_model_dir(tmp_path, with_sentence_embedding=False, hidden_state_output=unknown_output, pooling_mode="mean")

    with pytest.raises(ModelResolutionError):
        _open_settings(tmp_path)


def test_open_model_rejects_listed_pooling_module_without_config(tmp_path: Path) -> None:
    write_model_dir(tmp_path, with_sentence_embedding=False, pooling_mode="mean", pooling_path=CUSTOM_POOLING_PATH)
    (tmp_path / CUSTOM_POOLING_PATH / MODULE_CONFIG_FILE).unlink()

    with pytest.raises(ModelResolutionError):
        _open_settings(tmp_path)


def test_open_model_rejects_pooling_config_without_mode(tmp_path: Path) -> None:
    write_model_dir(tmp_path, with_sentence_embedding=False, pooling_mode="mean", pooling_path=CUSTOM_POOLING_PATH)
    (tmp_path / CUSTOM_POOLING_PATH / MODULE_CONFIG_FILE).write_text("{}")

    with pytest.raises(ModelResolutionError):
        _open_settings(tmp_path)


def test_open_model_rejects_malformed_module_list(tmp_path: Path) -> None:
    write_model_dir(tmp_path, with_sentence_embedding=False, pooling_mode="mean")
    (tmp_path / MODULES_FILE).write_text('{"path": "1_Pooling"}')

    with pytest.raises(ModelResolutionError):
        _open_settings(tmp_path)


def test_open_model_missing_prompts_defaults_empty(tmp_path: Path) -> None:
    write_model_dir(tmp_path)

    settings = _open_settings(tmp_path)

    assert (settings.query_prompt, settings.document_prompt) == ("", "")


def test_open_model_rejects_missing_pooling(tmp_path: Path) -> None:
    write_model_dir(tmp_path, with_sentence_embedding=False)

    with pytest.raises(ModelResolutionError):
        _open_settings(tmp_path)


def test_open_model_rejects_missing_tokenizer(tmp_path: Path) -> None:
    write_model_dir(tmp_path, with_tokenizer=False)

    with pytest.raises(ModelResolutionError):
        _open_settings(tmp_path)


def test_open_model_rejects_missing_model_file(tmp_path: Path) -> None:
    write_model_dir(tmp_path)

    with pytest.raises(ModelResolutionError):
        _open_settings(tmp_path, FULL_SIZE_ONNX_FILE)


def test_load_model_records_source_and_settings(tmp_path: Path) -> None:
    write_model_dir(tmp_path, query_prompt=PROMPT)
    source = _FolderSource(tmp_path)

    model = load_model(source, False)

    assert model.spec.source == source.reference
    assert model.spec.settings.onnx_file == QUANTIZED_ONNX_FILE
    assert model.spec.settings.query_prompt == PROMPT


def test_load_model_requests_the_selected_model_files(tmp_path: Path) -> None:
    write_model_dir(tmp_path, onnx_file=FULL_SIZE_ONNX_FILE)
    source = _FolderSource(tmp_path)

    model = load_model(source, True)

    expected_files = model_files(FULL_SIZE_ONNX_FILE)
    assert source.requested_files == [expected_files]
    assert model.spec.settings.onnx_file == FULL_SIZE_ONNX_FILE


def test_load_model_downloads_the_listed_pooling_config(tmp_path: Path) -> None:
    write_model_dir(tmp_path, with_sentence_embedding=False, pooling_mode="mean", pooling_path=CUSTOM_POOLING_PATH)
    source = _FolderSource(tmp_path)

    model = load_model(source, False)

    base_files = model_files(QUANTIZED_ONNX_FILE)
    pooling_config_files = ModelFiles(required=[f"{CUSTOM_POOLING_PATH}/{MODULE_CONFIG_FILE}"])
    assert source.requested_files == [base_files, pooling_config_files]
    assert model.spec.settings.pooling == "mean"
