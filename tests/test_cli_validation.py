import tempfile
from pathlib import Path

import pytest
import rich_click as click

from s2dm.exporters.utils.naming import load_naming_config, validate_naming_config


class TestValidateNamingConfig:
    def test_valid_config_mixed(self) -> None:
        config = {
            "type": "PascalCase",
            "field": {"object": "camelCase", "interface": "camelCase"},
            "enumValue": "PascalCase",
            "instanceTag": "COBOL-CASE",
        }
        validate_naming_config(config)

    def test_invalid_element_type(self) -> None:
        config = {"invalid_element": "PascalCase"}
        with pytest.raises(click.ClickException, match="Invalid element type 'invalid_element'"):
            validate_naming_config(config)

    def test_invalid_case_type(self) -> None:
        config = {"type": "InvalidCase"}
        with pytest.raises(click.ClickException, match="Invalid case type for 'type': 'InvalidCase'"):
            validate_naming_config(config)

    def test_invalid_context(self) -> None:
        config = {"type": {"invalid_context": "PascalCase"}}
        with pytest.raises(click.ClickException, match="Invalid context 'invalid_context' for 'type'"):
            validate_naming_config(config)

    def test_invalid_value_type(self) -> None:
        config = {"type": 123}
        with pytest.raises(click.ClickException, match="Invalid value type for 'type'. Expected string or dict"):
            validate_naming_config(config)

    def test_enum_value_without_instance_tag(self) -> None:
        config = {"enumValue": "PascalCase"}
        with pytest.raises(click.ClickException, match="If 'enumValue' is present, 'instanceTag' must also be present"):
            validate_naming_config(config)

    def test_instance_tag_without_enum_value_is_valid(self) -> None:
        config = {"instanceTag": "COBOL-CASE"}
        validate_naming_config(config)

    def test_contextless_element_with_context(self) -> None:
        config = {"enumValue": {"some_context": "PascalCase"}}
        with pytest.raises(click.ClickException, match="Element type 'enumValue' cannot have contexts"):
            validate_naming_config(config)

    def test_all_valid_case_types(self) -> None:
        valid_cases = [
            "camelCase",
            "PascalCase",
            "snake_case",
            "kebab-case",
            "MACROCASE",
            "COBOL-CASE",
            "flatcase",
            "TitleCase",
        ]
        for case in valid_cases:
            config = {"instanceTag": case}
            validate_naming_config(config)


class TestLoadNamingConfig:
    def test_load_valid_config_file(self) -> None:
        config_content = """
type:
  object: PascalCase
  interface: PascalCase
field:
  object: camelCase
enumValue: PascalCase
instanceTag: COBOL-CASE
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            f.flush()

            config = load_naming_config(Path(f.name))
            assert config is not None
            assert config["type"]["object"] == "PascalCase"
            assert config["enumValue"] == "PascalCase"
            assert config["instanceTag"] == "COBOL-CASE"

        Path(f.name).unlink()

    def test_load_invalid_config_file(self) -> None:
        config_content = """
invalid_element: PascalCase
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            f.flush()

            with pytest.raises(click.ClickException, match="Invalid element type 'invalid_element'"):
                load_naming_config(Path(f.name))

        Path(f.name).unlink()

    def test_load_nonexistent_file(self) -> None:
        config = load_naming_config(None)
        assert config is None

    def test_load_empty_config(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()

            config = load_naming_config(Path(f.name))
            assert config == {}

        Path(f.name).unlink()
