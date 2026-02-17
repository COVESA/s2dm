"""Tests for IDExporter with diff-based variant ID generation.

This module tests the IDExporter integration with graphql-inspector diff output.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from graphql import GraphQLSchema

from s2dm.exporters.id import IDExporter
from s2dm.registry.variant_ids import VariantIDFile
from s2dm.tools.diff_parser import DiffChange

SchemaBuilder = Callable[[str], GraphQLSchema]

# Schema constants for reusable test scenarios
SIMPLE_WINDOW_SCHEMA = """
type Query {
    window: Window
}

type Window {
    position: Float
}
"""

WINDOW_WITH_INT_POSITION_SCHEMA = """
type Query {
    window: Window
}

type Window {
    position: Int
}
"""

WINDOW_WITH_DESCRIPTION_SCHEMA = """
type Query {
    window: Window
}

type Window {
    position: Float
    description: String
}
"""

WINDOW_WITH_ENUM_SCHEMA = """
type Query {
    window: Window
}

type Window {
    position: Float
    state: WindowState
}

enum WindowState {
    OPEN
    CLOSED
}
"""

WINDOW_WITH_ENUM_EXPANDED_SCHEMA = """
type Query {
    window: Window
}

type Window {
    position: Float
    state: WindowState
}

enum WindowState {
    OPEN
    CLOSED
    LOCKED
}
"""

MULTI_TYPE_WITH_SHARED_ENUM_SCHEMA = """
type Query {
    window: Window
    door: Door
}

type Window {
    state: WindowState
}

type Door {
    state: WindowState
}

enum WindowState {
    OPEN
    CLOSED
}
"""

SIMPLE_TEST_SCHEMA = """
type Query {
    test: Test
}

type Test {
    field: String
}
"""

VEHICLE_WITH_ENUM_SCHEMA = """
type Query {
    vehicle: Vehicle
}

type Vehicle {
    speed: Float
    state: VehicleState
}

