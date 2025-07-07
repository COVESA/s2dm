import json
from pathlib import Path
from typing import Any

from graphql import GraphQLEnumType, GraphQLList, GraphQLNamedType, GraphQLObjectType

from s2dm import log
from s2dm.concept.models import (
    Concepts,
    ConceptUriModel,
    ConceptUriNode,
    SpecHistoryModel,
    SpecHistoryNode,
)


def load_json_file(file_path: Path) -> dict[str, Any]:
    """Load a JSON file and return its contents.

    Args:
        file_path: Path to the JSON file to load

    Returns:
        Dictionary containing the JSON file contents

    Raises:
        ValueError: If the loaded content is not a dictionary
    """
    with open(file_path) as f:
        data = json.load(f)

    # Ensure the loaded data is a dictionary
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {file_path}, got {type(data).__name__}")

    return data


def save_spec_history(spec_history: SpecHistoryModel, file_path: Path) -> None:
    """Save a spec history model to a JSON-LD file.

    Args:
        spec_history: The spec history model to save
        file_path: Path where to save the file
    """
    with open(file_path, "w") as f:
        # Use by_alias=True to ensure proper JSON-LD attribute names (@id, @type, etc.)
        json.dump(spec_history.to_json_ld(), f, indent=2)


def create_jsonld_context(namespace: str, include_spec_history: bool = False) -> dict[str, Any]:
    """Create a JSON-LD context dictionary.

    Args:
        namespace: The namespace URI for the context
        include_spec_history: Whether to include specHistory in the context

    Returns:
        A dictionary with the JSON-LD context
    """
    context = {
        "ns": namespace,
        "type": "@type",
        "hasField": {"@id": f"{namespace}hasField", "@type": "@id"},
        "hasNestedObject": {"@id": f"{namespace}hasNestedObject", "@type": "@id"},
        "Object": f"{namespace}Object",
        "Enum": f"{namespace}Enum",
        "Field": f"{namespace}Field",
        "ObjectField": f"{namespace}ObjectField",
    }

    if include_spec_history:
        context["specHistory"] = {
            "@id": f"{namespace}specHistory",
            "@container": "@list",
        }

    return context


def convert_concept_uri_to_spec_history(
    concept_model: ConceptUriModel, concept_ids: dict[str, str]
) -> SpecHistoryModel:
    """Convert concept URI model to a spec history model.

    Args:
        concept_model: The concept URI model
        concept_ids: A mapping of concept names to their IDs

    Returns:
        A new SpecHistory instance with initialized history entries
    """
    # Get namespace from the context
    namespace = concept_model.context.get("ns", "")

    # Create a new context with specHistory included
    updated_context = create_jsonld_context(namespace, include_spec_history=True)

    # Create new nodes with history where appropriate
    spec_nodes: list[SpecHistoryNode] = []

    for node in concept_model.graph:
        # Convert to SpecHistoryNode
        spec_node_dict = node.to_json_ld()
        spec_node = SpecHistoryNode.model_validate(spec_node_dict)

        # Initialize history for field and enum nodes
        if spec_node.should_have_history():
            concept_name = spec_node.get_concept_name()
            if concept_name in concept_ids:
                spec_node.initialize_history(concept_ids[concept_name])
            else:
                log.warning(f"No ID found for concept: {concept_name}")

        spec_nodes.append(spec_node)

    # Create and return the spec history
    return SpecHistoryModel(context=updated_context, graph=spec_nodes)


