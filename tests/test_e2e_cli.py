import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from s2dm.cli import cli
from s2dm.tools.string import normalize_whitespace
from tests.conftest import TestSchemaData as TSD


@pytest.fixture(scope="module")
def runner() -> CliRunner:
    return CliRunner()


# Output files (will be created in a temp dir)
@pytest.fixture(scope="module")
def tmp_outputs(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("e2e_outputs")


class ExpectedIds:
    """Expected spec history IDs for the test cases.

    The IDs are based on the test data files.
    """

    VEHICLE_AVG_SPEED_ID = "0x2B6F41EE"  # schema1-1.graphql
    NEW_VEHICLE_AVG_SPEED_ID = "0x6002D5AD"  # schema1-2.graphql
    PERSON_HEIGHT_ID = "0xC3D633BB"  # schema1-1.graphql
    NEW_PERSON_HEIGHT_ID = "0xBB5A2DD0"  # schema1-2.graphql


def contains_value(obj: dict[str, Any] | list[Any] | str, target: str) -> bool:
    """Helper function to recursively search dicts"""
    if isinstance(obj, dict):
        for v in obj.values():
            if contains_value(v, target):
                return True
    elif isinstance(obj, list):
        for item in obj:
            if contains_value(item, target):
                return True
    else:
        return obj == target
    return False


# ToDo(DA): please update this test to do proper asserts for the shacl exporter
def test_export_shacl(runner: CliRunner, tmp_outputs: Path) -> None:
    out = tmp_outputs / "shacl.ttl"
    result = runner.invoke(
        cli, ["export", "shacl", "-s", str(TSD.SAMPLE1_1), "-s", str(TSD.SAMPLE1_2), "-o", str(out), "-f", "ttl"]
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    with open(out, encoding="utf-8") as f:
        content = f.read()

    assert "shapes:Vehicle" in content
    assert "shapes:Vehicle_ADAS_ObstacleDetection" in content


# ToDo(DA): please update this test to do proper asserts for the vspec exporter
def test_export_vspec(runner: CliRunner, tmp_outputs: Path) -> None:
    out = tmp_outputs / "vspec.yaml"
    result = runner.invoke(cli, ["export", "vspec", "-s", str(TSD.SAMPLE1_1), "-s", str(TSD.SAMPLE1_2), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()
    with open(out, encoding="utf-8") as f:
        content = f.read()

    assert "Vehicle:" in content
    assert "Vehicle_ADAS_ObstacleDetection:" in content


def test_generate_skos_skeleton(runner: CliRunner, tmp_outputs: Path) -> None:
    out = tmp_outputs / "skos_skeleton.ttl"
    result = runner.invoke(
        cli, ["generate", "skos-skeleton", "-s", str(TSD.SAMPLE1_1), "-s", str(TSD.SAMPLE1_2), "-o", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    with open(out, encoding="utf-8") as f:
        content = f.read()

    assert "@prefix skos:" in content
    assert "skos:Concept" in content
    assert "skos:prefLabel" in content

    assert "Vehicle" in content
    assert "Vehicle_ADAS_ObstacleDetection" in content


@pytest.mark.parametrize(
    "schema_file,previous_file,expected_output",
    [
        ([TSD.NO_CHANGE_SCHEMA], [TSD.BASE_SCHEMA], "No version bump needed"),
        ([TSD.NON_BREAKING_SCHEMA], [TSD.BASE_SCHEMA], "Patch version bump needed"),
        ([TSD.DANGEROUS_SCHEMA], [TSD.BASE_SCHEMA], "Minor version bump needed"),
        ([TSD.BREAKING_SCHEMA], [TSD.BASE_SCHEMA], "Detected breaking changes, major version bump needed"),
        # Keep original test cases for backward compatibility
        ([TSD.SAMPLE1_1, TSD.SAMPLE1_2], [TSD.SAMPLE1_1, TSD.SAMPLE1_2], "No version bump needed"),
        (
            [TSD.SAMPLE1_1, TSD.SAMPLE1_2],
            [TSD.SAMPLE2_1, TSD.SAMPLE2_2],
            "Detected breaking changes, major version bump needed",
        ),
    ],
)
def test_check_version_bump(
    runner: CliRunner, schema_file: list[Path], previous_file: list[Path], expected_output: str
) -> None:
    result = runner.invoke(
        cli,
        ["check", "version-bump"]
        + [item for schema in schema_file for item in ["-s", str(schema)]]
        + [item for previous in previous_file for item in ["--previous", str(previous)]],
    )
    assert result.exit_code == 0, result.output
    # Replace all newlines and additional spaces with a single space with regex
    assert expected_output.lower() in normalize_whitespace(result.output).lower()


@pytest.mark.parametrize(
    "schema_file,previous_file,expected_type",
    [
        (TSD.NO_CHANGE_SCHEMA, TSD.BASE_SCHEMA, "none"),
        (TSD.NON_BREAKING_SCHEMA, TSD.BASE_SCHEMA, "patch"),
        (TSD.DANGEROUS_SCHEMA, TSD.BASE_SCHEMA, "minor"),
        (TSD.BREAKING_SCHEMA, TSD.BASE_SCHEMA, "major"),
    ],
)
def test_check_version_bump_output_type(
    runner: CliRunner, schema_file: Path, previous_file: Path, expected_type: str
) -> None:
    result = runner.invoke(
        cli, ["check", "version-bump", "-s", str(schema_file), "--previous", str(previous_file), "--output-type"]
    )
    assert result.exit_code == 0, result.output
    # The output type should be the last line
    output_lines = result.output.strip().split("\n")
    assert output_lines[-1] == expected_type


# ToDo(DA): can you provide a negative example here?
@pytest.mark.parametrize(
    "input_file,expected_output",
    [
        ((TSD.SAMPLE1_1, TSD.SAMPLE1_2), "All constraints passed"),
    ],
)
def test_check_constraints(runner: CliRunner, input_file: tuple[Path, Path], expected_output: str) -> None:
    result = runner.invoke(cli, ["check", "constraints", "-s", str(input_file[0]), "-s", str(input_file[1])])
    assert expected_output.lower() in normalize_whitespace(result.output).lower()
    assert result.exit_code in (0, 1)


def test_validate_graphql(runner: CliRunner, tmp_outputs: Path) -> None:
    out = tmp_outputs / "validate.json"
    result = runner.invoke(
        cli, ["validate", "graphql", "-s", str(TSD.SAMPLE1_1), "-s", str(TSD.SAMPLE1_2), "-o", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    with open(out) as f:
        file_content = f.read()
    assert "Vehicle" in file_content
    assert "Person" in file_content


@pytest.mark.parametrize(
    "schemas,val_schemas,expected_output",
    [
        ((TSD.SAMPLE1_1, TSD.SAMPLE1_2), (TSD.SAMPLE1_1, TSD.SAMPLE1_2), "No changes detected"),
        ((TSD.SAMPLE1_1, TSD.SAMPLE1_2), (TSD.SAMPLE2_1, TSD.SAMPLE2_2), "Detected"),
    ],
)
def test_diff_graphql(
    runner: CliRunner,
    tmp_outputs: Path,
    schemas: tuple[Path, Path],
    val_schemas: tuple[Path, Path],
    expected_output: str,
) -> None:
    out = tmp_outputs / "diff.json"
    result = runner.invoke(
        cli,
        [
            "diff",
            "graphql",
            "-s",
            str(schemas[0]),
            "-s",
            str(schemas[1]),
            "--val-schema",
            str(val_schemas[0]),
            "--val-schema",
            str(val_schemas[1]),
            "-o",
            str(out),
        ],
    )
    assert out.exists()
    with open(out) as f:
        file_content = f.read()
    assert expected_output in file_content or expected_output in result.output


def test_registry_export_concept_uri(runner: CliRunner, tmp_outputs: Path) -> None:
    out = tmp_outputs / "concept_uris.json"
    result = runner.invoke(
        cli,
        [
            "registry",
            "concept-uri",
            "-s",
            str(TSD.SAMPLE1_1),
            "-s",
            str(TSD.SAMPLE1_2),
            "-o",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    with open(out) as f:
        data = json.load(f)

    assert isinstance(data, dict), "Expected JSON-LD output to be a dict."

    assert contains_value(
        data, "ns:Vehicle.averageSpeed"
    ), 'Expected value "ns:Vehicle.averageSpeed" not found in the concept URI output.'
    assert contains_value(
        data, "ns:Person.name"
    ), 'Expected value "ns:Person.name" not found in the concept URI output.'


def test_registry_export_id(runner: CliRunner, tmp_outputs: Path) -> None:
    out = tmp_outputs / "ids.json"
    result = runner.invoke(
        cli,
        [
            "registry",
            "id",
            "-s",
            str(TSD.SAMPLE1_1),
            "-s",
            str(TSD.SAMPLE1_2),
            "-o",
            str(out),
        ],
    )
    assert result.exit_code == 0, f"Expected exit code 0, but got {result.exit_code}."
    assert out.exists(), f"Expected output file {out} not found."
    with open(out) as f:
        data = json.load(f)
    assert any("Vehicle.averageSpeed" in k for k in data), "Expected 'Vehicle.averageSpeed' not found in the output."
    assert any("Person.name" in k for k in data), "Expected 'Person.name' not found in the output."


def test_registry_init(runner: CliRunner, tmp_outputs: Path) -> None:
    out = tmp_outputs / "spec_history.json"
    result = runner.invoke(
        cli, ["registry", "init", "-s", str(TSD.SAMPLE1_1), "-s", str(TSD.SAMPLE1_2), "-o", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    with open(out) as f:
        data = json.load(f)

    found_vehicle = False
    found_person = False
    entries = data if isinstance(data, list) else data.get("@graph") or data.get("items") or []
    for entry in entries:
        if isinstance(entry, dict):
            if entry.get("@id") == "ns:Vehicle.averageSpeed":
                spec_history = entry.get("specHistory", [])
                if (
                    spec_history
                    and isinstance(spec_history, list)
                    and isinstance(spec_history[0], dict)
                    and spec_history[0].get("@id") == ExpectedIds.VEHICLE_AVG_SPEED_ID
                ):
                    found_vehicle = True
            elif entry.get("@id") == "ns:Person.height":
                spec_history = entry.get("specHistory", [])
                if (
                    spec_history
                    and isinstance(spec_history, list)
                    and isinstance(spec_history[0], dict)
                    and spec_history[0].get("@id") == ExpectedIds.PERSON_HEIGHT_ID
                ):
                    found_person = True
        if found_vehicle and found_person:
            break
    assert found_vehicle, (
        'Expected entry with "@id": "ns:Vehicle.averageSpeed" and specHistory id'
        + f'"{ExpectedIds.VEHICLE_AVG_SPEED_ID}" not found.'
    )
    assert (
        found_person
    ), f'Expected entry with "@id": "ns:Person.height" and specHistory id "{ExpectedIds.PERSON_HEIGHT_ID}" not found.'


def test_registry_update(runner: CliRunner, tmp_outputs: Path) -> None:
    out = tmp_outputs / "spec_history_update.json"
    # First, create a spec history file
    init_out = tmp_outputs / "spec_history.json"
    runner.invoke(cli, ["registry", "init", "-s", str(TSD.SAMPLE1_1), "-s", str(TSD.SAMPLE1_2), "-o", str(init_out)])
    runner.invoke(
        cli,
        [
            "registry",
            "update",
            "-s",
            str(TSD.SAMPLE2_1),
            "-s",
            str(TSD.SAMPLE2_2),
            "-sh",
            str(init_out),
            "-o",
            str(out),
        ],
    )
    assert out.exists()
    with open(out) as f:
        data = json.load(f)
    found_vehicle_old = False
    found_vehicle_new = False
    found_person_old = False
    found_person_new = False
    entries = data if isinstance(data, list) else data.get("@graph") or data.get("items") or []
    for entry in entries:
        if isinstance(entry, dict):
            if entry.get("@id") == "ns:Vehicle.averageSpeed":
                spec_history = entry.get("specHistory", [])
                ids = [h.get("@id") for h in spec_history if isinstance(h, dict)]
                if ExpectedIds.VEHICLE_AVG_SPEED_ID in ids:
                    found_vehicle_old = True
                if ExpectedIds.NEW_VEHICLE_AVG_SPEED_ID in ids:
                    found_vehicle_new = True
            elif entry.get("@id") == "ns:Person.height":
                spec_history = entry.get("specHistory", [])
                ids = [h.get("@id") for h in spec_history if isinstance(h, dict)]
                if ExpectedIds.PERSON_HEIGHT_ID in ids:
                    found_person_old = True
                if ExpectedIds.NEW_PERSON_HEIGHT_ID in ids:
                    found_person_new = True
        if found_vehicle_old and found_vehicle_new and found_person_old and found_person_new:
            break
    assert (
        found_vehicle_old
    ), f'Expected old specHistory id "{ExpectedIds.VEHICLE_AVG_SPEED_ID}" for Vehicle.averageSpeed not found.'
    assert (
        found_vehicle_new
    ), f'Expected new specHistory id "{ExpectedIds.NEW_VEHICLE_AVG_SPEED_ID}" for Vehicle.averageSpeed not found.'
    assert (
        found_person_old
    ), f'Expected old specHistory id "{ExpectedIds.PERSON_HEIGHT_ID}" for Person.height not found.'
    assert (
        found_person_new
    ), f'Expected new specHistory id "{ExpectedIds.NEW_PERSON_HEIGHT_ID}" for Person.height not found.'


@pytest.mark.parametrize(
    "search_term,expected_output",
    [
        ("Vehicle", "Vehicle"),
        ("averageSpeed", "Vehicle: ['averageSpeed']"),
        ("id", "Vehicle: ['id']"),
        ("NonExistentType", "No matches found"),
        ("nonExistentField", "No matches found"),
    ],
)
def test_search_graphql(runner: CliRunner, search_term: str, expected_output: str) -> None:
    result = runner.invoke(
        cli, ["search", "graphql", "-s", str(TSD.SAMPLE1_1), "-s", str(TSD.SAMPLE1_2), "-t", search_term, "--exact"]
    )
    assert result.exit_code == 0, result.output
    assert expected_output.lower() in normalize_whitespace(result.output).lower()


def test_search_skos(runner: CliRunner, tmp_outputs: Path) -> None:
    skos_file = tmp_outputs / "test_skos.ttl"
    result = runner.invoke(
        cli, ["generate", "skos-skeleton", "-s", str(TSD.SAMPLE1_1), "-s", str(TSD.SAMPLE1_2), "-o", str(skos_file)]
    )
    assert result.exit_code == 0, result.output
    assert skos_file.exists()

    result = runner.invoke(cli, ["search", "skos", "-f", str(skos_file), "-t", "Vehicle"])
    assert result.exit_code == 0, result.output
    assert "Vehicle" in normalize_whitespace(result.output)

    result = runner.invoke(
        cli,
        ["search", "skos", "-f", str(skos_file), "-t", "vehicle", "--case-insensitive"],
    )
    assert result.exit_code == 0, result.output
    assert "Vehicle" in normalize_whitespace(result.output)

    result = runner.invoke(cli, ["search", "skos", "-f", str(skos_file), "-t", "NonExistentConcept"])
    assert result.exit_code == 0, result.output
    assert "No matches found" in normalize_whitespace(result.output)


@pytest.mark.parametrize(
    "search_term,expected_returncode,expected_output",
    [("Vehicle", 0, "Vehicle"), ("Seat", 1, "Type 'Seat' doesn't exist")],
)
def test_similar_graphql(
    runner: CliRunner, tmp_outputs: Path, search_term: str, expected_returncode: int, expected_output: str
) -> None:
    out = tmp_outputs / "similar.json"
    result = runner.invoke(
        cli,
        ["similar", "graphql", "-s", str(TSD.SAMPLE1_1), "-s", str(TSD.SAMPLE1_2), "-k", search_term, "-o", str(out)],
    )
    assert expected_returncode == result.exit_code, result.output
    assert expected_output in normalize_whitespace(result.output)
    assert out.exists()


def test_compose_graphql(runner: CliRunner, tmp_outputs: Path) -> None:
    out = tmp_outputs / "composed.graphql"
    result = runner.invoke(cli, ["compose", "-s", str(TSD.SAMPLE1_1), "-s", str(TSD.SAMPLE1_2), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()

    composed_content = out.read_text()
    assert "type Vehicle" in composed_content
    assert "type Vehicle_ADAS" in composed_content
    assert "type Vehicle_ADAS_ObstacleDetection" in composed_content
    assert "enum AccelerationUnitEnum" in composed_content
    assert "directive @range" in composed_content

    assert "Successfully composed schema" in normalize_whitespace(result.output)


def test_compose_graphql_with_root_type(runner: CliRunner, tmp_outputs: Path) -> None:
    out = tmp_outputs / "composed_filtered.graphql"
    result = runner.invoke(
        cli, ["compose", "-s", str(TSD.SAMPLE1_1), "-s", str(TSD.SAMPLE1_2), "-r", "Vehicle", "-o", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert out.exists()

    composed_content = out.read_text()
    assert "type Query" in composed_content

    assert "type Vehicle" in composed_content
    assert "type Vehicle_ADAS" in composed_content
    assert "Successfully composed schema with root type 'Vehicle'" in normalize_whitespace(result.output)

    assert "type Person" not in composed_content


def test_compose_graphql_with_root_type_nonexistent(runner: CliRunner, tmp_outputs: Path) -> None:
    out = tmp_outputs / "composed_error.graphql"
    result = runner.invoke(
        cli, ["compose", "-s", str(TSD.SAMPLE1_1), "-s", str(TSD.SAMPLE1_2), "-r", "NonExistentType", "-o", str(out)]
    )

    assert result.exit_code == 1
    assert not out.exists()
    assert "Root type 'NonExistentType' not found in schema" in normalize_whitespace(result.output)


def test_compose_graphql_root_type_filters_unreferenced_types(runner: CliRunner, tmp_outputs: Path) -> None:
    out = tmp_outputs / "composed_filtered.graphql"
    result = runner.invoke(
        cli, ["compose", "-s", str(TSD.SAMPLE1_1), "-s", str(TSD.SAMPLE1_2), "-r", "Vehicle_ADAS", "-o", str(out)]
    )
    assert result.exit_code == 0

    composed_content = out.read_text()

    assert "type Vehicle_ADAS" in composed_content
    assert "type Vehicle_ADAS_ABS" in composed_content

    assert "type Vehicle_Body" not in composed_content
    assert "type Vehicle_Occupant" not in composed_content
    assert "type InCabinArea2x2" not in composed_content


def test_compose_preserves_custom_directives(runner: CliRunner, tmp_outputs: Path) -> None:
    """Test that compose preserves all types of custom directives and formatting."""
    out = tmp_outputs / "directive_preservation_test.graphql"
    result = runner.invoke(cli, ["compose", "-s", str(TSD.SAMPLE1_1), "-s", str(TSD.SAMPLE1_2), "-o", str(out)])

    assert result.exit_code == 0, result.output
    assert out.exists()

    composed_content = out.read_text()

    assert "directive @range(min: Float, max: Float) on FIELD_DEFINITION" in composed_content
    assert "directive @cardinality(min: Int, max: Int) on FIELD_DEFINITION" in composed_content
    assert "directive @noDuplicates on FIELD_DEFINITION" in composed_content
    assert "directive @instanceTag on OBJECT" in composed_content

    assert "type Vehicle" in composed_content
    assert "type Vehicle_ADAS_ObstacleDetection" in composed_content


def test_compose_adds_reference_directives(runner: CliRunner, tmp_outputs: Path) -> None:
    """Test that compose adds @reference directives to track source files."""
    out = tmp_outputs / "reference_directives_test.graphql"
    result = runner.invoke(cli, ["compose", "-s", str(TSD.SAMPLE1_1), "-s", str(TSD.SAMPLE1_2), "-o", str(out)])

    assert result.exit_code == 0, result.output
    assert out.exists()

    composed_content = out.read_text()

    assert 'type Vehicle @reference(source: "schema1-1.graphql")' in composed_content
    assert 'type Vehicle_ADAS @reference(source: "schema1-1.graphql")' in composed_content
    assert 'enum Vehicle_ADAS_ActiveAutonomyLevel_Enum @reference(source: "schema1-1.graphql")' in composed_content

    assert 'type Vehicle_ADAS_ObstacleDetection @reference(source: "schema1-2.graphql")' in composed_content
    assert 'type Vehicle_Occupant @reference(source: "schema1-2.graphql")' in composed_content
    assert 'type Person @reference(uri: "http://example.com")' in composed_content

    assert 'type InCabinArea2x2 @instanceTag @reference(source: "S2DM Spec")' in composed_content


def test_compose_reference_directive_placement_after_other_directives(runner: CliRunner, tmp_outputs: Path) -> None:
    """Test that @reference directives are placed correctly after implements clause."""
    # Create test schema with implements clause
    test_schema_dir = tmp_outputs / "test_schemas"
    test_schema_dir.mkdir()

    schema_file = test_schema_dir / "test.graphql"
    schema_file.write_text("""
scalar DateTime

interface Node {
  id: ID!
}

interface Timestamped {
  createdAt: String
  updatedAt: String
}

type User implements Node {
  id: ID!
  name: String
}

type Admin implements Node & Timestamped @instanceTag {
  id: ID!
  role: String
  createdAt: String
  updatedAt: String
}

union Person = User | Admin
""")

    out = tmp_outputs / "implements_test.graphql"
    result = runner.invoke(cli, ["compose", "-s", str(schema_file), "-o", str(out)])

    assert result.exit_code == 0, result.output
    composed_content = out.read_text()

    assert 'type User implements Node @reference(source: "test.graphql")' in composed_content
    assert (
        'type Admin implements Node & Timestamped @instanceTag @reference(source: "test.graphql")' in composed_content
    )

    assert 'scalar DateTime @reference(source: "test.graphql")' in composed_content
    assert 'union Person @reference(source: "test.graphql")' in composed_content


# ToDo(DA): needs refactoring after final decision how stats will work
def test_stats_graphql(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["stats", "graphql", "-s", str(TSD.SAMPLE1_1), "-s", str(TSD.SAMPLE1_2)])
    print(f"{result.output=}")
    assert result.exit_code == 0, normalize_whitespace(result.output)
    assert '"UInt32": 1' in normalize_whitespace(result.output)


def test_units_sync_cli(
    runner: CliRunner,
    units_sync_mocks: tuple[Callable[..., list[Path]], Callable[[], str]],
) -> None:
    """Test that the units sync CLI command works end-to-end."""
    # Test basic CLI functionality
    result = runner.invoke(cli, ["units", "sync"])
    assert result.exit_code == 0, result.output
    assert "Generated" in normalize_whitespace(result.output) or "enum files" in normalize_whitespace(result.output)

    # Test that --dry-run flag is accepted (detailed behavior tested in unit tests)
    result = runner.invoke(cli, ["units", "sync", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert (
        "Would generate" in normalize_whitespace(result.output) or "dry" in normalize_whitespace(result.output).lower()
    )
