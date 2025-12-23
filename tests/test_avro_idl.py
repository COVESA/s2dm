"""Tests for the Avro protocol exporter."""

import re

from graphql import build_schema

from s2dm.exporters.avro.protocol import translate_to_avro_protocol
from s2dm.exporters.utils.schema_loader import process_schema


class TestBasicIDLGeneration:
    def test_basic_struct_type(self) -> None:
        """Test that types with @struct directive are exported as IDL protocols and non-struct types are excluded."""
        schema_str = """
        directive @vspec(element: VspecElement!) on OBJECT

        enum VspecElement {
            STRUCT
        }

        type Vehicle @vspec(element: STRUCT) {
            id: ID!
            make: String!
            model: String
            year: Int
        }

        type Person {
            name: String
        }

        type Query {
            vehicle: Vehicle
            person: Person
        }
        """
        graphql_schema = build_schema(schema_str)
        annotated_schema = process_schema(schema=graphql_schema, source_map={}, query_document=None)

        result = translate_to_avro_protocol(annotated_schema, "com.example")

        assert len(result) == 1
        assert "Vehicle" in result
        assert "Person" not in result

        protocol = result["Vehicle"]
        assert re.search(
            r'@namespace\("com\.example"\).*?'
            r"protocol\s+Vehicle\s*\{.*?"
            r"record\s+Vehicle\s*\{.*?"
            r"string\?\s+id;.*?"
            r"string\?\s+make;.*?"
            r"string\?\s+model;.*?"
            r"int\?\s+year;.*?"
            r"\}.*?"
            r"\}",
            protocol,
            re.DOTALL,
        )


class TestEnumInIDL:
    def test_enum_inside_protocol(self) -> None:
        """Test that enum types map to strings in non-strict mode."""
        schema_str = """
        directive @vspec(element: VspecElement!) on OBJECT

        enum VspecElement {
            STRUCT
        }

        enum Status {
            ACTIVE
            INACTIVE
            PENDING
        }

        type Vehicle @vspec(element: STRUCT) {
            id: ID!
            status: Status
        }

        type Query {
            vehicle: Vehicle
        }
        """
        graphql_schema = build_schema(schema_str)
        annotated_schema = process_schema(schema=graphql_schema, source_map={}, query_document=None)

        result = translate_to_avro_protocol(annotated_schema, "com.example")

        protocol = result["Vehicle"]
        assert not re.search(r"^\s*enum\s+Status\s*\{", protocol, re.MULTILINE)
        assert re.search(
            r"protocol\s+Vehicle\s*\{.*?"
            r"record\s+Vehicle\s*\{.*?"
            r"string\?\s+id;.*?"
            r"string\?\s+status;.*?"
            r"\}.*?"
            r"\}",
            protocol,
            re.DOTALL,
        ), "Non-strict mode: all fields should be optional, status should be string"


class TestNestedTypesInIDL:
    def test_nested_record_inside_protocol(self) -> None:
        """Test that nested record dependencies are included inside the protocol definition."""
        schema_str = """
        directive @vspec(element: VspecElement!) on OBJECT

        enum VspecElement {
            STRUCT
        }

        type Address {
            street: String
            city: String
        }

        type Person @vspec(element: STRUCT) {
            name: String!
            address: Address
        }

        type Query {
            person: Person
        }
        """
        graphql_schema = build_schema(schema_str)
        annotated_schema = process_schema(schema=graphql_schema, source_map={}, query_document=None)

        result = translate_to_avro_protocol(annotated_schema, "com.example")

        protocol = result["Person"]
        assert re.search(r"protocol\s+Person\s*\{", protocol), "Should have Person protocol"
        assert re.search(
            r"record\s+Person\s*\{.*?" r"string\?\s+name;.*?" r"Address\?\s+address;.*?" r"\}",
            protocol,
            re.DOTALL,
        ), "Person record should have name and address fields"
        assert re.search(
            r"record\s+Address\s*\{.*?" r"string\?\s+street;.*?" r"string\?\s+city;.*?" r"\}",
            protocol,
            re.DOTALL,
        ), "Address record should be inside protocol with street and city fields"


class TestArrayTypesInIDL:
    def test_array_field_syntax(self) -> None:
        """Test that array fields use correct IDL syntax."""
        schema_str = """
        directive @vspec(element: VspecElement!) on OBJECT

        enum VspecElement {
            STRUCT
        }

        type Vehicle @vspec(element: STRUCT) {
            id: ID!
            features: [String]
        }

        type Query {
            vehicle: Vehicle
        }
        """
        graphql_schema = build_schema(schema_str)
        annotated_schema = process_schema(schema=graphql_schema, source_map={}, query_document=None)

        result = translate_to_avro_protocol(annotated_schema, "com.example")

        protocol = result["Vehicle"]
        assert re.search(r"array<string>\?\s+features;", protocol)


