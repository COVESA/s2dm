import re
from pathlib import Path
from typing import cast

import pytest
from graphql import GraphQLField, GraphQLObjectType, GraphQLSchema, build_schema, parse

from s2dm.exporters.protobuf import translate_to_protobuf
from s2dm.exporters.utils.extraction import get_root_level_types_from_query
from s2dm.exporters.utils.schema_loader import (
    load_schema_with_naming,
    process_schema,
    prune_schema_using_query_selection,
)


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

        type Query {
            scalarType: ScalarType
        }
        """
        schema = build_schema(schema_str)
        annotated_schema = process_schema(schema, {}, None, None, None, False)
        selection_query = parse("query Selection { scalarType { stringField intField floatField boolField idField } }")
        result = translate_to_protobuf(annotated_schema, selection_query=selection_query)

        assert 'syntax = "proto3";' in result
        assert re.search(
            r"message ScalarType \{.*?"
            r'option \(message_source\) = "ScalarType".*?;.*?'
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

        type Query {
            customScalarType: CustomScalarType
        }
        """
        schema = build_schema(schema_str)
        annotated_schema = process_schema(schema, {}, None, None, None, False)
        selection_query = parse(
            "query Selection { "
            "customScalarType { int8Field uint8Field int16Field uint16Field uint32Field int64Field uint64Field } "
            "}"
        )
        result = translate_to_protobuf(annotated_schema, selection_query=selection_query)

        assert re.search(
            r"message CustomScalarType \{.*?"
            r'option \(message_source\) = "CustomScalarType".*?;.*?'
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

        type Query {
            door: Door
        }
        """
        schema = build_schema(schema_str)
        annotated_schema = process_schema(schema, {}, None, None, None, False)
        selection_query = parse("query Selection { door { lockStatus } }")
        result = translate_to_protobuf(annotated_schema, selection_query=selection_query)

        assert re.search(
            r"message LockStatus \{.*?"
            r'option \(message_source\) = "LockStatus".*?;.*?'
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
            r'option \(message_source\) = "Door".*?;.*?'
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

        type Query {
            vehicle: Vehicle
        }
        """
        schema = build_schema(schema_str)
        annotated_schema = process_schema(schema, {}, None, None, None, False)
        selection_query = parse("query Selection { vehicle { features requiredFeatures model vin } }")
        result = translate_to_protobuf(annotated_schema, selection_query=selection_query)

        assert re.search(
            r"message Vehicle \{.*?"
            r'option \(message_source\) = "Vehicle".*?;.*?'
            r"repeated string features = 1.*?;.*?"
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

        type Query {
            vehicle: Vehicle
        }
        """
        schema = build_schema(schema_str)
        annotated_schema = process_schema(schema, {}, None, None, None, False)
        selection_query = parse("query Selection { vehicle { speed { average current } model } }")
        result = translate_to_protobuf(annotated_schema, selection_query=selection_query)

        assert re.search(
            r"message Speed \{.*?"
            r'option \(message_source\) = "Speed".*?;.*?'
            r"optional float average = 1.*?;.*?"
            r"optional float current = 2.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Speed message with source option and optional fields in order"

        assert re.search(
            r"message Vehicle \{.*?"
            r'option \(message_source\) = "Vehicle".*?;.*?'
            r"optional Speed speed = 1.*?;.*?"
            r"optional string model = 2.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Vehicle message with source option and optional fields in order"

    def test_query_type_renamed_with_selection_query(self) -> None:
        """Test that Query type is renamed to the selection query operation name in standard mode."""
        schema_str = """
        type Speed {
            average: Float
            current: Float
        }

        type Vehicle {
            speed: Speed
            model: String
        }

        type Query {
            vehicle: Vehicle
        }
        """
        schema = build_schema(schema_str)
        selection_query = parse("query Selection { vehicle { speed { average } model } }")
        annotated_schema = process_schema(schema, {}, None, None, None, False)
        result = translate_to_protobuf(annotated_schema, selection_query=selection_query)

        assert re.search(
            r"message Selection \{.*?"
            r'option \(message_source\) = "query: Selection";.*?'
            r"optional Vehicle vehicle = 1.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Query type renamed to Selection with query source option and fields"

        assert "message Query {" not in result, "Original Query type name should not appear"

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

        type Query {
            vehicle: Vehicle
        }
        """
        schema = build_schema(schema_str)
        annotated_schema = process_schema(schema, {}, None, None, None, False)
        selection_query = parse("query Selection { vehicle { speed { average { value timestamp } current } model } }")
        result = translate_to_protobuf(
            annotated_schema, flatten_root_types=["Vehicle"], selection_query=selection_query
        )

        assert re.search(
            r"message Selection \{.*?"
            r'option \(message_source\) = "query: Selection";.*?'
            r'float Vehicle_speed_average_value = 1 \[\(field_source\) = "Average"\];.*?'
            r'int32 Vehicle_speed_average_timestamp = 2 \[\(field_source\) = "Average"\];.*?'
            r'float Vehicle_speed_current = 3 \[\(field_source\) = "Speed"\];.*?'
            r'string Vehicle_model = 4 \[\(field_source\) = "Vehicle"\];.*?'
            r"\}",
            result,
            re.DOTALL,
        ), "Selection with source option and flattened fields with their source options"

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

        type Query {
            vehicle: Vehicle
        }
        """
        schema = build_schema(schema_str)
        annotated_schema = process_schema(schema, {}, None, None, None, False)
        selection_query = parse("query Selection { vehicle { id features { name enabled } } }")
        result = translate_to_protobuf(
            annotated_schema, flatten_root_types=["Vehicle"], selection_query=selection_query
        )

        assert re.search(
            r"message Feature \{.*?"
            r'option \(message_source\) = "Feature";.*?'
            r"string name = 1;.*?"
            r"bool enabled = 2;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Feature message should be included as it's referenced by array"

        assert re.search(
            r"message Car \{.*?" r'option \(message_source\) = "Car";.*?' r"string brand = 1;.*?" r"\}",
            result,
            re.DOTALL,
        ), "Car message should be included as it's part of union"

        assert re.search(
            r"message Truck \{.*?" r'option \(message_source\) = "Truck";.*?' r"int32 capacity = 1;.*?" r"\}",
            result,
            re.DOTALL,
        ), "Truck message should be included as it's part of union"

        assert re.search(
            r"message VehicleType \{.*?"
            r'option \(message_source\) = "VehicleType";.*?'
            r"oneof VehicleType \{.*?"
            r"Car Car = 1;.*?"
            r"Truck Truck = 2;.*?"
            r"\}.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "VehicleType union should be included"

        assert re.search(
            r"message Selection \{.*?"
            r'option \(message_source\) = "query: Selection";.*?'
            r'string Vehicle_id = 1 \[\(field_source\) = "Vehicle"\];.*?'
            r'repeated Feature Vehicle_features = 2 \[\(field_source\) = "Vehicle"\];.*?'
            r"\}",
            result,
            re.DOTALL,
        ), "Selection with source option, flattened fields with source"

        assert "message Vehicle {" not in result

    def test_package_name(self) -> None:
        """Test that package name is included when specified."""
        schema_str = """
        type Vehicle {
            model: String
        }

        type Query {
            vehicle: Vehicle
        }
        """
        schema = build_schema(schema_str)
        annotated_schema = process_schema(schema, {}, None, None, None, False)
        selection_query = parse("query Selection { vehicle { model } }")
        result = translate_to_protobuf(annotated_schema, package_name="package.name", selection_query=selection_query)

        assert "package package.name;" in result

    def test_descriptions_as_comments(self) -> None:
        """Test that type descriptions are converted to comments."""
        schema_str = '''
        """Represents a motor vehicle"""
        type Vehicle {
            """Vehicle identification number"""
            vin: String
        }

        type Query {
            vehicle: Vehicle
        }
        '''
        schema = build_schema(schema_str)
        annotated_schema = process_schema(schema, {}, None, None, None, False)
        selection_query = parse("query Selection { vehicle { vin } }")
        result = translate_to_protobuf(annotated_schema, selection_query=selection_query)

        assert re.search(
            r"// Represents a motor vehicle\s*\n\s*"
            r"message Vehicle \{.*?"
            r'option \(message_source\) = "Vehicle".*?;.*?'
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

        type Query {
            testType: TestType
        }
        """
        schema = build_schema(schema_str)
        annotated_schema = process_schema(schema, {}, None, None, None, False)
        selection_query = parse("query Selection { testType { vehicle } }")
        result = translate_to_protobuf(annotated_schema, selection_query=selection_query)

        assert re.search(
            r"message Car \{.*?" r'option \(message_source\) = "Car".*?;.*?' r"string brand = 1.*?;.*?" r"\}",
            result,
            re.DOTALL,
        ), "Car message with source option and field"

        assert re.search(
            r"message Truck \{.*?" r'option \(message_source\) = "Truck".*?;.*?' r"int32 capacity = 1.*?;.*?" r"\}",
            result,
            re.DOTALL,
        ), "Truck message with source option and field"

        assert re.search(
            r"message Vehicle \{.*?"
            r'option \(message_source\) = "Vehicle".*?;.*?'
            r"oneof Vehicle \{.*?"
            r"Car Car = 1.*?;.*?"
            r"Truck Truck = 2.*?;.*?"
            r"\}.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Vehicle message with source option and oneof containing Car = 1 and Truck = 2"

        assert re.search(
            r"message TestType \{.*?"
            r'option \(message_source\) = "TestType".*?;.*?'
            r"Vehicle vehicle = 1.*?;.*?"
            r"\}",
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

        type Query {
            electricVehicle: ElectricVehicle
        }
        """
        schema = build_schema(schema_str)
        annotated_schema = process_schema(schema, {}, None, None, None, False)
        selection_query = parse("query Selection { electricVehicle { vin batteryCapacity } }")
        result = translate_to_protobuf(annotated_schema, selection_query=selection_query)

        assert re.search(
            r"message Vehicle \{.*?" r'option \(message_source\) = "Vehicle".*?;.*?' r"string vin = 1.*?;.*?" r"\}",
            result,
            re.DOTALL,
        ), "Vehicle interface message with source option and string vin = 1"

        assert re.search(
            r"message ElectricVehicle \{.*?"
            r'option \(message_source\) = "ElectricVehicle".*?;.*?'
            r"string vin = 1.*?;.*?"
            r"int32 batteryCapacity = 2.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "ElectricVehicle message with source option and fields: string vin = 1, int32 batteryCapacity = 2"

    def test_include_instance_tag_types_without_expansion(self, test_schema_path: list[Path]) -> None:
        """Test that types with @instanceTag directive are included when expansion is disabled."""
        graphql_schema = load_schema_with_naming(test_schema_path, None)
        annotated_schema = process_schema(graphql_schema, {}, None, None, None, False)
        selection_query = parse("query Selection { cabin { seats { isOccupied } doors { isLocked } temperature } }")
        result = translate_to_protobuf(annotated_schema, selection_query=selection_query)

        assert re.search(
            r"message DoorPosition \{.*?"
            r'option \(message_source\) = "DoorPosition".*?;.*?'
            r"RowEnum.Enum row = 1.*?;.*?"
            r"SideEnum.Enum side = 2.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "DoorPosition message with source option and fields in order"

        assert re.search(
            r"message SeatPosition \{.*?"
            r'option \(message_source\) = "SeatPosition".*?;.*?'
            r"SeatRowEnum.Enum row = 1.*?;.*?"
            r"SeatPositionEnum.Enum position = 2.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "SeatPosition message with source option and fields in order"

        assert re.search(
            r"message Seat \{.*?"
            r'option \(message_source\) = "Seat".*?;.*?'
            r"bool isOccupied = 1.*?;.*?"
            r"int32 height = 2.*?"
            r"SeatPosition instanceTag = 3.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Seat message with source option and fields in order"

        assert re.search(
            r"message Door \{.*?"
            r'option \(message_source\) = "Door".*?;.*?'
            r"bool isLocked = 1.*?;.*?"
            r"int32 position = 2.*?"
            r"DoorPosition instanceTag = 3.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Door message with source option and fields in order"

        assert re.search(
            r"message Cabin \{.*?"
            r'option \(message_source\) = "Cabin".*?;.*?'
            r"repeated Seat seats = 1.*?;.*?"
            r"repeated Door doors = 2.*?;.*?"
            r"float temperature = 3.*?;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Cabin message with source option and fields in order"

        assert re.search(
            r"message RowEnum \{.*?"
            r'option \(message_source\) = "RowEnum";.*?'
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
            r'option \(message_source\) = "SideEnum";.*?'
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
            r'option \(message_source\) = "SeatRowEnum";.*?'
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
            r'option \(message_source\) = "SeatPositionEnum";.*?'
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

        type Query {
            vehicle: Vehicle
        }
        """
        schema = build_schema(schema_str)
        annotated_schema = process_schema(schema, {}, None, None, None, False)
        selection_query = parse("query Selection { vehicle { message enum service } }")
        result = translate_to_protobuf(annotated_schema, selection_query=selection_query)

        assert re.search(
            r"message Vehicle \{.*?"
            r'option \(message_source\) = "Vehicle".*?;.*?'
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

        type Query {
            vehicle: Vehicle
        }
        """
        schema = build_schema(schema_str)
        annotated_schema = process_schema(schema, {}, None, None, None, False)
        selection_query = parse("query Selection { vehicle { speed engineTemp sensors features wheels } }")
        result = translate_to_protobuf(annotated_schema, selection_query=selection_query)

        assert re.search(
            r"message Vehicle \{.*?"
            r'option \(message_source\) = "Vehicle";.*?'
            r"optional int32 speed = 1 \[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 250\}\];.*?"
            r"optional float engineTemp = 2 \[\(buf\.validate\.field\)\.float = \{gte: -40\.0, lte: 150\.0\}\];.*?"
            r"repeated string sensors = 3 \[\(buf\.validate\.field\)\.repeated = \{unique: true\}\];.*?"
            r"repeated string features = 4 "
            r"\[\(buf\.validate\.field\)\.repeated = \{min_items: 1, max_items: 10\}\];.*?"
            r"repeated int32 wheels = 5 \[\(buf\.validate\.field\)\.repeated = "
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

        type Query {
            vehicle: Vehicle
        }
        """
        schema = build_schema(schema_str)
        annotated_schema = process_schema(schema, {}, None, None, None, False)
        selection_query = parse("query Selection { vehicle { speed tags vin } }")
        result = translate_to_protobuf(annotated_schema, selection_query=selection_query)

        assert re.search(
            r"message Vehicle \{.*?"
            r'option \(message_source\) = "Vehicle";.*?'
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
        annotated_schema = process_schema(graphql_schema, {}, None, None, None, False)
        selection_query = parse("query Selection { cabin { seats { isOccupied } doors { isLocked } temperature } }")
        result = translate_to_protobuf(annotated_schema, selection_query=selection_query, flatten_root_types=["Cabin"])

        assert re.search(
            r"message Selection \{.*?"
            r'option \(message_source\) = "query: Selection";.*?'
            r"repeated Seat Cabin_seats = 1.*?"
            r"repeated Door Cabin_doors = 2.*?"
            r"float Cabin_temperature = 3.*?"
            r"\}",
            result,
            re.DOTALL,
        ), (
            "Selection with source option and fields: repeated Seat Cabin_seats = 1, "
            "repeated Door Cabin_doors = 2, float Cabin_temperature = 3"
        )

    def test_flatten_naming_includes_referenced_types_transitively(self, test_schema_path: list[Path]) -> None:
        """Test that flatten mode includes types referenced by non-flattened types and their dependencies."""
        graphql_schema = load_schema_with_naming(test_schema_path, None)
        annotated_schema = process_schema(graphql_schema, {}, None, None, None, False)
        selection_query = parse("query Selection { vehicle { doors { isLocked } model year features } }")
        result = translate_to_protobuf(
            annotated_schema, selection_query=selection_query, flatten_root_types=["Vehicle"]
        )

        assert re.search(
            r"message Selection \{.*?"
            r'option \(message_source\) = "query: Selection";.*?'
            r"repeated Door Vehicle_doors = 1.*?"
            r"optional string Vehicle_model = 2.*?"
            r"optional int32 Vehicle_year = 3.*?"
            r"repeated string Vehicle_features = 4.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Selection with source option and flattened Vehicle fields including repeated Door reference"

        assert re.search(
            r"message Door \{.*?"
            r'option \(message_source\) = "Door";.*?'
            r"optional bool isLocked = 1;.*?"
            r"optional int32 position = 2 \[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r"optional DoorPosition instanceTag = 3;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Door message should be included with DoorPosition reference"

        assert re.search(
            r"message DoorPosition \{.*?"
            r'option \(message_source\) = "DoorPosition";.*?'
            r"RowEnum.Enum row = 1 \[\(buf\.validate\.field\)\.required = true\];.*?"
            r"SideEnum.Enum side = 2 \[\(buf\.validate\.field\)\.required = true\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "DoorPosition message should be included as it's referenced by Door"

        assert re.search(
            r"message RowEnum \{.*?"
            r'option \(message_source\) = "RowEnum";.*?'
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
            r'option \(message_source\) = "SideEnum";.*?'
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

        type Query {
            transmission: Transmission
        }
        """
        schema = build_schema(schema_str)
        annotated_schema = process_schema(schema, {}, None, None, None, False)
        selection_query = parse("query Selection { transmission { currentGear rpm } }")
        result = translate_to_protobuf(annotated_schema, selection_query=selection_query)

        assert re.search(
            r'syntax = "proto3";.*?'
            r'import "google/protobuf/descriptor\.proto";.*?'
            r'import "buf/validate/validate\.proto";.*?'
            r"extend google\.protobuf\.MessageOptions \{.*?"
            r"string message_source = 50001;.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "File header with syntax, imports, and source option definition"

        assert re.search(
            r"message GearPosition \{.*?"
            r'option \(message_source\) = "GearPosition";.*?'
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
            r'option \(message_source\) = "Transmission";.*?'
            r"GearPosition\.Enum currentGear = 1;.*?"
            r"int32 rpm = 2 \[\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 8000\}\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Transmission message with enum field and validation"

    def test_flatten_naming_multiple_root_types_unnamed_query(self, test_schema_path: list[Path]) -> None:
        """Test that flatten mode without root_type flattens all root-level types with unnamed query."""
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
        query Selection {
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

        flatten_root_types = get_root_level_types_from_query(graphql_schema, selection_query)
        annotated_schema = process_schema(graphql_schema, {}, None, None, None, False)
        result = translate_to_protobuf(
            annotated_schema, selection_query=selection_query, flatten_root_types=flatten_root_types
        )

        assert re.search(
            r"message Selection \{.*?"
            r'option \(message_source\) = "query: Selection";.*?'
            r'repeated Door Vehicle_doors = 1 \[\(field_source\) = "Vehicle"\];.*?'
            r'optional string Vehicle_model = 2 \[\(field_source\) = "Vehicle"\];.*?'
            r'repeated Seat Cabin_seats = 3 \[\(field_source\) = "Cabin"\];.*?'
            r'optional float Cabin_temperature = 4 \[\(field_source\) = "Cabin", '
            r"\(buf\.validate\.field\)\.float = \{gte: -100, lte: 100\}\];.*?"
            r'optional bool Door_isLocked = 5 \[\(field_source\) = "Door"\];.*?'
            r'optional int32 Door_position = 6 \[\(field_source\) = "Door", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'RowEnum\.Enum Door_instanceTag_row = 7 \[\(field_source\) = "DoorPosition", '
            r"\(buf\.validate\.field\)\.required = true\];.*?"
            r'SideEnum\.Enum Door_instanceTag_side = 8 \[\(field_source\) = "DoorPosition", '
            r"\(buf\.validate\.field\)\.required = true\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Message with source option and flattened fields with sources from all root-level types"

        assert "message Seat {" in result, "Seat message should be included as it's referenced by arrays"

        assert "message Vehicle {" not in result, "Vehicle should be completely flattened"
        assert "message Cabin {" not in result, "Cabin should be completely flattened"
        assert "message Door {" not in result, "Door should be completely flattened"

    def test_range_directive_on_repeated_field(self) -> None:
        """Test that @range directive on repeated fields applies to items, not the field itself."""
        schema_str = """
        directive @range(min: Float, max: Float) on FIELD_DEFINITION
        directive @cardinality(min: Int, max: Int) on FIELD_DEFINITION

        type Vehicle {
            temperatures: [Float!]! @range(min: -40.0, max: 120.0) @cardinality(min: 1, max: 10)
            speeds: [Int] @range(min: 0, max: 250)
        }

        type Query {
            vehicle: Vehicle
        }
        """
        schema = build_schema(schema_str)
        selection_query = parse("query Selection { vehicle { temperatures speeds } }")
        annotated_schema = process_schema(schema, {}, None, None, None, False)
        result = translate_to_protobuf(annotated_schema, selection_query=selection_query)

        assert re.search(
            r"message Vehicle \{.*?"
            r'option \(message_source\) = "Vehicle";.*?'
            r"repeated float temperatures = 1 \[\(buf\.validate\.field\)\.required = true, "
            r"\(buf\.validate\.field\)\.repeated = \{min_items: 1, max_items: 10, "
            r"items: \{float: \{gte: -40\.0, lte: 120\.0\}\}\}\];.*?"
            r"repeated int32 speeds = 2 "
            r"\[\(buf\.validate\.field\)\.repeated = \{items: \{int32: \{gte: 0, lte: 250\}\}\}\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Vehicle message with range validation in repeated.items"

    def test_flatten_naming_multiple_root_types_named_query(self, test_schema_path: list[Path]) -> None:
        """Test that flatten mode uses the selection query name for the output message."""
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

        query_str = """
        query Selection {
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

        root_types = get_root_level_types_from_query(graphql_schema, selection_query)
        annotated_schema = process_schema(graphql_schema, {}, None, None, None, False)
        result = translate_to_protobuf(annotated_schema, selection_query=selection_query, flatten_root_types=root_types)

        assert re.search(
            r"message Selection \{.*?"
            r'option \(message_source\) = "query: Selection";.*?'
            r'repeated Door Vehicle_doors = 1 \[\(field_source\) = "Vehicle"\];.*?'
            r'optional string Vehicle_model = 2 \[\(field_source\) = "Vehicle"\];.*?'
            r'repeated Seat Cabin_seats = 3 \[\(field_source\) = "Cabin"\];.*?'
            r'optional float Cabin_temperature = 4 \[\(field_source\) = "Cabin", '
            r"\(buf\.validate\.field\)\.float = \{gte: -100, lte: 100\}\];.*?"
            r'optional bool Door_isLocked = 5 \[\(field_source\) = "Door"\];.*?'
            r'optional int32 Door_position = 6 \[\(field_source\) = "Door", '
            r"\(buf\.validate\.field\)\.int32 = \{gte: 0, lte: 100\}\];.*?"
            r'RowEnum\.Enum Door_instanceTag_row = 7 \[\(field_source\) = "DoorPosition", '
            r"\(buf\.validate\.field\)\.required = true\];.*?"
            r'SideEnum\.Enum Door_instanceTag_side = 8 \[\(field_source\) = "DoorPosition", '
            r"\(buf\.validate\.field\)\.required = true\];.*?"
            r"\}",
            result,
            re.DOTALL,
        ), "Selection message with source option and flattened fields with sources from all root-level types"

        assert "message Seat {" in result, "Seat message should be included as it's referenced by arrays"

        assert "message Vehicle {" not in result, "Vehicle should be completely flattened"
        assert "message Cabin {" not in result, "Cabin should be completely flattened"
        assert "message Door {" not in result, "Door should be completely flattened"

    def test_field_source_extension_only_in_flatten_mode(self) -> None:
        """Test that field_source extension is only declared in flatten mode."""
        schema_str = """
        type Vehicle {
            model: String
            year: Int
        }

        type Query {
            vehicle: Vehicle
        }
        """
        schema = build_schema(schema_str)
        selection_query = parse("query Selection { vehicle { model year } }")

        annotated_schema = process_schema(schema, {}, None, None, None, False)
        result_non_flatten = translate_to_protobuf(annotated_schema, selection_query=selection_query)
        flatten_root_types = get_root_level_types_from_query(schema, selection_query)
        result_flatten = translate_to_protobuf(
            annotated_schema, flatten_root_types=flatten_root_types, selection_query=selection_query
        )

        assert "extend google.protobuf.MessageOptions" in result_non_flatten
        assert "string message_source = 50001" in result_non_flatten
        assert "extend google.protobuf.FieldOptions" not in result_non_flatten
        assert "string field_source = 50002" not in result_non_flatten

        assert "extend google.protobuf.MessageOptions" in result_flatten
        assert "string message_source = 50001" in result_flatten
        assert "extend google.protobuf.FieldOptions" in result_flatten
        assert "string field_source = 50002" in result_flatten
