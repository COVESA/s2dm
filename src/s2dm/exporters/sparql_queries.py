"""Predefined SPARQL queries for traversing RDF-materialized GraphQL schemas.

This module provides a set of common SPARQL queries that operate on the s2dm
ontology triples produced by ``rdf_materializer.materialize_schema_to_rdf``.
Queries are stored in a registry and executed via ``run_query``.
"""

from pathlib import Path

from rdflib import Graph
from rdflib.query import ResultRow

from s2dm.exporters.rdf_materializer import FORMAT_REGISTRY
from s2dm.exporters.skos import S2DM_NAMESPACE_URI

# ---------------------------------------------------------------------------
# SPARQL query registry
# ---------------------------------------------------------------------------

#: Registry mapping query name to (description, SPARQL string).
QUERIES: dict[str, tuple[str, str]] = {
    "fields-outputting-enum": (
        "Find all fields whose output type is an enum type",
        f"""\
PREFIX s2dm: <{S2DM_NAMESPACE_URI}>

SELECT ?field ?enumType
WHERE {{
    ?field a s2dm:Field ;
           s2dm:hasOutputType ?enumType .
    ?enumType a s2dm:EnumType .
}}
ORDER BY ?field
""",
    ),
    "object-types-with-fields": (
        "List all object types with their fields",
        f"""\
PREFIX s2dm: <{S2DM_NAMESPACE_URI}>

SELECT ?objectType ?field
WHERE {{
    ?objectType a s2dm:ObjectType ;
                s2dm:hasField ?field .
}}
ORDER BY ?objectType ?field
""",
    ),
    "list-type-fields": (
        "Find all fields that use a list-like type wrapper pattern",
        f"""\
PREFIX s2dm: <{S2DM_NAMESPACE_URI}>

SELECT ?field ?pattern
WHERE {{
    ?field a s2dm:Field ;
           s2dm:usesTypeWrapperPattern ?pattern .
    FILTER(?pattern IN (
        s2dm:list,
        s2dm:nonNullList,
        s2dm:listOfNonNull,
        s2dm:nonNullListOfNonNull
    ))
}}
ORDER BY ?field
""",
    ),
}


def get_query_names() -> list[str]:
    """Return sorted list of available query names.

    Returns:
        List of query name strings.
    """
    return sorted(QUERIES.keys())


def get_query_description(query_name: str) -> str:
    """Return the human-readable description for a query.

    Args:
        query_name: Key in the QUERIES registry.

    Returns:
        Description string.

    Raises:
        KeyError: If *query_name* is not in the registry.
    """
    return QUERIES[query_name][0]


def load_rdf_graph(path: Path) -> Graph:
    """Load an RDF graph from a file, detecting format by extension.

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
    ext_to_format: dict[str, str] = {ext: rdflib_fmt for rdflib_fmt, ext in FORMAT_REGISTRY.items()}

    if not path.exists():
        raise FileNotFoundError(f"RDF file not found: {path}")

    fmt = ext_to_format.get(path.suffix.lower())
    if fmt is None:
        supported = ", ".join(sorted(ext_to_format.keys()))
        raise ValueError(f"Unsupported RDF file extension '{path.suffix}'. Supported: {supported}")

    graph = Graph()
    graph.parse(str(path), format=fmt)
    return graph


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
    qres = graph.query(sparql)
    variables = [str(v) for v in qres.vars] if qres.vars else []
    results: list[dict[str, str]] = []
    for row in qres:
        if isinstance(row, ResultRow):
            results.append({var: str(val) for var, val in zip(variables, row, strict=False)})
    return results


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
