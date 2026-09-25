"""Tests for the @retainedDefinitions selection query directive."""

from pathlib import Path
from typing import cast

import pytest
from graphql import GraphQLEnumType, GraphQLObjectType, GraphQLSchema, parse
from graphql import print_schema as print_graphql_schema

from s2dm.exporters.utils.schema_loader import (
    load_and_process_schema,
    load_schema,
    prune_schema_using_query_selection,
)

SCHEMA_PATH = Path("tests/data/retained_definitions_schema.graphql")


def prune(query: str, expanded_instances: bool = False) -> GraphQLSchema:
    schema = load_schema([SCHEMA_PATH])
    return prune_schema_using_query_selection(schema, parse(query), expanded_instances)


SEATS = "vehicle { cabin { seats { isOccupied } } }"


class TestWithoutTheDirective:
    def test_unreferenced_definitions_are_dropped(self) -> None:
        schema = prune(f"query Selection {{ {SEATS} }}")

        assert "DateTime" not in schema.type_map
        assert "SeatMaterial" not in schema.type_map
        assert "confidential" not in {directive.name for directive in schema.directives}

    def test_a_directive_on_a_pruned_field_is_still_retained(self) -> None:
        """Existing behavior: directives are collected from a type before its fields are deleted."""
        schema = prune(f"query Selection {{ {SEATS} }}")

        assert "range" in {directive.name for directive in schema.directives}


class TestRetention:
    def test_unreferenced_scalar_is_retained(self) -> None:
        schema = prune(f'query Selection @retainedDefinitions(scalars: ["DateTime"]) {{ {SEATS} }}')

        assert "DateTime" in schema.type_map

    def test_unapplied_directive_is_retained(self) -> None:
        schema = prune(f'query Selection @retainedDefinitions(directives: ["confidential"]) {{ {SEATS} }}')

        assert "confidential" in {directive.name for directive in schema.directives}

    def test_empty_list_retains_every_definition_of_that_kind(self) -> None:
        schema = prune(f"query Selection @retainedDefinitions(scalars: [], enums: []) {{ {SEATS} }}")

        assert "DateTime" in schema.type_map
        assert "SeatMaterial" in schema.type_map
        assert "VelocityUnit" in schema.type_map

    def test_unreferenced_enum_is_retained_and_narrowed(self) -> None:
        schema = prune(
            f"query Selection @retainedDefinitions(enums: {{ SeatMaterial: [CLOTH, LEATHER] }}) {{ {SEATS} }}"
        )

        enum_type = schema.type_map["SeatMaterial"]
        assert isinstance(enum_type, GraphQLEnumType)
        assert list(enum_type.values) == ["CLOTH", "LEATHER"]

    def test_empty_value_list_keeps_every_value(self) -> None:
        schema = prune(f"query Selection @retainedDefinitions(enums: {{ SeatMaterial: [] }}) {{ {SEATS} }}")

        enum_type = schema.type_map["SeatMaterial"]
        assert isinstance(enum_type, GraphQLEnumType)
        assert list(enum_type.values) == ["CLOTH", "LEATHER", "VINYL"]

    def test_the_directive_does_not_reach_the_filtered_schema(self) -> None:
        schema = prune(f'query Selection @retainedDefinitions(scalars: ["DateTime"]) {{ {SEATS} }}')

        assert "retainedDefinitions" not in print_graphql_schema(schema)


class TestValuesInUse:
    def test_a_retained_default_refuses_its_value_being_removed(self) -> None:
        query = (
            "query Selection @retainedDefinitions(enums: { VelocityUnit: [MI_PER_HR] }) { vehicle { averageSpeed } }"
        )

        with pytest.raises(ValueError, match="Vehicle.averageSpeed"):
            prune(query)

    def test_a_pruned_default_does_not_hold_its_value(self) -> None:
        query = f"query Selection @retainedDefinitions(enums: {{ VelocityUnit: [MI_PER_HR] }}) {{ {SEATS} }}"

        schema = prune(query)

        enum_type = schema.type_map["VelocityUnit"]
        assert isinstance(enum_type, GraphQLEnumType)
        assert list(enum_type.values) == ["MI_PER_HR"]


class TestValidation:
    @pytest.mark.parametrize(
        ("selection", "message"),
        [
            ('scalars: ["Timestamp"]', "'Timestamp' is not defined in the model"),
            ("enums: { Vehicle: [] }", "'Vehicle' is not an enum"),
            ("enums: { SeatMaterial: [SUEDE] }", "has no value"),
            ('directives: ["constraint"]', "is not defined in the model"),
        ],
    )
    def test_invalid_selections_are_reported(self, selection: str, message: str) -> None:
        with pytest.raises(ValueError, match=message):
            prune(f"query Selection @retainedDefinitions({selection}) {{ {SEATS} }}")


def expand(tmp_path: Path, query: str, schema_path: Path = SCHEMA_PATH) -> dict[str, list[str]]:
    """Filter and expand the fixture, returning the generated seat instances by row."""
    query_file = tmp_path / "query.graphql"
    query_file.write_text(query)
    annotated_schema, _, _ = load_and_process_schema([schema_path], None, query_file, None, True)
    return {
        name.split("_")[1]: sorted(cast(GraphQLObjectType, type_definition).fields)
        for name, type_definition in annotated_schema.schema.type_map.items()
        if name.startswith("Seat_") and name.endswith("_Position")
    }


class TestInstanceTagDimensions:
    def test_the_model_excludes_two_instances(self, tmp_path: Path) -> None:
        instances = expand(tmp_path, f"query Selection {{ {SEATS} }}")

        assert instances == {"ROW1": ["LEFT", "RIGHT"], "ROW2": ["MIDDLE", "RIGHT"]}

    def test_narrowing_a_dimension_reduces_the_instances(self, tmp_path: Path) -> None:
        query = f"query Selection @retainedDefinitions(enums: {{ PositionEnum: [LEFT, RIGHT] }}) {{ {SEATS} }}"

        instances = expand(tmp_path, query)

        assert instances == {"ROW1": ["LEFT", "RIGHT"], "ROW2": ["RIGHT"]}

    def test_a_misspelled_exclude_entry_still_fails(self, tmp_path: Path) -> None:
        schema_path = tmp_path / "schema.graphql"
        schema_path.write_text(SCHEMA_PATH.read_text().replace('"ROW1.MIDDLE"', '"ROW1.MIDLE"'))
        query = f"query Selection @retainedDefinitions(enums: {{ PositionEnum: [LEFT, RIGHT] }}) {{ {SEATS} }}"

        with pytest.raises(ValueError, match="match no instance"):
            expand(tmp_path, query, schema_path)
