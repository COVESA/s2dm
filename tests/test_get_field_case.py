"""Tests for get_field_case and get_field_case_extended functions using the test_spec.graphql schema."""

from pathlib import Path

import pytest

from s2dm.exporters.utils import FieldCase, get_field_case, get_field_case_extended, load_schema


@pytest.fixture
def test_schema():  # type: ignore[no-untyped-def]
    """Load the test schema from test_spec.graphql."""
    schema_path = Path(__file__).parent / "test_type_modifiers" / "test_spec.graphql"
    return load_schema(schema_path)


@pytest.mark.parametrize(
    "field_name,expected_case",
    [
        # A - DEFAULT cases
        ("defaultScalar", FieldCase.DEFAULT),
        ("defaultType", FieldCase.DEFAULT),
        ("defaultWithInstances", FieldCase.DEFAULT),
        # B - NON_NULL cases
        ("nonNullScalar", FieldCase.NON_NULL),
        ("nonNull", FieldCase.NON_NULL),
        ("nonNullWithInstances", FieldCase.NON_NULL),
        # C - LIST cases
        ("listScalar", FieldCase.LIST),
        ("list", FieldCase.LIST),
        ("listWithInstances", FieldCase.LIST),
        # D - NON_NULL_LIST cases
        ("nonNullListScalar", FieldCase.NON_NULL_LIST),
        ("nonNullList", FieldCase.NON_NULL_LIST),
        ("nonNullListWithInstances", FieldCase.NON_NULL_LIST),
        # E - LIST_NON_NULL cases
        ("listNonNullScalar", FieldCase.LIST_NON_NULL),
        ("listNonNull", FieldCase.LIST_NON_NULL),
        ("listNonNullWithInstances", FieldCase.LIST_NON_NULL),
        # F - NON_NULL_LIST_NON_NULL cases
        ("nonNullListNonNullScalar", FieldCase.NON_NULL_LIST_NON_NULL),
        ("nonNullListNonNull", FieldCase.NON_NULL_LIST_NON_NULL),
        ("nonNullListNonNullWithInstances", FieldCase.NON_NULL_LIST_NON_NULL),
    ],
)
def test_get_field_case_basic(test_schema, field_name, expected_case):  # type: ignore[no-untyped-def]
    """Test get_field_case function with basic GraphQL field types (A-F cases)."""
    test_type = test_schema.type_map["TestTypeModifiers"]
    field = test_type.fields[field_name]

    actual_case = get_field_case(field)
    assert actual_case == expected_case, f"Field '{field_name}' expected {expected_case}, got {actual_case}"


@pytest.mark.parametrize(
    "field_name,expected_case",
    [
        # G - SET cases (LIST + @noDuplicates)
        ("setScalar", FieldCase.SET),
        ("set", FieldCase.SET),
        ("setEnum", FieldCase.SET),
        ("setWithInstances", FieldCase.SET),
        # H - SET_NON_NULL cases (LIST_NON_NULL + @noDuplicates)
        ("setNonNullScalar", FieldCase.SET_NON_NULL),
        ("setNonNull", FieldCase.SET_NON_NULL),
        ("setNonNullWithInstances", FieldCase.SET_NON_NULL),
    ],
)
def test_get_field_case_extended_with_directives(test_schema, field_name, expected_case):  # type: ignore[no-untyped-def]
    """Test get_field_case_extended function with custom directive cases (G-H cases)."""
    test_type = test_schema.type_map["TestTypeModifiers"]
    field = test_type.fields[field_name]

    actual_case = get_field_case_extended(field)
    assert actual_case == expected_case, f"Field '{field_name}' expected {expected_case}, got {actual_case}"


def test_get_field_case_vs_extended(test_schema):  # type: ignore[no-untyped-def]
    """Test that get_field_case and get_field_case_extended return different results for directive cases."""
    test_type = test_schema.type_map["TestTypeModifiers"]

    # Fields with @noDuplicates should differ between basic and extended
    set_fields = ["setScalar", "set", "setEnum", "setWithInstances"]
    set_non_null_fields = ["setNonNullScalar", "setNonNull", "setNonNullWithInstances"]

    for field_name in set_fields:
        field = test_type.fields[field_name]
        basic_case = get_field_case(field)
        extended_case = get_field_case_extended(field)

        assert basic_case == FieldCase.LIST
        assert extended_case == FieldCase.SET
        assert basic_case != extended_case  # type: ignore[comparison-overlap]

    for field_name in set_non_null_fields:
        field = test_type.fields[field_name]
        basic_case = get_field_case(field)
        extended_case = get_field_case_extended(field)

        assert basic_case == FieldCase.LIST_NON_NULL
        assert extended_case == FieldCase.SET_NON_NULL
        assert basic_case != extended_case  # type: ignore[comparison-overlap]


def test_all_field_cases_covered(test_schema):  # type: ignore[no-untyped-def]
    """Test that all FieldCase enum values are represented in the test schema."""
    test_type = test_schema.type_map["TestTypeModifiers"]

    # Get all field cases from the schema
    basic_cases = set()
    extended_cases = set()

    for _field_name, field in test_type.fields.items():
        basic_cases.add(get_field_case(field))
        extended_cases.add(get_field_case_extended(field))

    # Check that all FieldCase values are covered
    all_field_cases = set(FieldCase)

    assert extended_cases == all_field_cases, f"Missing field cases: {all_field_cases - extended_cases}"


def test_field_case_consistency(test_schema):  # type: ignore[no-untyped-def]
    """Test that field case logic is consistent across different output types."""
    test_type = test_schema.type_map["TestTypeModifiers"]

    # Group fields by their type pattern (e.g., all DEFAULT fields should behave the same)
    patterns = {
        "default": ["defaultScalar", "defaultType", "defaultWithInstances"],
        "nonNull": ["nonNullScalar", "nonNull", "nonNullWithInstances"],
        "list": ["listScalar", "list", "listWithInstances"],
        "nonNullList": ["nonNullListScalar", "nonNullList", "nonNullListWithInstances"],
        "listNonNull": ["listNonNullScalar", "listNonNull", "listNonNullWithInstances"],
        "nonNullListNonNull": ["nonNullListNonNullScalar", "nonNullListNonNull", "nonNullListNonNullWithInstances"],
    }

    for pattern_name, field_names in patterns.items():
        cases = [get_field_case(test_type.fields[fname]) for fname in field_names]
        # All fields in the same pattern should return the same FieldCase
        assert len(set(cases)) == 1, (
            f"Inconsistent field cases for pattern {pattern_name}: " f"{dict(zip(field_names, cases, strict=True))}"
        )
