import pytest
from graphql import GraphQLScalarType, GraphQLSchema, build_schema
from rdflib import XSD, Literal
from rdflib.namespace import SH

from s2dm.exporters.shacl import GRAPHQL_SCALAR_TO_XSD, get_xsd_datatype, translate_to_shacl
from s2dm.exporters.utils.annotated_schema import AnnotatedSchema


class TestGetXsdDatatype:
    """Test the GraphQL scalar to XSD datatype mapping."""

    @pytest.mark.parametrize(
        "scalar_name,expected_xsd_fragment",
        [
            ("Int", "integer"),
            ("Float", "float"),
            ("String", "string"),
            ("Boolean", "boolean"),
            ("ID", "string"),
            ("Int8", "byte"),
            ("UInt8", "unsignedByte"),
            ("Int16", "short"),
            ("UInt16", "unsignedShort"),
            ("UInt32", "unsignedInt"),
            ("Int64", "long"),
            ("UInt64", "unsignedLong"),
        ],
    )
    def test_known_scalars_map_to_expected_xsd_type(self, scalar_name: str, expected_xsd_fragment: str) -> None:
        """Each known GraphQL scalar (built-in and custom integer widths) maps to the correct XSD datatype."""
        scalar = GraphQLScalarType(name=scalar_name)
        assert get_xsd_datatype(scalar) == XSD[expected_xsd_fragment]

    def test_unknown_scalar_falls_back_to_string(self) -> None:
        """A scalar not present in the mapping falls back to xsd:string."""
        scalar = GraphQLScalarType(name="SomeCustomScalar")
        assert get_xsd_datatype(scalar) == XSD.string

    def test_custom_integer_scalars_are_not_string(self) -> None:
        """Regression guard: custom integer-width scalars must not fall back to xsd:string."""
        for scalar_name in ("Int8", "UInt8", "Int16", "UInt16", "UInt32", "Int64", "UInt64"):
            assert GRAPHQL_SCALAR_TO_XSD[scalar_name] != "string"


class TestTranslateToShaclScalarDatatypes:
    """Integration test: translate_to_shacl emits the correct sh:datatype for custom integer scalars."""

    def _build_annotated_schema(self) -> GraphQLSchema:
        return build_schema("""
            scalar Int8
            scalar UInt8
            scalar Int16
            scalar UInt16
            scalar UInt32
            scalar Int64
            scalar UInt64

            type Vehicle {
                gear: Int8
                brightness: UInt8
                angle: Int16
                position: UInt16
                odometer: UInt32
                mileage: Int64
                totalDistance: UInt64
            }

            type Query {
                vehicle: Vehicle
            }
        """)

    def test_custom_scalar_fields_emit_correct_sh_datatype(self) -> None:
        schema = self._build_annotated_schema()
        annotated_schema = AnnotatedSchema(schema=schema)

        graph = translate_to_shacl(
            annotated_schema,
            "http://ex/shapes#",
            "shapes",
            "http://ex/model#",
            "model",
        )

        expected_field_to_datatype = {
            "gear": XSD.byte,
            "brightness": XSD.unsignedByte,
            "angle": XSD.short,
            "position": XSD.unsignedShort,
            "odometer": XSD.unsignedInt,
            "mileage": XSD.long,
            "totalDistance": XSD.unsignedLong,
        }

        for field_name, expected_datatype in expected_field_to_datatype.items():
            datatypes = {
                dtype
                for property_node in graph.subjects(SH.name, Literal(field_name))
                for dtype in graph.objects(property_node, SH.datatype)
            }
            assert datatypes == {expected_datatype}, f"Field '{field_name}' has datatypes {datatypes}"


if __name__ == "__main__":
    pytest.main([__file__])
