from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from ariadne import gql
from faker import Faker
from graphql import (
    GraphQLNamedType,
    GraphQLSchema,
    build_schema,
)
from hypothesis import strategies as st
from hypothesis.strategies import composite

from s2dm.exporters.utils.extraction import get_all_named_types
from s2dm.exporters.utils.schema_loader import ensure_query
from s2dm.idgen.models import IDGenerationSpec
from s2dm.units.sync import UnitRow, _uri_to_enum_symbol

SCALAR_TYPES = ["String", "Int", "Float", "Boolean"]


class TestSchemaData:
    """Test schema data paths and constants."""

    TESTS_DATA_DIR: Path = Path(__file__).parent / "data"
    SCHEMA1: Path = TESTS_DATA_DIR / "schema1.graphql"
    SCHEMA2: Path = TESTS_DATA_DIR / "schema2.graphql"
    SCHEMA3: Path = TESTS_DATA_DIR / "schema3.graphql"
    UNITS_SCHEMA_PATH: Path = TESTS_DATA_DIR / "units"

    SAMPLE1_1 = TESTS_DATA_DIR / "schema1-1.graphql"
    SAMPLE1_2 = TESTS_DATA_DIR / "schema1-2.graphql"
    SAMPLE2_1 = TESTS_DATA_DIR / "schema2-1.graphql"
    SAMPLE2_2 = TESTS_DATA_DIR / "schema2-2.graphql"
    SAMPLE3 = TESTS_DATA_DIR / "schema3.graphql"

    VALID_QUERY = TESTS_DATA_DIR / "valid_query.graphql"
    INVALID_QUERY = TESTS_DATA_DIR / "invalid_query.graphql"

    # Version bump test schemas
    BASE_SCHEMA = TESTS_DATA_DIR / "base.graphql"
    NO_CHANGE_SCHEMA = TESTS_DATA_DIR / "no-change.graphql"
    NON_BREAKING_SCHEMA = TESTS_DATA_DIR / "non-breaking.graphql"
    DANGEROUS_SCHEMA = TESTS_DATA_DIR / "dangerous.graphql"
    BREAKING_SCHEMA = TESTS_DATA_DIR / "breaking.graphql"


