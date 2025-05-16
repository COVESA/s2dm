import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, field_validator

# Configure logger
logger = logging.getLogger(__name__)

NodeType = TypeVar("NodeType", bound="ConceptBaseModel")


@dataclass
class Concepts:
    fields: list[str] = field(default_factory=list)
    enums: list[str] = field(default_factory=list)
    objects: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    nested_objects: dict[str, str] = field(default_factory=dict)


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

    def to_json_ld(self) -> dict[str, str]:
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


# Concept models
class ConceptBaseModel(JsonLDSerializable, Generic[NodeType]):
    """A base model for concepts."""

    context: dict[str, Any]
    graph: list[NodeType]

    def get_node_by_id(self, node_id: str) -> NodeType | None:
        """Get a node by its ID."""
        for node in self.graph:
            if node.id == node_id:
                return node
        return None

    def get_concept_map(self) -> dict[str, NodeType]:
        """Create a map of node IDs to nodes."""
        return {node.id: node for node in self.graph}


class ConceptUriNode(JsonLDSerializable):
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


class ConceptUriModel(ConceptBaseModel[ConceptUriNode]):
    """The core concept URI model."""


# Spec History models
class SpecHistoryEntry(JsonLDSerializable):
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


class SpecHistoryNode(ConceptUriNode):
    """A node in the spec history graph with history information."""

    specHistory: list[SpecHistoryEntry] | None = None

    def initialize_history(self, id_value: str) -> None:
        """Initialize the spec history with the given ID."""
        if self.should_have_history():
            self.specHistory = [SpecHistoryEntry.create(id_value)]

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


class SpecHistoryModel(ConceptBaseModel[SpecHistoryNode]):
    """The complete spec history document with history tracking."""
