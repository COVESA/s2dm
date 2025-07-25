import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from graphql import GraphQLSchema
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, SKOS
from rdflib.term import Node

from s2dm.concept.models import Concepts, FieldMetadata
from s2dm.concept.services import iter_all_concepts
from s2dm.exporters.utils import get_all_named_types, load_schema

# Constants

# S2DM Ontology Namespace
# This URI defines the official namespace for the S2DM (Schema to Data Model) ontology
# developed by COVESA (Connected Vehicle Systems Alliance). The s2dm ontology provides
# semantic types for GraphQL schema elements when mapped to RDF/SKOS:
# - s2dm:ObjectType - for GraphQL object types
# - s2dm:Field - for GraphQL scalar/enum fields
# - s2dm:EnumValue - for GraphQL enumeration values
# This namespace is referenced in SHACL validation shapes and ensures consistent
# semantic typing across s2dm tools and generated RDF output.
# See: https://covesa.global/ and examples/graphql-to-skos/shapes.shacl for usage examples.
S2DM_NAMESPACE_URI = "https://covesa.global/models/s2dm#"
S2DM = Namespace(S2DM_NAMESPACE_URI)


# SKOS concept types
class S2DMType:
    """Constants for s2dm ontology types."""

    OBJECT_TYPE = "ObjectType"
    FIELD = "Field"
    ENUM_VALUE = "EnumValue"


# Collection names
class CollectionNames:
    """Constants for SKOS collection names."""

    OBJECT_CONCEPTS = "ObjectConcepts"
    FIELD_CONCEPTS = "FieldConcepts"


@dataclass
class SKOSConcept:
    """Represents a SKOS concept with all required properties.

    Args:
        name: The concept name (e.g., "Vehicle_ADAS")
        pref_label: Human-readable label for the concept
        language: BCP 47 language tag for the preferred label
        definition: The concept definition/description
        s2dm_type: The s2dm type of the concept (e.g., "ObjectType", "Field", "EnumValue")
    """

    # Class constant for note template
    NOTE_TEMPLATE = (
        "Content of SKOS definition was inherited from the description of the "
        "GraphQL SDL element {name} whose URI is {uri}."
    )

    name: str
    pref_label: str
    language: str
    definition: str
    s2dm_type: str

    def _get_note(self) -> str:
        """Get the note for the SKOS concept."""
        return self.NOTE_TEMPLATE.format(name=self.name, uri=self.name)

    def add_to_graph(self, graph: Graph, namespace: Namespace) -> None:
        """Add this SKOS concept as RDF triples to the given graph."""
        concept_ref = namespace[self.name]

        # Add types
        graph.add((concept_ref, RDF.type, SKOS.Concept))
        s2dm_type_ref = getattr(S2DM, self.s2dm_type)
        graph.add((concept_ref, RDF.type, s2dm_type_ref))

        # Add preferred label with language tag
        graph.add((concept_ref, SKOS.prefLabel, Literal(self.pref_label, lang=self.language)))

        # Add definition and note only if there's actual content from GraphQL schema
        if self.definition.strip():
            graph.add((concept_ref, SKOS.definition, Literal(self.definition)))
            graph.add((concept_ref, SKOS.note, Literal(self._get_note())))


def create_skos_graph(namespace: str, prefix: str) -> tuple[Graph, Namespace]:
    """Create and configure an RDF graph for SKOS content."""
    graph = Graph()
    concept_namespace = Namespace(namespace)

    # Bind namespaces
    graph.bind("skos", SKOS)
    graph.bind("s2dm", S2DM)
    graph.bind(prefix, concept_namespace)

    return graph, concept_namespace


def create_collection(graph: Graph, namespace: Namespace, name: str, label: str, language: str) -> Node:
    """Create a SKOS collection with the given properties.

    Returns:
        The reference to the collection
    """
    collection_ref = namespace[name]
    graph.add((collection_ref, RDF.type, SKOS.Collection))
    graph.add((collection_ref, SKOS.prefLabel, Literal(label, lang=language)))
    return collection_ref


def add_concept_to_collection(graph: Graph, collection_ref: Node, concept_ref: Node) -> None:
    """Add a concept as a member of a collection."""
    graph.add((collection_ref, SKOS.member, concept_ref))


