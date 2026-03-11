"""API tests for schema and query validation routes."""

from fastapi.testclient import TestClient


class TestSchemaFilterRoute:
    """Test /api/v1/schema/filter route behavior."""

    def test_filter_schema_successful(self, test_client: TestClient) -> None:
        """Valid filter request returns filtered GraphQL schema output."""
        response = test_client.post(
            "/api/v1/schema/filter",
            json={
                "schemas": [
                    {
                        "type": "content",
                        "content": "type Query { vehicle: Vehicle } type Vehicle { id: ID! speed: Float }",
                    }
                ],
                "selection_query": {"type": "content", "content": "query Selection { vehicle { id } }"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["result_format"] == "graphql"
        assert len(data["result"]) == 1
        assert "type Vehicle" in data["result"][0]

    def test_filter_schema_missing_required_field_returns_400(self, test_client: TestClient) -> None:
        """Missing required fields returns BadRequest."""
        response = test_client.post(
            "/api/v1/schema/filter",
            json={},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "BadRequest"
        assert "validation_errors" in data["details"]

    def test_filter_schema_invalid_query_returns_422(self, test_client: TestClient) -> None:
        """Semantically invalid query returns validation error."""
        response = test_client.post(
            "/api/v1/schema/filter",
            json={
                "schemas": [
                    {
                        "type": "content",
                        "content": "type Query { vehicle: Vehicle } type Vehicle { id: ID! speed: Float }",
                    }
                ],
                "selection_query": {"type": "content", "content": "query Selection { missingField }"},
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"] in ["ValidationError", "GraphQLError"]


class TestSchemaValidateRoute:
    """Test /api/v1/schema/validate route behavior."""

    def test_validate_schema_successful(self, test_client: TestClient) -> None:
        """Valid schema request returns composed schema output."""
        response = test_client.post(
            "/api/v1/schema/validate",
            json={
                "schemas": [
                    {
                        "type": "content",
                        "content": "type Query { vehicle: Vehicle } type Vehicle { id: ID! speed: Float }",
                    }
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["result_format"] == "graphql"
        assert len(data["result"]) == 1
        assert "type Query" in data["result"][0]

    def test_validate_schema_missing_required_field_returns_400(self, test_client: TestClient) -> None:
        """Missing required fields returns BadRequest."""
        response = test_client.post(
            "/api/v1/schema/validate",
            json={},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "BadRequest"
        assert "validation_errors" in data["details"]

    def test_validate_schema_invalid_definition_returns_422(self, test_client: TestClient) -> None:
        """Semantically invalid schema returns validation error."""
        response = test_client.post(
            "/api/v1/schema/validate",
            json={
                "schemas": [
                    {
                        "type": "content",
                        "content": "type Query { vehicle: NonExistentType }",
                    }
                ],
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "ValidationError"

    def test_validate_schema_invalid_syntax_returns_meaningful_message(self, test_client: TestClient) -> None:
        """Schema syntax errors are normalized by the shared response service."""
        response = test_client.post(
            "/api/v1/schema/validate",
            json={
                "schemas": [
                    {
                        "type": "content",
                        "content": "type Query { vehicle: String ",
                    }
                ],
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "ValidationError"
        assert "Syntax Error" in data["message"]

    def test_validate_schema_file_content_uses_filename_for_reference_source(self, test_client: TestClient) -> None:
        """file_content schemas preserve filename in @reference source mapping."""
        schema_with_reference = (
            "directive @reference(uri: String, source: String, versionTag: String) "
            "on OBJECT | INTERFACE | UNION | ENUM | ENUM_VALUE | SCALAR | INPUT_OBJECT | FIELD_DEFINITION\n"
            "type Query { vehicle: Vehicle }\n"
            "type Vehicle { id: ID! }\n"
        )

        response = test_client.post(
            "/api/v1/schema/validate",
            json={
                "schemas": [
                    {
                        "type": "file_content",
                        "filename": "vehicle.graphql",
                        "content": schema_with_reference,
                    }
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["result_format"] == "graphql"
        assert 'type Vehicle @reference(source: "vehicle.graphql")' in data["result"][0]


class TestQueryValidateRoute:
    """Test /api/v1/query/validate route behavior."""

    def test_validate_query_successful(self, test_client: TestClient) -> None:
        """Valid query request returns schema output."""
        response = test_client.post(
            "/api/v1/query/validate",
            json={
                "schemas": [
                    {
                        "type": "content",
                        "content": "type Query { vehicle: Vehicle } type Vehicle { id: ID! speed: Float }",
                    }
                ],
                "selection_query": {"type": "content", "content": "query Selection { vehicle { id } }"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["result_format"] == "graphql"
        assert len(data["result"]) == 1
        assert "type Query" in data["result"][0]

    def test_validate_query_missing_required_field_returns_400(self, test_client: TestClient) -> None:
        """Missing required fields returns BadRequest."""
        response = test_client.post(
            "/api/v1/query/validate",
            json={},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "BadRequest"
        assert "validation_errors" in data["details"]

    def test_validate_query_invalid_selection_returns_422(self, test_client: TestClient) -> None:
        """Semantically invalid query returns validation error."""
        response = test_client.post(
            "/api/v1/query/validate",
            json={
                "schemas": [
                    {
                        "type": "content",
                        "content": "type Query { vehicle: Vehicle } type Vehicle { id: ID! speed: Float }",
                    }
                ],
                "selection_query": {"type": "content", "content": "query Selection { missingField }"},
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "ValidationError"
        assert "Query validation failed:" in data["message"]

    def test_validate_query_invalid_syntax_returns_meaningful_message(self, test_client: TestClient) -> None:
        """Query syntax errors are normalized by the shared response service."""
        response = test_client.post(
            "/api/v1/query/validate",
            json={
                "schemas": [
                    {
                        "type": "content",
                        "content": "type Query { vehicle: Vehicle } type Vehicle { id: ID! speed: Float }",
                    }
                ],
                "selection_query": {"type": "content", "content": "query Selection { vehicle { id }"},
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "ValidationError"
        assert "Syntax Error" in data["message"]
