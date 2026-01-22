"""Integration tests for load_and_process_schema."""

from pathlib import Path
from typing import cast

import pytest
from graphql import GraphQLObjectType

from s2dm.exporters.utils.schema_loader import load_and_process_schema


class TestLoadAndProcessSchema:
    @pytest.fixture
    def expanded_schema_path(self) -> list[Path]:
        return [Path("tests/test_expanded_instances/test_schema.graphql")]

    @pytest.fixture
    def valid_query_path(self, tmp_path: Path) -> Path:
        query_file = tmp_path / "query.graphql"
        query_file.write_text("""
            query {
                vehicle {
                    averageSpeed
                    lowVoltageSystemState
                    adas {
                        abs {
                            isEngaged
                        }
                    }
                }
            }
        """)
        return query_file

    @pytest.fixture
    def naming_config_path(self, tmp_path: Path) -> Path:
        config_file = tmp_path / "naming_config.json"
        config_file.write_text('{"type": "MACROCASE", "field": "snake_case"}')
        return config_file

    def test_load_with_selection_query(self, schema_path: list[Path], valid_query_path: Path) -> None:
        annotated_schema, naming_config, query_document = load_and_process_schema(
            schema_path, None, valid_query_path, None, False
        )

        assert query_document is not None
        assert naming_config is None

        assert "Vehicle" in annotated_schema.schema.type_map
        vehicle_type = cast(GraphQLObjectType, annotated_schema.schema.type_map["Vehicle"])
        assert "averageSpeed" in vehicle_type.fields
        assert "lowVoltageSystemState" in vehicle_type.fields
        assert "adas" in vehicle_type.fields

        assert "isAutoPowerOptimize" not in vehicle_type.fields
        assert "body" not in vehicle_type.fields

    def test_load_with_root_type(self, schema_path: list[Path]) -> None:
        annotated_schema, naming_config, query_document = load_and_process_schema(
            schema_path, None, None, "Vehicle", False
        )

        assert query_document is None
        assert naming_config is None
        assert "Vehicle" in annotated_schema.schema.type_map

        assert "Cabin" not in annotated_schema.schema.type_map
        assert "Seat" not in annotated_schema.schema.type_map

    def test_load_with_expanded_instances(self, expanded_schema_path: list[Path]) -> None:
        annotated_schema, naming_config, query_document = load_and_process_schema(
            expanded_schema_path, None, None, None, expanded_instances=True
        )

        assert query_document is None
        assert naming_config is None

        assert "Door_Row" in annotated_schema.schema.type_map
        assert "Door_Side" in annotated_schema.schema.type_map
        assert "Seat_Row" in annotated_schema.schema.type_map
        assert "Seat_Position" in annotated_schema.schema.type_map

        cabin_type = cast(GraphQLObjectType, annotated_schema.schema.type_map["Cabin"])
        assert "Door" in cabin_type.fields
        assert "doors" not in cabin_type.fields
        assert "Seat" in cabin_type.fields
        assert "seats" not in cabin_type.fields

    def test_load_with_naming_config(self, schema_path: list[Path], naming_config_path: Path) -> None:
        annotated_schema, naming_config, query_document = load_and_process_schema(
            schema_path, naming_config_path, None, None, False
        )

        assert query_document is None
        assert naming_config is not None

        assert "VEHICLE" in annotated_schema.schema.type_map
        vehicle_type = cast(GraphQLObjectType, annotated_schema.schema.type_map["VEHICLE"])
        assert "average_speed" in vehicle_type.fields
        assert "low_voltage_system_state" in vehicle_type.fields
        assert "averageSpeed" not in vehicle_type.fields
        assert "lowVoltageSystemState" not in vehicle_type.fields

    def test_load_with_all_options(
        self,
        schema_path: list[Path],
        naming_config_path: Path,
        tmp_path: Path,
    ) -> None:
        query_file = tmp_path / "query.graphql"
        query_file.write_text("""
            query {
                vehicle {
                    averageSpeed
                    lowVoltageSystemState
                    adas {
                        abs {
                            isEngaged
                        }
                    }
                }
            }
        """)

        annotated_schema, naming_config, query_document = load_and_process_schema(
            schema_path,
            naming_config_path,
            query_file,
            "Vehicle",
            expanded_instances=False,
        )

        assert query_document is not None
        assert naming_config is not None

        assert "VEHICLE" in annotated_schema.schema.type_map
        vehicle_type = cast(GraphQLObjectType, annotated_schema.schema.type_map["VEHICLE"])
        assert "average_speed" in vehicle_type.fields
        assert "low_voltage_system_state" in vehicle_type.fields
        assert "adas" in vehicle_type.fields

        assert "is_auto_power_optimize" not in vehicle_type.fields
        assert "body" not in vehicle_type.fields

        assert "CABIN" not in annotated_schema.schema.type_map
        assert "SEAT" not in annotated_schema.schema.type_map