def collect_skos_concepts(
    schema: GraphQLSchema,
    concepts: Concepts,
    graph: Graph,
    namespace: Namespace,
    language: str,
) -> None:
    """Collect all SKOS concepts from the Concepts data structure and add them to the graph."""
    # Create top-level collections
    object_collection_ref = create_collection(
        graph, namespace, CollectionNames.OBJECT_CONCEPTS, "Object Concepts", language
    )
    field_collection_ref = create_collection(
        graph, namespace, CollectionNames.FIELD_CONCEPTS, "Field Concepts", language
    )

    # Process object types
    for object_name in concepts.objects:
        object_type = schema.type_map.get(object_name)
        description = ""
        if object_type and hasattr(object_type, "description"):
            description = object_type.description or ""

        concept = SKOSConcept(
            name=object_name,
            pref_label=object_name,
            language=language,
            definition=description,
            s2dm_type=S2DMType.OBJECT_TYPE,
        )
        concept.add_to_graph(graph, namespace)
        add_concept_to_collection(graph, object_collection_ref, namespace[object_name])

    # Process fields using the exact same iteration logic as iter_all_concepts
    for field_fqn in concepts.fields:
        # Get typed field metadata
        if field_fqn in concepts.field_metadata:
            metadata: FieldMetadata = concepts.field_metadata[field_fqn]
            field_def = metadata["field_definition"]

            # Create concept directly from GraphQL field definition
            concept = SKOSConcept(
                name=field_fqn,
                pref_label=field_fqn,
                language=language,
                definition=field_def.description or "",
                s2dm_type=S2DMType.FIELD,
            )
            concept.add_to_graph(graph, namespace)
            add_concept_to_collection(graph, field_collection_ref, namespace[field_fqn])

    # Process enums and enum values
    for enum_name in concepts.enums:
        enum_type = schema.type_map.get(enum_name)
        if not enum_type or not hasattr(enum_type, "values"):
            continue

        # Create enum collection
        enum_collection_ref = namespace[enum_name]
        graph.add((enum_collection_ref, RDF.type, SKOS.Collection))
        graph.add((enum_collection_ref, SKOS.prefLabel, Literal(enum_name, lang=language)))

        # Add enum description if available
        if hasattr(enum_type, "description") and enum_type.description and enum_type.description.strip():
            graph.add((enum_collection_ref, SKOS.definition, Literal(enum_type.description)))

        # Create enum value concepts
        for value_name in enum_type.values:
            # Get the enum value definition to access its description
            enum_value_def = enum_type.values[value_name]
            value_description = ""
            if hasattr(enum_value_def, "description") and enum_value_def.description:
                value_description = enum_value_def.description

            value_concept_name = f"{enum_name}.{value_name}"
            concept = SKOSConcept(
                name=value_concept_name,
                pref_label=value_concept_name,
                language=language,
                definition=value_description,
                s2dm_type=S2DMType.ENUM_VALUE,
            )
            concept.add_to_graph(graph, namespace)

            # Add to both enum collection and field concepts collection
            add_concept_to_collection(graph, enum_collection_ref, namespace[value_concept_name])
            add_concept_to_collection(graph, field_collection_ref, namespace[value_concept_name])


def validate_skos_graph(graph: Graph) -> list[str]:
    """Validate a SKOS graph for basic structural issues."""
    errors: list[str] = []
    concepts: list[Node] = list(graph.subjects(RDF.type, SKOS.Concept))

    for concept in concepts:
        # Check required properties
        if not list(graph.objects(concept, SKOS.prefLabel)):
            errors.append(f"Concept {concept} missing required skos:prefLabel")

    logging.info(f"Validated {len(concepts)} SKOS concepts, found {len(errors)} issues")
    return errors


def generate_skos_skeleton(
    schema_path: Path,
    output_stream: TextIO,
    namespace: str,
    prefix: str,
    language: str,
    validate: bool = True,
) -> None:
    """Generate SKOS skeleton RDF file from GraphQL schema.

    Args:
        schema_path: Path to the GraphQL schema file
        output_stream: The output stream to write to
        namespace: The namespace for the concepts
        prefix: The prefix to use for the concepts
        language: BCP 47 language tag for prefLabels (validated at CLI level)
        validate: Whether to validate the generated RDF (default: True)

    Raises:
        ValueError: If validation is enabled and the generated RDF has errors
    """
    logging.info(f"Processing schema '{schema_path}' for SKOS generation")

    # Load schema and extract concepts
    graphql_schema = load_schema(schema_path)
    named_types = get_all_named_types(graphql_schema)
    concepts = iter_all_concepts(named_types)

    # Create and populate RDF graph
    graph, concept_namespace = create_skos_graph(namespace, prefix)
    collect_skos_concepts(graphql_schema, concepts, graph, concept_namespace, language)

    # Validate if requested
    if validate:
        validation_errors = validate_skos_graph(graph)
        if validation_errors:
            error_msg = "Generated SKOS has validation errors:\n" + "\n".join(validation_errors)
            logging.error(error_msg)
            raise ValueError(error_msg)
        logging.info("SKOS validation passed successfully")

    # Serialize the graph to Turtle format
    output_stream.write(graph.serialize(format="turtle"))
