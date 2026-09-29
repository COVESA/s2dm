"""QUDT sync utilities to fetch TTLs and generate GraphQL unit enums.

This module fetches a specific released version of the QUDT (Quantities, Units,
Dimensions and Types) vocabulary and maps it onto GraphQL SDL enum types:

- Each QUDT quantity kind (e.g. `quantitykind:Velocity`) becomes one GraphQL enum
  type (e.g. `VelocityUnit`).
- Each QUDT unit associated with that quantity kind (e.g. `unit:M-PER-SEC`) becomes
  one enum value of that type (e.g. `M_PER_SEC`).
- Elements that QUDT itself marks as deprecated (via `qudt:deprecated true` on
  either the unit or its quantity kind) are intentionally excluded from the
  generated enums, not mapped in any form (e.g. as `@deprecated` enum values).
  This avoids propagating QUDT's legacy/renamed identifiers into generated
  schemas; only the current, non-deprecated vocabulary is represented. These
  excluded elements are instead recorded in a CHANGELOG.md alongside the
  generated enums, for reference/traceability.

The module focuses on the scope:
- Fetch a single QUDT units catalog TTL for a given version (default: latest known)
- Parse via RDFLib efficiently
- Group units by quantity kind and emit GraphQL enum files under
  `/units/<QuantityKind>Unit.graphql`
- Persist a simple metadata file with the synced version to support a future
  `check-version` command

References:
- QUDT main TTL (moving): `https://github.com/qudt/qudt-public-repo/blob/main/src/main/rdf/vocab/quantitykinds/VOCAB_QUDT-QUANTITY-KINDS-ALL.ttl`
- QUDT versioned TTL (e.g. 3.1.4): `https://github.com/qudt/qudt-public-repo/blob/v{version}/src/main/rdf/vocab/quantitykinds/VOCAB_QUDT-QUANTITY-KINDS-ALL.ttl`
"""

import json
import re
import shutil
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import rdflib
import requests
from graphql import build_schema
from packaging import version
from rdflib.namespace import RDFS

from s2dm import __version__ as _s2dm_version

QUDT_UNITS_TTL_URL_TEMPLATE: str = (
    "https://raw.githubusercontent.com/qudt/qudt-public-repo/{version}/src/main/rdf/vocab/unit/VOCAB_QUDT-UNITS-ALL.ttl"
)

# Quantity kinds catalog. Needed in addition to the units catalog above because
# `qudt:specializationOf` relationships between quantity kinds (e.g.
# `quantitykind:Pressure` -> `quantitykind:ForcePerArea`) are only declared here,
# not in the units catalog. Both are parsed into one merged graph so SPARQL can
# resolve unit-to-quantity-kind links together with quantity-kind specialization.
QUDT_QUANTITY_KINDS_TTL_URL_TEMPLATE: str = (
    "https://raw.githubusercontent.com/qudt/qudt-public-repo/{version}/src/main/rdf/vocab/quantitykinds/"
    "VOCAB_QUDT-QUANTITY-KINDS-ALL.ttl"
)


QUDT_GITHUB_API_URL: str = "https://api.github.com/repos/qudt/qudt-public-repo/tags"

# README file stored in the units directory root (replaces metadata.json)
UNITS_README_FILENAME: str = "README.md"
UNITS_README_VERSION_PATTERN: str = r"<!-- qudt-version: (\S+) -->"

# Changelog file recording deprecated elements excluded from the generated enums
UNITS_CHANGELOG_FILENAME: str = "CHANGELOG.md"


def _extract_uri_segment(uri: str) -> str:
    """Extract the last segment from a URI.

    Args:
        uri: The URI to extract the segment from

    Returns:
        The last segment of the URI (after the final '/')
    """
    return uri.rsplit("/", 1)[-1]


