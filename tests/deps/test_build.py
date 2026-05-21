from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from s2dm.cli import cli
from s2dm.deps.compose import (
    DependencySchemaBuilder,
    DependencySchemaInput,
)
from s2dm.deps.models import DependencyMetadata
from tests.deps.helpers import write_metadata_file


def test_find_conflicts_reports_duplicate_type_with_dependency_metadata() -> None:
    dependency_schema_contents = [
        DependencySchemaInput(
            schema_content="type Query { vehicle: Vehicle }\ntype Vehicle { vin: String }\n",
            metadata=DependencyMetadata(name="BodyModel", id="urn:test:body", version="1.0.0"),
        ),
        DependencySchemaInput(
            schema_content="type Vehicle { speed: Float }\ntype Powertrain { vehicle: Vehicle }\n",
            metadata=DependencyMetadata(name="PowertrainModel", id="urn:test:powertrain", version="2.0.0"),
        ),
    ]

    conflicts = DependencySchemaBuilder(dependency_schema_contents).find_conflicts()

    assert len(conflicts) == 1
    assert conflicts[0].type_name == "Vehicle"
    assert _dependency_labels(conflicts[0].dependencies_metadata) == {"BodyModel@1.0.0", "PowertrainModel@2.0.0"}


def test_type_extensions_do_not_create_type_name_conflicts() -> None:
    dependency_schema_contents = [
        DependencySchemaInput(
            schema_content="type Vehicle { vin: String }\n",
            metadata=DependencyMetadata(name="BaseModel", id="urn:test:base", version="1.0.0"),
        ),
        DependencySchemaInput(
            schema_content="extend type Vehicle { speed: Float }\n",
            metadata=DependencyMetadata(name="ExtensionModel", id="urn:test:extension", version="1.0.0"),
        ),
    ]

    conflicts = DependencySchemaBuilder(dependency_schema_contents).find_conflicts()

    assert conflicts == ()


def test_auto_prefix_renames_conflicting_type_definitions_and_references() -> None:
    dependency_schema_contents = [
        DependencySchemaInput(
            schema_content="type BodyCatalog { vehicle: Vehicle }\ntype Vehicle { vin: String }\n",
            metadata=DependencyMetadata(name="BodyModel", id="urn:test:body", version="1.0.0", preferred_prefix="body"),
        ),
        DependencySchemaInput(
            schema_content="type PowertrainCatalog { vehicle: Vehicle }\ntype Vehicle { speed: Float }\n",
            metadata=DependencyMetadata(
                name="PowertrainModel", id="urn:test:powertrain", version="2.0.0", preferred_prefix="powertrain"
            ),
        ),
    ]

    schema_content = _write_auto_prefixed_schema_content(dependency_schema_contents)

    assert "type body_Vehicle" in schema_content
    assert "type powertrain_Vehicle" in schema_content
    assert "vehicle: body_Vehicle" in schema_content
    assert "vehicle: powertrain_Vehicle" in schema_content


def test_auto_prefix_fails_when_prefixed_type_names_collide() -> None:
    dependency_schema_contents = [
        DependencySchemaInput(
            schema_content="type Vehicle { vin: String }\n",
            metadata=DependencyMetadata(
                name="BodyModel", id="urn:test:body", version="1.0.0", preferred_prefix="vehicle"
            ),
        ),
        DependencySchemaInput(
            schema_content="type Vehicle { speed: Float }\ntype vehicle_Vehicle { id: ID }\n",
            metadata=DependencyMetadata(
                name="PowertrainModel", id="urn:test:powertrain", version="2.0.0", preferred_prefix="powertrain"
            ),
        ),
    ]

    with pytest.raises(ValueError, match="Auto-prefix produced duplicate type definitions: vehicle_Vehicle"):
        DependencySchemaBuilder(dependency_schema_contents).write_auto_prefixed_schema_files()


