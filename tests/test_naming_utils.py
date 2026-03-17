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

from s2dm.exporters.shacl import translate_to_shacl
from s2dm.exporters.utils.extraction import get_all_object_types, get_all_objects_with_directive
from s2dm.exporters.utils.instance_tag import expand_instance_tag, expand_instances_in_schema
from s2dm.exporters.utils.naming import (
    apply_naming_to_schema,
    convert_enum_values,
    convert_field_names,
    convert_name,
)
from s2dm.exporters.utils.naming_config import (
    ArgumentNamingConfig,
    CaseFormat,
    ContextType,
    ElementType,
    FieldNamingConfig,
    NamingConventionConfig,
    TypeNamingConfig,
    get_case_for_element,
)
from s2dm.exporters.utils.schema_loader import load_schema, load_schema_with_source_map, process_schema


class TestConvertName:
    """Test individual name conversion functions."""

    @pytest.mark.parametrize(
        "input_name,target_case,expected",
        [
            ("HelloWorld", CaseFormat.CAMEL_CASE, "helloWorld"),
            ("hello_world", CaseFormat.PASCAL_CASE, "HelloWorld"),
            ("HelloWorld", CaseFormat.SNAKE_CASE, "hello_world"),
            ("hello world", CaseFormat.KEBAB_CASE, "hello-world"),
            ("HelloWorld", CaseFormat.MACRO_CASE, "HELLO_WORLD"),
            ("hello-world", CaseFormat.COBOL_CASE, "HELLO-WORLD"),
            ("Hello World", CaseFormat.FLAT_CASE, "helloworld"),
            ("hello_world", CaseFormat.TITLE_CASE, "Hello World"),
        ],
    )
    def test_convert_name_supported_cases(self, input_name: str, target_case: CaseFormat, expected: str) -> None:
        """Test conversion for all supported case formats."""
        result = convert_name(input_name, target_case)
        assert result == expected

    def test_convert_name_empty_string(self) -> None:
        """Test conversion with empty string input."""
        result = convert_name("", CaseFormat.CAMEL_CASE)
        assert result == ""


class TestGetCaseForElement:
    """Test getting target case configuration for different element types."""

    def test_hierarchical_config(self) -> None:
        """Test hierarchical configuration lookup."""
        config = NamingConventionConfig(
            field=FieldNamingConfig(object=CaseFormat.CAMEL_CASE, interface=CaseFormat.SNAKE_CASE),
            enum_value=CaseFormat.MACRO_CASE,
            instance_tag=CaseFormat.FLAT_CASE,
        )

        result_object = get_case_for_element(ElementType.FIELD, ContextType.OBJECT, config)
        assert result_object == CaseFormat.CAMEL_CASE

        result_interface = get_case_for_element(ElementType.FIELD, ContextType.INTERFACE, config)
        assert result_interface == CaseFormat.SNAKE_CASE

        result_enum = get_case_for_element(ElementType.ENUM_VALUE, None, config)
        assert result_enum == CaseFormat.MACRO_CASE

    def test_missing_element_type(self) -> None:
        """Test behavior when element type is not in config."""
        config = NamingConventionConfig(field=FieldNamingConfig(object=CaseFormat.CAMEL_CASE))
        result = get_case_for_element(ElementType.TYPE, ContextType.ENUM, config)
        assert result is None

    def test_missing_context(self) -> None:
        """Test behavior when context is missing from hierarchical config."""
        config = NamingConventionConfig(field=FieldNamingConfig(object=CaseFormat.CAMEL_CASE))
        result = get_case_for_element(ElementType.FIELD, ContextType.INPUT, config)
        assert result is None

    def test_string_config_value(self) -> None:
        """Test when config value is a CaseFormat enum."""
        config = NamingConventionConfig(enum_value=CaseFormat.CAMEL_CASE, instance_tag=CaseFormat.FLAT_CASE)
        result = get_case_for_element(ElementType.ENUM_VALUE, None, config)
        assert result == CaseFormat.CAMEL_CASE