# Precompiled regex utilities to keep transformations DRY.
# GraphQL Names may only contain `[_A-Za-z][_0-9A-Za-z]*` (no spaces, hyphens,
# parentheses, slashes, etc.). Quantity kind names sourced from QUDT's rdfs:label
# or URI segments (e.g. "API Gravity") can contain such characters, so they must
# be stripped out entirely (not replaced with a separator) to keep multi-word
# names in CamelCase, and so directory segments and enum type names always match.
_ENUM_TYPE_INVALID_RE = re.compile(r"[^0-9A-Za-z_]+")
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

    E.g., "Rotary-TranslatoryMotionConversion" -> "RotaryTranslatoryMotionConversionUnit".
    Also handles labels with spaces or other GraphQL-Name-invalid characters (e.g.
    "API Gravity" -> "APIGravityUnit"), since QUDT's rdfs:label values are not
    guaranteed to be identifier-safe.
    """
    sanitized = _ENUM_TYPE_INVALID_RE.sub("", label)
    return f"{sanitized}Unit"


def _query_units(g: rdflib.Graph) -> list[UnitRow]:
    """Run SPARQL over the graph to extract units and their quantity kinds.

    Units whose `qudt:deprecated` flag is true, or whose quantity kind's
    `qudt:deprecated` flag is true, are excluded entirely (not emitted in any
    form). This keeps generated enums aligned with QUDT's current vocabulary.

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
      # QUDT renamed the unit-to-quantity-kind predicate from "hasQuantityKind" to
      # "unitForQuantityKind" around v3.4.0. Match either so both older and newer
      # catalog versions resolve units to quantity kinds.
      ?unit (qudt:hasQuantityKind|qudt:unitForQuantityKind) ?qk .

      # Filter out deprecated units (e.g., unit:Standard which is replaced by unit:STANDARD)
      # This prevents duplicate GraphQL enum symbols from deprecated/replacement unit pairs
      FILTER NOT EXISTS {{ ?unit qudt:deprecated true }}

      # Filter out units whose quantity kind is itself deprecated (e.g.,
      # quantitykind:Conductivity, replaced by quantitykind:ElectricConductivity).
      # Without this, units would be grouped under a stale quantity kind label,
      # producing an enum for a quantity kind QUDT no longer considers current.
      FILTER NOT EXISTS {{ ?qk qudt:deprecated true }}

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


def _dir_safe_name(name: str) -> str:
    """Sanitize a quantity-kind name for use as a directory name segment.

    Strips (rather than replacing with a separator) any character not valid in a
    GraphQL Name, using the same rule as `_quantity_kind_to_enum_type`, so a
    directory segment always matches its corresponding enum file name exactly
    (e.g. both render "APIGravity", never a mismatched "API_Gravity" directory
    next to an "APIGravityUnit.graphql" file).

    Args:
        name: Quantity kind name, normally the unique URI segment (e.g.
            "RotaryTranslatoryMotionConversion")

    Returns:
        A filesystem-safe, GraphQL-Name-safe directory segment

    Raises:
        UnitEnumError: If the resulting name is empty
    """
    safe = _ENUM_TYPE_INVALID_RE.sub("", name)
    if not safe:
        raise UnitEnumError(f"{UnitEnumErrorMessages.DIRECTORY_NAME_EMPTY}: '{name}'")
    return safe


def _query_quantity_kind_labels(g: rdflib.Graph) -> dict[str, str]:
    """Fetch a human-readable label for every non-deprecated quantity kind.

    Needed in addition to `_query_units` because quantity kinds with no directly
    attached units (e.g. `quantitykind:Pressure`, which only carries units via
    `qudt:specializationOf` inheritance) never appear in `_query_units` output,
    yet still need a label to build their enum type name and directory segment.

    Args:
        g: RDFLib graph containing the QUDT quantity kinds catalog

    Returns:
        Mapping of quantity kind IRI to label (falls back to the URI's last segment)
    """
    query = f"""
    PREFIX qudt: <{QUDT_NS}>
    PREFIX rdfs: <{RDFS}>

    SELECT DISTINCT ?qk ?label
    WHERE {{
      ?qk a qudt:QuantityKind .
      FILTER NOT EXISTS {{ ?qk qudt:deprecated true }}
      OPTIONAL {{
        ?qk rdfs:label ?label .
        FILTER(lang(?label) = "en" || lang(?label) = "en-US" || lang(?label) = "")
      }}
    }}
    """
    labels: dict[str, str] = {}
    for row in g.query(query):
        iri = str(row[0])  # type: ignore[index]
        labels[iri] = str(row[1]) if row[1] else _extract_uri_segment(iri)  # type: ignore[index]
    return labels


