from collections.abc import Callable

from fastapi.testclient import TestClient

IdentitiesPayloadFactory = Callable[[list[dict[str, str]]], dict[str, object]]


class TestDependenciesIdentitiesRoute:
    """Test /api/v1/deps/identities route behavior."""

    def test_get_dependencies_identities_missing_returns_404(self, test_client: TestClient) -> None:
        response = test_client.get("/api/v1/deps/identities")

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "NotFound"

    def test_store_dependencies_identities_returns_204(
        self,
        test_client: TestClient,
        identities_payload_factory: IdentitiesPayloadFactory,
    ) -> None:
        response = test_client.post(
            "/api/v1/deps/identities",
            json=identities_payload_factory([{"host": "github.com", "token": "test-token"}]),
        )

        assert response.status_code == 204
        assert response.content == b""

    def test_get_dependencies_identities_returns_stored_identities(
        self,
        test_client: TestClient,
        identities_payload_factory: IdentitiesPayloadFactory,
    ) -> None:
        test_client.post(
            "/api/v1/deps/identities",
            json=identities_payload_factory(
                [
                    {"host": "github.com", "token": "test-token"},
                    {"host": "example.ghe.com", "scope": "owner/repository", "token": "other-token"},
                ]
            ),
        )

        response = test_client.get("/api/v1/deps/identities")

        assert response.status_code == 200
        data = response.json()
        assert data["identities"] == [
            {"host": "github.com", "scope": None, "token": "test-token"},
            {"host": "example.ghe.com", "scope": "owner/repository", "token": "other-token"},
        ]

    def test_delete_dependencies_identities_existing_returns_204(
        self,
        test_client: TestClient,
        identities_payload_factory: IdentitiesPayloadFactory,
    ) -> None:
        test_client.post(
            "/api/v1/deps/identities",
            json=identities_payload_factory([{"host": "github.com", "token": "test-token"}]),
        )

        response = test_client.delete("/api/v1/deps/identities")

        assert response.status_code == 204
        assert response.content == b""

    def test_delete_dependencies_identities_missing_returns_204(self, test_client: TestClient) -> None:
        response = test_client.delete("/api/v1/deps/identities")

        assert response.status_code == 204
        assert response.content == b""
