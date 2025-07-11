"""Tests for the JSON Schema exporter."""

import json

import pytest
from graphql import build_schema

from s2dm.exporters.jsonschema.jsonschema import transform


class TestBasicTransformation:
    def test_basic_schema_structure(self) -> None:
        """Test that basic schema structure is generated correctly."""
        schema_str = """
            type Query { vehicle: Vehicle }
            type Vehicle { id: ID!, make: String! }
        """
        graphql_schema = build_schema(schema_str)

        result = transform(graphql_schema)
        schema = json.loads(result)

        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert "type" in schema
        assert "$defs" in schema
        assert "Vehicle" in schema["$defs"]

    def test_object_type_transformation(self) -> None:
        """Test that GraphQL object types are correctly transformed."""
        schema_str = """
            type Query { vehicle: Vehicle }
            type Vehicle {
                id: ID!
                make: String!
                model: String
                year: Int
            }
        """
        graphql_schema = build_schema(schema_str)

        result = transform(graphql_schema)
        schema = json.loads(result)

        vehicle_def = schema["$defs"]["Vehicle"]
        assert vehicle_def["type"] == "object"
        assert "properties" in vehicle_def
        assert "required" not in vehicle_def

        assert vehicle_def["properties"]["id"]["type"] == "string"
        assert vehicle_def["properties"]["make"]["type"] == "string"
        assert vehicle_def["properties"]["model"]["type"] == "string"
        assert vehicle_def["properties"]["year"]["type"] == "integer"


class TestRootNodeFiltering:
    def test_root_node_reference(self) -> None:
        """Test that specifying a root node creates a $ref to that node."""
        schema_str = """
            type Query { vehicle: Vehicle }
            type Vehicle { id: ID!, make: String! }
            type Engine { id: ID!, displacement: Float! }
        """
        graphql_schema = build_schema(schema_str)

        result = transform(graphql_schema, "Vehicle")
        schema = json.loads(result)

        assert schema["title"] == "Vehicle"
        assert schema["$ref"] == "#/$defs/Vehicle"
        assert "Vehicle" in schema["$defs"]

    def test_root_node_filters_types(self) -> None:
        """Test that root node filtering only includes reachable types."""
        schema_str = """
            type Query { vehicle: Vehicle, engine: Engine }
            type Vehicle { id: ID!, engine: Engine }
            type Engine { id: ID!, displacement: Float! }
            type UnrelatedType { id: ID!, data: String }
        """
        graphql_schema = build_schema(schema_str)

        result = transform(graphql_schema, "Vehicle")
        schema = json.loads(result)

        # Should include Vehicle and Engine (referenced by Vehicle)
        assert "Vehicle" in schema["$defs"]
        assert "Engine" in schema["$defs"]

        # Should NOT include UnrelatedType
        assert "UnrelatedType" not in schema["$defs"]

    def test_invalid_root_node_raises_error(self) -> None:
        """Test that specifying an invalid root node raises an error."""
        schema_str = """
            type Query { vehicle: Vehicle }
            type Vehicle { id: ID!, make: String! }
        """
        graphql_schema = build_schema(schema_str)

        with pytest.raises(ValueError, match="Root type 'NonExistent' not found in schema"):
            transform(graphql_schema, "NonExistent")


