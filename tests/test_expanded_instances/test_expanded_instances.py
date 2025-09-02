import json
import tempfile
from pathlib import Path

import pytest

from s2dm.exporters.jsonschema import translate_to_jsonschema


class TestExpandedInstances:
    """Test the expanded instances functionality for JSON Schema export."""

    @pytest.fixture
    def test_schema_path(self) -> Path:
        """Path to the test GraphQL schema."""
        return Path(__file__).parent / "test_schema.graphql"

    def test_default_behavior_creates_arrays(self, test_schema_path: Path) -> None:
        """Test that the default behavior creates arrays for instance tagged objects."""
        result = translate_to_jsonschema(test_schema_path, root_type="Cabin")
        schema = json.loads(result)

        # Check that doors is an array
        doors_def = schema["$defs"]["Cabin"]["properties"]["doors"]
        assert doors_def["type"] == "array"
        assert "items" in doors_def

        # Check that seats is an array
        seats_def = schema["$defs"]["Cabin"]["properties"]["seats"]
        assert seats_def["type"] == "array"
        assert "items" in seats_def

    def test_expanded_instances_creates_nested_objects(self, test_schema_path: Path) -> None:
        """Test that expanded_instances=True creates nested object structures."""
        result = translate_to_jsonschema(test_schema_path, root_type="Cabin", expanded_instances=True)
        schema = json.loads(result)

        # Check that Doors becomes Door (singular) and is a nested object structure
        door_def = schema["$defs"]["Cabin"]["properties"]["Door"]
        assert door_def["type"] == "object"
        assert "properties" in door_def

        # Should have ROW1 and ROW2
        assert "ROW1" in door_def["properties"]
        assert "ROW2" in door_def["properties"]

        # Each row should have DRIVERSIDE and PASSENGERSIDE
        row1 = door_def["properties"]["ROW1"]
        assert row1["type"] == "object"
        assert "DRIVERSIDE" in row1["properties"]
        assert "PASSENGERSIDE" in row1["properties"]

        # Each door position should use $ref to Door type (not copy properties inline)
        driver_door = row1["properties"]["DRIVERSIDE"]
        assert driver_door == {"$ref": "#/$defs/Door"}

    def test_expanded_instances_for_seats(self, test_schema_path: Path) -> None:
        """Test expanded instances for seats with 3-level nesting."""
        result = translate_to_jsonschema(test_schema_path, root_type="Cabin", expanded_instances=True)
        schema = json.loads(result)

        # Check that Seats becomes Seat (singular) and is a nested object structure
        seat_def = schema["$defs"]["Cabin"]["properties"]["Seat"]
        assert seat_def["type"] == "object"
        assert "properties" in seat_def

        # Should have ROW1, ROW2, ROW3
        assert "ROW1" in seat_def["properties"]
        assert "ROW2" in seat_def["properties"]
        assert "ROW3" in seat_def["properties"]

        # Each row should have LEFT, CENTER, RIGHT
        row1 = seat_def["properties"]["ROW1"]
        assert row1["type"] == "object"
        assert "LEFT" in row1["properties"]
        assert "CENTER" in row1["properties"]
        assert "RIGHT" in row1["properties"]

        # Each seat position should use $ref to Seat type (not copy properties inline)
        left_seat = row1["properties"]["LEFT"]
        assert left_seat == {"$ref": "#/$defs/Seat"}

    def test_non_instance_tagged_objects_remain_arrays(self, test_schema_path: Path) -> None:
        """Test that objects without instance tags remain as arrays even with expanded_instances=True."""
        # Create a schema with both instance-tagged and regular arrays
        extended_schema = """
        enum RowEnum {
          ROW1
          ROW2
        }

        enum SideEnum {
          DRIVERSIDE
          PASSENGERSIDE
        }

        type DoorPosition @instanceTag {
          Row: RowEnum!
          Side: SideEnum!
        }

        type Door {
          isLocked: Boolean
          instanceTag: DoorPosition
        }

        type RegularItem {
          name: String
          value: Int
        }

        type TestObject {
          doorsWithInstanceTag: [Door] @noDuplicates
          regularItems: [RegularItem] @noDuplicates
        }
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".graphql", delete=False) as f:
            f.write(extended_schema)
            temp_path = Path(f.name)

        try:
            result = translate_to_jsonschema(temp_path, root_type="TestObject", expanded_instances=True)
            schema = json.loads(result)

            # Instance-tagged doors should be expanded and use singular name
            doors_def = schema["$defs"]["TestObject"]["properties"]["Door"]
            assert doors_def["type"] == "object"
            assert "properties" in doors_def

            # Regular items should remain as array
            items_def = schema["$defs"]["TestObject"]["properties"]["regularItems"]
            assert items_def["type"] == "array"
            assert "items" in items_def

        finally:
            temp_path.unlink()

    def test_expanded_instances_with_strict_mode(self, test_schema_path: Path) -> None:
        """Test that expanded instances work correctly with strict mode."""
        result = translate_to_jsonschema(test_schema_path, root_type="Cabin", strict=True, expanded_instances=True)
        schema = json.loads(result)

        # Should still create expanded structure with singular naming
        door_def = schema["$defs"]["Cabin"]["properties"]["Door"]
        assert door_def["type"] == "object"
        assert "ROW1" in door_def["properties"]

        # In expanded instances, positions should use $ref (behavior is same in both modes)
        driver_door = door_def["properties"]["ROW1"]["properties"]["DRIVERSIDE"]
        assert driver_door == {"$ref": "#/$defs/Door"}

    def test_singular_naming_for_expanded_instances(self, test_schema_path: Path) -> None:
        """Test that expanded instances use singular type names instead of field names."""
        result_normal = translate_to_jsonschema(test_schema_path, root_type="Cabin", expanded_instances=False)
        result_expanded = translate_to_jsonschema(test_schema_path, root_type="Cabin", expanded_instances=True)

        schema_normal = json.loads(result_normal)
        schema_expanded = json.loads(result_expanded)

        # Normal behavior should use plural field names
        assert "doors" in schema_normal["$defs"]["Cabin"]["properties"]
        assert "seats" in schema_normal["$defs"]["Cabin"]["properties"]

        # Expanded behavior should use singular type names
        assert "Door" in schema_expanded["$defs"]["Cabin"]["properties"]
        assert "Seat" in schema_expanded["$defs"]["Cabin"]["properties"]

        # The original plural field names should not exist in expanded version
        assert "doors" not in schema_expanded["$defs"]["Cabin"]["properties"]
        assert "seats" not in schema_expanded["$defs"]["Cabin"]["properties"]

    def test_nested_instances_use_refs_not_inline_expansion(self) -> None:
        """Test that nested expanded instances use $ref instead of copying object properties inline."""
        # Create a nested schema path
        nested_schema_path = Path(__file__).parent / "test_nested_schema.graphql"

        result = translate_to_jsonschema(nested_schema_path, root_type="Chassis", expanded_instances=True)
        schema = json.loads(result)

        # Check that Chassis -> Axle uses proper expansion with $ref
        chassis_def = schema["$defs"]["Chassis"]
        axle_prop = chassis_def["properties"]["Axle"]

        # Should be an object with ROW1 and ROW2 properties
        assert axle_prop["type"] == "object"
        assert "ROW1" in axle_prop["properties"]
        assert "ROW2" in axle_prop["properties"]

        # Each ROW should use $ref to Axle, not copy properties inline
        assert axle_prop["properties"]["ROW1"] == {"$ref": "#/$defs/Axle"}
        assert axle_prop["properties"]["ROW2"] == {"$ref": "#/$defs/Axle"}

        # Check that Axle -> Wheel also uses proper expansion with $ref
        axle_def = schema["$defs"]["Axle"]
        wheel_prop = axle_def["properties"]["Wheel"]

        # Should be an object with LEFT and RIGHT properties
        assert wheel_prop["type"] == "object"
        assert "LEFT" in wheel_prop["properties"]
        assert "RIGHT" in wheel_prop["properties"]

        # Each position should use $ref to Wheel, not copy properties inline
        assert wheel_prop["properties"]["LEFT"] == {"$ref": "#/$defs/Wheel"}
        assert wheel_prop["properties"]["RIGHT"] == {"$ref": "#/$defs/Wheel"}

        # Verify that field names are singular (Wheel not Wheels, Axle not Axles)
        assert "Wheel" in axle_def["properties"]
        assert "Wheels" not in axle_def["properties"]
        assert "Axle" in chassis_def["properties"]
        assert "Axles" not in chassis_def["properties"]

        # Verify the nested Wheel definition exists and has the expected structure
        wheel_def = schema["$defs"]["Wheel"]
        assert wheel_def["type"] == "object"
        assert "Tire" in wheel_def["properties"]
        assert wheel_def["properties"]["Tire"] == {"$ref": "#/$defs/Tire"}
