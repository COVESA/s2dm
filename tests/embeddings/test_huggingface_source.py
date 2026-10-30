import shutil
from http import HTTPStatus
from pathlib import Path
from typing import Any

import httpx
import pytest
from huggingface_hub.errors import HfHubHTTPError, RemoteEntryNotFoundError

from s2dm.tools.embeddings.errors import ModelResolutionError
from s2dm.tools.embeddings.model import FULL_SIZE_ONNX_FILE, QUANTIZED_ONNX_FILE, model_files
from s2dm.tools.embeddings.model_spec import ModelSourceReference
from s2dm.tools.embeddings.sentence_transformers.pooling import MODULES_FILE
from s2dm.tools.embeddings.sources import huggingface_source as huggingface_source_module
from s2dm.tools.embeddings.sources.huggingface_source import (
    HUGGING_FACE_KIND,
    HuggingFaceReference,
    HuggingFaceSource,
)
from tests.embeddings.tiny_model import write_model_dir

REPO = "org/tiny-model"
REVISION = "abc123"


def _hub_response(status: HTTPStatus) -> httpx.Response:
    request = httpx.Request("GET", f"https://huggingface.co/{REPO}")
    return httpx.Response(status, request=request)


def _download(source: HuggingFaceSource, onnx_file: str = QUANTIZED_ONNX_FILE) -> Path:
    files = model_files(onnx_file)
    return source.download(files)


class _FakeHub:
    """Serves files from a local model folder in place of the Hugging Face Hub, reporting absent files as missing."""

    def __init__(self, source: Path) -> None:
        self.source = source
        self.download_calls: list[dict[str, Any]] = []
        self.failures_by_filename: dict[str, Exception] = {}

    def hf_hub_download(self, repo_id: str, filename: str, revision: str, local_dir: Path) -> str:
        download_call = {"repo_id": repo_id, "filename": filename, "revision": revision, "local_dir": local_dir}
        self.download_calls.append(download_call)
        failure = self.failures_by_filename.get(filename)
        if failure is not None:
            raise failure
        source_path = self.source / filename
        if not source_path.is_file():
            not_found_response = _hub_response(HTTPStatus.NOT_FOUND)
            raise RemoteEntryNotFoundError(f"{filename} not found", response=not_found_response)
        target = Path(local_dir) / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, target)
        return str(target)


@pytest.fixture
def fake_hub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _FakeHub:
    source = tmp_path / "hub"
    write_model_dir(source)
    hub = _FakeHub(source)
    monkeypatch.setattr(huggingface_source_module, "hf_hub_download", hub.hf_hub_download)
    return hub


@pytest.fixture
def hub_source(tmp_path: Path) -> HuggingFaceSource:
    reference = HuggingFaceReference(repo=REPO, revision=REVISION)
    source_reference = reference.to_source_reference()
    return HuggingFaceSource(source_reference, tmp_path / "cache")


def test_rejects_reference_without_repo(tmp_path: Path) -> None:
    reference = ModelSourceReference.model_validate({"kind": HUGGING_FACE_KIND, "revision": REVISION})

    with pytest.raises(ModelResolutionError):
        HuggingFaceSource(reference, tmp_path)


def test_download_uses_local_dir(fake_hub: _FakeHub, hub_source: HuggingFaceSource) -> None:
    directory = _download(hub_source)

    assert directory == hub_source.cache_root / REPO / REVISION
    assert {call["local_dir"] for call in fake_hub.download_calls} == {directory}
    assert {call["revision"] for call in fake_hub.download_calls} == {REVISION}


def test_download_reuses_cached_files(fake_hub: _FakeHub, hub_source: HuggingFaceSource) -> None:
    _download(hub_source)
    first_download_count = len(fake_hub.download_calls)

    _download(hub_source)

    assert len(fake_hub.download_calls) == first_download_count


def test_download_fetches_required_files_last(fake_hub: _FakeHub, hub_source: HuggingFaceSource) -> None:
    files = model_files(QUANTIZED_ONNX_FILE)

    _download(hub_source)

    requested_filenames = [call["filename"] for call in fake_hub.download_calls]
    assert requested_filenames == [*files.optional, *files.required]


def test_download_skips_absent_optional_files(fake_hub: _FakeHub, hub_source: HuggingFaceSource) -> None:
    directory = _download(hub_source)

    requested_filenames = {call["filename"] for call in fake_hub.download_calls}
    assert MODULES_FILE in requested_filenames
    assert not (directory / MODULES_FILE).exists()


def test_download_rejects_repo_without_model_file(fake_hub: _FakeHub, hub_source: HuggingFaceSource) -> None:
    with pytest.raises(ModelResolutionError):
        _download(hub_source, FULL_SIZE_ONNX_FILE)


def test_download_rejects_failing_optional_file(fake_hub: _FakeHub, hub_source: HuggingFaceSource) -> None:
    server_error_response = _hub_response(HTTPStatus.INTERNAL_SERVER_ERROR)
    fake_hub.failures_by_filename[MODULES_FILE] = HfHubHTTPError("server error", response=server_error_response)

    with pytest.raises(ModelResolutionError):
        _download(hub_source)


def test_download_wraps_dropped_connection(fake_hub: _FakeHub, hub_source: HuggingFaceSource) -> None:
    fake_hub.failures_by_filename[QUANTIZED_ONNX_FILE] = httpx.ConnectError("connection dropped")

    with pytest.raises(ModelResolutionError):
        _download(hub_source)
