"""Integration tests for load_and_process_schema."""

import json
from pathlib import Path
from typing import cast

import pytest
from graphql import GraphQLObjectType

from s2dm.exporters.utils.naming_config import CaseFormat
from s2dm.exporters.utils.schema_loader import load_and_process_schema


def _write_pick_query(tmp_path: Path, instances: str) -> Path:
    query_file = tmp_path / "query.graphql"
    query_file.write_text(f"""
        query {{
            cabin {{
                doors {{
                    doorPosition @pick(instances: {instances}) {{
                        row
                        side
                    }}
                }}
            }}
        }}
    """)
    return query_file


class TestLoadAndProcessSchema:
    @pytest.fixture
    def expanded_schema_path(self, spec_directory: Path) -> list[Path]:
        return [spec_directory, Path("tests/test_expanded_instances/test_schema.graphql")]

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
        config_file.write_text(
            json.dumps(
                {"type": {"object": CaseFormat.MACRO_CASE.value}, "field": {"object": CaseFormat.SNAKE_CASE.value}}
            )
        )
        return config_file

    @pytest.fixture
    def instance_tag_schema_path(self, tmp_path: Path) -> Path:
        schema_file = tmp_path / "instance_tag.graphql"
        schema_file.write_text("""
        directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

        enum RowEnum { ROW1 ROW2 }
        enum SideEnum { LEFT RIGHT }

        type DoorPosition @instanceTag {
          row: RowEnum!
          side: SideEnum!
        }

        type Door {
          doorPosition: DoorPosition @instanceTag
        }

        type Cabin {
          doors: [Door]
        }

        type Query {
          cabin: Cabin
        }
        """)
        return schema_file

    @pytest.fixture
    def instance_tag_naming_config_path(self, tmp_path: Path) -> Path:
        config_file = tmp_path / "instance_tag_naming_config.json"
        config_file.write_text(json.dumps({"instanceTag": CaseFormat.PASCAL_CASE.value}))
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

    def test_load_with_expanded_instances_uses_enum_values_without_tag_field_wrapper(
        self, enum_instance_tag_schema_path: Path
    ) -> None:
        annotated_schema, _, _ = load_and_process_schema(
            [enum_instance_tag_schema_path], None, None, None, expanded_instances=True
        )

        vehicle_type = cast(GraphQLObjectType, annotated_schema.schema.type_map["Vehicle"])
        assert "Mirror" in vehicle_type.fields
        assert "mirrors" not in vehicle_type.fields

        mirror_branch_type = cast(GraphQLObjectType, annotated_schema.schema.type_map["Mirror_Position"])
        assert "LEFT" in mirror_branch_type.fields
        assert "CENTER" in mirror_branch_type.fields
        assert "RIGHT" in mirror_branch_type.fields
        assert "position" not in mirror_branch_type.fields

        mirror_type = cast(GraphQLObjectType, annotated_schema.schema.type_map["Mirror"])
        assert "isFolded" in mirror_type.fields
        assert "position" not in mirror_type.fields

        field_meta = annotated_schema.field_metadata[("Vehicle", "Mirror")]
        assert field_meta.resolved_names == ["Mirror.LEFT", "Mirror.CENTER", "Mirror.RIGHT"]

    def test_load_with_expanded_instances_prunes_excluded_instance_tag_combination(self, tmp_path: Path) -> None:
        schema_path = tmp_path / "excluded_instance.graphql"
        schema_path.write_text("""
        directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

        enum RowEnum { ROW1 ROW2 }
        enum SideEnum { LEFT RIGHT }

        type DoorPosition @instanceTag {
          row: RowEnum!
          side: SideEnum!
        }

        type Door {
          isLocked: Boolean
          doorPosition: DoorPosition @instanceTag(exclude: [\"ROW1.LEFT\"])
        }

        type Cabin {
          doors: [Door]
        }

        type Query {
          cabin: Cabin
        }
        """)

        annotated_schema, _, _ = load_and_process_schema([schema_path], None, None, None, expanded_instances=True)

        field_meta = annotated_schema.field_metadata[("Cabin", "Door")]

        assert field_meta.resolved_names == ["Door.ROW1.RIGHT", "Door.ROW2.LEFT", "Door.ROW2.RIGHT"]

    def test_load_with_expanded_instances_raises_when_exclude_list_matches_nothing(self, tmp_path: Path) -> None:
        schema_path = tmp_path / "invalid_excluded_instance.graphql"
        schema_path.write_text("""
        directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

        enum RowEnum { ROW1 ROW2 }
        enum SideEnum { LEFT RIGHT }

        type DoorPosition @instanceTag {
          row: RowEnum!
          side: SideEnum!
        }

        type Door {
          doorPosition: DoorPosition @instanceTag(exclude: [\"ROW9.LEFT\"])
        }

        type Cabin {
          doors: [Door]
        }

        type Query {
          cabin: Cabin
        }
        """)

        with pytest.raises(ValueError):
            load_and_process_schema([schema_path], None, None, None, expanded_instances=True)

    def test_load_with_pick_reads_source_names_before_naming(
        self, instance_tag_schema_path: Path, instance_tag_naming_config_path: Path, tmp_path: Path
    ) -> None:
        query_file = _write_pick_query(tmp_path, '["ROW1.LEFT", "ROW2.RIGHT"]')

        annotated_schema, _, _ = load_and_process_schema(
            [instance_tag_schema_path], instance_tag_naming_config_path, query_file, None, expanded_instances=True
        )

        field_meta = annotated_schema.field_metadata[("Cabin", "Door")]
        assert field_meta.resolved_names == ["Door.Row1.Left", "Door.Row2.Right"]

    def test_load_with_pick_rejects_converted_names(
        self, instance_tag_schema_path: Path, instance_tag_naming_config_path: Path, tmp_path: Path
    ) -> None:
        query_file = _write_pick_query(tmp_path, '["Row1.Left"]')

        with pytest.raises(ValueError):
            load_and_process_schema(
                [instance_tag_schema_path], instance_tag_naming_config_path, query_file, None, expanded_instances=True
            )

    def test_load_with_expanded_instances_does_not_expand_non_list_field(self, tmp_path: Path) -> None:
        schema_path = tmp_path / "non_list_instance_tag.graphql"
        schema_path.write_text("""
        directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

        enum RowEnum { ROW1 ROW2 }
        enum SideEnum { LEFT RIGHT }

        type DoorPosition @instanceTag {
          row: RowEnum!
          side: SideEnum!
        }

        type Door {
          isLocked: Boolean
          doorPosition: DoorPosition @instanceTag
        }

        type Cabin {
          door: Door
        }

        type Query {
          cabin: Cabin
        }
        """)

        annotated_schema, _, _ = load_and_process_schema([schema_path], None, None, None, expanded_instances=True)

        assert "Door_Row" not in annotated_schema.schema.type_map
        assert "Door_Side" not in annotated_schema.schema.type_map

        cabin_type = cast(GraphQLObjectType, annotated_schema.schema.type_map["Cabin"])
        assert "door" in cabin_type.fields
        assert "Door" not in cabin_type.fields

        door_type = cast(GraphQLObjectType, annotated_schema.schema.type_map["Door"])
        assert "doorPosition" in door_type.fields
        assert "DoorPosition" in annotated_schema.schema.type_map

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

    def test_load_removes_introspection_types(self, schema_path: list[Path]) -> None:
        annotated_schema, _, _ = load_and_process_schema(schema_path, None, None, None, False)

        assert not any(type_name.startswith("__") for type_name in annotated_schema.schema.type_map)