class TestScalarTypes:
    def test_custom_scalars(self) -> None:
        """Test that custom scalar types are mapped correctly."""
        schema_str = """
        directive @vspec(element: VspecElement!) on OBJECT

        enum VspecElement {
            STRUCT
        }

        scalar Int64
        scalar UInt32

        type Sensor @vspec(element: STRUCT) {
            id: ID!
            reading: Int64
            counter: UInt32
        }

        type Query {
            sensor: Sensor
        }
        """
        graphql_schema = build_schema(schema_str)
        annotated_schema = process_schema(schema=graphql_schema, source_map={}, query_document=None)

        result = translate_to_avro_protocol(annotated_schema, "com.example")

        protocol = result["Sensor"]
        assert re.search(r"long\?\s+reading;", protocol)
        assert re.search(r"long\?\s+counter;", protocol)


class TestRangeDirectiveInIDL:
    def test_range_optimizes_to_int(self) -> None:
        """Test that @range directive optimizes to int when possible."""
        schema_str = """
        directive @vspec(element: VspecElement!) on OBJECT

        enum VspecElement {
            STRUCT
        }
        directive @range(min: Float, max: Float) on FIELD_DEFINITION

        scalar Int64

        type Vehicle @vspec(element: STRUCT) {
            speed: Int64 @range(min: 0, max: 300)
        }

        type Query {
            vehicle: Vehicle
        }
        """
        graphql_schema = build_schema(schema_str)
        annotated_schema = process_schema(schema=graphql_schema, source_map={}, query_document=None)

        result = translate_to_avro_protocol(annotated_schema, "com.example")

        protocol = result["Vehicle"]
        assert re.search(r"int\?\s+speed;", protocol)

    def test_range_requires_long(self) -> None:
        """Test that @range uses long when range exceeds 32-bit."""
        schema_str = """
        directive @vspec(element: VspecElement!) on OBJECT

        enum VspecElement {
            STRUCT
        }
        directive @range(min: Float, max: Float) on FIELD_DEFINITION

        type Vehicle @vspec(element: STRUCT) {
            mileage: Int @range(min: 0, max: 5000000000)
        }

        type Query {
            vehicle: Vehicle
        }
        """
        graphql_schema = build_schema(schema_str)
        annotated_schema = process_schema(schema=graphql_schema, source_map={}, query_document=None)

        result = translate_to_avro_protocol(annotated_schema, "com.example")

        protocol = result["Vehicle"]
        assert re.search(r"long\?\s+mileage;", protocol)


class TestUnionTypesInIDL:
    def test_union_type_transformation(self) -> None:
        """Test that union types are correctly transformed in IDL."""
        schema_str = """
        directive @vspec(element: VspecElement!) on OBJECT

        enum VspecElement {
            STRUCT
        }

        type Car {
            id: ID!
            doors: Int
        }

        type Truck {
            id: ID!
            payload: Float
        }

        union Vehicle = Car | Truck

        type Fleet @vspec(element: STRUCT) {
            id: ID!
            vehicle: Vehicle
        }

        type Query {
            fleet: Fleet
        }
        """
        graphql_schema = build_schema(schema_str)
        annotated_schema = process_schema(schema=graphql_schema, source_map={}, query_document=None)

        result = translate_to_avro_protocol(annotated_schema, "com.example")

        protocol = result["Fleet"]
        assert re.search(r"protocol\s+Fleet\s*\{", protocol), "Should have Fleet protocol"
        assert re.search(
            r"record\s+Fleet\s*\{.*?" r"string\?\s+id;.*?" r"Vehicle\?\s+vehicle;.*?" r"\}",
            protocol,
            re.DOTALL,
        ), "Fleet record should have id and vehicle fields"
        assert re.search(
            r"record\s+Vehicle\s*\{.*?" r"union\s*\{.*?Car.*?Truck.*?\}\s+value;.*?" r"\}",
            protocol,
            re.DOTALL,
        ), "Vehicle record should have union field with Car and Truck"
        assert re.search(
            r"record\s+Car\s*\{.*?" r"string\?\s+id;.*?" r"int\?\s+doors;.*?" r"\}",
            protocol,
            re.DOTALL,
        ), "Car record should be inside protocol"
        assert re.search(
            r"record\s+Truck\s*\{.*?" r"string\?\s+id;.*?" r"double\?\s+payload;.*?" r"\}",
            protocol,
            re.DOTALL,
        ), "Truck record should be inside protocol"


