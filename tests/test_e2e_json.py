"""End-to-end tests for JSON tree exporter CLI."""

import json
from pathlib import Path

from click.testing import CliRunner

from s2dm.cli import cli


def test_json_export_cli_basic(tmp_path: Path, spec_directory: Path) -> None:
    """Test basic JSON export via CLI."""
    output_file = tmp_path / "output.json"
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "export",
            "json",
            "-s",
            str(spec_directory / "common.graphql"),
            "-o",
            str(output_file),
        ],
    )

    assert result.exit_code == 0, f"CLI failed with: {result.output}"
    assert output_file.exists()

    # Validate JSON structure
    data = json.loads(output_file.read_text())
    assert isinstance(data, dict)
    assert len(data) > 0

    # Check that at least one type was exported (no 'type' key in default mode)
    for _type_name, type_data in data.items():
        assert "type" not in type_data  # No type in default mode
        if "children" in type_data:
            assert isinstance(type_data["children"], dict)
        break


def test_json_export_with_root_type(tmp_path: Path) -> None:
    """Test JSON export with specific root type."""
    output_file = tmp_path / "output.json"
    runner = CliRunner()

    # Create a simple test schema
    schema_file = tmp_path / "test_schema.graphql"
    schema_file.write_text(
        """
    type Vehicle {
        speed: Float
        doors: Int
    }

    type Building {
        floors: Int
    }
    """
    )

    result = runner.invoke(
        cli,
        [
            "export",
            "json",
            "-s",
            str(schema_file),
            "--root-type",
            "Vehicle",
            "-o",
            str(output_file),
        ],
    )

    assert result.exit_code == 0
    assert output_file.exists()

    data = json.loads(output_file.read_text())
    assert "Vehicle" in data
    assert "Building" not in data  # Should only export Vehicle


def test_json_export_with_directives(tmp_path: Path) -> None:
    """Test JSON export with @range directive (no @vspec)."""
    runner = CliRunner()
    schema_file = tmp_path / "test_schema.graphql"
    schema_file.write_text(
        """
    directive @range(min: Float, max: Float) on FIELD_DEFINITION
    directive @metadata(comment: String, vssType: String) on FIELD_DEFINITION

    type Vehicle {
        \"\"\"Vehicle speed in km/h\"\"\"
        speed: Float @range(min: 0.0, max: 250.0) @metadata(vssType: "sensor", comment: "Test comment")

        \"\"\"Number of doors\"\"\"
        doorCount: Int @metadata(vssType: "attribute")
    }
    """
    )

    output_file = tmp_path / "output.json"

    result = runner.invoke(
        cli,
        [
            "export",
            "json",
            "-s",
            str(schema_file),
            "-o",
            str(output_file),
        ],
    )

    assert result.exit_code == 0
    data = json.loads(output_file.read_text())

    vehicle = data["Vehicle"]
    assert "children" in vehicle

    speed = vehicle["children"]["speed"]
    assert speed["datatype"] == "Float"
    assert speed["min"] == 0.0
    assert speed["max"] == 250.0
    assert speed["description"] == "Vehicle speed in km/h"
    # @metadata is ignored without @vspec
    assert "type" not in speed
    assert "comment" not in speed

    door_count = vehicle["children"]["doorCount"]
    assert "type" not in door_count


