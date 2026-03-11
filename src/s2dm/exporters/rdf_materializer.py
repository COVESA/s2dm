"""RDF materialization of GraphQL schemas into separate SKOS and ontology graphs.

This module materializes GraphQL SDL into two separate RDF graphs:
- SKOS graph: skos:Concept, skos:prefLabel, skos:definition, skos:note,
  skos:Collection, skos:member
- Data graph (ontology instantiation): s2dm:ObjectType, InterfaceType,
  InputObjectType, UnionType, EnumType, Field, EnumValue, hasField,
  hasOutputType, hasEnumValue, hasUnionMember, usesTypeWrapperPattern
"""

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

# Template for skos:note on concepts whose definition was inherited from SDL
_SKOS_NOTE_TEMPLATE = (
    "Content of SKOS definition was inherited from the description of the "
    "GraphQL SDL element {name} whose URI is {uri}."
)

# Collection label constants
_COLLECTION_OBJECT_CONCEPTS = "ObjectConcepts"
_COLLECTION_FIELD_CONCEPTS = "FieldConcepts"
_COLLECTION_INTERFACE_CONCEPTS = "InterfaceConcepts"
_COLLECTION_INPUT_CONCEPTS = "InputObjectConcepts"
_COLLECTION_UNION_CONCEPTS = "UnionConcepts"


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


# ---------------------------------------------------------------------------
# Graph construction helpers
# ---------------------------------------------------------------------------


def _create_bound_graph(namespace: str, prefix: str) -> tuple[Graph, Namespace]:
    """Create an RDF graph with standard namespace bindings.

    Args:
        namespace: URI namespace for concept URIs.
        prefix: Prefix for concept URIs (e.g., "ns").

    Returns:
        Tuple of (graph, concept_namespace).
    """
    graph = Graph()
    concept_ns = Namespace(namespace)
    graph.bind("skos", SKOS)
    graph.bind("s2dm", S2DM)
    graph.bind(prefix, concept_ns)
    return graph, concept_ns


def _add_skos_concept(
    graph: Graph,
    uri: Node,
    pref_label: str,
    description: str,
    language: str,
) -> None:
    """Add SKOS concept triples: rdf:type, prefLabel, definition, note.

    Args:
        graph: SKOS RDF graph.
        uri: Concept URI.
        pref_label: Value for skos:prefLabel.
        description: Description for skos:definition (empty string to skip).
        language: BCP 47 language tag.
    """
    graph.add((uri, RDF.type, SKOS.Concept))
    graph.add((uri, SKOS.prefLabel, Literal(pref_label, lang=language)))
    if description.strip():
        graph.add((uri, SKOS.definition, Literal(description)))
        note = _SKOS_NOTE_TEMPLATE.format(name=pref_label, uri=str(uri))
        graph.add((uri, SKOS.note, Literal(note)))


def _add_collection(graph: Graph, namespace: Namespace, name: str, label: str, language: str) -> Node:
    """Create a SKOS collection and return its URI.

    Args:
        graph: SKOS RDF graph.
        namespace: Concept namespace.
        name: Collection URI local name.
        label: Human-readable label.
        language: BCP 47 language tag.

    Returns:
        Collection URI node.
    """
    ref = namespace[name]
    graph.add((ref, RDF.type, SKOS.Collection))
    graph.add((ref, SKOS.prefLabel, Literal(label, lang=language)))
    return ref


# ---------------------------------------------------------------------------
# SKOS graph materialization
# ---------------------------------------------------------------------------


def materialize_skos_graph(
    extract: RdfSchemaExtract,
    namespace: str,
    prefix: str,
    language: str = "en",
) -> Graph:
    """Materialize SKOS-only triples from an extracted schema.

    Produces:
    - skos:Concept with prefLabel, definition, and note for every type and field
    - skos:Collection groupings (ObjectConcepts, FieldConcepts, InterfaceConcepts,
      InputObjectConcepts, UnionConcepts, and per-enum collections)

    Args:
        extract: Pre-extracted schema elements.
        namespace: URI namespace for concept URIs.
        prefix: Prefix for concept URIs (e.g., "ns").
        language: BCP 47 language tag for skos:prefLabel.

    Returns:
        rdflib Graph containing only SKOS triples.
    """
    graph, concept_ns = _create_bound_graph(namespace, prefix)

    # Top-level collections
    object_coll = _add_collection(graph, concept_ns, _COLLECTION_OBJECT_CONCEPTS, "Object Concepts", language)
    field_coll = _add_collection(graph, concept_ns, _COLLECTION_FIELD_CONCEPTS, "Field Concepts", language)
    iface_coll = _add_collection(
        graph,
        concept_ns,
        _COLLECTION_INTERFACE_CONCEPTS,
        "Interface Concepts",
        language,
    )
    input_coll = _add_collection(
        graph,
        concept_ns,
        _COLLECTION_INPUT_CONCEPTS,
        "Input Object Concepts",
        language,
    )
    union_coll = _add_collection(graph, concept_ns, _COLLECTION_UNION_CONCEPTS, "Union Concepts", language)

    def _skos_field_container(container: RdfFieldContainerType, collection_ref: Node) -> None:
        """Add SKOS concepts for a field-container type and its fields."""
        type_uri = concept_ns[container.name]
        _add_skos_concept(graph, type_uri, container.name, container.description, language)
        graph.add((collection_ref, SKOS.member, type_uri))

        for fi in container.fields:
            field_uri = concept_ns[fi.field_fqn]
            _add_skos_concept(graph, field_uri, fi.field_fqn, "", language)
            graph.add((field_coll, SKOS.member, field_uri))

    for obj_type in extract.object_types:
        _skos_field_container(obj_type, object_coll)

    for iface_type in extract.interface_types:
        _skos_field_container(iface_type, iface_coll)

    for input_type in extract.input_object_types:
        _skos_field_container(input_type, input_coll)

    for union_type in extract.union_types:
        union_uri = concept_ns[union_type.name]
        _add_skos_concept(graph, union_uri, union_type.name, union_type.description, language)
        graph.add((union_coll, SKOS.member, union_uri))

    for enum_type in extract.enum_types:
        # Per-enum collection
        enum_coll = _add_collection(graph, concept_ns, enum_type.name, enum_type.name, language)
        if enum_type.description.strip():
            graph.add((concept_ns[enum_type.name], SKOS.definition, Literal(enum_type.description)))

        for value_name in enum_type.values:
            value_fqn = f"{enum_type.name}.{value_name}"
            value_uri = concept_ns[value_fqn]
            _add_skos_concept(graph, value_uri, value_fqn, "", language)
            graph.add((enum_coll, SKOS.member, value_uri))
            graph.add((field_coll, SKOS.member, value_uri))

    return graph


