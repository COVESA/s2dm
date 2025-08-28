from pathlib import Path

import pytest
from graphql import (
    GraphQLArgument,
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLField,
    GraphQLInputField,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLSchema,
    GraphQLString,
)

from s2dm.exporters.naming_utils import (
    apply_naming_to_schema,
    convert_enum_values,
    convert_field_names,
    convert_name,
    get_target_case_for_element,
)
from s2dm.exporters.utils import (
    expand_instance_tag,
    get_all_object_types,
    get_all_objects_with_directive,
    load_schema,
)


class TestConvertName:
    """Test individual name conversion functions."""

    @pytest.mark.parametrize(
        "input_name,target_case,expected",
        [
            ("HelloWorld", "camelCase", "helloWorld"),
            ("hello_world", "PascalCase", "HelloWorld"),
            ("HelloWorld", "snake_case", "hello_world"),
            ("hello world", "kebab-case", "hello-world"),
            ("HelloWorld", "MACROCASE", "HELLO_WORLD"),
            ("hello-world", "COBOL-CASE", "HELLO-WORLD"),
            ("Hello World", "flatcase", "helloworld"),
            ("hello_world", "TitleCase", "Hello World"),
        ],
    )
    def test_convert_name_supported_cases(self, input_name: str, target_case: str, expected: str) -> None:
        """Test conversion for all supported case formats."""
        result = convert_name(input_name, target_case)
        assert result == expected

    def test_convert_name_unsupported_case(self) -> None:
        """Test that unsupported cases return the original name."""
        original = "HelloWorld"
        result = convert_name(original, "unsupported_case")
        assert result == original

    def test_convert_name_empty_string(self) -> None:
        """Test conversion with empty string input."""
        result = convert_name("", "camelCase")
        assert result == ""


class TestGetTargetCaseForElement:
    """Test getting target case configuration for different element types."""

    def test_hierarchical_config(self) -> None:
        """Test hierarchical configuration lookup."""
        config = {"field": {"object": "camelCase", "interface": "snake_case"}, "enumValue": "macrocase"}

        # Test hierarchical lookup
        assert get_target_case_for_element("field", "object", config) == "camelCase"
        assert get_target_case_for_element("field", "interface", config) == "snake_case"

        # Test direct lookup
        assert get_target_case_for_element("enumValue", "", config) == "macrocase"

    def test_missing_element_type(self) -> None:
        """Test behavior when element type is not in config."""
        config = {"field": {"object": "camelCase"}}
        result = get_target_case_for_element("missing", "context", config)
        assert result is None

    def test_missing_context(self) -> None:
        """Test behavior when context is missing from hierarchical config."""
        config = {"field": {"object": "camelCase"}}
        result = get_target_case_for_element("field", "missing_context", config)
        assert result is None

    def test_string_config_value(self) -> None:
        """Test when config value is a string instead of dict."""
        config = {"enumValue": "camelCase"}
        result = get_target_case_for_element("enumValue", "", config)
        assert result == "camelCase"


