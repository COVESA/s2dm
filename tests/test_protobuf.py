import re
from pathlib import Path

import pytest
from graphql import build_schema

from s2dm.exporters.protobuf import translate_to_protobuf
from s2dm.exporters.utils.schema import load_schema_with_naming


class TestProtobufExporter:
    """Test suite for the Protobuf exporter."""

    @pytest.fixture
    def test_schema_path(self) -> list[Path]:
        """Fixture providing path to test schema."""
        return [Path("tests/test_expanded_instances/test_schema.graphql")]

    def test_basic_scalar_types(self) -> None:
        """Test that basic scalar types are correctly mapped to Protobuf types."""
        schema_str = """
        type ScalarType {
            stringField: String
            intField: Int
            floatField: Float
            boolField: Boolean
            idField: ID
        }
        """
        schema = build_schema(schema_str)
        result = translate_to_protobuf(schema, root_type="ScalarType")

        assert 'syntax = "proto3";' in result
        assert re.search(
            r"message ScalarType \{.*?"
            r'option \(source\) = "ScalarType".*?;.*?'
            r"string stringField = 1.*?;.*?"
            r"int32 intField = 2.*?;.*?"
            r"float floatField = 3.*?;.*?"
            r"bool boolField = 4.*?;.*?"
            r"string idField = 5.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "ScalarType message with source option and fields in order"

        assert "message Message {" not in result

    def test_custom_scalars(self) -> None:
        """Test that custom scalar types are mapped correctly."""
        schema_str = """
        scalar Int8
        scalar UInt8
        scalar Int16
        scalar UInt16
        scalar UInt32
        scalar Int64
        scalar UInt64

        type CustomScalarType {
            int8Field: Int8
            uint8Field: UInt8
            int16Field: Int16
            uint16Field: UInt16
            uint32Field: UInt32
            int64Field: Int64
            uint64Field: UInt64
        }
        """
        schema = build_schema(schema_str)
        result = translate_to_protobuf(schema, root_type="CustomScalarType")

        assert re.search(
            r"message CustomScalarType \{.*?"
            r'option \(source\) = "CustomScalarType".*?;.*?'
            r"int32 int8Field = 1.*?;.*?"
            r"uint32 uint8Field = 2.*?;.*?"
            r"int32 int16Field = 3.*?;.*?"
            r"uint32 uint16Field = 4.*?;.*?"
            r"uint32 uint32Field = 5.*?;.*?"
            r"int64 int64Field = 6.*?;.*?"
            r"uint64 uint64Field = 7.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "CustomScalarType message with source option and custom scalar fields in order"

    def test_enum_type_with_unspecified(self) -> None:
        """Test that enums include UNSPECIFIED default value."""
        schema_str = """
        enum LockStatus {
            LOCKED
            UNLOCKED
            PARTIAL
        }

        type Door {
            lockStatus: LockStatus
        }
        """
        schema = build_schema(schema_str)
        result = translate_to_protobuf(schema, root_type="Door")

        assert re.search(
            r"message LockStatus \{.*?"
            r'option \(source\) = "LockStatus".*?;.*?'
            r"enum Enum \{.*?"
            r"LOCKSTATUS_UNSPECIFIED = 0.*?;.*?"
            r"LOCKED = 1.*?;.*?"
            r"UNLOCKED = 2.*?;.*?"
            r"PARTIAL = 3.*?;.*?"
            r"\}.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "LockStatus enum wrapped in message with source option and values in order"

        assert re.search(
            r"message Door \{.*?" r'option \(source\) = "Door".*?;.*?' r"LockStatus.Enum lockStatus = 1.*?;.*?" r"\}",
            result,
            re.DOTALL,
        ), "Door message with source option and LockStatus.Enum lockStatus = 1 field"

    def test_list_to_repeated(self) -> None:
        """Test that GraphQL lists are converted to repeated fields and non-null handling."""
        schema_str = """
        type Vehicle {
            features: [String]
            requiredFeatures: [String!]!
            model: String
            vin: String!
        }
        """
        schema = build_schema(schema_str)
        result = translate_to_protobuf(schema, root_type="Vehicle")

        assert re.search(
            r"message Vehicle \{.*?"
            r'option \(source\) = "Vehicle".*?;.*?'
            r"repeated string features = 1.*?;.*?"
            r"repeated string requiredFeatures = 2.*?;.*?"
            r"string model = 3.*?;.*?"
            r"string vin = 4.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Vehicle message with source option and fields in order"

    def test_nested_objects_standard_mode(self) -> None:
        """Test nested object types in standard mode."""
        schema_str = """
        type Speed {
            average: Float
            current: Float
        }

        type Vehicle {
            speed: Speed
            model: String
        }
        """
        schema = build_schema(schema_str)
        result = translate_to_protobuf(schema, root_type="Vehicle")

        assert re.search(
            r"message Speed \{.*?"
            r'option \(source\) = "Speed".*?;.*?'
            r"float average = 1.*?;.*?"
            r"float current = 2.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Speed message with source option and fields in order"

        assert re.search(
            r"message Vehicle \{.*?"
            r'option \(source\) = "Vehicle".*?;.*?'
            r"Speed speed = 1.*?;.*?"
            r"string model = 2.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Vehicle message with source option and fields in order"

    def test_flattened_naming_mode(self) -> None:
        """Test that flatten_naming mode creates flattened field names."""
        schema_str = """
        type Average {
            value: Float
            timestamp: Int
        }

        type Speed {
            average: Average
            current: Float
        }

        type Vehicle {
            speed: Speed
            model: String
        }
        """
        schema = build_schema(schema_str)
        result = translate_to_protobuf(schema, root_type="Vehicle", flatten_naming=True)

        assert re.search(
            r"message Message \{.*?"
            r"float Vehicle_speed_average_value = 1.*?;.*?"
            r"int32 Vehicle_speed_average_timestamp = 2.*?;.*?"
            r"float Vehicle_speed_current = 3.*?;.*?"
            r"string Vehicle_model = 4.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Message with flattened fields in order"

        assert "message Speed {" not in result
        assert "message Average {" not in result
        assert "message Vehicle {" not in result

    def test_package_name(self) -> None:
        """Test that package name is included when specified."""
        schema_str = """
        type Vehicle {
            model: String
        }
        """
        schema = build_schema(schema_str)
        result = translate_to_protobuf(schema, root_type="Vehicle", package_name="package.name")

        assert "package package.name;" in result

    def test_descriptions_as_comments(self) -> None:
        """Test that type descriptions are converted to comments."""
        schema_str = '''
        """Represents a motor vehicle"""
        type Vehicle {
            """Vehicle identification number"""
            vin: String
        }
        '''
        schema = build_schema(schema_str)
        result = translate_to_protobuf(schema, root_type="Vehicle")

        assert re.search(
            r"// Represents a motor vehicle\s*\n\s*"
            r"message Vehicle \{.*?"
            r'option \(source\) = "Vehicle".*?;.*?'
            r"string vin = 1;  // Vehicle identification number.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Vehicle message with description comment, source option, and field with inline comment"

    def test_union_type_to_oneof(self) -> None:
        """Test that union types are converted to oneof."""
        schema_str = """
        type Car {
            brand: String
        }

        type Truck {
            capacity: Int
        }

        union Vehicle = Car | Truck

        type TestType {
            vehicle: Vehicle
        }
        """
        schema = build_schema(schema_str)
        result = translate_to_protobuf(schema, root_type="TestType")

        assert re.search(
            r"message Car \{.*?" r'option \(source\) = "Car".*?;.*?' r"string brand = 1.*?;.*?" r"\}", result, re.DOTALL
        ), "Car message with source option and field"

        assert re.search(
            r"message Truck \{.*?" r'option \(source\) = "Truck".*?;.*?' r"int32 capacity = 1.*?;.*?" r"\}",
            result,
            re.DOTALL,
        ), "Truck message with source option and field"

        assert re.search(
            r"message Vehicle \{.*?"
            r'option \(source\) = "Vehicle".*?;.*?'
            r"oneof Vehicle \{.*?"
            r"Car Car = 1.*?;.*?"
            r"Truck Truck = 2.*?;.*?"
            r"\}.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Vehicle message with source option and oneof containing Car = 1 and Truck = 2"

        assert re.search(
            r"message TestType \{.*?" r'option \(source\) = "TestType".*?;.*?' r"Vehicle vehicle = 1.*?;.*?" r"\}",
            result,
            re.DOTALL,
        ), "TestType message with source option and Vehicle field"

    def test_interface_type(self) -> None:
        """Test that interface types are converted to messages."""
        schema_str = """
        interface Vehicle {
            vin: String!
        }

        type ElectricVehicle implements Vehicle {
            vin: String!
            batteryCapacity: Int
        }
        """
        schema = build_schema(schema_str)
        result = translate_to_protobuf(schema, root_type="ElectricVehicle")

        assert re.search(
            r"message Vehicle \{.*?" r'option \(source\) = "Vehicle".*?;.*?' r"string vin = 1.*?;.*?" r"\}",
            result,
            re.DOTALL,
        ), "Vehicle interface message with source option and string vin = 1"

        assert re.search(
            r"message ElectricVehicle \{.*?"
            r'option \(source\) = "ElectricVehicle".*?;.*?'
            r"string vin = 1.*?;.*?"
            r"int32 batteryCapacity = 2.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "ElectricVehicle message with source option and fields: string vin = 1, int32 batteryCapacity = 2"

    def test_include_instance_tag_types_without_expansion(self, test_schema_path: list[Path]) -> None:
        """Test that types with @instanceTag directive are included when expansion is disabled."""
        graphql_schema = load_schema_with_naming(test_schema_path, None)
        result = translate_to_protobuf(graphql_schema, root_type="Cabin", expanded_instances=False)

        assert re.search(
            r"message DoorPosition \{.*?"
            r'option \(source\) = "DoorPosition".*?;.*?'
            r"RowEnum.Enum row = 1.*?;.*?"
            r"SideEnum.Enum side = 2.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "DoorPosition message with source option and fields in order"

        assert re.search(
            r"message SeatPosition \{.*?"
            r'option \(source\) = "SeatPosition".*?;.*?'
            r"SeatRowEnum.Enum row = 1.*?;.*?"
            r"SeatPositionEnum.Enum position = 2.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "SeatPosition message with source option and fields in order"

        assert re.search(
            r"message Seat \{.*?"
            r'option \(source\) = "Seat".*?;.*?'
            r"bool isOccupied = 1.*?;.*?"
            r"int32 height = 2.*?"
            r"SeatPosition instanceTag = 3.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Seat message with source option and fields in order"

        assert re.search(
            r"message Door \{.*?"
            r'option \(source\) = "Door".*?;.*?'
            r"bool isLocked = 1.*?;.*?"
            r"int32 position = 2.*?"
            r"DoorPosition instanceTag = 3.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Door message with source option and fields in order"

        assert re.search(
            r"message Cabin \{.*?"
            r'option \(source\) = "Cabin".*?;.*?'
            r"repeated Seat seats = 1.*?;.*?"
            r"repeated Door doors = 2.*?;.*?"
            r"float temperature = 3.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Cabin message with source option and fields in order"

    def test_reserved_keyword_escaping(self) -> None:
        """Test that Protobuf reserved keywords are escaped."""
        schema_str = """
        type Vehicle {
            message: String
            enum: Int
            service: Boolean
        }
        """
        schema = build_schema(schema_str)
        result = translate_to_protobuf(schema, root_type="Vehicle")

        assert re.search(
            r"message Vehicle \{.*?"
            r'option \(source\) = "Vehicle".*?;.*?'
            r"string _message_ = 1.*?;.*?"
            r"int32 _enum_ = 2.*?;.*?"
            r"bool _service_ = 3.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Vehicle message with source option and escaped fields in order"

    def test_validation_rules(self) -> None:
        """Test that validation directives are converted to protovalidate constraints."""
        schema_str = """
        directive @range(min: Float, max: Float) on FIELD_DEFINITION
        directive @cardinality(min: Int, max: Int) on FIELD_DEFINITION
        directive @noDuplicates on FIELD_DEFINITION

        type Vehicle {
            speed: Int @range(min: 0, max: 250)
            engineTemp: Float @range(min: -40.0, max: 150.0)
            sensors: [String] @noDuplicates
            features: [String] @cardinality(min: 1, max: 10)
            wheels: [Int] @noDuplicates @cardinality(min: 2, max: 6)
        }
        """
        schema = build_schema(schema_str)
        result = translate_to_protobuf(schema, root_type="Vehicle")

        assert re.search(
            r"message Vehicle \{.*?"
            r'option \(source\) = "Vehicle";.*?'
            r"int32 speed = 1 \[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 250\}\];.*?"
            r"float engineTemp = 2 \[\(buf\.validate\.field\)\.float = \{gte: -40\.0, lte: 150\.0\}\];.*?"
            r"repeated string sensors = 3 \[\(buf\.validate\.field\)\.repeated = \{unique: true\}\];.*?"
            r"repeated string features = 4 \[\(buf\.validate\.field\)\.repeated = \{min_items: 1, max_items: 10\}\];.*?"
            r"repeated int32 wheels = 5 \[\(buf\.validate\.field\)\.repeated = "
            r"\{unique: true, min_items: 2, max_items: 6\}\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Vehicle message with validation rules on all fields"

    def test_flatten_naming_without_expansion(self, test_schema_path: list[Path]) -> None:
        """Test that flatten mode WITHOUT -e flag keeps arrays as repeated."""
        graphql_schema = load_schema_with_naming(test_schema_path, None)
        result = translate_to_protobuf(graphql_schema, root_type="Cabin", flatten_naming=True, expanded_instances=False)

        assert re.search(
            r"message Message \{.*?"
            r"repeated Seat Cabin_seats = 1.*?"
            r"repeated Door Cabin_doors = 2.*?"
            r"float Cabin_temperature = 3.*?"
            r"\}",
            result,
            re.DOTALL,
        ), (
            "Message with fields: repeated Seat Cabin_seats = 1, "
            "repeated Door Cabin_doors = 2, float Cabin_temperature = 3"
        )

    def test_complete_proto_file(self) -> None:
        """Test that the complete Protobuf output includes syntax, imports, and source option definition."""
        schema_str = """
        directive @range(min: Float, max: Float) on FIELD_DEFINITION

        enum GearPosition {
            PARK
            DRIVE
            REVERSE
        }

        type Transmission {
            currentGear: GearPosition
            rpm: Int @range(min: 0, max: 8000)
        }
        """
        schema = build_schema(schema_str)
        result = translate_to_protobuf(schema, root_type="Transmission")

        assert re.search(
            r'syntax = "proto3";.*?'
            r'import "google/protobuf/descriptor\.proto";.*?'
            r'import "buf/validate/validate\.proto";.*?'
            r"extend google\.protobuf\.MessageOptions \{.*?"
            r"string source = 50001;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "File header with syntax, imports, and source option definition"

        assert re.search(
            r"message GearPosition \{.*?"
            r'option \(source\) = "GearPosition";.*?'
            r"enum Enum \{.*?"
            r"GEARPOSITION_UNSPECIFIED = 0;.*?"
            r"PARK = 1;.*?"
            r"DRIVE = 2;.*?"
            r"REVERSE = 3;.*?"
            r"\}.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "GearPosition enum with source option"

        assert re.search(
            r"message Transmission \{.*?"
            r'option \(source\) = "Transmission";.*?'
            r"GearPosition\.Enum currentGear = 1;.*?"
            r"int32 rpm = 2 \[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 8000\}\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Transmission message with enum field and validation"
