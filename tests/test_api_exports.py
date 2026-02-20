"""API export endpoint tests."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient


class TestExporters:
    """Test exporters endpoints."""

    def test_avro_schema_basic_export(self, test_client: TestClient) -> None:
        """Export Avro schema with inline content."""
        simple_schema = """
        type Query {
            vehicle: Vehicle
        }

        type Vehicle {
            id: ID!
            speed: Float
        }
        """
        simple_query = "query Selection { vehicle { id speed } }"

        response = test_client.post(
            "/api/v1/export/avro/schema",
            json={
                "schemas": [{"type": "content", "content": simple_schema}],
                "selection_query": {"type": "content", "content": simple_query},
                "namespace": "com.example.test",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert len(data["result"]) == 1
        assert data["metadata"]["result_format"] == "avsc"

        avro_schema = json.loads(data["result"][0])
        assert avro_schema["namespace"] == "com.example.test"
        assert avro_schema["type"] == "record"

    def test_avro_schema_response_metadata(self, test_client: TestClient) -> None:
        """Response includes correct metadata."""
        simple_schema = "type Query { vehicle: Vehicle } type Vehicle { id: ID! }"
        simple_query = "query Selection { vehicle { id } }"

        response = test_client.post(
            "/api/v1/export/avro/schema",
            json={
                "schemas": [{"type": "content", "content": simple_schema}],
                "selection_query": {"type": "content", "content": simple_query},
                "namespace": "com.example.test",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "metadata" in data
        assert data["metadata"]["result_format"] == "avsc"
        assert "processing_time_ms" in data["metadata"]
        assert isinstance(data["metadata"]["processing_time_ms"], int)
        assert data["metadata"]["processing_time_ms"] >= 0

    def test_avro_protocol_export(self, test_client: TestClient) -> None:
        """Export Avro protocol (IDL)."""
        simple_schema = "type Query { vehicle: Vehicle } type Vehicle { id: ID! speed: Float }"

        response = test_client.post(
            "/api/v1/export/avro/protocol",
            json={
                "schemas": [{"type": "content", "content": simple_schema}],
                "namespace": "com.example.test",
                "strict": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert data["metadata"]["result_format"] == "avdl"

    def test_jsonschema_export(self, test_client: TestClient) -> None:
        """Export to JSON Schema."""
        simple_schema = "type Query { vehicle: Vehicle } type Vehicle { id: ID! }"

        response = test_client.post(
            "/api/v1/export/jsonschema",
            json={
                "schemas": [{"type": "content", "content": simple_schema}],
                "strict": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["result_format"] == "json"

    def test_protobuf_export(self, test_client: TestClient) -> None:
        """Export to Protocol Buffers."""
        simple_schema = "type Query { vehicle: Vehicle } type Vehicle { id: ID! }"
        simple_query = "query Selection { vehicle { id } }"

        response = test_client.post(
            "/api/v1/export/protobuf",
            json={
                "schemas": [{"type": "content", "content": simple_schema}],
                "selection_query": {"type": "content", "content": simple_query},
                "namespace": "com.example.test",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["result_format"] == "proto"

    def test_shacl_export(self, test_client: TestClient) -> None:
        """Export to SHACL format."""
        simple_schema = "type Query { vehicle: Vehicle } type Vehicle { id: ID! }"

        response = test_client.post(
            "/api/v1/export/shacl",
            json={
                "schemas": [{"type": "content", "content": simple_schema}],
                "serialization_format": "ttl",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["result_format"] == "ttl"

    def test_vspec_export(self, test_client: TestClient) -> None:
        """Export to VSS format."""
        simple_schema = "type Query { vehicle: Vehicle } type Vehicle { id: ID! }"

        response = test_client.post(
            "/api/v1/export/vspec",
            json={
                "schemas": [{"type": "content", "content": simple_schema}],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["result_format"] == "vspec"

    def test_export_accepts_url_schema_input(self, test_client: TestClient, tmp_path: Path) -> None:
        """Export route accepts URL schema input and processes it."""
        schema_file = tmp_path / "schema.graphql"
        schema_file.write_text(
            "type Query { vehicle: Vehicle } type Vehicle { id: ID! speed: Float }",
            encoding="utf-8",
        )
        simple_query = "query Selection { vehicle { id speed } }"

        with patch("s2dm.api.services.schema_service.download_schema_to_temp", return_value=schema_file) as downloader:
            response = test_client.post(
                "/api/v1/export/avro/schema",
                json={
                    "schemas": [{"type": "url", "url": "https://example.com/schema.graphql"}],
                    "selection_query": {"type": "content", "content": simple_query},
                    "namespace": "com.example.test",
                },
            )

        assert response.status_code == 200
        downloader.assert_called_once_with("https://example.com/schema.graphql")


class TestExportersInternalFunctionsCalled:
    """Test successful route wiring to internal collaborators."""

    def test_avro_schema_route_calls_internal_functions(self, test_client: TestClient) -> None:
        """Avro schema route calls wrapper, schema check, and exporter."""
        payload = {
            "schemas": [{"type": "content", "content": "type Query { vehicle: Vehicle } type Vehicle { id: ID! }"}],
            "selection_query": {"type": "content", "content": "query Selection { vehicle { id } }"},
            "namespace": "com.example.test",
        }

        with (
            patch(
                "s2dm.api.routes.avro.load_and_process_schema_wrapper",
                return_value=(SimpleNamespace(schema=object()), object()),
            ) as wrapper_mock,
            patch("s2dm.api.routes.avro.check_correct_schema", return_value=[]) as schema_check_mock,
            patch("s2dm.api.routes.avro.translate_to_avro_schema", return_value='{"type":"record"}') as exporter_mock,
        ):
            response = test_client.post("/api/v1/export/avro/schema", json=payload)

        assert response.status_code == 200
        assert response.json()["metadata"]["result_format"] == "avsc"
        wrapper_mock.assert_called_once()
        schema_check_mock.assert_called_once()
        exporter_mock.assert_called_once()

    def test_avro_protocol_route_calls_internal_functions(self, test_client: TestClient) -> None:
        """Avro protocol route calls wrapper, schema check, and exporter."""
        payload = {
            "schemas": [{"type": "content", "content": "type Query { vehicle: Vehicle } type Vehicle { id: ID! }"}],
            "namespace": "com.example.test",
            "strict": True,
        }

        with (
            patch(
                "s2dm.api.routes.avro.load_and_process_schema_wrapper",
                return_value=(SimpleNamespace(schema=object()), object()),
            ) as wrapper_mock,
            patch("s2dm.api.routes.avro.check_correct_schema", return_value=[]) as schema_check_mock,
            patch(
                "s2dm.api.routes.avro.translate_to_avro_protocol",
                return_value={"Selection": "protocol Selection {}"},
            ) as exporter_mock,
        ):
            response = test_client.post("/api/v1/export/avro/protocol", json=payload)

        assert response.status_code == 200
        assert response.json()["metadata"]["result_format"] == "avdl"
        wrapper_mock.assert_called_once()
        schema_check_mock.assert_called_once()
        exporter_mock.assert_called_once()

    def test_jsonschema_route_calls_internal_functions(self, test_client: TestClient) -> None:
        """JSON Schema route calls wrapper, schema check, and exporter."""
        payload = {
            "schemas": [{"type": "content", "content": "type Query { vehicle: Vehicle } type Vehicle { id: ID! }"}],
            "strict": False,
        }

        with (
            patch(
                "s2dm.api.routes.jsonschema.load_and_process_schema_wrapper",
                return_value=(SimpleNamespace(schema=object()), object()),
            ) as wrapper_mock,
            patch("s2dm.api.routes.jsonschema.check_correct_schema", return_value=[]) as schema_check_mock,
            patch(
                "s2dm.api.routes.jsonschema.translate_to_jsonschema", return_value='{"type":"object"}'
            ) as exporter_mock,
        ):
            response = test_client.post("/api/v1/export/jsonschema", json=payload)

        assert response.status_code == 200
        assert response.json()["metadata"]["result_format"] == "json"
        wrapper_mock.assert_called_once()
        schema_check_mock.assert_called_once()
        exporter_mock.assert_called_once()

    def test_protobuf_route_calls_internal_functions(self, test_client: TestClient) -> None:
        """Protobuf route calls wrapper, schema check, and exporter."""
        payload = {
            "schemas": [{"type": "content", "content": "type Query { vehicle: Vehicle } type Vehicle { id: ID! }"}],
            "selection_query": {"type": "content", "content": "query Selection { vehicle { id } }"},
        }

        with (
            patch(
                "s2dm.api.routes.protobuf.load_and_process_schema_wrapper",
                return_value=(SimpleNamespace(schema=object()), object()),
            ) as wrapper_mock,
            patch("s2dm.api.routes.protobuf.check_correct_schema", return_value=[]) as schema_check_mock,
            patch("s2dm.api.routes.protobuf.translate_to_protobuf", return_value='syntax = "proto3";') as exporter_mock,
        ):
            response = test_client.post("/api/v1/export/protobuf", json=payload)

        assert response.status_code == 200
        assert response.json()["metadata"]["result_format"] == "proto"
        wrapper_mock.assert_called_once()
        schema_check_mock.assert_called_once()
        exporter_mock.assert_called_once()

    def test_shacl_route_calls_internal_functions(self, test_client: TestClient) -> None:
        """SHACL route calls wrapper, schema check, and exporter."""
        payload = {
            "schemas": [{"type": "content", "content": "type Query { vehicle: Vehicle } type Vehicle { id: ID! }"}],
            "serialization_format": "ttl",
        }
        graph_mock = Mock()
        graph_mock.serialize.return_value = "@prefix ex: <http://example/> ."

        with (
            patch(
                "s2dm.api.routes.shacl.load_and_process_schema_wrapper",
                return_value=(SimpleNamespace(schema=object()), object()),
            ) as wrapper_mock,
            patch("s2dm.api.routes.shacl.check_correct_schema", return_value=[]) as schema_check_mock,
            patch("s2dm.api.routes.shacl.translate_to_shacl", return_value=graph_mock) as exporter_mock,
        ):
            response = test_client.post("/api/v1/export/shacl", json=payload)

        assert response.status_code == 200
        assert response.json()["metadata"]["result_format"] == "ttl"
        wrapper_mock.assert_called_once()
        schema_check_mock.assert_called_once()
        exporter_mock.assert_called_once()

    def test_vspec_route_calls_internal_functions(self, test_client: TestClient) -> None:
        """VSPEC route calls wrapper, schema check, and exporter."""
        payload = {
            "schemas": [{"type": "content", "content": "type Query { vehicle: Vehicle } type Vehicle { id: ID! }"}],
        }

        with (
            patch(
                "s2dm.api.routes.vspec.load_and_process_schema_wrapper",
                return_value=(SimpleNamespace(schema=object()), object()),
            ) as wrapper_mock,
            patch("s2dm.api.routes.vspec.check_correct_schema", return_value=[]) as schema_check_mock,
            patch("s2dm.api.routes.vspec.translate_to_vspec", return_value="Vehicle:\n  id: {}") as exporter_mock,
        ):
            response = test_client.post("/api/v1/export/vspec", json=payload)

        assert response.status_code == 200
        assert response.json()["metadata"]["result_format"] == "vspec"
        wrapper_mock.assert_called_once()
        schema_check_mock.assert_called_once()
        exporter_mock.assert_called_once()


class TestExportSchemaValidationGuards:
    """Test that exporters are skipped when schema validation fails."""

    @pytest.mark.parametrize(
        ("route", "payload", "route_module", "exporter_function_name"),
        [
            (
                "/api/v1/export/avro/schema",
                {
                    "schemas": [
                        {"type": "content", "content": "type Query { vehicle: Vehicle } type Vehicle { id: ID! }"}
                    ],
                    "selection_query": {"type": "content", "content": "query Selection { vehicle { id } }"},
                    "namespace": "com.example.test",
                },
                "s2dm.api.routes.avro",
                "translate_to_avro_schema",
            ),
            (
                "/api/v1/export/avro/protocol",
                {
                    "schemas": [
                        {"type": "content", "content": "type Query { vehicle: Vehicle } type Vehicle { id: ID! }"}
                    ],
                    "namespace": "com.example.test",
                    "strict": True,
                },
                "s2dm.api.routes.avro",
                "translate_to_avro_protocol",
            ),
            (
                "/api/v1/export/jsonschema",
                {
                    "schemas": [
                        {"type": "content", "content": "type Query { vehicle: Vehicle } type Vehicle { id: ID! }"}
                    ],
                    "strict": False,
                },
                "s2dm.api.routes.jsonschema",
                "translate_to_jsonschema",
            ),
            (
                "/api/v1/export/protobuf",
                {
                    "schemas": [
                        {"type": "content", "content": "type Query { vehicle: Vehicle } type Vehicle { id: ID! }"}
                    ],
                    "selection_query": {"type": "content", "content": "query Selection { vehicle { id } }"},
                },
                "s2dm.api.routes.protobuf",
                "translate_to_protobuf",
            ),
            (
                "/api/v1/export/shacl",
                {
                    "schemas": [
                        {"type": "content", "content": "type Query { vehicle: Vehicle } type Vehicle { id: ID! }"}
                    ],
                    "serialization_format": "ttl",
                },
                "s2dm.api.routes.shacl",
                "translate_to_shacl",
            ),
            (
                "/api/v1/export/vspec",
                {
                    "schemas": [
                        {"type": "content", "content": "type Query { vehicle: Vehicle } type Vehicle { id: ID! }"}
                    ],
                },
                "s2dm.api.routes.vspec",
                "translate_to_vspec",
            ),
        ],
    )
    def test_exporter_not_called_when_schema_invalid(
        self,
        test_client: TestClient,
        route: str,
        payload: dict[str, object],
        route_module: str,
        exporter_function_name: str,
    ) -> None:
        """Schema check failures return 422 and short-circuit exporter execution."""
        with (
            patch(
                f"{route_module}.load_and_process_schema_wrapper",
                return_value=(SimpleNamespace(schema=object()), object()),
            ),
            patch(f"{route_module}.check_correct_schema", return_value=["invalid schema"]) as schema_check_mock,
            patch(f"{route_module}.{exporter_function_name}") as exporter_mock,
        ):
            response = test_client.post(route, json=payload)

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "ValidationError"
        schema_check_mock.assert_called_once()
        exporter_mock.assert_not_called()
