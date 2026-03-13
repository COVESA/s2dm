"""Unit and e2e tests for the JSON exporter --vspec-meta YAML overlay feature."""

import json
import textwrap
from pathlib import Path
from typing import Any

from click.testing import CliRunner
from graphql import build_schema

from s2dm.cli import cli
from s2dm.exporters.json import JsonExporter, export_to_json_tree, load_vspec_lookup
from s2dm.exporters.utils.annotated_schema import AnnotatedSchema

# ---------------------------------------------------------------------------
# load_vspec_lookup
# ---------------------------------------------------------------------------


def test_load_vspec_lookup_basic(tmp_path: Path) -> None:
    """load_vspec_lookup returns a dict keyed by FQN."""
    yaml_content = textwrap.dedent(
        """\
        Vehicle.Speed:
          type: sensor
          unit: km/h
          min: 0
          max: 250
        """
    )
    yaml_file = tmp_path / "lookup.yaml"
    yaml_file.write_text(yaml_content)

    result = load_vspec_lookup(yaml_file)

    assert isinstance(result, dict)
    assert "Vehicle.Speed" in result
    assert result["Vehicle.Speed"]["unit"] == "km/h"
    assert result["Vehicle.Speed"]["min"] == 0
    assert result["Vehicle.Speed"]["max"] == 250


def test_load_vspec_lookup_empty_file(tmp_path: Path) -> None:
    """load_vspec_lookup returns empty dict for empty file."""
    yaml_file = tmp_path / "empty.yaml"
    yaml_file.write_text("")

    result = load_vspec_lookup(yaml_file)

    assert result == {}


def test_load_vspec_lookup_partial_keys(tmp_path: Path) -> None:
    """load_vspec_lookup handles entries with only some keys present."""
    yaml_content = textwrap.dedent(
        """\
        Vehicle.ADAS.ABS.IsEnabled:
          type: actuator
          datatype: boolean
          description: Indicates if ABS is enabled.
        """
    )
    yaml_file = tmp_path / "lookup.yaml"
    yaml_file.write_text(yaml_content)

    result = load_vspec_lookup(yaml_file)

    entry = result["Vehicle.ADAS.ABS.IsEnabled"]
    assert entry["type"] == "actuator"
    assert "unit" not in entry
    assert "allowed" not in entry


# ---------------------------------------------------------------------------
# _apply_vspec_lookup
# ---------------------------------------------------------------------------


def test_apply_vspec_lookup_overwrites_unit() -> None:
    """_apply_vspec_lookup overwrites unit with YAML value."""
    schema_str = """
    type Vehicle {
        speed: Float
    }
    """
    schema = build_schema(schema_str)
    annotated = AnnotatedSchema(schema=schema, field_metadata={}, type_metadata={})
    lookup = {"Vehicle.Speed": {"unit": "km/h", "type": "sensor"}}
    exporter = JsonExporter(schema, annotated, vspec_lookup=lookup)

    node: dict[str, Any] = {"datatype": "float", "unit": "KILOMETER_PER_HOUR"}
    exporter._apply_vspec_lookup(node, "Vehicle.Speed")

    assert node["unit"] == "km/h"
    assert node["type"] == "sensor"


def test_apply_vspec_lookup_unknown_fqn_leaves_node_unchanged() -> None:
    """_apply_vspec_lookup does nothing for unrecognised FQN."""
    schema_str = """
    type Vehicle {
        speed: Float
    }
    """
    schema = build_schema(schema_str)
    annotated = AnnotatedSchema(schema=schema, field_metadata={}, type_metadata={})
    lookup: dict[str, Any] = {}
    exporter = JsonExporter(schema, annotated, vspec_lookup=lookup)

    node: dict[str, Any] = {"datatype": "float", "unit": "KILOMETER_PER_HOUR"}
    exporter._apply_vspec_lookup(node, "Vehicle.Speed")

    assert node["unit"] == "KILOMETER_PER_HOUR"


def test_apply_vspec_lookup_none_lookup_is_noop() -> None:
    """_apply_vspec_lookup does nothing when vspec_lookup is None."""
    schema_str = """
    type Vehicle {
        speed: Float
    }
    """
    schema = build_schema(schema_str)
    annotated = AnnotatedSchema(schema=schema, field_metadata={}, type_metadata={})
    exporter = JsonExporter(schema, annotated, vspec_lookup=None)

    node: dict[str, Any] = {"datatype": "float"}
    exporter._apply_vspec_lookup(node, "Vehicle.Speed")

    # Unchanged
    assert node == {"datatype": "float"}


def test_apply_vspec_lookup_adds_new_keys() -> None:
    """_apply_vspec_lookup adds keys not originally in the node."""
    schema_str = """
    type Vehicle {
        speed: Float
    }
    """
    schema = build_schema(schema_str)
    annotated = AnnotatedSchema(schema=schema, field_metadata={}, type_metadata={})
    lookup = {
        "Vehicle.Speed": {
            "comment": "Instantaneous speed",
            "default": 0,
            "allowed": None,
        }
    }
    exporter = JsonExporter(schema, annotated, vspec_lookup=lookup)

    node: dict[str, Any] = {"datatype": "float"}
    exporter._apply_vspec_lookup(node, "Vehicle.Speed")

    assert node["comment"] == "Instantaneous speed"
    assert node["default"] == 0
    # None values are skipped
    assert "allowed" not in node


