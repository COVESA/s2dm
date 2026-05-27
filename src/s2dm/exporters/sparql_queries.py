"""Predefined SPARQL queries for traversing RDF-materialized GraphQL schemas.

This module provides a set of common SPARQL queries that operate on the s2dm
ontology triples produced by ``rdf_materializer.materialize_schema_to_rdf``.

Predefined queries are loaded at import time from ``*.sparql`` files in the
``sparql_queries/`` directory next to this file.  Each file name (without the
``.sparql`` extension) becomes the query key. An optional first-line comment of
the form ``# description: <text>`` is parsed as the human-readable description.

Custom queries can be executed via :func:`run_query_from_file`.
Multiple RDF files (or directories) can be loaded and merged with
:func:`load_rdf_graphs`.
"""

import logging
from pathlib import Path
from urllib.parse import urlparse

from rdflib import Graph
from rdflib.query import ResultRow

from s2dm.exporters.rdf_materializer import FORMAT_REGISTRY
from s2dm.exporters.utils.schema_loader import resolve_files_by_extensions
from s2dm.utils.download import download_url_to_temp

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Built-in query directory
# ---------------------------------------------------------------------------

_QUERIES_DIR = Path(__file__).parent / "sparql_queries"

# Supported RDF file extensions derived from FORMAT_REGISTRY.
_RDF_EXTENSIONS: frozenset[str] = frozenset(FORMAT_REGISTRY.values())


# ---------------------------------------------------------------------------
# Query loading
# ---------------------------------------------------------------------------


def load_queries_from_directory(directory: Path) -> dict[str, tuple[str, str]]:
    """Load SPARQL queries from ``*.sparql`` files in *directory*.

    The file stem (e.g. ``fields-outputting-enum``) becomes the query name.
    If the first non-empty line starts with ``# description:``, the remainder
    of that line is used as the human-readable description; otherwise the file
    stem is used.

    Args:
        directory: Directory containing ``*.sparql`` files.

    Returns:
        Dict mapping query name to ``(description, sparql_string)``.
    """
    queries: dict[str, tuple[str, str]] = {}
    for sparql_file in sorted(directory.glob("*.sparql")):
        content = sparql_file.read_text(encoding="utf-8")
        lines = content.splitlines()
        description = sparql_file.stem
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# description:"):
                description = stripped[len("# description:") :].strip()
            break
        queries[sparql_file.stem] = (description, content)
    return queries


#: Registry mapping query name to (description, SPARQL string).
QUERIES: dict[str, tuple[str, str]] = load_queries_from_directory(_QUERIES_DIR)


# ---------------------------------------------------------------------------
# Query registry helpers
# ---------------------------------------------------------------------------


def get_query_names() -> list[str]:
    """Return sorted list of available predefined query names.

    Returns:
        List of query name strings.
    """
    return sorted(QUERIES.keys())


def get_query_description(query_name: str) -> str:
    """Return the human-readable description for a predefined query.

    Args:
        query_name: Key in the QUERIES registry.

    Returns:
        Description string.

    Raises:
        KeyError: If *query_name* is not in the registry.
    """
    return QUERIES[query_name][0]


# ---------------------------------------------------------------------------
# RDF file resolution and loading
# ---------------------------------------------------------------------------


def download_rdf_to_temp(url: str, max_size_mb: int = 50) -> Path:
    """Download an RDF file from *url* to a temporary file.

    The suffix is inferred from the URL path (e.g. ``.ttl``); when not
    recognisable, ``.ttl`` is used as a safe default.

    Args:
        url: HTTP/HTTPS URL of an RDF file.
        max_size_mb: Maximum allowed file size in megabytes.

    Returns:
        Path to the downloaded temporary file.

    Raises:
        RuntimeError: If the download fails or the file exceeds the size limit.
    """
    url_suffix = Path(urlparse(url).path).suffix.lower()
    suffix = url_suffix if url_suffix in _RDF_EXTENSIONS else ".ttl"
    return download_url_to_temp(url, suffix=suffix, resource_label="RDF", max_size_mb=max_size_mb)


def resolve_rdf_files(paths: list[Path]) -> list[Path]:
    """Resolve a list of paths into a flat, deduplicated list of RDF files.

    For each entry:
    - If a file with a recognised RDF extension (``.nt``, ``.ttl``, ``.jsonld``),
      include it directly.
    - If a directory, recurse with ``rglob`` and include all matching files.

    Args:
        paths: List of file or directory Paths (already resolved from strings/URLs
            by the caller).

    Returns:
        Deduplicated, sorted list of RDF file Paths.
    """
    return resolve_files_by_extensions(paths, _RDF_EXTENSIONS)