class TestApplyNamingToSchema:
    """Test applying naming configuration to GraphQL schemas."""

    def test_apply_naming_converts_type_names(self) -> None:
        """Test that type names are converted in the schema type_map."""
        enum_type = GraphQLEnumType(name="test_enum", values={"VALUE": GraphQLEnumValue("VALUE")})
        object_type = GraphQLObjectType(name="test_object", fields={"field": GraphQLField(GraphQLString)})

        query_type = GraphQLObjectType(name="Query", fields={"test": GraphQLField(object_type)})
        schema = GraphQLSchema(query=query_type, types=[object_type, enum_type])

        naming_config = {"type": {"object": "PascalCase", "enum": "PascalCase"}}

        converted_schema = apply_naming_to_schema(schema, naming_config)

        assert "TestObject" in converted_schema.type_map
        assert "TestEnum" in converted_schema.type_map
        assert "test_object" not in converted_schema.type_map
        assert "test_enum" not in converted_schema.type_map

        assert converted_schema.type_map["TestObject"].name == "TestObject"
        assert converted_schema.type_map["TestEnum"].name == "TestEnum"

    def test_apply_naming_preserves_builtin_types(self) -> None:
        """Test that built-in GraphQL types are not modified."""
        object_type = GraphQLObjectType(name="TestObject", fields={"field": GraphQLField(GraphQLString)})
        query_type = GraphQLObjectType(name="Query", fields={"test": GraphQLField(object_type)})
        schema = GraphQLSchema(query=query_type, types=[object_type])

        naming_config = {"type": {"object": "snake_case"}}
        converted_schema = apply_naming_to_schema(schema, naming_config)

        # Built-in types should remain unchanged
        builtin_types = ["String", "Int", "Float", "Boolean", "ID", "Query", "Mutation", "Subscription"]
        for builtin in builtin_types:
            if builtin in schema.type_map:
                assert builtin in converted_schema.type_map
                assert converted_schema.type_map[builtin].name == builtin

    def test_apply_naming_converts_fields_and_enums_end_to_end(self) -> None:
        """Test complete schema conversion with types, fields, and enum values."""
        enum_type = GraphQLEnumType(name="test_enum", values={"OLD_VALUE": GraphQLEnumValue("OLD_VALUE")})

        object_type = GraphQLObjectType(
            name="test_object", fields={"TestField": GraphQLField(GraphQLString), "enum_field": GraphQLField(enum_type)}
        )

        query_type = GraphQLObjectType(name="Query", fields={"test": GraphQLField(object_type)})
        schema = GraphQLSchema(query=query_type, types=[object_type, enum_type])

        naming_config = {
            "type": {"object": "PascalCase", "enum": "PascalCase"},
            "field": {"object": "camelCase"},
            "enumValue": "PascalCase",
        }

        converted_schema = apply_naming_to_schema(schema, naming_config)

        assert "TestObject" in converted_schema.type_map
        assert "TestEnum" in converted_schema.type_map

        test_object_type = converted_schema.type_map["TestObject"]
        assert isinstance(test_object_type, GraphQLObjectType)
        assert "testField" in test_object_type.fields
        assert "enumField" in test_object_type.fields
        assert "TestField" not in test_object_type.fields
        assert "enum_field" not in test_object_type.fields

        test_enum_type = converted_schema.type_map["TestEnum"]
        assert isinstance(test_enum_type, GraphQLEnumType)
        assert "OldValue" in test_enum_type.values
        assert "OLD_VALUE" not in test_enum_type.values

    def test_empty_naming_config_preserves_schema(self) -> None:
        """Test that empty config leaves schema unchanged."""
        object_type = GraphQLObjectType(name="TestObject", fields={"TestField": GraphQLField(GraphQLString)})
        query_type = GraphQLObjectType(name="Query", fields={"test": GraphQLField(object_type)})
        original_schema = GraphQLSchema(query=query_type, types=[object_type])

        converted_schema = apply_naming_to_schema(original_schema, {})

        assert len(converted_schema.type_map) == len(original_schema.type_map)
        assert "TestObject" in converted_schema.type_map
        test_object_type = converted_schema.type_map["TestObject"]
        assert isinstance(test_object_type, GraphQLObjectType)
        assert "TestField" in test_object_type.fields


class TestConvertFieldNames:
    """Test field name conversion functionality - verifies GraphQL schema objects are modified."""

    def test_convert_object_field_names_updates_dict_keys_and_objects(self) -> None:
        """Test that field conversion updates both dictionary keys and field.name properties."""
        object_type = GraphQLObjectType(
            name="TestObject",
            fields={"TestField": GraphQLField(GraphQLString), "AnotherTestField": GraphQLField(GraphQLString)},
        )

        naming_config = {"field": {"object": "camelCase"}}
        schema = GraphQLSchema(query=object_type)
        convert_field_names(object_type, naming_config, schema)

        assert "testField" in object_type.fields
        assert "anotherTestField" in object_type.fields
        assert "TestField" not in object_type.fields
        assert "AnotherTestField" not in object_type.fields

    def test_convert_interface_field_names(self) -> None:
        """Test field conversion works for interface types."""
        interface_type = GraphQLInterfaceType(name="TestInterface", fields={"TestField": GraphQLField(GraphQLString)})

        naming_config = {"field": {"interface": "snake_case"}}
        schema = GraphQLSchema(query=GraphQLObjectType(name="Query", fields={}))
        convert_field_names(interface_type, naming_config, schema)

        assert "test_field" in interface_type.fields
        assert "TestField" not in interface_type.fields

    def test_convert_input_field_names(self) -> None:
        """Test field conversion works for input types."""
        input_type = GraphQLInputObjectType(name="TestInput", fields={"TestField": GraphQLInputField(GraphQLString)})

        naming_config = {"field": {"input": "kebab-case"}}
        schema = GraphQLSchema(query=GraphQLObjectType(name="Query", fields={}))
        convert_field_names(input_type, naming_config, schema)

        assert "test-field" in input_type.fields
        assert "TestField" not in input_type.fields

    def test_convert_argument_names(self) -> None:
        """Test that field arguments are also converted."""
        object_type = GraphQLObjectType(
            name="TestObject",
            fields={
                "testField": GraphQLField(
                    GraphQLString,
                    args={"TestArg": GraphQLArgument(GraphQLString), "AnotherArg": GraphQLArgument(GraphQLString)},
                )
            },
        )

        naming_config = {"argument": {"field": "MACROCASE"}}
        schema = GraphQLSchema(query=object_type)
        convert_field_names(object_type, naming_config, schema)

        field_args = object_type.fields["testField"].args
        assert "TEST_ARG" in field_args
        assert "ANOTHER_ARG" in field_args
        assert "TestArg" not in field_args
        assert "AnotherArg" not in field_args

    def test_no_conversion_when_no_config(self) -> None:
        """Test that fields remain unchanged when no config is provided."""
        object_type = GraphQLObjectType(name="TestObject", fields={"TestField": GraphQLField(GraphQLString)})

        schema = GraphQLSchema(query=object_type)
        convert_field_names(object_type, {}, schema)

        assert "TestField" in object_type.fields

    def test_skip_instance_tag_field_conversion(self) -> None:
        """Test that instanceTag fields pointing to @instanceTag types are not converted."""
        schema_path = Path(__file__).parent / "test_expanded_instances" / "test_schema.graphql"
        schema = load_schema(schema_path)

        door_type = schema.get_type("Door")
        assert isinstance(door_type, GraphQLObjectType)

        door_type.fields["regularField"] = GraphQLField(GraphQLString)

        naming_config = {"field": {"object": "camelCase"}}
        convert_field_names(door_type, naming_config, schema)

        assert "instanceTag" in door_type.fields
        assert "instancetag" not in door_type.fields

        assert "regularField" in door_type.fields
        assert "RegularField" not in door_type.fields

        assert "isLocked" in door_type.fields  # was "isLocked" -> should stay as is in camelCase


