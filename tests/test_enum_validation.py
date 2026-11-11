from graphql import build_schema

from s2dm.exporters.utils.schema_loader import build_schema_with_query, check_correct_schema
from s2dm.exporters.utils.violations import ConstraintCode
from s2dm.tools.constraint_checker import get_directive_enum_value_errors


class TestEnumValueValidation:
    def test_valid_input_field_default(self) -> None:
        schema = build_schema_with_query(
            """
            enum Color { RED BLUE GREEN }

            input VehicleInput {
                color: Color = RED
            }
            """
        )
        errors = check_correct_schema(schema)
        assert errors == []

    def test_invalid_input_field_default(self) -> None:
        schema = build_schema_with_query(
            """
            enum Color { RED BLUE GREEN }

            input VehicleInput {
                color: Color = YELLOW
            }
            """
        )
        errors = check_correct_schema(schema)
        assert len(errors) == 1

        error = errors[0]
        assert error.code == ConstraintCode.SCHEMA_SPEC
        assert "VehicleInput.color" in error.message
        assert "YELLOW" in error.message

    def test_invalid_enum_defaults_on_multiple_inputs(self) -> None:
        schema = build_schema_with_query(
            """
            enum Color { RED BLUE GREEN }
            enum EngineType { ELECTRIC HYBRID COMBUSTION }

            input VehicleInput {
                color: Color = YELLOW
                engineType: EngineType = DIESEL
            }

            input BikeInput {
                color: Color = PURPLE
            }
            """
        )
        errors = check_correct_schema(schema)
        assert len(errors) == 3

        vehicle_color_error = errors[0]
        assert vehicle_color_error.code == ConstraintCode.SCHEMA_SPEC
        assert "VehicleInput.color" in vehicle_color_error.message
        assert "YELLOW" in vehicle_color_error.message

        vehicle_engine_error = errors[1]
        assert vehicle_engine_error.code == ConstraintCode.SCHEMA_SPEC
        assert "VehicleInput.engineType" in vehicle_engine_error.message
        assert "DIESEL" in vehicle_engine_error.message

        bike_color_error = errors[2]
        assert bike_color_error.code == ConstraintCode.SCHEMA_SPEC
        assert "BikeInput.color" in bike_color_error.message
        assert "PURPLE" in bike_color_error.message

    def test_valid_field_argument_default(self) -> None:
        schema = build_schema_with_query(
            """
            type Query {
                vehicle(color: Color = RED): String
            }

            enum Color { RED BLUE GREEN }
            """
        )
        errors = check_correct_schema(schema)
        assert errors == []

    def test_invalid_field_argument_default(self) -> None:
        schema = build_schema_with_query(
            """
            type Query {
                vehicle(color: Color = YELLOW): String
            }

            enum Color { RED BLUE GREEN }
            """
        )
        errors = check_correct_schema(schema)
        assert len(errors) == 1

        error = errors[0]
        assert error.code == ConstraintCode.SCHEMA_SPEC
        assert "Query.vehicle(color:)" in error.message
        assert "YELLOW" in error.message

    def test_valid_directive_definition_default(self) -> None:
        schema = build_schema_with_query(
            """
            directive @color(value: Color = RED) on OBJECT

            enum Color { RED BLUE GREEN }
            """
        )
        errors = check_correct_schema(schema)
        assert errors == []

    def test_invalid_directive_definition_default(self) -> None:
        schema = build_schema_with_query(
            """
            directive @color(value: Color = YELLOW) on OBJECT

            enum Color { RED BLUE GREEN }
            """
        )
        errors = check_correct_schema(schema)
        assert len(errors) == 1

        error = errors[0]
        assert error.code == ConstraintCode.SCHEMA_SPEC
        assert "@color(value:)" in error.message
        assert "YELLOW" in error.message

    def test_valid_directive_usage_on_type(self) -> None:
        schema = build_schema(
            """
            directive @color(value: Color) on OBJECT

            enum Color { RED BLUE GREEN }

            type Vehicle @color(value: RED) {
                field: String
            }
            """
        )
        errors = get_directive_enum_value_errors(schema)
        assert errors == []

    def test_invalid_directive_usage_on_type(self) -> None:
        schema = build_schema(
            """
            directive @color(value: Color) on OBJECT

            enum Color { RED BLUE GREEN }

            type Vehicle @color(value: YELLOW) {
                field: String
            }
            """
        )
        errors = get_directive_enum_value_errors(schema)
        assert len(errors) == 1

        error = errors[0]
        assert "Type 'Vehicle'" in error
        assert "@color(value)" in error
        assert "YELLOW" in error

    def test_valid_directive_usage_on_field(self) -> None:
        schema = build_schema(
            """
            directive @color(value: Color) on FIELD_DEFINITION

            enum Color { RED BLUE GREEN }

            type Vehicle {
                field: String @color(value: RED)
            }
            """
        )
        errors = get_directive_enum_value_errors(schema)
        assert errors == []

    def test_invalid_directive_usage_on_field(self) -> None:
        schema = build_schema(
            """
            directive @color(value: Color) on FIELD_DEFINITION

            enum Color { RED BLUE GREEN }

            type Vehicle {
                field: String @color(value: YELLOW)
            }
            """
        )
        errors = get_directive_enum_value_errors(schema)
        assert len(errors) == 1

        error = errors[0]
        assert "Field 'Vehicle.field'" in error
        assert "@color(value)" in error
        assert "YELLOW" in error

    def test_multiple_invalid_enum_defaults(self) -> None:
        schema = build_schema_with_query(
            """
            directive @color(value: Color = WHITE) on OBJECT | FIELD_DEFINITION

            type Query {
                vehicle(color: Color = CYAN): String
            }

            enum Color { RED BLUE GREEN }

            type Vehicle @color(value: MAROON) {
                field: String @color(value: MAGENTA)
            }

            input VehicleInput {
                color: Color = YELLOW
            }
            """
        )
        errors = check_correct_schema(schema)
        assert len(errors) == 5

        directive_def_error = errors[0]
        assert directive_def_error.code == ConstraintCode.SCHEMA_SPEC
        assert "@color(value:)" in directive_def_error.message
        assert "WHITE" in directive_def_error.message

        field_arg_error = errors[1]
        assert field_arg_error.code == ConstraintCode.SCHEMA_SPEC
        assert "Query.vehicle(color:)" in field_arg_error.message
        assert "CYAN" in field_arg_error.message

        input_field_error = errors[2]
        assert input_field_error.code == ConstraintCode.SCHEMA_SPEC
        assert "VehicleInput.color" in input_field_error.message
        assert "YELLOW" in input_field_error.message

        type_directive_error = errors[3]
        assert type_directive_error.code == ConstraintCode.DIRECTIVE_ENUM_VALUE
        assert "Type 'Vehicle'" in type_directive_error.message
        assert "MAROON" in type_directive_error.message

        field_directive_error = errors[4]
        assert field_directive_error.code == ConstraintCode.DIRECTIVE_ENUM_VALUE
        assert "Field 'Vehicle.field'" in field_directive_error.message
        assert "MAGENTA" in field_directive_error.message

    def test_no_default_is_not_error(self) -> None:
        """Verify fields without defaults aren't flagged."""
        schema = build_schema_with_query(
            """
            enum Color { RED BLUE GREEN }

            input VehicleInput {
                color: Color
            }
            """
        )
        errors = check_correct_schema(schema)
        assert errors == []
