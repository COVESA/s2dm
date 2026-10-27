import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from graphql import GraphQLSchema

from s2dm import cli as cli_module
from s2dm.cli import cli
from s2dm.tools.embeddings import onnx_embedder as onnx_embedder_module
from s2dm.tools.embeddings.errors import ModelResolutionError
from s2dm.tools.embeddings.file import EmbeddingsFile, build_embeddings_file
from s2dm.tools.embeddings.model import MODEL_CACHE_ROOT
from s2dm.tools.embeddings.model_spec import ModelSourceReference
from s2dm.tools.embeddings.sources.huggingface_source import DEFAULT_MODEL_REFERENCE, HuggingFaceReference
from s2dm.tools.embeddings.sources.source import ModelSource
from tests.embeddings.fake_embedder import FakeEmbedder
from tests.embeddings.fake_model import FakeLoadedModel, ModelLoad, install_fake_model

CLICK_USAGE_ERROR = 2


@pytest.fixture(scope="module")
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def model_loads(monkeypatch: pytest.MonkeyPatch) -> list[ModelLoad]:
    calls = install_fake_model(monkeypatch, [cli_module, onnx_embedder_module])
    return calls.model_loads


def _read_embeddings(embeddings_path: Path) -> EmbeddingsFile:
    embeddings_json = embeddings_path.read_text()
    return EmbeddingsFile.model_validate_json(embeddings_json)


def _write_embeddings(embeddings: EmbeddingsFile, embeddings_path: Path) -> None:
    embeddings_json = embeddings.to_json()
    embeddings_path.write_text(embeddings_json)


def test_embeddings_build_writes_valid_file(
    runner: CliRunner, embeddings_schema_path: Path, model_loads: list[ModelLoad], tmp_path: Path
) -> None:
    output_path = tmp_path / "out" / "embeddings.json"

    result = runner.invoke(cli, ["embeddings", "build", "-s", str(embeddings_schema_path), "-o", str(output_path)])

    assert result.exit_code == 0, result.output
    output_json = output_path.read_text()
    stored = json.loads(output_json)
    element_ids = {element["id"] for element in stored["elements"]}
    assert "Vehicle_Cabin_Door.isOpen" in element_ids
    assert all(set(element) == {"id"} for element in stored["elements"])
    default_reference = DEFAULT_MODEL_REFERENCE.to_source_reference()
    assert model_loads == [(default_reference, MODEL_CACHE_ROOT, False)]


def test_embeddings_build_verbose_stores_details(
    runner: CliRunner, embeddings_schema_path: Path, model_loads: list[ModelLoad], tmp_path: Path
) -> None:
    output_path = tmp_path / "embeddings.json"
    arguments = ["embeddings", "build", "-s", str(embeddings_schema_path), "-o", str(output_path)]

    result = runner.invoke(cli, [*arguments, "--verbose-embeddings"])

    assert result.exit_code == 0, result.output
    embeddings = _read_embeddings(output_path)
    elements_by_id = {element.id: element for element in embeddings.elements}
    is_open = elements_by_id["Vehicle_Cabin_Door.isOpen"]
    assert (is_open.kind, is_open.description) == ("field", "Is the door open or closed.")


def test_embeddings_build_passes_model_options(
    runner: CliRunner, embeddings_schema_path: Path, model_loads: list[ModelLoad], tmp_path: Path
) -> None:
    output_path = tmp_path / "embeddings.json"
    arguments = ["embeddings", "build", "-s", str(embeddings_schema_path), "-o", str(output_path)]
    model_options = ["--model", "org/other-model", "--revision", "rev1", "--full-size"]

    result = runner.invoke(cli, [*arguments, *model_options])

    assert result.exit_code == 0, result.output
    other_reference = HuggingFaceReference(repo="org/other-model", revision="rev1")
    expected_reference = other_reference.to_source_reference()
    assert model_loads == [(expected_reference, MODEL_CACHE_ROOT, True)]


def test_embeddings_build_requires_revision_with_model(
    runner: CliRunner, embeddings_schema_path: Path, model_loads: list[ModelLoad], tmp_path: Path
) -> None:
    output_path = tmp_path / "embeddings.json"
    arguments = ["embeddings", "build", "-s", str(embeddings_schema_path), "-o", str(output_path)]

    result = runner.invoke(cli, [*arguments, "--model", "org/other-model"])

    assert result.exit_code == CLICK_USAGE_ERROR
    assert model_loads == []


