from pathlib import Path
from typing import Any

import pytest
from graphql.type import GraphQLObjectType

from s2dm.exporters import utils

DATA_DIR: Path = Path(__file__).parent / "data"
SCHEMA1: Path = DATA_DIR / "schema1.graphql"


@pytest.fixture(scope="module")
def schema_path() -> Path:
    assert SCHEMA1.exists(), f"Missing test file: {SCHEMA1}"
    return SCHEMA1


def test_read_file(schema_path: Path) -> None:
    content: str = utils.read_file(schema_path)
    assert isinstance(content, str)
    assert "type" in content


def test_build_schema_str(schema_path: Path) -> None:
    schema_str: str = utils.build_schema_str(schema_path)
    assert isinstance(schema_str, str)
    assert "type" in schema_str


def test_load_schema(schema_path: Path) -> None:
    schema = utils.load_schema(schema_path)
    assert hasattr(schema, "type_map")
    assert "Query" in schema.type_map


def test_load_schema_as_str(schema_path: Path) -> None:
    schema_str: str = utils.load_schema_as_str(schema_path)
    assert isinstance(schema_str, str)
    assert "type Query" in schema_str


def test_create_tempfile_to_composed_schema(schema_path: Path) -> None:
    temp_path: Path = utils.create_tempfile_to_composed_schema(schema_path)
    assert temp_path.exists()
    with open(temp_path) as f:
        content: str = f.read()
        assert "type Query" in content
    temp_path.unlink()


def test_ensure_query(schema_path: Path) -> None:
    schema = utils.load_schema(schema_path)
    ensured = utils.ensure_query(schema)
    assert hasattr(ensured, "query_type")
    assert ensured.query_type is not None


def test_get_all_named_types(schema_path: Path) -> None:
    schema = utils.load_schema(schema_path)
    named_types = utils.get_all_named_types(schema)
    assert any(t.name == "Query" for t in named_types)


def test_get_all_object_types(schema_path: Path) -> None:
    schema = utils.load_schema(schema_path)
    object_types = utils.get_all_object_types(schema)
    assert any(o.name == "Query" for o in object_types)


def test_get_all_objects_with_directive(schema_path: Path) -> None:
    schema = utils.load_schema(schema_path)
    object_types = utils.get_all_object_types(schema)
    result: list[Any] = utils.get_all_objects_with_directive(object_types, "instanceTag")
    assert isinstance(result, list)


def test_expand_instance_tag_and_get_all_expanded_instance_tags(schema_path: Path) -> None:
    schema = utils.load_schema(schema_path)
    tags: dict[GraphQLObjectType, list[str]] = utils.get_all_expanded_instance_tags(schema)
    assert isinstance(tags, dict)


def test_get_directive_arguments(schema_path: Path) -> None:
    schema = utils.load_schema(schema_path)
    object_types = utils.get_all_object_types(schema)
    for obj in object_types:
        for field in obj.fields.values():
            args: dict[str, Any] = utils.get_directive_arguments(field, "range")
            assert isinstance(args, dict)
            break
        break


def test_FieldCase_enum() -> None:
    assert utils.FieldCase.DEFAULT.value.description
    assert utils.FieldCase.NON_NULL.value.value_cardinality.min in (0, 1)


def test_get_field_case_and_extended(schema_path: Path) -> None:
    schema = utils.load_schema(schema_path)
    object_types = utils.get_all_object_types(schema)
    for obj in object_types:
        for field in obj.fields.values():
            case = utils.get_field_case(field)
            assert isinstance(case, utils.FieldCase)
            ext_case = utils.get_field_case_extended(field)
            assert isinstance(ext_case, utils.FieldCase)
            break
        break


def test_has_directive(schema_path: Path) -> None:
    schema = utils.load_schema(schema_path)
    object_types = utils.get_all_object_types(schema)
    for obj in object_types:
        for field in obj.fields.values():
            _ = utils.has_directive(field, "range")
            break
        break


def test_print_field_sdl(schema_path: Path) -> None:
    schema = utils.load_schema(schema_path)
    object_types = utils.get_all_object_types(schema)
    for obj in object_types:
        for field in obj.fields.values():
            sdl: str = utils.print_field_sdl(field)
            assert isinstance(sdl, str)
            break
        break


def test_is_valid_instance_tag_field_and_has_valid_instance_tag_field(schema_path: Path) -> None:
    schema = utils.load_schema(schema_path)
    object_types = utils.get_all_object_types(schema)
    for obj in object_types:
        for field in obj.fields.values():
            _ = utils.is_valid_instance_tag_field(field, schema)
            break
        break
    for obj in object_types:
        _ = utils.has_valid_instance_tag_field(obj, schema)
        break


def test_get_instance_tag_object_and_dict(schema_path: Path) -> None:
    schema = utils.load_schema(schema_path)
    object_types = utils.get_all_object_types(schema)
    for obj in object_types:
        tag_obj = utils.get_instance_tag_object(obj, schema)
        if tag_obj:
            tag_dict: dict[str, list[str]] = utils.get_instance_tag_dict(tag_obj)
            assert isinstance(tag_dict, dict)
        break
    for obj in object_types:
        tag_obj = utils.get_instance_tag_object(obj, schema)
        if tag_obj:
            tag_dict = utils.get_instance_tag_dict(tag_obj)
            assert isinstance(tag_dict, dict)
        break


def test_search_schema(schema_path: Path) -> None:
    schema = utils.load_schema(schema_path)
    # Search for a type by name
    results = utils.search_schema(schema, type_name="Vehicle", partial=True, case_insensitive=False)
    print(results)
    assert "Vehicle" in results
    assert any("averageSpeed" in fields for fields in results.values() if fields)
    # Search for a field by name (partial, case-insensitive)
    results_field = utils.search_schema(schema, field_name="averagespeed", partial=True, case_insensitive=True)
    found = False
    for _tname, fields in results_field.items():
        if fields and any("averageSpeed".lower() in f.lower() for f in fields):
            found = True
    assert found
