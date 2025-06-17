from pathlib import Path

import pytest

from s2dm.exporters.graphql_inspector import GraphQLInspector
from s2dm.exporters.utils import create_tempfile_to_composed_schema

DATA_DIR = Path(__file__).parent / "data"
SCHEMA1 = DATA_DIR / "schema1.graphql"
SCHEMA2 = DATA_DIR / "schema2.graphql"


@pytest.fixture(scope="module")
def schema1_tmp():
    assert SCHEMA1.exists(), f"Missing test file: {SCHEMA1}"
    tmp = create_tempfile_to_composed_schema(SCHEMA1)
    yield tmp
    if tmp.exists():
        tmp.unlink()


@pytest.fixture(scope="module")
def schema2_tmp():
    assert SCHEMA2.exists(), f"Missing test file: {SCHEMA2}"
    tmp = create_tempfile_to_composed_schema(SCHEMA2)
    yield tmp
    if tmp.exists():
        tmp.unlink()


def test_introspect(schema1_tmp):
    inspector = GraphQLInspector(schema1_tmp)
    result = inspector.introspect()
    assert isinstance(result, dict)
    assert "stdout" in result
    assert result["returncode"] == 0


def test_diff_no_changes(schema1_tmp):
    inspector = GraphQLInspector(schema1_tmp)
    result = inspector.diff(schema1_tmp)
    assert isinstance(result, dict)
    assert "stdout" in result
    assert result["returncode"] == 0
    assert "No changes detected" in result["stdout"]


def test_diff_with_changes(schema1_tmp, schema2_tmp):
    inspector = GraphQLInspector(schema1_tmp)
    result = inspector.diff(schema2_tmp)
    assert isinstance(result, dict)
    assert "stdout" in result
    assert "Detected" in result["stdout"] or "No changes detected" in result["stdout"]


def test_similar(schema1_tmp):
    inspector = GraphQLInspector(schema1_tmp)
    result = inspector.similar()
    assert isinstance(result, dict)
    assert "stdout" in result
    assert result["returncode"] == 0


# ToDo: add a test for validate if you have a query file
# def test_validate(schema1_tmp):
#     inspector = GraphQLInspector(schema1_tmp)
#     query_file = DATA_DIR / "query.graphql"
#     assert query_file.exists()
#     result = inspector.validate(str(query_file))
#     print(f"{result=}")
#     assert isinstance(result, dict)
#     assert "stdout" in result
#     assert result["returncode"] == 0
