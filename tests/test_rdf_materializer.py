"""Tests for RDF materialization of GraphQL schemas."""

from pathlib import Path
from typing import Any

from graphql import GraphQLSchema, build_schema
from rdflib import Graph
from rdflib.namespace import RDF, SKOS

from s2dm.exporters.rdf_materializer import (
    BUILTIN_SCALARS,
    extract_schema_for_rdf,
    materialize_schema_to_rdf,
    serialize_sorted_ntriples,
    write_rdf_artifacts,
)
from s2dm.exporters.skos import S2DM
from s2dm.exporters.utils.schema_loader import load_schema

NS = "https://example.org/vss#"
NS_ALT = "https://ex.org#"
PREFIX = "ns"


def _subject(graph: Graph, s2dm_type: Any, name_in: str, *, exclude: str | None = None) -> Any:
    """First subject of s2dm_type whose URI contains name_in, optionally excluding exclude."""
    for s in graph.subjects(RDF.type, s2dm_type):
        uri = str(s)
        if name_in in uri and (exclude is None or exclude not in uri):
            return s
    return None


def _cabin_door_schema() -> GraphQLSchema:
    """Test Cabin/Door/Window schema"""

    return build_schema("""
        type Query { cabin: Cabin }

        type Cabin {
            kind: CabinKindEnum
            doors: [Door]
        }

        enum CabinKindEnum {
            SUV
            VAN
        }

        type Door {
            instanceTag: InCabinArea2x2
            isOpen: Boolean
            window: Window
        }

        type Window {
            isTinted: Boolean
        }

        type InCabinArea2x2 {
            row: TwoRowsInCabinEnum
            column: TwoColumnsInCabinEnum
        }

        enum TwoRowsInCabinEnum { ROW1, ROW2 }
        enum TwoColumnsInCabinEnum { DRIVER_SIDE, PASSENGER_SIDE }
    """)


