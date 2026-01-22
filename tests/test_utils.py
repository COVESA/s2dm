from pathlib import Path
from typing import Any, cast

from graphql import parse
from graphql.type import GraphQLObjectType

from s2dm.exporters.utils import directive as directive_utils
from s2dm.exporters.utils import extraction as extraction_utils
from s2dm.exporters.utils import field as field_utils
from s2dm.exporters.utils import instance_tag as instance_tag_utils
from s2dm.exporters.utils import schema as schema_utils
from s2dm.exporters.utils import schema_loader as schema_loader_utils

# #########################################################
# Schema loader utils
# #########################################################


def test_build_schema_str(schema_path: list[Path]) -> None:
    schema_str: str = schema_loader_utils.build_schema_str(schema_path)
    assert isinstance(schema_str, str)
    assert "type" in schema_str


def test_load_schema(schema_path: list[Path]) -> None:
    schema = schema_loader_utils.load_schema(schema_path)
    assert hasattr(schema, "type_map")
    assert "Query" in schema.type_map


def test_load_schema_as_str(schema_path: list[Path]) -> None:
    schema_str: str = schema_loader_utils.load_schema_as_str(schema_path)
    assert isinstance(schema_str, str)
    assert "type Query" in schema_str


def test_create_tempfile_to_composed_schema(schema_path: list[Path]) -> None:
    temp_path: Path = schema_loader_utils.create_tempfile_to_composed_schema(schema_path)
    assert temp_path.exists()
    with open(temp_path) as f:
        content: str = f.read()
        assert "type Query" in content
    temp_path.unlink()


def test_ensure_query(schema_path: list[Path]) -> None:
    schema = schema_loader_utils.load_schema(schema_path)
    ensured = schema_loader_utils.ensure_query(schema)
    assert hasattr(ensured, "query_type")
    assert ensured.query_type is not None


def test_filter_schema(schema_path: list[Path]) -> None:
    schema = schema_loader_utils.load_schema(schema_path)

    root_type = "Vehicle"
    filtered_schema = schema_loader_utils.filter_schema(schema, root_type)

    assert root_type in filtered_schema.type_map
    assert filtered_schema.type_map[root_type] == schema.type_map[root_type]

    assert "Cabin" not in filtered_schema.type_map
    assert "Seat" not in filtered_schema.type_map


def test_prune_schema_using_query_selection(schema_path: list[Path]) -> None:
    schema = schema_loader_utils.load_schema(schema_path)

    query_str = """
    query {
        vehicle {
            isAutoPowerOptimize
            adas { abs { isEngaged } }
        }
    }
    """
    selection_query = parse(query_str)
    pruned_schema = schema_loader_utils.prune_schema_using_query_selection(schema, selection_query)

    assert "Vehicle" in pruned_schema.type_map
    assert "Vehicle_ADAS" in pruned_schema.type_map
    assert "Vehicle_ADAS_ABS" in pruned_schema.type_map

    vehicle_type = cast(GraphQLObjectType, pruned_schema.type_map["Vehicle"])
    assert "isAutoPowerOptimize" in vehicle_type.fields
    assert "adas" in vehicle_type.fields
    assert "averageSpeed" not in vehicle_type.fields
    assert "body" not in vehicle_type.fields

    adas_type = cast(GraphQLObjectType, pruned_schema.type_map["Vehicle_ADAS"])
    assert "abs" in adas_type.fields
    assert "activeAutonomyLevel" not in adas_type.fields

    abs_type = cast(GraphQLObjectType, pruned_schema.type_map["Vehicle_ADAS_ABS"])
    assert "isEngaged" in abs_type.fields
    assert "isError" not in abs_type.fields


# #########################################################
# Extraction utils
# #########################################################


def test_get_all_named_types(schema_path: list[Path]) -> None:
    schema = schema_loader_utils.load_schema(schema_path)
    named_types = extraction_utils.get_all_named_types(schema)
    assert any(t.name == "Query" for t in named_types)


def test_get_all_object_types(schema_path: list[Path]) -> None:
    schema = schema_loader_utils.load_schema(schema_path)
    object_types = extraction_utils.get_all_object_types(schema)
    assert any(o.name == "Query" for o in object_types)


def test_get_all_objects_with_directive(schema_path: list[Path]) -> None:
    schema = schema_loader_utils.load_schema(schema_path)
    object_types = extraction_utils.get_all_object_types(schema)
    result: list[Any] = extraction_utils.get_all_objects_with_directive(object_types, "instanceTag")
    assert isinstance(result, list)


# #########################################################
# Instance tag utils
# #########################################################


def test_expand_instance_tag_and_get_all_expanded_instance_tags(schema_path: list[Path]) -> None:
    schema = schema_loader_utils.load_schema(schema_path)
    tags: dict[GraphQLObjectType, list[str]] = instance_tag_utils.get_all_expanded_instance_tags(schema)
    assert isinstance(tags, dict)


def test_is_valid_instance_tag_field_and_has_valid_instance_tag_field(schema_path: list[Path]) -> None:
    schema = schema_loader_utils.load_schema(schema_path)
    object_types = extraction_utils.get_all_object_types(schema)
    for obj in object_types:
        for field in obj.fields.values():
            _ = instance_tag_utils.is_valid_instance_tag_field(field, schema)
            break
        break
    for obj in object_types:
        _ = instance_tag_utils.has_valid_instance_tag_field(obj, schema)
        break


