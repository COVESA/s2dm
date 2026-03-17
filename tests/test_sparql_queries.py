"""Tests for SPARQL query module for RDF-materialized GraphQL schemas."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from graphql import build_schema
from rdflib import Graph

from s2dm.exporters.rdf_materializer import (
    materialize_schema_to_rdf,
    serialize_sorted_ntriples,
)
from s2dm.exporters.sparql_queries import (
    QUERIES,
    download_rdf_to_temp,
    format_results_as_table,
    get_query_description,
    get_query_names,
    load_queries_from_directory,
    load_rdf_graph,
    load_rdf_graphs,
    resolve_rdf_files,
    run_query,
    run_query_from_file,
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


class TestLoadQueriesFromDirectory:
    """Tests for loading queries from .sparql files."""

    def test_loads_queries_from_files(self, tmp_path: Path) -> None:
        """Queries are loaded from .sparql files in the directory."""
        (tmp_path / "my-query.sparql").write_text(
            "# description: My test query\nSELECT * WHERE { ?s ?p ?o }", encoding="utf-8"
        )
        loaded = load_queries_from_directory(tmp_path)
        assert "my-query" in loaded
        desc, sparql = loaded["my-query"]
        assert desc == "My test query"
        assert "SELECT" in sparql

    def test_fallback_description_is_stem(self, tmp_path: Path) -> None:
        """When no description comment, filename stem is used as description."""
        (tmp_path / "fallback-query.sparql").write_text("SELECT * WHERE { ?s ?p ?o }", encoding="utf-8")
        loaded = load_queries_from_directory(tmp_path)
        desc, _ = loaded["fallback-query"]
        assert desc == "fallback-query"

    def test_empty_directory_returns_empty_dict(self, tmp_path: Path) -> None:
        """Empty directory returns empty dict."""
        assert load_queries_from_directory(tmp_path) == {}

    def test_non_sparql_files_are_ignored(self, tmp_path: Path) -> None:
        """Files without .sparql extension are ignored."""
        (tmp_path / "not-a-query.txt").write_text("SELECT * WHERE { ?s ?p ?o }", encoding="utf-8")
        loaded = load_queries_from_directory(tmp_path)
        assert loaded == {}


class TestLoadRdfGraph:
    """Tests for loading a single RDF graph from a file."""

    def test_load_nt_file(self, tmp_path: Path) -> None:
        """Load graph from n-triples file."""
        nt_path = tmp_path / "test.nt"
        nt_path.write_text(serialize_sorted_ntriples(_cabin_door_graph()), encoding="utf-8")
        loaded = load_rdf_graph(nt_path)
        assert len(loaded) > 0

    def test_load_ttl_file(self, tmp_path: Path) -> None:
        """Load graph from turtle file."""
        ttl_path = tmp_path / "test.ttl"
        _cabin_door_graph().serialize(destination=str(ttl_path), format="turtle")
        loaded = load_rdf_graph(ttl_path)
        assert len(loaded) > 0

    def test_load_jsonld_file(self, tmp_path: Path) -> None:
        """Load graph from JSON-LD file."""
        jsonld_path = tmp_path / "test.jsonld"
        _cabin_door_graph().serialize(destination=str(jsonld_path), format="json-ld")
        loaded = load_rdf_graph(jsonld_path)
        assert len(loaded) > 0

    def test_unsupported_extension_raises(self, tmp_path: Path) -> None:
        """Unsupported file extension raises ValueError."""
        bad_path = tmp_path / "test.rdf"
        bad_path.write_text("<rdf/>", encoding="utf-8")
        with pytest.raises(ValueError, match="Unsupported RDF file extension"):
            load_rdf_graph(bad_path)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """Non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_rdf_graph(tmp_path / "does_not_exist.nt")


class TestLoadRdfGraphs:
    """Tests for merging multiple RDF files into one graph."""

    def test_merges_two_nt_files(self, tmp_path: Path) -> None:
        """Two .nt files are merged into a single graph with combined triples."""
        graph = _cabin_door_graph()
        nt = serialize_sorted_ntriples(graph)
        path1 = tmp_path / "a.nt"
        path2 = tmp_path / "b.nt"
        path1.write_text(nt, encoding="utf-8")
        path2.write_text(nt, encoding="utf-8")

        merged = load_rdf_graphs([path1, path2])
        # Deduplication: merging the same triples twice should still yield same count
        assert len(merged) == len(graph)

    def test_merges_different_graphs(self, tmp_path: Path) -> None:
        """Two different RDF files are merged with all triples present."""
        schema_a = build_schema("type Query { a: A } type A { x: String }")
        schema_b = build_schema("type Query { b: B } type B { y: Int }")
        graph_a = materialize_schema_to_rdf(schema=schema_a, namespace=NS, prefix=PREFIX)
        graph_b = materialize_schema_to_rdf(schema=schema_b, namespace=NS, prefix=PREFIX)

        path_a = tmp_path / "a.nt"
        path_b = tmp_path / "b.nt"
        path_a.write_text(serialize_sorted_ntriples(graph_a), encoding="utf-8")
        path_b.write_text(serialize_sorted_ntriples(graph_b), encoding="utf-8")

        merged = load_rdf_graphs([path_a, path_b])
        nt = serialize_sorted_ntriples(merged)
        assert "A" in nt and "B" in nt

    def test_empty_list_raises(self) -> None:
        """Empty paths list raises ValueError."""
        with pytest.raises(ValueError, match="At least one RDF file path is required"):
            load_rdf_graphs([])


