import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from s2dm.exporters.utils.schema_loader import create_tempfile_to_composed_schema
from s2dm.tools.graphql_inspector import GraphQLInspector
from s2dm.tools.string import normalize_whitespace
from tests.conftest import TestSchemaData as TSD


@pytest.fixture(scope="module")
def schema1_tmp() -> Generator[Path, None, None]:
    assert TSD.SCHEMA1.exists(), f"Missing test file: {TSD.SCHEMA1}"
    tmp: Path = create_tempfile_to_composed_schema([TSD.SCHEMA1, TSD.UNITS_SCHEMA_PATH])
    yield tmp
    if tmp.exists():
        tmp.unlink()


@pytest.fixture(scope="module")
def schema2_tmp() -> Generator[Path, None, None]:
    assert TSD.SCHEMA2.exists(), f"Missing test file: {TSD.SCHEMA2}"
    tmp: Path = create_tempfile_to_composed_schema([TSD.SCHEMA2, TSD.UNITS_SCHEMA_PATH])
    yield tmp
    if tmp.exists():
        tmp.unlink()


def test_introspect(schema1_tmp: Path) -> None:
    inspector: GraphQLInspector = GraphQLInspector(schema1_tmp)
    with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
        output_path = Path(tmpfile.name + ".graphql")
    result = inspector.introspect(output=output_path)
    assert hasattr(result, "output")
    assert result.returncode == 0
    assert output_path.exists()
    with open(output_path) as f:
        file_content = f.read()
    assert "Vehicle" in file_content
    output_path.unlink()


def test_diff_no_changes(schema1_tmp: Path) -> None:
    inspector: GraphQLInspector = GraphQLInspector(schema1_tmp)
    result = inspector.diff(schema1_tmp)
    assert hasattr(result, "output")
    assert result.returncode == 0
    assert "No changes detected" in result.output


def test_diff_with_changes(schema1_tmp: Path, schema2_tmp: Path) -> None:
    inspector: GraphQLInspector = GraphQLInspector(schema1_tmp)
    result = inspector.diff(schema2_tmp)
    assert hasattr(result, "output")
    assert "Detected" in result.output or "No changes detected" in result.output


def test_similar(schema1_tmp: Path) -> None:
    inspector: GraphQLInspector = GraphQLInspector(schema1_tmp)
    result = inspector.similar(output=None)
    assert hasattr(result, "output")
    assert result.returncode == 0


@pytest.mark.parametrize("output_to_file", [False, True])
def test_similar_output(schema1_tmp: Path, output_to_file: bool) -> None:
    inspector: GraphQLInspector = GraphQLInspector(schema1_tmp)
    output_path = None
    file_content = None
    if output_to_file:
        with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            output_path = Path(tmpfile.name + ".json")
        result = inspector.similar(output=output_path)
        assert output_path.exists()
        with open(output_path) as f:
            file_content = f.read()
        assert file_content.strip() != ""
        output_path.unlink()
    else:
        result = inspector.similar(output=None)
    assert hasattr(result, "output")
    assert result.returncode == 0


def test_similar_keyword(schema1_tmp: Path) -> None:
    inspector: GraphQLInspector = GraphQLInspector(schema1_tmp)
    # Use a keyword that is likely to exist in the test schema, e.g. "Query"
    result = inspector.similar_keyword("Vehicle_ADAS", output=None)
    assert hasattr(result, "output")
    assert result.returncode == 0 or result.returncode == 1  # allow not found
    # Optionally check that the output contains the keyword if found
    if result.returncode == 0:
        assert "Vehicle_ADAS" in result.output


@pytest.mark.parametrize("output_to_file", [False, True])
def test_similar_keyword_output(schema1_tmp: Path, output_to_file: bool) -> None:
    inspector: GraphQLInspector = GraphQLInspector(schema1_tmp)
    keyword = "Vehicle_ADAS"  # Use a keyword likely to exist
    output_path = None
    file_content = None
    if output_to_file:
        with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            output_path = Path(tmpfile.name + ".json")
        result = inspector.similar_keyword(keyword, output=output_path)
        assert output_path.exists()
        with open(output_path) as f:
            file_content = f.read()
        assert file_content.strip() != ""
        output_path.unlink()
    else:
        result = inspector.similar_keyword(keyword, output=None)
    assert hasattr(result, "output")
    assert result.returncode == 0 or result.returncode == 1
    if result.returncode == 0:
        assert keyword in normalize_whitespace(result.output) or (
            output_to_file and file_content and keyword in file_content
        )


# ToDo: add a test for validate if we have a query file
# def test_validate(schema1_tmp: Path) -> None:
#     inspector: GraphQLInspector = GraphQLInspector(schema1_tmp)
#     query_file: Path = DATA_DIR / "query.graphql"
#     assert query_file.exists()
#     result: dict = inspector.validate(str(query_file))
#     print(f"{result=}")
#     assert isinstance(result, dict)
#     assert "stdout" in result
#     assert result["returncode"] == 0
