from collections.abc import Callable
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

import s2dm.api.services.deps_service as deps_service
from s2dm.api.main import app

DependencySourceFactory = Callable[..., Path]
DependenciesConfigPayloadFactory = Callable[..., dict[str, object]]
IdentitiesPayloadFactory = Callable[[list[dict[str, str]]], dict[str, object]]
ResolvePayloadFactory = Callable[..., dict[str, bool]]


@pytest.fixture(autouse=True)
def api_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    workspace = tmp_path / "api-workspace"
    monkeypatch.setattr(deps_service, "get_api_workspace", lambda: workspace)
    return workspace


@pytest.fixture
def dependency_source_factory(tmp_path: Path) -> DependencySourceFactory:
    def create_source(
        directory_name: str,
        *,
        name: str,
        version: str,
        schema: str,
        metadata_id: str,
        preferred_prefix: str | None = None,
    ) -> Path:
        source_directory = tmp_path / directory_name
        source_directory.mkdir(parents=True, exist_ok=True)
        (source_directory / "schema.graphql").write_text(schema, encoding="utf-8")

        metadata_payload: dict[str, str] = {
            "name": name,
            "id": metadata_id,
            "version": version,
        }
        if preferred_prefix is not None:
            metadata_payload["preferred_prefix"] = preferred_prefix
        (source_directory / "metadata.yaml").write_text(
            yaml.safe_dump(metadata_payload, sort_keys=False),
            encoding="utf-8",
        )
        return source_directory

    return create_source


@pytest.fixture
def dependencies_config_payload_factory() -> DependenciesConfigPayloadFactory:
    def build_payload(
        sources: list[str | Path],
        *,
        names: list[str] | None = None,
        versions: list[str] | None = None,
        selections: list[dict[str, object] | None] | None = None,
    ) -> dict[str, object]:
        dependencies: list[dict[str, object]] = []
        for index, source in enumerate(sources):
            dependency_payload: dict[str, object] = {
                "name": names[index] if names is not None else "B",
                "version": versions[index] if versions is not None else "5.1.0",
                "source": str(source),
                "artifact": "schema.graphql",
            }
            if selections is not None:
                dependency_payload["selection"] = selections[index]
            dependencies.append(dependency_payload)
        return {"dependencies": dependencies}

    return build_payload


@pytest.fixture
def identities_payload_factory() -> IdentitiesPayloadFactory:
    def build_payload(identities: list[dict[str, str]]) -> dict[str, object]:
        return {"identities": identities}

    return build_payload


@pytest.fixture
def resolve_payload_factory() -> ResolvePayloadFactory:
    def build_payload(*, clean: bool = False) -> dict[str, bool]:
        return {"clean": clean}

    return build_payload


@pytest.fixture
def crash_client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)
