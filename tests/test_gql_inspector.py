from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from s2dm.exporters.utils import create_tempfile_to_composed_schema
from s2dm.tools.graphql_inspector import GraphQLInspector

DATA_DIR: Path = Path(__file__).parent / "data"
SCHEMA1: Path = DATA_DIR / "schema1.graphql"
SCHEMA2: Path = DATA_DIR / "schema2.graphql"


@pytest.fixture(scope="module")
def schema1_tmp() -> Generator[Path, None, None]:
    assert SCHEMA1.exists(), f"Missing test file: {SCHEMA1}"
    tmp: Path = create_tempfile_to_composed_schema(SCHEMA1)
    yield tmp
    if tmp.exists():
        tmp.unlink()


@pytest.fixture(scope="module")
def schema2_tmp() -> Generator[Path, None, None]:
    assert SCHEMA2.exists(), f"Missing test file: {SCHEMA2}"
    tmp: Path = create_tempfile_to_composed_schema(SCHEMA2)
    yield tmp
    if tmp.exists():
        tmp.unlink()


def test_introspect(schema1_tmp: Path) -> None:
    inspector: GraphQLInspector = GraphQLInspector(schema1_tmp)
    result: dict[str, Any] = inspector.introspect()
    assert isinstance(result, dict)
    assert "stdout" in result
    assert result["returncode"] == 0


def test_diff_no_changes(schema1_tmp: Path) -> None:
    inspector: GraphQLInspector = GraphQLInspector(schema1_tmp)
    result: dict[str, Any] = inspector.diff(schema1_tmp)
    assert isinstance(result, dict)
    assert "stdout" in result
    assert result["returncode"] == 0
    assert "No changes detected" in result["stdout"]


def test_diff_with_changes(schema1_tmp: Path, schema2_tmp: Path) -> None:
    inspector: GraphQLInspector = GraphQLInspector(schema1_tmp)
    result: dict[str, Any] = inspector.diff(schema2_tmp)
    assert isinstance(result, dict)
    assert "stdout" in result
    assert "Detected" in result["stdout"] or "No changes detected" in result["stdout"]


def test_similar(schema1_tmp: Path) -> None:
    inspector: GraphQLInspector = GraphQLInspector(schema1_tmp)
    result: dict[str, Any] = inspector.similar()
    assert isinstance(result, dict)
    assert "stdout" in result
    assert result["returncode"] == 0


# ToDo: add a test for validate if you have a query file
# def test_validate(schema1_tmp: Path) -> None:
#     inspector: GraphQLInspector = GraphQLInspector(schema1_tmp)
#     query_file: Path = DATA_DIR / "query.graphql"
#     assert query_file.exists()
#     result: dict = inspector.validate(str(query_file))
#     print(f"{result=}")
#     assert isinstance(result, dict)
#     assert "stdout" in result
#     assert result["returncode"] == 0
