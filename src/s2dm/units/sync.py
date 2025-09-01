"""QUDT sync utilities to fetch TTLs and generate GraphQL unit enums.

This module focuses on the scope:
- Fetch a single QUDT quantity kinds catalog TTL for a given version (default: latest known)
- Parse via RDFLib efficiently
- Group units by quantity kind and emit GraphQL enum files under
  `/units/<quantityKind>/<QuantityKind>_Unit_Enum.graphql`
- Persist a simple metadata file with the synced version to support a future
  `check-version` command

References:
- QUDT main TTL (moving): `https://github.com/qudt/qudt-public-repo/blob/main/src/main/rdf/vocab/quantitykinds/VOCAB_QUDT-QUANTITY-KINDS-ALL.ttl`
- QUDT versioned TTL (e.g. 3.1.4): `https://github.com/qudt/qudt-public-repo/blob/v{version}/src/main/rdf/vocab/quantitykinds/VOCAB_QUDT-QUANTITY-KINDS-ALL.ttl`
"""

import json
import re
import urllib.request
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import rdflib
from graphql import build_schema
from rdflib.namespace import RDFS

QUDT_UNITS_TTL_URL_TEMPLATE: str = (
    "https://raw.githubusercontent.com/qudt/qudt-public-repo/v{version}/src/main/rdf/vocab/unit/"
    "VOCAB_QUDT-UNITS-ALL.ttl"
)

QUDT_UNITS_TTL_URL_MAIN: str = (
    "https://raw.githubusercontent.com/qudt/qudt-public-repo/main/src/main/rdf/vocab/unit/VOCAB_QUDT-UNITS-ALL.ttl"
)

QUDT_GITHUB_API_URL: str = "https://api.github.com/repos/qudt/qudt-public-repo/tags"

# Metadata file stored in the units directory root
UNITS_META_FILENAME: str = "metadata.json"
UNITS_META_VERSION_KEY: str = "qudt_quantitykinds_version"


def _extract_uri_segment(uri: str) -> str:
    """Extract the last segment from a URI.

    Args:
        uri: The URI to extract the segment from

    Returns:
        The last segment of the URI (after the final '/')
    """
    return uri.rsplit("/", 1)[-1]


# Precompiled regex utilities to keep transformations DRY
_DIR_SAFE_RE = re.compile(r"[^0-9A-Za-z_-]+")
QUDT_NS = rdflib.Namespace("http://qudt.org/schema/qudt/")


class UnitEnumError(ValueError):
    """Raised when a unit enum symbol cannot be derived from input.

    This error indicates that the provided input string cannot be transformed
    into a valid SCREAMING_SNAKE_CASE enum value (e.g., because it is empty
    or reduces to no alphanumeric content after cleaning).
    """


# Error message constants for consistent messaging and testability
class UnitEnumErrorMessages:
    """Standard error messages for UnitEnumError exceptions."""

    URI_SEGMENT_EMPTY = "Cannot extract URI segment from"
    ENUM_SYMBOL_EMPTY = "Cannot derive enum symbol from URI segment"
    QUANTITY_KIND_EMPTY = "Cannot derive quantity kind enum type from empty or invalid label"
    DIRECTORY_NAME_EMPTY = "Cannot derive directory name from empty or invalid quantity kind label"
    INVALID_SDL = "Generated SDL for {enum_type} is not valid GraphQL"


@dataclass
class UnitRow:
    """A single unit row from the SPARQL result.

    Attributes:
        unit_iri: IRI of the unit
        unit_label: Human readable label (English or default)
        quantity_kind_iri: IRI of the quantity kind
        quantity_kind_label: Human readable label for the quantity kind (English or default)
        symbol: Suggested enum symbol (screaming snake case)
        ucum_code: UCUM code if available
    """

    unit_iri: str
    unit_label: str
    quantity_kind_iri: str
    quantity_kind_label: str
    symbol: str
    ucum_code: str | None = None


