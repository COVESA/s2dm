from collections.abc import Callable
from pathlib import Path
from typing import Any

import requests
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

import s2dm.api.routes.deps as deps_route

DependenciesConfigPayloadFactory = Callable[..., dict[str, object]]
DependencySourceFactory = Callable[..., Path]
ResolvePayloadFactory = Callable[..., dict[str, bool]]


class TestDepsResolveRoute:
    """Test /api/v1/deps/resolve route behavior."""

    def test_resolve_dependencies_missing_config_returns_404(
        self,
        test_client: TestClient,
        resolve_payload_factory: ResolvePayloadFactory,
    ) -> None:
        response = test_client.post("/api/v1/deps/resolve", json=resolve_payload_factory())

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "NotFound"

    def test_resolve_dependencies_success_without_warnings_returns_204(
        self,
        test_client: TestClient,
        dependency_source_factory: DependencySourceFactory,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
        resolve_payload_factory: ResolvePayloadFactory,
    ) -> None:
        source_directory = dependency_source_factory(
            "source",
            name="DemoDependency",
            version="1.0.0",
            schema="type Query { ping: String }\n",
            metadata_id="urn:test:demo",
            preferred_prefix="demo",
        )
        test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory(
                [source_directory.resolve()],
                names=["DemoDependency"],
                versions=["1.0.0"],
            ),
        )

        response = test_client.post("/api/v1/deps/resolve", json=resolve_payload_factory())

        assert response.status_code == 204
        assert response.content == b""

    def test_resolve_dependencies_success_with_warnings_returns_200(
        self,
        test_client: TestClient,
        dependency_source_factory: DependencySourceFactory,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
        resolve_payload_factory: ResolvePayloadFactory,
    ) -> None:
        body_source_directory = dependency_source_factory(
            "body-source",
            name="BodyDependency",
            version="1.0.0",
            schema="type Query { body: String }\n",
            metadata_id="urn:test:body",
            preferred_prefix="demo",
        )
        powertrain_source_directory = dependency_source_factory(
            "powertrain-source",
            name="PowertrainDependency",
            version="1.0.0",
            schema="type Query { powertrain: String }\n",
            metadata_id="urn:test:powertrain",
            preferred_prefix="demo",
        )
        test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory(
                [body_source_directory.resolve(), powertrain_source_directory.resolve()],
                names=["BodyDependency", "PowertrainDependency"],
                versions=["1.0.0", "1.0.0"],
            ),
        )

        response = test_client.post("/api/v1/deps/resolve", json=resolve_payload_factory())

        assert response.status_code == 200
        data = response.json()
        assert len(data["warnings"]) == 2
        assert all("resolves prefix 'demo'" in warning for warning in data["warnings"])

    def test_resolve_dependencies_invalid_dependency_returns_422(
        self,
        test_client: TestClient,
        tmp_path: Path,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
        resolve_payload_factory: ResolvePayloadFactory,
    ) -> None:
        missing_source_directory = tmp_path / "missing-source"
        test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory(
                [missing_source_directory.resolve()],
                names=["MissingDependency"],
                versions=["1.0.0"],
            ),
        )

        response = test_client.post("/api/v1/deps/resolve", json=resolve_payload_factory())

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "DependencySourceError"
        assert "Dependency source directory does not exist" in data["message"]

    def test_resolve_dependencies_upstream_failure_returns_502(
        self,
        test_client: TestClient,
        monkeypatch: MonkeyPatch,
        dependencies_config_payload_factory: DependenciesConfigPayloadFactory,
        resolve_payload_factory: ResolvePayloadFactory,
    ) -> None:
        def fail_download(*args: Any, **kwargs: Any) -> None:
            raise requests.ConnectionError("upstream unavailable")

        test_client.post(
            "/api/v1/deps/config",
            json=dependencies_config_payload_factory(
                ["https://github.com/example/repository"],
                names=["RemoteDependency"],
                versions=["1.0.0"],
            ),
        )
        monkeypatch.setattr("s2dm.utils.download.requests.get", fail_download)

        response = test_client.post("/api/v1/deps/resolve", json=resolve_payload_factory())

        assert response.status_code == 502
        data = response.json()
        assert data["error"] == "DependencyUpstreamError"
        assert "Failed to download dependency asset 'metadata.yaml'" in data["message"]

    def test_resolve_dependencies_unexpected_failure_returns_500(
        self,
        crash_client: TestClient,
        monkeypatch: MonkeyPatch,
        resolve_payload_factory: ResolvePayloadFactory,
    ) -> None:
        def fail_unexpectedly(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("boom")

        monkeypatch.setattr(deps_route, "resolve_api_dependencies", fail_unexpectedly)

        response = crash_client.post("/api/v1/deps/resolve", json=resolve_payload_factory())

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "ServerError"
