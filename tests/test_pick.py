"""Tests for the @pick selection query directive."""

from pathlib import Path

import pytest
from graphql import GraphQLEnumType, GraphQLSchema, parse
from graphql import print_schema as print_graphql_schema

from s2dm.exporters.utils.schema_loader import load_schema, prune_schema_using_query_selection

SCHEMA_PATH = Path("tests/data/pick_schema.graphql")
SEATS = "vehicle { cabin { seats { isOccupied } } }"


def prune(query: str) -> GraphQLSchema:
    schema = load_schema([SCHEMA_PATH])
    return prune_schema_using_query_selection(schema, parse(query))


def directive_names(schema: GraphQLSchema) -> set[str]:
    return {directive.name for directive in schema.directives}


class TestWithoutTheDirective:
    def test_unreferenced_definitions_are_dropped(self) -> None:
        schema = prune(f"query Selection {{ {SEATS} }}")

        assert "DateTime" not in schema.type_map
        assert "SeatMaterial" not in schema.type_map
        assert "confidential" not in directive_names(schema)

    def test_a_directive_on_a_pruned_field_is_still_kept(self) -> None:
        """Existing behavior: directives are collected from a type before its fields are deleted."""
        schema = prune(f"query Selection {{ {SEATS} }}")

        assert "range" in directive_names(schema)


class TestPicking:
    def test_unreferenced_scalar_is_kept(self) -> None:
        schema = prune(f'query Selection @pick(scalars: ["DateTime"]) {{ {SEATS} }}')

        assert "DateTime" in schema.type_map

    def test_unapplied_directive_is_kept(self) -> None:
        schema = prune(f'query Selection @pick(directives: ["confidential"]) {{ {SEATS} }}')

        assert "confidential" in directive_names(schema)

    def test_unreferenced_enum_is_kept_whole(self) -> None:
        schema = prune(f'query Selection @pick(enums: ["SeatMaterial"]) {{ {SEATS} }}')

        enum_type = schema.type_map["SeatMaterial"]
        assert isinstance(enum_type, GraphQLEnumType)
        assert list(enum_type.values) == ["CLOTH", "LEATHER", "VINYL"]

    def test_empty_list_keeps_every_definition_of_that_kind(self) -> None:
        schema = prune(f"query Selection @pick(scalars: [], enums: [], directives: []) {{ {SEATS} }}")

        assert "DateTime" in schema.type_map
        assert "SeatMaterial" in schema.type_map
        assert "VelocityUnit" in schema.type_map
        assert "confidential" in directive_names(schema)

    def test_absent_arguments_leave_the_existing_behavior(self) -> None:
        picked = prune(f'query Selection @pick(scalars: ["DateTime"]) {{ {SEATS} }}')
        plain = prune(f"query Selection {{ {SEATS} }}")

        assert "SeatMaterial" not in picked.type_map
        assert set(plain.type_map) < set(picked.type_map)

    def test_the_directive_does_not_reach_the_filtered_schema(self) -> None:
        schema = prune(f'query Selection @pick(scalars: ["DateTime"]) {{ {SEATS} }}')

        assert "pick" not in print_graphql_schema(schema)


class TestValidation:
    @pytest.mark.parametrize(
        ("selection", "message"),
        [
            ('scalars: ["Timestamp"]', "'Timestamp' is not defined in the model"),
            ('enums: ["Vehicle"]', "'Vehicle' is not an enum"),
            ('scalars: ["SeatMaterial"]', "'SeatMaterial' is not a scalar"),
            ('directives: ["constraint"]', "is not defined in the model"),
            ('enums: "SeatMaterial"', "must be a list of names"),
            ('unknown: ["x"]', "unknown argument"),
        ],
    )
    def test_invalid_selections_are_reported(self, selection: str, message: str) -> None:
        with pytest.raises(ValueError, match=message):
            prune(f"query Selection @pick({selection}) {{ {SEATS} }}")