def load_rdf_graph(path: Path) -> Graph:
    """Load an RDF graph from a single file, detecting format by extension.

    Supported extensions: ``.nt`` (n-triples), ``.ttl`` (turtle),
    ``.jsonld`` (JSON-LD).

    Args:
        path: Path to the RDF file.

    Returns:
        Parsed rdflib Graph.

    Raises:
        ValueError: If the file extension is not recognised.
        FileNotFoundError: If the file does not exist.
    """
    # Derive extension-to-rdflib-format mapping from the shared FORMAT_REGISTRY
    ext_to_format: dict[str, str] = {ext: fmt for fmt, ext in FORMAT_REGISTRY.items()}

    if not path.exists():
        raise FileNotFoundError(f"RDF file not found: {path}")

    fmt = ext_to_format.get(path.suffix.lower())
    if fmt is None:
        supported = ", ".join(sorted(ext_to_format.keys()))
        raise ValueError(f"Unsupported RDF file extension '{path.suffix}'. Supported: {supported}")

    graph = Graph()
    graph.parse(str(path), format=fmt)
    return graph


def load_rdf_graphs(paths: list[Path]) -> Graph:
    """Load and merge one or more RDF files into a single Graph.

    Args:
        paths: List of RDF file paths (already resolved/downloaded).

    Returns:
        A single rdflib Graph containing all triples from all files.

    Raises:
        ValueError: If *paths* is empty.
    """
    if not paths:
        raise ValueError("At least one RDF file path is required.")

    merged = Graph()
    for path in paths:
        partial = load_rdf_graph(path)
        for triple in partial:
            merged.add(triple)
    return merged


# ---------------------------------------------------------------------------
# Query execution
# ---------------------------------------------------------------------------


def _execute_sparql(graph: Graph, sparql: str) -> list[dict[str, str]]:
    """Execute a raw SPARQL SELECT string against *graph*.

    Args:
        graph: The rdflib Graph to query.
        sparql: SPARQL SELECT query string.

    Returns:
        List of result rows, each a dict mapping variable name to string value.
    """
    qres = graph.query(sparql)
    variables = [str(v) for v in qres.vars] if qres.vars else []
    results: list[dict[str, str]] = []
    for row in qres:
        if isinstance(row, ResultRow):
            results.append({var: str(val) for var, val in zip(variables, row, strict=False)})
    return results


def run_query(graph: Graph, query_name: str) -> list[dict[str, str]]:
    """Execute a predefined SPARQL query against an RDF graph.

    Args:
        graph: The rdflib Graph to query.
        query_name: Key in the QUERIES registry.

    Returns:
        List of result rows, each a dict mapping variable name to string value.

    Raises:
        KeyError: If *query_name* is not in the registry.
    """
    _, sparql = QUERIES[query_name]
    return _execute_sparql(graph, sparql)


def run_query_from_file(graph: Graph, path: Path) -> list[dict[str, str]]:
    """Execute a SPARQL query read from *path* against *graph*.

    Args:
        graph: The rdflib Graph to query.
        path: Path to a ``.sparql`` file containing a SELECT query.

    Returns:
        List of result rows, each a dict mapping variable name to string value.

    Raises:
        FileNotFoundError: If *path* does not exist.
        ValueError: If *path* does not have a ``.sparql`` extension.
    """
    if not path.exists():
        raise FileNotFoundError(f"Query file not found: {path}")
    if path.suffix.lower() != ".sparql":
        raise ValueError(f"Expected a .sparql file, got: '{path.suffix}'")
    sparql = path.read_text(encoding="utf-8")
    return _execute_sparql(graph, sparql)


# ---------------------------------------------------------------------------
# Result formatting
# ---------------------------------------------------------------------------


def format_results_as_table(
    results: list[dict[str, str]],
    compact: bool = True,
) -> list[dict[str, str]]:
    """Optionally shorten URIs in query results for display.

    When *compact* is True, URIs are shortened to their fragment or last
    path segment for readability.

    Args:
        results: Raw query result rows.
        compact: Whether to shorten URIs (default: True).

    Returns:
        Processed result rows.
    """
    if not compact:
        return results

    def _shorten(uri: str) -> str:
        """Extract the local name from a URI."""
        for sep in ("#", "/"):
            if sep in uri:
                return uri.rsplit(sep, 1)[-1]
        return uri

    return [{k: _shorten(v) for k, v in row.items()} for row in results]
