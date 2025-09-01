"""Tests for units sync helpers.

Tests for URI segment extraction, enum symbol generation, and dry-run functionality.
"""

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from s2dm.units.sync import (
    UnitEnumError,
    UnitEnumErrorMessages,
    UnitRow,
    _cleanup_units_directory,
    _extract_uri_segment,
    _uri_to_enum_symbol,
    sync_qudt_units,
)
from tests.conftest import MOCK_QUDT_VERSION, QUDT_UNIT_BASE, create_test_unit_row


@pytest.mark.parametrize(
    "uri,expected",
    [
        (f"{QUDT_UNIT_BASE}/Meter-Per-Second", "Meter-Per-Second"),  # QUDT unit URI
        ("http://example.com/test", "test"),  # Generic HTTP URI
        ("simple", "simple"),  # Simple string
        ("path/to/resource", "resource"),  # Path-like string
    ],
    ids=["qudt_unit_uri", "http_uri", "simple_string", "path_string"],
)
def test_extract_uri_segment(uri: str, expected: str) -> None:
    """Test URI segment extraction from various URIs."""
    assert _extract_uri_segment(uri) == expected


@pytest.mark.parametrize(
    "uri,expected",
    [
        # Cases with separators
        (f"{QUDT_UNIT_BASE}/Meter-Per-Second", "METER_PER_SECOND"),  # hyphen separators
        (f"{QUDT_UNIT_BASE}/PicoMOL-PER-KiloGM", "PICOMOL_PER_KILOGM"),  # mixed case with separators
        (f"{QUDT_UNIT_BASE}/A-HR-PER-DEG_C", "A_HR_PER_DEG_C"),  # underscore and hyphen mix
        (f"{QUDT_UNIT_BASE}/Newton.Meter", "NEWTON_METER"),  # dot separator
        # Cases without separators (unit symbols)
        (f"{QUDT_UNIT_BASE}/kWh", "KWH"),  # compact symbol
        (f"{QUDT_UNIT_BASE}/MHz", "MHZ"),  # frequency symbol
        (f"{QUDT_UNIT_BASE}/Hz", "HZ"),  # simple symbol
        # Cases starting with numbers
        (f"{QUDT_UNIT_BASE}/2PiRAD", "_2PIRAD"),  # number prefix uppercase
        (f"{QUDT_UNIT_BASE}/3kWh", "_3KWH"),  # number prefix lowercase
    ],
    ids=[
        "hyphen_separators",
        "mixed_case_with_separators",
        "underscore_and_hyphen_mix",
        "dot_separator",
        "compact_symbol",
        "frequency_symbol",
        "simple_symbol",
        "number_prefix_uppercase",
        "number_prefix_lowercase",
    ],
)
def test_uri_to_enum_symbol(uri: str, expected: str) -> None:
    """Test enum symbol generation for various URI patterns."""
    assert _uri_to_enum_symbol(uri) == expected


@pytest.mark.parametrize(
    "invalid_uri,expected_message_key",
    [
        (f"{QUDT_UNIT_BASE}/", UnitEnumErrorMessages.URI_SEGMENT_EMPTY),  # empty URI segment
        ("", UnitEnumErrorMessages.URI_SEGMENT_EMPTY),  # empty string
        ("///", UnitEnumErrorMessages.URI_SEGMENT_EMPTY),  # only separators
    ],
    ids=["empty_segment", "empty_string", "only_separators"],
)
def test_uri_to_enum_symbol_invalid(invalid_uri: str, expected_message_key: str) -> None:
    """Test enum symbol generation with various invalid URI patterns."""
    with pytest.raises(UnitEnumError, match=expected_message_key):
        _uri_to_enum_symbol(invalid_uri)


@pytest.fixture
def mock_sync_setup() -> Iterator[tuple[Mock, Mock]]:
    """Set up common mocks for sync tests."""
    with (
        patch("s2dm.units.sync._load_graph_from_url") as mock_load_graph,
        patch("s2dm.units.sync._query_units") as mock_query_units,
    ):
        mock_graph = Mock()
        mock_load_graph.return_value = mock_graph
        yield mock_query_units, mock_load_graph


