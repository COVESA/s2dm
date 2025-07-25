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
        assert "required" in vehicle_def

        required_fields = vehicle_def["required"]
        assert "id" in required_fields
        assert "make" in required_fields

        assert "model" not in required_fields
        assert "year" not in required_fields

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

        assert "required" in vehicle_def
        required_fields = vehicle_def["required"]
        assert "id" in required_fields
        assert "make" in required_fields

        car_def = schema["$defs"]["Car"]
        assert car_def["type"] == "object"
        assert "id" in car_def["properties"]
        assert "make" in car_def["properties"]
        assert "doors" in car_def["properties"]

        assert "required" in car_def
        car_required_fields = car_def["required"]
        assert "id" in car_required_fields
        assert "make" in car_required_fields
        assert "doors" in car_required_fields


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

        assert "required" in vehicle_def
        required_fields = vehicle_def["required"]
        assert "features" in required_fields

        assert "optionalExtras" not in required_fields
        assert "maintenanceRecords" not in required_fields

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
        assert "$comment" in vehicle_def
        assert vehicle_def["$comment"] == "Vehicle entity"
        assert "x-metadata" in vehicle_def
        assert vehicle_def["x-metadata"]["vssType"] == "branch"

        speed_field = vehicle_def["properties"]["speed"]
        assert "$comment" in speed_field
        assert speed_field["$comment"] == "Current speed"
        assert "x-metadata" in speed_field
        assert speed_field["x-metadata"]["vssType"] == "sensor"


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