class TestApplyNamingToSchema:
    """Test applying naming configuration to GraphQL schemas."""

    def test_apply_naming_converts_type_names(self) -> None:
        """Test that type names are converted in the schema type_map."""
        enum_type = GraphQLEnumType(name="test_enum", values={"VALUE": GraphQLEnumValue("VALUE")})
        object_type = GraphQLObjectType(name="test_object", fields={"field": GraphQLField(GraphQLString)})

        query_type = GraphQLObjectType(name="Query", fields={"test": GraphQLField(object_type)})
        schema = GraphQLSchema(query=query_type, types=[object_type, enum_type])

        naming_config = NamingConventionConfig(
            type=TypeNamingConfig(object=CaseFormat.PASCAL_CASE, enum=CaseFormat.PASCAL_CASE)
        )

        apply_naming_to_schema(schema, naming_config)

        assert "TestObject" in schema.type_map
        assert "TestEnum" in schema.type_map
        assert "test_object" not in schema.type_map
        assert "test_enum" not in schema.type_map

        assert schema.type_map["TestObject"].name == "TestObject"
        assert schema.type_map["TestEnum"].name == "TestEnum"

    def test_apply_naming_preserves_builtin_types(self) -> None:
        """Test that built-in GraphQL types are not modified."""
        object_type = GraphQLObjectType(name="TestObject", fields={"field": GraphQLField(GraphQLString)})
        query_type = GraphQLObjectType(name="Query", fields={"test": GraphQLField(object_type)})
        schema = GraphQLSchema(query=query_type, types=[object_type])

        naming_config = NamingConventionConfig(type=TypeNamingConfig(object=CaseFormat.SNAKE_CASE))
        apply_naming_to_schema(schema, naming_config)

        # Built-in types should remain unchanged
        builtin_types = ["String", "Int", "Float", "Boolean", "ID", "Query", "Mutation", "Subscription"]
        for builtin in builtin_types:
            if builtin in schema.type_map:
                assert builtin in schema.type_map
                assert schema.type_map[builtin].name == builtin

    def test_apply_naming_converts_fields_and_enums_end_to_end(self) -> None:
        """Test complete schema conversion with types, fields, and enum values."""
        enum_type = GraphQLEnumType(name="test_enum", values={"OLD_VALUE": GraphQLEnumValue("OLD_VALUE")})

        object_type = GraphQLObjectType(
            name="test_object", fields={"TestField": GraphQLField(GraphQLString), "enum_field": GraphQLField(enum_type)}
        )

        query_type = GraphQLObjectType(name="Query", fields={"test": GraphQLField(object_type)})
        schema = GraphQLSchema(query=query_type, types=[object_type, enum_type])

        naming_config = NamingConventionConfig(
            type=TypeNamingConfig(object=CaseFormat.PASCAL_CASE, enum=CaseFormat.PASCAL_CASE),
            field=FieldNamingConfig(object=CaseFormat.CAMEL_CASE),
            enum_value=CaseFormat.PASCAL_CASE,
            instance_tag=CaseFormat.PASCAL_CASE,
        )

        apply_naming_to_schema(schema, naming_config)

        assert "TestObject" in schema.type_map
        assert "TestEnum" in schema.type_map

        test_object_type = schema.type_map["TestObject"]
        assert isinstance(test_object_type, GraphQLObjectType)
        assert "testField" in test_object_type.fields
        assert "enumField" in test_object_type.fields
        assert "TestField" not in test_object_type.fields
        assert "enum_field" not in test_object_type.fields

        test_enum_type = schema.type_map["TestEnum"]
        assert isinstance(test_enum_type, GraphQLEnumType)
        assert "OldValue" in test_enum_type.values
        assert "OLD_VALUE" not in test_enum_type.values

    def test_empty_naming_config_preserves_schema(self) -> None:
        """Test that empty config leaves schema unchanged."""
        object_type = GraphQLObjectType(name="TestObject", fields={"TestField": GraphQLField(GraphQLString)})
        query_type = GraphQLObjectType(name="Query", fields={"test": GraphQLField(object_type)})
        original_schema = GraphQLSchema(query=query_type, types=[object_type])

        apply_naming_to_schema(original_schema, NamingConventionConfig())

        assert "TestObject" in original_schema.type_map
        test_object_type = original_schema.type_map["TestObject"]
        assert isinstance(test_object_type, GraphQLObjectType)
        assert "TestField" in test_object_type.fields

    def test_apply_naming_routes_instancetag_enums_to_instancetag_case(self) -> None:
        """Enums inside @instanceTag types get instanceTag case; other enums get enumValue case."""
        from graphql import build_schema as _build_schema

        schema = _build_schema("""
            directive @instanceTag on OBJECT
            type Query { car: Car }
            type Car { kind: CarKind }
            enum TwoRows { front rear }
            enum TwoSides { left right }
            type DoorTag @instanceTag { row: TwoRows  side: TwoSides }
            enum CarKind { sedan suv }
        """)
        naming_config = NamingConventionConfig(
            enum_value=CaseFormat.MACRO_CASE,
            instance_tag=CaseFormat.PASCAL_CASE,
        )
        apply_naming_to_schema(schema, naming_config)

        # @instanceTag enums → PascalCase
        two_rows = schema.get_type("TwoRows")
        assert isinstance(two_rows, GraphQLEnumType)
        assert "Front" in two_rows.values
        assert "Rear" in two_rows.values
        assert "front" not in two_rows.values

        two_sides = schema.get_type("TwoSides")
        assert isinstance(two_sides, GraphQLEnumType)
        assert "Left" in two_sides.values
        assert "Right" in two_sides.values

        # Regular enum → MACRO_CASE
        car_kind = schema.get_type("CarKind")
        assert isinstance(car_kind, GraphQLEnumType)
        assert "SEDAN" in car_kind.values
        assert "SUV" in car_kind.values
        assert "sedan" not in car_kind.values


