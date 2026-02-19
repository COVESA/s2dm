"""Core API tests for health, capabilities, and error handling."""

from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from graphql import GraphQLError, GraphQLSyntaxError, Source

from s2dm import __version__
from s2dm.api.main import app


class TestCoreEndpoints:
    """Test health and metadata endpoints."""

    def test_health_check_returns_200_with_version(self, test_client: TestClient) -> None:
        """Health endpoint returns 200 with status and version."""
        response = test_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == __version__

    def test_capabilities_returns_openapi_schema(self, test_client: TestClient) -> None:
        """Capabilities endpoint returns valid OpenAPI schema."""
        response = test_client.get("/api/v1/capabilities")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "S2DM Export API"
        assert "paths" in data


class TestErrorHandling:
    """Test global error handling."""

    def test_missing_required_field_returns_400(self, test_client: TestClient) -> None:
        """Missing required fields return 400 with validation errors."""
        response = test_client.post(
            "/api/v1/export/avro/schema",
            json={},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "BadRequest"
        assert "validation_errors" in data["details"]

    def test_schema_validation_error_returns_422(self, test_client: TestClient) -> None:
        """Schema validation errors return 422."""
        response = test_client.post(
            "/api/v1/export/avro/schema",
            json={
                "schemas": [{"type": "content", "content": "type Query { test: NonExistentType }"}],
                "selection_query": {"type": "content", "content": "query { test }"},
                "namespace": "com.test",
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"] in ["ValidationError", "GraphQLError"]

    def test_missing_selection_query_returns_400(self, test_client: TestClient) -> None:
        """Returns 400 when selection_query is required but missing."""
        response = test_client.post(
            "/api/v1/export/avro/schema",
            json={
                "schemas": [{"type": "content", "content": "type Query { test: String }"}],
                "namespace": "com.test",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "BadRequest"

    def test_cors_allows_localhost(self, test_client: TestClient) -> None:
        """CORS middleware allows localhost requests."""
        response = test_client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000"},
        )

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


class TestExceptionHandlers:
    """Test specific exception handlers in API app."""

    @staticmethod
    def _valid_avro_request() -> dict[str, object]:
        return {
            "schemas": [{"type": "content", "content": "type Query { test: String }"}],
            "selection_query": {"type": "content", "content": "query Selection { test }"},
            "namespace": "com.test",
        }

    def test_file_not_found_error_returns_400(self, test_client: TestClient) -> None:
        """FileNotFoundError is mapped to 400."""
        with patch("s2dm.api.routes.avro.load_and_process_schema_wrapper", side_effect=FileNotFoundError("missing")):
            response = test_client.post("/api/v1/export/avro/schema", json=self._valid_avro_request())

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "FileNotFound"

    def test_runtime_error_returns_400(self, test_client: TestClient) -> None:
        """RuntimeError is mapped to 400."""
        with patch("s2dm.api.routes.avro.load_and_process_schema_wrapper", side_effect=RuntimeError("download failed")):
            response = test_client.post("/api/v1/export/avro/schema", json=self._valid_avro_request())

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "RuntimeError"

    def test_type_error_returns_422(self, test_client: TestClient) -> None:
        """TypeError is mapped to 422 ValidationError."""
        annotated_schema = SimpleNamespace(schema=object())
        with (
            patch("s2dm.api.routes.avro.load_and_process_schema_wrapper", return_value=(annotated_schema, object())),
            patch("s2dm.api.routes.avro.check_correct_schema", return_value=[]),
            patch("s2dm.api.routes.avro.translate_to_avro_schema", side_effect=TypeError("bad type")),
        ):
            response = test_client.post("/api/v1/export/avro/schema", json=self._valid_avro_request())

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "ValidationError"

    def test_graphql_syntax_error_returns_422(self, test_client: TestClient) -> None:
        """GraphQLSyntaxError is mapped to 422."""
        syntax_error = GraphQLSyntaxError(Source("query Selection {"), 18, "Syntax Error")
        with patch("s2dm.api.routes.avro.load_and_process_schema_wrapper", side_effect=syntax_error):
            response = test_client.post("/api/v1/export/avro/schema", json=self._valid_avro_request())

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "GraphQLSyntaxError"

    def test_graphql_error_returns_422(self, test_client: TestClient) -> None:
        """GraphQLError is mapped to 422."""
        with patch(
            "s2dm.api.routes.avro.load_and_process_schema_wrapper", side_effect=GraphQLError("validation failed")
        ):
            response = test_client.post("/api/v1/export/avro/schema", json=self._valid_avro_request())

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "GraphQLError"

    def test_unhandled_exception_returns_500(self) -> None:
        """Unexpected exceptions are mapped to 500."""
        with (
            patch("s2dm.api.routes.avro.load_and_process_schema_wrapper", side_effect=Exception("unexpected")),
            TestClient(app, raise_server_exceptions=False) as non_raising_client,
        ):
            response = non_raising_client.post("/api/v1/export/avro/schema", json=self._valid_avro_request())

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "ServerError"