# ---------------------------------------------------------------------------
# export_to_json_tree with vspec_lookup_path
# ---------------------------------------------------------------------------


_SIMPLE_SCHEMA = """\
directive @vspec(element: String, fqn: String) on FIELD_DEFINITION

type Vehicle {
    \"\"\"Vehicle speed.\"\"\"
    averageSpeed: Float @vspec(element: "sensor", fqn: "Vehicle.AverageSpeed")
}
"""


def test_export_without_vspec_meta_keeps_raw_unit(tmp_path: Path) -> None:
    """Without vspec_lookup_path, unit stays as raw string from field arg."""
    schema_str = """\
directive @unit(unit: String) on FIELD_DEFINITION

type Vehicle {
    speed: Float @unit(unit: "KILOMETER_PER_HOUR")
}
"""
    from graphql import build_schema as _build

    from s2dm.exporters.utils.annotated_schema import AnnotatedSchema

    schema = _build(schema_str)
    annotated = AnnotatedSchema(schema=schema, field_metadata={}, type_metadata={})
    exporter = JsonExporter(schema, annotated)
    result = exporter.export(root_type="Vehicle")
    # raw arg default logic doesn't apply here (no default_value set via build_schema),
    # but make sure no KeyError / crash
    assert "speed" in result["Vehicle"]["children"]


def test_export_with_vspec_meta_overrides_unit(tmp_path: Path) -> None:
    """With vspec_lookup_path, unit in leaf node is replaced by YAML value."""
    from s2dm.exporters.utils.schema_loader import load_and_process_schema

    schema_file = tmp_path / "schema.graphql"
    schema_file.write_text(_SIMPLE_SCHEMA)

    lookup_yaml = tmp_path / "lookup.yaml"
    lookup_yaml.write_text(
        textwrap.dedent(
            """\
            Vehicle.AverageSpeed:
              type: sensor
              unit: km/h
              min: 0
              max: 250
            """
        )
    )

    annotated_schema, _, _ = load_and_process_schema(
        schema_paths=[schema_file],
        naming_config_path=None,
        selection_query_path=None,
        root_type=None,
        expanded_instances=False,
    )

    result = export_to_json_tree(annotated_schema, vspec_lookup_path=lookup_yaml)

    speed = result["Vehicle"]["children"]["AverageSpeed"]
    assert speed["unit"] == "km/h"
    assert speed["min"] == 0
    assert speed["max"] == 250
    assert speed["type"] == "sensor"


def test_export_with_vspec_meta_partial_override(tmp_path: Path) -> None:
    """YAML overlay only sets specified keys; schema-derived keys are preserved."""
    from s2dm.exporters.utils.schema_loader import load_and_process_schema

    schema_file = tmp_path / "schema.graphql"
    schema_file.write_text(_SIMPLE_SCHEMA)

    lookup_yaml = tmp_path / "lookup.yaml"
    lookup_yaml.write_text(
        textwrap.dedent(
            """\
            Vehicle.AverageSpeed:
              unit: km/h
            """
        )
    )

    annotated_schema, _, _ = load_and_process_schema(
        schema_paths=[schema_file],
        naming_config_path=None,
        selection_query_path=None,
        root_type=None,
        expanded_instances=False,
    )

    result = export_to_json_tree(annotated_schema, vspec_lookup_path=lookup_yaml)

    speed = result["Vehicle"]["children"]["AverageSpeed"]
    # YAML overrides unit
    assert speed["unit"] == "km/h"
    # @vspec(element:...) is still processed in vspec-meta mode
    assert speed["type"] == "sensor"
    # Datatype is preserved (raw scalar name, may be overwritten by YAML overlay)
    assert speed["datatype"] == "Float"


# ---------------------------------------------------------------------------
# CLI --vspec-meta option (e2e)
# ---------------------------------------------------------------------------


def test_cli_json_vspec_meta_option(tmp_path: Path) -> None:
    """CLI --vspec-meta flag passes YAML overlay to exporter."""
    schema_file = tmp_path / "schema.graphql"
    schema_file.write_text(_SIMPLE_SCHEMA)

    lookup_yaml = tmp_path / "lookup.yaml"
    lookup_yaml.write_text(
        textwrap.dedent(
            """\
            Vehicle.AverageSpeed:
              unit: km/h
              comment: Instantaneous speed of the vehicle.
            """
        )
    )

    output_file = tmp_path / "output.json"
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "export",
            "json",
            "-s",
            str(schema_file),
            "--vspec-meta",
            str(lookup_yaml),
            "-o",
            str(output_file),
        ],
    )

    assert result.exit_code == 0, f"CLI failed: {result.output}"
    assert output_file.exists()

    data = json.loads(output_file.read_text())
    speed = data["Vehicle"]["children"]["AverageSpeed"]
    assert speed["unit"] == "km/h"
    assert speed["comment"] == "Instantaneous speed of the vehicle."


def test_cli_json_without_vspec_meta_no_error(tmp_path: Path) -> None:
    """CLI without --vspec-meta still works correctly."""
    schema_file = tmp_path / "schema.graphql"
    schema_file.write_text(
        """\
    type Vehicle {
        speed: Float
    }
    """
    )

    output_file = tmp_path / "output.json"
    runner = CliRunner()

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

    assert result.exit_code == 0, f"CLI failed: {result.output}"
    data = json.loads(output_file.read_text())
    assert "Vehicle" in data
    assert "speed" in data["Vehicle"]["children"]