def test_embeddings_build_model_error_exits_nonzero(
    runner: CliRunner, embeddings_schema_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def failing_load_model(source: ModelSource, full_size: bool) -> FakeLoadedModel:
        raise ModelResolutionError("hub unreachable")

    monkeypatch.setattr(cli_module, "load_model", failing_load_model)
    output_path = tmp_path / "embeddings.json"

    result = runner.invoke(cli, ["embeddings", "build", "-s", str(embeddings_schema_path), "-o", str(output_path)])

    assert result.exit_code == 1
    assert not output_path.exists()


@pytest.fixture
def door_embeddings_path(embeddings_schema: GraphQLSchema, tmp_path: Path) -> Path:
    embeddings = build_embeddings_file(embeddings_schema, FakeEmbedder(), verbose=False)
    embeddings_path = tmp_path / "embeddings.json"
    _write_embeddings(embeddings, embeddings_path)
    return embeddings_path


def _parse_hits(output: str) -> list[dict[str, Any]]:
    json_start = output.index("[")
    hits_json = output[json_start:]
    hits: list[dict[str, Any]] = json.loads(hits_json)
    return hits


def test_search_semantic_outputs_ranked_hits(
    runner: CliRunner, door_embeddings_path: Path, model_loads: list[ModelLoad]
) -> None:
    query = "vehicle cabin door is open (Boolean): Is the door open or closed."

    result = runner.invoke(cli, ["search", "semantic", "-e", str(door_embeddings_path), "-q", query, "-l", "3"])

    assert result.exit_code == 0, result.output
    hits = _parse_hits(result.output)
    assert [hit["rank"] for hit in hits] == [1, 2, 3]
    assert hits[0]["id"] == "Vehicle_Cabin_Door.isOpen"
    assert set(hits[0]) == {"rank", "score", "id"}
    assert model_loads == [(FakeEmbedder.spec.source, MODEL_CACHE_ROOT, False)]


def test_search_semantic_rejects_blank_query(
    runner: CliRunner, door_embeddings_path: Path, model_loads: list[ModelLoad]
) -> None:
    result = runner.invoke(cli, ["search", "semantic", "-e", str(door_embeddings_path), "-q", "   "])

    assert result.exit_code == 1
    assert model_loads == []


def test_search_semantic_rejects_limit_below_one(
    runner: CliRunner, door_embeddings_path: Path, model_loads: list[ModelLoad]
) -> None:
    arguments = ["search", "semantic", "-e", str(door_embeddings_path), "-q", "door", "-l", "0"]

    result = runner.invoke(cli, arguments)

    assert result.exit_code == CLICK_USAGE_ERROR
    assert model_loads == []


def test_search_semantic_rejects_unreadable_file(
    runner: CliRunner, tmp_path: Path, model_loads: list[ModelLoad]
) -> None:
    embeddings_path = tmp_path / "broken.json"
    embeddings_path.write_text("not json")

    result = runner.invoke(cli, ["search", "semantic", "-e", str(embeddings_path), "-q", "door"])

    assert result.exit_code == 1


def test_search_semantic_rejects_unsupported_format_version(
    runner: CliRunner, door_embeddings_path: Path, model_loads: list[ModelLoad]
) -> None:
    embeddings = _read_embeddings(door_embeddings_path)
    future_embeddings = embeddings.model_copy(update={"format_version": embeddings.format_version + 1})
    _write_embeddings(future_embeddings, door_embeddings_path)

    result = runner.invoke(cli, ["search", "semantic", "-e", str(door_embeddings_path), "-q", "door"])

    assert result.exit_code == 1


def test_search_semantic_rejects_unregistered_source(
    runner: CliRunner, door_embeddings_path: Path, model_loads: list[ModelLoad]
) -> None:
    embeddings = _read_embeddings(door_embeddings_path)
    unknown_source = ModelSourceReference(kind="unknown")
    unknown_model = embeddings.model.model_copy(update={"source": unknown_source})
    unknown_source_embeddings = embeddings.model_copy(update={"model": unknown_model})
    _write_embeddings(unknown_source_embeddings, door_embeddings_path)

    result = runner.invoke(cli, ["search", "semantic", "-e", str(door_embeddings_path), "-q", "door"])

    assert result.exit_code == 1
    assert model_loads == []
