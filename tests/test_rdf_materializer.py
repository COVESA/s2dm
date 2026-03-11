"""Tests for RDF materialization of GraphQL schemas (split SKOS + data graph)."""

from pathlib import Path
from typing import Any

from graphql import GraphQLSchema, build_schema
from rdflib import Graph
from rdflib.namespace import RDF, SKOS

from s2dm.exporters.rdf_materializer import (
    BUILTIN_SCALARS,
    extract_schema_for_rdf,
    materialize_data_graph,
    materialize_skos_graph,
    serialize_sorted_ntriples,
    write_rdf_artifacts,
)
from s2dm.exporters.skos import S2DM
from s2dm.exporters.utils.schema_loader import load_schema

NS = "https://example.org/vss#"
NS_ALT = "https://ex.org#"
PREFIX = "ns"


def _subject(graph: Graph, rdf_type: Any, name_in: str, *, exclude: str | None = None) -> Any:
    """First subject of rdf_type whose URI contains name_in, optionally excluding exclude."""
    for s in graph.subjects(RDF.type, rdf_type):
        uri = str(s)
        if name_in in uri and (exclude is None or exclude not in uri):
            return s
    return None


def _cabin_door_schema() -> GraphQLSchema:
    """Test Cabin/Door/Window schema."""
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


class TestMaterializeSkosGraph:
    """Test SKOS graph materialization."""

    def test_concepts_have_skos_type_and_label(self) -> None:
        """All concepts are skos:Concept with prefLabel."""
        extract = extract_schema_for_rdf(_cabin_door_schema())
        graph = materialize_skos_graph(extract, NS, PREFIX)

        cabin = _subject(graph, SKOS.Concept, "Cabin", exclude="Cabin.")
        assert cabin is not None
        labels = list(graph.objects(cabin, SKOS.prefLabel))
        assert any("Cabin" in str(label) for label in labels)

    def test_skos_graph_has_no_s2dm_types(self) -> None:
        """SKOS graph must not contain s2dm ontology type triples."""
        extract = extract_schema_for_rdf(_cabin_door_schema())
        graph = materialize_skos_graph(extract, NS, PREFIX)

        for s2dm_type in (S2DM.ObjectType, S2DM.Field, S2DM.EnumType, S2DM.EnumValue):
            assert len(list(graph.subjects(RDF.type, s2dm_type))) == 0

    def test_object_collection_has_members(self) -> None:
        """ObjectConcepts collection contains object types."""
        extract = extract_schema_for_rdf(_cabin_door_schema())
        graph = materialize_skos_graph(extract, NS, PREFIX)

        obj_coll = _subject(graph, SKOS.Collection, "ObjectConcepts")
        assert obj_coll is not None
        members = list(graph.objects(obj_coll, SKOS.member))
        member_uris = {str(m) for m in members}
        assert any("Cabin" in u for u in member_uris)

    def test_field_collection_has_members(self) -> None:
        """FieldConcepts collection contains field concepts."""
        extract = extract_schema_for_rdf(_cabin_door_schema())
        graph = materialize_skos_graph(extract, NS, PREFIX)

        field_coll = _subject(graph, SKOS.Collection, "FieldConcepts")
        assert field_coll is not None
        members = list(graph.objects(field_coll, SKOS.member))
        member_uris = {str(m) for m in members}
        assert any("Cabin.doors" in u for u in member_uris)

    def test_enum_collection_created(self) -> None:
        """Per-enum collections are created for enum types."""
        extract = extract_schema_for_rdf(_cabin_door_schema())
        graph = materialize_skos_graph(extract, NS, PREFIX)

        enum_coll = _subject(graph, SKOS.Collection, "CabinKindEnum")
        assert enum_coll is not None
        members = list(graph.objects(enum_coll, SKOS.member))
        assert len(members) == 2

    def test_note_added_for_description(self) -> None:
        """Concepts with descriptions get skos:note."""
        schema = build_schema("""
            type Query { t: T }
            \"\"\"A described type.\"\"\"
            type T { f: String }
        """)
        extract = extract_schema_for_rdf(schema)
        graph = materialize_skos_graph(extract, NS, PREFIX)

        t_concept = _subject(graph, SKOS.Concept, "#T", exclude="T.")
        assert t_concept is not None
        notes = list(graph.objects(t_concept, SKOS.note))
        assert len(notes) == 1
        assert "inherited from the description" in str(notes[0])

    def test_interface_and_union_collections(self) -> None:
        """Interface and union types get their own collections."""
        schema = build_schema("""
            type Query { x: SearchResult }
            interface Node { id: ID! }
            union SearchResult = User | Post
            type User implements Node { id: ID! }
            type Post implements Node { id: ID! }
        """)
        extract = extract_schema_for_rdf(schema)
        graph = materialize_skos_graph(extract, NS, PREFIX)

        iface_coll = _subject(graph, SKOS.Collection, "InterfaceConcepts")
        assert iface_coll is not None
        union_coll = _subject(graph, SKOS.Collection, "UnionConcepts")
        assert union_coll is not None


