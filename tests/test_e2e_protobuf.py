"""End-to-end integration tests for Protobuf export."""

import json
import re
from pathlib import Path
from typing import cast

import pytest
from graphql import DocumentNode

from s2dm.exporters.protobuf import translate_to_protobuf
from s2dm.exporters.utils.schema_loader import load_and_process_schema


class TestProtobufE2E:
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
        result = translate_to_protobuf(annotated_schema, selection_query=cast(DocumentNode, selection_query))

        assert re.search(
            r"message Cabin \{.*?"
            r'option \(message_source\) = "Cabin".*?;.*?'
            r"repeated Seat seats = 1.*?;.*?"
            r"repeated Door doors = 2.*?;.*?"
            r"float temperature = 3.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Cabin message with source option and repeated fields"

        assert re.search(
            r"message Seat \{.*?" r'option \(message_source\) = "Seat";', result, re.DOTALL
        ), "Seat message with source option"

        assert re.search(
            r"message Door \{.*?" r'option \(message_source\) = "Door";', result, re.DOTALL
        ), "Door message with source option"

        assert "message Cabin_seats" not in result
        assert "message Cabin_doors" not in result

    def test_expanded_instances(self, test_schema_path: list[Path], tmp_path: Path) -> None:
        """Test that instance tags are expanded into nested messages when enabled."""

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
        result = translate_to_protobuf(annotated_schema, selection_query=cast(DocumentNode, selection_query))

        assert re.search(
            r"message Cabin \{.*?"
            r'option \(message_source\) = "Cabin";.*?'
            r"optional float temperature = 1.*?"
            r"Seat_Row Seat = 2 \[\(buf\.validate\.field\)\.required = true\];.*?"
            r"Door_Row Door = 3 \[\(buf\.validate\.field\)\.required = true\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Cabin message with temperature and expanded instance references"

        assert re.search(
            r"message Seat_Position \{.*?"
            r'option \(message_source\) = "Seat_Position";.*?'
            r"optional Seat LEFT = 1;.*?"
            r"optional Seat CENTER = 2;.*?"
            r"optional Seat RIGHT = 3;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Seat_Position intermediate type with seat instances"

        assert re.search(
            r"message Seat_Row \{.*?"
            r'option \(message_source\) = "Seat_Row";.*?'
            r"Seat_Position ROW1 = 1 \[\(buf\.validate\.field\)\.required = true\];.*?"
            r"Seat_Position ROW2 = 2 \[\(buf\.validate\.field\)\.required = true\];.*?"
            r"Seat_Position ROW3 = 3 \[\(buf\.validate\.field\)\.required = true\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Seat_Row intermediate type with row positions"

        assert re.search(
            r"message Door_Side \{.*?"
            r'option \(message_source\) = "Door_Side";.*?'
            r"optional Door DRIVERSIDE = 1;.*?"
            r"optional Door PASSENGERSIDE = 2;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Door_Side intermediate type with door instances"

        assert re.search(
            r"message Door_Row \{.*?"
            r'option \(message_source\) = "Door_Row";.*?'
            r"Door_Side ROW1 = 1 \[\(buf\.validate\.field\)\.required = true\];.*?"
            r"Door_Side ROW2 = 2 \[\(buf\.validate\.field\)\.required = true\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Door_Row intermediate type with row sides"

        assert re.search(
            r"message Door \{.*?"
            r'option \(message_source\) = "Door";.*?'
            r"optional bool isLocked = 1;.*?"
            r"optional int32 position = 2 \[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Door message with fields"

        assert re.search(
            r"message Seat \{.*?"
            r'option \(message_source\) = "Seat";.*?'
            r"optional bool isOccupied = 1;.*?"
            r"optional int32 height = 2 \[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Seat message with fields"

        assert "SeatRowEnum" in result
        assert "SeatPositionEnum" in result
        assert "RowEnum" in result
        assert "SideEnum" in result

        assert not re.search(r"message DoorPosition \{", result), "DoorPosition type should be removed"
        assert not re.search(r"message SeatPosition \{", result), "SeatPosition type should be removed"

    def test_expanded_instances_with_flatten_naming(self, test_schema_path: list[Path], tmp_path: Path) -> None:
        """Test that expanded instances only expand in flatten mode when flag is set."""

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
        result = translate_to_protobuf(
            annotated_schema, flatten_root_types=["Cabin"], selection_query=cast(DocumentNode, selection_query)
        )

        assert re.search(
            r"message Selection \{.*?"
            r'option \(message_source\) = "query: Selection";.*?'
            r'optional float Cabin_temperature = 1 \[\(field_source\) = "Cabin", '
            r"\(buf\.validate\.field\)\.float = \{gte: -100, lte: 100\}\];.*?"
            r'optional bool Cabin_Seat_ROW1_LEFT_isOccupied = 2 \[\(field_source\) = "Seat"\];.*?'
            r'optional int32 Cabin_Seat_ROW1_LEFT_height = 3 \[\(field_source\) = "Seat", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_Seat_ROW1_CENTER_isOccupied = 4 \[\(field_source\) = "Seat"\];.*?'
            r'optional int32 Cabin_Seat_ROW1_CENTER_height = 5 \[\(field_source\) = "Seat", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_Seat_ROW1_RIGHT_isOccupied = 6 \[\(field_source\) = "Seat"\];.*?'
            r'optional int32 Cabin_Seat_ROW1_RIGHT_height = 7 \[\(field_source\) = "Seat", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_Seat_ROW2_LEFT_isOccupied = 8 \[\(field_source\) = "Seat"\];.*?'
            r'optional int32 Cabin_Seat_ROW2_LEFT_height = 9 \[\(field_source\) = "Seat", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_Seat_ROW2_CENTER_isOccupied = 10 \[\(field_source\) = "Seat"\];.*?'
            r'optional int32 Cabin_Seat_ROW2_CENTER_height = 11 \[\(field_source\) = "Seat", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_Seat_ROW2_RIGHT_isOccupied = 12 \[\(field_source\) = "Seat"\];.*?'
            r'optional int32 Cabin_Seat_ROW2_RIGHT_height = 13 \[\(field_source\) = "Seat", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_Seat_ROW3_LEFT_isOccupied = 14 \[\(field_source\) = "Seat"\];.*?'
            r'optional int32 Cabin_Seat_ROW3_LEFT_height = 15 \[\(field_source\) = "Seat", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_Seat_ROW3_CENTER_isOccupied = 16 \[\(field_source\) = "Seat"\];.*?'
            r'optional int32 Cabin_Seat_ROW3_CENTER_height = 17 \[\(field_source\) = "Seat", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_Seat_ROW3_RIGHT_isOccupied = 18 \[\(field_source\) = "Seat"\];.*?'
            r'optional int32 Cabin_Seat_ROW3_RIGHT_height = 19 \[\(field_source\) = "Seat", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_Door_ROW1_DRIVERSIDE_isLocked = 20 \[\(field_source\) = "Door"\];.*?'
            r'optional int32 Cabin_Door_ROW1_DRIVERSIDE_position = 21 \[\(field_source\) = "Door", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_Door_ROW1_PASSENGERSIDE_isLocked = 22 \[\(field_source\) = "Door"\];.*?'
            r'optional int32 Cabin_Door_ROW1_PASSENGERSIDE_position = 23 \[\(field_source\) = "Door", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_Door_ROW2_DRIVERSIDE_isLocked = 24 \[\(field_source\) = "Door"\];.*?'
            r'optional int32 Cabin_Door_ROW2_DRIVERSIDE_position = 25 \[\(field_source\) = "Door", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_Door_ROW2_PASSENGERSIDE_isLocked = 26 \[\(field_source\) = "Door"\];.*?'
            r'optional int32 Cabin_Door_ROW2_PASSENGERSIDE_position = 27 \[\(field_source\) = "Door", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Selection message with all flattened expanded instance fields"

        assert "SeatRowEnum" not in result
        assert "SeatPositionEnum" not in result
        assert "RowEnum" not in result
        assert "SideEnum" not in result

    def test_expanded_instances_with_naming_config(self, test_schema_path: list[Path], tmp_path: Path) -> None:
        """Test that naming config is applied to expanded instance field names in non-flatten mode."""
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
        result = translate_to_protobuf(annotated_schema, selection_query=cast(DocumentNode, selection_query))

        assert re.search(
            r"message Cabin \{.*?"
            r'option \(message_source\) = "Cabin";.*?'
            r"optional float TEMPERATURE = 1.*?"
            r"Seat_Row SEAT = 2 \[\(buf\.validate\.field\)\.required = true\];.*?"
            r"Door_Row DOOR = 3 \[\(buf\.validate\.field\)\.required = true\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Cabin message with MACROCASE field names"

        assert re.search(
            r"message Seat_Position \{.*?"
            r'option \(message_source\) = "Seat_Position";.*?'
            r"optional Seat LEFT = 1;.*?"
            r"optional Seat CENTER = 2;.*?"
            r"optional Seat RIGHT = 3;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Seat_Position intermediate type"

        assert re.search(
            r"message Seat_Row \{.*?"
            r'option \(message_source\) = "Seat_Row";.*?'
            r"Seat_Position ROW1 = 1 \[\(buf\.validate\.field\)\.required = true\];.*?"
            r"Seat_Position ROW2 = 2 \[\(buf\.validate\.field\)\.required = true\];.*?"
            r"Seat_Position ROW3 = 3 \[\(buf\.validate\.field\)\.required = true\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Seat_Row intermediate type"

        assert re.search(
            r"message Door \{.*?"
            r'option \(message_source\) = "Door";.*?'
            r"optional bool IS_LOCKED = 1;.*?"
            r"optional int32 POSITION = 2 \[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Door message with MACROCASE fields"

        assert re.search(
            r"message Seat \{.*?"
            r'option \(message_source\) = "Seat";.*?'
            r"optional bool IS_OCCUPIED = 1;.*?"
            r"optional int32 HEIGHT = 2 \[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Seat message with MACROCASE fields"

        assert "SeatRowEnum" in result
        assert "SeatPositionEnum" in result
        assert "RowEnum" in result
        assert "SideEnum" in result

        assert not re.search(r"message DoorPosition \{", result), "DoorPosition type should be removed"
        assert not re.search(r"message SeatPosition \{", result), "SeatPosition type should be removed"

    def test_flatten_mode_expanded_instances_with_naming_config(
        self, test_schema_path: list[Path], tmp_path: Path
    ) -> None:
        """Test that naming config is applied to type name in flattened prefix with expanded instances."""
        naming_config = {"field": {"object": "snake_case"}, "enumValue": "PascalCase", "instanceTag": "PascalCase"}
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
        result = translate_to_protobuf(
            annotated_schema, flatten_root_types=["Cabin"], selection_query=cast(DocumentNode, selection_query)
        )

        assert re.search(
            r"message Selection \{.*?"
            r'option \(message_source\) = "query: Selection";.*?'
            r'optional float Cabin_temperature = 1 \[\(field_source\) = "Cabin", '
            r"\(buf\.validate\.field\)\.float = \{gte: -100, lte: 100\}\];.*?"
            r'optional bool Cabin_seat_Row1_Left_is_occupied = 2 \[\(field_source\) = "Seat"\];.*?'
            r'optional int32 Cabin_seat_Row1_Left_height = 3 \[\(field_source\) = "Seat", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_seat_Row1_Center_is_occupied = 4 \[\(field_source\) = "Seat"\];.*?'
            r'optional int32 Cabin_seat_Row1_Center_height = 5 \[\(field_source\) = "Seat", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_seat_Row1_Right_is_occupied = 6 \[\(field_source\) = "Seat"\];.*?'
            r'optional int32 Cabin_seat_Row1_Right_height = 7 \[\(field_source\) = "Seat", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_seat_Row2_Left_is_occupied = 8 \[\(field_source\) = "Seat"\];.*?'
            r'optional int32 Cabin_seat_Row2_Left_height = 9 \[\(field_source\) = "Seat", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_seat_Row2_Center_is_occupied = 10 \[\(field_source\) = "Seat"\];.*?'
            r'optional int32 Cabin_seat_Row2_Center_height = 11 \[\(field_source\) = "Seat", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_seat_Row2_Right_is_occupied = 12 \[\(field_source\) = "Seat"\];.*?'
            r'optional int32 Cabin_seat_Row2_Right_height = 13 \[\(field_source\) = "Seat", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_seat_Row3_Left_is_occupied = 14 \[\(field_source\) = "Seat"\];.*?'
            r'optional int32 Cabin_seat_Row3_Left_height = 15 \[\(field_source\) = "Seat", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_seat_Row3_Center_is_occupied = 16 \[\(field_source\) = "Seat"\];.*?'
            r'optional int32 Cabin_seat_Row3_Center_height = 17 \[\(field_source\) = "Seat", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_seat_Row3_Right_is_occupied = 18 \[\(field_source\) = "Seat"\];.*?'
            r'optional int32 Cabin_seat_Row3_Right_height = 19 \[\(field_source\) = "Seat", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_door_Row1_Driverside_is_locked = 20 \[\(field_source\) = "Door"\];.*?'
            r'optional int32 Cabin_door_Row1_Driverside_position = 21 \[\(field_source\) = "Door", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_door_Row1_Passengerside_is_locked = 22 \[\(field_source\) = "Door"\];.*?'
            r'optional int32 Cabin_door_Row1_Passengerside_position = 23 \[\(field_source\) = "Door", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_door_Row2_Driverside_is_locked = 24 \[\(field_source\) = "Door"\];.*?'
            r'optional int32 Cabin_door_Row2_Driverside_position = 25 \[\(field_source\) = "Door", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'optional bool Cabin_door_Row2_Passengerside_is_locked = 26 \[\(field_source\) = "Door"\];.*?'
            r'optional int32 Cabin_door_Row2_Passengerside_position = 27 \[\(field_source\) = "Door", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Selection message with all flattened expanded instance fields with PascalCase enum values"

        assert "SeatRowEnum" not in result
        assert "SeatPositionEnum" not in result
        assert "RowEnum" not in result
        assert "SideEnum" not in result
