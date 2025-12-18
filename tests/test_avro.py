"""Tests for the Avro exporter."""

import json

from avro.schema import parse as parse_avro_schema
from graphql import build_schema, parse

from s2dm.exporters.avro.schema import transform
from s2dm.exporters.utils.schema_loader import process_schema


class TestBasicTransformation:
    def test_basic_scalar_types(self) -> None:
        """Test that basic scalar types are correctly mapped to Avro types and field descriptions are preserved."""
        schema_str = """
        type ScalarType {
            "A string field"
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
        graphql_schema = build_schema(schema_str)
        selection_query = parse("query Selection { scalarType { stringField intField floatField boolField idField } }")
        annotated_schema = process_schema(
            schema=graphql_schema,
            source_map={},
            query_document=selection_query,
        )

        result = transform(annotated_schema, "com.example", selection_query)
        result_dict = json.loads(result)

        assert result_dict["type"] == "record"
        assert result_dict["name"] == "Selection"
        assert result_dict["namespace"] == "com.example"
        assert len(result_dict["fields"]) == 1

        scalar_type_field = result_dict["fields"][0]
        assert scalar_type_field["name"] == "scalarType"
        assert isinstance(scalar_type_field["type"], list)
        assert scalar_type_field["type"][0] == "null"

        scalar_type_record = scalar_type_field["type"][1]
        assert scalar_type_record["type"] == "record"
        assert scalar_type_record["name"] == "ScalarType"
        assert scalar_type_record["namespace"] == "com.example"
        assert len(scalar_type_record["fields"]) == 5

        string_field = scalar_type_record["fields"][0]
        assert string_field["name"] == "stringField"
        assert string_field["doc"] == "A string field"
        assert string_field["type"] == ["null", "string"]

        int_field = scalar_type_record["fields"][1]
        assert int_field["name"] == "intField"
        assert int_field["type"] == ["null", "int"]

        float_field = scalar_type_record["fields"][2]
        assert float_field["name"] == "floatField"
        assert float_field["type"] == ["null", "double"]

        bool_field = scalar_type_record["fields"][3]
        assert bool_field["name"] == "boolField"
        assert bool_field["type"] == ["null", "boolean"]

        id_field = scalar_type_record["fields"][4]
        assert id_field["name"] == "idField"
        assert id_field["type"] == ["null", "string"]

        parse_avro_schema(result)

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
        graphql_schema = build_schema(schema_str)
        selection_query = parse(
            "query Selection { "
            "customScalarType { int8Field uint8Field int16Field uint16Field uint32Field int64Field uint64Field } "
            "}"
        )
        annotated_schema = process_schema(
            schema=graphql_schema,
            source_map={},
            query_document=selection_query,
        )

        result = transform(annotated_schema, "com.example", selection_query)
        result_dict = json.loads(result)

        assert result_dict["type"] == "record"
        assert result_dict["name"] == "Selection"
        assert result_dict["namespace"] == "com.example"
        assert len(result_dict["fields"]) == 1

        custom_scalar_field = result_dict["fields"][0]
        assert custom_scalar_field["name"] == "customScalarType"
        assert isinstance(custom_scalar_field["type"], list)
        assert custom_scalar_field["type"][0] == "null"

        custom_scalar_record = custom_scalar_field["type"][1]
        assert custom_scalar_record["type"] == "record"
        assert custom_scalar_record["name"] == "CustomScalarType"
        assert custom_scalar_record["namespace"] == "com.example"
        assert len(custom_scalar_record["fields"]) == 7

        int8_field = custom_scalar_record["fields"][0]
        assert int8_field["name"] == "int8Field"
        assert int8_field["type"] == ["null", "int"]

        uint8_field = custom_scalar_record["fields"][1]
        assert uint8_field["name"] == "uint8Field"
        assert uint8_field["type"] == ["null", "int"]

        int16_field = custom_scalar_record["fields"][2]
        assert int16_field["name"] == "int16Field"
        assert int16_field["type"] == ["null", "int"]

        uint16_field = custom_scalar_record["fields"][3]
        assert uint16_field["name"] == "uint16Field"
        assert uint16_field["type"] == ["null", "int"]

        uint32_field = custom_scalar_record["fields"][4]
        assert uint32_field["name"] == "uint32Field"
        assert uint32_field["type"] == ["null", "long"]

        int64_field = custom_scalar_record["fields"][5]
        assert int64_field["name"] == "int64Field"
        assert int64_field["type"] == ["null", "long"]

        uint64_field = custom_scalar_record["fields"][6]
        assert uint64_field["name"] == "uint64Field"
        assert uint64_field["type"] == ["null", "long"]

        parse_avro_schema(result)

    def test_nested_objects(self) -> None:
        """Test nested object types and type descriptions."""
        schema_str = """
        type Speed {
            average: Float
            current: Float
        }

        "A vehicle entity"
        type Vehicle {
            speed: Speed
            model: String
        }

        type Query {
            vehicle: Vehicle
        }
        """
        graphql_schema = build_schema(schema_str)
        selection_query = parse("query Selection { vehicle { speed { average current } model } }")
        annotated_schema = process_schema(
            schema=graphql_schema,
            source_map={},
            query_document=selection_query,
        )

        result = transform(annotated_schema, "com.example", selection_query)
        result_dict = json.loads(result)

        assert result_dict["type"] == "record"
        assert result_dict["name"] == "Selection"
        assert len(result_dict["fields"]) == 1

        vehicle_field = result_dict["fields"][0]
        assert vehicle_field["name"] == "vehicle"
        assert vehicle_field["type"][0] == "null"

        vehicle_record = vehicle_field["type"][1]
        assert vehicle_record["type"] == "record"
        assert vehicle_record["name"] == "Vehicle"
        assert vehicle_record["doc"] == "A vehicle entity"
        assert len(vehicle_record["fields"]) == 2

        speed_field = vehicle_record["fields"][0]
        assert speed_field["name"] == "speed"
        assert speed_field["type"][0] == "null"

        speed_record = speed_field["type"][1]
        assert speed_record["type"] == "record"
        assert speed_record["name"] == "Speed"
        assert len(speed_record["fields"]) == 2
        assert speed_record["fields"][0]["name"] == "average"
        assert speed_record["fields"][0]["type"] == ["null", "double"]
        assert speed_record["fields"][1]["name"] == "current"
        assert speed_record["fields"][1]["type"] == ["null", "double"]

        model_field = vehicle_record["fields"][1]
        assert model_field["name"] == "model"
        assert model_field["type"] == ["null", "string"]

        parse_avro_schema(result)


class TestEnumTypes:
    def test_enum_transformation_and_reuse(self) -> None:
        """Test enum transformation and that reused enums are referenced, not redefined."""
        schema_str = """
        enum LockStatus {
            LOCKED
            UNLOCKED
        }

        enum Status {
            ACTIVE
            INACTIVE
        }

        type Item {
            lockStatus: LockStatus
            primaryStatus: Status
            secondaryStatus: Status
        }

        type Query {
            item: Item
        }
        """
        graphql_schema = build_schema(schema_str)
        selection_query = parse("query Selection { item { lockStatus primaryStatus secondaryStatus } }")
        annotated_schema = process_schema(
            schema=graphql_schema,
            source_map={},
            query_document=selection_query,
        )

        result = transform(annotated_schema, "com.example", selection_query)
        result_dict = json.loads(result)

        assert result_dict["name"] == "Selection"
        assert len(result_dict["fields"]) == 1

        item_field = result_dict["fields"][0]
        item_record = item_field["type"][1]
        assert item_record["name"] == "Item"
        assert len(item_record["fields"]) == 3

        lock_status_field = item_record["fields"][0]
        assert lock_status_field["name"] == "lockStatus"
        assert lock_status_field["type"][0] == "null"
        lock_status_enum = lock_status_field["type"][1]
        assert lock_status_enum["type"] == "enum"
        assert lock_status_enum["name"] == "LockStatus"
        assert lock_status_enum["namespace"] == "com.example"
        assert lock_status_enum["symbols"] == ["LOCKED", "UNLOCKED"]

        primary_status_field = item_record["fields"][1]
        assert primary_status_field["name"] == "primaryStatus"
        assert primary_status_field["type"][0] == "null"
        primary_status_enum = primary_status_field["type"][1]
        assert primary_status_enum["type"] == "enum"
        assert primary_status_enum["name"] == "Status"
        assert primary_status_enum["symbols"] == ["ACTIVE", "INACTIVE"]

        secondary_status_field = item_record["fields"][2]
        assert secondary_status_field["name"] == "secondaryStatus"
        assert secondary_status_field["type"][0] == "null"
        assert secondary_status_field["type"][1] == "com.example.Status"

        parse_avro_schema(result)


class TestTypeReuse:
    def test_type_reuse_and_recursion(self) -> None:
        """Test that reused types are referenced correctly, including recursive/self-referencing types."""
        schema_str = """
        type Address {
            street: String
            city: String
        }

        type Component {
            id: ID!
            name: String!
            parent: Component
        }

        type Person {
            name: String!
            address: Address
            billingAddress: Address
            manager: Component
        }

        type Query {
            person: Person
        }
        """
        graphql_schema = build_schema(schema_str)
        selection_query = parse(
            "query Selection { person { name address { street city } billingAddress { street city } "
            "manager { id name parent { id name } } } }"
        )
        annotated_schema = process_schema(
            schema=graphql_schema,
            source_map={},
            query_document=selection_query,
        )

        result = transform(annotated_schema, "com.example", selection_query)
        result_dict = json.loads(result)

        assert result_dict["name"] == "Selection"
        assert len(result_dict["fields"]) == 1

        person_field = result_dict["fields"][0]
        person_record = person_field["type"][1]
        assert person_record["name"] == "Person"
        assert len(person_record["fields"]) == 4

        name_field = person_record["fields"][0]
        assert name_field["name"] == "name"
        assert name_field["type"] == "string"

        address_field = person_record["fields"][1]
        assert address_field["name"] == "address"
        assert address_field["type"][0] == "null"
        address_record = address_field["type"][1]
        assert address_record["type"] == "record"
        assert address_record["name"] == "Address"
        assert len(address_record["fields"]) == 2
        assert address_record["fields"][0]["name"] == "street"
        assert address_record["fields"][0]["type"] == ["null", "string"]
        assert address_record["fields"][1]["name"] == "city"
        assert address_record["fields"][1]["type"] == ["null", "string"]

        billing_address_field = person_record["fields"][2]
        assert billing_address_field["name"] == "billingAddress"
        assert billing_address_field["type"] == ["null", "com.example.Address"]

        manager_field = person_record["fields"][3]
        assert manager_field["name"] == "manager"
        assert manager_field["type"][0] == "null"
        component_record = manager_field["type"][1]
        assert component_record["type"] == "record"
        assert component_record["name"] == "Component"
        assert len(component_record["fields"]) == 3
        assert component_record["fields"][0]["name"] == "id"
        assert component_record["fields"][0]["type"] == "string"
        assert component_record["fields"][1]["name"] == "name"
        assert component_record["fields"][1]["type"] == "string"

        parent_field = component_record["fields"][2]
        assert parent_field["name"] == "parent"
        assert parent_field["type"] == ["null", "com.example.Component"]

        parse_avro_schema(result)


class TestListTypes:
    def test_list_transformation(self) -> None:
        """Test handling of lists of both scalar and object types."""
        schema_str = """
        type Wheel {
            size: Int
        }

        type Vehicle {
            features: [String]
            requiredFeatures: [String!]!
            wheels: [Wheel]
            model: String
            vin: String!
        }

        type Query {
            vehicle: Vehicle
        }
        """
        graphql_schema = build_schema(schema_str)
        selection_query = parse("query Selection { vehicle { features requiredFeatures wheels { size } model vin } }")
        annotated_schema = process_schema(
            schema=graphql_schema,
            source_map={},
            query_document=selection_query,
        )

        result = transform(annotated_schema, "com.example", selection_query)
        result_dict = json.loads(result)

        assert result_dict["name"] == "Selection"
        assert len(result_dict["fields"]) == 1

        vehicle_field = result_dict["fields"][0]
        vehicle_record = vehicle_field["type"][1]
        assert len(vehicle_record["fields"]) == 5

        features_field = vehicle_record["fields"][0]
        assert features_field["name"] == "features"
        assert features_field["type"] == ["null", {"type": "array", "items": ["null", "string"]}]

        required_features_field = vehicle_record["fields"][1]
        assert required_features_field["name"] == "requiredFeatures"
        assert required_features_field["type"] == {"type": "array", "items": "string"}

        wheels_field = vehicle_record["fields"][2]
        assert wheels_field["name"] == "wheels"
        assert wheels_field["type"][0] == "null"
        wheels_array = wheels_field["type"][1]
        assert wheels_array["type"] == "array"
        wheel_items = wheels_array["items"]
        assert wheel_items[0] == "null"
        wheel_record = wheel_items[1]
        assert wheel_record["type"] == "record"
        assert wheel_record["name"] == "Wheel"
        assert len(wheel_record["fields"]) == 1
        assert wheel_record["fields"][0]["name"] == "size"
        assert wheel_record["fields"][0]["type"] == ["null", "int"]

        model_field = vehicle_record["fields"][3]
        assert model_field["name"] == "model"
        assert model_field["type"] == ["null", "string"]

        vin_field = vehicle_record["fields"][4]
        assert vin_field["name"] == "vin"
        assert vin_field["type"] == "string"

        parse_avro_schema(result)


class TestUnionTypes:
    def test_union_type_transformation(self) -> None:
        """Test that union types are correctly transformed."""
        schema_str = """
        type Car {
            id: ID!
            doors: Int
        }

        type Truck {
            id: ID!
            payload: Float
        }

        union SearchResult = Car | Truck

        type Query {
            result: SearchResult
        }
        """
        graphql_schema = build_schema(schema_str)
        selection_query = parse("query Selection { result { ... on Car { id doors } ... on Truck { id payload } } }")
        annotated_schema = process_schema(
            schema=graphql_schema,
            source_map={},
            query_document=selection_query,
        )

        result = transform(annotated_schema, "com.example", selection_query)
        result_dict = json.loads(result)

        assert result_dict["name"] == "Selection"
        assert result_dict["type"] == "record"

        result_field = result_dict["fields"][0]
        assert result_field["name"] == "result"
        assert result_field["type"][0] == "null"

        search_result_record = result_field["type"][1]
        assert search_result_record["type"] == "record"
        assert search_result_record["name"] == "SearchResult"
        assert len(search_result_record["fields"]) == 1

        value_field = search_result_record["fields"][0]
        assert value_field["name"] == "value"
        assert value_field["type"][0] == "null"

        car_record = value_field["type"][1]
        assert car_record["type"] == "record"
        assert car_record["name"] == "Car"
        assert len(car_record["fields"]) == 2
        assert car_record["fields"][0]["name"] == "id"
        assert car_record["fields"][0]["type"] == "string"
        assert car_record["fields"][1]["name"] == "doors"
        assert car_record["fields"][1]["type"] == ["null", "int"]

        truck_record = value_field["type"][2]
        assert truck_record["type"] == "record"
        assert truck_record["name"] == "Truck"
        assert len(truck_record["fields"]) == 2
        assert truck_record["fields"][0]["name"] == "id"
        assert truck_record["fields"][0]["type"] == "string"
        assert truck_record["fields"][1]["name"] == "payload"
        assert truck_record["fields"][1]["type"] == ["null", "double"]

        parse_avro_schema(result)


class TestInterfaceTypes:
    def test_interface_transformation(self) -> None:
        """Test that interface types are correctly transformed."""
        schema_str = """
        interface Vehicle {
            id: ID!
            make: String!
        }

        type Car implements Vehicle {
            id: ID!
            make: String!
            doors: Int!
        }

        type Query {
            vehicle: Vehicle
        }
        """
        graphql_schema = build_schema(schema_str)
        selection_query = parse("query Selection { vehicle { id make } }")
        annotated_schema = process_schema(
            schema=graphql_schema,
            source_map={},
            query_document=selection_query,
        )

        result = transform(annotated_schema, "com.example", selection_query)
        result_dict = json.loads(result)

        assert result_dict["name"] == "Selection"
        assert result_dict["type"] == "record"

        vehicle_field = result_dict["fields"][0]
        assert vehicle_field["name"] == "vehicle"
        assert vehicle_field["type"][0] == "null"

        vehicle_record = vehicle_field["type"][1]
        assert vehicle_record["type"] == "record"
        assert vehicle_record["name"] == "Vehicle"
        assert len(vehicle_record["fields"]) == 2
        assert vehicle_record["fields"][0]["name"] == "id"
        assert vehicle_record["fields"][0]["type"] == "string"
        assert vehicle_record["fields"][1]["name"] == "make"
        assert vehicle_record["fields"][1]["type"] == "string"

        parse_avro_schema(result)


class TestRangeDirective:
    def test_range_int32_optimization(self) -> None:
        """Test that @range directive optimizes Int64 to int when range fits in 32-bit."""
        schema_str = """
        directive @range(min: Float, max: Float) on FIELD_DEFINITION

        scalar Int64

        type Vehicle {
            speed: Int64 @range(min: 0, max: 300)
        }

        type Query {
            vehicle: Vehicle
        }
        """
        graphql_schema = build_schema(schema_str)
        selection_query = parse("query Selection { vehicle { speed } }")
        annotated_schema = process_schema(
            schema=graphql_schema,
            source_map={},
            query_document=selection_query,
        )

        result = transform(annotated_schema, "com.example", selection_query)
        result_dict = json.loads(result)

        vehicle_field = result_dict["fields"][0]
        vehicle_record = vehicle_field["type"][1]
        speed_field = vehicle_record["fields"][0]

        assert speed_field["name"] == "speed"
        assert speed_field["type"] == ["null", "int"]

        parse_avro_schema(result)

    def test_range_requires_long(self) -> None:
        """Test that @range directive uses long when range exceeds 32-bit."""
        schema_str = """
        directive @range(min: Float, max: Float) on FIELD_DEFINITION

        type Vehicle {
            mileage: Int @range(min: 0, max: 5000000000)
        }

        type Query {
            vehicle: Vehicle
        }
        """
        graphql_schema = build_schema(schema_str)
        selection_query = parse("query Selection { vehicle { mileage } }")
        annotated_schema = process_schema(
            schema=graphql_schema,
            source_map={},
            query_document=selection_query,
        )

        result = transform(annotated_schema, "com.example", selection_query)
        result_dict = json.loads(result)

        vehicle_field = result_dict["fields"][0]
        vehicle_record = vehicle_field["type"][1]
        mileage_field = vehicle_record["fields"][0]

        assert mileage_field["name"] == "mileage"
        assert mileage_field["type"] == ["null", "long"]

        parse_avro_schema(result)

    def test_range_negative_values(self) -> None:
        """Test that @range directive handles negative values correctly."""
        schema_str = """
        directive @range(min: Float, max: Float) on FIELD_DEFINITION

        scalar Int64

        type Sensor {
            temperature: Int64 @range(min: -40, max: 150)
        }

        type Query {
            sensor: Sensor
        }
        """
        graphql_schema = build_schema(schema_str)
        selection_query = parse("query Selection { sensor { temperature } }")
        annotated_schema = process_schema(
            schema=graphql_schema,
            source_map={},
            query_document=selection_query,
        )

        result = transform(annotated_schema, "com.example", selection_query)
        result_dict = json.loads(result)

        sensor_field = result_dict["fields"][0]
        sensor_record = sensor_field["type"][1]
        temp_field = sensor_record["fields"][0]

        assert temp_field["name"] == "temperature"
        assert temp_field["type"] == ["null", "int"]

        parse_avro_schema(result)

    def test_no_range_uses_type_mapping(self) -> None:
        """Test that fields without @range use default type mapping."""
        schema_str = """
        scalar Int64
        scalar UInt32

        type Vehicle {
            id: Int64
            counter: UInt32
        }

        type Query {
            vehicle: Vehicle
        }
        """
        graphql_schema = build_schema(schema_str)
        selection_query = parse("query Selection { vehicle { id counter } }")
        annotated_schema = process_schema(
            schema=graphql_schema,
            source_map={},
            query_document=selection_query,
        )

        result = transform(annotated_schema, "com.example", selection_query)
        result_dict = json.loads(result)

        vehicle_field = result_dict["fields"][0]
        vehicle_record = vehicle_field["type"][1]

        id_field = vehicle_record["fields"][0]
        assert id_field["name"] == "id"
        assert id_field["type"] == ["null", "long"]

        counter_field = vehicle_record["fields"][1]
        assert counter_field["name"] == "counter"
        assert counter_field["type"] == ["null", "long"]

        parse_avro_schema(result)

    def test_range_with_only_min(self) -> None:
        """Test that @range with only min optimizes correctly."""
        schema_str = """
        directive @range(min: Float, max: Float) on FIELD_DEFINITION

        scalar Int64

        type Vehicle {
            speed: Int64 @range(min: 0)
        }

        type Query {
            vehicle: Vehicle
        }
        """
        graphql_schema = build_schema(schema_str)
        selection_query = parse("query Selection { vehicle { speed } }")
        annotated_schema = process_schema(
            schema=graphql_schema,
            source_map={},
            query_document=selection_query,
        )

        result = transform(annotated_schema, "com.example", selection_query)
        result_dict = json.loads(result)

        vehicle_field = result_dict["fields"][0]
        vehicle_record = vehicle_field["type"][1]
        speed_field = vehicle_record["fields"][0]

        assert speed_field["name"] == "speed"
        assert speed_field["type"] == ["null", "int"]

        parse_avro_schema(result)

    def test_range_with_only_max(self) -> None:
        """Test that @range with only max optimizes correctly."""
        schema_str = """
        directive @range(min: Float, max: Float) on FIELD_DEFINITION

        scalar Int64

        type Vehicle {
            rpm: Int64 @range(max: 8000)
        }

        type Query {
            vehicle: Vehicle
        }
        """
        graphql_schema = build_schema(schema_str)
        selection_query = parse("query Selection { vehicle { rpm } }")
        annotated_schema = process_schema(
            schema=graphql_schema,
            source_map={},
            query_document=selection_query,
        )

        result = transform(annotated_schema, "com.example", selection_query)
        result_dict = json.loads(result)

        vehicle_field = result_dict["fields"][0]
        vehicle_record = vehicle_field["type"][1]
        rpm_field = vehicle_record["fields"][0]

        assert rpm_field["name"] == "rpm"
        assert rpm_field["type"] == ["null", "int"]

        parse_avro_schema(result)

    def test_range_with_only_min_requires_long(self) -> None:
        """Test that @range with only min uses long when needed."""
        schema_str = """
        directive @range(min: Float, max: Float) on FIELD_DEFINITION

        type Vehicle {
            mileage: Int @range(min: 5000000000)
        }

        type Query {
            vehicle: Vehicle
        }
        """
        graphql_schema = build_schema(schema_str)
        selection_query = parse("query Selection { vehicle { mileage } }")
        annotated_schema = process_schema(
            schema=graphql_schema,
            source_map={},
            query_document=selection_query,
        )

        result = transform(annotated_schema, "com.example", selection_query)
        result_dict = json.loads(result)

        vehicle_field = result_dict["fields"][0]
        vehicle_record = vehicle_field["type"][1]
        mileage_field = vehicle_record["fields"][0]

        assert mileage_field["name"] == "mileage"
        assert mileage_field["type"] == ["null", "long"]

        parse_avro_schema(result)