class TestMaterializeDataGraph:
    """Test s2dm ontology data graph materialization."""

    def test_object_type_triples(self) -> None:
        """Object types are typed as s2dm:ObjectType with hasField."""
        extract = extract_schema_for_rdf(_cabin_door_schema())
        graph = materialize_data_graph(extract, NS, PREFIX)

        cabin = _subject(graph, S2DM.ObjectType, "Cabin", exclude="Cabin.")
        assert cabin is not None
        fields = list(graph.objects(cabin, S2DM.hasField))
        field_uris = {str(f) for f in fields}
        assert any("Cabin.doors" in u for u in field_uris)

    def test_field_has_output_type_and_wrapper(self) -> None:
        """Fields have hasOutputType and usesTypeWrapperPattern."""
        extract = extract_schema_for_rdf(_cabin_door_schema())
        graph = materialize_data_graph(extract, NS, PREFIX)

        cabin = _subject(graph, S2DM.ObjectType, "Cabin", exclude="Cabin.")
        cabin_doors = next(
            (o for _, _, o in graph.triples((cabin, S2DM.hasField, None)) if "Cabin.doors" in str(o)),
            None,
        )
        assert cabin_doors is not None
        assert "Door" in str(next(graph.objects(cabin_doors, S2DM.hasOutputType)))
        assert S2DM.list in list(graph.objects(cabin_doors, S2DM.usesTypeWrapperPattern))

    def test_enum_type_and_values(self) -> None:
        """Enum types have hasEnumValue pointing to EnumValue instances."""
        extract = extract_schema_for_rdf(_cabin_door_schema())
        graph = materialize_data_graph(extract, NS, PREFIX)

        cabin_enum = _subject(graph, S2DM.EnumType, "CabinKindEnum")
        assert cabin_enum is not None
        values = list(graph.objects(cabin_enum, S2DM.hasEnumValue))
        assert len(values) == 2

    def test_data_graph_has_no_skos_concepts(self) -> None:
        """Data graph must not contain skos:Concept triples."""
        extract = extract_schema_for_rdf(_cabin_door_schema())
        graph = materialize_data_graph(extract, NS, PREFIX)

        assert len(list(graph.subjects(RDF.type, SKOS.Concept))) == 0

    def test_builtin_scalars_use_s2dm_namespace(self) -> None:
        """Built-in scalars resolve to s2dm:Int, s2dm:Boolean, etc."""
        schema_str = "type Query { t: T } " "type T { id: ID! name: String count: Int ratio: Float flag: Boolean }"
        extract = extract_schema_for_rdf(build_schema(schema_str))
        graph = materialize_data_graph(extract, NS, PREFIX)

        field_uri = _subject(graph, S2DM.Field, "T.id")
        output_type = str(next(graph.objects(field_uri, S2DM.hasOutputType)))
        assert "s2dm" in output_type and "ID" in output_type

    def test_custom_scalar_uses_concept_namespace(self) -> None:
        """Custom scalars use concept namespace."""
        schema_str = "type Query { t: T } scalar DateTime type T { at: DateTime }"
        extract = extract_schema_for_rdf(build_schema(schema_str))
        graph = materialize_data_graph(extract, NS, PREFIX)

        field_uri = _subject(graph, S2DM.Field, "T.at")
        output_type = str(next(graph.objects(field_uri, S2DM.hasOutputType)))
        assert "DateTime" in output_type and "vss" in output_type

    def test_interface_input_union_materialized(self) -> None:
        """Interface, InputObject, and Union types produce correct triples."""
        schema_str = (
            "type Query { x: SearchResult } interface Node { id: ID! } "
            "union SearchResult = User | Post "
            "input CreateInput { name: String } "
            "type User implements Node { id: ID! } "
            "type Post implements Node { id: ID! }"
        )
        extract = extract_schema_for_rdf(build_schema(schema_str))
        graph = materialize_data_graph(extract, NS, PREFIX)

        assert _subject(graph, S2DM.InterfaceType, "Node") is not None
        assert _subject(graph, S2DM.InputObjectType, "CreateInput") is not None
        union = _subject(graph, S2DM.UnionType, "SearchResult")
        assert len(list(graph.objects(union, S2DM.hasUnionMember))) == 2