class TestStrictMode:
    def test_strict_mode_enums_and_nullability(self) -> None:
        """Test that strict mode enforces enums as enums and nullability."""
        schema_str = """
        directive @vspec(element: VspecElement!) on OBJECT

        enum VspecElement {
            STRUCT
        }

        enum Status {
            ACTIVE
            INACTIVE
        }

        type Vehicle @vspec(element: STRUCT) {
            id: ID!
            make: String!
            model: String
            status: Status
        }

        type Query {
            vehicle: Vehicle
        }
        """
        graphql_schema = build_schema(schema_str)
        annotated_schema = process_schema(schema=graphql_schema, source_map={}, query_document=None)

        result = translate_to_avro_protocol(annotated_schema, "com.example", strict=True)

        protocol = result["Vehicle"]
        assert re.search(
            r"protocol\s+Vehicle\s*\{.*?" r"enum\s+Status\s*\{.*?ACTIVE.*?INACTIVE.*?\}.*?" r"\}",
            protocol,
            re.DOTALL,
        ), "Strict mode: Status enum inside protocol"

        assert re.search(
            r"protocol\s+Vehicle\s*\{.*?"
            r"record\s+Vehicle\s*\{.*?"
            r"string\s+id;.*?"
            r"string\s+make;.*?"
            r"string\?\s+model;.*?"
            r"Status\?\s+status;.*?"
            r"\}.*?"
            r"\}",
            protocol,
            re.DOTALL,
        ), "Strict mode: Vehicle record inside protocol with correct fields and nullability"

    def test_strict_mode_includes_enums_from_instance_tag_types(self) -> None:
        """Test that strict mode includes enum definitions used by @instanceTag types."""
        schema_str = """
        directive @vspec(element: VspecElement!) on OBJECT
        directive @instanceTag on OBJECT

        enum VspecElement {
            STRUCT
        }

        enum RowEnum {
            ROW1
            ROW2
        }

        enum SideEnum {
            DRIVERSIDE
            PASSENGERSIDE
        }

        type DoorPosition @instanceTag {
            row: RowEnum!
            side: SideEnum!
        }

        type Door {
            isLocked: Boolean
            position: Int
            instanceTag: DoorPosition
        }

        type Vehicle @vspec(element: STRUCT) {
            doors: [Door]
            model: String
        }

        type Query {
            vehicle: Vehicle
        }
        """
        graphql_schema = build_schema(schema_str)
        annotated_schema = process_schema(schema=graphql_schema, source_map={}, query_document=None)

        result = translate_to_avro_protocol(annotated_schema, "com.example", strict=True)

        protocol = result["Vehicle"]

        assert re.search(
            r"enum\s+RowEnum\s*\{.*?ROW1.*?ROW2.*?\}",
            protocol,
            re.DOTALL,
        ), "Strict mode: RowEnum should be defined in protocol"

        assert re.search(
            r"enum\s+SideEnum\s*\{.*?DRIVERSIDE.*?PASSENGERSIDE.*?\}",
            protocol,
            re.DOTALL,
        ), "Strict mode: SideEnum should be defined in protocol"

        assert re.search(
            r"record\s+DoorPosition\s*\{.*?" r"RowEnum\s+row;.*?" r"SideEnum\s+side;.*?" r"\}",
            protocol,
            re.DOTALL,
        ), "Strict mode: DoorPosition should reference RowEnum and SideEnum types (required fields)"

    def test_non_strict_mode_defaults(self) -> None:
        """Test that non-strict mode uses string for enums and all fields optional."""
        schema_str = """
        directive @vspec(element: VspecElement!) on OBJECT

        enum VspecElement {
            STRUCT
        }

        enum Status {
            ACTIVE
            INACTIVE
        }

        type Vehicle @vspec(element: STRUCT) {
            id: ID!
            make: String!
            model: String
            status: Status
        }

        type Query {
            vehicle: Vehicle
        }
        """
        graphql_schema = build_schema(schema_str)
        annotated_schema = process_schema(schema=graphql_schema, source_map={}, query_document=None)

        result = translate_to_avro_protocol(annotated_schema, "com.example", strict=False)

        protocol = result["Vehicle"]
        # Non-strict mode: enum definitions should not be generated (but may appear in comments)
        assert not re.search(r"^\s*enum\s+Status\s*\{", protocol, re.MULTILINE)
        assert re.search(
            r"protocol\s+Vehicle\s*\{.*?"
            r"record\s+Vehicle\s*\{.*?"
            r"string\?\s+id;.*?"
            r"string\?\s+make;.*?"
            r"string\?\s+model;.*?"
            r"string\?\s+status;.*?"
            r"\}.*?"
            r"\}",
            protocol,
            re.DOTALL,
        ), "Non-strict mode: all fields should be optional, status should be string"