class TestInstanceTagHandling:
    def test_instance_tag_objects_excluded_from_schema(self) -> None:
        """Test that objects with @instanceTag directive are excluded from JSON Schema."""
        schema_str = """
            directive @instanceTag on OBJECT

            type Query {
                vehicle: Vehicle
                seat: Seat
            }

            type Vehicle {
                id: ID!
                seats: [Seat!]!
            }

            type Seat {
                id: ID!
            }

            type SeatPosition @instanceTag {
                row: RowEnum!
                column: ColumnEnum!
            }

            enum RowEnum {
                ROW1
                ROW2
            }

            enum ColumnEnum {
                LEFT
                RIGHT
            }
        """
        graphql_schema = build_schema(schema_str)
        result = transform(graphql_schema)
        schema = json.loads(result)

        assert "Vehicle" in schema["$defs"]
        assert "Seat" in schema["$defs"]
        assert "RowEnum" in schema["$defs"]
        assert "ColumnEnum" in schema["$defs"]

        assert "SeatPosition" not in schema["$defs"]

    def test_error_on_invalid_instance_tag_field_name(self) -> None:
        """Test that an error is raised if an instanceTag object is referenced incorrectly."""
        schema_str = """
            directive @instanceTag on OBJECT

            type Query {
                vehicle: Vehicle
            }

            type Vehicle {
                id: ID!
                seatPosition: SeatPosition!
            }

            type SeatPosition @instanceTag {
                row: RowEnum!
                column: ColumnEnum!
            }

            enum RowEnum {
                FRONT
                BACK
            }

            enum ColumnEnum {
                LEFT
                RIGHT
            }
        """
        graphql_schema = build_schema(schema_str)

        with pytest.raises(
            ValueError, match="Invalid schema: instanceTag object found on non-instanceTag named field 'seatPosition'"
        ):
            transform(graphql_schema)

    def test_instance_tag_field_excluded_when_valid(self) -> None:
        """Test that instanceTag fields are excluded when they reference valid instance tag objects."""
        schema_str = """
            directive @instanceTag on OBJECT

            type Query {
                vehicle: Vehicle
            }

            type Vehicle {
                id: ID!
                instanceTag: CabinPosition!
                normalField: String!
            }

            type CabinPosition @instanceTag {
                row: RowEnum!
                column: ColumnEnum!
            }

            enum RowEnum {
                ROW1
                ROW2
            }

            enum ColumnEnum {
                LEFT
                RIGHT
            }
        """
        graphql_schema = build_schema(schema_str)
        result = transform(graphql_schema)
        schema = json.loads(result)

        assert "Vehicle" in schema["$defs"]
        vehicle_def = schema["$defs"]["Vehicle"]

        assert "instanceTag" not in vehicle_def["properties"]

        assert "id" in vehicle_def["properties"]
        assert "normalField" in vehicle_def["properties"]

        assert "CabinPosition" not in schema["$defs"]

    def test_instance_tag_field_included_when_invalid(self) -> None:
        """Test that instanceTag fields are included when they don't reference valid instance tag objects."""
        schema_str = """
            type Query {
                vehicle: Vehicle
            }

            type Vehicle {
                id: ID!
                instanceTag: String!  # Not a valid instance tag object
                normalField: String!
            }
        """
        graphql_schema = build_schema(schema_str)
        result = transform(graphql_schema)
        schema = json.loads(result)

        assert "Vehicle" in schema["$defs"]
        vehicle_def = schema["$defs"]["Vehicle"]

        assert "instanceTag" in vehicle_def["properties"]
        assert vehicle_def["properties"]["instanceTag"]["type"] == "string"

        assert "id" in vehicle_def["properties"]
        assert "normalField" in vehicle_def["properties"]

    def test_instance_tag_field_with_non_instance_tag_object(self) -> None:
        """Test that instanceTag fields referencing regular objects (without @instanceTag) are included."""
        schema_str = """
            directive @instanceTag on OBJECT

            type Query {
                vehicle: Vehicle
            }

            type Vehicle {
                id: ID!
                instanceTag: RegularObject!  # References object without @instanceTag
                normalField: String!
            }

            type RegularObject {
                name: String!
                value: Int!
            }
        """
        graphql_schema = build_schema(schema_str)
        result = transform(graphql_schema)
        schema = json.loads(result)

        assert "Vehicle" in schema["$defs"]
        vehicle_def = schema["$defs"]["Vehicle"]

        assert "instanceTag" in vehicle_def["properties"]
        assert vehicle_def["properties"]["instanceTag"]["$ref"] == "#/$defs/RegularObject"

        assert "RegularObject" in schema["$defs"]

        assert "id" in vehicle_def["properties"]
        assert "normalField" in vehicle_def["properties"]

    def test_instance_tag_object_expansion(self) -> None:
        """Test that instanceTag objects are expanded correctly in the schema."""
        schema_str = """
            directive @instanceTag on OBJECT

            type Query {
                vehicle: Vehicle
            }

            type Vehicle {
                id: ID!
                door: Door!
            }

            type Door {
                locked: Boolean!
                instanceTag: InCabinArea2x2
            }

            enum TwoRowsInCabinEnum {
                ROW1
                ROW2
            }

            enum ThreeColumnsInCabinEnum {
                DRIVERSIDE
                MIDDLE
                PASSENGERSIDE
            }

            type InCabinArea2x2 @instanceTag {
                row: TwoRowsInCabinEnum
                column: ThreeColumnsInCabinEnum
            }
        """
        graphql_schema = build_schema(schema_str)
        result = transform(graphql_schema)
        schema = json.loads(result)

        assert "Vehicle" in schema["$defs"]
        vehicle_def = schema["$defs"]["Vehicle"]

        assert "door" in vehicle_def["properties"]

        door_property = vehicle_def["properties"]["door"]
        assert door_property["type"] == "object"
        assert "properties" in door_property
        assert door_property["additionalProperties"] is False

        door_property_properties = door_property["properties"]
        assert door_property_properties["ROW1"]["properties"]["DRIVERSIDE"]["$ref"] == "#/$defs/Door"
        assert door_property_properties["ROW1"]["properties"]["MIDDLE"]["$ref"] == "#/$defs/Door"
        assert door_property_properties["ROW1"]["properties"]["PASSENGERSIDE"]["$ref"] == "#/$defs/Door"

        assert "Door" in schema["$defs"]
        door_def = schema["$defs"]["Door"]

        assert "locked" in door_def["properties"]

    def test_instance_tag_list_object_expansion(self) -> None:
        """Test that instanceTag objects in lists are expanded correctly in the schema."""
        schema_str = """
            directive @instanceTag on OBJECT

            type Query {
                vehicle: Vehicle
            }

            type Vehicle {
                id: ID!
                doors: [Door]!
            }

            type Door {
                locked: Boolean!
                instanceTag: InCabinArea2x2
            }

            enum TwoRowsInCabinEnum {
                ROW1
                ROW2
            }

            enum ThreeColumnsInCabinEnum {
                DRIVERSIDE
                MIDDLE
                PASSENGERSIDE
            }

            type InCabinArea2x2 @instanceTag {
                row: TwoRowsInCabinEnum
                column: ThreeColumnsInCabinEnum
            }
        """
        graphql_schema = build_schema(schema_str)
        result = transform(graphql_schema)
        schema = json.loads(result)

        assert "Vehicle" in schema["$defs"]
        vehicle_def = schema["$defs"]["Vehicle"]

        assert "doors" in vehicle_def["properties"]

        door_property = vehicle_def["properties"]["doors"]
        assert door_property["type"] == "array"
        assert "items" in door_property
        assert "additionalProperties" not in door_property

        door_property_items = door_property["items"]
        assert door_property_items["type"] == "object"
        assert door_property_items["additionalProperties"] is False
        assert "properties" in door_property_items

        door_property_items_properties = door_property_items["properties"]
        assert door_property_items_properties["ROW1"]["properties"]["DRIVERSIDE"]["$ref"] == "#/$defs/Door"
        assert door_property_items_properties["ROW1"]["properties"]["MIDDLE"]["$ref"] == "#/$defs/Door"
        assert door_property_items_properties["ROW1"]["properties"]["PASSENGERSIDE"]["$ref"] == "#/$defs/Door"

        assert "Door" in schema["$defs"]
        door_def = schema["$defs"]["Door"]

        assert "locked" in door_def["properties"]


