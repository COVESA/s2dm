import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from s2dm.exporters.skos import SKOSConcept
from s2dm.tools.skos_search import NO_LIMIT_KEYWORDS, SKOSSearchService


@pytest.fixture
def sample_skos_ttl() -> str:
    """Create a sample SKOS TTL content for testing."""
    return """
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ns: <https://example.org/vss#> .

ns:Vehicle a skos:Concept ;
    skos:prefLabel "Vehicle"@en ;
    skos:definition "A motorized conveyance such as a car, truck, or motorcycle" ;
    skos:note "{vehicle_note}" .

ns:Vehicle_Window a skos:Concept ;
    skos:prefLabel "Vehicle Window"@en ;
    skos:definition "A transparent panel in a vehicle that allows light and air to enter" ;
    skos:note "{vehicle_window_note}" .

ns:Engine a skos:Concept ;
    skos:prefLabel "Engine"@en ;
    skos:definition "The power unit of a vehicle that converts fuel into mechanical energy" ;
    skos:note "{engine_note}" .

ns:Door a skos:Concept ;
    skos:prefLabel "Door"@en ;
    skos:definition "A movable barrier used to close off an entrance to a vehicle" ;
    skos:note "{door_note}" .
""".format(
        vehicle_note=SKOSConcept.NOTE_TEMPLATE.format(name="Vehicle", uri="https://example.org/vss#Vehicle"),
        vehicle_window_note=SKOSConcept.NOTE_TEMPLATE.format(
            name="Vehicle_Window", uri="https://example.org/vss#Vehicle_Window"
        ),
        engine_note=SKOSConcept.NOTE_TEMPLATE.format(name="Engine", uri="https://example.org/vss#Engine"),
        door_note=SKOSConcept.NOTE_TEMPLATE.format(name="Door", uri="https://example.org/vss#Door"),
    )