class TestConvertEnumValues:
    """Test enum value conversion functionality - verifies GraphQL schema objects are modified."""

    def test_convert_enum_values_updates_dict_keys_and_objects(self) -> None:
        """Test that enum conversion updates both dictionary keys and enum value names."""
        enum_type = GraphQLEnumType(
            name="TestEnum",
            values={
                "OLD_VALUE": GraphQLEnumValue("OLD_VALUE"),
                "ANOTHER_OLD_VALUE": GraphQLEnumValue("ANOTHER_OLD_VALUE"),
            },
        )

        naming_config = {"enumValue": "PascalCase"}
        convert_enum_values(enum_type, naming_config)

        assert "OldValue" in enum_type.values
        assert "AnotherOldValue" in enum_type.values
        assert "OLD_VALUE" not in enum_type.values
        assert "ANOTHER_OLD_VALUE" not in enum_type.values

    def test_enum_conversion_preserves_other_properties(self) -> None:
        """Test that other enum value properties are preserved during conversion."""
        enum_value = GraphQLEnumValue("OLD_VALUE", description="Test description")
        enum_type = GraphQLEnumType(name="TestEnum", values={"OLD_VALUE": enum_value})

        naming_config = {"enumValue": "camelCase"}
        convert_enum_values(enum_type, naming_config)

        converted_value = enum_type.values["oldValue"]
        assert converted_value.description == "Test description"

    def test_no_conversion_when_no_config(self) -> None:
        """Test that enum values remain unchanged when no config is provided."""
        enum_type = GraphQLEnumType(name="TestEnum", values={"OLD_VALUE": GraphQLEnumValue("OLD_VALUE")})

        convert_enum_values(enum_type, {})

        assert "OLD_VALUE" in enum_type.values


class TestInstanceTagConversion:
    """Test instance tag expansion with naming conversion."""

    def test_expand_instance_tag_with_naming_config(self) -> None:
        """Test that instance tag expansion applies naming conversion."""
        schema_path = Path(__file__).parent / "test_expanded_instances" / "test_schema.graphql"
        schema = load_schema(schema_path)
        object_types = get_all_object_types(schema)
        instance_tag_objects = get_all_objects_with_directive(object_types, "instanceTag")

        assert len(instance_tag_objects) > 0
        door_position = next((obj for obj in instance_tag_objects if obj.name == "DoorPosition"), None)
        assert door_position is not None

        naming_config = {"instanceTag": "PascalCase"}
        result = expand_instance_tag(door_position, naming_config)

        expected = ["Row1.Driverside", "Row1.Passengerside", "Row2.Driverside", "Row2.Passengerside"]
        assert set(result) == set(expected)

    def test_expand_instance_tag_without_naming_config(self) -> None:
        """Test that instance tag expansion works without naming config."""
        schema_path = Path(__file__).parent / "test_expanded_instances" / "test_schema.graphql"
        schema = load_schema(schema_path)
        object_types = get_all_object_types(schema)
        instance_tag_objects = get_all_objects_with_directive(object_types, "instanceTag")

        door_position = next((obj for obj in instance_tag_objects if obj.name == "DoorPosition"), None)
        assert door_position is not None

        result = expand_instance_tag(door_position)

        expected = ["ROW1.DRIVERSIDE", "ROW1.PASSENGERSIDE", "ROW2.DRIVERSIDE", "ROW2.PASSENGERSIDE"]
        assert set(result) == set(expected)


if __name__ == "__main__":
    pytest.main([__file__])
