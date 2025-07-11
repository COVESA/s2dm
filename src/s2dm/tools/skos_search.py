import logging
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from rdflib import Graph
from rdflib.query import ResultRow


@dataclass
class SearchResult:
    """Represents a search result from SPARQL query.

    Args:
        subject: The RDF subject that matched the search
        predicate: The RDF predicate of the matching triple
        object_value: The RDF object value that matched the search
        match_type: Whether the match was found in 'subject' or 'object'
    """

    subject: str
    predicate: str
    object_value: str
    match_type: str

    def __str__(self) -> str:
        """Return a human-readable string representation of the search result."""
        return f"{self.match_type.upper()}: {self.subject} -> {self.predicate} -> {self.object_value}"


class SKOSSearchService:
    """Service for searching SKOS RDF data using SPARQL queries."""

    def __init__(self, ttl_file_path: Path) -> None:
        """Initialize the search service with a TTL file.

        Args:
            ttl_file_path: Path to the TTL file containing SKOS data

        Raises:
            FileNotFoundError: If the TTL file doesn't exist
            ValueError: If the TTL file cannot be parsed
        """
        if not ttl_file_path.exists():
            raise FileNotFoundError(f"TTL file not found: {ttl_file_path}")

        self.ttl_file_path = ttl_file_path
        self.graph = Graph()

        try:
            self.graph.parse(ttl_file_path, format="turtle")
            logging.info(f"Loaded {len(self.graph)} triples from {ttl_file_path}")
        except Exception as e:
            raise ValueError(f"Failed to parse TTL file {ttl_file_path}: {e}") from e

    def search_keyword(self, keyword: str, ignore_case: bool = False) -> list[SearchResult]:
        """Search for a keyword in SKOS RDF data using SPARQL.

        Searches both RDF subjects and objects for the specified keyword.

        Args:
            keyword: The keyword to search for
            ignore_case: Whether to perform case-insensitive matching (default: False)

        Returns:
            List of SearchResult objects containing matching triples
        """
        if not keyword.strip():
            return []

        # Escape quotes in keyword for SPARQL
        escaped_keyword = keyword.replace('"', '\\"')

        # Build filter conditions based on case sensitivity
        if ignore_case:
            subject_filter = f'FILTER(CONTAINS(LCASE(STR(?subject)), LCASE("{escaped_keyword}")))'
            object_filter = f'FILTER(CONTAINS(LCASE(STR(?object)), LCASE("{escaped_keyword}")))'
        else:
            subject_filter = f'FILTER(CONTAINS(STR(?subject), "{escaped_keyword}"))'
            object_filter = f'FILTER(CONTAINS(STR(?object), "{escaped_keyword}"))'

        query = f"""
        SELECT ?subject ?predicate ?object ?match_type
        WHERE {{
            {{
                ?subject ?predicate ?object .
                {subject_filter}
                BIND("subject" AS ?match_type)
            }}
            UNION
            {{
                ?subject ?predicate ?object .
                {object_filter}
                BIND("object" AS ?match_type)
            }}
        }}
        ORDER BY ?subject ?predicate
        """

        logging.debug(f"Executing SPARQL query: {query}")

        try:
            results = self.graph.query(query)
            search_results = []

            for row in results:
                # Cast to ResultRow to access SPARQL result variables by name
                result_row: ResultRow = cast(ResultRow, row)
                result = SearchResult(
                    subject=str(result_row["subject"]),
                    predicate=str(result_row["predicate"]),
                    object_value=str(result_row["object"]),
                    match_type=str(result_row["match_type"]),
                )
                search_results.append(result)

            logging.info(f"Found {len(search_results)} matches for keyword '{keyword}'")
            return search_results

        except Exception as e:
            logging.error(f"SPARQL query failed: {e}")
            raise ValueError(f"Search query failed: {e}") from e