@pytest.fixture
def ttl_file(sample_skos_ttl: str) -> Path:
    """Create a temporary TTL file with sample SKOS data."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False) as f:
        f.write(sample_skos_ttl)
        return Path(f.name)


@pytest.fixture
def search_service(ttl_file: Path) -> Generator[SKOSSearchService, None, None]:
    """Create a SKOSSearchService instance for testing."""
    with SKOSSearchService(ttl_file) as service:
        yield service


class TestSKOSSearchService:
    """Test cases for SKOSSearchService class."""

    def test_init_with_valid_file(self, search_service: SKOSSearchService, ttl_file: Path) -> None:
        """Test initialization with a valid TTL file."""
        assert search_service.ttl_file_path == ttl_file
        assert len(search_service.graph) > 0

    def test_init_with_nonexistent_file(self) -> None:
        """Test initialization with a non-existent file raises FileNotFoundError."""
        nonexistent_file = Path("/nonexistent/file.ttl")
        with pytest.raises(FileNotFoundError, match="TTL file not found"):
            SKOSSearchService(nonexistent_file)

    def test_init_with_invalid_ttl(self) -> None:
        """Test initialization with invalid TTL content raises ValueError when graph is accessed."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False) as f:
            f.write("invalid ttl content here")
            invalid_file = Path(f.name)

        with SKOSSearchService(invalid_file) as service, pytest.raises(ValueError, match="Failed to parse TTL file"):
            # Access the graph property to trigger parsing
            _ = service.graph

    def test_search_keyword_finds_matches(self, search_service: SKOSSearchService) -> None:
        """Test keyword search finds expected matches."""
        results = search_service.search_keyword("vehicle", ignore_case=True, limit_value=None)

        # Should find both "Vehicle" and "Vehicle_Window"
        assert len(results) >= 2
        subjects = {result.subject for result in results}
        assert "https://example.org/vss#Vehicle" in subjects
        assert "https://example.org/vss#Vehicle_Window" in subjects

    def test_search_and_count_case_sensitivity(self, search_service: SKOSSearchService) -> None:
        """Test case sensitivity for both search and count operations."""
        # Test search case sensitivity
        case_insensitive_search = search_service.search_keyword("DOOR", ignore_case=True)
        case_sensitive_search = search_service.search_keyword("DOOR", ignore_case=False)
        assert len(case_insensitive_search) > len(case_sensitive_search)

        # Test count case sensitivity
        case_sensitive_count = search_service.count_keyword_matches("vehicle", ignore_case=False)
        case_insensitive_count = search_service.count_keyword_matches("vehicle", ignore_case=True)
        assert case_insensitive_count >= case_sensitive_count
        assert case_insensitive_count > 0

        # Test consistency between search and count
        for term, case_insensitive in [("Vehicle", False), ("vehicle", True), ("Door", False)]:
            total_count = search_service.count_keyword_matches(term, ignore_case=case_insensitive)
            search_results = search_service.search_keyword(term, ignore_case=case_insensitive, limit_value=None)
            assert total_count == len(
                search_results
            ), f"Count mismatch for '{term}' case_insensitive={case_insensitive}"

    def test_search_empty_string(self, search_service: SKOSSearchService) -> None:
        """Test search with empty keyword returns empty results."""
        assert search_service.search_keyword("") == []
        assert search_service.search_keyword("   ") == []

    def test_search_no_matches(self, search_service: SKOSSearchService) -> None:
        """Test search with term that has no matches."""
        results = search_service.search_keyword("nonexistent_term_xyz")
        assert len(results) == 0

    def test_search_deduplication(self, search_service: SKOSSearchService) -> None:
        """Test that search results are properly deduplicated."""
        results = search_service.search_keyword("Vehicle", ignore_case=True)

        # Check that we don't have duplicate triples with the same match type
        seen_triples = set()
        for result in results:
            triple_key = (result.subject, result.predicate, result.object_value, result.match_type)
            assert triple_key not in seen_triples, f"Duplicate triple found: {triple_key}"
            seen_triples.add(triple_key)

        assert len(results) > 0

    @pytest.mark.parametrize(
        "limit,expected_behavior",
        [
            (10, "limited"),
            (2, "limited"),
            (0, "zero"),
            ("3", "limited"),
            ("0", "zero"),
            ("all", "unlimited"),
            ("inf", "unlimited"),
            ("none", "unlimited"),
        ],
    )
    def test_search_keyword_limits(
        self, search_service: SKOSSearchService, limit: int | str, expected_behavior: str
    ) -> None:
        """Test search with various limit values."""
        limit_value = search_service.parse_limit(limit)

        # Get reference unlimited count
        unlimited_results = search_service.search_keyword("example", ignore_case=True, limit_value=None)
        unlimited_count = len(unlimited_results)

        # Perform test search
        results = search_service.search_keyword("example", ignore_case=True, limit_value=limit_value)

        # Assert results based on expected behavior
        if expected_behavior == "zero":
            assert len(results) == 0
        elif expected_behavior == "limited":
            expected_limit = int(limit) if isinstance(limit, str) else limit
            assert len(results) <= expected_limit
        elif expected_behavior == "unlimited":
            assert len(results) == unlimited_count

    def test_parse_limit_method(self, search_service: SKOSSearchService) -> None:
        """Test the parse_limit helper method with various inputs."""
        # Numeric limits
        assert search_service.parse_limit(10) == 10
        assert search_service.parse_limit(0) == 0
        assert search_service.parse_limit("5") == 5
        assert search_service.parse_limit(-1) == 0  # Negative numbers

        # Unlimited keywords
        for keyword in NO_LIMIT_KEYWORDS:
            assert search_service.parse_limit(keyword) is None
            assert search_service.parse_limit(keyword.upper()) is None

        # Invalid string should return 0
        assert search_service.parse_limit("invalid") == 0
        assert search_service.parse_limit("not_a_number") == 0

    def test_count_keyword_matches(self, search_service: SKOSSearchService) -> None:
        """Test that count_keyword_matches returns correct counts."""
        # Test with "Vehicle" (should match multiple times)
        total_count = search_service.count_keyword_matches("Vehicle", ignore_case=False)
        search_results = search_service.search_keyword("Vehicle", ignore_case=False, limit_value=None)

        # Count should match the unlimited search results length
        assert total_count == len(search_results)
        assert total_count > 0

        # Test with empty string
        assert search_service.count_keyword_matches("", ignore_case=False) == 0
        assert search_service.count_keyword_matches("   ", ignore_case=True) == 0

        # Test with no matches
        assert search_service.count_keyword_matches("nonexistent_xyz", ignore_case=False) == 0

    def test_sparql_error_handling(self, search_service: SKOSSearchService) -> None:
        """Test SPARQL query error handling."""
        from unittest.mock import patch

        # Test count query error
        with (
            patch("s2dm.tools.skos_search.prepareQuery", side_effect=Exception("SPARQL error")),
            pytest.raises(ValueError, match="Count query execution failed"),
        ):
            search_service.count_keyword_matches("test")

        # Test search query preparation error
        with (
            patch("s2dm.tools.skos_search.prepareQuery", side_effect=Exception("SPARQL prep error")),
            pytest.raises(ValueError, match="Invalid SPARQL query template"),
        ):
            search_service.search_keyword("test")

        # Test search query execution error
        with (
            patch.object(search_service.graph, "query", side_effect=Exception("Query exec error")),
            pytest.raises(ValueError, match="Search query execution failed"),
        ):
            search_service.search_keyword("test")

    def test_empty_graph_handling(self) -> None:
        """Test behavior with an empty TTL file."""
        empty_ttl = "@prefix skos: <http://www.w3.org/2004/02/skos/core#> ."

        with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False) as f:
            f.write(empty_ttl)
            empty_file = Path(f.name)

        with SKOSSearchService(empty_file) as service:
            results = service.search_keyword("anything")
            assert len(results) == 0
            assert service.count_keyword_matches("anything") == 0

    def test_context_manager_cleanup(self, ttl_file: Path) -> None:
        """Test that context manager properly cleans up resources."""
        service = SKOSSearchService(ttl_file)

        # Access graph to load it
        assert len(service.graph) > 0
        assert service._graph is not None

        # Exit context manager
        service.__exit__(None, None, None)

        # Graph should be cleaned up
        assert service._graph is None
