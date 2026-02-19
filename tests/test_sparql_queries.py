"""Tests for SPARQL query module for RDF-materialized GraphQL schemas."""

from pathlib import Path

import pytest
from graphql import build_schema
from rdflib import Graph

from s2dm.exporters.rdf_materializer import (
    materialize_schema_to_rdf,
    serialize_sorted_ntriples,
)
from s2dm.exporters.sparql_queries import (
    QUERIES,
    format_results_as_table,
    get_query_description,
    get_query_names,
    load_rdf_graph,
    run_query,
)

NS = "https://example.org/test#"
PREFIX = "ns"


def _cabin_door_graph() -> Graph:
    """Create a materialized RDF graph from a Cabin/Door/Window schema."""
    schema = build_schema("""
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
            isOpen: Boolean
            window: Window
        }

        type Window {
            isTinted: Boolean
        }
    """)
    return materialize_schema_to_rdf(schema=schema, namespace=NS, prefix=PREFIX)


class TestQueryRegistry:
    """Tests for the SPARQL query registry."""

    def test_has_three_queries(self) -> None:
        """Registry contains exactly 3 predefined queries."""
        assert len(QUERIES) == 3

    def test_get_query_names(self) -> None:
        """get_query_names returns sorted list."""
        names = get_query_names()
        assert names == sorted(names)
        assert "fields-outputting-enum" in names
        assert "object-types-with-fields" in names
        assert "list-type-fields" in names

    def test_get_query_description(self) -> None:
        """get_query_description returns a non-empty string."""
        for name in get_query_names():
            desc = get_query_description(name)
            assert isinstance(desc, str)
            assert len(desc) > 0

    def test_unknown_query_raises(self) -> None:
        """Accessing unknown query name raises KeyError."""
        with pytest.raises(KeyError):
            get_query_description("nonexistent-query")


class TestLoadRdfGraph:
    """Tests for loading RDF graphs from files."""

    def test_load_nt_file(self, tmp_path: Path) -> None:
        """Load graph from n-triples file."""
        graph = _cabin_door_graph()
        nt_path = tmp_path / "test.nt"
        nt_path.write_text(serialize_sorted_ntriples(graph), encoding="utf-8")

        loaded = load_rdf_graph(nt_path)
        assert len(loaded) > 0

    def test_load_ttl_file(self, tmp_path: Path) -> None:
        """Load graph from turtle file."""
        graph = _cabin_door_graph()
        ttl_path = tmp_path / "test.ttl"
        graph.serialize(destination=str(ttl_path), format="turtle")

        loaded = load_rdf_graph(ttl_path)
        assert len(loaded) > 0

    def test_unsupported_extension_raises(self, tmp_path: Path) -> None:
        """Unsupported file extension raises ValueError."""
        bad_path = tmp_path / "test.rdf"
        bad_path.write_text("<rdf/>", encoding="utf-8")

        with pytest.raises(ValueError, match="Unsupported RDF file extension"):
            load_rdf_graph(bad_path)

    def test_load_jsonld_file(self, tmp_path: Path) -> None:
        """Load graph from JSON-LD file."""
        graph = _cabin_door_graph()
        jsonld_path = tmp_path / "test.jsonld"
        graph.serialize(destination=str(jsonld_path), format="json-ld")

        loaded = load_rdf_graph(jsonld_path)
        assert len(loaded) > 0

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """Non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_rdf_graph(tmp_path / "does_not_exist.nt")


class TestRunQuery:
    """Tests for executing SPARQL queries."""

    def test_fields_outputting_enum(self) -> None:
        """fields-outputting-enum finds Cabin.kind -> CabinKindEnum."""
        graph = _cabin_door_graph()
        results = run_query(graph, "fields-outputting-enum")

        assert len(results) > 0
        field_uris = [r["field"] for r in results]
        assert any("Cabin.kind" in uri for uri in field_uris)
        enum_uris = [r["enumType"] for r in results]
        assert any("CabinKindEnum" in uri for uri in enum_uris)

    def test_object_types_with_fields(self) -> None:
        """object-types-with-fields lists Cabin, Door, Window with fields."""
        graph = _cabin_door_graph()
        results = run_query(graph, "object-types-with-fields")

        type_names = {r["objectType"] for r in results}
        assert any("Cabin" in t for t in type_names)
        assert any("Door" in t for t in type_names)
        assert any("Window" in t for t in type_names)

    def test_list_type_fields(self) -> None:
        """list-type-fields finds Cabin.doors (list wrapper)."""
        graph = _cabin_door_graph()
        results = run_query(graph, "list-type-fields")

        assert len(results) > 0
        field_uris = [r["field"] for r in results]
        assert any("Cabin.doors" in uri for uri in field_uris)

    def test_query_empty_graph(self) -> None:
        """Query on empty graph returns empty list."""
        empty_graph = Graph()
        for query_name in get_query_names():
            results = run_query(empty_graph, query_name)
            assert results == []

    def test_unknown_query_raises(self) -> None:
        """Unknown query name raises KeyError."""
        graph = _cabin_door_graph()
        with pytest.raises(KeyError):
            run_query(graph, "nonexistent")


class TestFormatResults:
    """Tests for result formatting."""

    def test_compact_shortens_uris(self) -> None:
        """Compact mode shortens URIs to local names."""
        results = [{"field": "https://example.org/test#Cabin.kind"}]
        compact = format_results_as_table(results, compact=True)
        assert compact[0]["field"] == "Cabin.kind"

    def test_no_compact_preserves_uris(self) -> None:
        """Non-compact mode preserves full URIs."""
        results = [{"field": "https://example.org/test#Cabin.kind"}]
        non_compact = format_results_as_table(results, compact=False)
        assert non_compact[0]["field"] == "https://example.org/test#Cabin.kind"

    def test_compact_shortens_slash_separator_uris(self) -> None:
        """Compact mode shortens URIs using '/' separator when '#' is absent."""
        results = [{"type": "https://example.org/ontology/ObjectType"}]
        compact = format_results_as_table(results, compact=True)
        assert compact[0]["type"] == "ObjectType"

    def test_empty_results(self) -> None:
        """Empty results return empty list."""
        assert format_results_as_table([]) == []
