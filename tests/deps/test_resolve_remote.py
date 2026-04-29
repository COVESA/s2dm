from pathlib import Path
from unittest.mock import Mock, patch

import yaml

from s2dm.deps.models import DependencyConfig
from s2dm.deps.resolve.common import (
    DEFAULT_DEPS_CONFIG_FILENAME,
    DEPENDENCY_LOCK_FILENAME,
    METADATA_FILENAME,
    SCHEMA_FILENAME,
)
from s2dm.deps.resolve.resolve import resolve_dependencies
from tests.deps.helpers import load_yaml_file, write_dependency_config


def test_resolve_dependencies_from_remote_release(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    config_path = workspace / DEFAULT_DEPS_CONFIG_FILENAME
    write_dependency_config(config_path, "https://github.com/owner/repo", SCHEMA_FILENAME)

    schema_response = Mock()
    schema_response.raise_for_status = Mock()
    schema_response.headers = {}
    schema_response.content = b"type Query { ping: String }\n"

    metadata_response = Mock()
    metadata_response.raise_for_status = Mock()
    metadata_response.headers = {}
    metadata_response.content = yaml.safe_dump(
        {"name": "B", "id": "urn:test:B", "version": "5.1.0"},
        sort_keys=False,
    ).encode("utf-8")

    def mock_get(url: str, timeout: int) -> Mock:
        assert timeout == 30
        response = None
        if url == "https://github.com/owner/repo/releases/download/5.1.0/schema.graphql":
            response = schema_response
        if url == "https://github.com/owner/repo/releases/download/5.1.0/metadata.yaml":
            response = metadata_response
        if response is None:
            raise AssertionError(f"Unexpected URL requested: {url}")

        return response

    with patch("s2dm.utils.download.requests.get", side_effect=mock_get):
        lock_file = resolve_dependencies(DependencyConfig.load(config_path), workspace)

    lock_path = workspace / DEPENDENCY_LOCK_FILENAME
    lock_file.save(lock_path)

    lock_data = load_yaml_file(lock_path)
    dependencies = lock_data["dependencies"]
    assert isinstance(dependencies, list)
    dependency = dependencies[0]
    assert isinstance(dependency, dict)
    assert dependency["resolved_path"] == "https://github.com/owner/repo/releases/download/5.1.0/schema.graphql"


def test_resolve_dependencies_skips_remote_release_when_lock_and_vendor_exist(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    config_path = workspace / DEFAULT_DEPS_CONFIG_FILENAME
    write_dependency_config(config_path, "https://github.com/owner/repo", SCHEMA_FILENAME)

    vendored_directory = workspace / ".s2dm" / "vendor" / "B" / "5.1.0"
    vendored_directory.mkdir(parents=True)
    vendored_schema_path = vendored_directory / SCHEMA_FILENAME
    vendored_schema_path.write_text("type Query { cached: String }\n", encoding="utf-8")
    (vendored_directory / METADATA_FILENAME).write_text("name: stale\n", encoding="utf-8")
    (workspace / DEPENDENCY_LOCK_FILENAME).write_text(
        "dependencies:\n"
        "  - name: B\n"
        '    version: "5.1.0"\n'
        '    resolved_path: "https://github.com/owner/repo/releases/download/5.1.0/schema.graphql"\n'
        f'    integrity: "{"a" * 64}"\n',
        encoding="utf-8",
    )

    with patch("s2dm.utils.download.requests.get") as mock_get:
        lock_file = resolve_dependencies(DependencyConfig.load(config_path), workspace)

    mock_get.assert_not_called()
    lock_path = workspace / DEPENDENCY_LOCK_FILENAME
    lock_file.save(lock_path)

    lock_data = load_yaml_file(lock_path)
    dependencies = lock_data["dependencies"]
    assert isinstance(dependencies, list)
    dependency = dependencies[0]
    assert isinstance(dependency, dict)
    assert dependency["resolved_path"] == "https://github.com/owner/repo/releases/download/5.1.0/schema.graphql"
    assert vendored_schema_path.read_text(encoding="utf-8") == "type Query { cached: String }\n"