class TestNamespaceHandling:
    def test_per_type_namespace(self) -> None:
        """Test that @vspec directive with namespace in metadata uses per-type namespace."""
        schema_str = """
        directive @vspec(element: VspecElement!, metadata: [KeyValue]) on OBJECT

        input KeyValue {
            key: String!
            value: String!
        }

        enum VspecElement {
            STRUCT
        }

        type Vehicle @vspec(element: STRUCT, metadata: [{key: "namespace", value: "com.vehicle"}]) {
            id: ID!
            make: String!
        }

        type Query {
            vehicle: Vehicle
        }
        """
        graphql_schema = build_schema(schema_str)
        annotated_schema = process_schema(schema=graphql_schema, source_map={}, query_document=None)

        result = translate_to_avro_protocol(annotated_schema, "com.default")

        protocol = result["Vehicle"]
        assert re.search(
            r'@namespace\("com\.vehicle"\)\s*'
            r"protocol\s+Vehicle\s*\{.*?"
            r"record\s+Vehicle\s*\{.*?"
            r"string\?\s+id;.*?"
            r"string\?\s+make;.*?"
            r"\}.*?"
            r"\}",
            protocol,
            re.DOTALL,
        ), "Should use namespace from @vspec metadata in correct protocol structure"

    def test_global_namespace_fallback(self) -> None:
        """Test that types without namespace in metadata use global namespace."""
        schema_str = """
        directive @vspec(element: VspecElement!) on OBJECT

        enum VspecElement {
            STRUCT
        }

        type Vehicle @vspec(element: STRUCT) {
            id: ID!
            make: String!
        }

        type Query {
            vehicle: Vehicle
        }
        """
        graphql_schema = build_schema(schema_str)
        annotated_schema = process_schema(schema=graphql_schema, source_map={}, query_document=None)

        result = translate_to_avro_protocol(annotated_schema, "com.default")

        protocol = result["Vehicle"]
        assert re.search(
            r'@namespace\("com\.default"\)\s*'
            r"protocol\s+Vehicle\s*\{.*?"
            r"record\s+Vehicle\s*\{.*?"
            r"string\?\s+id;.*?"
            r"string\?\s+make;.*?"
            r"\}.*?"
            r"\}",
            protocol,
            re.DOTALL,
        ), "Should use global namespace when no namespace argument in correct protocol structure"

    def test_mixed_namespaces(self) -> None:
        """Test that different types can have different namespaces."""
        schema_str = """
        directive @vspec(element: VspecElement!, metadata: [KeyValue]) on OBJECT

        input KeyValue {
            key: String!
            value: String!
        }

        enum VspecElement {
            STRUCT
        }

        type Vehicle @vspec(element: STRUCT, metadata: [{key: "namespace", value: "com.vehicle"}]) {
            id: ID!
            make: String!
        }

        type Person @vspec(element: STRUCT) {
            name: String!
        }

        type Query {
            vehicle: Vehicle
            person: Person
        }
        """
        graphql_schema = build_schema(schema_str)
        annotated_schema = process_schema(schema=graphql_schema, source_map={}, query_document=None)

        result = translate_to_avro_protocol(annotated_schema, "com.default")

        vehicle_protocol = result["Vehicle"]
        person_protocol = result["Person"]

        assert re.search(
            r'@namespace\("com\.vehicle"\)\s*'
            r"protocol\s+Vehicle\s*\{.*?"
            r"record\s+Vehicle\s*\{.*?"
            r"string\?\s+id;.*?"
            r"string\?\s+make;.*?"
            r"\}.*?"
            r"\}",
            vehicle_protocol,
            re.DOTALL,
        ), "Vehicle should use custom namespace in correct protocol structure"

        assert re.search(
            r'@namespace\("com\.default"\)\s*'
            r"protocol\s+Person\s*\{.*?"
            r"record\s+Person\s*\{.*?"
            r"string\?\s+name;.*?"
            r"\}.*?"
            r"\}",
            person_protocol,
            re.DOTALL,
        ), "Person should use global namespace in correct protocol structure"
