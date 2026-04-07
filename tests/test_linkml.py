"""Tests for the LinkML exporter."""

from typing import Any, cast

from graphql import build_schema
from linkml_runtime.loaders import yaml_loader

from s2dm.exporters.linkml import translate_to_linkml
from s2dm.exporters.utils.naming_config import NamingConventionConfig, ValidationMode
from s2dm.exporters.utils.schema_loader import process_schema

LINKML_SCHEMA_ID = "https://covesa.global/s2dm"
LINKML_SCHEMA_NAME = "TestSchema"
LINKML_DEFAULT_PREFIX = "s2dm"
LINKML_DEFAULT_PREFIX_URL = "https://covesa.global/s2dm"


def _transform_to_schema_dict(
    schema_str: str,
    naming_config: NamingConventionConfig | None = None,
    root_type: str | None = None,
) -> dict[str, Any]:
    graphql_schema = build_schema(schema_str)
    annotated_schema = process_schema(
        schema=graphql_schema,
        source_map={},
        naming_config=naming_config,
        query_document=None,
        root_type=root_type,
        expanded_instances=False,
    )
    result = translate_to_linkml(
        annotated_schema,
        LINKML_SCHEMA_ID,
        LINKML_SCHEMA_NAME,
        LINKML_DEFAULT_PREFIX,
        LINKML_DEFAULT_PREFIX_URL,
    )
    return cast(dict[str, Any], yaml_loader.load_as_dict(result))


class TestBasicTransformation:
    def test_basic_schema_structure(self) -> None:
        """Test that basic LinkML schema structure is generated correctly."""
        schema_str = """
            type Query { vehicle: Vehicle }
            type Vehicle { id: ID!, make: String! }
        """

        schema = _transform_to_schema_dict(schema_str)

        assert schema["name"] == LINKML_SCHEMA_NAME
        assert schema["id"] == LINKML_SCHEMA_ID
        assert schema["default_prefix"] == LINKML_DEFAULT_PREFIX
        assert schema["prefixes"][LINKML_DEFAULT_PREFIX] == LINKML_DEFAULT_PREFIX_URL
        assert "linkml:types" in schema["imports"]
        assert "Query" not in schema["classes"]
        assert "Vehicle" in schema["classes"]

    def test_root_operation_types_are_excluded(self) -> None:
        """Test that GraphQL root operation types are not emitted as LinkML classes."""
        schema_str = """
            type Query { vehicle: Vehicle }
            type Mutation { updateVehicle: Vehicle }
            type Subscription { vehicleUpdated: Vehicle }

            type Vehicle {
                vehicleKey: ID!
            }
        """

        schema = _transform_to_schema_dict(schema_str)

        assert "Query" not in schema["classes"]
        assert "Mutation" not in schema["classes"]
        assert "Subscription" not in schema["classes"]
        assert "Vehicle" in schema["classes"]

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

        schema = _transform_to_schema_dict(schema_str)
        vehicle = schema["classes"]["Vehicle"]

        assert "id" in vehicle["attributes"]
        assert "make" in vehicle["attributes"]
        assert "model" in vehicle["attributes"]
        assert "year" in vehicle["attributes"]

        assert vehicle["attributes"]["id"]["range"] == "string"
        assert vehicle["attributes"]["id"]["required"] is True
        assert vehicle["attributes"]["make"]["required"] is True
        assert "required" not in vehicle["attributes"]["model"]
        assert vehicle["attributes"]["year"]["range"] == "integer"

    def test_query_object_types_are_marked_as_tree_roots(self) -> None:
        """Test that object types returned directly from Query are marked as tree roots."""
        schema_str = """
            type Query {
                vehicle: Vehicle
                garage: Garage
                status: String
            }

            type Vehicle {
                id: ID!
                wheel: Wheel
            }

            type Garage {
                id: ID!
            }

            type Wheel {
                diameter: Int
            }
        """

        schema = _transform_to_schema_dict(schema_str)

        assert schema["classes"]["Vehicle"]["tree_root"] is True
        assert schema["classes"]["Garage"]["tree_root"] is True
        assert "tree_root" not in schema["classes"]["Wheel"]

    def test_root_type_filtered_object_is_marked_as_tree_root(self) -> None:
        """Test that root_type filtering leaves only the selected object type as tree root."""
        schema_str = """
            type Query {
                vehicle: Vehicle
                garage: Garage
            }

            type Vehicle {
                id: ID!
                wheel: Wheel
            }

            type Garage {
                id: ID!
            }

            type Wheel {
                diameter: Int
            }
        """

        schema = _transform_to_schema_dict(schema_str, root_type="Vehicle")

        assert schema["classes"]["Vehicle"]["tree_root"] is True
        assert "Garage" not in schema["classes"]
        assert "tree_root" not in schema["classes"]["Wheel"]

    def test_id_typed_fields_are_marked_as_identifiers(self) -> None:
        """Test that GraphQL ID fields are marked as LinkML identifiers."""
        schema_str = """
            type Query { vehicle: Vehicle }

            type Vehicle {
                vehicleKey: ID!
                externalRef: String!
            }
        """

        schema = _transform_to_schema_dict(schema_str)
        vehicle_attributes = schema["classes"]["Vehicle"]["attributes"]

        assert vehicle_attributes["vehicleKey"]["range"] == "string"
        assert vehicle_attributes["vehicleKey"]["required"] is True
        assert vehicle_attributes["vehicleKey"]["identifier"] is True
        assert "identifier" not in vehicle_attributes["externalRef"]