class TestGraphQLTypeHandling:
    def test_scalar_types(self) -> None:
        """Test that GraphQL scalar types are correctly mapped."""
        schema_str = """
            type Query { vehicle: Vehicle }
            type Vehicle {
                vin: String
                year: Int
                price: Float
                isElectric: Boolean
                id: ID
            }
        """
        graphql_schema = build_schema(schema_str)

        result = transform(graphql_schema)
        schema = json.loads(result)

        vehicle_def = schema["$defs"]["Vehicle"]
        props = vehicle_def["properties"]

        assert props["vin"]["type"] == "string"
        assert props["year"]["type"] == "integer"
        assert props["price"]["type"] == "number"
        assert props["isElectric"]["type"] == "boolean"
        assert props["id"]["type"] == "string"

    def test_enum_types(self) -> None:
        """Test that GraphQL enum types are correctly transformed."""
        schema_str = """
            type Query { vehicle: Vehicle }

            enum FuelType {
                GASOLINE
                DIESEL
                ELECTRIC
                HYBRID
            }

            type Vehicle {
                fuelType: FuelType
            }
        """
        graphql_schema = build_schema(schema_str)

        result = transform(graphql_schema)
        schema = json.loads(result)

        fuel_type_def = schema["$defs"]["FuelType"]
        assert fuel_type_def["type"] == "string"
        assert set(fuel_type_def["enum"]) == {"GASOLINE", "DIESEL", "ELECTRIC", "HYBRID"}

        vehicle_def = schema["$defs"]["Vehicle"]
        assert vehicle_def["properties"]["fuelType"]["$ref"] == "#/$defs/FuelType"

    def test_union_types(self) -> None:
        """Test that GraphQL union types are correctly transformed."""
        schema_str = """
            type Query { searchResults: VehicleSearchResult }

            union VehicleSearchResult = Car | Truck

            type Car { id: ID!, doors: Int! }
            type Truck { id: ID!, payloadCapacity: Float! }
        """
        graphql_schema = build_schema(schema_str)

        result = transform(graphql_schema)
        schema = json.loads(result)

        union_def = schema["$defs"]["VehicleSearchResult"]
        assert "oneOf" in union_def

        refs = [item["$ref"] for item in union_def["oneOf"]]
        assert "#/$defs/Car" in refs
        assert "#/$defs/Truck" in refs

    def test_interface_types(self) -> None:
        """Test that GraphQL interface types are correctly transformed."""
        schema_str = """
            type Query { vehicle: Vehicle }

            interface Vehicle {
                id: ID!
                make: String!
            }

            type Car implements Vehicle {
                id: ID!
                make: String!
                doors: Int!
            }
        """
        graphql_schema = build_schema(schema_str)

        result = transform(graphql_schema)
        schema = json.loads(result)

        vehicle_def = schema["$defs"]["Vehicle"]
        assert vehicle_def["type"] == "object"
        assert "id" in vehicle_def["properties"]
        assert "make" in vehicle_def["properties"]
        assert "required" not in vehicle_def

        car_def = schema["$defs"]["Car"]
        assert car_def["type"] == "object"
        assert "id" in car_def["properties"]
        assert "make" in car_def["properties"]
        assert "doors" in car_def["properties"]


class TestEdgeCases:
    def test_list_types(self) -> None:
        """Test handling of GraphQL list types."""
        schema_str = """
            type Query { vehicle: Vehicle }
            type Vehicle {
                features: [String!]!
                optionalExtras: [String]
                maintenanceRecords: [MaintenanceRecord]
            }
            type MaintenanceRecord { id: ID!, date: String! }
        """
        graphql_schema = build_schema(schema_str)

        result = transform(graphql_schema)
        schema = json.loads(result)

        vehicle_def = schema["$defs"]["Vehicle"]
        props = vehicle_def["properties"]

        assert props["features"]["type"] == "array"
        assert props["features"]["items"]["type"] == "string"
        assert "required" not in vehicle_def

        assert props["optionalExtras"]["type"] == "array"

        # Check list of objects (nullable items use oneOf)
        assert props["maintenanceRecords"]["type"] == "array"
        items = props["maintenanceRecords"]["items"]
        if "oneOf" in items:
            # Nullable items use oneOf
            refs = [item.get("$ref") for item in items["oneOf"] if "$ref" in item]
            assert "#/$defs/MaintenanceRecord" in refs
        else:
            # Non-nullable items use direct reference
            assert items["$ref"] == "#/$defs/MaintenanceRecord"

    def test_nested_types(self) -> None:
        """Test handling of nested object types."""
        schema_str = """
            type Query { vehicle: Vehicle }
            type Vehicle {
                id: ID!
                engine: Engine!
                seats: [Seat!]!
            }
            type Engine {
                displacement: Float
                horsepower: Int
            }
            type Seat {
                id: ID!
                position: String!
                material: String
                vehicle: Vehicle!
            }
        """
        graphql_schema = build_schema(schema_str)

        result = transform(graphql_schema)
        schema = json.loads(result)

        assert "Vehicle" in schema["$defs"]
        assert "Engine" in schema["$defs"]
        assert "Seat" in schema["$defs"]

        vehicle_def = schema["$defs"]["Vehicle"]
        assert vehicle_def["properties"]["engine"]["$ref"] == "#/$defs/Engine"
        assert vehicle_def["properties"]["seats"]["items"]["$ref"] == "#/$defs/Seat"

        seat_def = schema["$defs"]["Seat"]
        assert seat_def["properties"]["vehicle"]["$ref"] == "#/$defs/Vehicle"

    def test_recursive_types(self) -> None:
        """Test handling of recursive/self-referencing types."""
        schema_str = """
            type Query { component: VehicleComponent }

            type VehicleComponent {
                id: ID!
                name: String!
                subComponents: [VehicleComponent!]
                parentComponent: VehicleComponent
            }
        """
        graphql_schema = build_schema(schema_str)

        result = transform(graphql_schema)
        schema = json.loads(result)

        # Check that recursive references work
        component_def = schema["$defs"]["VehicleComponent"]
        assert component_def["properties"]["subComponents"]["items"]["$ref"] == "#/$defs/VehicleComponent"
        assert component_def["properties"]["parentComponent"]["$ref"] == "#/$defs/VehicleComponent"


