"""Registry search helpers (e.g., SKOS search)."""

import logging
import types
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from rdflib import Graph, Literal
from rdflib.plugins.sparql import prepareQuery
from rdflib.query import ResultRow

from s2dm.tools.string import normalize_whitespace

NO_LIMIT_KEYWORDS = {"inf", "infinity", "-1", "no", "none", "unlimited", "all"}


@dataclass
class SearchResult:
    """Represents a search result from SPARQL query."""

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
        """Initialize the search service with a TTL file."""
        if not ttl_file_path.exists():
            raise FileNotFoundError(f"TTL file not found: {ttl_file_path}")
        self.ttl_file_path = ttl_file_path
        self._graph: Graph | None = None

    @property
    def graph(self) -> Graph:
        """Lazy-loaded RDF graph property."""
        if self._graph is None:
            self._graph = Graph()
            try:
                self._graph.parse(self.ttl_file_path, format="turtle")
            except OSError as e:
                raise ValueError(f"Failed to read TTL file {self.ttl_file_path}: {e}") from e
            except Exception as e:
                raise ValueError(f"Failed to parse TTL file {self.ttl_file_path}: {e}") from e
            logging.info(f"Loaded {len(self._graph)} triples from {self.ttl_file_path}")
        return self._graph

    def __enter__(self) -> "SKOSSearchService":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Context manager exit with resource cleanup."""
        if self._graph is not None:
            self._graph = None

    @classmethod
    def parse_limit(cls, limit: int | str) -> int | None:
        """Parse and validate the limit parameter."""
        if isinstance(limit, str):
            if limit.lower() in NO_LIMIT_KEYWORDS:
                return None
            try:
                limit_int = int(limit)
                return limit_int if limit_int > 0 else 0
            except ValueError:
                return 0
        return limit if limit > 0 else 0

    def count_keyword_matches(self, keyword: str, ignore_case: bool = False) -> int:
        """Count total number of matches for a keyword in SKOS RDF data."""
        if not keyword.strip():
            return 0

        if ignore_case:
            subject_filter = "FILTER(CONTAINS(LCASE(STR(?subject)), LCASE(?keyword)))"
            object_filter = "FILTER(CONTAINS(LCASE(STR(?object)), LCASE(?keyword)))"
        else:
            subject_filter = "FILTER(CONTAINS(STR(?subject), ?keyword))"
            object_filter = "FILTER(CONTAINS(STR(?object), ?keyword))"

        count_query_template = f"""
        SELECT (COUNT(*) AS ?total_count)
        WHERE {{
            {{
                SELECT DISTINCT ?subject ?predicate ?object ?match_type
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
            }}
        }}
        """

        try:
            prepared_query = prepareQuery(count_query_template)
            results = self.graph.query(prepared_query, initBindings={"keyword": Literal(keyword)})
            for row in results:
                result_row: ResultRow = cast(ResultRow, row)
                return int(result_row["total_count"])
            return 0
        except Exception as e:
            logging.error(f"Count query execution failed: {e}")
            raise ValueError(f"Count query execution failed: {e}") from e

    def search_keyword(
        self, keyword: str, ignore_case: bool = False, limit_value: int | None = 10
    ) -> list[SearchResult]:
        """Search for a keyword in SKOS RDF data using SPARQL."""
        if not keyword.strip():
            return []
        if limit_value == 0:
            return []

        if ignore_case:
            subject_filter = "FILTER(CONTAINS(LCASE(STR(?subject)), LCASE(?keyword)))"
            object_filter = "FILTER(CONTAINS(LCASE(STR(?object)), LCASE(?keyword)))"
        else:
            subject_filter = "FILTER(CONTAINS(STR(?subject), ?keyword))"
            object_filter = "FILTER(CONTAINS(STR(?object), ?keyword))"

        query_template = f"""
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

        if limit_value is not None:
            query_template += f"\nLIMIT {limit_value}"

        try:
            prepared_query = prepareQuery(query_template)
        except Exception as e:
            logging.error(f"SPARQL query preparation failed: {e}")
            raise ValueError(f"Invalid SPARQL query template: {e}") from e

        try:
            results = self.graph.query(prepared_query, initBindings={"keyword": Literal(keyword)})
        except Exception as e:
            logging.error(f"SPARQL query execution failed: {e}")
            raise ValueError(f"Search query execution failed: {e}") from e

        search_results: list[SearchResult] = []
        seen_triples: set[tuple[str, str, str, str]] = set()

        for row in results:
            result_row: ResultRow = cast(ResultRow, row)
            subject = normalize_whitespace(str(result_row["subject"]))
            predicate = normalize_whitespace(str(result_row["predicate"]))
            object_value = normalize_whitespace(str(result_row["object"]))
            match_type = normalize_whitespace(str(result_row["match_type"]))

            triple_key = (subject, predicate, object_value, match_type)
            if triple_key in seen_triples:
                continue
            seen_triples.add(triple_key)
            search_results.append(
                SearchResult(
                    subject=subject,
                    predicate=predicate,
                    object_value=object_value,
                    match_type=match_type,
                )
            )

        logging.info(f"{len(search_results)} unique matches for keyword '{keyword}' with limit {limit_value}")
        return search_results
