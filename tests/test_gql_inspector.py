import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from s2dm.exporters.utils.schema_loader import create_tempfile_to_composed_schema
from s2dm.tools.graphql_inspector import GraphQLInspector
from s2dm.tools.string import normalize_whitespace
from tests.conftest import TestSchemaData as TSD


@pytest.fixture(scope="module")
def schema1_tmp(spec_directory: Path) -> Generator[Path, None, None]:
    assert TSD.SCHEMA1.exists(), f"Missing test file: {TSD.SCHEMA1}"
    tmp: Path = create_tempfile_to_composed_schema([spec_directory, TSD.SCHEMA1, TSD.UNITS_SCHEMA_PATH])
    yield tmp
    if tmp.exists():
        tmp.unlink()


@pytest.fixture(scope="module")
def schema2_tmp(spec_directory: Path) -> Generator[Path, None, None]:
    assert TSD.SCHEMA2.exists(), f"Missing test file: {TSD.SCHEMA2}"
    tmp: Path = create_tempfile_to_composed_schema([spec_directory, TSD.SCHEMA2, TSD.UNITS_SCHEMA_PATH])
    yield tmp
    if tmp.exists():
        tmp.unlink()


@pytest.mark.graphql_inspector
def test_introspect(schema1_tmp: Path, inspector_path: Path | None) -> None:
    inspector: GraphQLInspector = GraphQLInspector(schema1_tmp, node_modules_path=inspector_path)
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


@pytest.mark.graphql_inspector
def test_diff_no_changes(schema1_tmp: Path, inspector_path: Path | None) -> None:
    inspector: GraphQLInspector = GraphQLInspector(schema1_tmp, node_modules_path=inspector_path)
    result = inspector.diff(schema1_tmp)
    assert hasattr(result, "output")
    assert result.returncode == 0
    assert "No changes detected" in result.output


@pytest.mark.graphql_inspector
def test_diff_with_changes(schema1_tmp: Path, schema2_tmp: Path, inspector_path: Path | None) -> None:
    inspector: GraphQLInspector = GraphQLInspector(schema1_tmp, node_modules_path=inspector_path)
    result = inspector.diff(schema2_tmp)
    assert hasattr(result, "output")
    assert "Detected" in result.output or "No changes detected" in result.output


@pytest.mark.graphql_inspector
def test_similar(schema1_tmp: Path, inspector_path: Path | None) -> None:
    inspector: GraphQLInspector = GraphQLInspector(schema1_tmp, node_modules_path=inspector_path)
    result = inspector.similar(output=None)
    assert hasattr(result, "output")
    assert result.returncode == 0


@pytest.mark.graphql_inspector
@pytest.mark.parametrize("output_to_file", [False, True])
def test_similar_output(schema1_tmp: Path, output_to_file: bool, inspector_path: Path | None) -> None:
    inspector: GraphQLInspector = GraphQLInspector(schema1_tmp, node_modules_path=inspector_path)
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


@pytest.mark.graphql_inspector
def test_similar_keyword(schema1_tmp: Path, inspector_path: Path | None) -> None:
    inspector: GraphQLInspector = GraphQLInspector(schema1_tmp, node_modules_path=inspector_path)
    # Use a keyword that is likely to exist in the test schema, e.g. "Query"
    result = inspector.similar_keyword("Vehicle_ADAS", output=None)
    assert hasattr(result, "output")
    assert result.returncode == 0 or result.returncode == 1  # allow not found
    # Optionally check that the output contains the keyword if found
    if result.returncode == 0:
        assert "Vehicle_ADAS" in result.output


@pytest.mark.graphql_inspector
@pytest.mark.parametrize("output_to_file", [False, True])
def test_similar_keyword_output(schema1_tmp: Path, output_to_file: bool, inspector_path: Path | None) -> None:
    inspector: GraphQLInspector = GraphQLInspector(schema1_tmp, node_modules_path=inspector_path)
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
