import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from s2dm.exporters.skos import SKOSConcept
from s2dm.tools.skos_search import NO_LIMIT_KEYWORDS, SearchResult, SKOSSearchService


@pytest.fixture
def sample_skos_ttl() -> str:
    """Create a sample SKOS TTL content for testing.

    Returns:
        String containing sample SKOS RDF in Turtle format
    """
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
    """Create a temporary TTL file with sample SKOS data.

    Args:
        sample_skos_ttl: Sample SKOS content

    Returns:
        Path to the temporary TTL file
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False) as f:
        f.write(sample_skos_ttl)
        return Path(f.name)


@pytest.fixture
def search_service(ttl_file: Path) -> Generator[SKOSSearchService, None, None]:
    """Create a SKOSSearchService instance for testing.

    Args:
        ttl_file: Path to the test TTL file

    Returns:
        Configured SKOSSearchService instance
    """
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

    def test_search_keyword_finds_vehicle_matches(self, search_service: SKOSSearchService) -> None:
        """Test keyword search finds vehicle-related matches."""
        # Use unlimited search to ensure we get all matches
        results = search_service.search_keyword("vehicle", ignore_case=True, limit_value=None)

        # Should find both "Vehicle" and "Vehicle_Window"
        assert len(results) >= 2

        # Check that results contain expected subjects
        subjects = {result.subject for result in results}
        assert "https://example.org/vss#Vehicle" in subjects
        assert "https://example.org/vss#Vehicle_Window" in subjects

    def test_search_keyword_case_insensitive(self, search_service: SKOSSearchService) -> None:
        """Test case-insensitive search when explicitly enabled."""
        results_lower = search_service.search_keyword("vehicle", ignore_case=True)
        results_upper = search_service.search_keyword("VEHICLE", ignore_case=True)

        # Both searches should return the same results when case-insensitive
        assert len(results_lower) == len(results_upper)

    def test_search_keyword_case_sensitive_default(self, search_service: SKOSSearchService) -> None:
        """Test case-sensitive search is the default behavior."""
        # Default behavior should be case-sensitive
        results_exact = search_service.search_keyword("Vehicle")

        # Should find "Vehicle" in URIs and labels with exact case
        assert len(results_exact) > 0

    def test_search_keyword_case_sensitive_vs_insensitive(self, search_service: SKOSSearchService) -> None:
        """Test difference between case-sensitive and case-insensitive search."""
        # Case-insensitive should find more matches for mixed case terms
        case_insensitive_results = search_service.search_keyword("DOOR", ignore_case=True)
        case_sensitive_results = search_service.search_keyword("DOOR", ignore_case=False)

        # Case-insensitive should find "Door" concept, case-sensitive should not
        assert len(case_insensitive_results) > len(case_sensitive_results)

    def test_search_keyword_empty_string(self, search_service: SKOSSearchService) -> None:
        """Test search with empty keyword returns empty results."""
        results = search_service.search_keyword("")
        assert len(results) == 0

        results = search_service.search_keyword("   ")  # Whitespace only
        assert len(results) == 0

    def test_search_keyword_special_characters(self, search_service: SKOSSearchService) -> None:
        """Test search with special characters in keyword."""
        # Should not crash with special characters
        results = search_service.search_keyword('test"quotes')
        assert isinstance(results, list)

        results = search_service.search_keyword("test'apostrophe")
        assert isinstance(results, list)

    def test_search_finds_window_in_definition(self, search_service: SKOSSearchService) -> None:
        """Test that search finds 'window' in definitions."""
        results = search_service.search_keyword("transparent")

        # Should find Vehicle_Window which has "transparent" in its definition
        assert len(results) > 0
        window_found = any("Vehicle_Window" in result.subject for result in results)
        assert window_found

    def test_search_finds_terms_in_subjects(self, search_service: SKOSSearchService) -> None:
        """Test that search finds terms in RDF subjects."""
        results = search_service.search_keyword("Engine")

        # Should find results where "Engine" appears in the subject URI
        subject_matches = [r for r in results if r.match_type == "subject"]
        object_matches = [r for r in results if r.match_type == "object"]

        # Should have both subject and object matches
        assert len(subject_matches) > 0
        assert len(object_matches) > 0

    def test_search_no_matches(self, search_service: SKOSSearchService) -> None:
        """Test search with term that has no matches."""
        results = search_service.search_keyword("nonexistent_term_xyz")
        assert len(results) == 0

    def test_search_deduplication(self, search_service: SKOSSearchService) -> None:
        """Test that search results are properly deduplicated."""
        # Search for a term that might appear in both subject and object
        results = search_service.search_keyword("Vehicle", ignore_case=True)

        # Check that we don't have duplicate triples with the same match type
        seen_triples = set()
        for result in results:
            triple_key = (result.subject, result.predicate, result.object_value, result.match_type)
            assert triple_key not in seen_triples, f"Duplicate triple found: {triple_key}"
            seen_triples.add(triple_key)

            # Should have some results
        assert len(results) > 0

    @pytest.mark.parametrize(
        "limit,expected_count",
        [
            # Default and numeric limits
            (10, "limited"),
            (2, "limited"),
            (0, 0),
            ("3", "limited"),
            ("0", 0),
        ]
        + [
            # Unlimited keywords (sample)
            (list(NO_LIMIT_KEYWORDS)[0], "unlimited"),
            (list(NO_LIMIT_KEYWORDS)[1], "unlimited"),
            (list(NO_LIMIT_KEYWORDS)[0].upper(), "unlimited"),
        ],
    )
    def test_search_keyword_limits(
        self, search_service: SKOSSearchService, limit: int | str, expected_count: str | int
    ) -> None:
        """Test search with various limit values."""
        # Parse the limit to get the expected values
        limit_value = search_service.parse_limit(limit)

        # Get reference unlimited count
        unlimited_results = search_service.search_keyword("example", ignore_case=True, limit_value=None)
        unlimited_count = len(unlimited_results)

        # Perform test search
        results = search_service.search_keyword("example", ignore_case=True, limit_value=limit_value)

        # Assert results
        if expected_count == 0:
            assert len(results) == 0
        elif expected_count == "limited":
            expected_limit = int(limit) if isinstance(limit, str) else limit
            assert len(results) <= expected_limit
        elif expected_count == "unlimited":
            assert len(results) == unlimited_count

    @pytest.mark.parametrize(
        "limit_value,expected_limit",
        [
            # Numeric limits
            (10, 10),
            (1, 1),
            (5, 5),
            # Zero limits
            (0, 0),
            # String numeric limits
            ("5", 5),
            ("10", 10),
            ("0", 0),
        ]
        + [
            # Unlimited keywords (lowercase)
            (keyword, None)
            for keyword in NO_LIMIT_KEYWORDS
        ]
        + [
            # Unlimited keywords (uppercase)
            (keyword.upper(), None)
            for keyword in NO_LIMIT_KEYWORDS
        ],
    )
    def test_parse_limit_method(
        self,
        search_service: SKOSSearchService,
        limit_value: int | str,
        expected_limit: int | None,
    ) -> None:
        """Test the parse_limit helper method."""
        limit_result = search_service.parse_limit(limit_value)
        assert limit_result == expected_limit


class TestSearchResultModel:
    """Test cases for SearchResult dataclass."""

    def test_search_result_creation(self) -> None:
        """Test creating SearchResult instances."""
        result = SearchResult(
            subject="https://example.org/test#Subject",
            predicate="https://example.org/test#predicate",
            object_value="Test Value",
            match_type="object",
        )

        assert result.subject == "https://example.org/test#Subject"
        assert result.predicate == "https://example.org/test#predicate"
        assert result.object_value == "Test Value"
        assert result.match_type == "object"

    def test_search_result_string_formatting(self) -> None:
        """Test SearchResult string formatting for different match types."""
        subject_result = SearchResult("subj", "pred", "obj", "subject")
        object_result = SearchResult("subj", "pred", "obj", "object")

        assert str(subject_result).startswith("SUBJECT:")
        assert str(object_result).startswith("OBJECT:")
        assert "subj -> pred -> obj" in str(subject_result)
        assert "subj -> pred -> obj" in str(object_result)


class TestErrorHandling:
    """Test error handling in SKOS search functionality."""

    def test_sparql_query_execution(self, search_service: SKOSSearchService) -> None:
        """Test that SPARQL queries execute without errors."""
        # This should not crash the service
        results = search_service.search_keyword("normal_term")
        assert isinstance(results, list)

    def test_empty_graph_handling(self) -> None:
        """Test behavior with an empty TTL file."""
        empty_ttl = """
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False) as f:
            f.write(empty_ttl)
            empty_file = Path(f.name)

        with SKOSSearchService(empty_file) as service:
            results = service.search_keyword("anything")

            assert len(results) == 0
