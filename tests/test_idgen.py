import ast

import pytest
from faker import Faker
from graphql import GraphQLNamedType
from hypothesis import given

from idgen.idgen import fnv1_32_wrapper
from idgen.spec import IDGenerationSpec
from tests.conftest import (
    MockFieldData,
    mock_named_types_strategy,
)
from tools.to_id import iter_all_id_specs


@given(named_types_and_fields=mock_named_types_strategy())
def test_id_spec_generation_of_all_fields_from_graphql_schema(
    named_types_and_fields: tuple[list[GraphQLNamedType], list[MockFieldData]],
    mock_unit_lookup: dict,
):
    """Test that ID generation spec can be generated from a GraphQL schema."""
    named_types, fields = named_types_and_fields
    expected_id_specs = {field.expected_id_spec() for field in fields}

    all_id_specs = set(iter_all_id_specs(named_types, mock_unit_lookup))

    for expected_id_spec in expected_id_specs:
        assert expected_id_spec in all_id_specs


@given(named_types_and_fields=mock_named_types_strategy())
@pytest.mark.parametrize("strict_mode", [True, False])
def test_id_generation_is_deterministic_across_iterations(
    named_types_and_fields: tuple[list[GraphQLNamedType], list[MockFieldData]],
    strict_mode: bool,
    mock_unit_lookup: dict,
):
    """Test that ID generation is deterministic across iterations."""

    named_types, _ = named_types_and_fields

    all_id_specs = set(iter_all_id_specs(named_types, mock_unit_lookup))

    first_iteration_ids = {}
    for id_spec in all_id_specs:
        field_id = fnv1_32_wrapper(id_spec, strict_mode=strict_mode)
        first_iteration_ids[id_spec.name] = field_id

    second_iteration_ids = {}
    for id_spec in all_id_specs:
        field_id = fnv1_32_wrapper(id_spec, strict_mode=strict_mode)
        second_iteration_ids[id_spec.name] = field_id

    assert first_iteration_ids == second_iteration_ids


@given(named_types_and_fields=mock_named_types_strategy())
@pytest.mark.parametrize("strict_mode", [True, False])
def test_id_generation_is_unique_accros_schema(
    named_types_and_fields: tuple[list[GraphQLNamedType], list[MockFieldData]],
    strict_mode: bool,
    mock_unit_lookup: dict,
):
    """Test that ID generation produces unique IDs across the schema fields."""

    named_types, _ = named_types_and_fields

    ids = {}
    for id_spec in iter_all_id_specs(named_types, mock_unit_lookup):
        field_id = fnv1_32_wrapper(id_spec, strict_mode=strict_mode)
        ids[id_spec.name] = field_id

    assert len(ids) == len(set(ids.values())), f"Generated duplicate IDs!: {ids}"


@pytest.mark.parametrize("strict_mode", [True, False])
def test_id_generation_changes_with_field_changes_for_enum_field_allowed_values(strict_mode: bool, faker: Faker):
    """Test that ID generation changes with allowed values."""

    changes_to_test = [
        # Adding a new value
        lambda lst: lst.append(faker.unique.word()),
        # Removing a value
        lambda lst: lst.pop(),
        # Inserting a value at a specific index
        lambda lst: lst.insert(len(lst) // 2, faker.unique.word()),
    ]

    original_id_spec = MockFieldData.enum_field_data(faker).expected_id_spec()
    initial_id = fnv1_32_wrapper(original_id_spec, strict_mode=strict_mode)
    assert initial_id is not None

    id_spec_dict = original_id_spec.__dict__.copy()
    original_allowed_values = ast.literal_eval(id_spec_dict["allowed"])

    for change_fn in changes_to_test:
        allowed_values_copy = original_allowed_values.copy()
        # Apply the change to the allowed values
        change_fn(allowed_values_copy)
        id_spec_dict["allowed"] = allowed_values_copy

        new_id_spec = IDGenerationSpec(**id_spec_dict)

        changed_id = fnv1_32_wrapper(new_id_spec, strict_mode=strict_mode)

        assert changed_id is not None
        assert changed_id != initial_id


@pytest.mark.parametrize("strict_mode", [True, False])
@pytest.mark.parametrize("field_to_change", ["name", "data_type", "unit", "minimum", "maximum"])
def test_id_generation_changes_with_field_changes_for_non_enum_field(
    strict_mode: bool, field_to_change: str, faker: Faker
):
    """Test that ID generation changes with field changes."""

    mock_field_data = MockFieldData.non_enum_field_data(faker)
    id_spec = mock_field_data.expected_id_spec()
    initial_id = fnv1_32_wrapper(id_spec, strict_mode=strict_mode)
    assert initial_id is not None

    id_spec_dict = id_spec.__dict__

    # Change the field to a new value
    if field_to_change in ["name", "data_type", "unit"]:
        new_field_value = "New" + getattr(id_spec, field_to_change)
    elif field_to_change in ["minimum", "maximum"]:
        new_field_value = faker.random_int(min=id_spec.minimum or 1, max=id_spec.maximum or 100)
    else:
        raise ValueError(f"Invalid field to change: {field_to_change}")

    # Create a new ID spec with the changed field
    id_spec_dict[field_to_change] = new_field_value
    new_id_spec = IDGenerationSpec(**id_spec_dict)

    changed_id = fnv1_32_wrapper(new_id_spec, strict_mode=strict_mode)

    assert changed_id is not None
    assert changed_id != initial_id
