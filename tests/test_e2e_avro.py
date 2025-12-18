"""End-to-end integration tests for Avro export with expanded instances."""

import json
from pathlib import Path
from typing import cast

import pytest
from graphql import DocumentNode

from s2dm.exporters.avro import translate_to_avro_schema
from s2dm.exporters.utils.schema_loader import load_and_process_schema


class TestAvroE2EExpandedInstances:
    @pytest.fixture
    def test_schema_path(self) -> list[Path]:
        """Path to the test GraphQL schema."""
        return [Path(__file__).parent / "test_expanded_instances" / "test_schema.graphql"]

    def test_expanded_instances_default(self, test_schema_path: list[Path], tmp_path: Path) -> None:
        """Test that instance tags are NOT expanded by default (treated as regular types)."""
        query_file = tmp_path / "selection.graphql"
        query_file.write_text("query Selection { cabin { seats { isOccupied } doors { isLocked } temperature } }")

        root_type = "Cabin"
        annotated_schema, _, selection_query = load_and_process_schema(
            schema_paths=test_schema_path,
            naming_config_path=None,
            selection_query_path=query_file,
            root_type=root_type,
            expanded_instances=False,
        )
        result = translate_to_avro_schema(annotated_schema, "com.example", cast(DocumentNode, selection_query))
        result_dict = json.loads(result)

        assert result_dict["name"] == "Selection"
        assert result_dict["type"] == "record"
        assert result_dict["namespace"] == "com.example"

        cabin_field = result_dict["fields"][0]
        assert cabin_field["name"] == "cabin"
        assert cabin_field["type"][0] == "null"

        cabin_record = cabin_field["type"][1]
        assert cabin_record["type"] == "record"
        assert cabin_record["name"] == "Cabin"
        assert len(cabin_record["fields"]) == 3

        seats_field = cabin_record["fields"][0]
        assert seats_field["name"] == "seats"
        assert seats_field["type"][0] == "null"
        seats_array = seats_field["type"][1]
        assert seats_array["type"] == "array"

        seat_record = seats_array["items"][1]
        assert seat_record["type"] == "record"
        assert seat_record["name"] == "Seat"

        doors_field = cabin_record["fields"][1]
        assert doors_field["name"] == "doors"
        assert doors_field["type"][0] == "null"
        doors_array = doors_field["type"][1]
        assert doors_array["type"] == "array"

        door_record = doors_array["items"][1]
        assert door_record["type"] == "record"
        assert door_record["name"] == "Door"

        temperature_field = cabin_record["fields"][2]
        assert temperature_field["name"] == "temperature"
        assert temperature_field["type"] == ["null", "double"]

        assert "Seat_Row" not in result
        assert "Seat_Position" not in result
        assert "Door_Row" not in result
        assert "Door_Side" not in result

    def test_expanded_instances(self, test_schema_path: list[Path], tmp_path: Path) -> None:
        """Test that instance tags are expanded into nested structures when enabled."""
        query_file = tmp_path / "selection.graphql"
        query_file.write_text(
            "query Selection { cabin { seats { isOccupied height } doors { isLocked position } temperature } }"
        )

        root_type = "Cabin"
        annotated_schema, _, selection_query = load_and_process_schema(
            schema_paths=test_schema_path,
            naming_config_path=None,
            selection_query_path=query_file,
            root_type=root_type,
            expanded_instances=True,
        )
        result = translate_to_avro_schema(annotated_schema, "com.example", cast(DocumentNode, selection_query))
        result_dict = json.loads(result)

        assert result_dict["name"] == "Selection"
        assert result_dict["type"] == "record"
        assert result_dict["namespace"] == "com.example"

        cabin_field = result_dict["fields"][0]
        assert cabin_field["name"] == "cabin"
        assert isinstance(cabin_field["type"], list)
        assert cabin_field["type"][0] == "null"

        cabin_record = cabin_field["type"][1]
        assert isinstance(cabin_record, dict)
        assert cabin_record["type"] == "record"
        assert cabin_record["name"] == "Cabin"
        assert cabin_record["namespace"] == "com.example"
        assert len(cabin_record["fields"]) == 3

        temperature_field = cabin_record["fields"][0]
        assert temperature_field["name"] == "temperature"
        assert temperature_field["type"] == ["null", "double"]

        seat_field = cabin_record["fields"][1]
        assert seat_field["name"] == "Seat"
        seat_row_type = seat_field["type"]
        assert isinstance(seat_row_type, dict)
        assert seat_row_type["type"] == "record"
        assert seat_row_type["name"] == "Seat_Row"
        assert seat_row_type["namespace"] == "com.example"
        assert len(seat_row_type["fields"]) == 3

        for idx, row_name in enumerate(["ROW1", "ROW2", "ROW3"]):
            row_field = seat_row_type["fields"][idx]
            assert row_field["name"] == row_name

            if idx == 0:
                seat_position_type = row_field["type"]
                assert isinstance(seat_position_type, dict)
                assert seat_position_type["type"] == "record"
                assert seat_position_type["name"] == "Seat_Position"
                assert seat_position_type["namespace"] == "com.example"
                assert len(seat_position_type["fields"]) == 3

                for pos_idx, position_name in enumerate(["LEFT", "CENTER", "RIGHT"]):
                    position_field = seat_position_type["fields"][pos_idx]
                    assert position_field["name"] == position_name
                    assert isinstance(position_field["type"], list)
                    assert position_field["type"][0] == "null"

                    seat_type = position_field["type"][1]
                    if pos_idx == 0:
                        assert isinstance(seat_type, dict)
                        assert seat_type["type"] == "record"
                        assert seat_type["name"] == "Seat"
                        assert seat_type["namespace"] == "com.example"
                        assert len(seat_type["fields"]) == 2
                        assert seat_type["fields"][0]["name"] == "isOccupied"
                        assert seat_type["fields"][0]["type"] == ["null", "boolean"]
                        assert seat_type["fields"][1]["name"] == "height"
                        assert seat_type["fields"][1]["type"] == ["null", "int"]
                    else:
                        assert seat_type == "com.example.Seat"
            else:
                assert row_field["type"] == "com.example.Seat_Position"

        door_field = cabin_record["fields"][2]
        assert door_field["name"] == "Door"
        door_row_type = door_field["type"]
        assert isinstance(door_row_type, dict)
        assert door_row_type["type"] == "record"
        assert door_row_type["name"] == "Door_Row"
        assert door_row_type["namespace"] == "com.example"
        assert len(door_row_type["fields"]) == 2

        for idx, row_name in enumerate(["ROW1", "ROW2"]):
            door_row_field = door_row_type["fields"][idx]
            assert door_row_field["name"] == row_name

            if idx == 0:
                door_side_type = door_row_field["type"]
                assert isinstance(door_side_type, dict)
                assert door_side_type["type"] == "record"
                assert door_side_type["name"] == "Door_Side"
                assert door_side_type["namespace"] == "com.example"
                assert len(door_side_type["fields"]) == 2

                for side_idx, side_name in enumerate(["DRIVERSIDE", "PASSENGERSIDE"]):
                    side_field = door_side_type["fields"][side_idx]
                    assert side_field["name"] == side_name
                    assert isinstance(side_field["type"], list)
                    assert side_field["type"][0] == "null"

                    door_type = side_field["type"][1]
                    if side_idx == 0:
                        assert isinstance(door_type, dict)
                        assert door_type["type"] == "record"
                        assert door_type["name"] == "Door"
                        assert door_type["namespace"] == "com.example"
                        assert len(door_type["fields"]) == 2
                        assert door_type["fields"][0]["name"] == "isLocked"
                        assert door_type["fields"][0]["type"] == ["null", "boolean"]
                        assert door_type["fields"][1]["name"] == "position"
                        assert door_type["fields"][1]["type"] == ["null", "int"]
                    else:
                        assert door_type == "com.example.Door"
            else:
                assert door_row_field["type"] == "com.example.Door_Side"

    def test_expanded_instances_with_naming_config(self, test_schema_path: list[Path], tmp_path: Path) -> None:
        """Test that naming config is applied to expanded instance field names."""
        naming_config = {"field": {"object": "MACROCASE"}}
        naming_config_file = tmp_path / "naming_config.json"
        naming_config_file.write_text(json.dumps(naming_config))

        query_file = tmp_path / "selection.graphql"
        query_file.write_text(
            "query Selection { cabin { seats { isOccupied height } doors { isLocked position } temperature } }"
        )

        root_type = "Cabin"
        annotated_schema, _, selection_query = load_and_process_schema(
            schema_paths=test_schema_path,
            naming_config_path=naming_config_file,
            selection_query_path=query_file,
            root_type=root_type,
            expanded_instances=True,
        )
        result = translate_to_avro_schema(annotated_schema, "com.example", cast(DocumentNode, selection_query))
        result_dict = json.loads(result)

        assert result_dict["name"] == "Selection"
        assert result_dict["type"] == "record"
        assert result_dict["namespace"] == "com.example"

        cabin_field = result_dict["fields"][0]
        assert cabin_field["name"] == "cabin"
        assert isinstance(cabin_field["type"], list)
        assert cabin_field["type"][0] == "null"

        cabin_record = cabin_field["type"][1]
        assert isinstance(cabin_record, dict)
        assert cabin_record["type"] == "record"
        assert cabin_record["name"] == "Cabin"
        assert cabin_record["namespace"] == "com.example"
        assert len(cabin_record["fields"]) == 3

        temperature_field = cabin_record["fields"][0]
        assert temperature_field["name"] == "TEMPERATURE"
        assert temperature_field["type"] == ["null", "double"]

        seat_field = cabin_record["fields"][1]
        assert seat_field["name"] == "SEAT"
        seat_row_type = seat_field["type"]
        assert isinstance(seat_row_type, dict)
        assert seat_row_type["type"] == "record"
        assert seat_row_type["name"] == "Seat_Row"
        assert seat_row_type["namespace"] == "com.example"
        assert len(seat_row_type["fields"]) == 3

        for idx, row_name in enumerate(["ROW1", "ROW2", "ROW3"]):
            row_field = seat_row_type["fields"][idx]
            assert row_field["name"] == row_name

            if idx == 0:
                seat_position_type = row_field["type"]
                assert isinstance(seat_position_type, dict)
                assert seat_position_type["type"] == "record"
                assert seat_position_type["name"] == "Seat_Position"
                assert seat_position_type["namespace"] == "com.example"
                assert len(seat_position_type["fields"]) == 3

                for pos_idx, position_name in enumerate(["LEFT", "CENTER", "RIGHT"]):
                    position_field = seat_position_type["fields"][pos_idx]
                    assert position_field["name"] == position_name
                    assert isinstance(position_field["type"], list)
                    assert position_field["type"][0] == "null"

                    seat_type = position_field["type"][1]
                    if pos_idx == 0:
                        assert isinstance(seat_type, dict)
                        assert seat_type["type"] == "record"
                        assert seat_type["name"] == "Seat"
                        assert seat_type["namespace"] == "com.example"
                        assert len(seat_type["fields"]) == 2
                        assert seat_type["fields"][0]["name"] == "IS_OCCUPIED"
                        assert seat_type["fields"][0]["type"] == ["null", "boolean"]
                        assert seat_type["fields"][1]["name"] == "HEIGHT"
                        assert seat_type["fields"][1]["type"] == ["null", "int"]
                    else:
                        assert seat_type == "com.example.Seat"
            else:
                assert row_field["type"] == "com.example.Seat_Position"

        door_field = cabin_record["fields"][2]
        assert door_field["name"] == "DOOR"
        door_row_type = door_field["type"]
        assert isinstance(door_row_type, dict)
        assert door_row_type["type"] == "record"
        assert door_row_type["name"] == "Door_Row"
        assert door_row_type["namespace"] == "com.example"
        assert len(door_row_type["fields"]) == 2

        for idx, row_name in enumerate(["ROW1", "ROW2"]):
            door_row_field = door_row_type["fields"][idx]
            assert door_row_field["name"] == row_name

            if idx == 0:
                door_side_type = door_row_field["type"]
                assert isinstance(door_side_type, dict)
                assert door_side_type["type"] == "record"
                assert door_side_type["name"] == "Door_Side"
                assert door_side_type["namespace"] == "com.example"
                assert len(door_side_type["fields"]) == 2

                for side_idx, side_name in enumerate(["DRIVERSIDE", "PASSENGERSIDE"]):
                    side_field = door_side_type["fields"][side_idx]
                    assert side_field["name"] == side_name
                    assert isinstance(side_field["type"], list)
                    assert side_field["type"][0] == "null"

                    door_type = side_field["type"][1]
                    if side_idx == 0:
                        assert isinstance(door_type, dict)
                        assert door_type["type"] == "record"
                        assert door_type["name"] == "Door"
                        assert door_type["namespace"] == "com.example"
                        assert len(door_type["fields"]) == 2
                        assert door_type["fields"][0]["name"] == "IS_LOCKED"
                        assert door_type["fields"][0]["type"] == ["null", "boolean"]
                        assert door_type["fields"][1]["name"] == "POSITION"
                        assert door_type["fields"][1]["type"] == ["null", "int"]
                    else:
                        assert door_type == "com.example.Door"
            else:
                assert door_row_field["type"] == "com.example.Door_Side"
