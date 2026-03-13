"""Test JSON exporter with schemas that have NO @vspec annotations.

These tests ensure that only default fields are included when @vspec is not present:
- description (from GraphQL docstring)
- datatype (from scalar type)
- min (from @range directive)
- max (from @range directive)
- unit (from field argument)
"""

from graphql import build_schema

from s2dm.exporters.json import JsonExporter
from s2dm.exporters.utils.annotated_schema import AnnotatedSchema


def test_no_vspec_basic_fields() -> None:
    """Test that only default fields appear without @vspec directive."""
    schema_str = """
    type Vehicle {
        \"\"\"Current vehicle speed\"\"\"
        speed: Float
    }
    """
    schema = build_schema(schema_str)
    annotated = AnnotatedSchema(schema=schema, field_metadata={}, type_metadata={})
    exporter = JsonExporter(schema, annotated)

    result = exporter.export(root_type="Vehicle")
    speed = result["Vehicle"]["children"]["speed"]

    # Should have: description, datatype
    assert "description" in speed
    assert speed["description"] == "Current vehicle speed"
    assert "datatype" in speed
    assert speed["datatype"] == "float"

    # Should NOT have: type, comment, allowed, default
    assert "type" not in speed
    assert "comment" not in speed
    assert "allowed" not in speed
    assert "default" not in speed


def test_no_vspec_with_range() -> None:
    """Test that @range directive values are included without @vspec."""
    schema_str = """
    directive @range(min: Float, max: Float) on FIELD_DEFINITION

    type Vehicle {
        \"\"\"Vehicle speed in km/h\"\"\"
        speed: Float @range(min: 0.0, max: 250.0)
    }
    """
    schema = build_schema(schema_str)
    annotated = AnnotatedSchema(schema=schema, field_metadata={}, type_metadata={})
    exporter = JsonExporter(schema, annotated)

    result = exporter.export(root_type="Vehicle")
    speed = result["Vehicle"]["children"]["speed"]

    # Should have: description, datatype, min, max
    assert speed["description"] == "Vehicle speed in km/h"
    assert speed["datatype"] == "float"
    assert speed["min"] == 0.0
    assert speed["max"] == 250.0

    # Should NOT have: type, comment
    assert "type" not in speed
    assert "comment" not in speed


def test_no_vspec_with_unit() -> None:
    """Test that unit field argument is included without @vspec."""
    schema_str = """
    enum SpeedUnit {
        KILOMETER_PER_HOUR
        METER_PER_SECOND
    }

    type Vehicle {
        \"\"\"Vehicle speed\"\"\"
        speed(unit: SpeedUnit = KILOMETER_PER_HOUR): Float
    }
    """
    schema = build_schema(schema_str)
    annotated = AnnotatedSchema(schema=schema, field_metadata={}, type_metadata={})
    exporter = JsonExporter(schema, annotated)

    result = exporter.export(root_type="Vehicle")
    speed = result["Vehicle"]["children"]["speed"]

    # Should have: description, datatype, unit
    assert speed["description"] == "Vehicle speed"
    assert speed["datatype"] == "float"
    assert speed["unit"] == "KILOMETER_PER_HOUR"

    # Should NOT have: type, comment
    assert "type" not in speed
    assert "comment" not in speed


def test_no_vspec_enum_field() -> None:
    """Test that enum fields don't include 'allowed' without @vspec."""
    schema_str = """
    enum GearPosition {
        PARK
        REVERSE
        NEUTRAL
        DRIVE
    }

    type Vehicle {
        \"\"\"Current gear position\"\"\"
        gear: GearPosition
    }
    """
    schema = build_schema(schema_str)
    annotated = AnnotatedSchema(schema=schema, field_metadata={}, type_metadata={})
    exporter = JsonExporter(schema, annotated)

    result = exporter.export(root_type="Vehicle")
    gear = result["Vehicle"]["children"]["gear"]

    # Should have: description, datatype
    assert gear["description"] == "Current gear position"
    assert gear["datatype"] == "string"

    # Should NOT have: allowed, type
    assert "allowed" not in gear
    assert "type" not in gear


def test_no_vspec_with_metadata_directive() -> None:
    """Test that @metadata directive is ignored without @vspec."""
    schema_str = """
    directive @metadata(comment: String, vssType: String) on FIELD_DEFINITION

    type Vehicle {
        \"\"\"Vehicle speed\"\"\"
        speed: Float @metadata(comment: "This is a comment", vssType: "sensor")
    }
    """
    schema = build_schema(schema_str)
    annotated = AnnotatedSchema(schema=schema, field_metadata={}, type_metadata={})
    exporter = JsonExporter(schema, annotated)

    result = exporter.export(root_type="Vehicle")
    speed = result["Vehicle"]["children"]["speed"]

    # Should have: description, datatype
    assert speed["description"] == "Vehicle speed"
    assert speed["datatype"] == "float"

    # Should NOT have: comment, type (even though @metadata provides them)
    assert "comment" not in speed
    assert "type" not in speed


def test_no_vspec_complete_example() -> None:
    """Test complete example with all default fields but no @vspec."""
    schema_str = """
    directive @range(min: Float, max: Float) on FIELD_DEFINITION

    enum TemperatureUnit {
        CELSIUS
        FAHRENHEIT
    }

    type Vehicle {
        \"\"\"Exterior temperature\"\"\"
        temperature(unit: TemperatureUnit = CELSIUS): Float @range(min: -50.0, max: 50.0)

        \"\"\"Vehicle identification number\"\"\"
        vin: String
    }
    """
    schema = build_schema(schema_str)
    annotated = AnnotatedSchema(schema=schema, field_metadata={}, type_metadata={})
    exporter = JsonExporter(schema, annotated)

    result = exporter.export(root_type="Vehicle")

    # Check temperature field
    temperature = result["Vehicle"]["children"]["temperature"]
    assert temperature == {
        "description": "Exterior temperature",
        "datatype": "float",
        "min": -50.0,
        "max": 50.0,
        "unit": "CELSIUS"
    }

    # Check vin field
    vin = result["Vehicle"]["children"]["vin"]
    assert vin == {
        "description": "Vehicle identification number",
        "datatype": "string"
    }


def test_no_vspec_branch_nodes() -> None:
    """Test that branch nodes (nested types) work without @vspec."""
    schema_str = """
    type Door {
        \"\"\"Is door open\"\"\"
        isOpen: Boolean
    }

    type Vehicle {
        \"\"\"Vehicle door\"\"\"
        door: Door
    }
    """
    schema = build_schema(schema_str)
    annotated = AnnotatedSchema(schema=schema, field_metadata={}, type_metadata={})
    exporter = JsonExporter(schema, annotated)

    result = exporter.export(root_type="Vehicle")

    # Check branch node
    door = result["Vehicle"]["children"]["door"]
    assert door["type"] == "branch"  # Branch type is always included
    assert door["description"] == "Vehicle door"
    assert "children" in door

    # Check leaf node within branch
    is_open = door["children"]["isOpen"]
    assert is_open == {
        "description": "Is door open",
        "datatype": "boolean"
    }