class TestExtractSchemaForRdf:
    """Test RDF schema extraction and related constants."""

    def test_extracts_object_types_with_all_fields(self) -> None:
        """Object types include object refs, lists, scalars."""
        extract = extract_schema_for_rdf(_cabin_door_schema())

        cabin = next(ot for ot in extract.object_types if ot.name == "Cabin")
        assert len(cabin.fields) == 2  # kind, doors
        kind_field = next(f for f in cabin.fields if f.field_fqn == "Cabin.kind")
        assert kind_field.output_type_name == "CabinKindEnum"
        assert kind_field.type_wrapper_pattern == "bare"

        doors_field = next(f for f in cabin.fields if f.field_fqn == "Cabin.doors")
        assert doors_field.output_type_name == "Door"
        assert doors_field.type_wrapper_pattern == "list"

    def test_extracts_enum_types_with_values(self) -> None:
        """Enum types and values are extracted."""
        extract = extract_schema_for_rdf(_cabin_door_schema())

        cabin_enum = next(e for e in extract.enum_types if e.name == "CabinKindEnum")
        assert cabin_enum.values == ["SUV", "VAN"]

    def test_excludes_query_and_mutation(self) -> None:
        """Query, Mutation, Subscription are excluded."""
        extract = extract_schema_for_rdf(_cabin_door_schema())

        type_names = set[str](ot.name for ot in extract.object_types)
        assert "Query" not in type_names and "Mutation" not in type_names

    def test_extracts_interface_types(self) -> None:
        """Interface types with fields are extracted."""
        extract = extract_schema_for_rdf(
            build_schema("""
            type Query { x: Node }
            interface Node { id: ID! name: String }
            type User implements Node { id: ID! name: String }
        """)
        )

        assert len(extract.interface_types) == 1
        node = extract.interface_types[0]
        assert node.name == "Node"
        assert len(node.fields) == 2
        field_fqns = {f.field_fqn for f in node.fields}
        assert "Node.id" in field_fqns
        assert "Node.name" in field_fqns

    def test_extracts_input_object_types(self) -> None:
        """Input object types with fields are extracted."""
        extract = extract_schema_for_rdf(
            build_schema("""
            type Query { x: String }
            input CreateUserInput { name: String! email: String }
        """)
        )

        assert len(extract.input_object_types) == 1
        inp = extract.input_object_types[0]
        assert inp.name == "CreateUserInput"
        assert len(inp.fields) == 2
        patterns = {f.field_fqn: f.type_wrapper_pattern for f in inp.fields}
        assert patterns["CreateUserInput.name"] == "nonNull"
        assert patterns["CreateUserInput.email"] == "bare"

    def test_extracts_union_types(self) -> None:
        """Union types with member types are extracted."""
        extract = extract_schema_for_rdf(
            build_schema("""
            type Query { x: SearchResult }
            union SearchResult = User | Post
            type User { id: ID }
            type Post { id: ID }
        """)
        )

        assert len(extract.union_types) == 1
        union = extract.union_types[0]
        assert union.name == "SearchResult"
        assert set[str](union.member_type_names) == {"User", "Post"}

    def test_all_type_wrapper_patterns(self) -> None:
        """All GraphQL modifier patterns map correctly."""
        extract = extract_schema_for_rdf(
            build_schema("""
            type Query { t: T }
            type T {
                bare: String
                nonNull: String!
                list: [String]
                listOfNonNull: [String!]
                nonNullList: [String]!
                nonNullListOfNonNull: [String!]!
            }
        """)
        )
        t = next(ot for ot in extract.object_types if ot.name == "T")
        patterns = {f.field_fqn: f.type_wrapper_pattern for f in t.fields}
        expected = {
            "T.bare": "bare",
            "T.nonNull": "nonNull",
            "T.list": "list",
            "T.listOfNonNull": "listOfNonNull",
            "T.nonNullList": "nonNullList",
            "T.nonNullListOfNonNull": "nonNullListOfNonNull",
        }
        assert patterns == expected

    def test_builtin_scalars_constant(self) -> None:
        """BUILTIN_SCALARS contains expected GraphQL scalars."""
        for scalar in ("Int", "Float", "String", "Boolean", "ID"):
            assert scalar in BUILTIN_SCALARS


