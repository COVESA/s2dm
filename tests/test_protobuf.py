import re
from pathlib import Path
from typing import cast

import pytest
from graphql import GraphQLField, GraphQLObjectType, GraphQLSchema, build_schema, parse

from s2dm.exporters.protobuf import translate_to_protobuf
from s2dm.exporters.utils.schema import load_schema_with_naming
from s2dm.exporters.utils.schema_loader import prune_schema_using_query_selection


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
            r"optional string stringField = 1.*?;.*?"
            r"optional int32 intField = 2.*?;.*?"
            r"optional float floatField = 3.*?;.*?"
            r"optional bool boolField = 4.*?;.*?"
            r"optional string idField = 5.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "ScalarType message with source option and optional fields in order"

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
            r"optional int32 int8Field = 1.*?;.*?"
            r"optional uint32 uint8Field = 2.*?;.*?"
            r"optional int32 int16Field = 3.*?;.*?"
            r"optional uint32 uint16Field = 4.*?;.*?"
            r"optional uint32 uint32Field = 5.*?;.*?"
            r"optional int64 int64Field = 6.*?;.*?"
            r"optional uint64 uint64Field = 7.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "CustomScalarType message with source option and optional custom scalar fields in order"

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
            r"message Door \{.*?"
            r'option \(source\) = "Door".*?;.*?'
            r"optional LockStatus.Enum lockStatus = 1.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Door message with source option and optional LockStatus.Enum lockStatus = 1 field"

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
            r"optional repeated string features = 1.*?;.*?"
            r"repeated string requiredFeatures = 2 \[\(buf\.validate\.field\)\.required = true\].*?;.*?"
            r"optional string model = 3.*?;.*?"
            r"string vin = 4 \[\(buf\.validate\.field\)\.required = true\].*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Vehicle message with optional for nullable fields and required for non-nullable"

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
            r"optional float average = 1.*?;.*?"
            r"optional float current = 2.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Speed message with source option and optional fields in order"

        assert re.search(
            r"message Vehicle \{.*?"
            r'option \(source\) = "Vehicle".*?;.*?'
            r"optional Speed speed = 1.*?;.*?"
            r"optional string model = 2.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Vehicle message with source option and optional fields in order"

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

    def test_flattened_naming_with_arrays_and_unions(self) -> None:
        """Test that flatten_naming mode keeps arrays and unions as references with their definitions."""
        schema_str = """
        type Feature {
            name: String
            enabled: Boolean
        }

        type Car {
            brand: String
        }

        type Truck {
            capacity: Int
        }

        union VehicleType = Car | Truck

        type Vehicle {
            id: String
            features: [Feature]
            vehicleType: VehicleType
        }
        """
        schema = build_schema(schema_str)
        result = translate_to_protobuf(schema, root_type="Vehicle", flatten_naming=True)

        assert re.search(
            r"message Feature \{.*?"
            r'option \(source\) = "Feature";.*?'
            r"string name = 1;.*?"
            r"bool enabled = 2;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Feature message should be included as it's referenced by array"

        assert re.search(
            r"message Car \{.*?" r'option \(source\) = "Car";.*?' r"string brand = 1;.*?" r"\}",
            result,
            re.DOTALL,
        ), "Car message should be included as it's part of union"

        assert re.search(
            r"message Truck \{.*?" r'option \(source\) = "Truck";.*?' r"int32 capacity = 1;.*?" r"\}",
            result,
            re.DOTALL,
        ), "Truck message should be included as it's part of union"

        assert re.search(
            r"message VehicleType \{.*?"
            r'option \(source\) = "VehicleType";.*?'
            r"oneof VehicleType \{.*?"
            r"Car Car = 1;.*?"
            r"Truck Truck = 2;.*?"
            r"\}.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "VehicleType union should be included"

        assert re.search(
            r"message Message \{.*?"
            r"string Vehicle_id = 1;.*?"
            r"repeated Feature Vehicle_features = 2;.*?"
            r"VehicleType Vehicle_vehicleType = 3;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Message with flattened scalar, array reference, and union reference"

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

        assert re.search(
            r"message RowEnum \{.*?"
            r'option \(source\) = "RowEnum";.*?'
            r"enum Enum \{.*?"
            r"ROWENUM_UNSPECIFIED = 0;.*?"
            r"ROW1 = 1;.*?"
            r"ROW2 = 2;.*?"
            r"\}.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "RowEnum present with all values"

        assert re.search(
            r"message SideEnum \{.*?"
            r'option \(source\) = "SideEnum";.*?'
            r"enum Enum \{.*?"
            r"SIDEENUM_UNSPECIFIED = 0;.*?"
            r"DRIVERSIDE = 1;.*?"
            r"PASSENGERSIDE = 2;.*?"
            r"\}.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "SideEnum present with all values"

        assert re.search(
            r"message SeatRowEnum \{.*?"
            r'option \(source\) = "SeatRowEnum";.*?'
            r"enum Enum \{.*?"
            r"SEATROWENUM_UNSPECIFIED = 0;.*?"
            r"ROW1 = 1;.*?"
            r"ROW2 = 2;.*?"
            r"ROW3 = 3;.*?"
            r"\}.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "SeatRowEnum present with all values"

        assert re.search(
            r"message SeatPositionEnum \{.*?"
            r'option \(source\) = "SeatPositionEnum";.*?'
            r"enum Enum \{.*?"
            r"SEATPOSITIONENUM_UNSPECIFIED = 0;.*?"
            r"LEFT = 1;.*?"
            r"CENTER = 2;.*?"
            r"RIGHT = 3;.*?"
            r"\}.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "SeatPositionEnum present with all values"

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
            r"optional int32 speed = 1 \[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 250\}\];.*?"
            r"optional float engineTemp = 2 \[\(buf\.validate\.field\)\.float = \{gte: -40\.0, lte: 150\.0\}\];.*?"
            r"optional repeated string sensors = 3 \[\(buf\.validate\.field\)\.repeated = \{unique: true\}\];.*?"
            r"optional repeated string features = 4 "
            r"\[\(buf\.validate\.field\)\.repeated = \{min_items: 1, max_items: 10\}\];.*?"
            r"optional repeated int32 wheels = 5 \[\(buf\.validate\.field\)\.repeated = "
            r"\{unique: true, min_items: 2, max_items: 6\}\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Vehicle message with optional and validation rules on all fields"

    def test_required_validation_with_other_rules(self) -> None:
        """Test that required validation works together with other validation rules."""
        schema_str = """
        directive @range(min: Float, max: Float) on FIELD_DEFINITION
        directive @cardinality(min: Int, max: Int) on FIELD_DEFINITION
        directive @noDuplicates on FIELD_DEFINITION

        type Vehicle {
            speed: Int! @range(min: 0, max: 300)
            tags: [String!]! @noDuplicates @cardinality(min: 1, max: 10)
            vin: String!
        }
        """
        schema = build_schema(schema_str)
        result = translate_to_protobuf(schema, root_type="Vehicle")

        assert re.search(
            r"message Vehicle \{.*?"
            r'option \(source\) = "Vehicle";.*?'
            r"int32 speed = 1 \[\(buf\.validate\.field\)\.required = true, "
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 300\}\];.*?"
            r"repeated string tags = 2 \[\(buf\.validate\.field\)\.required = true, "
            r"\(buf\.validate\.field\)\.repeated = \{unique: true, min_items: 1, max_items: 10\}\];.*?"
            r"string vin = 3 \[\(buf\.validate\.field\)\.required = true\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Vehicle message with required combined with other validation rules"

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

    def test_flatten_naming_includes_referenced_types_transitively(self, test_schema_path: list[Path]) -> None:
        """Test that flatten mode includes types referenced by non-flattened types and their dependencies."""
        graphql_schema = load_schema_with_naming(test_schema_path, None)
        result = translate_to_protobuf(
            graphql_schema, root_type="Vehicle", flatten_naming=True, expanded_instances=False
        )

        assert re.search(
            r"message Message \{.*?"
            r"optional repeated Door Vehicle_doors = 1.*?"
            r"optional string Vehicle_model = 2.*?"
            r"optional int32 Vehicle_year = 3.*?"
            r"optional repeated string Vehicle_features = 4.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Message with flattened Vehicle fields including repeated Door reference"

        assert re.search(
            r"message Door \{.*?"
            r'option \(source\) = "Door";.*?'
            r"optional bool isLocked = 1;.*?"
            r"optional int32 position = 2 \[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional DoorPosition instanceTag = 3;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Door message should be included with DoorPosition reference"

        assert re.search(
            r"message DoorPosition \{.*?"
            r'option \(source\) = "DoorPosition";.*?'
            r"RowEnum.Enum row = 1 \[\(buf\.validate\.field\)\.required = true\];.*?"
            r"SideEnum.Enum side = 2 \[\(buf\.validate\.field\)\.required = true\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "DoorPosition message should be included as it's referenced by Door"

        assert re.search(
            r"message RowEnum \{.*?"
            r'option \(source\) = "RowEnum";.*?'
            r"enum Enum \{.*?"
            r"ROWENUM_UNSPECIFIED = 0;.*?"
            r"ROW1 = 1;.*?"
            r"ROW2 = 2;.*?"
            r"\}.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "RowEnum should be included as it's used by DoorPosition"

        assert re.search(
            r"message SideEnum \{.*?"
            r'option \(source\) = "SideEnum";.*?'
            r"enum Enum \{.*?"
            r"SIDEENUM_UNSPECIFIED = 0;.*?"
            r"DRIVERSIDE = 1;.*?"
            r"PASSENGERSIDE = 2;.*?"
            r"\}.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "SideEnum should be included as it's used by DoorPosition"

        assert "SeatPosition" not in result, "SeatPosition should not be included as it's not referenced by Vehicle"
        assert "SeatRowEnum" not in result, "SeatRowEnum should not be included as it's not referenced by Vehicle"
        assert (
            "SeatPositionEnum" not in result
        ), "SeatPositionEnum should not be included as it's not referenced by Vehicle"

    def test_expanded_instances_default(self, test_schema_path: list[Path]) -> None:
        """Test that instance tags are NOT expanded by default (treated as regular types)."""
        graphql_schema = load_schema_with_naming(test_schema_path, None)
        result = translate_to_protobuf(graphql_schema, root_type="Cabin", expanded_instances=False)

        assert re.search(
            r"message Cabin \{.*?"
            r'option \(source\) = "Cabin".*?;.*?'
            r"repeated Seat seats = 1.*?;.*?"
            r"repeated Door doors = 2.*?;.*?"
            r"float temperature = 3.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Cabin message with source option and repeated fields"

        assert re.search(
            r"message Seat \{.*?" r'option \(source\) = "Seat";', result, re.DOTALL
        ), "Seat message with source option"

        assert re.search(
            r"message Door \{.*?" r'option \(source\) = "Door";', result, re.DOTALL
        ), "Door message with source option"

        assert "message Cabin_seats" not in result
        assert "message Cabin_doors" not in result

    def test_expanded_instances(self, test_schema_path: list[Path]) -> None:
        """Test that instance tags are expanded into nested messages when enabled."""
        graphql_schema = load_schema_with_naming(test_schema_path, None)
        result = translate_to_protobuf(graphql_schema, root_type="Cabin", expanded_instances=True)

        assert re.search(
            r"message Cabin \{.*?"
            r'option \(source\) = "Cabin";.*?'
            r"message Cabin_Seat \{.*?"
            r"message Cabin_Seat_ROW1 \{.*?"
            r"Seat LEFT = 1;.*?"
            r"Seat CENTER = 2;.*?"
            r"Seat RIGHT = 3;.*?"
            r"\}.*?"
            r"message Cabin_Seat_ROW2 \{.*?"
            r"Seat LEFT = 1;.*?"
            r"Seat CENTER = 2;.*?"
            r"Seat RIGHT = 3;.*?"
            r"\}.*?"
            r"message Cabin_Seat_ROW3 \{.*?"
            r"Seat LEFT = 1;.*?"
            r"Seat CENTER = 2;.*?"
            r"Seat RIGHT = 3;.*?"
            r"\}.*?"
            r"Cabin_Seat_ROW1 ROW1 = 1;.*?"
            r"Cabin_Seat_ROW2 ROW2 = 2;.*?"
            r"Cabin_Seat_ROW3 ROW3 = 3;.*?"
            r"\}.*?"
            r"message Cabin_Door \{.*?"
            r"message Cabin_Door_ROW1 \{.*?"
            r"Door DRIVERSIDE = 1;.*?"
            r"Door PASSENGERSIDE = 2;.*?"
            r"\}.*?"
            r"message Cabin_Door_ROW2 \{.*?"
            r"Door DRIVERSIDE = 1;.*?"
            r"Door PASSENGERSIDE = 2;.*?"
            r"\}.*?"
            r"Cabin_Door_ROW1 ROW1 = 1;.*?"
            r"Cabin_Door_ROW2 ROW2 = 2;.*?"
            r"\}.*?"
            r"Cabin_Seat Seat = 1;.*?"
            r"Cabin_Door Door = 2;.*?"
            r"optional float temperature = 3 \[\(buf\.validate\.field\)\.float = \{gte: -100, lte: 100\}\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Cabin message with complete nested expanded instance structure"

        assert re.search(
            r"message Door \{.*?"
            r'option \(source\) = "Door";.*?'
            r"optional bool isLocked = 1;.*?"
            r"optional int32 position = 2 \[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Door message with fields"

        assert re.search(
            r"message Seat \{.*?"
            r'option \(source\) = "Seat";.*?'
            r"optional bool isOccupied = 1;.*?"
            r"optional int32 height = 2 \[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Seat message with fields"

        assert "SeatRowEnum" not in result
        assert "SeatPositionEnum" not in result
        assert "RowEnum" not in result
        assert "SideEnum" not in result

    def test_expanded_instances_with_flatten_naming(self, test_schema_path: list[Path]) -> None:
        """Test that expanded instances only expand in flatten mode when flag is set."""
        graphql_schema = load_schema_with_naming(test_schema_path, None)
        result = translate_to_protobuf(graphql_schema, root_type="Cabin", flatten_naming=True, expanded_instances=True)

        assert re.search(
            r"message Message \{.*?"
            r"optional bool Cabin_seats_ROW1_LEFT_isOccupied = 1;.*?"
            r"optional int32 Cabin_seats_ROW1_LEFT_height = 2 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_seats_ROW1_CENTER_isOccupied = 3;.*?"
            r"optional int32 Cabin_seats_ROW1_CENTER_height = 4 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_seats_ROW1_RIGHT_isOccupied = 5;.*?"
            r"optional int32 Cabin_seats_ROW1_RIGHT_height = 6 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_seats_ROW2_LEFT_isOccupied = 7;.*?"
            r"optional int32 Cabin_seats_ROW2_LEFT_height = 8 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_seats_ROW2_CENTER_isOccupied = 9;.*?"
            r"optional int32 Cabin_seats_ROW2_CENTER_height = 10 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_seats_ROW2_RIGHT_isOccupied = 11;.*?"
            r"optional int32 Cabin_seats_ROW2_RIGHT_height = 12 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_seats_ROW3_LEFT_isOccupied = 13;.*?"
            r"optional int32 Cabin_seats_ROW3_LEFT_height = 14 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_seats_ROW3_CENTER_isOccupied = 15;.*?"
            r"optional int32 Cabin_seats_ROW3_CENTER_height = 16 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_seats_ROW3_RIGHT_isOccupied = 17;.*?"
            r"optional int32 Cabin_seats_ROW3_RIGHT_height = 18 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_doors_ROW1_DRIVERSIDE_isLocked = 19;.*?"
            r"optional int32 Cabin_doors_ROW1_DRIVERSIDE_position = 20 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_doors_ROW1_PASSENGERSIDE_isLocked = 21;.*?"
            r"optional int32 Cabin_doors_ROW1_PASSENGERSIDE_position = 22 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_doors_ROW2_DRIVERSIDE_isLocked = 23;.*?"
            r"optional int32 Cabin_doors_ROW2_DRIVERSIDE_position = 24 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_doors_ROW2_PASSENGERSIDE_isLocked = 25;.*?"
            r"optional int32 Cabin_doors_ROW2_PASSENGERSIDE_position = 26 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional float Cabin_temperature = 27 \[\(buf\.validate\.field\)\.float = \{gte: -100, lte: 100\}\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Message with all flattened expanded instance fields"

        assert "SeatRowEnum" not in result
        assert "SeatPositionEnum" not in result
        assert "RowEnum" not in result
        assert "SideEnum" not in result

    def test_expanded_instances_with_naming_config(self, test_schema_path: list[Path]) -> None:
        """Test that naming config is applied to expanded instance field names in non-flatten mode."""
        naming_config = {"field": {"object": "MACROCASE"}}
        graphql_schema = load_schema_with_naming(test_schema_path, naming_config)
        result = translate_to_protobuf(
            graphql_schema, root_type="Cabin", expanded_instances=True, naming_config=naming_config
        )

        assert re.search(
            r"message Cabin \{.*?"
            r'option \(source\) = "Cabin";.*?'
            r"message Cabin_Seat \{.*?"
            r"message Cabin_Seat_ROW1 \{.*?"
            r"Seat LEFT = 1;.*?"
            r"Seat CENTER = 2;.*?"
            r"Seat RIGHT = 3;.*?"
            r"\}.*?"
            r"message Cabin_Seat_ROW2 \{.*?"
            r"Seat LEFT = 1;.*?"
            r"Seat CENTER = 2;.*?"
            r"Seat RIGHT = 3;.*?"
            r"\}.*?"
            r"message Cabin_Seat_ROW3 \{.*?"
            r"Seat LEFT = 1;.*?"
            r"Seat CENTER = 2;.*?"
            r"Seat RIGHT = 3;.*?"
            r"\}.*?"
            r"Cabin_Seat_ROW1 ROW1 = 1;.*?"
            r"Cabin_Seat_ROW2 ROW2 = 2;.*?"
            r"Cabin_Seat_ROW3 ROW3 = 3;.*?"
            r"\}.*?"
            r"message Cabin_Door \{.*?"
            r"message Cabin_Door_ROW1 \{.*?"
            r"Door DRIVERSIDE = 1;.*?"
            r"Door PASSENGERSIDE = 2;.*?"
            r"\}.*?"
            r"message Cabin_Door_ROW2 \{.*?"
            r"Door DRIVERSIDE = 1;.*?"
            r"Door PASSENGERSIDE = 2;.*?"
            r"\}.*?"
            r"Cabin_Door_ROW1 ROW1 = 1;.*?"
            r"Cabin_Door_ROW2 ROW2 = 2;.*?"
            r"\}.*?"
            r"Cabin_Seat SEAT = 1;.*?"
            r"Cabin_Door DOOR = 2;.*?"
            r"optional float TEMPERATURE = 3 \[\(buf\.validate\.field\)\.float = \{gte: -100, lte: 100\}\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Cabin message with complete nested expanded instance structure and MACROCASE field names"

        assert re.search(
            r"message Door \{.*?"
            r'option \(source\) = "Door";.*?'
            r"optional bool IS_LOCKED = 1;.*?"
            r"optional int32 POSITION = 2 \[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Door message with MACROCASE fields"

        assert re.search(
            r"message Seat \{.*?"
            r'option \(source\) = "Seat";.*?'
            r"optional bool IS_OCCUPIED = 1;.*?"
            r"optional int32 HEIGHT = 2 \[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Seat message with MACROCASE fields"

        assert "SeatRowEnum" not in result
        assert "SeatPositionEnum" not in result
        assert "RowEnum" not in result
        assert "SideEnum" not in result

    def test_flatten_mode_expanded_instances_with_naming_config(self, test_schema_path: list[Path]) -> None:
        """Test that naming config is applied to type name in flattened prefix with expanded instances."""
        naming_config = {"field": {"object": "snake_case"}}
        graphql_schema = load_schema_with_naming(test_schema_path, naming_config)
        result = translate_to_protobuf(
            graphql_schema, root_type="Cabin", flatten_naming=True, expanded_instances=True, naming_config=naming_config
        )

        assert re.search(
            r"message Message \{.*?"
            r"optional bool Cabin_seats_ROW1_LEFT_is_occupied = 1;.*?"
            r"optional int32 Cabin_seats_ROW1_LEFT_height = 2 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_seats_ROW1_CENTER_is_occupied = 3;.*?"
            r"optional int32 Cabin_seats_ROW1_CENTER_height = 4 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_seats_ROW1_RIGHT_is_occupied = 5;.*?"
            r"optional int32 Cabin_seats_ROW1_RIGHT_height = 6 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_seats_ROW2_LEFT_is_occupied = 7;.*?"
            r"optional int32 Cabin_seats_ROW2_LEFT_height = 8 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_seats_ROW2_CENTER_is_occupied = 9;.*?"
            r"optional int32 Cabin_seats_ROW2_CENTER_height = 10 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_seats_ROW2_RIGHT_is_occupied = 11;.*?"
            r"optional int32 Cabin_seats_ROW2_RIGHT_height = 12 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_seats_ROW3_LEFT_is_occupied = 13;.*?"
            r"optional int32 Cabin_seats_ROW3_LEFT_height = 14 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_seats_ROW3_CENTER_is_occupied = 15;.*?"
            r"optional int32 Cabin_seats_ROW3_CENTER_height = 16 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_seats_ROW3_RIGHT_is_occupied = 17;.*?"
            r"optional int32 Cabin_seats_ROW3_RIGHT_height = 18 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_doors_ROW1_DRIVERSIDE_is_locked = 19;.*?"
            r"optional int32 Cabin_doors_ROW1_DRIVERSIDE_position = 20 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_doors_ROW1_PASSENGERSIDE_is_locked = 21;.*?"
            r"optional int32 Cabin_doors_ROW1_PASSENGERSIDE_position = 22 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_doors_ROW2_DRIVERSIDE_is_locked = 23;.*?"
            r"optional int32 Cabin_doors_ROW2_DRIVERSIDE_position = 24 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional bool Cabin_doors_ROW2_PASSENGERSIDE_is_locked = 25;.*?"
            r"optional int32 Cabin_doors_ROW2_PASSENGERSIDE_position = 26 "
            r"\[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional float Cabin_temperature = 27 "
            r"\[\(buf\.validate\.field\)\.float = \{gte: -100, lte: 100\}\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Message with all flattened expanded instance fields in snake_case"

        assert "SeatRowEnum" not in result
        assert "SeatPositionEnum" not in result
        assert "RowEnum" not in result
        assert "SideEnum" not in result

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

    def test_flatten_naming_multiple_root_types(self, test_schema_path: list[Path]) -> None:
        """Test that flatten mode without root_type flattens all root-level types."""
        graphql_schema = load_schema_with_naming(test_schema_path, None)

        vehicle_type = cast(GraphQLObjectType, graphql_schema.type_map["Vehicle"])
        cabin_type = cast(GraphQLObjectType, graphql_schema.type_map["Cabin"])
        door_type = cast(GraphQLObjectType, graphql_schema.type_map["Door"])

        query_type = GraphQLObjectType(
            "Query",
            {
                "vehicle": GraphQLField(vehicle_type),
                "cabin": GraphQLField(cabin_type),
                "door": GraphQLField(door_type),
            },
        )

        types = [type_def for type_def in graphql_schema.type_map.values() if type_def.name != "Query"]
        graphql_schema = GraphQLSchema(query=query_type, types=types, directives=graphql_schema.directives)

        # Selection query that selects vehicle, cabin, and door at the top level
        query_str = """
        query {
            vehicle {
                doors { isLocked }
                model
            }
            cabin {
                seats { isOccupied }
                temperature
            }
            door {
                isLocked
                position
                instanceTag { row side }
            }
        }
        """
        selection_query = parse(query_str)
        graphql_schema = prune_schema_using_query_selection(graphql_schema, selection_query)

        result = translate_to_protobuf(
            graphql_schema, flatten_naming=True, expanded_instances=False, selection_query=selection_query
        )

        assert re.search(
            r"message Message \{.*?"
            r"optional repeated Door Vehicle_doors = 1;.*?"
            r"optional string Vehicle_model = 2;.*?"
            r"optional repeated Seat Cabin_seats = 3;.*?"
            r"optional float Cabin_temperature = 4 \[\(buf\.validate\.field\)\.float = \{gte: -100, lte: 100\}\];.*?"
            r"optional bool Door_isLocked = 5;.*?"
            r"optional int32 Door_position = 6 \[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"RowEnum\.Enum Door_instanceTag_row = 7 \[\(buf\.validate\.field\)\.required = true\];.*?"
            r"SideEnum\.Enum Door_instanceTag_side = 8 \[\(buf\.validate\.field\)\.required = true\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Message with flattened fields from all root-level types (Vehicle, Cabin, Door)"

        assert "message Seat {" in result, "Seat message should be included as it's referenced by arrays"

        assert "message Vehicle {" not in result, "Vehicle should be completely flattened"
        assert "message Cabin {" not in result, "Cabin should be completely flattened"
        assert "message Door {" not in result, "Door should be completely flattened"
