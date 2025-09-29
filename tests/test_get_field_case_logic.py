"""Additional tests to verify the get_field_case implementation logic."""

from graphql import GraphQLField, GraphQLList, GraphQLNonNull, GraphQLString

from s2dm.exporters.utils.field import FieldCase, get_field_case


def test_get_field_case_implementation_logic() -> None:
    """Test the implementation logic of get_field_case with manually constructed GraphQL types."""

    # Test DEFAULT: String
    field_default = GraphQLField(GraphQLString)
    assert get_field_case(field_default) == FieldCase.DEFAULT

    # Test NON_NULL: String!
    field_non_null = GraphQLField(GraphQLNonNull(GraphQLString))
    assert get_field_case(field_non_null) == FieldCase.NON_NULL

    # Test LIST: [String]
    field_list = GraphQLField(GraphQLList(GraphQLString))
    assert get_field_case(field_list) == FieldCase.LIST

    # Test NON_NULL_LIST: [String]!
    field_non_null_list = GraphQLField(GraphQLNonNull(GraphQLList(GraphQLString)))
    assert get_field_case(field_non_null_list) == FieldCase.NON_NULL_LIST

    # Test LIST_NON_NULL: [String!]
    field_list_non_null = GraphQLField(GraphQLList(GraphQLNonNull(GraphQLString)))
    assert get_field_case(field_list_non_null) == FieldCase.LIST_NON_NULL

    # Test NON_NULL_LIST_NON_NULL: [String!]!
    field_non_null_list_non_null = GraphQLField(GraphQLNonNull(GraphQLList(GraphQLNonNull(GraphQLString))))
    assert get_field_case(field_non_null_list_non_null) == FieldCase.NON_NULL_LIST_NON_NULL


def test_get_field_case_edge_cases() -> None:
    """Test edge cases and nested type unwrapping."""

    # Deep nesting should still work correctly
    deeply_nested = GraphQLNonNull(GraphQLList(GraphQLNonNull(GraphQLString)))
    field = GraphQLField(deeply_nested)
    assert get_field_case(field) == FieldCase.NON_NULL_LIST_NON_NULL

    # Single non-null
    single_non_null = GraphQLNonNull(GraphQLString)
    field_single = GraphQLField(single_non_null)
    assert get_field_case(field_single) == FieldCase.NON_NULL


if __name__ == "__main__":
    test_get_field_case_implementation_logic()
    test_get_field_case_edge_cases()
    print("All implementation logic tests passed!")