def _uri_to_enum_symbol(uri: str) -> str:
    """Convert a QUDT unit URI to a valid GraphQL enum symbol.

    Uses a simple approach: uppercase the URI segment and replace separators with underscores.
    QUDT URI segments only use hyphens (-) and underscores (_) as separators, making this
    approach both simple and effective (e.g., "PicoMOL-PER-KiloGM" → "PICOMOL_PER_KILOGM").

    Args:
        uri: QUDT unit URI (e.g., "http://qudt.org/vocab/unit/PicoMOL-PER-KiloGM")

    Returns:
        Valid GraphQL enum symbol in SCREAMING_SNAKE_CASE

    Raises:
        UnitEnumError: If a valid enum symbol cannot be derived from the URI.
    """
    # Extract the last segment of the URI
    uri_segment = _extract_uri_segment(uri)

    if not uri_segment:
        raise UnitEnumError(f"{UnitEnumErrorMessages.URI_SEGMENT_EMPTY}: '{uri}'")

    # Simple case conversion: uppercase and replace separators with underscores
    # QUDT URI segments primarily use hyphens (-) and underscores (_), with rare edge cases
    symbol = uri_segment.upper().replace("-", "_").replace(".", "_")

    if not symbol:
        raise UnitEnumError(f"{UnitEnumErrorMessages.ENUM_SYMBOL_EMPTY}: '{uri_segment}'")

    # Ensure it starts with a letter or underscore (GraphQL requirement)
    # E.g 2PiRAD -> _2PiRAD
    if symbol[0].isdigit():
        symbol = f"_{symbol}"

    return symbol


def _quantity_kind_to_enum_type(label: str) -> str:
    """Turn a quantity kind label into an enum type name.

    E.g., "Rotary-TranslatoryMotionConversion" -> "RotaryTranslatoryMotionConversionUnitEnum".
    """
    label = label.replace("-", "")
    return f"{label}UnitEnum"


def _query_units(g: rdflib.Graph) -> list[UnitRow]:
    """Run SPARQL over the graph to extract units and their quantity kinds.

    Args:
        g: RDFLib graph containing QUDT units catalog

    Returns:
        List of UnitRow items
    """

    # Filter for language labels (English or default)
    query = f"""
    PREFIX qudt: <{QUDT_NS}>
    PREFIX rdfs: <{RDFS}>

    SELECT DISTINCT ?unit ?unitLabel ?qk ?qkLabel ?ucumCode
    WHERE {{
      ?unit a qudt:Unit .
      ?unit qudt:hasQuantityKind ?qk .

      # Filter out deprecated units (e.g., unit:Standard which is replaced by unit:STANDARD)
      # This prevents duplicate GraphQL enum symbols from deprecated/replacement unit pairs
      FILTER NOT EXISTS {{ ?unit qudt:deprecated true }}

      OPTIONAL {{
        ?unit rdfs:label ?unitLabel .
        FILTER(lang(?unitLabel) = "en" || lang(?unitLabel) = "en-US" || lang(?unitLabel) = "")
      }}
      OPTIONAL {{
        ?qk rdfs:label ?qkLabel .
        FILTER(lang(?qkLabel) = "en" || lang(?qkLabel) = "en-US" || lang(?qkLabel) = "")
      }}
      OPTIONAL {{ ?unit qudt:ucumCode ?ucumCode }}
    }}
    """

    seen_units: dict[tuple[str, str], UnitRow] = {}  # (symbol, qk_iri) -> UnitRow

    for row in g.query(query):
        unit_iri = str(row[0])  # type: ignore[index]
        unit_label = str(row[1]) if row[1] else ""  # type: ignore[index]
        qk_iri = str(row[2])  # type: ignore[index]
        qk_label = str(row[3]) if row[3] else _extract_uri_segment(qk_iri)  # type: ignore[index,misc]
        ucum_code = str(row[4]) if row[4] else None  # type: ignore[index,misc]

        try:
            # Use URI-based symbol generation (always reliable)
            symbol = _uri_to_enum_symbol(unit_iri)
        except UnitEnumError:
            # Skip this unit if we can't generate a valid symbol from URI
            continue

        # Deduplicate based on symbol and quantity kind IRI to prevent duplicate enum values
        unit_key = (symbol, qk_iri)
        unit_row = UnitRow(
            unit_iri=unit_iri,
            unit_label=unit_label,
            quantity_kind_iri=qk_iri,
            quantity_kind_label=qk_label,
            symbol=symbol,
            ucum_code=ucum_code,
        )

        # Prefer entries with UCUM codes when deduplicating
        if unit_key not in seen_units or (ucum_code and not seen_units[unit_key].ucum_code):
            seen_units[unit_key] = unit_row

    return list(seen_units.values())