def test_json_export_with_enum(tmp_path: Path) -> None:
    """Test JSON export with enum types (no @vspec means no allowed field)."""
    runner = CliRunner()
    schema_file = tmp_path / "test_schema.graphql"
    schema_file.write_text(
        """
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
    )

    output_file = tmp_path / "output.json"

    result = runner.invoke(
        cli,
        [
            "export",
            "json",
            "-s",
            str(schema_file),
            "-o",
            str(output_file),
        ],
    )

    assert result.exit_code == 0
    data = json.loads(output_file.read_text())

    gear = data["Vehicle"]["children"]["gear"]
    assert gear["datatype"] == "GearPosition"
    # No allowed field without @vspec
    assert "allowed" not in gear


def test_json_export_nested_types(tmp_path: Path) -> None:
    """Test JSON export with nested object types."""
    runner = CliRunner()
    schema_file = tmp_path / "test_schema.graphql"
    schema_file.write_text(
        """
    type Door {
        \"\"\"Is door open\"\"\"
        isOpen: Boolean

        \"\"\"Is door locked\"\"\"
        isLocked: Boolean
    }

    type Vehicle {
        \"\"\"Vehicle doors\"\"\"
        door: Door

        \"\"\"Vehicle speed\"\"\"
        speed: Float
    }
    """
    )

    output_file = tmp_path / "output.json"

    result = runner.invoke(
        cli,
        [
            "export",
            "json",
            "-s",
            str(schema_file),
            "-o",
            str(output_file),
        ],
    )

    assert result.exit_code == 0
    data = json.loads(output_file.read_text())

    vehicle = data["Vehicle"]
    assert "door" in vehicle["children"]

    door = vehicle["children"]["door"]
    assert "type" not in door  # No type in default mode
    assert door["description"] == "Vehicle doors"
    assert "children" in door
    assert "isOpen" in door["children"]
    assert "isLocked" in door["children"]

    is_open = door["children"]["isOpen"]
    assert is_open["datatype"] == "Boolean"
    assert is_open["description"] == "Is door open"


def test_json_export_array_types(tmp_path: Path) -> None:
    """Test JSON export with array types."""
    runner = CliRunner()
    schema_file = tmp_path / "test_schema.graphql"
    schema_file.write_text(
        """
    scalar UInt8

    type Vehicle {
        seatPosCount: [UInt8]
    }
    """
    )

    output_file = tmp_path / "output.json"

    result = runner.invoke(
        cli,
        [
            "export",
            "json",
            "-s",
            str(schema_file),
            "-o",
            str(output_file),
        ],
    )

    assert result.exit_code == 0
    data = json.loads(output_file.read_text())

    seat_pos = data["Vehicle"]["children"]["seatPosCount"]
    assert seat_pos["datatype"] == "UInt8[]"


def test_json_export_creates_parent_dirs(tmp_path: Path) -> None:
    """Test that export creates parent directories if they don't exist."""
    runner = CliRunner()
    output_file = tmp_path / "nested" / "dir" / "output.json"

    schema_file = tmp_path / "test_schema.graphql"
    schema_file.write_text(
        """
    type Vehicle {
        speed: Float
    }
    """
    )

    result = runner.invoke(
        cli,
        [
            "export",
            "json",
            "-s",
            str(schema_file),
            "-o",
            str(output_file),
        ],
    )

    assert result.exit_code == 0
    assert output_file.exists()
    assert output_file.parent.exists()


def test_json_export_invalid_root_type(tmp_path: Path) -> None:
    """Test that invalid root type produces an error."""
    runner = CliRunner()
    schema_file = tmp_path / "test_schema.graphql"
    schema_file.write_text(
        """
    type Vehicle {
        speed: Float
    }
    """
    )

    output_file = tmp_path / "output.json"

    result = runner.invoke(
        cli,
        [
            "export",
            "json",
            "-s",
            str(schema_file),
            "--root-type",
            "NonExistent",
            "-o",
            str(output_file),
        ],
    )

    assert result.exit_code != 0
    assert "not found" in result.output.lower()


def test_json_export_with_selection_query(tmp_path: Path) -> None:
    """Test JSON export with selection query."""
    runner = CliRunner()
    schema_file = tmp_path / "test_schema.graphql"
    schema_file.write_text(
        """
    type Vehicle {
        speed: Float
        doors: Int
        engine: Engine
    }

    type Engine {
        power: Float
    }

    type Query {
        vehicle(id: ID!): Vehicle
    }
    """
    )

    query_file = tmp_path / "query.graphql"
    query_file.write_text(
        """
    {
        vehicle(id: "test") {
            speed
            doors
        }
    }
    """
    )

    output_file = tmp_path / "output.json"

    result = runner.invoke(
        cli,
        [
            "export",
            "json",
            "-s",
            str(schema_file),
            "--selection-query",
            str(query_file),
            "-o",
            str(output_file),
        ],
    )

    assert result.exit_code == 0
    data = json.loads(output_file.read_text())

    # After selection query, should only have the selected fields
    vehicle = data["Vehicle"]
    assert "speed" in vehicle["children"]
    assert "doors" in vehicle["children"]
    # Engine is not selected, so it should not be in the output
    assert "engine" not in vehicle["children"]