class TestStrictMode:
    def test_strict_mode_set_to_false(self) -> None:
        """Test schema translation with strict mode set to False."""
        schema_str = """
            type Vehicle {
                id: ID!
                year: Int!
                make: String
                doors: [Door!]!
                doorsAlt: [Door]
            }

            type Door {
                locked: Boolean
            }
        """
        graphql_schema = build_schema(schema_str)

        result = transform(graphql_schema, strict=False)
        schema = json.loads(result)

        assert "Vehicle" in schema["$defs"]
        vehicle_def = schema["$defs"]["Vehicle"]
        assert "required" in vehicle_def
        assert "id" in vehicle_def["required"]
        assert "year" in vehicle_def["required"]
        assert "make" not in vehicle_def["required"]
        assert "doors" in vehicle_def["required"]
        assert "doorsAlt" not in vehicle_def["required"]

        assert vehicle_def["properties"]["year"]["type"] == "integer"
        assert vehicle_def["properties"]["make"]["type"] == "string"

        doors_def = vehicle_def["properties"]["doors"]
        assert doors_def["items"]["$ref"] == "#/$defs/Door"

        doors_alt_def = vehicle_def["properties"]["doorsAlt"]
        assert doors_alt_def["type"] == "array"
        assert doors_alt_def["items"]["$ref"] == "#/$defs/Door"

    def test_strict_mode_set_to_true(self) -> None:
        """Test schema translation with strict mode set to True."""
        schema_str = """
            type Vehicle {
                id: ID!
                year: Int!
                make: String
                doors: [Door!]!
                doorsAlt: [Door]
            }

            type Door {
                locked: Boolean
            }
        """
        graphql_schema = build_schema(schema_str)

        result = transform(graphql_schema, strict=True)
        schema = json.loads(result)

        assert "Vehicle" in schema["$defs"]
        vehicle_def = schema["$defs"]["Vehicle"]
        assert "required" in vehicle_def
        assert "id" in vehicle_def["required"]
        assert "year" in vehicle_def["required"]
        assert "make" not in vehicle_def["required"]
        assert "doors" in vehicle_def["required"]
        assert "doorsAlt" not in vehicle_def["required"]

        assert vehicle_def["properties"]["year"]["type"] == "integer"
        assert vehicle_def["properties"]["make"]["type"] == ["string", "null"]

        doors_def = vehicle_def["properties"]["doors"]
        assert doors_def["type"] == "array"
        assert doors_def["items"]["$ref"] == "#/$defs/Door"

        doors_alt_def = vehicle_def["properties"]["doorsAlt"]

        assert "oneOf" in doors_alt_def
        assert len(doors_alt_def["oneOf"]) == 2

        array_option = doors_alt_def["oneOf"][0]
        assert array_option["type"] == "array"
        assert array_option["items"] == {"oneOf": [{"$ref": "#/$defs/Door"}, {"type": "null"}]}

        null_option = doors_alt_def["oneOf"][1]
        assert null_option == {"type": "null"}

        assert "Door" in schema["$defs"]
        door_def = schema["$defs"]["Door"]
        assert door_def["properties"]["locked"]["type"] == ["boolean", "null"]