def _emit_enum_sdl(quantity_kind_label: str, quantity_kind_iri: str, unit_rows: Iterable[UnitRow], version: str) -> str:
    """Build GraphQL SDL content for a quantity kind enum.

    Uses URI-based enum values with description strings containing human-readable labels.
    Includes @reference directives linking to QUDT IRIs with version tags.

    Note: We use a custom SDL generation approach instead of graphql-core's print_type()
    because we need to include custom @reference directives that are not supported by
    the standard GraphQL specification. The generated SDL is validated using graphql-core's
    build_schema() to ensure correctness.

    Args:
        quantity_kind_label: Human-readable label for the quantity kind (e.g., "Velocity")
        quantity_kind_iri: QUDT IRI for the quantity kind
        unit_rows: Unit data for enum values
        version: QUDT version for documentation and version tag

    Returns:
        Valid GraphQL SDL string with custom @reference directives including versionTag

    Raises:
        UnitEnumError: If the generated SDL is not valid GraphQL
    """
    enum_type = _quantity_kind_to_enum_type(quantity_kind_label)

    lines = [
        f"# Generated from QUDT units catalog version {version}",
        f'enum {enum_type} @reference(uri: "{quantity_kind_iri}", versionTag: "{version}") {{',
    ]

    for row in sorted(unit_rows, key=lambda r: r.symbol):
        # Build description string with label and UCUM code
        description_parts = []
        if row.unit_label:
            description_parts.append(row.unit_label)
        if row.ucum_code:
            description_parts.append(f"UCUM: {row.ucum_code}")

        description = " | ".join(description_parts) if description_parts else row.symbol

        lines.append(f'  """{description}"""')
        lines.append(f'  {row.symbol} @reference(uri: "{row.unit_iri}", versionTag: "{version}")')
        lines.append("")  # Empty line for readability

    # Remove the last empty line and add closing brace
    if lines and lines[-1] == "":
        lines.pop()
    lines.append("}")

    # Generate the SDL and validate it
    sdl = "\n".join(lines) + "\n"
    _validate_enum_sdl(sdl, enum_type)
    return sdl


def _validate_enum_sdl(sdl: str, enum_type: str) -> None:
    """Validate that the generated SDL is valid GraphQL.

    Args:
        sdl: The SDL string to validate
        enum_type: The enum type name for error reporting

    Raises:
        UnitEnumError: If the SDL is not valid GraphQL
    """
    try:
        # Add the @reference directive definition needed for validation
        sdl_with_directive = f"""
directive @reference(uri: String!, versionTag: String) on ENUM | ENUM_VALUE

{sdl}
"""
        build_schema(sdl_with_directive)
    except Exception as e:
        raise UnitEnumError(f"{UnitEnumErrorMessages.INVALID_SDL.format(enum_type=enum_type)}: {e}") from e


def _write_units(units_root: Path, quantity_kind_label: str, sdl: str) -> Path:
    """Write enum SDL to `/units/<quantityKind>/<QuantityKind>_Unit_Enum.graphql`.

    Args:
        units_root: Root directory for units
        quantity_kind_label: Label used to build directory and enum file names
        sdl: GraphQL SDL content

    Returns:
        Path of the written file
    """
    enum_type = _quantity_kind_to_enum_type(quantity_kind_label)
    target_dir = units_root
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{enum_type}.graphql"
    target_file.write_text(sdl, encoding="utf-8")
    return target_file