@pytest.fixture
def sample_units() -> list[UnitRow]:
    """Sample unit data for testing."""
    return [
        create_test_unit_row("Meter-Per-Second", "Velocity", "meter per second", "m/s"),
        create_test_unit_row("Kilogram", "Mass", "kilogram", "kg"),
    ]


@pytest.fixture
def single_unit() -> list[UnitRow]:
    """Single unit data for testing."""
    return [create_test_unit_row("Meter", "Length", "meter", "m")]


@pytest.mark.parametrize("dry_run", [True, False])
def test_sync_qudt_units(
    mock_sync_setup: tuple[Mock, Mock],
    sample_units: list[UnitRow],
    tmp_path: Path,
    dry_run: bool,
) -> None:
    """Test sync_qudt_units behavior for both dry-run and normal execution."""
    mock_query_units, mock_load_graph = mock_sync_setup
    mock_query_units.return_value = sample_units

    units_root = tmp_path / "units"
    result_paths = sync_qudt_units(units_root, MOCK_QUDT_VERSION, dry_run=dry_run)

    # Common assertions
    assert len(result_paths) == len(sample_units)

    if dry_run:
        # Dry run should not create any files or directories
        assert not units_root.exists(), "Dry run should not create directories"
    else:
        # Normal run should create files and directories
        assert units_root.exists(), "Normal run should create directories"

        # Check metadata file exists
        metadata_file = units_root / "metadata.json"
        assert metadata_file.exists(), "Normal run should create metadata.json"

        # Check that at least one enum file exists and has expected content
        enum_files = list(units_root.rglob("*.graphql"))
        assert len(enum_files) >= 1, "Normal run should create enum files"

        # Verify content of first enum file
        first_enum = enum_files[0]
        content = first_enum.read_text()
        assert "enum" in content and "UnitEnum" in content


def test_sync_qudt_units_path_generation(
    mock_sync_setup: tuple[Mock, Mock],
    single_unit: list[UnitRow],
    tmp_path: Path,
) -> None:
    """Test that sync generates correct file paths."""
    mock_query_units, mock_load_graph = mock_sync_setup
    mock_query_units.return_value = single_unit

    units_root = tmp_path / "units"
    result_paths = sync_qudt_units(units_root, MOCK_QUDT_VERSION, dry_run=True)

    # Should generate path based on quantity kind
    expected_path = units_root / "LengthUnitEnum.graphql"
    assert expected_path in result_paths


def test_cleanup_units_directory(tmp_path: Path) -> None:
    """Test that cleanup removes GraphQL files and metadata but preserves other files."""
    units_dir = tmp_path / "units"
    units_dir.mkdir()

    # Create files that should be cleaned up
    (units_dir / "TestEnum.graphql").write_text("# old enum")
    (units_dir / "metadata.json").write_text('{"version": "old"}')

    # Create file that should be preserved
    (units_dir / "README.md").write_text("should remain")

    # Run cleanup
    _cleanup_units_directory(units_dir)

    # Check results
    assert not (units_dir / "TestEnum.graphql").exists()
    assert not (units_dir / "metadata.json").exists()
    assert (units_dir / "README.md").exists()


def test_sync_with_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_sync_setup: tuple[Mock, Mock],
    single_unit: list[UnitRow],
) -> None:
    """Test that sync cleans up old files but dry-run preserves them."""
    mock_query_units, mock_load_graph = mock_sync_setup
    mock_query_units.return_value = single_unit

    units_dir = tmp_path / "units"
    units_dir.mkdir()

    # Create an old file
    old_file = units_dir / "OldEnum.graphql"
    old_file.write_text("# old")

    # Test 1: Dry run preserves old file
    sync_qudt_units(units_dir, MOCK_QUDT_VERSION, dry_run=True)
    assert old_file.exists()

    # Test 2: Normal sync removes old file
    sync_qudt_units(units_dir, MOCK_QUDT_VERSION, dry_run=False)
    assert not old_file.exists()