class TestGraphQLTypeHandling:
    def test_enum_types(self) -> None:
        """Test that GraphQL enum types are correctly transformed."""
        schema_str = """
            type Query { vehicle: Vehicle }

            enum FuelType {
                GASOLINE
                DIESEL
                ELECTRIC
            }

            type Vehicle {
                fuelType: FuelType
            }
        """

        schema = _transform_to_schema_dict(schema_str)

        assert "FuelType" in schema["enums"]
        assert set(schema["enums"]["FuelType"]["permissible_values"].keys()) == {"GASOLINE", "DIESEL", "ELECTRIC"}
        assert schema["classes"]["Vehicle"]["attributes"]["fuelType"]["range"] == "FuelType"

    def test_union_types(self) -> None:
        """Test that GraphQL union types are correctly transformed."""
        schema_str = """
            type Query { vehicle: Vehicle }

            union Transport = Car | Truck

            type Car { id: ID!, doors: Int! }
            type Truck { id: ID!, payloadCapacity: Float! }

            type Vehicle {
                transport: Transport
            }
        """

        schema = _transform_to_schema_dict(schema_str)
        transport_slot = schema["classes"]["Vehicle"]["attributes"]["transport"]

        assert "any_of" in transport_slot
        assert {value["range"] for value in transport_slot["any_of"]} == {"Car", "Truck"}

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

        schema = _transform_to_schema_dict(schema_str)

        assert schema["classes"]["Vehicle"]["abstract"] is True
        assert schema["classes"]["Car"]["is_a"] == "Vehicle"
        assert schema["classes"]["Car"]["attributes"]["doors"]["range"] == "integer"

    def test_custom_scalar_types(self) -> None:
        """Test that custom scalar types are correctly transformed."""
        schema_str = """
            scalar DateTime

            type Query { vehicle: Vehicle }
            type Vehicle { builtAt: DateTime }
        """

        schema = _transform_to_schema_dict(schema_str)

        assert "DateTime" in schema["types"]
        assert schema["types"]["DateTime"]["base"] == "string"
        assert schema["classes"]["Vehicle"]["attributes"]["builtAt"]["range"] == "DateTime"


class TestDirectiveMapping:
    def test_range_cardinality_no_duplicates_and_metadata(self) -> None:
        """Test directive mapping to LinkML slot constraints and annotations."""
        schema_str = """
            directive @range(min: Float, max: Float) on FIELD_DEFINITION
            directive @cardinality(min: Int, max: Int) on FIELD_DEFINITION
            directive @noDuplicates on FIELD_DEFINITION
            directive @metadata(comment: String, vssType: String) on FIELD_DEFINITION | OBJECT

            type Query { vehicle: Vehicle }

            type Vehicle @metadata(comment: "Vehicle entity", vssType: "branch") {
                speed: Float @range(min: 0, max: 250)
                tags: [String]
                    @cardinality(min: 1, max: 5)
                    @noDuplicates
                    @metadata(comment: "Tag values", vssType: "attribute")
            }
        """

        schema = _transform_to_schema_dict(schema_str)
        vehicle = schema["classes"]["Vehicle"]
        speed_slot = vehicle["attributes"]["speed"]
        tags_slot = vehicle["attributes"]["tags"]

        assert "description" not in vehicle
        assert vehicle["annotations"]["s2dm_metadata_comment"] == "Vehicle entity"
        assert vehicle["annotations"]["s2dm_metadata_vssType"] == "branch"

        assert speed_slot["minimum_value"] == 0
        assert speed_slot["maximum_value"] == 250

        assert tags_slot["multivalued"] is True
        assert tags_slot["minimum_cardinality"] == 1
        assert tags_slot["maximum_cardinality"] == 5
        assert tags_slot["list_elements_unique"] is True
        assert "description" not in tags_slot
        assert tags_slot["annotations"]["s2dm_metadata_comment"] == "Tag values"
        assert tags_slot["annotations"]["s2dm_metadata_vssType"] == "attribute"


