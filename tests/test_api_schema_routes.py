"""API tests for schema and query validation routes."""

from fastapi.testclient import TestClient

INVALID_ENUM_DEFAULT_SCHEMA = """
enum DriveMode { ECO SPORT }
input VehicleFilter { mode: DriveMode = COMFORT }
type Query { vehicle(filter: VehicleFilter): String }
"""

PICK_DOOR_SCHEMA = """
directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

type Query {
  doors: [Door]
}

type Door {
  position: DoorPosition @instanceTag
}

type DoorPosition @instanceTag {
  side: Side
}

enum Side {
  LEFT
  RIGHT
}
"""


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

    def test_filter_schema_invalid_enum_default_returns_422(self, test_client: TestClient) -> None:
        """Schemas rejected by shared correctness checks fail before filtering."""
        response = test_client.post(
            "/api/v1/schema/filter",
            json={
                "schemas": [{"type": "content", "content": INVALID_ENUM_DEFAULT_SCHEMA}],
                "selection_query": {"type": "content", "content": "query Selection { vehicle }"},
            },
        )

        assert response.status_code == 422
        assert response.json()["error"] == "ValidationError"


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


class TestSchemaInstanceTagsRoute:
    """Test /api/v1/schema/instance-tags route behavior."""

    def test_instance_tags_indexes_the_tag_fields(self, test_client: TestClient) -> None:
        """Each instance tag field comes with its dimensions and the instances left after exclude."""
        schema_content = """
        directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM
        type Query { doors: [Door] }
        type Door { position: DoorPosition @instanceTag(exclude: ["ROW2.RIGHT"]) }
        type DoorPosition @instanceTag { row: Row side: Side }
        enum Row { ROW1 ROW2 }
        enum Side { LEFT RIGHT }
        """
        response = test_client.post(
            "/api/v1/schema/instance-tags",
            json={"schemas": [{"type": "content", "content": schema_content}]},
        )

        assert response.status_code == 200
        assert response.json() == {
            "Door.position": {
                "dimensions": {"row": ["ROW1", "ROW2"], "side": ["LEFT", "RIGHT"]},
                "instances": ["ROW1.LEFT", "ROW1.RIGHT", "ROW2.LEFT"],
            }
        }

    def test_instance_tags_without_tag_fields_returns_an_empty_index(self, test_client: TestClient) -> None:
        """A schema without instance tags returns no tag fields."""
        schema_content = "type Query { vehicle: Vehicle } type Vehicle { id: ID }"
        response = test_client.post(
            "/api/v1/schema/instance-tags",
            json={"schemas": [{"type": "content", "content": schema_content}]},
        )

        assert response.status_code == 200
        assert response.json() == {}

    def test_instance_tags_missing_required_field_returns_400(self, test_client: TestClient) -> None:
        """Missing required fields returns BadRequest."""
        response = test_client.post("/api/v1/schema/instance-tags", json={})

        assert response.status_code == 400
        assert response.json()["error"] == "BadRequest"


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

    def test_validate_query_accepts_pick_on_an_instance_tag_field(self, test_client: TestClient) -> None:
        """A query with @pick on an instance tag field is valid."""
        selection_query = 'query Selection { doors { position @pick(instances: ["LEFT"]) { side } } }'
        response = test_client.post(
            "/api/v1/query/validate",
            json={
                "schemas": [{"type": "content", "content": PICK_DOOR_SCHEMA}],
                "selection_query": {"type": "content", "content": selection_query},
            },
        )

        assert response.status_code == 200

    def test_validate_query_rejects_a_pick_the_tag_does_not_define_returns_422(self, test_client: TestClient) -> None:
        """A query whose @pick names an instance the tag does not define is invalid."""
        selection_query = 'query Selection { doors { position @pick(instances: ["MIDDLE"]) { side } } }'
        response = test_client.post(
            "/api/v1/query/validate",
            json={
                "schemas": [{"type": "content", "content": PICK_DOOR_SCHEMA}],
                "selection_query": {"type": "content", "content": selection_query},
            },
        )

        assert response.status_code == 422
        assert response.json()["error"] == "ValidationError"

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

    def test_validate_query_invalid_enum_default_returns_422(self, test_client: TestClient) -> None:
        """Schemas rejected by shared correctness checks fail before query validation."""
        response = test_client.post(
            "/api/v1/query/validate",
            json={
                "schemas": [{"type": "content", "content": INVALID_ENUM_DEFAULT_SCHEMA}],
                "selection_query": {"type": "content", "content": "query Selection { vehicle }"},
            },
        )

        assert response.status_code == 422
        assert response.json()["error"] == "ValidationError"
