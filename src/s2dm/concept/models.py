from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeVar

from graphql import GraphQLField
from pydantic import BaseModel, field_validator
from typing_extensions import TypedDict


class FieldMetadata(TypedDict):
    """Metadata for a GraphQL field in the concepts extraction.

    This provides structured access to GraphQL field information without
    requiring string parsing, ensuring type safety and consistency.
    """

    object_name: str  # The GraphQL object type name (e.g., "Vehicle")
    field_name: str  # The GraphQL field name (e.g., "averageSpeed")
    field_definition: GraphQLField  # The GraphQL field definition object


class JsonLDSerializable(BaseModel):
    """A base model for concepts."""

    # Pydantic model config
    model_config = {
        "populate_by_name": True,
        "extra": "allow",
        "alias_generator": lambda field_name: (
            f"@{field_name}" if field_name in ("id", "type", "context", "graph") else field_name
        ),
    }

    def to_json_ld(self) -> dict[str, Any]:
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


class HasIdMixin(JsonLDSerializable):
    """Base class for objects that have an id attribute."""

    id: str


NodeType = TypeVar("NodeType", bound=HasIdMixin)


@dataclass
class Concepts:
    """Data class containing all the concepts extracted from a GraphQL schema.

    Args:
        fields: List of field names
        enums: List of enum names
        objects: Dictionary mapping object names to their field lists
        nested_objects: Dictionary mapping field names to object type names
        field_metadata: Dictionary mapping field names to their structured metadata
    """

    fields: list[str] = field(default_factory=list)
    enums: list[str] = field(default_factory=list)
    objects: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    nested_objects: dict[str, str] = field(default_factory=dict)
    # Enhanced metadata for advanced functionality (SKOS generation, etc.)
    field_metadata: dict[str, FieldMetadata] = field(default_factory=dict)


# Concept models
class ConceptBaseModel(JsonLDSerializable, Generic[NodeType]):
    """A base model for concepts.

    Args:
        context: JSON-LD context dictionary
        graph: List of nodes in the graph
    """

    context: dict[str, Any]
    graph: list[NodeType]

    def get_node_by_id(self, node_id: str) -> NodeType | None:
        """Get a node by its ID.

        Args:
            node_id: The ID of the node to find

        Returns:
            The node with the given ID, or None if not found
        """
        for node in self.graph:
            if node.id == node_id:
                return node
        return None

    def get_concept_map(self) -> dict[str, NodeType]:
        """Create a map of node IDs to nodes.

        Returns:
            Dictionary mapping node IDs to node objects
        """
        return {node.id: node for node in self.graph}


class ConceptUriNode(HasIdMixin):
    """A node in the concept URI graph.

    Args:
        id: The unique identifier for this node
        type: The type of the node (Object, Field, Enum, etc.)
        hasField: List of field IDs for object nodes
        hasNestedObject: ID of nested object for field nodes
    """

    type: str
    hasField: list[str] | None = None
    hasNestedObject: str | None = None

    def get_concept_name(self) -> str:
        """Extract the concept name from the URI.

        Returns:
            The concept name (last part after the colon)
        """
        return self.id.split(":")[-1]

    def is_field(self) -> bool:
        """Check if this node is a Field type.

        Returns:
            True if the node type is "Field"
        """
        return self.type == "Field"

    def should_have_history(self) -> bool:
        """Check if this node should have history (Field or Enum).

        Returns:
            True if the node type is "Field" or "Enum"
        """
        return self.type in ("Field", "Enum")


class ConceptUriModel(ConceptBaseModel[ConceptUriNode]):
    """The core concept URI model containing concept URI nodes."""


# Spec History models
class SpecHistoryEntry(HasIdMixin):
    """A single entry in the spec history.

    Args:
        id: The ID value for this history entry
        timestamp: ISO format timestamp when this entry was created
    """

    timestamp: str

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate that the timestamp is in ISO format.

        Args:
            v: The timestamp string to validate

        Returns:
            The validated timestamp string

        Raises:
            ValueError: If timestamp is not in ISO format
        """
        try:
            datetime.fromisoformat(v)
        except ValueError as err:
            raise ValueError("timestamp must be in ISO format") from err
        return v

    @classmethod
    def create(cls, id_value: str) -> "SpecHistoryEntry":
        """Create a new spec history entry with the current timestamp.

        Args:
            id_value: The ID value for this entry

        Returns:
            A new SpecHistoryEntry with current timestamp
        """
        return cls(id=id_value, timestamp=datetime.now().isoformat())


class SpecHistoryNode(ConceptUriNode):
    """A node in the spec history graph with history information.

    Args:
        specHistory: List of history entries for this node
    """

    specHistory: list[SpecHistoryEntry] | None = None

    def initialize_history(self, id_value: str) -> None:
        """Initialize the spec history with the given ID.

        Args:
            id_value: The initial ID value for the history
        """
        if self.should_have_history():
            self.specHistory = [SpecHistoryEntry.create(id_value)]

    def add_history_entry(self, id_value: str) -> bool:
        """Add a new entry to the spec history if it's different from the latest one.

        Args:
            id_value: The new ID value to add

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


class SpecHistoryModel(ConceptBaseModel[SpecHistoryNode]):
    """The complete spec history document with history tracking."""