class TestComplexSchemas:
    def test_vehicle_fleet_schema(self) -> None:
        """Test with a realistic vehicle fleet management schema."""
        schema_str = """
            type Query {
                vehicles: [Vehicle!]!
                drivers: [Driver!]!
            }

            type Vehicle {
                id: ID!
                vin: String!
                make: String!
                model: String!
                year: Int!
                engine: Engine!
                seats: [Seat!]!
                currentDriver: Driver
            }

            type Engine {
                displacement: Float
                horsepower: Int
                fuelType: FuelType!
                efficiency: Float
            }

            enum FuelType {
                GASOLINE
                DIESEL
                ELECTRIC
                HYBRID
            }

            type Seat {
                id: ID!
                position: SeatPosition!
                material: String
                hasHeating: Boolean!
            }

            enum SeatPosition {
                DRIVER
                PASSENGER_FRONT
                PASSENGER_REAR_LEFT
                PASSENGER_REAR_RIGHT
            }

            type Driver {
                id: ID!
                licenseNumber: String!
                name: String!
                assignedVehicles: [Vehicle!]!
            }
        """
        graphql_schema = build_schema(schema_str)

        result = transform(graphql_schema)
        schema = json.loads(result)

        # Check all types are present
        expected_types = {"Vehicle", "Engine", "Seat", "Driver", "FuelType", "SeatPosition"}
        assert all(t in schema["$defs"] for t in expected_types)

        # Check some key relationships
        vehicle_def = schema["$defs"]["Vehicle"]
        assert vehicle_def["properties"]["engine"]["$ref"] == "#/$defs/Engine"
        assert vehicle_def["properties"]["seats"]["items"]["$ref"] == "#/$defs/Seat"
        assert vehicle_def["properties"]["currentDriver"]["$ref"] == "#/$defs/Driver"

        engine_def = schema["$defs"]["Engine"]
        assert engine_def["properties"]["fuelType"]["$ref"] == "#/$defs/FuelType"

        seat_def = schema["$defs"]["Seat"]
        assert seat_def["properties"]["position"]["$ref"] == "#/$defs/SeatPosition"