def test_get_instance_tag_object_and_dict(schema_path: list[Path]) -> None:
    schema = schema_loader_utils.load_schema(schema_path)
    object_types = extraction_utils.get_all_object_types(schema)
    for obj in object_types:
        tag_obj = instance_tag_utils.get_instance_tag_object(obj, schema)
        if tag_obj:
            tag_dict: dict[str, list[str]] = instance_tag_utils.get_instance_tag_dict(tag_obj)
            assert isinstance(tag_dict, dict)
        break
    for obj in object_types:
        tag_obj = instance_tag_utils.get_instance_tag_object(obj, schema)
        if tag_obj:
            tag_dict = instance_tag_utils.get_instance_tag_dict(tag_obj)
            assert isinstance(tag_dict, dict)
        break


def test_expand_instances_in_schema() -> None:
    schema = schema_loader_utils.load_schema([Path("tests/test_expanded_instances/test_schema.graphql")])

    expanded_schema, _, _ = instance_tag_utils.expand_instances_in_schema(schema)

    assert "Door_Row" in expanded_schema.type_map
    assert "Door_Side" in expanded_schema.type_map
    assert "Seat_Row" in expanded_schema.type_map
    assert "Seat_Position" in expanded_schema.type_map

    door_row_type = cast(GraphQLObjectType, expanded_schema.type_map["Door_Row"])
    assert "ROW1" in door_row_type.fields
    assert "ROW2" in door_row_type.fields

    door_side_type = cast(GraphQLObjectType, expanded_schema.type_map["Door_Side"])
    assert "DRIVERSIDE" in door_side_type.fields
    assert "PASSENGERSIDE" in door_side_type.fields

    seat_row_type = cast(GraphQLObjectType, expanded_schema.type_map["Seat_Row"])
    assert "ROW1" in seat_row_type.fields
    assert "ROW2" in seat_row_type.fields
    assert "ROW3" in seat_row_type.fields

    seat_position_type = cast(GraphQLObjectType, expanded_schema.type_map["Seat_Position"])
    assert "LEFT" in seat_position_type.fields
    assert "CENTER" in seat_position_type.fields
    assert "RIGHT" in seat_position_type.fields

    cabin_type = cast(GraphQLObjectType, expanded_schema.type_map["Cabin"])
    assert "Door" in cabin_type.fields
    assert "doors" not in cabin_type.fields
    assert "Seat" in cabin_type.fields
    assert "seats" not in cabin_type.fields

    door_type = cast(GraphQLObjectType, expanded_schema.type_map["Door"])
    assert "instanceTag" not in door_type.fields
    seat_type = cast(GraphQLObjectType, expanded_schema.type_map["Seat"])
    assert "instanceTag" not in seat_type.fields


# #########################################################
# Directive utils
# #########################################################


def test_get_directive_arguments(schema_path: list[Path]) -> None:
    schema = schema_loader_utils.load_schema(schema_path)
    object_types = extraction_utils.get_all_object_types(schema)
    for obj in object_types:
        for field in obj.fields.values():
            args: dict[str, Any] = directive_utils.get_directive_arguments(field, "range")
            assert isinstance(args, dict)
            break
        break


def test_has_given_directive(schema_path: list[Path]) -> None:
    schema = schema_loader_utils.load_schema(schema_path)
    object_types = extraction_utils.get_all_object_types(schema)
    for obj in object_types:
        for field in obj.fields.values():
            _ = directive_utils.has_given_directive(field, "range")
            break
        break


# #########################################################
# Field utils
# #########################################################


def test_FieldCase_enum() -> None:
    assert field_utils.FieldCase.DEFAULT.value.description
    assert field_utils.FieldCase.NON_NULL.value.value_cardinality.min in (0, 1)


def test_get_field_case_and_extended(schema_path: list[Path]) -> None:
    schema = schema_loader_utils.load_schema(schema_path)
    object_types = extraction_utils.get_all_object_types(schema)
    for obj in object_types:
        for field in obj.fields.values():
            case = field_utils.get_field_case(field)
            assert isinstance(case, field_utils.FieldCase)
            ext_case = field_utils.get_field_case_extended(field)
            assert isinstance(ext_case, field_utils.FieldCase)
            break
        break


def test_print_field_sdl(schema_path: list[Path]) -> None:
    schema = schema_loader_utils.load_schema(schema_path)
    object_types = extraction_utils.get_all_object_types(schema)
    for obj in object_types:
        for field in obj.fields.values():
            sdl: str = field_utils.print_field_sdl(field)
            assert isinstance(sdl, str)
            break
        break


# #########################################################
# Schema utils
# #########################################################


def test_search_schema(schema_path: list[Path]) -> None:
    schema = schema_loader_utils.load_schema(schema_path)
    # Search for a type by name
    results = schema_utils.search_schema(schema, type_name="Vehicle", partial=True, case_insensitive=False)
    print(results)
    assert "Vehicle" in results
    assert any("averageSpeed" in fields for fields in results.values() if fields)
    # Search for a field by name (partial, case-insensitive)
    results_field = schema_utils.search_schema(schema, field_name="averagespeed", partial=True, case_insensitive=True)
    found = False
    for _tname, fields in results_field.items():
        if fields and any("averageSpeed".lower() in f.lower() for f in fields):
            found = True
    assert found