class TestUnitMapping:
    def test_qudt_unit_reference_mapping(self) -> None:
        """Test that QUDT unit references are mapped to LinkML slot units."""
        schema_str = '''
            directive @reference(uri: String, versionTag: String) on ENUM | ENUM_VALUE

            type Query { vehicle: Vehicle }

            enum TransmittanceDensityUnitEnum
                @reference(uri: "http://qudt.org/vocab/quantitykind/TransmittanceDensity", versionTag: "v3.1.8") {
                """Unitless"""
                UNITLESS @reference(uri: "http://qudt.org/vocab/unit/UNITLESS", versionTag: "v3.1.8")
            }

            type Vehicle {
                transmittanceDensity(unit: TransmittanceDensityUnitEnum = UNITLESS): Float
            }
        '''

        schema = _transform_to_schema_dict(schema_str)
        unit = schema["classes"]["Vehicle"]["attributes"]["transmittanceDensity"]["unit"]

        assert unit["symbol"] == "UNITLESS"
        assert unit["exact_mappings"] == ["http://qudt.org/vocab/unit/UNITLESS"]
        assert unit["has_quantity_kind"] == "http://qudt.org/vocab/quantitykind/TransmittanceDensity"

    def test_qudt_unit_reference_mapping_with_enum_value_renaming(self) -> None:
        """Test QUDT unit mapping when enum value naming conversion changes enum keys."""
        schema_str = """
            directive @reference(uri: String, versionTag: String) on ENUM | ENUM_VALUE

            type Query { vehicle: Vehicle }

            enum VelocityUnitEnum @reference(uri: "http://qudt.org/vocab/quantitykind/Velocity", versionTag: "v3.1.8") {
                KILOM_PER_HR @reference(uri: "http://qudt.org/vocab/unit/KiloM-PER-HR", versionTag: "v3.1.8")
            }

            type Vehicle {
                speed(unit: VelocityUnitEnum = KILOM_PER_HR): Float
            }
        """

        naming_config = NamingConventionConfig.model_validate(
            {"enumValue": "snake_case", "instanceTag": "snake_case"},
            context={"mode": ValidationMode.CONVERSION},
        )

        schema = _transform_to_schema_dict(schema_str, naming_config=naming_config)
        unit = schema["classes"]["Vehicle"]["attributes"]["speed"]["unit"]

        assert unit["symbol"] == "kilom_per_hr"
        assert unit["exact_mappings"] == ["http://qudt.org/vocab/unit/KiloM-PER-HR"]
        assert unit["has_quantity_kind"] == "http://qudt.org/vocab/quantitykind/Velocity"

    def test_input_types_are_excluded_from_linkml_classes(self) -> None:
        """Test that GraphQL input object types are not emitted as LinkML classes."""
        schema_str = """
            directive @range(min: Float, max: Float) on FIELD_DEFINITION | INPUT_FIELD_DEFINITION
            directive @cardinality(min: Int, max: Int) on FIELD_DEFINITION | INPUT_FIELD_DEFINITION
            directive @noDuplicates on FIELD_DEFINITION | INPUT_FIELD_DEFINITION
            directive @metadata(comment: String, vssType: String) on
                FIELD_DEFINITION | INPUT_FIELD_DEFINITION | OBJECT | INTERFACE | INPUT_OBJECT

            interface BaseEntity @metadata(comment: "Base interface", vssType: "interface") {
                id: ID!
            }

            input VehicleFilter @metadata(comment: "Filter input", vssType: "input") {
                tags: [String]
                    @cardinality(min: 1, max: 3)
                    @noDuplicates
                    @metadata(comment: "Input tags", vssType: "attribute")
                confidence: Float @range(min: 0.1, max: 0.9)
            }

            type Query {
                vehicle(filter: VehicleFilter): Vehicle
            }

            type Vehicle implements BaseEntity {
                id: ID!
            }
        """

        schema = _transform_to_schema_dict(schema_str)
        base_entity = schema["classes"]["BaseEntity"]

        assert "VehicleFilter" not in schema["classes"]
        assert base_entity["annotations"]["s2dm_metadata_comment"] == "Base interface"
        assert base_entity["annotations"]["s2dm_metadata_vssType"] == "interface"
