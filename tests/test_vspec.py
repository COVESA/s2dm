from pathlib import Path

import pytest
import yaml

from s2dm.exporters.utils.schema_loader import load_and_process_schema
from s2dm.exporters.vspec import translate_to_vspec


@pytest.mark.parametrize("renames_enum_values", [False, True], ids=["plain", "renaming"])
def test_translate_to_vspec_keeps_the_default_unit(tmp_path: Path, renames_enum_values: bool) -> None:
    schema_str = """
    enum LengthUnit {
      MILLIM
      CENTIM
    }

    type Vehicle {
      length(unit: LengthUnit = MILLIM): Float
    }
    """
    naming_config_str = """
    enumValue: snake_case
    instanceTag: snake_case
    """
    schema_path = tmp_path / "schema.graphql"
    schema_path.write_text(schema_str, encoding="utf-8")
    naming_config_path: Path | None = None
    if renames_enum_values:
        naming_config_path = tmp_path / "naming.yaml"
        naming_config_path.write_text(naming_config_str, encoding="utf-8")
    annotated_schema, _, _ = load_and_process_schema(schema_paths=[schema_path], naming_config_path=naming_config_path)

    vspec_content = translate_to_vspec(annotated_schema)
    vspec = yaml.safe_load(vspec_content)

    assert vspec["Vehicle.length"]["unit"] == "mm"


def test_translate_to_vspec_omits_a_null_range_bound(tmp_path: Path) -> None:
    schema_str = """
    directive @range(min: Float, max: Float) on FIELD_DEFINITION

    type Vehicle {
      speed: Float @range(min: null, max: 250)
    }
    """
    schema_path = tmp_path / "schema.graphql"
    schema_path.write_text(schema_str, encoding="utf-8")
    annotated_schema, _, _ = load_and_process_schema(schema_paths=[schema_path], naming_config_path=None)

    vspec_content = translate_to_vspec(annotated_schema)
    vspec = yaml.safe_load(vspec_content)

    assert "min" not in vspec["Vehicle.speed"]
    assert "max" in vspec["Vehicle.speed"]
