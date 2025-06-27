import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from s2dm.cli import cli

TESTS_DATA = Path(__file__).parent / "data"
SAMPLE1 = TESTS_DATA / "schema1.graphql"
SAMPLE2 = TESTS_DATA / "schema2.graphql"
UNITS = TESTS_DATA / "test_units.yaml"


@pytest.fixture(scope="module")
def runner() -> CliRunner:
    return CliRunner()


# Output files (will be created in a temp dir)
@pytest.fixture(scope="module")
def tmp_outputs(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("e2e_outputs")


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
    "input_files,expected_output",
    [
        ((SAMPLE1, SAMPLE1), "No version bump needed"),
        ((SAMPLE1, SAMPLE2), "Major version bump"),
    ],
)
def test_check_version_bump(runner: CliRunner, input_files: tuple[Path, Path], expected_output: str) -> None:
    result = runner.invoke(cli, ["check", "version-bump", "-s", str(input_files[0]), "--previous", str(input_files[1])])
    assert result.exit_code == 0, result.output
    assert expected_output.lower() in result.output.lower()


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
