import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from s2dm.cli import cli

TESTS_DATA = Path(__file__).parent / "data"
SAMPLE1 = TESTS_DATA / "schema1.graphql"
SAMPLE2 = TESTS_DATA / "schema2.graphql"
UNITS = TESTS_DATA / "test_units.yaml"

# Version bump test schemas
BASE_SCHEMA = TESTS_DATA / "base.graphql"
NO_CHANGE_SCHEMA = TESTS_DATA / "no-change.graphql"
NON_BREAKING_SCHEMA = TESTS_DATA / "non-breaking.graphql"
DANGEROUS_SCHEMA = TESTS_DATA / "dangerous.graphql"
BREAKING_SCHEMA = TESTS_DATA / "breaking.graphql"


@pytest.fixture(scope="module")
def runner() -> CliRunner:
    return CliRunner()


# Output files (will be created in a temp dir)
@pytest.fixture(scope="module")
def tmp_outputs(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("e2e_outputs")


def contains_value(obj: dict[str, Any], target: str) -> bool:
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
    result = runner.invoke(cli, ["export", "shacl", "-s", str(SAMPLE1), "-o", str(out), "-f", "ttl"])
    assert result.exit_code == 0, result.output
    assert out.exists()


# ToDo(DA): please update this test to do proper asserts for the vspec exporter
def test_export_vspec(runner: CliRunner, tmp_outputs: Path) -> None:
    out = tmp_outputs / "vspec.yaml"
    result = runner.invoke(cli, ["export", "vspec", "-s", str(SAMPLE1), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()


@pytest.mark.parametrize(
    "schema_file,previous_file,expected_output",
    [
        (NO_CHANGE_SCHEMA, BASE_SCHEMA, "No version bump needed"),
        (NON_BREAKING_SCHEMA, BASE_SCHEMA, "Patch version bump needed"),
        (DANGEROUS_SCHEMA, BASE_SCHEMA, "Minor version bump needed"),
        (BREAKING_SCHEMA, BASE_SCHEMA, "Detected breaking changes, major version bump needed"),
        # Keep original test cases for backward compatibility
        (SAMPLE1, SAMPLE1, "No version bump needed"),
        (SAMPLE1, SAMPLE2, "Detected breaking changes, major version bump needed"),
    ],
)
def test_check_version_bump(runner: CliRunner, schema_file: Path, previous_file: Path, expected_output: str) -> None:
    result = runner.invoke(cli, ["check", "version-bump", "-s", str(schema_file), "--previous", str(previous_file)])
    assert result.exit_code == 0, result.output
    assert expected_output.lower() in result.output.lower()


@pytest.mark.parametrize(
    "schema_file,previous_file,expected_type",
    [
        (NO_CHANGE_SCHEMA, BASE_SCHEMA, "none"),
        (NON_BREAKING_SCHEMA, BASE_SCHEMA, "patch"),
        (DANGEROUS_SCHEMA, BASE_SCHEMA, "minor"),
        (BREAKING_SCHEMA, BASE_SCHEMA, "major"),
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
        (SAMPLE1, "All constraints passed"),
    ],
)
def test_check_constraints(runner: CliRunner, input_file: Path, expected_output: str) -> None:
    result = runner.invoke(cli, ["check", "constraints", "-s", str(input_file)])
    assert expected_output.lower() in result.output.lower()
    assert result.exit_code in (0, 1)


def test_validate_graphql(runner: CliRunner, tmp_outputs: Path) -> None:
    out = tmp_outputs / "validate.json"
    result = runner.invoke(cli, ["validate", "graphql", "-s", str(SAMPLE1), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()
    with open(out) as f:
        file_content = f.read()
    assert "Vehicle" in file_content


@pytest.mark.parametrize(
    "input_files,expected_output",
    [
        ((SAMPLE1, SAMPLE1), "No changes detected"),
        ((SAMPLE1, SAMPLE2), "Detected"),
    ],
)
def test_diff_graphql(
    runner: CliRunner, tmp_outputs: Path, input_files: tuple[Path, Path], expected_output: str
) -> None:
    out = tmp_outputs / f"diff_{input_files[0].stem}_{input_files[1].stem}.json"
    result = runner.invoke(
        cli, ["diff", "graphql", "-s", str(input_files[0]), "--val-schema", str(input_files[1]), "-o", str(out)]
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
            str(SAMPLE1),
            "-o",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    with open(out) as f:
        data = json.load(f)

    assert isinstance(data, dict), "Expected JSON-LD output to be a dict."

    # Recursively search for the value 'ns:Vehicle.averageSpeed' in the output
    assert contains_value(
        data, "ns:Vehicle.averageSpeed"
    ), 'Expected value "ns:Vehicle.averageSpeed" not found in the concept URI output.'


def test_registry_export_id(runner: CliRunner, tmp_outputs: Path) -> None:
    out = tmp_outputs / "ids.json"
    result = runner.invoke(
        cli,
        [
            "registry",
            "id",
            "-s",
            str(SAMPLE1),
            "-u",
            str(UNITS),
            "-o",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    with open(out) as f:
        data = json.load(f)

    assert any("Vehicle.averageSpeed" in k for k in data)


def test_registry_init(runner: CliRunner, tmp_outputs: Path) -> None:
    out = tmp_outputs / "spec_history.json"
    result = runner.invoke(cli, ["registry", "init", "-s", str(SAMPLE1), "-u", str(UNITS), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()
    with open(out) as f:
        data = json.load(f)
    found = False
    # The output may be a dict with a list under a key, or a list directly
    entries = data if isinstance(data, list) else data.get("@graph") or data.get("items") or []
    for entry in entries:
        if isinstance(entry, dict) and entry.get("@id") == "ns:Vehicle.averageSpeed":
            spec_history = entry.get("specHistory", [])
            if (
                spec_history
                and isinstance(spec_history, list)
                and isinstance(spec_history[0], dict)
                and spec_history[0].get("@id") == "0xEC20D822"
            ):
                found = True
                break
    assert found, 'Expected entry with "@id": "ns:Vehicle.averageSpeed" and specHistory id "0xEC20D822" not found.'


def test_registry_update(runner: CliRunner, tmp_outputs: Path) -> None:
    out = tmp_outputs / "spec_history_update.json"
    # First, create a spec history file
    init_out = tmp_outputs / "spec_history.json"
    runner.invoke(cli, ["registry", "init", "-s", str(SAMPLE1), "-u", str(UNITS), "-o", str(init_out)])
    runner.invoke(
        cli, ["registry", "update", "-s", str(SAMPLE2), "-u", str(UNITS), "-sh", str(init_out), "-o", str(out)]
    )
    assert out.exists()
    with open(out) as f:
        data = json.load(f)
    found_old = False
    found_new = False
    # New IDs are always appended to the specHistory entry
    entries = data if isinstance(data, list) else data.get("@graph") or data.get("items") or []
    for entry in entries:
        if isinstance(entry, dict) and entry.get("@id") == "ns:Vehicle.averageSpeed":
            spec_history = entry.get("specHistory", [])
            ids = [h.get("@id") for h in spec_history if isinstance(h, dict)]
            if "0xEC20D822" in ids:
                found_old = True
            if "0xB86BF561" in ids:
                found_new = True
            break
    assert found_old, 'Expected old specHistory id "0xEC20D822" not found.'
    assert found_new, 'Expected new specHistory id "0xB86BF561" not found.'


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
    result = runner.invoke(cli, ["search", "graphql", "-s", str(SAMPLE1), "-t", search_term, "--exact"])
    assert result.exit_code == 0, result.output
    assert expected_output.lower() in result.output.lower()


@pytest.mark.parametrize(
    "search_term,expected_returncode,expected_output",
    [("Vehicle", 0, "Vehicle"), ("Seat", 1, "Type 'Seat' doesn't exist")],
)
def test_similar_graphql(
    runner: CliRunner, tmp_outputs: Path, search_term: str, expected_returncode: int, expected_output: str
) -> None:
    out = tmp_outputs / "similar.json"
    result = runner.invoke(cli, ["similar", "graphql", "-s", str(SAMPLE1), "-k", search_term, "-o", str(out)])
    assert expected_returncode == result.exit_code, result.output
    assert expected_output in result.output
    assert out.exists()


# ToDo(DA): needs refactoring after final decision how stats will work
def test_stats_graphql(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["stats", "graphql", "-s", str(SAMPLE1)])
    print(f"{result.output=}")
    assert result.exit_code == 0, result.output
    assert "'UInt32': 1" in result.output
