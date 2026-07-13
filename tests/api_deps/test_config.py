from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient

from s2dm.deps import DEPENDENCY_LOCK_FILENAME
from s2dm.deps.resolve.common import SCHEMA_FILENAME, VENDOR_DIRECTORY

DependenciesConfigPayloadFactory = Callable[..., dict[str, object]]


class TestDependenciesConfigRoute:
    """Test /api/v1/deps/config route behavior."""

    def test_get_dependencies_config_missing_returns_404(self, test_client: TestClient) -> None:
        response = test_client.get("/api/v1/deps/config")

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "NotFound"

    def test_store_dependencies_config_returns_204(
        self,
        test_client: TestClient,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
    ) -> None:
        response = test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory(["https://github.com/example/repository"]),
        )

        assert response.status_code == 204
        assert response.content == b""

    def test_get_dependencies_config_returns_stored_dependencies(
        self,
        test_client: TestClient,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
    ) -> None:
        test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory(
                ["https://github.com/example/repository"],
                names=["RemoteDependency"],
                versions=["1.0.0"],
            ),
        )

        response = test_client.get("/api/v1/deps/config")

        assert response.status_code == 200
        data = response.json()
        assert data["dependencies"] == [
            {
                "name": "RemoteDependency",
                "version": "1.0.0",
                "source": "https://github.com/example/repository",
                "artifact": "schema.graphql",
                "selection": None,
            }
        ]

    def test_get_dependencies_config_returns_content_backed_selection(
        self,
        test_client: TestClient,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
    ) -> None:
        selection_content = "query Selection { vehicle { vin } }\n"
        test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory(
                ["https://github.com/example/repository"],
                names=["RemoteDependency"],
                versions=["1.0.0"],
                selections=[{"type": "content", "content": selection_content}],
            ),
        )

        response = test_client.get("/api/v1/deps/config")

        assert response.status_code == 200
        data = response.json()
        assert data["dependencies"][0]["selection"] == {"type": "content", "content": selection_content}

    def test_store_dependencies_config_invalid_missing_absolute_selection_path_returns_422(
        self,
        test_client: TestClient,
        tmp_path: Path,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
    ) -> None:
        missing_selection_path = tmp_path / "missing-selection.graphql"

        response = test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory(
                ["https://github.com/example/repository"],
                names=["RemoteDependency"],
                versions=["1.0.0"],
                selections=[{"type": "path", "path": str(missing_selection_path.resolve())}],
            ),
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "ValidationError"

    def test_store_dependencies_config_normalizes_absolute_path_selection_to_managed_content(
        self,
        test_client: TestClient,
        api_workspace: Path,
        tmp_path: Path,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
    ) -> None:
        selection_path = tmp_path / "selection.graphql"
        selection_content = "query Selection { vehicle { vin } }\n"
        selection_path.write_text(selection_content, encoding="utf-8")

        response = test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory(
                ["https://github.com/example/repository"],
                names=["RemoteDependency"],
                versions=["1.0.0"],
                selections=[{"type": "path", "path": str(selection_path.resolve())}],
            ),
        )

        assert response.status_code == 204
        managed_selection_path = api_workspace / "selections" / "RemoteDependency-1.0.0.graphql"
        assert managed_selection_path.read_text(encoding="utf-8") == selection_content
        assert selection_path.exists()

        response = test_client.get("/api/v1/deps/config")

        assert response.status_code == 200
        data = response.json()
        assert data["dependencies"][0]["selection"] == {"type": "content", "content": selection_content}

    def test_get_dependencies_config_returns_vendored_schema_when_available(
        self,
        test_client: TestClient,
        api_workspace: Path,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
    ) -> None:
        schema_content = "type Query { vehicle: Vehicle }\ntype Vehicle { vin: String }\n"
        test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory(
                ["https://github.com/example/repository"],
                names=["RemoteDependency"],
                versions=["1.0.0"],
            ),
        )
        vendored_schema_path = api_workspace / VENDOR_DIRECTORY / "RemoteDependency" / "1.0.0" / SCHEMA_FILENAME
        vendored_schema_path.parent.mkdir(parents=True, exist_ok=True)
        vendored_schema_path.write_text(schema_content, encoding="utf-8")

        response = test_client.get("/api/v1/deps/config")

        assert response.status_code == 200
        data = response.json()
        assert data["dependencies"][0]["schema_content"] == schema_content

    def test_store_dependencies_config_resolves_relative_selection_path_with_config_directory(
        self,
        test_client: TestClient,
        api_workspace: Path,
        tmp_path: Path,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
    ) -> None:
        config_directory = tmp_path / "configs"
        config_directory.mkdir()
        selection_path = tmp_path / "queries" / "selection.graphql"
        selection_path.parent.mkdir()
        selection_content = "query Selection { vehicle { vin } }\n"
        selection_path.write_text(selection_content, encoding="utf-8")

        payload = dependencies_config_payload_factory(
            ["https://github.com/example/repository"],
            names=["RemoteDependency"],
            versions=["1.0.0"],
            selections=[{"type": "path", "path": "../queries/selection.graphql"}],
        )
        payload["config_directory"] = str(config_directory.resolve())

        response = test_client.post("/api/v1/deps/config", json=payload)

        assert response.status_code == 204
        managed_selection_path = api_workspace / "selections" / "RemoteDependency-1.0.0.graphql"
        assert managed_selection_path.read_text(encoding="utf-8") == selection_content

        response = test_client.get("/api/v1/deps/config")

        assert response.status_code == 200
        data = response.json()
        assert data["dependencies"][0]["selection"] == {"type": "content", "content": selection_content}

    def test_store_dependencies_config_relative_selection_without_config_directory_returns_422(
        self,
        test_client: TestClient,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
    ) -> None:
        response = test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory(
                ["https://github.com/example/repository"],
                names=["RemoteDependency"],
                versions=["1.0.0"],
                selections=[{"type": "path", "path": "queries/selection.graphql"}],
            ),
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "ValidationError"

    def test_store_dependencies_config_cleans_up_orphaned_managed_selection_files(
        self,
        test_client: TestClient,
        api_workspace: Path,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
    ) -> None:
        selection_content = "query Selection { vehicle { vin } }\n"
        test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory(
                ["https://github.com/example/repository"],
                names=["RemoteDependency"],
                versions=["1.0.0"],
                selections=[{"type": "content", "content": selection_content}],
            ),
        )

        managed_selection_path = api_workspace / "selections" / "RemoteDependency-1.0.0.graphql"
        orphan_selection_path = api_workspace / "selections" / "orphan.graphql"
        orphan_selection_path.write_text("query Selection { vehicle { id } }\n", encoding="utf-8")

        response = test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory(
                ["https://github.com/example/repository"],
                names=["RemoteDependency"],
                versions=["1.0.0"],
            ),
        )

        assert response.status_code == 204
        assert not managed_selection_path.exists()
        assert not orphan_selection_path.exists()

    def test_store_dependencies_config_preserves_external_selection_file_from_cleanup(
        self,
        test_client: TestClient,
        api_workspace: Path,
        tmp_path: Path,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
    ) -> None:
        selection_path = tmp_path / "selection.graphql"
        selection_path.write_text("query Selection { vehicle { vin } }\n", encoding="utf-8")
        test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory(
                ["https://github.com/example/repository"],
                names=["RemoteDependency"],
                versions=["1.0.0"],
                selections=[{"type": "path", "path": str(selection_path.resolve())}],
            ),
        )

        managed_selection_path = api_workspace / "selections" / "RemoteDependency-1.0.0.graphql"
        response = test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory(
                ["https://github.com/example/repository"],
                names=["RemoteDependency"],
                versions=["1.0.0"],
            ),
        )

        assert response.status_code == 204
        assert selection_path.exists()
        assert not managed_selection_path.exists()

    def test_store_dependencies_config_empty_list_clears_lock_and_vendored_dependencies(
        self,
        test_client: TestClient,
        api_workspace: Path,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
    ) -> None:
        lock_path = api_workspace / DEPENDENCY_LOCK_FILENAME
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text("dependencies: []\n", encoding="utf-8")

        vendored_dependency_path = api_workspace / VENDOR_DIRECTORY / "DemoDependency" / "1.0.0"
        vendored_dependency_path.mkdir(parents=True, exist_ok=True)
        (vendored_dependency_path / "schema.graphql").write_text("type Query { cached: String }\n", encoding="utf-8")

        response = test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory([]),
        )

        assert response.status_code == 204
        assert not lock_path.exists()
        assert not (api_workspace / VENDOR_DIRECTORY).exists()

        response = test_client.get("/api/v1/deps/config")

        assert response.status_code == 200
        assert response.json() == {"dependencies": []}
