"""RDF materialization of GraphQL schemas using SKOS and s2dm ontology.

This module materializes GraphQL SDL into RDF triples with:
- SKOS skeleton (skos:Concept, skos:prefLabel, skos:definition)
- s2dm ontology instantiation (ObjectType, InterfaceType, InputObjectType,
  UnionType, EnumType, Field, EnumValue, hasField, hasOutputType,
  hasEnumValue, hasUnionMember, usesTypeWrapperPattern)
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from graphql import (
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLSchema,
    GraphQLUnionType,
    get_named_type,
)
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, SKOS
from rdflib.term import Node

from s2dm.exporters.skos import S2DM
from s2dm.exporters.utils.extraction import get_all_named_types
from s2dm.exporters.utils.field import field_case_to_type_wrapper_pattern, get_field_case
from s2dm.exporters.utils.graphql_type import is_introspection_or_root_type

# Built-in GraphQL scalars (use s2dm: namespace)
BUILTIN_SCALARS = frozenset({"Int", "Float", "String", "Boolean", "ID"})


@dataclass
class RdfFieldInfo:
    """Field metadata for RDF materialization.

    Args:
        field_fqn: Fully qualified field name (e.g., "Cabin.doors")
        output_type_name: Name of the output type (e.g., "Door", "Boolean")
        type_wrapper_pattern: s2dm TypeWrapperPattern (e.g., "list", "nonNull")
    """

    field_fqn: str
    output_type_name: str
    type_wrapper_pattern: str


@dataclass
class RdfFieldContainerType:
    """Object, interface, or input type with fields for RDF materialization.

    Args:
        name: GraphQL type name
        description: Optional type description from schema
        fields: List of field metadata
    """

    name: str
    description: str
    fields: list[RdfFieldInfo] = field(default_factory=list)


@dataclass
class RdfEnumType:
    """Enum type for RDF materialization.

    Args:
        name: GraphQL enum type name
        description: Optional enum description from schema
        values: List of enum value names
    """

    name: str
    description: str
    values: list[str] = field(default_factory=list)


@dataclass
class RdfUnionType:
    """Union type for RDF materialization.

    Args:
        name: GraphQL union type name
        description: Optional union description from schema
        member_type_names: List of member type names
    """

    name: str
    description: str
    member_type_names: list[str] = field(default_factory=list)


@dataclass
class RdfSchemaExtract:
    """Extracted schema data for RDF materialization.

    Args:
        object_types: Object types with their fields
        interface_types: Interface types with their fields
        input_object_types: Input object types with their fields
        union_types: Union types with their member types
        enum_types: Enum types with their values
    """

    object_types: list[RdfFieldContainerType] = field(default_factory=list)
    interface_types: list[RdfFieldContainerType] = field(default_factory=list)
    input_object_types: list[RdfFieldContainerType] = field(default_factory=list)
    union_types: list[RdfUnionType] = field(default_factory=list)
    enum_types: list[RdfEnumType] = field(default_factory=list)


def _get_fields_from_container(
    container: GraphQLObjectType | GraphQLInterfaceType | GraphQLInputObjectType,
) -> dict[str, Any]:
    """Get fields dict from a type that has fields (Object, Interface, or InputObject).

    InputObjectType uses input_fields in GraphQL spec; graphql-core may expose as fields.
    """
    return cast(dict[str, Any], getattr(container, "input_fields", container.fields))


def _extract_fields_from_container(
    container: GraphQLObjectType | GraphQLInterfaceType | GraphQLInputObjectType,
    type_name: str,
) -> list[RdfFieldInfo]:
    """Extract field metadata from an object, interface, or input type."""
    fields_info: list[RdfFieldInfo] = []
    fields_dict = _get_fields_from_container(container)

    for field_name, graphql_field in fields_dict.items():
        output_type = get_named_type(graphql_field.type)
        output_type_name = output_type.name
        field_case = get_field_case(graphql_field)
        type_wrapper_pattern = field_case_to_type_wrapper_pattern(field_case)

        field_fqn = f"{type_name}.{field_name}"
        fields_info.append(
            RdfFieldInfo(
                field_fqn=field_fqn,
                output_type_name=output_type_name,
                type_wrapper_pattern=type_wrapper_pattern,
            )
        )

    return fields_info


_CONTAINER_TYPE_TO_ATTR: dict[type, str] = {
    GraphQLObjectType: "object_types",
    GraphQLInterfaceType: "interface_types",
    GraphQLInputObjectType: "input_object_types",
}


def _get_description(obj: object) -> str:
    """Get description from a GraphQL type, or empty string if absent."""
    return getattr(obj, "description", None) or ""


def extract_schema_for_rdf(schema: GraphQLSchema) -> RdfSchemaExtract:
    """Extract schema elements for RDF materialization.

    Extracts ObjectType, InterfaceType, InputObjectType, UnionType, and
    EnumType with all fields (including object refs, lists, ID fields).

    Args:
        schema: The GraphQL schema to extract from.

    Returns:
        RdfSchemaExtract with all extracted types.
    """
    result = RdfSchemaExtract()
    named_types = get_all_named_types(schema)

    for named_type in named_types:
        if is_introspection_or_root_type(named_type.name):
            continue

        if isinstance(
            named_type,
            GraphQLObjectType | GraphQLInterfaceType | GraphQLInputObjectType,
        ):
            graphql_container = cast(  # type: ignore[redundant-cast]
                GraphQLObjectType | GraphQLInterfaceType | GraphQLInputObjectType,
                named_type,
            )
            for graphql_cls, attr in _CONTAINER_TYPE_TO_ATTR.items():
                if isinstance(named_type, graphql_cls):
                    fields_info = _extract_fields_from_container(graphql_container, named_type.name)
                    container = RdfFieldContainerType(
                        name=named_type.name,
                        description=_get_description(named_type),
                        fields=fields_info,
                    )
                    getattr(result, attr).append(container)
                    break

        elif isinstance(named_type, GraphQLUnionType):
            member_names = [t.name for t in named_type.types]
            result.union_types.append(
                RdfUnionType(
                    name=named_type.name,
                    description=_get_description(named_type),
                    member_type_names=member_names,
                )
            )

        elif isinstance(named_type, GraphQLEnumType):
            result.enum_types.append(
                RdfEnumType(
                    name=named_type.name,
                    description=_get_description(named_type),
                    values=list(named_type.values.keys()),
                )
            )

    return result


# Type for optional directive-to-triples handler (for future extensibility).
DirectiveTripleHandler = Callable[[Graph, RdfSchemaExtract, Namespace, str, str], None]


def _add_concept_header(
    graph: Graph,
    uri: Node,
    pref_label: str,
    description: str,
    s2dm_type: Node,
    language: str,
) -> None:
    """Add SKOS concept header triples (rdf:type, prefLabel, optional definition).

    Args:
        graph: RDF graph to add triples to.
        uri: Concept URI (rdflib term).
        pref_label: Value for skos:prefLabel.
        description: Optional description for skos:definition.
        s2dm_type: S2DM type term (e.g., S2DM.ObjectType).
        language: BCP 47 language tag for prefLabel.
    """
    graph.add((uri, RDF.type, SKOS.Concept))
    graph.add((uri, RDF.type, s2dm_type))
    graph.add((uri, SKOS.prefLabel, Literal(pref_label, lang=language)))
    stripped_description = description.strip()
    if stripped_description:
        graph.add((uri, SKOS.definition, Literal(stripped_description)))


def materialize_schema_to_rdf(
    schema: GraphQLSchema,
    namespace: str,
    prefix: str,
    language: str = "en",
    directive_triple_handler: DirectiveTripleHandler | None = None,
) -> Graph:
    """Materialize a GraphQL schema to RDF triples using SKOS and s2dm ontology.

    Produces triples for:
    - ObjectType (rdf:type skos:Concept, s2dm:ObjectType)
    - Field (s2dm:hasField, s2dm:hasOutputType, s2dm:usesTypeWrapperPattern)
    - EnumType (rdf:type skos:Concept, s2dm:EnumType)
    - EnumValue (s2dm:hasEnumValue, rdf:type s2dm:EnumValue)

    Args:
        schema: The GraphQL schema to materialize.
        namespace: URI namespace for concept URIs.
        prefix: Prefix for concept URIs (e.g., "ns").
        language: BCP 47 language tag for skos:prefLabel.
        directive_triple_handler: Optional callback to add triples from custom
            directives. Receives (graph, extract, concept_ns, prefix, language).

    Returns:
        rdflib Graph with all triples.
    """
    if not namespace.endswith(("#", "/")):
        logging.getLogger(__name__).warning(
            "Namespace '%s' does not end with '#' or '/'. "
            "Generated URIs may be malformed (e.g. '%sCabin' instead of '%s#Cabin').",
            namespace,
            namespace,
            namespace,
        )

    graph = Graph()
    concept_ns = Namespace(namespace)

    # Bind namespaces
    graph.bind("skos", SKOS)
    graph.bind("s2dm", S2DM)
    graph.bind(prefix, concept_ns)

    extract = extract_schema_for_rdf(schema)

    def _materialize_field_container(
        container_type: RdfFieldContainerType,
        s2dm_type: Node,
    ) -> None:
        """Materialize ObjectType, InterfaceType, or InputObjectType and their fields."""
        type_uri = concept_ns[container_type.name]
        _add_concept_header(
            graph,
            type_uri,
            container_type.name,
            container_type.description,
            s2dm_type,
            language,
        )

        for field_info in container_type.fields:
            field_uri = concept_ns[field_info.field_fqn]
            graph.add((type_uri, S2DM.hasField, field_uri))

            _add_concept_header(
                graph,
                field_uri,
                field_info.field_fqn,
                "",
                S2DM.Field,
                language,
            )

            if field_info.output_type_name in BUILTIN_SCALARS:
                output_uri = getattr(S2DM, field_info.output_type_name)
            else:
                output_uri = concept_ns[field_info.output_type_name]
            graph.add((field_uri, S2DM.hasOutputType, output_uri))

            wrapper_pattern = getattr(S2DM, field_info.type_wrapper_pattern)
            graph.add((field_uri, S2DM.usesTypeWrapperPattern, wrapper_pattern))

    # Materialize object types and fields
    for obj_type in extract.object_types:
        _materialize_field_container(obj_type, S2DM.ObjectType)

    # Materialize interface types and fields
    for iface_type in extract.interface_types:
        _materialize_field_container(iface_type, S2DM.InterfaceType)

    # Materialize input object types and fields
    for input_type in extract.input_object_types:
        _materialize_field_container(input_type, S2DM.InputObjectType)

    # Materialize union types
    for union_type in extract.union_types:
        union_uri = concept_ns[union_type.name]
        _add_concept_header(
            graph,
            union_uri,
            union_type.name,
            union_type.description,
            S2DM.UnionType,
            language,
        )
        for member_name in union_type.member_type_names:
            member_uri = concept_ns[member_name]
            graph.add((union_uri, S2DM.hasUnionMember, member_uri))

    # Materialize enum types and values
    for enum_type in extract.enum_types:
        enum_uri = concept_ns[enum_type.name]
        _add_concept_header(
            graph,
            enum_uri,
            enum_type.name,
            enum_type.description,
            S2DM.EnumType,
            language,
        )
        for value_name in enum_type.values:
            value_fqn = f"{enum_type.name}.{value_name}"
            value_uri = concept_ns[value_fqn]
            graph.add((enum_uri, S2DM.hasEnumValue, value_uri))
            _add_concept_header(
                graph,
                value_uri,
                value_fqn,
                "",
                S2DM.EnumValue,
                language,
            )

    if directive_triple_handler is not None:
        directive_triple_handler(graph, extract, concept_ns, prefix, language)

    return graph


def _sort_ntriples_lines(nt_str: str) -> str:
    """Sort n-triple lines lexicographically for deterministic output.

    This implementation can be replaced (e.g. with triple-level sorting via
    sorted(graph) + _nt_row) if different semantics are needed.
    """
    lines = [line for line in nt_str.strip().split("\n") if line.strip()]
    return "\n".join(sorted(lines)) + "\n" if lines else ""


def serialize_sorted_ntriples(graph: Graph) -> str:
    """Serialize an RDF graph as sorted n-triples for deterministic, git-friendly output.

    Args:
        graph: The rdflib Graph to serialize.

    Returns:
        Sorted n-triples string, one triple per line, with trailing newline.
    """
    nt = graph.serialize(format="nt")
    return _sort_ntriples_lines(nt)


# Registry mapping rdflib format names to file extensions.
# The keys are the canonical format identifiers (also accepted by rdflib).
# New formats can be added here without further code changes.
FORMAT_REGISTRY: dict[str, str] = {
    "nt": ".nt",
    "turtle": ".ttl",
    "json-ld": ".jsonld",
}

# Common short aliases that users may prefer on the CLI.
FORMAT_ALIASES: dict[str, str] = {
    "ttl": "turtle",
    "jsonld": "json-ld",
}

# Default formats for day-to-day use (sorted n-triples for git, Turtle for reading).
DEFAULT_FORMATS: list[str] = ["nt", "turtle"]


def resolve_format(fmt: str) -> str:
    """Resolve a format key to its canonical rdflib name.

    Accepts both canonical names (``"turtle"``, ``"json-ld"``) and common
    aliases (``"ttl"``, ``"jsonld"``).

    Args:
        fmt: User-supplied format key.

    Returns:
        Canonical rdflib format name.

    Raises:
        ValueError: If *fmt* is not a known format or alias.
    """
    if fmt in FORMAT_REGISTRY:
        return fmt
    if fmt in FORMAT_ALIASES:
        return FORMAT_ALIASES[fmt]
    all_accepted = sorted(set(FORMAT_REGISTRY) | set(FORMAT_ALIASES))
    raise ValueError(f"Unknown RDF format: '{fmt}'. Supported: {', '.join(all_accepted)}")


def write_rdf_artifacts(
    graph: Graph,
    output_dir: Path,
    base_name: str = "schema",
    formats: list[str] | None = None,
) -> list[Path]:
    """Write RDF graph to one or more serialization formats.

    Uses FORMAT_REGISTRY to resolve format keys to rdflib serializer names and
    file extensions.  The ``"nt"`` format is special-cased to use
    ``serialize_sorted_ntriples`` for deterministic, git-friendly output.

    Accepts both canonical rdflib names (e.g. ``"turtle"``) and common
    aliases (e.g. ``"ttl"``).

    Args:
        graph: The rdflib Graph to write.
        output_dir: Directory to write files into (created if needed).
        base_name: Base filename without extension (default: "schema").
        formats: List of format keys (e.g. ``["nt", "ttl", "json-ld"]``).
            Defaults to ``["nt", "turtle"]`` when *None*.

    Returns:
        List of paths to the written files.

    Raises:
        ValueError: If an unknown format key is provided.
    """
    if formats is None:
        formats = list(DEFAULT_FORMATS)

    # Resolve aliases to canonical names
    resolved = [resolve_format(f) for f in formats]

    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for fmt in resolved:
        extension = FORMAT_REGISTRY[fmt]
        out_path = output_dir / f"{base_name}{extension}"

        if fmt == "nt":
            # Sorted n-triples for deterministic, git-friendly output
            out_path.write_text(serialize_sorted_ntriples(graph), encoding="utf-8")
        else:
            graph.serialize(destination=str(out_path), format=fmt)

        written.append(out_path)

    return written