@pytest.fixture(autouse=True)
def patch_default_units_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch DEFAULT_QUDT_UNITS_DIR to use tests/data/units for all tests.

    This prevents the "No QUDT units directory found" warning during tests
    and provides the necessary unit enum definitions that test schemas reference.

    Tests that use the units_sync_mocks fixture will have this overridden with
    their own tmp_path directory for isolation.
    """
    monkeypatch.setattr("s2dm.cli.DEFAULT_QUDT_UNITS_DIR", TestSchemaData.UNITS_SCHEMA_PATH)


def parsed_console_output() -> str:
    """Parse console output (placeholder function)."""
    return ""


@pytest.fixture(scope="module")
def schema_path() -> list[Path]:
    assert TestSchemaData.SCHEMA1.exists(), f"Missing test file: {TestSchemaData.SCHEMA1}"
    assert TestSchemaData.UNITS_SCHEMA_PATH.exists(), f"Missing units folder: {TestSchemaData.UNITS_SCHEMA_PATH}"
    return [TestSchemaData.SCHEMA1, TestSchemaData.UNITS_SCHEMA_PATH]


@dataclass
class MockFieldData:
    name: str
    data_type: str = ""
    unit: str = ""
    allowed: list[str] = field(default_factory=list)
    minimum: int | None = None
    maximum: int | None = None

    @property
    def parent_name(self) -> str:
        return "Vehicle"

    @property
    def is_enum_field(self) -> bool:
        return bool(self.allowed)

    @property
    def enum_name(self) -> str:
        return f"{self.parent_name}_{self.name.capitalize()}_Enum"

    @property
    def enum_schema_str(self) -> str:
        return f"""
            enum {self.enum_name if self.is_enum_field else self.unit_enum_name} {{
                {" ".join(self.allowed or self.unit_allowed_values)}
            }}
        """

    @property
    def unit_enum_name(self) -> str:
        return f"{self.unit.capitalize()}UnitEnum"

    @property
    def unit_default_value(self) -> str:
        return self.unit[:2]

    @property
    def unit_allowed_values(self) -> list[str]:
        return [self.unit_default_value]

    @classmethod
    def non_enum_field_data(cls, faker: Faker) -> "MockFieldData":
        """Generates a random non-enum field data with a random values
        e.g.
        length(unit: LengthUnitEnum = MILLIMETER): Int
        """
        name = faker.unique.word().lower()
        data_type = faker.random_element(SCALAR_TYPES)
        unit = faker.unique.word()

        return cls(name, data_type, unit)

    @classmethod
    def enum_field_data(cls, faker: Faker) -> "MockFieldData":
        """Generates a random enum field data with a random values
        e.g.
        lowVoltageSystemState: Vehicle_LowVoltageSystemState_Enum
        """

        name = faker.unique.word().lower()
        num_values = faker.random_int(min=2, max=5)
        allowed = [faker.unique.word().upper() for _ in range(num_values)]

        return cls(name, data_type="string", allowed=allowed)

    def to_field_str(self) -> str:
        if self.is_enum_field:
            return f"{self.name}: {self.enum_name}"
        return f"{self.name}(unit: {self.unit_enum_name} = {self.unit_default_value}): {self.data_type}"

    def expected_id_spec(self) -> IDGenerationSpec:
        sorted_allowed = sorted(self.allowed.copy())
        return IDGenerationSpec(
            name=f"{self.parent_name}.{self.name}",
            data_type=self.data_type.lower(),
            unit=self.unit_default_value,
            allowed=str(sorted_allowed or ""),
            minimum=self.minimum,
            maximum=self.maximum,
        )


@composite
def mock_graphql_schema_strategy(
    draw: Callable[[st.SearchStrategy[Any]], Any],
) -> tuple[GraphQLSchema, list[MockFieldData]]:
    """Generate a random GraphQL schema with random types and fields."""
    faker = Faker()

    # Generate fields with a random name and a random type
    num_fields = draw(st.integers(min_value=2, max_value=5))
    fields = []
    enums = []
    for _ in range(num_fields):
        if draw(st.booleans()):
            # Generate an enum field
            field_data = MockFieldData.enum_field_data(faker)
        else:
            field_data = MockFieldData.non_enum_field_data(faker)

        enums.append(field_data.enum_schema_str)
        fields.append(field_data)

    schema_str = gql(
        f"""#graphql
        type Query {{
            vehicle: Vehicle
        }}

        {" ".join(enums)}

        type Vehicle {{
            {" ".join(map(lambda f: f.to_field_str(), fields))}
        }}
        """
    )

    return ensure_query(build_schema(gql(schema_str))), fields


@composite
def mock_named_types_strategy(
    draw: Callable[[st.SearchStrategy[Any]], Any],
) -> tuple[list[GraphQLNamedType], list[MockFieldData]]:
    schema, fields = draw(mock_graphql_schema_strategy())
    return get_all_named_types(schema), fields


# Constants for common test values
MOCK_QUDT_VERSION = "3.1.5"
MOCK_ENUM_CONTENT = "enum TestEnum { TEST1 }"

# QUDT constants for unit testing
QUDT_UNIT_BASE = "http://qudt.org/vocab/unit"
QUDT_QK_BASE = "http://qudt.org/vocab/quantitykind"

# Standard test paths for units sync
STANDARD_UNIT_PATHS = [
    "velocity/VelocityUnitEnum.graphql",
    "mass/MassUnitEnum.graphql",
    "length/LengthUnitEnum.graphql",
]


@pytest.fixture
def mock_qudt_version() -> str:
    """Standard QUDT version for testing."""
    return MOCK_QUDT_VERSION


@pytest.fixture
def mock_get_latest_qudt_version(mock_qudt_version: str) -> Callable[[], str]:
    """Mock function for checking latest QUDT version."""

    def _mock() -> str:
        return mock_qudt_version

    return _mock


@pytest.fixture
def mock_sync_qudt_units() -> Callable[..., list[Path]]:
    """Mock function for sync_qudt_units with configurable behavior."""

    def _mock(
        units_root: Path,
        version: str | None = None,
        *,
        dry_run: bool = False,
        num_paths: int = 3,
        create_files: bool = True,
    ) -> list[Path]:
        # Generate test paths based on the number requested
        test_paths = [units_root / path for path in STANDARD_UNIT_PATHS[:num_paths]]

        # Simulate creating files only when not in dry-run mode and create_files is True
        if not dry_run and create_files:
            for path in test_paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(MOCK_ENUM_CONTENT)

        return test_paths

    return _mock


@pytest.fixture
def units_sync_mocks(
    monkeypatch: pytest.MonkeyPatch,
    mock_sync_qudt_units: Callable[..., list[Path]],
    mock_get_latest_qudt_version: Callable[[], str],
    tmp_path: Path,
) -> tuple[Callable[..., list[Path]], Callable[[], str]]:
    """Fixture that applies all units sync mocks at once and isolates DEFAULT_QUDT_UNITS_DIR."""
    # Patch DEFAULT_QUDT_UNITS_DIR to use a temporary directory for test isolation
    test_units_dir = tmp_path / "test_units"
    monkeypatch.setattr("s2dm.cli.DEFAULT_QUDT_UNITS_DIR", test_units_dir)

    monkeypatch.setattr("s2dm.cli.sync_qudt_units", mock_sync_qudt_units)
    monkeypatch.setattr("s2dm.cli.get_latest_qudt_version", mock_get_latest_qudt_version)
    return mock_sync_qudt_units, mock_get_latest_qudt_version


def create_test_unit_row(
    unit_segment: str,
    qk_segment: str,
    label: str | None = None,
    ucum: str | None = None,
) -> "UnitRow":
    """Create a test UnitRow with minimal required data.

    Note: This imports UnitRow and _uri_to_enum_symbol locally to avoid circular imports.
    """
    unit_label = label or unit_segment.lower().replace("-", " ")
    symbol = _uri_to_enum_symbol(f"{QUDT_UNIT_BASE}/{unit_segment}")

    return UnitRow(
        unit_iri=f"{QUDT_UNIT_BASE}/{unit_segment}",
        unit_label=unit_label,
        quantity_kind_iri=f"{QUDT_QK_BASE}/{qk_segment}",
        quantity_kind_label=qk_segment,
        symbol=symbol,
        ucum_code=ucum or unit_segment.lower(),
    )