def _query_commensurability_closure(g: rdflib.Graph) -> list[tuple[str, str]]:
    """Return every (quantity kind, related kind) pair sharing inter-convertible units.

    Per QUDT's own definition of `qudt:specializationOf`, "commensurability families
    are the connected components under `(qudt:specializationOf | qudt:exactMatch)`" —
    both relations assert that units are shared/inter-convertible, so both are
    combined into a single SPARQL property path here. `qudt:specializationOf` is a
    directed parent/child relation (traversed in both directions since a parent's
    units are also applicable to its children and vice versa); `qudt:exactMatch` is
    itself typed `qudt:SymmetricRelation` by QUDT but is not always asserted in both
    directions in the source data, so it is also traversed in both directions
    explicitly here rather than relying on the data to be bidirectionally asserted.

    This closure is used only to union applicable units (via `_build_inherited_units`)
    — it must NOT be used to derive folder placement, since `qudt:exactMatch` is an
    equivalence between sibling quantity kinds, not a parent/child relation. Folder
    placement is derived solely from `qudt:specializationOf` via `_query_immediate_parents`.

    Per the SPARQL 1.1 property path semantics, arbitrary-length paths already visit
    each node at most once, so this is safe even though combining a symmetric relation
    (`qudt:exactMatch`, traversed both ways) trivially creates 2-hop cycles between
    matched pairs — those are a benign artifact of symmetry, not a modeling defect.
    Each quantity kind is included as its own ancestor (reflexive), so a kind with no
    `specializationOf`/`exactMatch` relationships still yields a single (target, target)
    pair.

    Args:
        g: RDFLib graph containing the QUDT quantity kinds catalog

    Returns:
        List of (target_iri, related_iri) pairs, both non-deprecated
    """
    query = f"""
    PREFIX qudt: <{QUDT_NS}>

    SELECT DISTINCT ?target ?related
    WHERE {{
      ?target a qudt:QuantityKind .
      FILTER NOT EXISTS {{ ?target qudt:deprecated true }}
      ?target (qudt:specializationOf|^qudt:specializationOf|qudt:exactMatch|^qudt:exactMatch)* ?related .
      FILTER NOT EXISTS {{ ?related qudt:deprecated true }}
    }}
    """
    return [(str(row[0]), str(row[1])) for row in g.query(query)]  # type: ignore[index]


def _query_immediate_parents(g: rdflib.Graph) -> dict[str, str]:
    """Return the single direct `qudt:specializationOf` parent for each quantity kind.

    Quantity kinds with more than one direct parent (ambiguous for a single-parent
    folder hierarchy) are intentionally omitted here; callers treat such kinds as
    roots. Detection of which kinds are ambiguous is done via `_query_multi_parent_quantity_kinds`,
    driven entirely by the SPARQL result rather than a hardcoded list.

    Args:
        g: RDFLib graph containing the QUDT quantity kinds catalog

    Returns:
        Mapping of quantity kind IRI to its single direct parent IRI
    """
    query = f"""
    PREFIX qudt: <{QUDT_NS}>

    SELECT ?x ?parent
    WHERE {{
      ?x qudt:specializationOf ?parent .
    }}
    """
    parents_by_child: dict[str, list[str]] = defaultdict(list)
    for row in g.query(query):
        parents_by_child[str(row[0])].append(str(row[1]))  # type: ignore[index]
    return {child: parents[0] for child, parents in parents_by_child.items() if len(parents) == 1}


def _query_multi_parent_quantity_kinds(g: rdflib.Graph) -> set[str]:
    """Return quantity kinds with more than one direct `qudt:specializationOf` parent.

    A folder hierarchy needs exactly one parent per node, so these are ambiguous and
    are treated as top-level roots instead of being nested under any one parent. This
    is determined dynamically from the model (via SPARQL `GROUP BY`/`HAVING`), not
    hardcoded to any specific quantity kind name.

    Args:
        g: RDFLib graph containing the QUDT quantity kinds catalog

    Returns:
        Set of quantity kind IRIs that have more than one distinct direct parent
    """
    query = f"""
    PREFIX qudt: <{QUDT_NS}>

    SELECT ?x (COUNT(DISTINCT ?parent) AS ?parentCount)
    WHERE {{
      ?x qudt:specializationOf ?parent .
    }}
    GROUP BY ?x
    HAVING (COUNT(DISTINCT ?parent) > 1)
    """
    return {str(row[0]) for row in g.query(query)}  # type: ignore[index]


