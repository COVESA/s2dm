from graphql import build_schema

from s2dm.exporters.utils.schema_loader import check_enum_defaults


class TestEnumDefaultValidation:
    def test_valid_input_field_default(self) -> None:
        schema = build_schema(
            """
            enum Color { RED BLUE GREEN }

            input VehicleInput {
                color: Color = RED
            }
            """
        )
        errors = check_enum_defaults(schema)
        assert errors == []

    def test_invalid_input_field_default(self) -> None:
        schema = build_schema(
            """
            enum Color { RED BLUE GREEN }

            input VehicleInput {
                color: Color = YELLOW
            }
            """
        )
        errors = check_enum_defaults(schema)
        assert len(errors) == 1

        error = errors[0]
        assert "VehicleInput.color" in error
        assert "YELLOW" in error
        assert "['RED', 'BLUE', 'GREEN']" in error

    def test_invalid_enum_defaults_on_multiple_inputs(self) -> None:
        schema = build_schema(
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
        errors = check_enum_defaults(schema)
        assert len(errors) == 3

        vehicle_color_error = errors[0]
        assert "VehicleInput.color" in vehicle_color_error
        assert "YELLOW" in vehicle_color_error

        vehicle_engine_error = errors[1]
        assert "VehicleInput.engineType" in vehicle_engine_error
        assert "DIESEL" in vehicle_engine_error

        bike_color_error = errors[2]
        assert "BikeInput.color" in bike_color_error
        assert "PURPLE" in bike_color_error

    def test_valid_field_argument_default(self) -> None:
        schema = build_schema(
            """
            type Query {
                vehicle(color: Color = RED): String
            }

            enum Color { RED BLUE GREEN }
            """
        )
        errors = check_enum_defaults(schema)
        assert errors == []

    def test_invalid_field_argument_default(self) -> None:
        schema = build_schema(
            """
            type Query {
                vehicle(color: Color = YELLOW): String
            }

            enum Color { RED BLUE GREEN }
            """
        )
        errors = check_enum_defaults(schema)
        assert len(errors) == 1

        error = errors[0]
        assert "Query.vehicle(color)" in error
        assert "YELLOW" in error

    def test_valid_directive_definition_default(self) -> None:
        schema = build_schema(
            """
            directive @color(value: Color = RED) on OBJECT

            enum Color { RED BLUE GREEN }
            """
        )
        errors = check_enum_defaults(schema)
        assert errors == []

    def test_invalid_directive_definition_default(self) -> None:
        schema = build_schema(
            """
            directive @color(value: Color = YELLOW) on OBJECT

            enum Color { RED BLUE GREEN }
            """
        )
        errors = check_enum_defaults(schema)
        assert len(errors) == 1

        error = errors[0]
        assert "@color(value)" in error
        assert "YELLOW" in error

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
        errors = check_enum_defaults(schema)
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
        errors = check_enum_defaults(schema)
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
        errors = check_enum_defaults(schema)
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
        errors = check_enum_defaults(schema)
        assert len(errors) == 1

        error = errors[0]
        assert "Field 'Vehicle.field'" in error
        assert "@color(value)" in error
        assert "YELLOW" in error

    def test_multiple_invalid_enum_defaults(self) -> None:
        schema = build_schema(
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
        errors = check_enum_defaults(schema)
        assert len(errors) == 5

        field_arg_error = errors[0]
        assert "Query.vehicle(color)" in field_arg_error
        assert "CYAN" in field_arg_error

        type_directive_error = errors[1]
        assert "Type 'Vehicle'" in type_directive_error
        assert "MAROON" in type_directive_error

        field_directive_error = errors[2]
        assert "Field 'Vehicle.field'" in field_directive_error
        assert "MAGENTA" in field_directive_error

        input_field_error = errors[3]
        assert "VehicleInput.color" in input_field_error
        assert "YELLOW" in input_field_error

        directive_def_error = errors[4]
        assert "@color(value)" in directive_def_error
        assert "WHITE" in directive_def_error

    def test_no_default_is_not_error(self) -> None:
        """Verify fields without defaults aren't flagged (both cases result in Undefined)."""
        schema = build_schema(
            """
            enum Color { RED BLUE GREEN }

            input VehicleInput {
                color: Color
            }
            """
        )
        errors = check_enum_defaults(schema)
        assert errors == []
