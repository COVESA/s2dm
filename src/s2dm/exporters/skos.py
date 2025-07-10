import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from graphql import GraphQLEnumType, GraphQLNamedType, GraphQLObjectType
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, RDFS, SKOS

from s2dm.exporters.utils import get_all_named_types, load_schema


@dataclass
class SKOSConcept:
    """Represents a SKOS concept with all required properties.

    Args:
        name: The concept name (e.g., "Vehicle_ADAS")
        pref_label: Human-readable label for the concept
        language: BCP 47 language tag for the preferred label
        definition: The concept definition/description
    """

    name: str
    pref_label: str
    language: str
    definition: str

    def add_to_graph(self, graph: Graph, namespace: Namespace) -> None:
        """Add this SKOS concept as RDF triples to the given graph.

        Args:
            graph: The RDF graph to add triples to
            namespace: The namespace for the concept URI
        """
        # Create concept reference using namespace
        concept_ref = namespace[self.name]

        # Add concept type
        graph.add((concept_ref, RDF.type, SKOS.Concept))

        # Add preferred label with language tag
        graph.add((concept_ref, SKOS.prefLabel, Literal(self.pref_label, lang=self.language)))

        # Add definition
        graph.add((concept_ref, SKOS.definition, Literal(self.definition)))

        # Add note with concept URI reference
        graph.add(
            (
                concept_ref,
                SKOS.note,
                Literal(f"Definition was inherit from the description of the element {concept_ref}"),
            )
        )

        # Add seeAlso reference
        graph.add((concept_ref, RDFS.seeAlso, concept_ref))


def create_skos_graph(namespace: str, prefix: str) -> tuple[Graph, Namespace]:
    """Create and configure an RDF graph for SKOS content.

    Args:
        namespace: The namespace URI for the concepts
        prefix: The prefix to use for the concepts

    Returns:
        Tuple of configured Graph and the concept Namespace
    """
    graph = Graph()
    concept_namespace = Namespace(namespace)

    # Bind standard namespaces
    graph.bind("skos", SKOS)
    graph.bind("rdfs", RDFS)
    graph.bind(prefix, concept_namespace)

    return graph, concept_namespace


def collect_skos_concepts(
    named_types: list[GraphQLNamedType],
    graph: Graph,
    namespace: Namespace,
    language: str,
) -> None:
    """Collect all SKOS concepts from GraphQL types and add them to the graph.

    Args:
        named_types: List of GraphQL named types
        graph: The RDF graph to add concepts to
        namespace: The namespace for concept URIs
        language: BCP 47 language tag
    """
    for named_type in named_types:
        if named_type.name in ("Query", "Mutation"):
            continue

        # Only process enums, objects and their fields
        if not isinstance(named_type, GraphQLEnumType) and not isinstance(named_type, GraphQLObjectType):
            continue

        concept = SKOSConcept(
            name=named_type.name,
            pref_label=named_type.name,
            language=language,
            definition=named_type.description or "",
        )
        concept.add_to_graph(graph, namespace)

        # Process object fields
        if isinstance(named_type, GraphQLObjectType):
            for field_name, field in named_type.fields.items():
                if field_name.lower() == "id":
                    continue

                field_fqn = f"{named_type.name}.{field_name}"
                field_concept = SKOSConcept(
                    name=field_fqn,
                    pref_label=field_fqn,
                    language=language,
                    definition=field.description or "",
                )
                field_concept.add_to_graph(graph, namespace)


def validate_skos_graph(graph: Graph) -> list[str]:
    """Validate a SKOS graph for common issues.

    Args:
        graph: The RDF graph to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check that all concepts have required SKOS properties
    concepts = list(graph.subjects(RDF.type, SKOS.Concept))

    for concept in concepts:
        # Check for required prefLabel
        pref_labels = list(graph.objects(concept, SKOS.prefLabel))
        if not pref_labels:
            errors.append(f"Concept {concept} missing required skos:prefLabel")

        # Check for definition or note (at least one should be present)
        definitions = list(graph.objects(concept, SKOS.definition))
        notes = list(graph.objects(concept, SKOS.note))
        if not definitions and not notes:
            errors.append(f"Concept {concept} missing both skos:definition and skos:note")

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

    # Load the schema and get named types
    graphql_schema = load_schema(schema_path)
    named_types = get_all_named_types(graphql_schema)

    # Create and configure the RDF graph
    graph, concept_namespace = create_skos_graph(namespace, prefix)

    # Add SKOS content to the graph
    collect_skos_concepts(named_types, graph, concept_namespace, language)

    # Validate the graph if requested
    if validate:
        validation_errors = validate_skos_graph(graph)
        if validation_errors:
            error_msg = "Generated SKOS has validation errors:\n" + "\n".join(validation_errors)
            logging.error(error_msg)
            raise ValueError(error_msg)
        logging.info("SKOS validation passed successfully")

    # Serialize the graph to Turtle format
    output_stream.write(graph.serialize(format="turtle"))