def _build_inherited_units(
    explicit_rows: list[UnitRow], closure: list[tuple[str, str]]
) -> dict[str, dict[str, UnitRow]]:
    """Union each quantity kind's own units with those of every SPARQL-derived ancestor.

    This is a plain dictionary join of two already-computed fact tables (explicit
    unit-per-quantity-kind rows, and the commensurability closure) — no graph
    traversal or transitive reasoning happens here; that was already performed by
    `_query_commensurability_closure`'s SPARQL property path.

    Args:
        explicit_rows: Units directly attached to a quantity kind (see `_query_units`)
        closure: (target, ancestor) pairs from `_query_commensurability_closure`

    Returns:
        Mapping of quantity kind IRI to its unioned units, keyed by enum symbol
    """
    explicit_by_qk: dict[str, list[UnitRow]] = defaultdict(list)
    for row in explicit_rows:
        explicit_by_qk[row.quantity_kind_iri].append(row)

    unioned: dict[str, dict[str, UnitRow]] = defaultdict(dict)
    for target, ancestor in closure:
        for row in explicit_by_qk.get(ancestor, []):
            unioned[target].setdefault(row.symbol, row)
    return unioned


def _build_quantity_kind_paths(
    target_iris: Iterable[str],
    immediate_parents: dict[str, str],
    multi_parent_roots: set[str],
) -> dict[str, list[str]]:
    """Build a root-to-leaf list of directory-safe name segments for each quantity kind.

    Walks the single-parent map (`_query_immediate_parents`) upward from each target.
    A quantity kind with no entry in `immediate_parents` — either because it has no
    `specializationOf` parent at all, or because it was excluded for having multiple
    parents (see `_query_multi_parent_quantity_kinds`) — is treated as a root, so its
    own segment starts the path.

    Each segment is derived from the quantity kind's unique URI segment rather than
    its `rdfs:label`, since QUDT labels are not guaranteed unique (e.g. both
    `quantitykind:Volume` and `quantitykind:CartesianVolume` are labeled "Volume") —
    using the URI segment avoids two distinct quantity kinds ever colliding on the
    same directory name.

    Args:
        target_iris: Quantity kind IRIs that will get an enum file
        immediate_parents: Single direct parent per quantity kind IRI
        multi_parent_roots: Quantity kinds forced to be roots due to ambiguous parents

    Returns:
        Mapping of quantity kind IRI to its ordered list of directory-safe segments
        (root first, the quantity kind's own segment last)
    """
    paths: dict[str, list[str]] = {}
    for target in target_iris:
        segments: list[str] = []
        current: str | None = target
        visited: set[str] = set()
        while current is not None and current not in visited:
            visited.add(current)
            segments.insert(0, _dir_safe_name(_extract_uri_segment(current)))
            if current in multi_parent_roots:
                break
            current = immediate_parents.get(current)
        paths[target] = segments
    return paths


@dataclass
class DeprecatedRow:
    """A deprecated unit or quantity kind excluded from the generated enums.

    Attributes:
        iri: IRI of the deprecated element
        label: Human readable label (English or default)
        kind: Either "unit" or "quantitykind"
        deprecated_in_version: QUDT version string when deprecation was recorded, if present
        replaced_by: IRI of the replacement element, if present
    """

    iri: str
    label: str
    kind: str
    deprecated_in_version: str | None = None
    replaced_by: str | None = None


def _query_deprecated_elements(g: rdflib.Graph) -> list[DeprecatedRow]:
    """Run SPARQL to find deprecated units and quantity kinds relevant to this exporter.

    Scoped to only `qudt:Unit` and `qudt:QuantityKind` instances (the two element
    types mapped by this module), not QUDT's broader vocabulary. Used to report,
    in CHANGELOG.md, which elements were intentionally excluded from the
    generated enums because QUDT marks them as deprecated.

    Args:
        g: RDFLib graph containing QUDT units catalog

    Returns:
        List of DeprecatedRow items
    """
    query = f"""
    PREFIX qudt: <{QUDT_NS}>
    PREFIX rdfs: <{RDFS}>
    PREFIX dcterms: <http://purl.org/dc/terms/>

    SELECT DISTINCT ?x ?label ?kind ?depVersion ?replacedBy
    WHERE {{
      {{
        ?x a qudt:Unit .
        BIND("unit" AS ?kind)
      }} UNION {{
        ?x a qudt:QuantityKind .
        BIND("quantitykind" AS ?kind)
      }}
      ?x qudt:deprecated true .
      OPTIONAL {{
        ?x rdfs:label ?label .
        FILTER(lang(?label) = "en" || lang(?label) = "en-US" || lang(?label) = "")
      }}
      OPTIONAL {{ ?x qudt:deprecatedInVersion ?depVersion }}
      OPTIONAL {{ ?x dcterms:isReplacedBy ?replacedBy }}
    }}
    """

    seen: dict[str, DeprecatedRow] = {}  # iri -> DeprecatedRow

    for row in g.query(query):
        iri = str(row[0])  # type: ignore[index]
        label = str(row[1]) if row[1] else _extract_uri_segment(iri)  # type: ignore[index]
        kind = str(row[2])  # type: ignore[index]
        dep_version = str(row[3]) if row[3] else None  # type: ignore[index,misc]
        replaced_by = str(row[4]) if row[4] else None  # type: ignore[index,misc]

        if iri not in seen or (replaced_by and not seen[iri].replaced_by):
            seen[iri] = DeprecatedRow(
                iri=iri,
                label=label,
                kind=kind,
                deprecated_in_version=dep_version,
                replaced_by=replaced_by,
            )

    return list(seen.values())