def update_spec_history_from_concept_uris(
    spec_history: SpecHistoryModel,
    concept_uris: ConceptUriModel,
    concept_ids: dict[str, str],
) -> tuple[list[str], list[str]]:
    """Update this spec history from concept URIs and IDs.

    Args:
        spec_history: The spec history to update
        concept_uris: The concept URIs model
        concept_ids: The concept IDs

    Returns:
        Tuple containing:
        - List of new concept URIs added
        - List of concepts with updated IDs
    """
    # Track changes
    new_concepts = []
    updated_ids = []

    # Create a map of existing concepts by ID for faster lookup
    existing_concepts = spec_history.get_concept_map()

    # Process each node in the concept URIs
    for uri_node in concept_uris.graph:
        concept_uri = uri_node.id
        concept_name = uri_node.get_concept_name()

        # If this concept doesn't exist in the history, add it
        if concept_uri not in existing_concepts:
            # Convert to SpecHistoryNode
            spec_node_dict = uri_node.to_json_ld()
            new_node = SpecHistoryNode.model_validate(spec_node_dict)

            # Add history if it should have history (Field or Enum)
            if new_node.should_have_history() and concept_name in concept_ids:
                new_node.initialize_history(concept_ids[concept_name])
                new_concepts.append(concept_name)

            # Add the new node to the graph
            spec_history.graph.append(new_node)

        # If this concept exists, update its specHistory if needed
        elif uri_node.should_have_history():
            existing_node = existing_concepts[concept_uri]

            # Skip if not a SpecHistoryNode (shouldn't happen)
            if not isinstance(existing_node, SpecHistoryNode):
                continue

            # Check if the ID has changed
            if concept_name in concept_ids:
                current_id = concept_ids[concept_name]

                # Add to history if ID changed
                if existing_node.add_history_entry(current_id):
                    updated_ids.append(concept_name)

    return new_concepts, updated_ids


def create_concept_uri_model(concepts: Concepts, namespace: str, prefix: str) -> ConceptUriModel:
    """Create a ConceptUriModel from Concepts.

    Args:
        concepts: The Concepts object with fields, enums, objects, and nested objects
        namespace: The namespace URI
        prefix: The prefix for the URIs

    Returns:
        A ConceptUriModel representing the concepts
    """
    # Create the JSON-LD context
    context = create_jsonld_context(namespace)

    # Create all nodes
    graph: list[ConceptUriNode] = []

    # Helper function to create a URI
    def uri(name: str) -> str:
        return f"{prefix}:{name}"

    # Object nodes
    for type_name, fields in concepts.objects.items():
        graph.append(
            ConceptUriNode(
                id=uri(type_name),
                type="Object",
                hasField=[uri(field) for field in fields],
            )
        )

    # Field nodes
    for field_id in concepts.fields:
        graph.append(
            ConceptUriNode(
                id=uri(field_id),
                type="Field",
            )
        )

    # Enum nodes
    for enum in concepts.enums:
        graph.append(
            ConceptUriNode(
                id=uri(enum),
                type="Enum",
            )
        )

    # Nested object relationships
    for field_id, object_type in concepts.nested_objects.items():
        graph.append(
            ConceptUriNode(
                id=uri(field_id),
                type="ObjectField",
                hasNestedObject=uri(object_type),
            )
        )

    # Create and return the model
    return ConceptUriModel(context=context, graph=graph)


def generate_concept_uri(
    prefix: str,
    name: str,
) -> str:
    """Generate a concept URI for a field.

    Args:
        prefix: The prefix for the URI (e.g., "ns")
        name: The name of the field or type

    Returns:
        The generated concept URI
    """
    return f"{prefix}:{name}"


def iter_all_concepts(named_types: list[GraphQLNamedType]) -> Concepts:
    """Extract all concepts from GraphQL named types.

    Args:
        named_types: List of GraphQL named types to process

    Returns:
        Concepts object containing all extracted concepts
    """
    concepts = Concepts()
    for named_type in named_types:
        if named_type.name in ("Query", "Mutation"):
            continue

        if isinstance(named_type, GraphQLEnumType):
            log.debug(f"Processing enum: {named_type.name}")
            concepts.enums.append(named_type.name)

        elif isinstance(named_type, GraphQLObjectType):
            log.debug(f"Processing object: {named_type.name}")
            # Get the ID of all fields in the object
            for field_name, field in named_type.fields.items():
                if field_name.lower() == "id":
                    continue

                field_fqn = f"{named_type.name}.{field_name}"

                if isinstance(field.type, GraphQLObjectType):
                    # field uses the object type
                    concepts.nested_objects[field_fqn] = field.type.name
                elif isinstance(field.type, GraphQLList):
                    # field uses a list of the object type
                    internal_type = field.type
                    while hasattr(internal_type, "of_type"):
                        internal_type = internal_type.of_type
                    # Get the name from the internal type if it has one
                    if hasattr(internal_type, "name"):
                        concepts.nested_objects[field_fqn] = internal_type.name
                else:
                    # field uses a scalar type or enum type
                    concepts.objects[named_type.name].append(field_fqn)
                    concepts.fields.append(field_fqn)

    return concepts
