"""Unit tests for the vspec exporter."""

import logging
from collections.abc import Callable

import pytest
from graphql import GraphQLSchema

from s2dm.exporters.utils.schema_loader import process_schema
from s2dm.exporters.vspec import translate_to_vspec

# A minimal schema with two scalar fields that take a unit argument:
#   - `length` defaults to `M` (mapped in UNITS_DICT to "m")
#   - `unmapped` defaults to `BANANA` (deliberately unknown)
#
# `BANANA` is not in `UNITS_DICT`, so the exporter must:
#   1. omit the unit from the YAML output for that field, and
#   2. log a `WARNING` so the silent drop is visible to the user.
SCHEMA_WITH_UNMAPPED_UNIT = """
enum LengthUnit {
    M
    KILOM
}

enum BananaUnit {
    BANANA
}

type Vehicle {
    length(unit: LengthUnit = M): Float
    unmapped(unit: BananaUnit = BANANA): Float
}
"""


def _to_vspec(schema_builder: Callable[[str], GraphQLSchema], schema_str: str) -> str:
    schema = schema_builder(schema_str)
    annotated = process_schema(schema, {}, None, None, None, False)
    return translate_to_vspec(annotated)


def test_unmapped_unit_emits_warning_and_is_dropped(
    schema_builder: Callable[[str], GraphQLSchema],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Unrecognized units must surface a warning rather than vanishing silently."""
    with caplog.at_level(logging.WARNING, logger="s2dm"):
        yaml_out = _to_vspec(schema_builder, SCHEMA_WITH_UNMAPPED_UNIT)

    # The mapped unit is present in the YAML; the unmapped one is dropped.
    assert "unit: m\n" in yaml_out
    assert "BANANA" not in yaml_out

    # And the user is told why the unmapped one disappeared.
    warning_messages = [
        record.getMessage() for record in caplog.records if record.levelno == logging.WARNING
    ]
    matching = [msg for msg in warning_messages if "BANANA" in msg and "Vehicle.unmapped" in msg]
    assert matching, (
        f"Expected a WARNING about the unmapped 'BANANA' unit on Vehicle.unmapped, "
        f"got: {warning_messages}"
    )


def test_mapped_unit_does_not_warn(
    schema_builder: Callable[[str], GraphQLSchema],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Recognized units must round-trip cleanly without spurious warnings."""
    schema_str = """
    enum LengthUnit {
        M
        KILOM
    }

    type Vehicle {
        length(unit: LengthUnit = M): Float
    }
    """
    with caplog.at_level(logging.WARNING, logger="s2dm"):
        yaml_out = _to_vspec(schema_builder, schema_str)

    assert "unit: m\n" in yaml_out
    unit_warnings = [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.WARNING and "UNITS_DICT" in record.getMessage()
    ]
    assert not unit_warnings, f"Did not expect any UNITS_DICT warnings, got: {unit_warnings}"