def _emit_enum_sdl(quantity_kind_name: str, quantity_kind_iri: str, unit_rows: Iterable[UnitRow]) -> str:
    """Build GraphQL SDL content for a quantity kind enum.

    Uses URI-based enum values with description strings containing human-readable labels.
    Includes @reference directives linking to QUDT IRIs.

    Note: We use a custom SDL generation approach instead of graphql-core's print_type()
    because we need to include custom @reference directives that are not supported by
    the standard GraphQL specification. The generated SDL is validated using graphql-core's
    build_schema() to ensure correctness.

    The QUDT catalog version is intentionally not embedded in this file's header comment.
    It is recorded once in the directory's README.md instead, so that re-syncing an
    unchanged catalog does not touch every enum file and produce noisy diffs.

    Args:
        quantity_kind_name: Quantity kind name used to derive the enum type name,
            normally the unique URI segment (e.g., "Velocity") rather than the
            possibly-colliding `rdfs:label`
        quantity_kind_iri: QUDT IRI for the quantity kind
        unit_rows: Unit data for enum values

    Returns:
        Valid GraphQL SDL string with custom @reference directives

    Raises:
        UnitEnumError: If the generated SDL is not valid GraphQL
    """
    enum_type = _quantity_kind_to_enum_type(quantity_kind_name)

    lines = [
        "# Generated by S2DM from the QUDT unit vocabulary. See README.md in this directory for the QUDT version used.",
        "# Source data: QUDT Public Repository (https://github.com/qudt/qudt-public-repo)",
        "# © QUDT.org — Licensed under Creative Commons Attribution 4.0 International (CC BY 4.0)",
        "# License: https://creativecommons.org/licenses/by/4.0/",
        "# Changes: vocabulary terms transformed to GraphQL SDL enum format by S2DM (https://github.com/COVESA/s2dm)",
        f'enum {enum_type} @reference(uri: "{quantity_kind_iri}") {{',
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
        lines.append(f'  {row.symbol} @reference(uri: "{row.unit_iri}")')
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
directive @reference(uri: String!) on ENUM | ENUM_VALUE

{sdl}
"""
        build_schema(sdl_with_directive)
    except Exception as e:
        raise UnitEnumError(f"{UnitEnumErrorMessages.INVALID_SDL.format(enum_type=enum_type)}: {e}") from e


def _write_units(units_root: Path, dir_segments: list[str], quantity_kind_name: str, sdl: str) -> Path:
    """Write enum SDL to `/units/<Root>/.../<dir_segments>/<QuantityKind>Unit.graphql`.

    `dir_segments` is the directory the file is written into: for a quantity kind
    with descendants, this includes the quantity kind's own segment (so its file
    sits alongside its children's subdirectories); for a quantity kind with no
    descendants, this is its parent's directory (or the units root, if it has no
    parent), avoiding a pointless directory that would otherwise wrap a single file.

    Args:
        units_root: Root directory for units
        dir_segments: Directory-safe segments identifying where the file is written
        quantity_kind_name: Name used to build the enum file name, normally the
            unique URI segment (e.g. "Velocity") rather than the possibly-colliding
            `rdfs:label`
        sdl: GraphQL SDL content

    Returns:
        Path of the written file
    """
    enum_type = _quantity_kind_to_enum_type(quantity_kind_name)
    target_dir = units_root.joinpath(*dir_segments)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{enum_type}.graphql"
    target_file.write_text(sdl, encoding="utf-8")
    return target_file


def _write_readme(
    units_root: Path,
    qudt_version: str,
    s2dm_version: str,
    multi_parent_details: dict[str, list[str]],
) -> Path:
    """Write a README.md with CC BY 4.0 attribution and machine-readable version anchors.

    Args:
        units_root: Root directory for units
        qudt_version: QUDT version this snapshot was read from
        s2dm_version: S2DM version that generated this snapshot
        multi_parent_details: Quantity kinds with more than one direct
            `specializationOf` parent, mapped to their parent IRIs. These are
            placed at the top level of the directory tree instead of being nested
            under either parent, since a folder hierarchy needs one parent per node.

    Returns:
        Path of the written file
    """
    units_root.mkdir(parents=True, exist_ok=True)
    readme_path = units_root / UNITS_README_FILENAME

    if multi_parent_details:
        roots_lines = ["| Quantity Kind | Parents |", "|---|---|"]
        for iri, parents in sorted(multi_parent_details.items()):
            parent_names = ", ".join(f"`{_extract_uri_segment(p)}`" for p in sorted(parents))
            roots_lines.append(f"| `{_extract_uri_segment(iri)}` | {parent_names} |")
        roots_section = "\n".join(roots_lines)
    else:
        roots_section = "_None in this release._"

    content = f"""<!-- qudt-version: {qudt_version} -->
