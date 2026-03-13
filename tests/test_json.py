"""Unit tests for JSON tree exporter."""

from pathlib import Path

import pytest
from graphql import build_schema

from s2dm.exporters.json import JsonExporter
from s2dm.exporters.utils.annotated_schema import AnnotatedSchema
from s2dm.exporters.utils.schema_loader import load_and_process_schema


def test_simple_scalar_field() -> None:
    """Test extraction of simple scalar field properties."""
    schema_str = """
    type Vehicle {
        \"\"\"Vehicle speed in km/h\"\"\"
        speed: Float
    }
    """
    schema = build_schema(schema_str)
    annotated = AnnotatedSchema(schema=schema, field_metadata={}, type_metadata={})
    exporter = JsonExporter(schema, annotated)

    result = exporter.export(root_type="Vehicle")

    assert "Vehicle" in result
    vehicle = result["Vehicle"]
    assert "type" not in vehicle  # No type in default mode
    assert "children" in vehicle
    assert "speed" in vehicle["children"]

    speed = vehicle["children"]["speed"]
    assert speed["datatype"] == "Float"
    assert speed["description"] == "Vehicle speed in km/h"
    # No 'type' field without @vspec


def test_range_directive() -> None:
    """Test extraction from @range directive."""
    schema_str = """
    directive @range(min: Float, max: Float) on FIELD_DEFINITION

    type Vehicle {
        speed: Float @range(min: 0.0, max: 250.0)
    }
    """
    schema = build_schema(schema_str)
    annotated = AnnotatedSchema(schema=schema, field_metadata={}, type_metadata={})
    exporter = JsonExporter(schema, annotated)

    result = exporter.export(root_type="Vehicle")
    speed = result["Vehicle"]["children"]["speed"]

    assert speed["min"] == 0.0
    assert speed["max"] == 250.0


def test_metadata_directive() -> None:
    """Test that @metadata directive is ignored without @vspec."""
    schema_str = """
    directive @metadata(comment: String, vssType: String) on FIELD_DEFINITION

    type Vehicle {
        speed: Float @metadata(comment: "Test comment", vssType: "actuator")
    }
    """
    schema = build_schema(schema_str)
    annotated = AnnotatedSchema(schema=schema, field_metadata={}, type_metadata={})
    exporter = JsonExporter(schema, annotated)

    result = exporter.export(root_type="Vehicle")
    speed = result["Vehicle"]["children"]["speed"]

    # @metadata is ignored without @vspec
    assert "comment" not in speed
    assert "type" not in speed
    assert speed["datatype"] == "Float"


def test_enum_field() -> None:
    """Test enum field without @vspec has no allowed values."""
    schema_str = """
    enum GearPosition {
        PARK
        REVERSE
        NEUTRAL
        DRIVE
    }

    type Vehicle {
        gear: GearPosition
    }
    """
    schema = build_schema(schema_str)
    annotated = AnnotatedSchema(schema=schema, field_metadata={}, type_metadata={})
    exporter = JsonExporter(schema, annotated)

    result = exporter.export(root_type="Vehicle")
    gear = result["Vehicle"]["children"]["gear"]

    assert gear["datatype"] == "GearPosition"
    # No 'allowed' field without @vspec
    assert "allowed" not in gear


def test_array_type() -> None:
    """Test that array types get [] suffix on datatype."""
    schema_str = """
    type Vehicle {
        seatPosCount: [Int]
    }
    """
    schema = build_schema(schema_str)
    annotated = AnnotatedSchema(schema=schema, field_metadata={}, type_metadata={})
    exporter = JsonExporter(schema, annotated)

    result = exporter.export(root_type="Vehicle")
    seat_pos = result["Vehicle"]["children"]["seatPosCount"]

    assert seat_pos["datatype"] == "Int[]"


def test_nested_object_types() -> None:
    """Test nested object types create branch nodes."""
    schema_str = """
    type Door {
        isOpen: Boolean
        isLocked: Boolean
    }

    type Vehicle {
        door: Door
    }
    """
    schema = build_schema(schema_str)
    annotated = AnnotatedSchema(schema=schema, field_metadata={}, type_metadata={})
    exporter = JsonExporter(schema, annotated)

    result = exporter.export(root_type="Vehicle")
    door = result["Vehicle"]["children"]["door"]

    assert "type" not in door  # No type in default mode
    assert "children" in door
    assert "isOpen" in door["children"]
    assert "isLocked" in door["children"]


def test_multi_root_export() -> None:
    """Test exporting multiple root types."""
    schema_str = """
    type Vehicle {
        speed: Float
    }

    type Building {
        floors: Int
    }

    type Query {
        ping: String
    }
    """
    schema = build_schema(schema_str)
    annotated = AnnotatedSchema(schema=schema, field_metadata={}, type_metadata={})
    exporter = JsonExporter(schema, annotated)

    result = exporter.export(root_type=None)

    # Should export Vehicle and Building, but not Query (introspection types are filtered)
    assert "Vehicle" in result
    assert "Building" in result
    # Query is not an introspection type, so it should be included
    assert "Query" in result


def test_cycle_detection() -> None:
    """Test that circular references are handled with $ref."""
    schema_str = """
    type Node {
        value: String
        parent: Node
    }
    """
    schema = build_schema(schema_str)
    annotated = AnnotatedSchema(schema=schema, field_metadata={}, type_metadata={})
    exporter = JsonExporter(schema, annotated)

    result = exporter.export(root_type="Node")
    parent_field = result["Node"]["children"]["parent"]

    # Should have $ref to prevent infinite recursion
    assert "$ref" in parent_field


def test_combined_directives() -> None:
    """Test that @range works but @metadata is ignored without @vspec."""
    schema_str = """
    directive @range(min: Float, max: Float) on FIELD_DEFINITION
    directive @metadata(comment: String, vssType: String) on FIELD_DEFINITION

    type Vehicle {
        \"\"\"Current speed\"\"\"
        speed: Float @range(min: 0.0, max: 250.0) @metadata(comment: "In kilometers per hour", vssType: "sensor")
    }
    """
    schema = build_schema(schema_str)
    annotated = AnnotatedSchema(schema=schema, field_metadata={}, type_metadata={})
    exporter = JsonExporter(schema, annotated)

    result = exporter.export(root_type="Vehicle")
    speed = result["Vehicle"]["children"]["speed"]

    assert speed["datatype"] == "Float"
    assert speed["description"] == "Current speed"
    assert speed["min"] == 0.0
    assert speed["max"] == 250.0
    # @metadata is ignored without @vspec
    assert "comment" not in speed
    assert "type" not in speed


def test_integration_with_test_schema(spec_directory: Path) -> None:
    """Test with actual test schema from tests/data/spec."""
    schema_path = spec_directory / "common.graphql"
    if not schema_path.exists():
        pytest.skip("Test schema not found")

    annotated_schema, _, _ = load_and_process_schema(
        schema_paths=[schema_path],
        naming_config_path=None,
        selection_query_path=None,
        root_type=None,
        expanded_instances=False,
    )

    exporter = JsonExporter(annotated_schema.schema, annotated_schema)
    result = exporter.export(root_type=None)

    # Should successfully export without errors
    assert isinstance(result, dict)
    assert len(result) > 0