enum VehicleState {
    ON
    OFF
}
"""


# Helper functions


def save_previous_ids(path: Path, concepts: dict[str, dict[str, Any]], version_tag: str = "v1.0.0") -> None:
    """Save previous IDs to a JSON file.

    Args:
        path: Path to write the JSON file
        concepts: Dict mapping concept names to their ID info
        version_tag: Version tag for the IDs file
    """
    with open(path, "w") as f:
        json.dump({"version_tag": version_tag, "concepts": concepts}, f)


def create_diff_change(
    change_type: str,
    concept_name: str,
    criticality: str,
    message: str = "",
    **extra_fields: Any,
) -> DiffChange:
    """Create DiffChange objects with minimal boilerplate.

    Args:
        change_type: Type of change (e.g., "FIELD_TYPE_CHANGED", "ENUM_VALUE_ADDED")
        concept_name: The concept name affected by the change
        criticality: Criticality level ("BREAKING", "DANGEROUS", or "NON_BREAKING")
        message: Description message (optional)
        **extra_fields: Additional fields to include in the change

    Returns:
        DiffChange instance
    """
    # Infer action from change type name
    if "ADDED" in change_type:
        action = "insert"
    elif "REMOVED" in change_type:
        action = "delete"
    else:
        action = "update"

    return DiffChange.model_validate(
        {
            "type": change_type,
            "action": action,
            "criticality": criticality,
            "path": concept_name,
            "concept_name": concept_name,
            "message": message,
            **extra_fields,
        }
    )


def run_exporter(
    schema: GraphQLSchema,
    version_tag: str,
    output_path: Path,
    previous_ids_path: Path | None = None,
    diff_output: list[DiffChange] | None = None,
) -> VariantIDFile:
    """Run IDExporter with standard parameters.

    Args:
        schema: GraphQL schema to process
        version_tag: Version tag for the export
        output_path: Path to write IDs JSON file
        previous_ids_path: Optional path to previous IDs file
        diff_output: Optional diff output from graphql-inspector

    Returns:
        VariantIDFile result
    """
    exporter = IDExporter(
        schema=schema,
        version_tag=version_tag,
        output=output_path,
        previous_ids_path=previous_ids_path,
        diff_output=diff_output,
    )
    return exporter.run()


def test_id_exporter_generates_variant_ids(temp_output_paths: dict[str, Path], schema_builder: SchemaBuilder) -> None:
    """Test that IDExporter generates variant-based IDs."""
    schema = schema_builder(VEHICLE_WITH_ENUM_SCHEMA)

    result = run_exporter(
        schema=schema,
        version_tag="v1.0.0",
        output_path=temp_output_paths["ids"],
    )

    # Check that result has version_tag and concepts
    assert result.version_tag == "v1.0.0"  # version_tag is required
    assert result.concepts is not None

    # Check that IDs are in semantic version format (Concept/vM.m)
    assert "Vehicle" in result.concepts  # Object type should be included
    assert result.concepts["Vehicle"].id == "Vehicle/v1.0"
    assert result.concepts["Vehicle"].variant == (1, 0)
    assert result.concepts["Vehicle"].variant_counter == 1

    assert "Vehicle.speed" in result.concepts
    assert result.concepts["Vehicle.speed"].id == "Vehicle.speed/v1.0"
    assert result.concepts["Vehicle.speed"].variant == (1, 0)
    assert result.concepts["Vehicle.speed"].variant_counter == 1

    assert "VehicleState" in result.concepts
    assert result.concepts["VehicleState"].id == "VehicleState/v1.0"
    assert result.concepts["VehicleState"].variant == (1, 0)
    assert result.concepts["VehicleState"].variant_counter == 1


def test_id_exporter_uses_previous_ids(temp_output_paths: dict[str, Path], schema_builder: SchemaBuilder) -> None:
    """Test that IDExporter uses previous IDs to track variants."""
    schema = schema_builder(SIMPLE_WINDOW_SCHEMA)

    # Create previous variant IDs file
    save_previous_ids(
        temp_output_paths["previous_ids"],
        {
            "Window": {"id": "Window/v1.0", "variant_counter": 1},
            "Window.position": {"id": "Window.position/v1.0", "variant_counter": 1},
        },
    )

    # First run with same schema - should stay at v1.0
    result = run_exporter(
        schema=schema,
        version_tag="v1.0.0",
        output_path=temp_output_paths["ids"],
        previous_ids_path=temp_output_paths["previous_ids"],
    )

    assert result.concepts["Window"].id == "Window/v1.0"
    assert result.concepts["Window"].variant == (1, 0)
    assert result.concepts["Window.position"].id == "Window.position/v1.0"
    assert result.concepts["Window.position"].variant == (1, 0)


def test_id_exporter_increments_variant_on_change(
    temp_output_paths: dict[str, Path], schema_builder: SchemaBuilder
) -> None:
    """Test that IDExporter increments variant when field changes according to diff."""
    schema = schema_builder(WINDOW_WITH_INT_POSITION_SCHEMA)

    # Create previous variant IDs file
    save_previous_ids(
        temp_output_paths["previous_ids"],
        {
            "Window": {"id": "Window/v1.0", "variant_counter": 1},
            "Window.position": {"id": "Window.position/v1.0", "variant_counter": 1},
        },
    )

    # Create diff output indicating field type changed
    diff = [
        create_diff_change(
            "FIELD_TYPE_CHANGED",
            "Window.position",
            "BREAKING",
            message="Field 'Window.position' changed type from 'Float' to 'Int'",
            meta={"oldFieldType": "Float", "newFieldType": "Int"},
        )
    ]

    # Run with changed schema
    result = run_exporter(
        schema=schema,
        version_tag="v1.1.0",
        output_path=temp_output_paths["ids"],
        previous_ids_path=temp_output_paths["previous_ids"],
        diff_output=diff,
    )

    # Breaking change should increment major version (v1.0 → v2.0)
    assert result.concepts["Window.position"].id == "Window.position/v2.0"
    assert result.concepts["Window.position"].variant == (2, 0)
    # variant_counter should increment for this concept (1 → 2)
    assert result.concepts["Window.position"].variant_counter == 2
    # Window object type should also increment due to field change (breaking change)
    assert result.concepts["Window"].id == "Window/v2.0"
    assert result.concepts["Window"].variant == (2, 0)
    assert result.concepts["Window"].variant_counter == 2


def test_id_exporter_increments_minor_for_non_breaking_changes(
    temp_output_paths: dict[str, Path], schema_builder: SchemaBuilder
) -> None:
    """Test that IDExporter increments minor version for non-breaking changes."""
    schema = schema_builder(WINDOW_WITH_DESCRIPTION_SCHEMA)

    # Create previous variant IDs file
    save_previous_ids(
        temp_output_paths["previous_ids"],
        {
            "Window": {"id": "Window/v1.0", "variant_counter": 1},
            "Window.position": {"id": "Window.position/v1.0", "variant_counter": 1},
        },
    )

    # Create diff output indicating non-breaking change (field added)
    diff = [
        create_diff_change(
            "FIELD_ADDED",
            "Window.description",
            "NON_BREAKING",
            message="Field 'description' was added to object type 'Window'",
        )
    ]

    # Run with new field added (non-breaking)
    result = run_exporter(
        schema=schema,
        version_tag="v1.1.0",
        output_path=temp_output_paths["ids"],
        previous_ids_path=temp_output_paths["previous_ids"],
        diff_output=diff,
    )

    # position should remain unchanged
    assert result.concepts["Window.position"].id == "Window.position/v1.0"
    assert result.concepts["Window.position"].variant == (1, 0)
    assert result.concepts["Window.position"].variant_counter == 1

    # Window object type should increment minor version (non-breaking change)
    assert result.concepts["Window"].id == "Window/v1.1"
    assert result.concepts["Window"].variant == (1, 1)
    assert result.concepts["Window"].variant_counter == 2

    # New field should start at v1.0
    assert result.concepts["Window.description"].id == "Window.description/v1.0"
    assert result.concepts["Window.description"].variant == (1, 0)
    assert result.concepts["Window.description"].variant_counter == 1


def test_id_exporter_handles_removed_fields(temp_output_paths: dict[str, Path], schema_builder: SchemaBuilder) -> None:
    """Test that IDExporter marks removed fields with removed_in_version."""
    schema = schema_builder(SIMPLE_WINDOW_SCHEMA)

    # Create previous variant IDs file with oldField that will be removed
    save_previous_ids(
        temp_output_paths["previous_ids"],
        {
            "Window": {"id": "Window/v1.0", "variant_counter": 1},
            "Window.position": {"id": "Window.position/v1.0", "variant_counter": 1},
            "Window.oldField": {"id": "Window.oldField/v1.0", "variant_counter": 1},
        },
    )

    # Create diff output indicating field was removed
    diff = [
        create_diff_change(
            "FIELD_REMOVED",
            "Window.oldField",
            "BREAKING",
            message="Field 'oldField' was removed from object type 'Window'",
        )
    ]

    # Run with new schema (oldField removed)
    result = run_exporter(
        schema=schema,
        version_tag="v1.1.0",
        output_path=temp_output_paths["ids"],
        previous_ids_path=temp_output_paths["previous_ids"],
        diff_output=diff,
    )

    # oldField should be marked as removed
    assert "Window.oldField" in result.concepts
    assert result.concepts["Window.oldField"].removed_in_version == "v1.1.0"
    assert result.concepts["Window.oldField"].variant == (1, 0)

    # Window object type should increment due to field removal (breaking change)
    assert result.concepts["Window"].id == "Window/v2.0"
    assert result.concepts["Window"].variant == (2, 0)
    assert result.concepts["Window"].variant_counter == 2

    # position should remain unchanged
    assert result.concepts["Window.position"].id == "Window.position/v1.0"
    assert result.concepts["Window.position"].removed_in_version is None


def test_id_exporter_output_format(temp_output_paths: dict[str, Path], schema_builder: SchemaBuilder) -> None:
    """Test that IDExporter output format includes metadata."""
    schema = schema_builder(SIMPLE_TEST_SCHEMA)

    # Run exporter
    result = run_exporter(
        schema=schema,
        version_tag="v1.0.0",
        output_path=temp_output_paths["ids"],
    )

    # Verify output file format
    saved_file = VariantIDFile.load(temp_output_paths["ids"])

    assert saved_file.version_tag == "v1.0.0"
    assert "Test" in saved_file.concepts  # Object type should be included
    assert saved_file.concepts["Test"].variant_counter == 1
    assert "Test.field" in saved_file.concepts
    assert saved_file.concepts["Test.field"].id == "Test.field/v1.0"
    assert saved_file.concepts["Test.field"].variant == (1, 0)
    assert saved_file.concepts["Test.field"].variant_counter == 1

    # Verify result matches saved file
    assert result.version_tag == saved_file.version_tag
    assert result.concepts["Test.field"].id == saved_file.concepts["Test.field"].id


def test_enum_value_added_breaking(temp_output_paths: dict[str, Path], schema_builder: SchemaBuilder) -> None:
    """Test that adding an enum value (BREAKING) increments the enum variant."""
    schema = schema_builder(WINDOW_WITH_ENUM_EXPANDED_SCHEMA)

    # Create previous IDs with smaller enum
    save_previous_ids(
        temp_output_paths["previous_ids"],
        {
            "Window": {"id": "Window/v1.0", "variant_counter": 1},
            "Window.position": {"id": "Window.position/v1.0", "variant_counter": 1},
            "Window.state": {"id": "Window.state/v1.0", "variant_counter": 1},
            "WindowState": {"id": "WindowState/v1.0", "variant_counter": 1},
        },
    )

    # Enum value added (DANGEROUS criticality treated as BREAKING)
    diff = [
        create_diff_change(
            "ENUM_VALUE_ADDED",
            "WindowState",
            "DANGEROUS",
            message="Enum value 'LOCKED' was added to enum 'WindowState'",
        )
    ]

    result = run_exporter(
        schema=schema,
        version_tag="v1.1.0",
        output_path=temp_output_paths["ids"],
        previous_ids_path=temp_output_paths["previous_ids"],
        diff_output=diff,
    )

    # WindowState enum should increment major version
    assert result.concepts["WindowState"].id == "WindowState/v2.0"
    assert result.concepts["WindowState"].variant == (2, 0)
    assert result.concepts["WindowState"].variant_counter == 2


def test_enum_value_removed(temp_output_paths: dict[str, Path], schema_builder: SchemaBuilder) -> None:
    """Test that removing an enum value (BREAKING) increments the enum variant."""
    schema = schema_builder(WINDOW_WITH_ENUM_SCHEMA)

    # Create previous IDs with larger enum (included LOCKED)
    save_previous_ids(
        temp_output_paths["previous_ids"],
        {
            "Window": {"id": "Window/v1.0", "variant_counter": 1},
            "Window.position": {"id": "Window.position/v1.0", "variant_counter": 1},
            "Window.state": {"id": "Window.state/v1.0", "variant_counter": 1},
            "WindowState": {"id": "WindowState/v1.0", "variant_counter": 1},
        },
    )

    # Enum value removed
    diff = [
        create_diff_change(
            "ENUM_VALUE_REMOVED",
            "WindowState",
            "BREAKING",
            message="Enum value 'LOCKED' was removed from enum 'WindowState'",
        )
    ]

    result = run_exporter(
        schema=schema,
        version_tag="v1.1.0",
        output_path=temp_output_paths["ids"],
        previous_ids_path=temp_output_paths["previous_ids"],
        diff_output=diff,
    )

    # WindowState enum should increment major version (breaking change)
    assert result.concepts["WindowState"].id == "WindowState/v2.0"
    assert result.concepts["WindowState"].variant == (2, 0)
    assert result.concepts["WindowState"].variant_counter == 2


def test_enum_change_propagates_across_types(temp_output_paths: dict[str, Path], schema_builder: SchemaBuilder) -> None:
    """Test that enum changes affect all object types that use the enum."""
    schema = schema_builder(MULTI_TYPE_WITH_SHARED_ENUM_SCHEMA)

    # Create previous IDs
    save_previous_ids(
        temp_output_paths["previous_ids"],
        {
            "Window": {"id": "Window/v1.0", "variant_counter": 1},
            "Window.state": {"id": "Window.state/v1.0", "variant_counter": 1},
            "Door": {"id": "Door/v1.0", "variant_counter": 1},
            "Door.state": {"id": "Door.state/v1.0", "variant_counter": 1},
            "WindowState": {"id": "WindowState/v1.0", "variant_counter": 1},
        },
    )

    # WindowState enum changes
    diff = [
        create_diff_change(
            "ENUM_VALUE_ADDED",
            "WindowState",
            "DANGEROUS",
            message="Enum value 'LOCKED' was added to enum 'WindowState'",
        )
    ]

    result = run_exporter(
        schema=schema,
        version_tag="v1.1.0",
        output_path=temp_output_paths["ids"],
        previous_ids_path=temp_output_paths["previous_ids"],
        diff_output=diff,
    )

    # WindowState enum should increment
    assert result.concepts["WindowState"].id == "WindowState/v2.0"
    assert result.concepts["WindowState"].variant == (2, 0)
    assert result.concepts["WindowState"].variant_counter == 2

    # Fields using the enum DO get incremented when the enum changes
    # The IDExporter propagates enum changes to all fields using that enum
    assert result.concepts["Window.state"].id == "Window.state/v2.0"
    assert result.concepts["Window.state"].variant == (2, 0)
    assert result.concepts["Window.state"].variant_counter == 2
    assert result.concepts["Door.state"].id == "Door.state/v2.0"
    assert result.concepts["Door.state"].variant == (2, 0)
    assert result.concepts["Door.state"].variant_counter == 2

    # Parent types DO NOT increment in the current implementation
    # Enum propagation to fields doesn't trigger parent type increments
    # Only direct field changes in the diff trigger parent type increments
    assert result.concepts["Window"].id == "Window/v1.0"
    assert result.concepts["Door"].id == "Door/v1.0"


def test_multiple_changes_to_same_concept_increment_once(
    temp_output_paths: dict[str, Path], schema_builder: SchemaBuilder
) -> None:
    """Test that multiple changes to same concept only increment variant_counter once."""
    schema = schema_builder(WINDOW_WITH_ENUM_EXPANDED_SCHEMA)

    # Create previous IDs
    save_previous_ids(
        temp_output_paths["previous_ids"],
        {
            "Window": {"id": "Window/v1.0", "variant_counter": 1},
            "Window.position": {"id": "Window.position/v1.0", "variant_counter": 1},
            "Window.state": {"id": "Window.state/v1.0", "variant_counter": 1},
            "WindowState": {"id": "WindowState/v1.0", "variant_counter": 1},
        },
    )

    # Multiple enum value changes (should only increment once)
    diff = [
        create_diff_change(
            "ENUM_VALUE_ADDED",
            "WindowState",
            "DANGEROUS",
            message="Enum value 'LOCKED' was added",
        ),
        create_diff_change(
            "ENUM_VALUE_ADDED",
            "WindowState",
            "DANGEROUS",
            message="Enum value 'BROKEN' was added",
        ),
    ]

    result = run_exporter(
        schema=schema,
        version_tag="v1.1.0",
        output_path=temp_output_paths["ids"],
        previous_ids_path=temp_output_paths["previous_ids"],
        diff_output=diff,
    )

    # WindowState should only increment variant_counter by 1 (not 2)
    assert result.concepts["WindowState"].id == "WindowState/v2.0"
    assert result.concepts["WindowState"].variant == (2, 0)
    assert result.concepts["WindowState"].variant_counter == 2  # Not 3!


def test_mixed_breaking_and_non_breaking_uses_breaking(
    temp_output_paths: dict[str, Path], schema_builder: SchemaBuilder
) -> None:
    """Test that mixed criticalities use the highest (breaking wins over non-breaking)."""
    schema = schema_builder(WINDOW_WITH_DESCRIPTION_SCHEMA)

    # Create previous IDs
    save_previous_ids(
        temp_output_paths["previous_ids"],
        {
            "Window": {"id": "Window/v1.0", "variant_counter": 1},
            "Window.position": {"id": "Window.position/v1.0", "variant_counter": 1},
        },
    )

    # Mixed criticality changes to Window
    diff = [
        create_diff_change(
            "FIELD_ADDED",
            "Window.description",
            "NON_BREAKING",
            message="Field 'description' was added",
        ),
        create_diff_change(
            "FIELD_TYPE_CHANGED",
            "Window.position",
            "BREAKING",
            message="Field 'position' changed type",
        ),
    ]

    result = run_exporter(
        schema=schema,
        version_tag="v1.1.0",
        output_path=temp_output_paths["ids"],
        previous_ids_path=temp_output_paths["previous_ids"],
        diff_output=diff,
    )

    # Window should increment major version (breaking wins)
    assert result.concepts["Window"].id == "Window/v2.0"
    assert result.concepts["Window"].variant == (2, 0)
    assert result.concepts["Window"].variant_counter == 2


def test_no_changes_with_empty_diff(temp_output_paths: dict[str, Path], schema_builder: SchemaBuilder) -> None:
    """Test that empty diff results in no version increments."""
    schema = schema_builder(SIMPLE_WINDOW_SCHEMA)

    # Create previous IDs
    save_previous_ids(
        temp_output_paths["previous_ids"],
        {
            "Window": {"id": "Window/v1.0", "variant_counter": 1},
            "Window.position": {"id": "Window.position/v1.0", "variant_counter": 1},
        },
    )

    # Empty diff (no changes)
    diff: list[DiffChange] = []

    result = run_exporter(
        schema=schema,
        version_tag="v1.1.0",
        output_path=temp_output_paths["ids"],
        previous_ids_path=temp_output_paths["previous_ids"],
        diff_output=diff,
    )

    # All concepts should remain unchanged
    assert result.concepts["Window"].id == "Window/v1.0"
    assert result.concepts["Window"].variant == (1, 0)
    assert result.concepts["Window"].variant_counter == 1
    assert result.concepts["Window.position"].id == "Window.position/v1.0"
    assert result.concepts["Window.position"].variant == (1, 0)
    assert result.concepts["Window.position"].variant_counter == 1


def test_variant_counter_continues_across_updates(
    temp_output_paths: dict[str, Path], schema_builder: SchemaBuilder
) -> None:
    """Test that variant_counter increments correctly across multiple updates: 1→2→3."""
    schema = schema_builder(SIMPLE_WINDOW_SCHEMA)

    # Initial state
    save_previous_ids(
        temp_output_paths["previous_ids"],
        {
            "Window": {"id": "Window/v1.0", "variant_counter": 1},
            "Window.position": {"id": "Window.position/v1.0", "variant_counter": 1},
        },
    )

    # First update (breaking change)
    diff1 = [
        create_diff_change(
            "FIELD_TYPE_CHANGED",
            "Window.position",
            "BREAKING",
            message="Changed to Int",
        )
    ]

    result1 = run_exporter(
        schema=schema,
        version_tag="v1.1.0",
        output_path=temp_output_paths["ids"],
        previous_ids_path=temp_output_paths["previous_ids"],
        diff_output=diff1,
    )

    # After first update: counter should be 2
    assert result1.concepts["Window.position"].variant_counter == 2
    assert result1.concepts["Window.position"].variant == (2, 0)

    # Save for next iteration
    result1.save(temp_output_paths["previous_ids"])

    # Second update (non-breaking change)
    diff2 = [
        create_diff_change(
            "FIELD_DESCRIPTION_CHANGED",
            "Window.position",
            "NON_BREAKING",
            message="Description updated",
        )
    ]

    result2 = run_exporter(
        schema=schema,
        version_tag="v1.2.0",
        output_path=temp_output_paths["ids"],
        previous_ids_path=temp_output_paths["previous_ids"],
        diff_output=diff2,
    )

    # After second update: counter should be 3
    assert result2.concepts["Window.position"].variant_counter == 3
    assert result2.concepts["Window.position"].variant == (2, 1)  # Major stays, minor increments


@pytest.mark.parametrize(
    "criticality,expected_major,expected_minor",
    [
        ("BREAKING", 2, 0),
        ("DANGEROUS", 2, 0),
        ("NON_BREAKING", 1, 1),
    ],
)
def test_criticality_levels_version_increments(
    criticality: str,
    expected_major: int,
    expected_minor: int,
    temp_output_paths: dict[str, Path],
    schema_builder: SchemaBuilder,
) -> None:
    """Test that different criticality levels produce correct version increments."""
    schema = schema_builder(WINDOW_WITH_DESCRIPTION_SCHEMA)

    # Create previous IDs
    save_previous_ids(
        temp_output_paths["previous_ids"],
        {
            "Window": {"id": "Window/v1.0", "variant_counter": 1},
            "Window.position": {"id": "Window.position/v1.0", "variant_counter": 1},
        },
    )

    # Create diff with specified criticality
    diff = [
        create_diff_change(
            "FIELD_ADDED",
            "Window.description",
            criticality,
            message=f"Field added with {criticality} criticality",
        )
    ]

    result = run_exporter(
        schema=schema,
        version_tag="v1.1.0",
        output_path=temp_output_paths["ids"],
        previous_ids_path=temp_output_paths["previous_ids"],
        diff_output=diff,
    )

    # Window object type should increment according to criticality
    assert result.concepts["Window"].variant == (expected_major, expected_minor)
    # variant_counter always increments by 1
    assert result.concepts["Window"].variant_counter == 2


@pytest.mark.parametrize(
    "change_type,expected_criticality",
    [
        ("FIELD_REMOVED", "BREAKING"),
        ("FIELD_TYPE_CHANGED", "BREAKING"),
        ("ENUM_VALUE_REMOVED", "BREAKING"),
        ("FIELD_ADDED", "NON_BREAKING"),
        ("TYPE_ADDED", "NON_BREAKING"),
    ],
)
def test_change_types_produce_expected_criticality(
    change_type: str,
    expected_criticality: str,
    temp_output_paths: dict[str, Path],
    schema_builder: SchemaBuilder,
) -> None:
    """Test that specific change types produce expected criticality levels."""
    schema = schema_builder(SIMPLE_WINDOW_SCHEMA)

    # Create previous IDs
    save_previous_ids(
        temp_output_paths["previous_ids"],
        {
            "Window": {"id": "Window/v1.0", "variant_counter": 1},
            "Window.position": {"id": "Window.position/v1.0", "variant_counter": 1},
        },
    )

    # Create diff with specified change type
    diff = [
        create_diff_change(
            change_type,
            "Window.position",
            expected_criticality,
            message=f"{change_type} occurred",
        )
    ]

    result = run_exporter(
        schema=schema,
        version_tag="v1.1.0",
        output_path=temp_output_paths["ids"],
        previous_ids_path=temp_output_paths["previous_ids"],
        diff_output=diff,
    )

    # Verify the increment matches the expected criticality
    is_breaking = expected_criticality in ("BREAKING", "DANGEROUS")
    expected_variant = (2, 0) if is_breaking else (1, 1)

    assert result.concepts["Window.position"].variant == expected_variant