class TestDirectives:
    def test_range_directive_on_field(self) -> None:
        schema_str = """
            directive @range(min: Float, max: Float) on FIELD_DEFINITION

            type Query { vehicle: Vehicle }
            type Vehicle {
                id: ID!
                year: Int! @range(min: 1900, max: 2030)
                price: Float @range(min: 0.0, max: 999999.99)
            }
        """
        graphql_schema = build_schema(schema_str)
        result = transform(graphql_schema)
        schema = json.loads(result)

        vehicle_def = schema["$defs"]["Vehicle"]
        year_prop = vehicle_def["properties"]["year"]
        price_prop = vehicle_def["properties"]["price"]

        assert "minimum" in year_prop
        assert "maximum" in year_prop
        assert year_prop["minimum"] == 1900.0
        assert year_prop["maximum"] == 2030.0

        assert "minimum" in price_prop
        assert "maximum" in price_prop
        assert price_prop["minimum"] == 0.0
        assert price_prop["maximum"] == 999999.99

    def test_no_duplicates_directive(self) -> None:
        schema_str = """
            directive @noDuplicates on FIELD_DEFINITION

            type Query { vehicle: Vehicle }
            type Vehicle {
                id: ID!
                features: [String!]! @noDuplicates
            }
        """
        graphql_schema = build_schema(schema_str)
        result = transform(graphql_schema)
        schema = json.loads(result)

        vehicle_def = schema["$defs"]["Vehicle"]
        features_prop = vehicle_def["properties"]["features"]
        assert features_prop.get("uniqueItems") is True

    def test_cardinality_directive_on_field(self) -> None:
        schema_str = """
            directive @cardinality(min: Int, max: Int) on FIELD_DEFINITION

            type Query { vehicle: Vehicle }
            type Vehicle {
                id: ID!
                features: [String!]! @cardinality(min: 1, max: 5)
            }
        """
        graphql_schema = build_schema(schema_str)
        result = transform(graphql_schema)
        schema = json.loads(result)

        vehicle_def = schema["$defs"]["Vehicle"]
        features_prop = vehicle_def["properties"]["features"]
        assert "minItems" in features_prop
        assert "maxItems" in features_prop
        assert features_prop["minItems"] == 1
        assert features_prop["maxItems"] == 5

    def test_multiple_directives_on_field(self) -> None:
        schema_str = """
            directive @cardinality(min: Int, max: Int) on FIELD_DEFINITION
            directive @noDuplicates on FIELD_DEFINITION

            type Query { vehicle: Vehicle }
            type Vehicle {
                id: ID!
                tags: [String!]! @cardinality(min: 1, max: 10) @noDuplicates
            }
        """
        graphql_schema = build_schema(schema_str)
        result = transform(graphql_schema)
        schema = json.loads(result)

        vehicle_def = schema["$defs"]["Vehicle"]
        tags_prop = vehicle_def["properties"]["tags"]
        assert tags_prop.get("uniqueItems") is True
        assert "minItems" in tags_prop
        assert "maxItems" in tags_prop

    def test_metadata_directive(self) -> None:
        schema_str = """
            directive @metadata(comment: String, vssType: String) on FIELD_DEFINITION | OBJECT

            type Query { vehicle: Vehicle }
            type Vehicle @metadata(comment: "Vehicle entity", vssType: "branch") {
                id: ID!
                speed: Float @metadata(comment: "Current speed", vssType: "sensor")
            }
        """
        graphql_schema = build_schema(schema_str)
        result = transform(graphql_schema)
        schema = json.loads(result)

        vehicle_def = schema["$defs"]["Vehicle"]
        assert "x-metadata" in vehicle_def
        assert vehicle_def["x-metadata"]["comment"] == "Vehicle entity"
        assert vehicle_def["x-metadata"]["vssType"] == "branch"


class TestErrorHandling:
    def test_unsupported_graphql_type_handling(self) -> None:
        schema_str = """
            type Query { data: String }
            input InputType { field: String }
        """
        graphql_schema = build_schema(schema_str)
        result = transform(graphql_schema)
        schema = json.loads(result)

        assert "InputType" not in schema["$defs"]

    def test_empty_schema_handling(self) -> None:
        schema_str = """
            type Query { hello: String }
        """
        graphql_schema = build_schema(schema_str)
        result = transform(graphql_schema)
        schema = json.loads(result)

        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert "$defs" in schema


class TestAdvancedFeatures:
    def test_field_descriptions(self) -> None:
        schema_str = """
            type Query { vehicle: Vehicle }
            type Vehicle {
                id: ID!
                "The make of the vehicle"
                make: String!
                "The model year of the vehicle"
                year: Int
            }
        """
        graphql_schema = build_schema(schema_str)
        result = transform(graphql_schema)
        schema = json.loads(result)

        vehicle_def = schema["$defs"]["Vehicle"]
        make_prop = vehicle_def["properties"]["make"]
        year_prop = vehicle_def["properties"]["year"]

        assert "description" in make_prop
        assert make_prop["description"] == "The make of the vehicle"
        assert "description" in year_prop
        assert year_prop["description"] == "The model year of the vehicle"

    def test_union_type_as_field_type(self) -> None:
        schema_str = """
            type Query { vehicle: Vehicle }
            type Vehicle {
                id: ID!
                transport: Transport
            }
            union Transport = Car | Bike
            type Car { wheels: Int! }
            type Bike { wheels: Int! }
        """
        graphql_schema = build_schema(schema_str)
        result = transform(graphql_schema)
        schema = json.loads(result)

        vehicle_def = schema["$defs"]["Vehicle"]
        transport_prop = vehicle_def["properties"]["transport"]
        assert transport_prop["$ref"] == "#/$defs/Transport"

        transport_def = schema["$defs"]["Transport"]
        assert "oneOf" in transport_def