class TestConvertFieldNames:
    """Test field name conversion functionality - verifies GraphQL schema objects are modified."""

    def test_convert_object_field_names_updates_dict_keys_and_objects(self) -> None:
        """Test that field conversion updates both dictionary keys and field.name properties."""
        object_type = GraphQLObjectType(
            name="TestObject",
            fields={"TestField": GraphQLField(GraphQLString), "AnotherTestField": GraphQLField(GraphQLString)},
        )

        naming_config = NamingConventionConfig(field=FieldNamingConfig(object=CaseFormat.CAMEL_CASE))
        schema = GraphQLSchema(query=object_type)
        convert_field_names(object_type, naming_config, schema)

        assert "testField" in object_type.fields
        assert "anotherTestField" in object_type.fields
        assert "TestField" not in object_type.fields
        assert "AnotherTestField" not in object_type.fields

    def test_convert_interface_field_names(self) -> None:
        """Test field conversion works for interface types."""
        interface_type = GraphQLInterfaceType(name="TestInterface", fields={"TestField": GraphQLField(GraphQLString)})

        naming_config = NamingConventionConfig(field=FieldNamingConfig(interface=CaseFormat.SNAKE_CASE))
        schema = GraphQLSchema(query=GraphQLObjectType(name="Query", fields={}))
        convert_field_names(interface_type, naming_config, schema)

        assert "test_field" in interface_type.fields
        assert "TestField" not in interface_type.fields

    def test_convert_input_field_names(self) -> None:
        """Test field conversion works for input types."""
        input_type = GraphQLInputObjectType(name="TestInput", fields={"TestField": GraphQLInputField(GraphQLString)})

        naming_config = NamingConventionConfig(field=FieldNamingConfig(input=CaseFormat.KEBAB_CASE))
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

        naming_config = NamingConventionConfig(argument=ArgumentNamingConfig(field=CaseFormat.MACRO_CASE))
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
        convert_field_names(object_type, NamingConventionConfig(), schema)

        assert "TestField" in object_type.fields

    def test_skip_instance_tag_field_conversion(self, spec_directory: Path) -> None:
        """Test that instanceTag fields pointing to @instanceTag types are not converted."""
        schema_path = Path(__file__).parent / "test_expanded_instances" / "test_schema.graphql"
        schema = load_schema([spec_directory, schema_path])

        door_type = schema.get_type("Door")
        assert isinstance(door_type, GraphQLObjectType)

        door_type.fields["regularField"] = GraphQLField(GraphQLString)

        naming_config = NamingConventionConfig(field=FieldNamingConfig(object=CaseFormat.CAMEL_CASE))
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

        naming_config = NamingConventionConfig(enum_value=CaseFormat.PASCAL_CASE, instance_tag=CaseFormat.PASCAL_CASE)
        convert_enum_values(enum_type, naming_config)

        assert "OldValue" in enum_type.values
        assert "AnotherOldValue" in enum_type.values
        assert "OLD_VALUE" not in enum_type.values
        assert "ANOTHER_OLD_VALUE" not in enum_type.values

    def test_enum_conversion_preserves_other_properties(self) -> None:
        """Test that other enum value properties are preserved during conversion."""
        enum_value = GraphQLEnumValue("OLD_VALUE", description="Test description")
        enum_type = GraphQLEnumType(name="TestEnum", values={"OLD_VALUE": enum_value})

        naming_config = NamingConventionConfig(enum_value=CaseFormat.CAMEL_CASE, instance_tag=CaseFormat.CAMEL_CASE)
        convert_enum_values(enum_type, naming_config)

        converted_value = enum_type.values["oldValue"]
        assert converted_value.description == "Test description"

    def test_no_conversion_when_no_config(self) -> None:
        """Test that enum values remain unchanged when no config is provided."""
        enum_type = GraphQLEnumType(name="TestEnum", values={"OLD_VALUE": GraphQLEnumValue("OLD_VALUE")})

        convert_enum_values(enum_type, NamingConventionConfig())

        assert "OLD_VALUE" in enum_type.values