def test_auto_prefix_keeps_no_conflict_schema_unchanged() -> None:
    dependency_schema_contents = [
        DependencySchemaInput(
            schema_content="type Vehicle { vin: String }\n",
            metadata=DependencyMetadata(name="BodyModel", id="urn:test:body", version="1.0.0"),
        ),
        DependencySchemaInput(
            schema_content="type Powertrain { speed: Float }\n",
            metadata=DependencyMetadata(name="PowertrainModel", id="urn:test:powertrain", version="2.0.0"),
        ),
    ]

    schema_content = _write_auto_prefixed_schema_content(dependency_schema_contents)

    assert "type Vehicle" in schema_content
    assert "type Powertrain" in schema_content
    assert "body_" not in schema_content
    assert "powertrain_" not in schema_content


_CONFLICTING_DEPENDENCIES = (
    {
        "name": "BodyModel",
        "version": "1.0.0",
        "id": "urn:test:body",
        "preferred_prefix": "body",
        "schema": "type BodyCatalog { vehicle: Vehicle }\ntype Vehicle { vin: String }\n",
    },
    {
        "name": "PowertrainModel",
        "version": "2.0.0",
        "id": "urn:test:powertrain",
        "preferred_prefix": "powertrain",
        "schema": "type PowertrainCatalog { vehicle: Vehicle }\ntype Vehicle { speed: Float }\n",
    },
)


@pytest.fixture
def conflicting_workspace() -> Iterator[tuple[CliRunner, Path]]:
    runner = CliRunner()
    with runner.isolated_filesystem():
        working_directory = Path.cwd()
        config_entries: list[dict[str, str]] = []
        for dep in _CONFLICTING_DEPENDENCIES:
            source = (working_directory / "sources" / dep["name"]).resolve()
            config_entries.append(
                {"name": dep["name"], "version": dep["version"], "source": str(source), "artifact": "schema.graphql"}
            )
            vendor_directory = working_directory / ".s2dm" / "vendor" / dep["name"] / dep["version"]
            vendor_directory.mkdir(parents=True)
            (vendor_directory / "schema.graphql").write_text(dep["schema"], encoding="utf-8")
            write_metadata_file(
                vendor_directory / "metadata.yaml",
                name=dep["name"],
                id=dep["id"],
                version=dep["version"],
                preferred_prefix=dep["preferred_prefix"],
            )
        (working_directory / "s2dm.deps.yaml").write_text(
            yaml.safe_dump({"dependencies": config_entries}), encoding="utf-8"
        )
        yield runner, working_directory / "composed.graphql"


def test_deps_build_without_auto_prefix_fails_on_conflicts(
    conflicting_workspace: tuple[CliRunner, Path],
) -> None:
    runner, output_path = conflicting_workspace

    result = runner.invoke(cli, ["deps", "build", "-o", str(output_path)])

    assert result.exit_code == 1, result.output
    assert not output_path.exists()


def test_deps_build_auto_prefix_writes_composed_schema_for_conflicts(
    conflicting_workspace: tuple[CliRunner, Path],
) -> None:
    runner, output_path = conflicting_workspace

    result = runner.invoke(cli, ["deps", "build", "--auto-prefix", "-o", str(output_path)])

    assert result.exit_code == 0, result.output
    composed_schema = output_path.read_text(encoding="utf-8")
    assert "type body_Vehicle" in composed_schema
    assert "type powertrain_Vehicle" in composed_schema
    assert "vehicle: body_Vehicle" in composed_schema


def _dependency_labels(dependencies_metadata: tuple[DependencyMetadata, ...]) -> set[str]:
    return {
        f"{dependency_metadata.name}@{dependency_metadata.version}" for dependency_metadata in dependencies_metadata
    }


def _write_auto_prefixed_schema_content(dependency_schema_contents: list[DependencySchemaInput]) -> str:
    schema_paths = DependencySchemaBuilder(dependency_schema_contents).write_auto_prefixed_schema_files()
    return "\n".join(schema_path.read_text(encoding="utf-8") for schema_path in schema_paths)
