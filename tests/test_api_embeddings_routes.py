"""API tests for building and searching cached schema embeddings."""

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from s2dm.api.services import embeddings_service, schema_store
from s2dm.tools.embeddings import onnx_embedder as onnx_embedder_module
from s2dm.tools.embeddings.file import EmbeddingsFile
from s2dm.tools.embeddings.model_spec import ModelSpec
from tests.embeddings.fake_model import install_fake_model

VEHICLE_SCHEMA = """
type Vehicle {
  id: ID!
  cabin: Cabin
}

type Cabin {
  seat: String
}

type Query {
  vehicle: Vehicle
}
"""

CHANGED_VEHICLE_SCHEMA = """
type Vehicle {
  id: ID!
  cabin: Cabin
  speed: Float
}

type Cabin {
  seat: String
}

type Query {
  vehicle: Vehicle
}
"""

INVALID_ENUM_DEFAULT_SCHEMA = """
enum DriveMode { ECO SPORT }
input VehicleFilter { mode: DriveMode = COMFORT }
type Query { vehicle(filter: VehicleFilter): String }
"""

CABIN_FIELD_TEXT = "vehicle cabin (Cabin)"
UNKNOWN_EMBEDDINGS_ID = "0" * 64


def _schemas_payload(schema: str) -> dict[str, Any]:
    return {"schemas": [{"type": "content", "content": schema}]}


@pytest.fixture
def embedder_loads(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[ModelSpec]:
    def fake_api_workspace() -> Path:
        return tmp_path

    monkeypatch.setattr(embeddings_service, "get_api_workspace", fake_api_workspace)
    monkeypatch.setattr(schema_store, "get_api_workspace", fake_api_workspace)
    calls = install_fake_model(monkeypatch, [embeddings_service, onnx_embedder_module])
    return calls.embedder_loads


def _build(test_client: TestClient, schema: str) -> str:
    response = test_client.post("/api/v1/embeddings/build", json=_schemas_payload(schema))
    assert response.status_code == 200, response.text
    embeddings_id: str = response.json()["embeddings_id"]
    return embeddings_id


class TestEmbeddingsBuildRoute:
    """Test /api/v1/embeddings/build route behavior."""

    def test_build_returns_embeddings_id_and_writes_cache(
        self, test_client: TestClient, embedder_loads: list[ModelSpec], tmp_path: Path
    ) -> None:
        embeddings_id = _build(test_client, VEHICLE_SCHEMA)

        assert len(embeddings_id) == 64
        assert set(embeddings_id) <= set("0123456789abcdef")
        cache_path = tmp_path / "embeddings" / f"{embeddings_id}.json"
        embeddings = EmbeddingsFile.model_validate_json(cache_path.read_text())
        assert "Vehicle.cabin" in {element.id for element in embeddings.elements}

    def test_build_cache_hit_skips_embedding(self, test_client: TestClient, embedder_loads: list[ModelSpec]) -> None:
        first_id = _build(test_client, VEHICLE_SCHEMA)
        embedder_loads_after_first_build = len(embedder_loads)

        second_id = _build(test_client, VEHICLE_SCHEMA)

        assert second_id == first_id
        assert len(embedder_loads) == embedder_loads_after_first_build

    def test_build_schema_change_gets_new_id(
        self, test_client: TestClient, embedder_loads: list[ModelSpec], tmp_path: Path
    ) -> None:
        first_id = _build(test_client, VEHICLE_SCHEMA)

        second_id = _build(test_client, CHANGED_VEHICLE_SCHEMA)

        assert second_id != first_id
        assert {path.stem for path in (tmp_path / "embeddings").iterdir()} == {first_id, second_id}

    def test_build_from_schema_id_reuses_the_cache_of_its_text(
        self, test_client: TestClient, embedder_loads: list[ModelSpec]
    ) -> None:
        validate_response = test_client.post("/api/v1/schema/validate", json=_schemas_payload(VEHICLE_SCHEMA))
        validate_data = validate_response.json()
        composed_schema = validate_data["result"][0]
        schema_id = validate_data["schema_id"]
        reference_payload = {"schemas": [{"type": "schema_id", "id": schema_id}]}
        text_embeddings_id = _build(test_client, composed_schema)
        embedder_loads_after_first_build = len(embedder_loads)

        reference_response = test_client.post("/api/v1/embeddings/build", json=reference_payload)

        assert reference_response.status_code == 200, reference_response.text
        assert reference_response.json()["embeddings_id"] == text_embeddings_id
        assert len(embedder_loads) == embedder_loads_after_first_build

    def test_build_invalid_schema(self, test_client: TestClient, embedder_loads: list[ModelSpec]) -> None:
        response = test_client.post("/api/v1/embeddings/build", json=_schemas_payload(INVALID_ENUM_DEFAULT_SCHEMA))

        assert response.status_code == 422
        assert response.json()["error"] == "ValidationError"


class TestEmbeddingsSearchRoute:
    """Test /api/v1/embeddings/search route behavior."""

    def test_search_returns_ranked_hits(self, test_client: TestClient, embedder_loads: list[ModelSpec]) -> None:
        embeddings_id = _build(test_client, VEHICLE_SCHEMA)
        search_request = {"embeddings_id": embeddings_id, "query": CABIN_FIELD_TEXT, "limit": 3}

        response = test_client.post("/api/v1/embeddings/search", json=search_request)

        assert response.status_code == 200, response.text
        hits = response.json()
        assert [hit["rank"] for hit in hits] == [1, 2, 3]
        assert hits[0]["id"] == "Vehicle.cabin"
        assert all(set(hit) == {"rank", "score", "id"} for hit in hits)

    def test_search_unknown_id_returns_404(self, test_client: TestClient, embedder_loads: list[ModelSpec]) -> None:
        search_request = {"embeddings_id": UNKNOWN_EMBEDDINGS_ID, "query": "cabin", "limit": 3}

        response = test_client.post("/api/v1/embeddings/search", json=search_request)

        assert response.status_code == 404
        assert response.json()["error"] == "NotFound"

    @pytest.mark.parametrize(
        "search_request",
        [
            {"embeddings_id": "../x", "query": "cabin", "limit": 3},
            {"embeddings_id": UNKNOWN_EMBEDDINGS_ID, "query": "   ", "limit": 3},
            {"embeddings_id": UNKNOWN_EMBEDDINGS_ID, "query": "cabin", "limit": 0},
        ],
    )
    def test_search_rejects_invalid_requests(
        self, test_client: TestClient, embedder_loads: list[ModelSpec], search_request: dict[str, Any]
    ) -> None:
        response = test_client.post("/api/v1/embeddings/search", json=search_request)

        assert response.status_code == 400
        assert response.json()["error"] == "BadRequest"