class TestInstanceTagConversion:
    """Test instance tag expansion with naming conversion."""

    def test_expand_instance_tag_with_naming_config(self, spec_directory: Path) -> None:
        """Test that instance tag expansion applies naming conversion."""
        schema_path = Path(__file__).parent / "test_expanded_instances" / "test_schema.graphql"
        schema = load_schema([spec_directory, schema_path])
        object_types = get_all_object_types(schema)
        instance_tag_objects = get_all_objects_with_directive(object_types, "instanceTag")

        assert len(instance_tag_objects) > 0
        door_position = next((obj for obj in instance_tag_objects if obj.name == "DoorPosition"), None)
        assert door_position is not None

        naming_config = NamingConventionConfig(instance_tag=CaseFormat.PASCAL_CASE)
        result = expand_instance_tag(door_position, naming_config)

        expected = ["Row1.Driverside", "Row1.Passengerside", "Row2.Driverside", "Row2.Passengerside"]
        assert set(result) == set(expected)

    def test_expand_instance_tag_without_naming_config(self, spec_directory: Path) -> None:
        """Test that instance tag expansion works without naming config."""
        schema_path = Path(__file__).parent / "test_expanded_instances" / "test_schema.graphql"
        schema = load_schema([spec_directory, schema_path])
        object_types = get_all_object_types(schema)
        instance_tag_objects = get_all_objects_with_directive(object_types, "instanceTag")

        door_position = next((obj for obj in instance_tag_objects if obj.name == "DoorPosition"), None)
        assert door_position is not None

        result = expand_instance_tag(door_position)

        expected = ["ROW1.DRIVERSIDE", "ROW1.PASSENGERSIDE", "ROW2.DRIVERSIDE", "ROW2.PASSENGERSIDE"]
        assert set(result) == set(expected)

    def test_expand_instances_in_schema_pipeline_applies_instance_tag_case(self, spec_directory: Path) -> None:
        """Full pipeline: expand_instances_in_schema applies instanceTag case to resolved_names."""
        schema_path = Path(__file__).parent / "test_expanded_instances" / "test_schema.graphql"
        schema = load_schema([spec_directory, schema_path])

        naming_config = NamingConventionConfig(
            enum_value=CaseFormat.MACRO_CASE,
            instance_tag=CaseFormat.PASCAL_CASE,
        )

        apply_naming_to_schema(schema, naming_config)
        _, _, field_metadata = expand_instances_in_schema(schema, naming_config)

        door_meta = field_metadata.get(("Vehicle", "Door"))
        assert door_meta is not None
        assert set(door_meta.resolved_names) == {
            "Door.Row1.Driverside",
            "Door.Row1.Passengerside",
            "Door.Row2.Driverside",
            "Door.Row2.Passengerside",
        }

    def test_shacl_instancetag_nodeshape_uses_instance_tag_case(self, spec_directory: Path) -> None:
        """translate_to_shacl applies instanceTag naming to sh:in values inside @instanceTag NodeShapes."""
        from rdflib import Namespace
        from rdflib.collection import Collection
        from rdflib.namespace import SH

        schema_path = Path(__file__).parent / "test_expanded_instances" / "test_schema.graphql"
        schema, source_map = load_schema_with_source_map([spec_directory, schema_path])

        naming_config = NamingConventionConfig(
            enum_value=CaseFormat.MACRO_CASE,
            instance_tag=CaseFormat.PASCAL_CASE,
        )

        annotated = process_schema(schema, source_map, naming_config, expanded_instances=False)
        graph = translate_to_shacl(
            annotated,
            "http://ex/shapes#",
            "shapes",
            "http://ex/model#",
            "model",
        )

        shapes_ns = Namespace("http://ex/shapes#")
        door_position_shape = shapes_ns["DoorPosition"]
        sh_in_values: set[str] = set()
        for _, _, prop_node in graph.triples((door_position_shape, SH.property, None)):
            for _, _, in_list in graph.triples((prop_node, SH["in"], None)):
                for val in Collection(graph, in_list):
                    sh_in_values.add(str(val))

        # DoorPosition has row: RowEnum (ROW1, ROW2) and side: SideEnum (DRIVERSIDE, PASSENGERSIDE)
        # instanceTag: PascalCase -> Row1, Row2, Driverside, Passengerside
        assert sh_in_values == {"Row1", "Row2", "Driverside", "Passengerside"}


if __name__ == "__main__":
    pytest.main([__file__])
