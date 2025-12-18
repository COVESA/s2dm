"""End-to-end integration tests for Avro protocol export with expanded instances."""

import json
import re
from pathlib import Path

import pytest

from s2dm.exporters.avro.protocol import translate_to_avro_protocol
from s2dm.exporters.utils.schema_loader import load_and_process_schema


class TestAvroIDLE2EExpandedInstances:
    @pytest.fixture
    def test_schema_path(self) -> list[Path]:
        """Path to the test GraphQL schema with @struct and @instanceTag."""
        return [Path(__file__).parent / "test_expanded_instances" / "test_schema.graphql"]

    def test_basic_struct_types_no_expanded_instances(self, test_schema_path: list[Path]) -> None:
        """Test that only types with @struct directive generate IDL protocols."""
        annotated_schema, _, _ = load_and_process_schema(
            schema_paths=test_schema_path,
            naming_config_path=None,
            selection_query_path=None,
            root_type=None,
            expanded_instances=False,
        )
        result = translate_to_avro_protocol(annotated_schema, "com.example")

        assert len(result) == 2
        assert "Cabin" in result
        assert "Vehicle" in result
        assert "Seat" not in result
        assert "Door" not in result

        cabin_idl = result["Cabin"]

        assert re.search(
            r'@namespace\("com\.example"\)\s*'
            r"protocol\s+Cabin\s*\{.*?"
            r"record\s+Cabin\s*\{.*?"
            r"array<Seat>\?\s+seats;.*?"
            r"array<Door>\?\s+doors;.*?"
            r"double\?\s+temperature;.*?"
            r"\}.*?"
            r"\}",
            cabin_idl,
            re.DOTALL,
        ), "Cabin record inside protocol with correct namespace and fields"

        assert re.search(
            r"protocol\s+Cabin\s*\{.*?"
            r"record\s+Door\s*\{.*?"
            r"boolean\?\s+isLocked;.*?"
            r"int\?\s+position;.*?"
            r"DoorPosition\?\s+instanceTag;.*?"
            r"\}.*?"
            r"\}",
            cabin_idl,
            re.DOTALL,
        ), "Door record inside protocol with correct fields"

        assert re.search(
            r"protocol\s+Cabin\s*\{.*?"
            r"record\s+DoorPosition\s*\{.*?"
            r"string\?\s+row;.*?"
            r"string\?\s+side;.*?"
            r"\}.*?"
            r"\}",
            cabin_idl,
            re.DOTALL,
        ), "DoorPosition record inside protocol with correct fields"

        assert re.search(
            r"protocol\s+Cabin\s*\{.*?"
            r"record\s+Seat\s*\{.*?"
            r"boolean\?\s+isOccupied;.*?"
            r"int\?\s+height;.*?"
            r"SeatPosition\?\s+instanceTag;.*?"
            r"\}.*?"
            r"\}",
            cabin_idl,
            re.DOTALL,
        ), "Seat record inside protocol with correct fields"

        assert re.search(
            r"protocol\s+Cabin\s*\{.*?"
            r"record\s+SeatPosition\s*\{.*?"
            r"string\?\s+row;.*?"
            r"string\?\s+position;.*?"
            r"\}.*?"
            r"\}",
            cabin_idl,
            re.DOTALL,
        ), "SeatPosition record inside protocol with correct fields"

    def test_basic_struct_types_with_expanded_instances(self, test_schema_path: list[Path]) -> None:
        """Test that instance tags ARE expanded into nested records when expanded_instances=True."""
        annotated_schema, _, _ = load_and_process_schema(
            schema_paths=test_schema_path,
            naming_config_path=None,
            selection_query_path=None,
            root_type=None,
            expanded_instances=True,
        )
        result = translate_to_avro_protocol(annotated_schema, "com.example")

        cabin_idl = result["Cabin"]

        assert re.search(
            r"record\s+Cabin\s*\{.*?"
            r"double\?\s+temperature;.*?"
            r"Seat_Row\?\s+Seat;.*?"
            r"Door_Row\?\s+Door;.*?"
            r"\}",
            cabin_idl,
            re.DOTALL,
        ), "Cabin should have Seat_Row and Door_Row fields instead of arrays"

        assert re.search(
            r"record\s+Seat_Row\s*\{.*?"
            r"Seat_Position\?\s+ROW1;.*?"
            r"Seat_Position\?\s+ROW2;.*?"
            r"Seat_Position\?\s+ROW3;.*?"
            r"\}",
            cabin_idl,
            re.DOTALL,
        ), "Seat_Row should have ROW1, ROW2, ROW3 fields"

        assert re.search(
            r"record\s+Seat_Position\s*\{.*?" r"Seat\?\s+LEFT;.*?" r"Seat\?\s+CENTER;.*?" r"Seat\?\s+RIGHT;.*?" r"\}",
            cabin_idl,
            re.DOTALL,
        ), "Seat_Position should have LEFT, CENTER, RIGHT fields"

        assert re.search(
            r"record\s+Door_Row\s*\{.*?" r"Door_Side\?\s+ROW1;.*?" r"Door_Side\?\s+ROW2;.*?" r"\}",
            cabin_idl,
            re.DOTALL,
        ), "Door_Row should have ROW1, ROW2 fields"

        assert re.search(
            r"record\s+Door_Side\s*\{.*?" r"Door\?\s+DRIVERSIDE;.*?" r"Door\?\s+PASSENGERSIDE;.*?" r"\}",
            cabin_idl,
            re.DOTALL,
        ), "Door_Side should have DRIVERSIDE, PASSENGERSIDE fields"

    def test_expanded_instances_with_naming_config(self, test_schema_path: list[Path], tmp_path: Path) -> None:
        """Test that naming config is applied to expanded instance field names."""
        naming_config = {"field": {"object": "MACROCASE"}}
        naming_config_file = tmp_path / "naming_config.json"
        naming_config_file.write_text(json.dumps(naming_config))

        annotated_schema, _, _ = load_and_process_schema(
            schema_paths=test_schema_path,
            naming_config_path=naming_config_file,
            selection_query_path=None,
            root_type=None,
            expanded_instances=True,
        )
        result = translate_to_avro_protocol(annotated_schema, "com.example")

        cabin_idl = result["Cabin"]

        assert re.search(
            r"record\s+Cabin\s*\{.*?"
            r"double\?\s+TEMPERATURE;.*?"
            r"Seat_Row\?\s+SEAT;.*?"
            r"Door_Row\?\s+DOOR;.*?"
            r"\}",
            cabin_idl,
            re.DOTALL,
        ), "Cabin fields should be in MACROCASE (TEMPERATURE, SEAT, DOOR)"

        assert re.search(
            r"record\s+Seat\s*\{.*?" r"boolean\?\s+IS_OCCUPIED;.*?" r"int\?\s+HEIGHT;",
            cabin_idl,
            re.DOTALL,
        ), "Seat fields should be in MACROCASE (IS_OCCUPIED, HEIGHT)"

        assert re.search(
            r"record\s+Door\s*\{.*?" r"boolean\?\s+IS_LOCKED;.*?" r"int\?\s+POSITION;",
            cabin_idl,
            re.DOTALL,
        ), "Door fields should be in MACROCASE (IS_LOCKED, POSITION)"

    def test_strict_mode_with_expanded_instances(self, test_schema_path: list[Path]) -> None:
        """Test strict mode with expanded instances enforces nullability."""
        annotated_schema, _, _ = load_and_process_schema(
            schema_paths=test_schema_path,
            naming_config_path=None,
            selection_query_path=None,
            root_type=None,
            expanded_instances=True,
        )
        result = translate_to_avro_protocol(annotated_schema, "com.example", strict=True)

        cabin_idl = result["Cabin"]

        assert re.search(
            r"record\s+Cabin\s*\{.*?" r"double\?\s+temperature;.*?" r"Seat_Row\s+Seat;.*?" r"Door_Row\s+Door;.*?" r"\}",
            cabin_idl,
            re.DOTALL,
        ), "Strict mode: expanded fields Seat and Door should not be optional"
