import tempfile
from pathlib import Path

import pytest

from s2dm.tools.skos_search import SearchResult, SKOSSearchService


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
    skos:note "Definition was inherit from the description of the element https://example.org/vss#Vehicle" ;
    rdfs:seeAlso ns:Vehicle .

ns:Vehicle_Window a skos:Concept ;
    skos:prefLabel "Vehicle Window"@en ;
    skos:definition "A transparent panel in a vehicle that allows light and air to enter" ;
    skos:note "Definition was inherit from the description of the element https://example.org/vss#Vehicle_Window" ;
    rdfs:seeAlso ns:Vehicle_Window .

ns:Engine a skos:Concept ;
    skos:prefLabel "Engine"@en ;
    skos:definition "The power unit of a vehicle that converts fuel into mechanical energy" ;
    skos:note "Definition was inherit from the description of the element https://example.org/vss#Engine" ;
    rdfs:seeAlso ns:Engine .

ns:Door a skos:Concept ;
    skos:prefLabel "Door"@en ;
    skos:definition "A movable barrier used to close off an entrance to a vehicle" ;
    skos:note "Definition was inherit from the description of the element https://example.org/vss#Door" ;
    rdfs:seeAlso ns:Door .
"""


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
def search_service(ttl_file: Path) -> SKOSSearchService:
    """Create a SKOSSearchService instance for testing.

    Args:
        ttl_file: Path to the test TTL file

    Returns:
        Configured SKOSSearchService instance
    """
    return SKOSSearchService(ttl_file)


class TestSKOSSearchService:
    """Test cases for SKOSSearchService class."""

    def test_init_with_valid_file(self, ttl_file: Path) -> None:
        """Test initialization with a valid TTL file."""
        service = SKOSSearchService(ttl_file)
        assert service.ttl_file_path == ttl_file
        assert len(service.graph) > 0

    def test_init_with_nonexistent_file(self) -> None:
        """Test initialization with a non-existent file raises FileNotFoundError."""
        nonexistent_file = Path("/nonexistent/file.ttl")
        with pytest.raises(FileNotFoundError, match="TTL file not found"):
            SKOSSearchService(nonexistent_file)

    def test_init_with_invalid_ttl(self) -> None:
        """Test initialization with invalid TTL content raises ValueError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False) as f:
            f.write("invalid ttl content here")
            invalid_file = Path(f.name)

        with pytest.raises(ValueError, match="Failed to parse TTL file"):
            SKOSSearchService(invalid_file)

    def test_search_keyword_finds_vehicle_matches(self, search_service: SKOSSearchService) -> None:
        """Test keyword search finds vehicle-related matches."""
        results = search_service.search_keyword("vehicle", ignore_case=True)

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

        service = SKOSSearchService(empty_file)
        results = service.search_keyword("anything")

        assert len(results) == 0
