"""Tests for stored composed schemas and the schema reference inputs that point to them."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from graphql import print_schema

from s2dm.api.models.base import ContentInput, DependencyInput, SchemaIdInput
from s2dm.api.services import schema_service, schema_store
from s2dm.deps.resolve.common import SCHEMA_FILENAME, VENDOR_DIRECTORY

VEHICLE_SCHEMA = """
directive @range(min: Float, max: Float) on FIELD_DEFINITION

type Query {
  vehicle: Vehicle
}

\"\"\"A vehicle.\"\"\"
type Vehicle {
  speed: Float @range(min: 0, max: 250)
  cabin: Cabin
}

type Cabin {
  doorCount: Int
  temperatureUnit: TemperatureUnit
}

enum TemperatureUnit {
  CELSIUS
  FAHRENHEIT
}
"""

UNKNOWN_SCHEMA_ID = "0" * 64


@pytest.fixture(autouse=True)
def api_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(schema_store, "get_api_workspace", lambda: tmp_path)
    return tmp_path


def _validate(test_client: TestClient, schema: str) -> tuple[str, str]:
    response = test_client.post(
        "/api/v1/schema/validate",
        json={"schemas": [{"type": "content", "content": schema}]},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    composed_schema: str = data["result"][0]
    schema_id: str = data["schema_id"]
    return composed_schema, schema_id


def _write_vendored_schema(api_workspace: Path, name: str, version: str, schema: str) -> None:
    schema_path = api_workspace / VENDOR_DIRECTORY / name / version / SCHEMA_FILENAME
    schema_path.parent.mkdir(parents=True)
    schema_path.write_text(schema)


class TestSchemaStore:
    def test_validate_stores_the_composed_schema_under_its_id(
        self, test_client: TestClient, api_workspace: Path
    ) -> None:
        composed_schema, schema_id = _validate(test_client, VEHICLE_SCHEMA)

        assert schema_id == schema_store.schema_text_id(composed_schema)
        stored_path = api_workspace / schema_store.SCHEMA_STORE_DIRECTORY / f"{schema_id}.graphql"
        assert stored_path.read_text() == composed_schema

    def test_validating_the_same_schema_again_returns_the_same_id(self, test_client: TestClient) -> None:
        _, first_schema_id = _validate(test_client, VEHICLE_SCHEMA)
        _, second_schema_id = _validate(test_client, VEHICLE_SCHEMA)

        assert second_schema_id == first_schema_id


class TestSchemaReferenceLoading:
    def test_schema_id_loads_the_same_schema_as_the_composed_text(self, test_client: TestClient) -> None:
        composed_schema, schema_id = _validate(test_client, VEHICLE_SCHEMA)

        from_text, _ = schema_service.load_validated_schema(
            [ContentInput(type="content", content=composed_schema)], None, None, None, False
        )
        from_reference, _ = schema_service.load_validated_schema(
            [SchemaIdInput(type="schema_id", id=schema_id)], None, None, None, False
        )

        assert print_schema(from_reference.schema) == print_schema(from_text.schema)
        assert from_reference.type_metadata.keys() == from_text.type_metadata.keys()
        assert from_reference.field_metadata.keys() == from_text.field_metadata.keys()

    def test_dependency_loads_its_vendored_schema(self, api_workspace: Path) -> None:
        _write_vendored_schema(api_workspace, "vehicle-model", "1.0.0", VEHICLE_SCHEMA)

        annotated_schema, _ = schema_service.load_validated_schema(
            [DependencyInput(type="dependency", name="vehicle-model", version="1.0.0")], None, None, None, False
        )

        assert "Cabin" in annotated_schema.schema.type_map


class TestSchemaReferenceErrors:
    def test_unknown_schema_id_returns_404(self, test_client: TestClient) -> None:
        response = test_client.post(
            "/api/v1/insights/concepts",
            json={"schemas": [{"type": "schema_id", "id": UNKNOWN_SCHEMA_ID}]},
        )

        assert response.status_code == 404

    def test_unknown_dependency_returns_404(self, test_client: TestClient) -> None:
        response = test_client.post(
            "/api/v1/insights/concepts",
            json={"schemas": [{"type": "dependency", "name": "missing", "version": "1.0.0"}]},
        )

        assert response.status_code == 404

    def test_dependency_outside_the_vendor_directory_returns_404(
        self, test_client: TestClient, api_workspace: Path
    ) -> None:
        outside_path = api_workspace / SCHEMA_FILENAME
        outside_path.write_text(VEHICLE_SCHEMA)

        response = test_client.post(
            "/api/v1/insights/concepts",
            json={"schemas": [{"type": "dependency", "name": "../..", "version": "."}]},
        )

        assert response.status_code == 404

    def test_malformed_schema_id_returns_400(self, test_client: TestClient) -> None:
        response = test_client.post(
            "/api/v1/insights/concepts",
            json={"schemas": [{"type": "schema_id", "id": "not-a-hash"}]},
        )

        assert response.status_code == 400