# ---------------------------------------------------------------------------
# Data graph (ontology) materialization
# ---------------------------------------------------------------------------


def materialize_data_graph(
    extract: RdfSchemaExtract,
    namespace: str,
    prefix: str,
    language: str = "en",
) -> Graph:
    """Materialize s2dm ontology triples from an extracted schema.

    Produces:
    - rdf:type triples for s2dm types (ObjectType, Field, EnumType, etc.)
    - Relationship triples (hasField, hasOutputType, usesTypeWrapperPattern,
      hasEnumValue, hasUnionMember)

    Args:
        extract: Pre-extracted schema elements.
        namespace: URI namespace for concept URIs.
        prefix: Prefix for concept URIs (e.g., "ns").
        language: BCP 47 language tag (used for labels on ontology instances).

    Returns:
        rdflib Graph containing only s2dm ontology triples.
    """
    graph, concept_ns = _create_bound_graph(namespace, prefix)

    def _data_field_container(container: RdfFieldContainerType, s2dm_type: Node) -> None:
        """Add ontology triples for a field-container type and its fields."""
        type_uri = concept_ns[container.name]
        graph.add((type_uri, RDF.type, s2dm_type))

        for fi in container.fields:
            field_uri = concept_ns[fi.field_fqn]
            graph.add((type_uri, S2DM.hasField, field_uri))
            graph.add((field_uri, RDF.type, S2DM.Field))

            if fi.output_type_name in BUILTIN_SCALARS:
                output_uri = getattr(S2DM, fi.output_type_name)
            else:
                output_uri = concept_ns[fi.output_type_name]
            graph.add((field_uri, S2DM.hasOutputType, output_uri))

            wrapper = getattr(S2DM, fi.type_wrapper_pattern)
            graph.add((field_uri, S2DM.usesTypeWrapperPattern, wrapper))

    for obj_type in extract.object_types:
        _data_field_container(obj_type, S2DM.ObjectType)

    for iface_type in extract.interface_types:
        _data_field_container(iface_type, S2DM.InterfaceType)

    for input_type in extract.input_object_types:
        _data_field_container(input_type, S2DM.InputObjectType)

    for union_type in extract.union_types:
        union_uri = concept_ns[union_type.name]
        graph.add((union_uri, RDF.type, S2DM.UnionType))
        for member_name in union_type.member_type_names:
            graph.add((union_uri, S2DM.hasUnionMember, concept_ns[member_name]))

    for enum_type in extract.enum_types:
        enum_uri = concept_ns[enum_type.name]
        graph.add((enum_uri, RDF.type, S2DM.EnumType))
        for value_name in enum_type.values:
            value_fqn = f"{enum_type.name}.{value_name}"
            value_uri = concept_ns[value_fqn]
            graph.add((enum_uri, S2DM.hasEnumValue, value_uri))
            graph.add((value_uri, RDF.type, S2DM.EnumValue))

    return graph


# ---------------------------------------------------------------------------
# Serialization and file output
# ---------------------------------------------------------------------------


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


def write_rdf_artifacts(
    graph: Graph,
    output_dir: Path,
    base_name: str = "schema",
) -> None:
    """Write RDF graph to sorted n-triples and Turtle files.

    Args:
        graph: The rdflib Graph to write.
        output_dir: Directory to write files into (created if needed).
        base_name: Base filename without extension (default: "schema").
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    nt_path = output_dir / f"{base_name}.nt"
    ttl_path = output_dir / f"{base_name}.ttl"

    nt_path.write_text(serialize_sorted_ntriples(graph), encoding="utf-8")
    graph.serialize(destination=str(ttl_path), format="turtle")