class TestMaterializeSchemaToRdf:
    """Test RDF materialization, serialization, and file output."""

    def test_cabin_door_ontology_triples(self) -> None:
        """Cabin/Door/Window schema produces expected ontology triples."""
        graph = materialize_schema_to_rdf(schema=_cabin_door_schema(), namespace=NS, prefix=PREFIX, language="en")

        cabin = _subject(graph, S2DM.ObjectType, "Cabin", exclude="Cabin.")
        assert cabin is not None
        assert (cabin, RDF.type, SKOS.Concept) in graph
        assert (cabin, RDF.type, S2DM.ObjectType) in graph

        triples = graph.triples((cabin, S2DM.hasField, None))
        cabin_doors = next((o for _, _, o in triples if "Cabin.doors" in str(o)), None)
        assert cabin_doors is not None
        assert "Door" in str(next(graph.objects(cabin_doors, S2DM.hasOutputType)))
        assert S2DM.list in list(graph.objects(cabin_doors, S2DM.usesTypeWrapperPattern))

        cabin_enum = _subject(graph, S2DM.EnumType, "CabinKindEnum")
        assert len(list(graph.objects(cabin_enum, S2DM.hasEnumValue))) == 2

    def test_builtin_scalars_use_s2dm_namespace(self) -> None:
        """Built-in scalars resolve to s2dm:Int, s2dm:Boolean, etc."""
        schema = "type Query { t: T } type T { id: ID! name: String count: Int ratio: Float flag: Boolean }"
        graph = materialize_schema_to_rdf(schema=build_schema(schema), namespace=NS, prefix=PREFIX)
        field_uri = _subject(graph, S2DM.Field, "T.id")
        output_type = str(next(graph.objects(field_uri, S2DM.hasOutputType)))
        assert "s2dm" in output_type
        assert "ID" in output_type

    def test_interface_input_union_materialized(self) -> None:
        """Interface, InputObject, and Union types produce correct triples."""
        schema = (
            "type Query { x: SearchResult } interface Node { id: ID! } union SearchResult = User | Post "
            "input CreateInput { name: String } type User implements Node { id: ID! } "
            "type Post implements Node { id: ID! }"
        )
        graph = materialize_schema_to_rdf(schema=build_schema(schema), namespace=NS, prefix=PREFIX)

        assert _subject(graph, S2DM.InterfaceType, "Node") is not None
        assert _subject(graph, S2DM.InputObjectType, "CreateInput") is not None
        union = _subject(graph, S2DM.UnionType, "SearchResult")
        assert len(list(graph.objects(union, S2DM.hasUnionMember))) == 2

    def test_custom_scalar_uses_concept_namespace(self) -> None:
        """Custom scalars use concept namespace."""
        schema = "type Query { t: T } scalar DateTime type T { at: DateTime }"
        graph = materialize_schema_to_rdf(schema=build_schema(schema), namespace=NS, prefix=PREFIX)
        field_uri = _subject(graph, S2DM.Field, "T.at")
        output_type = str(next(graph.objects(field_uri, S2DM.hasOutputType)))
        assert "DateTime" in output_type
        assert "vss" in output_type

    def test_output_is_sorted(self) -> None:
        """Serialized n-triples are lexicographically sorted."""
        graph = materialize_schema_to_rdf(schema=_cabin_door_schema(), namespace=NS, prefix=PREFIX)
        lines = [line for line in serialize_sorted_ntriples(graph).strip().split("\n") if line.strip()]
        assert lines == sorted(lines)

    def test_deterministic_across_runs(self) -> None:
        """Same schema produces same sorted output."""
        schema = _cabin_door_schema()
        g1 = materialize_schema_to_rdf(schema=schema, namespace=NS_ALT, prefix=PREFIX)
        g2 = materialize_schema_to_rdf(schema=schema, namespace=NS_ALT, prefix=PREFIX)
        assert serialize_sorted_ntriples(g1) == serialize_sorted_ntriples(g2)

    def test_ends_with_newline(self) -> None:
        """Output ends with newline."""
        schema = "type Query { x: String } type T { f: String }"
        graph = materialize_schema_to_rdf(schema=build_schema(schema), namespace=NS_ALT, prefix=PREFIX)
        assert serialize_sorted_ntriples(graph).endswith("\n")

    def test_writes_nt_and_ttl(self, tmp_path: Path) -> None:
        """write_rdf_artifacts creates .nt and .ttl files."""
        graph = materialize_schema_to_rdf(schema=_cabin_door_schema(), namespace=NS, prefix=PREFIX)
        write_rdf_artifacts(graph, tmp_path, base_name="schema")

        assert (tmp_path / "schema.nt").exists()
        assert (tmp_path / "schema.ttl").exists()
        nt = (tmp_path / "schema.nt").read_text()
        assert "skos:Concept" in nt or "Concept" in nt  # format varies: prefix or full URI
        assert "hasField" in nt and "hasOutputType" in nt
        ttl = (tmp_path / "schema.ttl").read_text()
        assert "@prefix" in ttl and "skos:" in ttl and "s2dm:" in ttl

    def test_real_schema_materializes(self) -> None:
        """Real schema from files materializes successfully."""
        data = Path(__file__).parent / "data"
        spec_dir, base = data / "spec", data / "base.graphql"
        assert spec_dir.exists() and base.exists()

        graph = materialize_schema_to_rdf(schema=load_schema([spec_dir, base]), namespace=NS, prefix=PREFIX)
        nt = serialize_sorted_ntriples(graph)
        assert len(nt.strip().split("\n")) > 10
        assert "Vehicle" in nt and "Engine" in nt
