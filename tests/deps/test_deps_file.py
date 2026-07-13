from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from s2dm.deps.models import DependencyConfig, RemoteIdentityConfig
from s2dm.deps.resolve.common import SCHEMA_FILENAME


def test_dependency_config_rejects_duplicate_dependency_targets(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        DependencyConfig.model_validate(
            {
                "dependencies": [
                    {
                        "name": "B",
                        "version": "5.1.0",
                        "source": str(tmp_path),
                        "artifact": SCHEMA_FILENAME,
                    },
                    {
                        "name": "B",
                        "version": "5.1.0",
                        "source": str(tmp_path),
                        "artifact": SCHEMA_FILENAME,
                    },
                ]
            }
        )


def test_dependency_config_allows_same_name_with_different_versions(tmp_path: Path) -> None:
    dependency_config = DependencyConfig.model_validate(
        {
            "dependencies": [
                {
                    "name": "B",
                    "version": "5.1.0",
                    "source": str(tmp_path),
                    "artifact": SCHEMA_FILENAME,
                },
                {
                    "name": "B",
                    "version": "5.2.0",
                    "source": str(tmp_path),
                    "artifact": SCHEMA_FILENAME,
                },
            ]
        }
    )

    assert len(dependency_config.dependencies) == 2


def test_dependency_config_allows_canonical_remote_repository_root_urls() -> None:
    dependency_config = DependencyConfig.model_validate(
        {
            "dependencies": [
                {
                    "name": "B",
                    "version": "5.1.0",
                    "source": "https://github.com/owner/repo",
                    "artifact": SCHEMA_FILENAME,
                },
                {
                    "name": "C",
                    "version": "5.1.0",
                    "source": "https://example.ghe.com/owner/repo/",
                    "artifact": SCHEMA_FILENAME,
                },
            ]
        }
    )

    assert len(dependency_config.dependencies) == 2


@pytest.mark.parametrize(
    "source",
    [
        "https://github.com/owner/repo.git",
        "https://github.com/owner/repo/tree/main",
        "https://github.com/owner/repo/issues",
        "https://github.com/owner",
        "https://github.com/owner/repo?ref=main",
        "https://github.com/owner/repo#readme",
    ],
)
def test_dependency_config_rejects_non_root_remote_repository_urls(source: str) -> None:
    with pytest.raises(ValidationError):
        DependencyConfig.model_validate(
            {
                "dependencies": [
                    {
                        "name": "B",
                        "version": "5.1.0",
                        "source": source,
                        "artifact": SCHEMA_FILENAME,
                    }
                ]
            }
        )


def test_dependency_config_load_resolves_relative_selection_path(tmp_path: Path) -> None:
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    selection_directory = tmp_path / "queries"
    selection_directory.mkdir()
    selection_path = selection_directory / "selection.graphql"
    selection_path.write_text("query Selection { ping }\n", encoding="utf-8")

    config_path = tmp_path / "configs" / "s2dm.deps.yaml"
    config_path.parent.mkdir()
    config_path.write_text(
        yaml.safe_dump(
            {
                "dependencies": [
                    {
                        "name": "B",
                        "version": "5.1.0",
                        "source": str(source_directory.resolve()),
                        "artifact": SCHEMA_FILENAME,
                        "selection": "../queries/selection.graphql",
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    dependency_config = DependencyConfig.load(config_path)

    assert dependency_config.dependencies[0].selection == selection_path.resolve()


def test_dependency_config_load_rejects_missing_relative_selection_path(tmp_path: Path) -> None:
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    config_path = tmp_path / "configs" / "s2dm.deps.yaml"
    config_path.parent.mkdir()
    config_path.write_text(
        yaml.safe_dump(
            {
                "dependencies": [
                    {
                        "name": "B",
                        "version": "5.1.0",
                        "source": str(source_directory.resolve()),
                        "artifact": SCHEMA_FILENAME,
                        "selection": "../queries/missing.graphql",
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError) as exc_info:
        DependencyConfig.load(config_path)

    assert any(error["loc"] == ("dependencies", 0, "selection") for error in exc_info.value.errors())


@pytest.mark.parametrize("name", ["demo-package", "Demo.Package", "demo_package", "A1"])
def test_dependency_config_allows_pep503_style_names(name: str, tmp_path: Path) -> None:
    dependency_config = DependencyConfig.model_validate(
        {
            "dependencies": [
                {
                    "name": name,
                    "version": "1.0.0",
                    "source": str(tmp_path),
                    "artifact": SCHEMA_FILENAME,
                }
            ]
        }
    )

    assert dependency_config.dependencies[0].name == name


@pytest.mark.parametrize("name", ["demo package", "@demo", "demo/package"])
def test_dependency_config_rejects_invalid_dependency_names(name: str, tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        DependencyConfig.model_validate(
            {
                "dependencies": [
                    {
                        "name": name,
                        "version": "1.0.0",
                        "source": str(tmp_path),
                        "artifact": SCHEMA_FILENAME,
                    }
                ]
            }
        )


def test_dependency_config_allows_plus_in_version(tmp_path: Path) -> None:
    dependency_config = DependencyConfig.model_validate(
        {
            "dependencies": [
                {
                    "name": "DemoPackage",
                    "version": "1.0.0+build.1",
                    "source": str(tmp_path),
                    "artifact": SCHEMA_FILENAME,
                }
            ]
        }
    )

    assert dependency_config.dependencies[0].version == "1.0.0+build.1"


@pytest.mark.parametrize("version", ["1.0.0 release", "release/1.0.0"])
def test_dependency_config_rejects_invalid_dependency_versions(version: str, tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        DependencyConfig.model_validate(
            {
                "dependencies": [
                    {
                        "name": "DemoPackage",
                        "version": version,
                        "source": str(tmp_path),
                        "artifact": SCHEMA_FILENAME,
                    }
                ]
            }
        )


def test_dependency_identity_config_allows_empty_identities() -> None:
    identity_config = RemoteIdentityConfig.model_validate({"identities": []})

    assert identity_config.identities == []


def test_dependency_identity_config_rejects_host_with_scheme() -> None:
    with pytest.raises(ValidationError):
        RemoteIdentityConfig.model_validate(
            {
                "identities": [
                    {
                        "host": "https://github.com",
                        "token": "test-token",
                    }
                ]
            }
        )


def test_dependency_identity_config_rejects_host_with_path() -> None:
    with pytest.raises(ValidationError):
        RemoteIdentityConfig.model_validate(
            {
                "identities": [
                    {
                        "host": "github.com/owner/repo",
                        "token": "test-token",
                    }
                ]
            }
        )


def test_dependency_identity_config_rejects_duplicate_host_wide_entries() -> None:
    with pytest.raises(ValidationError):
        RemoteIdentityConfig.model_validate(
            {
                "identities": [
                    {
                        "host": "github.com",
                        "token": "token-a",
                    },
                    {
                        "host": "github.com",
                        "token": "token-b",
                    },
                ]
            }
        )


def test_dependency_identity_config_rejects_duplicate_scoped_entries() -> None:
    with pytest.raises(ValidationError):
        RemoteIdentityConfig.model_validate(
            {
                "identities": [
                    {
                        "host": "github.com",
                        "scope": "owner/repo",
                        "token": "token-a",
                    },
                    {
                        "host": "github.com",
                        "scope": "owner/repo",
                        "token": "token-b",
                    },
                ]
            }
        )


def test_dependency_identity_config_allows_host_wide_and_scoped_entries() -> None:
    identity_config = RemoteIdentityConfig.model_validate(
        {
            "identities": [
                {
                    "host": "github.com",
                    "token": "token-a",
                },
                {
                    "host": "github.com",
                    "scope": "owner/repo",
                    "token": "token-b",
                },
            ]
        }
    )

    assert len(identity_config.identities) == 2


def test_dependency_identity_config_allows_distinct_scoped_entries() -> None:
    identity_config = RemoteIdentityConfig.model_validate(
        {
            "identities": [
                {
                    "host": "github.com",
                    "scope": "owner/repo-a",
                    "token": "token-a",
                },
                {
                    "host": "github.com",
                    "scope": "owner/repo-b",
                    "token": "token-b",
                },
            ]
        }
    )

    assert len(identity_config.identities) == 2
