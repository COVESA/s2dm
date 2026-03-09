"""End-to-end integration tests for LinkML export."""

import json
from pathlib import Path
from typing import Any, cast

import pytest
from linkml_runtime.loaders import yaml_loader

from s2dm.exporters.linkml import translate_to_linkml
from s2dm.exporters.utils.schema_loader import load_and_process_schema

LINKML_SCHEMA_ID = "https://covesa.global/s2dm"
LINKML_SCHEMA_NAME = "TestSchema"
LINKML_DEFAULT_PREFIX = "s2dm"
LINKML_DEFAULT_PREFIX_URL = "https://covesa.global/s2dm"


class TestLinkmlE2E:
    @pytest.fixture
    def test_schema_path(self, spec_directory: Path) -> list[Path]:
        """Path to the test GraphQL schema."""
        return [spec_directory, Path(__file__).parent / "test_expanded_instances" / "test_schema.graphql"]

    def test_expanded_instances_default(self, test_schema_path: list[Path]) -> None:
        """Test that instance tags are NOT expanded by default."""
        annotated_schema, _, _ = load_and_process_schema(
            schema_paths=test_schema_path,
            naming_config_path=None,
            selection_query_path=None,
            root_type="Cabin",
            expanded_instances=False,
        )

        result = translate_to_linkml(
            annotated_schema,
            LINKML_SCHEMA_ID,
            LINKML_SCHEMA_NAME,
            LINKML_DEFAULT_PREFIX,
            LINKML_DEFAULT_PREFIX_URL,
        )
        schema = cast(dict[str, Any], yaml_loader.load_as_dict(result))
        cabin_attributes = schema["classes"]["Cabin"]["attributes"]

        assert "doors" in cabin_attributes
        assert "seats" in cabin_attributes
        assert cabin_attributes["doors"]["multivalued"] is True
        assert cabin_attributes["doors"]["range"] == "Door"
        assert cabin_attributes["doors"]["list_elements_unique"] is True
        assert cabin_attributes["seats"]["multivalued"] is True
        assert cabin_attributes["seats"]["range"] == "Seat"
        assert cabin_attributes["seats"]["list_elements_unique"] is True

        assert "DoorPosition" in schema["classes"]
        assert "SeatPosition" in schema["classes"]

    def test_expanded_instances(self, test_schema_path: list[Path]) -> None:
        """Test that instance tags are expanded when enabled."""
        annotated_schema, _, _ = load_and_process_schema(
            schema_paths=test_schema_path,
            naming_config_path=None,
            selection_query_path=None,
            root_type="Cabin",
            expanded_instances=True,
        )

        result = translate_to_linkml(
            annotated_schema,
            LINKML_SCHEMA_ID,
            LINKML_SCHEMA_NAME,
            LINKML_DEFAULT_PREFIX,
            LINKML_DEFAULT_PREFIX_URL,
        )
        schema = cast(dict[str, Any], yaml_loader.load_as_dict(result))
        cabin_attributes = schema["classes"]["Cabin"]["attributes"]

        assert "Door" in cabin_attributes
        assert "Seat" in cabin_attributes
        assert "doors" not in cabin_attributes
        assert "seats" not in cabin_attributes

        assert cabin_attributes["Door"]["required"] is True
        assert cabin_attributes["Seat"]["required"] is True
        assert "annotations" not in cabin_attributes["Door"]
        assert "annotations" not in cabin_attributes["Seat"]

        assert "Door_Row" not in schema["classes"]
        assert "Door_Side" not in schema["classes"]
        assert "Seat_Row" not in schema["classes"]
        assert "Seat_Position" not in schema["classes"]

    def test_expanded_instances_with_naming_config(self, test_schema_path: list[Path], tmp_path: Path) -> None:
        """Test that naming config is applied to expanded instance field names."""
        naming_config = {"field": {"object": "MACROCASE"}}
        naming_config_file = tmp_path / "naming_config.json"
        naming_config_file.write_text(json.dumps(naming_config))

        annotated_schema, _, _ = load_and_process_schema(
            schema_paths=test_schema_path,
            naming_config_path=naming_config_file,
            selection_query_path=None,
            root_type="Cabin",
            expanded_instances=True,
        )

        result = translate_to_linkml(
            annotated_schema,
            LINKML_SCHEMA_ID,
            LINKML_SCHEMA_NAME,
            LINKML_DEFAULT_PREFIX,
            LINKML_DEFAULT_PREFIX_URL,
        )
        schema = cast(dict[str, Any], yaml_loader.load_as_dict(result))
        cabin_attributes = schema["classes"]["Cabin"]["attributes"]

        assert "SEAT" in cabin_attributes
        assert "DOOR" in cabin_attributes
        assert "Seat" not in cabin_attributes
        assert "Door" not in cabin_attributes
        assert "annotations" not in cabin_attributes["SEAT"]
        assert "annotations" not in cabin_attributes["DOOR"]

        seat_attributes = schema["classes"]["Seat"]["attributes"]
        door_attributes = schema["classes"]["Door"]["attributes"]

        assert "IS_OCCUPIED" in seat_attributes
        assert "HEIGHT" in seat_attributes
        assert "isOccupied" not in seat_attributes
        assert "height" not in seat_attributes

        assert "IS_LOCKED" in door_attributes
        assert "POSITION" in door_attributes
        assert "isLocked" not in door_attributes
        assert "position" not in door_attributes