class TestSerializationAndOutput:
    """Test serialization, sorting, and file output."""

    def test_output_is_sorted(self) -> None:
        """Serialized n-triples are lexicographically sorted."""
        extract = extract_schema_for_rdf(_cabin_door_schema())
        graph = materialize_data_graph(extract, NS, PREFIX)
        lines = [line for line in serialize_sorted_ntriples(graph).strip().split("\n") if line.strip()]
        assert lines == sorted(lines)

    def test_deterministic_across_runs(self) -> None:
        """Same schema produces same sorted output."""
        schema = _cabin_door_schema()
        extract = extract_schema_for_rdf(schema)
        g1 = materialize_data_graph(extract, NS_ALT, PREFIX)
        g2 = materialize_data_graph(extract, NS_ALT, PREFIX)
        assert serialize_sorted_ntriples(g1) == serialize_sorted_ntriples(g2)

    def test_ends_with_newline(self) -> None:
        """Output ends with newline."""
        schema_str = "type Query { x: String } type T { f: String }"
        extract = extract_schema_for_rdf(build_schema(schema_str))
        graph = materialize_data_graph(extract, NS_ALT, PREFIX)
        assert serialize_sorted_ntriples(graph).endswith("\n")

    def test_writes_skos_and_data_graph_files(self, tmp_path: Path) -> None:
        """write_rdf_artifacts creates .nt and .ttl files for both graphs."""
        extract = extract_schema_for_rdf(_cabin_door_schema())
        skos_graph = materialize_skos_graph(extract, NS, PREFIX)
        data_graph = materialize_data_graph(extract, NS, PREFIX)

        write_rdf_artifacts(skos_graph, tmp_path, base_name="skos")
        write_rdf_artifacts(data_graph, tmp_path, base_name="data_graph")

        assert (tmp_path / "skos.nt").exists()
        assert (tmp_path / "skos.ttl").exists()
        assert (tmp_path / "data_graph.nt").exists()
        assert (tmp_path / "data_graph.ttl").exists()

        skos_nt = (tmp_path / "skos.nt").read_text()
        assert "Concept" in skos_nt
        assert "prefLabel" in skos_nt or "skos" in skos_nt

        data_nt = (tmp_path / "data_graph.nt").read_text()
        assert "hasField" in data_nt and "hasOutputType" in data_nt

        skos_ttl = (tmp_path / "skos.ttl").read_text()
        assert "@prefix" in skos_ttl and "skos:" in skos_ttl

    def test_real_schema_materializes(self) -> None:
        """Real schema from files materializes successfully."""
        data = Path(__file__).parent / "data"
        spec_dir, base = data / "spec", data / "base.graphql"
        assert spec_dir.exists() and base.exists()

        schema = load_schema([spec_dir, base])
        extract = extract_schema_for_rdf(schema)
        skos_graph = materialize_skos_graph(extract, NS, PREFIX)
        data_graph = materialize_data_graph(extract, NS, PREFIX)

        skos_nt = serialize_sorted_ntriples(skos_graph)
        assert len(skos_nt.strip().split("\n")) > 10
        assert "Vehicle" in skos_nt

        data_nt = serialize_sorted_ntriples(data_graph)
        assert len(data_nt.strip().split("\n")) > 10
        assert "Vehicle" in data_nt and "Engine" in data_nt
