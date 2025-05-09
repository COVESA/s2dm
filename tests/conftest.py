from dataclasses import dataclass, field

import pytest
from ariadne import gql
from faker import Faker
from graphql import (
    build_schema,
)
from hypothesis import strategies as st
from hypothesis.strategies import composite

from idgen.spec import IDGenerationSpec
from tools.utils import ensure_query, get_all_named_types

SCALAR_TYPES = ["String", "Int", "Float", "Boolean"]


class EchoDict(dict):
    """A dictionary that echoes the key as the value."""

    def __missing__(self, key):
        return key


@pytest.fixture(scope="session")
def mock_unit_lookup():
    return EchoDict()


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
                {' '.join(self.allowed or self.unit_allowed_values)}
            }}
        """

    @property
    def unit_enum_name(self) -> str:
        return f"{self.unit.capitalize()}_Unit_Enum"

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
        length(unit: Length_Unit_Enum = MILLIMETER): Int
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
def mock_graphql_schema_strategy(draw):
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

        {' '.join(enums)}

        type Vehicle {{
            {' '.join(map(lambda f: f.to_field_str(), fields))}
        }}
        """
    )

    return ensure_query(build_schema(gql(schema_str))), fields


@composite
def mock_named_types_strategy(draw):
    schema, fields = draw(mock_graphql_schema_strategy())
    return get_all_named_types(schema), fields
