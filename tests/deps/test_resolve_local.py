from pathlib import Path

import pytest

from s2dm.deps.models import DependencyConfig
from s2dm.deps.resolve.common import (
    DEFAULT_DEPS_CONFIG_FILENAME,
    DEPENDENCY_LOCK_FILENAME,
    METADATA_FILENAME,
    SCHEMA_FILENAME,
)
from s2dm.deps.resolve.resolve import resolve_dependencies
from tests.deps.helpers import create_archive, load_yaml_file, write_dependency_config, write_metadata_file


def test_resolve_dependencies_from_local_graphql(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    source_directory = tmp_path / "source"
    source_directory.mkdir()
    source_schema_path = source_directory / SCHEMA_FILENAME
    source_schema_path.write_text("type Query { ping: String }\n", encoding="utf-8")
    write_metadata_file(source_directory / METADATA_FILENAME)

    config_path = workspace / DEFAULT_DEPS_CONFIG_FILENAME
    write_dependency_config(config_path, str(source_directory.resolve()), SCHEMA_FILENAME)

    lock_file = resolve_dependencies(DependencyConfig.load(config_path), workspace)
    lock_path = workspace / DEPENDENCY_LOCK_FILENAME
    lock_file.save(lock_path)

    vendored_directory = workspace / ".s2dm" / "vendor" / "B" / "5.1.0"
    assert (vendored_directory / SCHEMA_FILENAME).read_text(encoding="utf-8") == source_schema_path.read_text(
        encoding="utf-8"
    )
    assert (vendored_directory / METADATA_FILENAME).exists()
    assert lock_path == workspace / DEPENDENCY_LOCK_FILENAME

    lock_data = load_yaml_file(lock_path)
    dependencies = lock_data["dependencies"]
    assert isinstance(dependencies, list)
    dependency = dependencies[0]
    assert isinstance(dependency, dict)
    assert dependency["name"] == "B"
    assert dependency["version"] == "5.1.0"
    assert dependency["resolved_path"] == str(source_schema_path.resolve())
    assert len(str(dependency["integrity"])) == 64


def test_resolve_dependencies_overwrites_incomplete_vendor_target_with_lock(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / SCHEMA_FILENAME).write_text("type Query { ping: String }\n", encoding="utf-8")
    write_metadata_file(source_directory / METADATA_FILENAME)

    config_path = workspace / DEFAULT_DEPS_CONFIG_FILENAME
    write_dependency_config(config_path, str(source_directory.resolve()), SCHEMA_FILENAME)

    vendored_directory = workspace / ".s2dm" / "vendor" / "B" / "5.1.0"
    vendored_directory.mkdir(parents=True)
    (vendored_directory / SCHEMA_FILENAME).write_text("type Query { stale: String }\n", encoding="utf-8")
    (workspace / DEPENDENCY_LOCK_FILENAME).write_text(
        "dependencies:\n"
        "  - name: B\n"
        '    version: "5.1.0"\n'
        f'    resolved_path: "{(source_directory / SCHEMA_FILENAME).resolve()}"\n'
        f'    integrity: "{"a" * 64}"\n',
        encoding="utf-8",
    )

    resolve_dependencies(DependencyConfig.load(config_path), workspace)

    assert (vendored_directory / SCHEMA_FILENAME).read_text(encoding="utf-8") == "type Query { ping: String }\n"
    assert (vendored_directory / METADATA_FILENAME).exists()


@pytest.mark.parametrize("artifact_name", ["bundle.zip", "bundle.tar", "bundle.tar.gz"])
def test_resolve_dependencies_from_local_archive(
    tmp_path: Path,
    artifact_name: str,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    source_directory = tmp_path / "source"
    source_directory.mkdir()
    archive_path = source_directory / artifact_name
    create_archive(archive_path)

    config_path = workspace / DEFAULT_DEPS_CONFIG_FILENAME
    write_dependency_config(config_path, str(source_directory.resolve()), artifact_name)

    resolve_dependencies(DependencyConfig.load(config_path), workspace)

    vendored_directory = workspace / ".s2dm" / "vendor" / "B" / "5.1.0"
    assert (vendored_directory / SCHEMA_FILENAME).exists()
    assert (vendored_directory / METADATA_FILENAME).exists()


def test_resolve_dependencies_fails_for_non_fixed_schema_name(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "model.graphql").write_text("type Query { ping: String }\n", encoding="utf-8")
    write_metadata_file(source_directory / METADATA_FILENAME)

    config_path = workspace / DEFAULT_DEPS_CONFIG_FILENAME
    write_dependency_config(config_path, str(source_directory.resolve()), "model.graphql")

    with pytest.raises(ValueError):
        resolve_dependencies(DependencyConfig.load(config_path), workspace)


def test_resolve_dependencies_fails_for_version_mismatch(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / SCHEMA_FILENAME).write_text("type Query { ping: String }\n", encoding="utf-8")
    write_metadata_file(source_directory / METADATA_FILENAME, version="5.2.0")

    config_path = workspace / DEFAULT_DEPS_CONFIG_FILENAME
    write_dependency_config(config_path, str(source_directory.resolve()), SCHEMA_FILENAME, version="5.1.0")

    with pytest.raises(ValueError):
        resolve_dependencies(DependencyConfig.load(config_path), workspace)
