from pathlib import Path

from fastapi.testclient import TestClient

from s2dm.deps import DEPENDENCY_LOCK_FILENAME
from s2dm.deps.resolve.common import METADATA_FILENAME, SCHEMA_FILENAME, VENDOR_DIRECTORY
from tests.api_deps.conftest import DependenciesConfigPayloadFactory, DependencySourceFactory
from tests.deps.helpers import file_sha256, write_dependency_lock, write_metadata_file


class TestDependenciesStatusRoute:
    """Test /api/v1/deps/status route behavior."""

    def test_get_dependencies_status_without_config_returns_not_configured(
        self,
        test_client: TestClient,
    ) -> None:
        response = test_client.get("/api/v1/deps/status")

        assert response.status_code == 200
        assert response.json() == {"status": "not_configured"}

    def test_get_dependencies_status_with_config_without_lock_returns_unresolved(
        self,
        test_client: TestClient,
        dependency_source_factory: DependencySourceFactory,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
    ) -> None:
        source_directory = dependency_source_factory(
            "source",
            name="DemoDependency",
            version="1.0.0",
            schema="type Query { ping: String }\n",
            metadata_id="urn:test:demo",
        )
        test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory(
                [source_directory.resolve()],
                names=["DemoDependency"],
                versions=["1.0.0"],
            ),
        )

        response = test_client.get("/api/v1/deps/status")

        assert response.status_code == 200
        assert response.json() == {"status": "unresolved"}

    def test_get_dependencies_status_with_valid_lock_and_cache_returns_resolved(
        self,
        test_client: TestClient,
        dependency_source_factory: DependencySourceFactory,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
    ) -> None:
        source_directory = dependency_source_factory(
            "source",
            name="DemoDependency",
            version="1.0.0",
            schema="type Query { ping: String }\n",
            metadata_id="urn:test:demo",
        )
        test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory(
                [source_directory.resolve()],
                names=["DemoDependency"],
                versions=["1.0.0"],
            ),
        )
        test_client.post("/api/v1/deps/resolve", json={"clean": False})

        response = test_client.get("/api/v1/deps/status")

        assert response.status_code == 200
        assert response.json() == {"status": "resolved"}

    def test_get_dependencies_status_with_lock_mismatch_returns_invalid(
        self,
        test_client: TestClient,
        api_workspace: Path,
        dependency_source_factory: DependencySourceFactory,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
    ) -> None:
        source_directory = dependency_source_factory(
            "source",
            name="DemoDependency",
            version="1.0.0",
            schema="type Query { ping: String }\n",
            metadata_id="urn:test:demo",
        )
        test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory(
                [source_directory.resolve()],
                names=["DemoDependency"],
                versions=["1.0.0"],
            ),
        )

        vendor_directory = api_workspace / VENDOR_DIRECTORY / "DemoDependency" / "1.0.0"
        vendor_directory.mkdir(parents=True)
        vendored_schema_path = vendor_directory / SCHEMA_FILENAME
        vendored_schema_path.write_text("type Query { cached: String }\n", encoding="utf-8")
        write_metadata_file(
            vendor_directory / METADATA_FILENAME,
            name="DemoDependency",
            version="1.0.0",
            id="urn:test:demo",
        )
        write_dependency_lock(
            api_workspace / DEPENDENCY_LOCK_FILENAME,
            name="DemoDependency",
            version="1.0.0",
            resolved_path=str((Path("/tmp") / "other" / SCHEMA_FILENAME).resolve()),
            integrity=file_sha256(vendored_schema_path),
        )

        response = test_client.get("/api/v1/deps/status")

        assert response.status_code == 200
        assert response.json() == {"status": "invalid"}

    def test_get_dependencies_status_with_missing_cached_schema_returns_invalid(
        self,
        test_client: TestClient,
        api_workspace: Path,
        dependency_source_factory: DependencySourceFactory,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
    ) -> None:
        source_directory = dependency_source_factory(
            "source",
            name="DemoDependency",
            version="1.0.0",
            schema="type Query { ping: String }\n",
            metadata_id="urn:test:demo",
        )
        test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory(
                [source_directory.resolve()],
                names=["DemoDependency"],
                versions=["1.0.0"],
            ),
        )
        test_client.post("/api/v1/deps/resolve", json={"clean": False})

        cached_schema_path = api_workspace / VENDOR_DIRECTORY / "DemoDependency" / "1.0.0" / SCHEMA_FILENAME
        cached_schema_path.unlink()

        response = test_client.get("/api/v1/deps/status")

        assert response.status_code == 200
        assert response.json() == {"status": "invalid"}
