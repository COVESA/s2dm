from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient

from s2dm.deps import DEPENDENCY_LOCK_FILENAME
from s2dm.deps.resolve.common import METADATA_FILENAME, SCHEMA_FILENAME, VENDOR_DIRECTORY
from tests.deps.helpers import file_sha256, write_dependency_lock, write_metadata_file

DependenciesConfigPayloadFactory = Callable[..., dict[str, object]]
DependencySourceFactory = Callable[..., Path]


class TestDepsBuildRoute:
    """Test /api/v1/deps/build route behavior."""

    def test_build_dependencies_missing_config_returns_404(self, test_client: TestClient) -> None:
        response = test_client.post("/api/v1/deps/build", json={"auto_prefix": False})

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "NotFound"

    def test_build_dependencies_success_returns_composed_schema(
        self,
        test_client: TestClient,
        dependency_source_factory: DependencySourceFactory,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
    ) -> None:
        source_directory = dependency_source_factory(
            "source",
            name="DemoDependency",
            version="1.0.0",
            schema="type Query { vehicle: Vehicle }\ntype Vehicle { vin: String }\n",
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

        response = test_client.post("/api/v1/deps/build", json={"auto_prefix": False})

        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["result_format"] == "graphql"
        assert "type Vehicle" in data["result"][0]
        assert "vin: String" in data["result"][0]

    def test_build_dependencies_applies_dependency_selection(
        self,
        test_client: TestClient,
        dependency_source_factory: DependencySourceFactory,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
    ) -> None:
        source_directory = dependency_source_factory(
            "source",
            name="DemoDependency",
            version="1.0.0",
            schema=(
                "type Query { vehicle: Vehicle }\n"
                "type Vehicle { vin: String model: String speed: Speed cabin: Cabin }\n"
                "type Speed { value: Float unit: String }\n"
                "type Cabin { seats: Int }\n"
            ),
            metadata_id="urn:test:demo",
        )
        test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory(
                [source_directory.resolve()],
                names=["DemoDependency"],
                versions=["1.0.0"],
                selections=[{"type": "content", "content": "query Selection { vehicle { vin speed { value } } }\n"}],
            ),
        )
        test_client.post("/api/v1/deps/resolve", json={"clean": False})

        response = test_client.post("/api/v1/deps/build", json={"auto_prefix": False})

        assert response.status_code == 200
        composed_schema = response.json()["result"][0]
        assert "type Vehicle" in composed_schema
        assert "vin: String" in composed_schema
        assert "speed: Speed" in composed_schema
        assert "value: Float" in composed_schema
        assert "model: String" not in composed_schema
        assert "unit: String" not in composed_schema
        assert "type Cabin" not in composed_schema

    def test_build_dependencies_invalid_selection_names_dependency(
        self,
        test_client: TestClient,
        dependency_source_factory: DependencySourceFactory,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
    ) -> None:
        source_directory = dependency_source_factory(
            "source",
            name="DemoDependency",
            version="1.0.0",
            schema="type Query { vehicle: Vehicle }\ntype Vehicle { vin: String }\n",
            metadata_id="urn:test:demo",
        )
        test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory(
                [source_directory.resolve()],
                names=["DemoDependency"],
                versions=["1.0.0"],
                selections=[{"type": "content", "content": "query Selection { vehicle { missingField } }\n"}],
            ),
        )
        test_client.post("/api/v1/deps/resolve", json={"clean": False})

        response = test_client.post("/api/v1/deps/build", json={"auto_prefix": False})

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "ValidationError"
        # The fix's contract: the error identifies which dependency failed.
        assert "DemoDependency" in data["message"]
        assert "1.0.0" in data["message"]
        assert "missingField" in data["message"]

    def test_build_dependencies_conflicts_without_auto_prefix_returns_422(
        self,
        test_client: TestClient,
        dependency_source_factory: DependencySourceFactory,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
    ) -> None:
        body_source_directory = dependency_source_factory(
            "body-source",
            name="BodyModel",
            version="1.0.0",
            schema="type BodyCatalog { vehicle: Vehicle }\ntype Vehicle { vin: String }\n",
            metadata_id="urn:test:body",
            preferred_prefix="body",
        )
        powertrain_source_directory = dependency_source_factory(
            "powertrain-source",
            name="PowertrainModel",
            version="2.0.0",
            schema="type PowertrainCatalog { vehicle: Vehicle }\ntype Vehicle { speed: Float }\n",
            metadata_id="urn:test:powertrain",
            preferred_prefix="powertrain",
        )
        test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory(
                [body_source_directory.resolve(), powertrain_source_directory.resolve()],
                names=["BodyModel", "PowertrainModel"],
                versions=["1.0.0", "2.0.0"],
            ),
        )
        test_client.post("/api/v1/deps/resolve", json={"clean": False})

        response = test_client.post("/api/v1/deps/build", json={"auto_prefix": False})

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "ValidationError"
        assert "Multiple `Vehicle` types found in [BodyModel@1.0.0, PowertrainModel@2.0.0]" in data["message"]

    def test_build_dependencies_auto_prefix_returns_composed_schema(
        self,
        test_client: TestClient,
        dependency_source_factory: DependencySourceFactory,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
    ) -> None:
        body_source_directory = dependency_source_factory(
            "body-source",
            name="BodyModel",
            version="1.0.0",
            schema="type BodyCatalog { vehicle: Vehicle }\ntype Vehicle { vin: String }\n",
            metadata_id="urn:test:body",
            preferred_prefix="body",
        )
        powertrain_source_directory = dependency_source_factory(
            "powertrain-source",
            name="PowertrainModel",
            version="2.0.0",
            schema="type PowertrainCatalog { vehicle: Vehicle }\ntype Vehicle { speed: Float }\n",
            metadata_id="urn:test:powertrain",
            preferred_prefix="powertrain",
        )
        test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory(
                [body_source_directory.resolve(), powertrain_source_directory.resolve()],
                names=["BodyModel", "PowertrainModel"],
                versions=["1.0.0", "2.0.0"],
            ),
        )
        test_client.post("/api/v1/deps/resolve", json={"clean": False})

        response = test_client.post("/api/v1/deps/build", json={"auto_prefix": True})

        assert response.status_code == 200
        composed_schema = response.json()["result"][0]
        assert "type body_Vehicle" in composed_schema
        assert "type powertrain_Vehicle" in composed_schema
        assert "vehicle: body_Vehicle" in composed_schema
        assert "vehicle: powertrain_Vehicle" in composed_schema

    def test_build_dependencies_with_lock_mismatch_returns_422(
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
        metadata_path = vendor_directory / METADATA_FILENAME
        write_metadata_file(
            metadata_path,
            name="DemoDependency",
            version="1.0.0",
            id="urn:test:demo",
        )
        lock_path = api_workspace / DEPENDENCY_LOCK_FILENAME
        invalid_resolved_path = str((Path("/tmp") / "other" / SCHEMA_FILENAME).resolve())
        write_dependency_lock(
            lock_path,
            name="DemoDependency",
            version="1.0.0",
            resolved_path=invalid_resolved_path,
            integrity=file_sha256(vendored_schema_path),
        )
        lock_content = lock_path.read_text(encoding="utf-8")
        metadata_content = metadata_path.read_text(encoding="utf-8")
        vendored_schema_content = vendored_schema_path.read_text(encoding="utf-8")

        response = test_client.post("/api/v1/deps/build", json={"auto_prefix": False})

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "DependencySourceError"
        assert lock_path.read_text(encoding="utf-8") == lock_content
        assert metadata_path.read_text(encoding="utf-8") == metadata_content
        assert vendored_schema_path.read_text(encoding="utf-8") == vendored_schema_content
