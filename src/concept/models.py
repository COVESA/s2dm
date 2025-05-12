import logging
from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator

# Configure logger
logger = logging.getLogger(__name__)


class SpecModel(BaseModel):
    """A base model for spec history."""

    model_config = {
        "populate_by_name": True,
        "extra": "allow",
        "alias_generator": lambda field_name: (
            f"@{field_name}" if field_name in ("id", "type", "context", "graph") else field_name
        ),
        "exclude_none": True,
    }

    def to_json_ld(self) -> dict:
        """Serialize model to JSON-LD format with consistent options.

        This is the preferred method to use when serializing any model
        to JSON-LD format. It ensures consistent handling of aliases
        (using @ prefixes for JSON-LD special attributes) and excludes
        None/null values from the output for cleaner, more standards-compliant
        JSON-LD documents.

        Use this method in conjunction with json.dump() or json.dumps():

        ```python
        import json

        # Serialize to a file
        with open("output.json", "w") as f:
            json.dump(model.to_json_ld(), f, indent=2)

        # Or to a string
        json_string = json.dumps(model.to_json_ld(), indent=2)
        ```

        Returns:
            A dict ready for JSON serialization with proper JSON-LD field names
            and without None fields.
        """
        return self.model_dump(by_alias=True, exclude_none=True)


class SpecHistoryEntry(BaseModel):
    """A single entry in the spec history."""

    id: str
    timestamp: str

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate that the timestamp is in ISO format."""
        try:
            datetime.fromisoformat(v)
        except ValueError as err:
            raise ValueError("timestamp must be in ISO format") from err
        return v

    @classmethod
    def create(cls, id_value: str) -> "SpecHistoryEntry":
        """Create a new spec history entry with the current timestamp."""
        return cls(id=id_value, timestamp=datetime.now().isoformat())


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


class ConceptUriNode(SpecModel):
    """A node in the concept URI graph."""

    id: str
    type: str
    hasField: list[str] | None = None
    hasNestedObject: str | None = None

    def get_concept_name(self) -> str:
        """Extract the concept name from the URI."""
        return self.id.split(":")[-1]

    def is_field(self) -> bool:
        """Check if this node is a Field type."""
        return self.type == "Field"

    def should_have_history(self) -> bool:
        """Check if this node should have history (Field or Enum)."""
        return self.type in ("Field", "Enum")


class SpecHistoryNode(ConceptUriNode):
    """A node in the spec history graph with history information."""

    specHistory: list[SpecHistoryEntry] | None = None

    def add_history_entry(self, id_value: str) -> bool:
        """Add a new entry to the spec history if it's different from the latest one.

        Returns:
            bool: True if a new entry was added, False otherwise.
        """
        if not self.should_have_history():
            return False

        if self.specHistory is None:
            self.specHistory = []

        # Check if the ID is different from the latest one
        if not self.specHistory or self.specHistory[-1].id != id_value:
            self.specHistory.append(SpecHistoryEntry.create(id_value))
            return True

        return False

    def initialize_history(self, id_value: str) -> None:
        """Initialize the spec history with the given ID."""
        if self.should_have_history():
            self.specHistory = [SpecHistoryEntry.create(id_value)]


class ConceptUriModel(SpecModel):
    """The core concept URI model."""

    context: dict[str, Any]
    graph: list[ConceptUriNode]

    def get_node_by_id(self, node_id: str) -> ConceptUriNode | None:
        """Get a node by its ID."""
        for node in self.graph:
            if node.id == node_id:
                return node
        return None

    def get_concept_map(self) -> dict[str, ConceptUriNode]:
        """Create a map of node IDs to nodes."""
        return {node.id: node for node in self.graph}

    def to_spec_history(self, concept_ids: dict[str, str]) -> "SpecHistory":
        """Convert this concept URI model to a spec history model.

        Args:
            concept_ids: A mapping of concept names to their IDs

        Returns:
            A new SpecHistory instance with initialized history entries
        """
        # Get namespace from the context
        namespace = self.context.get("ns", "")

        # Create a new context with specHistory included
        updated_context = create_jsonld_context(namespace, include_spec_history=True)

        # Create new nodes with history where appropriate
        spec_nodes: list[SpecHistoryNode] = []

        for node in self.graph:
            # Convert to SpecHistoryNode
            spec_node_dict = node.to_json_ld()
            spec_node = SpecHistoryNode.model_validate(spec_node_dict)

            # Initialize history for field and enum nodes
            if spec_node.should_have_history():
                concept_name = spec_node.get_concept_name()
                if concept_name in concept_ids:
                    spec_node.initialize_history(concept_ids[concept_name])
                else:
                    logger.warning(f"No ID found for concept: {concept_name}")

            spec_nodes.append(spec_node)

        # Create and return the spec history
        return SpecHistory(context=updated_context, graph=spec_nodes)


class SpecHistory(ConceptUriModel):
    """The complete spec history document with history tracking."""

    graph: list[SpecHistoryNode]

    def update_from_concept_uris(
        self, concept_uris: ConceptUriModel, concept_ids: dict[str, str]
    ) -> tuple[list[str], list[str]]:
        """Update this spec history from concept URIs and IDs.

        Args:
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
        existing_concepts = self.get_concept_map()

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
                self.graph.append(new_node)

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