class TestResolveRdfFiles:
    """Tests for resolve_rdf_files."""

    def test_single_nt_file(self, tmp_path: Path) -> None:
        """A single .nt file is returned as-is."""
        f = tmp_path / "graph.nt"
        f.write_text("", encoding="utf-8")
        assert resolve_rdf_files([f]) == [f]

    def test_directory_finds_rdf_files(self, tmp_path: Path) -> None:
        """Files with RDF extensions in a directory are found."""
        (tmp_path / "a.nt").write_text("", encoding="utf-8")
        (tmp_path / "b.ttl").write_text("", encoding="utf-8")
        (tmp_path / "c.txt").write_text("", encoding="utf-8")
        result = resolve_rdf_files([tmp_path])
        names = {p.name for p in result}
        assert "a.nt" in names and "b.ttl" in names
        assert "c.txt" not in names

    def test_directory_recurses_into_subdirectories(self, tmp_path: Path) -> None:
        """RDF files in subdirectories are found via rglob."""
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "deep.nt").write_text("", encoding="utf-8")
        result = resolve_rdf_files([tmp_path])
        assert any(p.name == "deep.nt" for p in result)

    def test_deduplicates_files(self, tmp_path: Path) -> None:
        """Passing the same file twice yields one entry."""
        f = tmp_path / "graph.nt"
        f.write_text("", encoding="utf-8")
        result = resolve_rdf_files([f, f])
        assert result.count(f) == 1

    def test_unsupported_file_extension_excluded(self, tmp_path: Path) -> None:
        """Files with unsupported extensions are excluded."""
        f = tmp_path / "graph.rdf"
        f.write_text("", encoding="utf-8")
        assert resolve_rdf_files([f]) == []


class TestDownloadRdfToTemp:
    """Tests for download_rdf_to_temp."""

    def test_downloads_ttl_url(self, tmp_path: Path) -> None:
        """A .ttl URL is downloaded with correct suffix."""
        mock_response = MagicMock()
        mock_response.text = "@prefix ex: <https://example.org/> ."
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()

        with patch("s2dm.exporters.utils.schema_loader.requests.get", return_value=mock_response) as mock_get:
            result = download_rdf_to_temp("https://example.org/graph.ttl")
            mock_get.assert_called_once()
            assert result.exists()
            assert result.suffix == ".ttl"
            result.unlink()

    def test_unknown_extension_defaults_to_ttl(self) -> None:
        """URL with unrecognised extension falls back to .ttl suffix."""
        mock_response = MagicMock()
        mock_response.text = "some rdf content"
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()

        with patch("s2dm.exporters.utils.schema_loader.requests.get", return_value=mock_response):
            result = download_rdf_to_temp("https://example.org/graph")
            assert result.suffix == ".ttl"
            result.unlink()

    def test_request_failure_raises_runtime_error(self) -> None:
        """Network failure raises RuntimeError."""
        import requests as req

        with (
            patch("s2dm.exporters.utils.schema_loader.requests.get", side_effect=req.RequestException("fail")),
            pytest.raises(RuntimeError, match="Failed to download RDF"),
        ):
            download_rdf_to_temp("https://example.org/graph.ttl")

    def test_size_limit_respected(self) -> None:
        """Files exceeding max_size_mb raise RuntimeError."""
        mock_response = MagicMock()
        mock_response.headers = {"content-length": str(60 * 1024 * 1024)}
        mock_response.raise_for_status = MagicMock()

        with (
            patch("s2dm.exporters.utils.schema_loader.requests.get", return_value=mock_response),
            pytest.raises(RuntimeError, match="RDF file too large"),
        ):
            download_rdf_to_temp("https://example.org/graph.ttl", max_size_mb=50)


class TestRunQuery:
    """Tests for executing predefined SPARQL queries."""

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
            assert run_query(empty_graph, query_name) == []

    def test_unknown_query_raises(self) -> None:
        """Unknown query name raises KeyError."""
        with pytest.raises(KeyError):
            run_query(_cabin_door_graph(), "nonexistent")


class TestRunQueryFromFile:
    """Tests for executing a custom .sparql file."""

    def test_executes_custom_query(self, tmp_path: Path) -> None:
        """A valid .sparql file is executed and returns results."""
        graph = _cabin_door_graph()
        sparql_file = tmp_path / "all-subjects.sparql"
        sparql_file.write_text("SELECT ?s WHERE { ?s ?p ?o } LIMIT 1", encoding="utf-8")

        results = run_query_from_file(graph, sparql_file)
        assert isinstance(results, list)
        assert len(results) == 1

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """Non-existent .sparql file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            run_query_from_file(Graph(), tmp_path / "missing.sparql")

    def test_non_sparql_extension_raises(self, tmp_path: Path) -> None:
        """File without .sparql extension raises ValueError."""
        f = tmp_path / "query.txt"
        f.write_text("SELECT * WHERE { ?s ?p ?o }", encoding="utf-8")
        with pytest.raises(ValueError, match=r"\.sparql"):
            run_query_from_file(Graph(), f)

    def test_description_comment_does_not_break_execution(self, tmp_path: Path) -> None:
        """A .sparql file with a # description: header still executes correctly."""
        graph = _cabin_door_graph()
        sparql_file = tmp_path / "described.sparql"
        sparql_file.write_text(
            "# description: Find something\nSELECT ?s WHERE { ?s ?p ?o } LIMIT 1",
            encoding="utf-8",
        )
        results = run_query_from_file(graph, sparql_file)
        assert len(results) == 1


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
