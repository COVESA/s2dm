"""End-to-end integration tests for JSON Schema export."""

import json
import tempfile
from pathlib import Path

import pytest

from s2dm.exporters.jsonschema import translate_to_jsonschema
from s2dm.exporters.jsonschema.jsonschema import transform
from s2dm.exporters.utils.schema_loader import load_and_process_schema


class TestJsonSchemaE2E:
    @pytest.fixture
    def test_schema_path(self, spec_directory: Path) -> list[Path]:
        """Path to the test GraphQL schema."""
        return [spec_directory, Path(__file__).parent / "test_expanded_instances" / "test_schema.graphql"]

    def test_root_node_filters_types(self, tmp_path: Path) -> None:
        """Test that root node filtering only includes reachable types."""
        schema_str = """
            type Query { vehicle: Vehicle, engine: Engine }
            type Vehicle { id: ID!, engine: Engine }
            type Engine { id: ID!, displacement: Float! }
            type UnrelatedType { id: ID!, data: String }
        """
        schema_file = tmp_path / "test_root_node_filters_types.graphql"
        schema_file.write_text(schema_str)

        root_type = "Vehicle"
        annotated_schema, _, _ = load_and_process_schema(
            schema_paths=[schema_file],
            naming_config_path=None,
            selection_query_path=None,
            root_type=root_type,
            expanded_instances=False,
        )

        result = transform(annotated_schema.schema, root_type=root_type, strict=False)
        schema = json.loads(result)

        assert "Vehicle" in schema["$defs"]
        assert "Engine" in schema["$defs"]
        assert schema["title"] == "Vehicle"
        assert schema["$ref"] == "#/$defs/Vehicle"

        assert "UnrelatedType" not in schema["$defs"]

    def test_instance_tag_expansion(self, test_schema_path: list[Path]) -> None:
        """Test expanded instances for seats with 3-level nesting are inlined in parent property."""
        root_type = "Cabin"
        annotated_schema, _, _ = load_and_process_schema(
            schema_paths=test_schema_path,
            naming_config_path=None,
            selection_query_path=None,
            root_type=root_type,
            expanded_instances=True,
        )
        result = translate_to_jsonschema(annotated_schema, root_type=root_type)
        schema = json.loads(result)

        # Intermediate types must NOT appear as named $defs
        assert "Seat_Row" not in schema["$defs"]
        assert "Seat_Position" not in schema["$defs"]

        # The expanded structure is inlined directly in the parent property
        cabin_def = schema["$defs"]["Cabin"]
        seat_property = cabin_def["properties"]["Seat"]
        assert seat_property["type"] == "object"
        assert seat_property["additionalProperties"] is False
        assert set(seat_property["properties"].keys()) == {"ROW1", "ROW2", "ROW3"}

        row1 = seat_property["properties"]["ROW1"]
        assert row1["type"] == "object"
        assert set(row1["properties"].keys()) == {"LEFT", "CENTER", "RIGHT"}
        assert row1["properties"]["LEFT"]["$ref"] == "#/$defs/Seat"
        assert row1["properties"]["CENTER"]["$ref"] == "#/$defs/Seat"
        assert row1["properties"]["RIGHT"]["$ref"] == "#/$defs/Seat"

        seat_def = schema["$defs"]["Seat"]
        assert "isOccupied" in seat_def["properties"]

    def test_default_behavior_creates_arrays(self, test_schema_path: list[Path]) -> None:
        """Test that the default behavior creates arrays for instance tagged objects."""
        root_type = "Cabin"
        annotated_schema, _, _ = load_and_process_schema(
            schema_paths=test_schema_path,
            naming_config_path=None,
            selection_query_path=None,
            root_type=root_type,
            expanded_instances=False,
        )
        result = translate_to_jsonschema(annotated_schema, root_type=root_type)
        schema = json.loads(result)

        doors_def = schema["$defs"]["Cabin"]["properties"]["doors"]
        assert doors_def["type"] == "array"
        assert "items" in doors_def

        seats_def = schema["$defs"]["Cabin"]["properties"]["seats"]
        assert seats_def["type"] == "array"
        assert "items" in seats_def

    def test_non_instance_tagged_objects_remain_arrays(
        self, spec_directory: Path, test_schema_path: list[Path]
    ) -> None:
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
            root_type = "TestObject"
            annotated_schema, _, _ = load_and_process_schema(
                schema_paths=[spec_directory, temp_path],
                naming_config_path=None,
                selection_query_path=None,
                root_type=root_type,
                expanded_instances=True,
            )
            result = translate_to_jsonschema(annotated_schema, root_type=root_type)
            schema = json.loads(result)

            # The expanded Door structure is inlined (no named intermediate $defs)
            doors_def = schema["$defs"]["TestObject"]["properties"]["Door"]
            assert doors_def["type"] == "object"
            assert doors_def["additionalProperties"] is False
            assert set(doors_def["properties"].keys()) == {"ROW1", "ROW2"}

            row1 = doors_def["properties"]["ROW1"]
            assert row1["type"] == "object"
            assert set(row1["properties"].keys()) == {"DRIVERSIDE", "PASSENGERSIDE"}
            assert row1["properties"]["DRIVERSIDE"]["$ref"] == "#/$defs/Door"

            assert "Door_Row" not in schema["$defs"]

            # Regular arrays remain unaffected
            items_def = schema["$defs"]["TestObject"]["properties"]["regularItems"]
            assert items_def["type"] == "array"
            assert "items" in items_def

        finally:
            temp_path.unlink()

    def test_expanded_instances_with_strict_mode(self, test_schema_path: list[Path]) -> None:
        """Test that expanded instances are inlined correctly with strict mode."""
        root_type = "Cabin"
        annotated_schema, _, _ = load_and_process_schema(
            schema_paths=test_schema_path,
            naming_config_path=None,
            selection_query_path=None,
            root_type=root_type,
            expanded_instances=True,
        )
        result = translate_to_jsonschema(annotated_schema, root_type=root_type, strict=True)
        schema = json.loads(result)

        # Intermediate types must NOT appear as named $defs
        assert "Door_Row" not in schema["$defs"]
        assert "Door_Side" not in schema["$defs"]

        # The expansion is inlined in the parent property
        cabin_def = schema["$defs"]["Cabin"]
        door_property = cabin_def["properties"]["Door"]
        assert door_property["type"] == "object"
        assert door_property["additionalProperties"] is False
        assert set(door_property["properties"].keys()) == {"ROW1", "ROW2"}

        row1 = door_property["properties"]["ROW1"]
        assert row1["type"] == "object"
        assert set(row1["properties"].keys()) == {"DRIVERSIDE", "PASSENGERSIDE"}

        # In strict mode, nullable leaf references use oneOf with null
        driverside_field = row1["properties"]["DRIVERSIDE"]
        assert "oneOf" in driverside_field
        refs = [item.get("$ref") for item in driverside_field["oneOf"] if "$ref" in item]
        assert "#/$defs/Door" in refs

    def test_singular_naming_for_expanded_instances(self, test_schema_path: list[Path]) -> None:
        """Test that expanded instances use singular type names instead of field names."""
        root_type = "Cabin"
        annotated_schema_normal, _, _ = load_and_process_schema(
            schema_paths=test_schema_path,
            naming_config_path=None,
            selection_query_path=None,
            root_type=root_type,
            expanded_instances=False,
        )
        result_normal = translate_to_jsonschema(annotated_schema_normal, root_type=root_type)

        annotated_schema_expanded, _, _ = load_and_process_schema(
            schema_paths=test_schema_path,
            naming_config_path=None,
            selection_query_path=None,
            root_type=root_type,
            expanded_instances=True,
        )
        result_expanded = translate_to_jsonschema(annotated_schema_expanded, root_type=root_type)

        schema_normal = json.loads(result_normal)
        schema_expanded = json.loads(result_expanded)

        assert "doors" in schema_normal["$defs"]["Cabin"]["properties"]
        assert "seats" in schema_normal["$defs"]["Cabin"]["properties"]

        assert "Door" in schema_expanded["$defs"]["Cabin"]["properties"]
        assert "Seat" in schema_expanded["$defs"]["Cabin"]["properties"]

        assert "doors" not in schema_expanded["$defs"]["Cabin"]["properties"]
        assert "seats" not in schema_expanded["$defs"]["Cabin"]["properties"]

    def test_nested_instances_use_inline_expansion(self, spec_directory: Path) -> None:
        """Test that nested expanded instances are inlined at each level without named intermediate $defs."""
        nested_schema_path = Path(__file__).parent / "test_expanded_instances" / "test_nested_schema.graphql"

        root_type = "Chassis"
        annotated_schema, _, _ = load_and_process_schema(
            schema_paths=[spec_directory, nested_schema_path],
            naming_config_path=None,
            selection_query_path=None,
            root_type=root_type,
            expanded_instances=True,
        )
        result = translate_to_jsonschema(annotated_schema, root_type=root_type)
        schema = json.loads(result)

        # Intermediate types must NOT appear as named $defs
        assert "Axle_Row" not in schema["$defs"]
        assert "Wheel_Position" not in schema["$defs"]

        # Chassis.Axle is inlined
        chassis_def = schema["$defs"]["Chassis"]
        axle_prop = chassis_def["properties"]["Axle"]
        assert axle_prop["type"] == "object"
        assert axle_prop["additionalProperties"] is False
        assert set(axle_prop["properties"].keys()) == {"ROW1", "ROW2"}
        assert axle_prop["properties"]["ROW1"]["$ref"] == "#/$defs/Axle"
        assert axle_prop["properties"]["ROW2"]["$ref"] == "#/$defs/Axle"

        # Axle.Wheel is also inlined
        axle_def = schema["$defs"]["Axle"]
        wheel_prop = axle_def["properties"]["Wheel"]
        assert wheel_prop["type"] == "object"
        assert wheel_prop["additionalProperties"] is False
        assert set(wheel_prop["properties"].keys()) == {"LEFT", "RIGHT"}
        assert wheel_prop["properties"]["LEFT"]["$ref"] == "#/$defs/Wheel"
        assert wheel_prop["properties"]["RIGHT"]["$ref"] == "#/$defs/Wheel"

        # Field names are singular
        assert "Wheel" in axle_def["properties"]
        assert "Wheels" not in axle_def["properties"]
        assert "Axle" in chassis_def["properties"]
        assert "Axles" not in chassis_def["properties"]

        wheel_def = schema["$defs"]["Wheel"]
        assert wheel_def["type"] == "object"
        assert "Tire" in wheel_def["properties"]
        assert wheel_def["properties"]["Tire"]["$ref"] == "#/$defs/Tire"