def _write_metadata(units_root: Path, version: str) -> Path:
    """Persist a minimal metadata JSON with the synced version."""
    units_root.mkdir(parents=True, exist_ok=True)
    meta_path = units_root / UNITS_META_FILENAME
    metadata = {UNITS_META_VERSION_KEY: version}
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return meta_path


def _cleanup_units_directory(units_root: Path) -> None:
    """Clean up existing unit enum files and metadata from the units directory.

    Removes all *.graphql files and metadata.json to ensure a fresh sync.
    This prevents stale files from previous syncs when units are deprecated,
    renamed, or the catalog structure changes.

    Args:
        units_root: Root directory containing unit enums
    """
    if not units_root.exists():
        return

    # Remove all GraphQL enum files
    for graphql_file in units_root.glob("**/*.graphql"):
        graphql_file.unlink()

    # Remove metadata file if it exists
    metadata_file = units_root / UNITS_META_FILENAME
    if metadata_file.exists():
        metadata_file.unlink()

    # Remove empty directories (but keep the root directory)
    for item in units_root.iterdir():
        if item.is_dir() and not any(item.iterdir()):
            item.rmdir()


def _load_graph_from_url(url: str) -> rdflib.Graph:
    """Load a TTL file from a URL directly into an RDFLib graph.

    Args:
        url: Direct raw URL to a TTL resource
    Returns:
        Parsed RDF graph
    """
    g = rdflib.Graph()
    # RDFLib can parse remote URLs directly when given a format
    g.parse(url, format="turtle")
    return g


def sync_qudt_units(units_root: Path, version: str | None = None, *, dry_run: bool = False) -> list[Path]:
    """Fetch QUDT quantity kinds TTL and generate GraphQL enums per quantity kind.

    Cleans up existing unit enum files before generating new ones to prevent stale data.

    Args:
        units_root: Root `/units/` target directory
        version: QUDT version string. If None, use main branch (latest moving target)
        dry_run: If True, process data but don't write files (for counting/testing)
    Returns:
        List of enum file paths that were written (or would be written in dry-run mode)
    """
    # Clean up existing files before sync (but not during dry run)
    if not dry_run:
        _cleanup_units_directory(units_root)

    url = QUDT_UNITS_TTL_URL_MAIN if version is None else QUDT_UNITS_TTL_URL_TEMPLATE.format(version=version)

    g = _load_graph_from_url(url)
    rows = _query_units(g)

    # Group rows by quantity kind label
    grouped: dict[str, list[UnitRow]] = defaultdict(list)
    for row in rows:
        grouped[row.quantity_kind_label].append(row)

    written: list[Path] = []
    effective_version = version or "main"

    for qk_label, items in grouped.items():
        if not items:  # Skip empty groups
            continue
        qk_iri = items[0].quantity_kind_iri
        sdl = _emit_enum_sdl(qk_label, qk_iri, items, effective_version)

        if dry_run:
            # Simulate the file path that would be written without actually writing
            enum_type = _quantity_kind_to_enum_type(qk_label)
            target_file = units_root / f"{enum_type}.graphql"
            written.append(target_file)
        else:
            written.append(_write_units(units_root, qk_label, sdl))

    if not dry_run:
        _write_metadata(units_root, effective_version)
    return written


def check_latest_qudt_version() -> str:
    """Return a string representing the latest known QUDT tag for the public repo.

    Minimal, non-overengineered approach: read Git tags via GitHub's tags API.
    We avoid adding heavy dependencies; this can be replaced later if needed.
    """
    with urllib.request.urlopen(QUDT_GITHUB_API_URL) as resp:  # nosec - public metadata
        data = json.loads(resp.read().decode("utf-8"))
    # Tags are objects with 'name', e.g., 'v3.1.4'. Pick the first entry.
    if not data:
        return "main"
    name = data[0]["name"]
    # Ensure it starts with 'v'
    return name.lstrip("v")  # type: ignore[no-any-return]
