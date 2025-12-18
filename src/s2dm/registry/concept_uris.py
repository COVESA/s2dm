"""Concept URI models and helpers."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from s2dm.concept.models import Concepts


class JsonLDSerializable(BaseModel):
    """A base model for concepts."""

    model_config = {
        "populate_by_name": True,
        "extra": "allow",
        "alias_generator": lambda field_name: (
            f"@{field_name}" if field_name in ("id", "type", "context", "graph") else field_name
        ),
    }

    def to_json_ld(self) -> dict[str, Any]:
        """Serialize model to JSON-LD format with consistent options."""
        return self.model_dump(by_alias=True, exclude_none=True)


class HasIdMixin(JsonLDSerializable):
    """Base class for objects that have an id attribute."""

    id: str


NodeType = TypeVar("NodeType", bound=HasIdMixin)


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


class ConceptUriNode(HasIdMixin):
    """A node in the concept URI graph."""

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
    """The core concept URI model containing concept URI nodes."""


def create_concept_uri_model(concepts: Concepts, namespace: str, prefix: str) -> ConceptUriModel:
    """Create a ConceptUriModel from extracted Concepts."""
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

    graph: list[ConceptUriNode] = []

    def uri(name: str) -> str:
        return f"{prefix}:{name}"

    for type_name, fields in concepts.objects.items():
        graph.append(
            ConceptUriNode(
                id=uri(type_name),
                type="Object",
                hasField=[uri(field) for field in fields],
            )
        )

    for field_id in concepts.fields:
        graph.append(
            ConceptUriNode(
                id=uri(field_id),
                type="Field",
            )
        )

    for enum in concepts.enums:
        graph.append(
            ConceptUriNode(
                id=uri(enum),
                type="Enum",
            )
        )

    for field_id, object_type in concepts.nested_objects.items():
        graph.append(
            ConceptUriNode(
                id=uri(field_id),
                type="ObjectField",
                hasNestedObject=uri(object_type),
            )
        )

    return ConceptUriModel(context=context, graph=graph)


def generate_concept_uri(prefix: str, name: str) -> str:
    """Generate a concept URI for a field or type."""
    return f"{prefix}:{name}"