<!-- s2dm-version: {s2dm_version} -->
# QUDT Units — Generated by S2DM

This directory contains GraphQL SDL enum files generated from the
[QUDT (Quantities, Units, Dimensions and Types)](https://qudt.org/) reference model.

## Attribution

Source data: [QUDT Public Repository](https://github.com/qudt/qudt-public-repo)

© QUDT.org — Licensed under
[Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)

Changes: vocabulary terms transformed to GraphQL SDL enum format by
[S2DM](https://github.com/COVESA/s2dm)

## Provenance

| Field | Value |
|---|---|
| QUDT catalog version | `{qudt_version}` |
| S2DM version | `{s2dm_version}` |

Elements deprecated in QUDT (units and quantity kinds intentionally not mapped
above) are listed in [CHANGELOG.md](./CHANGELOG.md), or can be inspected directly
at the [QUDT `{qudt_version}` release page](https://github.com/qudt/qudt-public-repo/releases/tag/{qudt_version}).

## Directory Structure

Enum files are nested to mirror QUDT's `qudt:specializationOf` hierarchy between
quantity kinds (most generic first). A quantity kind inherits every unit of its
ancestors, in addition to any units attached to it directly (e.g. units on
`ForcePerArea` are also available on `Pressure`, since Pressure specializes
ForcePerArea).

## Quantity Kinds Treated as Roots (Multiple Specializations)

These quantity kinds have more than one direct `qudt:specializationOf` parent in
this release. Since a directory tree needs exactly one parent per node, they are
placed at the top level instead of being nested under either parent (their
generated enums still include units inherited from *both* parents):

{roots_section}

## Usage

Run `s2dm units sync` to regenerate these files from the latest QUDT catalog.
"""
    readme_path.write_text(content, encoding="utf-8")
    return readme_path


def _write_changelog(
    units_root: Path,
    qudt_version: str,
    deprecated: list[DeprecatedRow],
    skipped_quantity_kinds: list[tuple[str, str]],
) -> Path:
    """Write CHANGELOG.md listing quantity kinds and units excluded as deprecated.

    Scoped to only the two element types this module maps (units and quantity
    kinds), not QUDT's full vocabulary.

    Args:
        units_root: Root directory for units
        qudt_version: QUDT version this snapshot was read from
        deprecated: Deprecated units/quantity kinds found in this release
        skipped_quantity_kinds: (IRI, label) pairs for non-deprecated quantity kinds
            that have no applicable units at all — neither directly attached nor
            inherited via `qudt:specializationOf` — and so got no generated enum

    Returns:
        Path of the written file
    """
    units_root.mkdir(parents=True, exist_ok=True)
    changelog_path = units_root / UNITS_CHANGELOG_FILENAME

    quantity_kinds = sorted((d for d in deprecated if d.kind == "quantitykind"), key=lambda d: d.label)
    units = sorted((d for d in deprecated if d.kind == "unit"), key=lambda d: d.label)

    def _table(rows: list[DeprecatedRow]) -> list[str]:
        if not rows:
            return ["_None in this release._", ""]
        lines = ["| Label | IRI | Deprecated in | Replaced by |", "|---|---|---|---|"]
        for d in rows:
            dep_in = d.deprecated_in_version or "—"
            replaced = f"`{_extract_uri_segment(d.replaced_by)}`" if d.replaced_by else "—"
            lines.append(f"| {d.label} | `{d.iri}` | {dep_in} | {replaced} |")
        lines.append("")
        return lines

    if skipped_quantity_kinds:
        skipped_lines = ["| Label | IRI |", "|---|---|"]
        for iri, label in skipped_quantity_kinds:
            skipped_lines.append(f"| {label} | `{iri}` |")
        skipped_lines.append("")
    else:
        skipped_lines = ["_None in this release._", ""]

    content_lines = [
        f"<!-- qudt-version: {qudt_version} -->",
        "# QUDT Deprecations — as reported by S2DM",
        "",
        f"Snapshot of quantity kinds and units marked `qudt:deprecated true` in QUDT "
        f"catalog version `{qudt_version}`. These elements are intentionally excluded "
        "from the generated GraphQL enums (see README.md) and are listed here only "
        "for reference/traceability.",
        "",
        "## Deprecated Quantity Kinds",
        "",
        *_table(quantity_kinds),
        "## Deprecated Units",
        "",
        *_table(units),
        "## Quantity Kinds Excluded (No Applicable Units)",
        "",
        "Non-deprecated quantity kinds with no units attached directly, and none "
        "inherited from any `qudt:specializationOf` ancestor, so no enum was generated:",
        "",
        *skipped_lines,
    ]
    changelog_path.write_text("\n".join(content_lines) + "\n", encoding="utf-8")
    return changelog_path


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


def _load_merged_graph_from_urls(urls: Iterable[str]) -> rdflib.Graph:
    """Load and merge multiple TTL sources into a single RDFLib graph.

    Used to combine the units catalog (unit-to-quantity-kind links) with the
    quantity kinds catalog (`qudt:specializationOf` relationships) so a single
    SPARQL query can reason across both.

    Args:
        urls: Direct raw URLs to TTL resources
    Returns:
        Parsed RDF graph containing the union of all sources' triples
    """
    g = rdflib.Graph()
    for url in urls:
        g.parse(url, format="turtle")
    return g


def _query_parents_for_iris(g: rdflib.Graph, iris: set[str]) -> dict[str, list[str]]:
    """Return every direct `qudt:specializationOf` parent for the given quantity kinds.

    Used only for reporting ambiguous (multi-parent) quantity kinds in README.md
    with their actual parent IRIs.

    Args:
        g: RDFLib graph containing the QUDT quantity kinds catalog
        iris: Quantity kind IRIs to fetch parents for

    Returns:
        Mapping of quantity kind IRI to its list of direct parent IRIs
    """
    if not iris:
        return {}
    values_clause = " ".join(f"<{iri}>" for iri in sorted(iris))
    query = f"""
    PREFIX qudt: <{QUDT_NS}>

    SELECT ?x ?parent
    WHERE {{
      VALUES ?x {{ {values_clause} }}
      ?x qudt:specializationOf ?parent .
    }}
    """
    result: dict[str, list[str]] = defaultdict(list)
    for row in g.query(query):
        result[str(row[0])].append(str(row[1]))  # type: ignore[index]
    return result


def sync_qudt_units(units_root: Path, version: str, *, dry_run: bool = False) -> list[Path]:
    """Fetch a specific QUDT release and generate GraphQL enums per quantity kind.

    Reads the QUDT units and quantity kinds catalogs for the given release and maps
    them onto GraphQL SDL enum types: each quantity kind (e.g. `quantitykind:Velocity`)
    becomes one enum type (e.g. `VelocityUnit`), and each unit applicable to that
    quantity kind becomes one enum value. A unit is applicable to a quantity kind if
    it is directly attached to it, or attached to any quantity kind reachable via
    `qudt:specializationOf` (e.g. units attached to `quantitykind:ForcePerArea` are
    also applicable to `quantitykind:Pressure`, since Pressure specializes
    ForcePerArea) or via `qudt:exactMatch` (e.g. `quantitykind:Radioactivity` has no
    units of its own but is an exact match of `quantitykind:Activity`, so it inherits
    Activity's units) — the full closure and its cycle-safety are resolved via a
    SPARQL property path, not Python-side graph traversal. Generated enum files are
    nested into directories that mirror the `qudt:specializationOf` hierarchy only
    (most generic quantity kind first); `qudt:exactMatch` is an equivalence between
    sibling quantity kinds, not a parent/child relation, so it never affects folder
    placement — a quantity kind whose only units come from an `exactMatch` partner
    still keeps its own position (or becomes its own root) in the specialization tree,
    just with duplicated enum content. A quantity kind only gets its own directory if
    it is the `specializationOf` parent of at least one other emitted quantity kind;
    otherwise its file is written directly into its parent's directory (or the units
    root, if it has no parent), avoiding a directory that would otherwise wrap a
    single file. Directory and enum type names are both derived from each quantity
    kind's unique URI segment rather than its `rdfs:label`, since QUDT labels are not
    guaranteed unique across distinct quantity kinds.

    Elements that QUDT marks as deprecated in that release (units or their quantity
    kind) are intentionally not mapped and are ignored. Quantity kinds with no
    applicable units at all (neither explicit nor inherited) are skipped entirely and
    reported in CHANGELOG.md. Quantity kinds with more than one direct
    `specializationOf` parent are ambiguous for a single-parent folder hierarchy and
    are treated as top-level roots instead of being nested under either parent
    (reported in README.md). A CHANGELOG.md listing deprecated and skipped elements is
    written alongside the generated enums (skipped in dry-run mode).

    Cleans up existing unit enum files before generating new ones to prevent stale data.

    Args:
        units_root: Root `/units/` target directory
        version: QUDT version string. If None, use main branch (latest moving target)
        dry_run: If True, process data but don't write files (for counting/testing)
    Returns:
        List of enum file paths that were written (or would be written in dry-run mode)
    """
    # Clean up existing files before sync (but not during dry run)
    if not dry_run and units_root.exists():
        try:
            shutil.rmtree(units_root)
        except OSError as e:
            raise UnitEnumError(f"Failed to clean up units directory: {e}") from e

    units_url = QUDT_UNITS_TTL_URL_TEMPLATE.format(version=version)
    quantity_kinds_url = QUDT_QUANTITY_KINDS_TTL_URL_TEMPLATE.format(version=version)
    g = _load_merged_graph_from_urls([units_url, quantity_kinds_url])

    explicit_rows = _query_units(g)
    deprecated_rows = _query_deprecated_elements(g)
    closure = _query_commensurability_closure(g)
    immediate_parents = _query_immediate_parents(g)
    multi_parent_roots = _query_multi_parent_quantity_kinds(g)
    qk_labels = _query_quantity_kind_labels(g)

    unioned_units = _build_inherited_units(explicit_rows, closure)
    target_iris = sorted(unioned_units.keys())
    paths = _build_quantity_kind_paths(target_iris, immediate_parents, multi_parent_roots)

    # Quantity kinds that are the immediate `specializationOf` parent of at least one
    # other emitted quantity kind need their own directory (to hold their own file
    # alongside their children's subdirectories). A quantity kind with no such
    # children gets its file written directly into its parent's directory instead of
    # a directory named after itself wrapping a single file.
    parents_with_children = {immediate_parents[iri] for iri in target_iris if iri in immediate_parents}

    written: list[Path] = []

    for qk_iri in target_iris:
        qk_name = _extract_uri_segment(qk_iri)
        items = list(unioned_units[qk_iri].values())
        sdl = _emit_enum_sdl(qk_name, qk_iri, items)
        path_segments = paths[qk_iri]
        dir_segments = path_segments if qk_iri in parents_with_children else path_segments[:-1]

        if dry_run:
            # Simulate the file path that would be written without actually writing
            enum_type = _quantity_kind_to_enum_type(qk_name)
            target_file = units_root.joinpath(*dir_segments, f"{enum_type}.graphql")
            written.append(target_file)
        else:
            written.append(_write_units(units_root, dir_segments, qk_name, sdl))

    if not dry_run:
        # Quantity kinds with no explicit or inherited units at all (per point 5:
        # log/report, don't generate an empty enum for them).
        skipped = sorted(
            ((iri, label) for iri, label in qk_labels.items() if iri not in unioned_units),
            key=lambda item: item[1],
        )
        multi_parent_details = _query_parents_for_iris(g, multi_parent_roots)

        _write_readme(units_root, version, _s2dm_version, multi_parent_details)
        _write_changelog(units_root, version, deprecated_rows, skipped)
    return written


def get_latest_qudt_version(fallback: str = "main") -> str:
    """Return a string representing the latest known QUDT tag for the public repo.

    Minimal, non-overengineered approach: read Git tags via GitHub's tags API.
    We avoid adding heavy dependencies; this can be replaced later if needed.
    """
    try:
        resp = requests.get(QUDT_GITHUB_API_URL, timeout=10)
        resp.raise_for_status()
        tags = resp.json()

        if not tags:
            return fallback

        # Pick the latest version
        latest_tag = max(tags, key=lambda tag: version.parse(tag["name"]))
        return str(latest_tag["name"])
    except (requests.RequestException, json.JSONDecodeError, version.InvalidVersion):
        return fallback
