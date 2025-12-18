"""Spec history models and helpers."""

import json
from pathlib import Path
from typing import Any

from s2dm import log
from s2dm.registry.concept_uris import ConceptBaseModel, ConceptUriModel, ConceptUriNode, HasIdMixin


class SpecHistoryEntry(HasIdMixin):
    """A single entry in the spec history."""

    version_tag: str | None = None

    @classmethod
    def create(cls, id_value: str, version_tag: str | None = None) -> "SpecHistoryEntry":
        """Create a new spec history entry.

        Args:
            id_value: The variant ID (e.g., "Vehicle.speed/v1.0")
            version_tag: The version tag when this entry was created (e.g., "v1.0.0")
        """
        return cls(id=id_value, version_tag=version_tag)


class SpecHistoryNode(ConceptUriNode):
    """A node in the spec history graph with history information."""

    specHistory: list[SpecHistoryEntry] | None = None

    def initialize_history(self, id_value: str, version_tag: str | None = None) -> None:
        """Initialize the spec history with the given ID and version tag.

        Args:
            id_value: The variant ID (e.g., "Vehicle.speed/v1.0")
            version_tag: The version tag when this entry was created (e.g., "v1.0.0")
        """
        if self.should_have_history():
            self.specHistory = [SpecHistoryEntry.create(id_value, version_tag)]

    def add_history_entry(self, id_value: str, version_tag: str | None = None) -> bool:
        """Add a new entry to the spec history if it's different from the latest one.

        Args:
            id_value: The variant ID (e.g., "Vehicle.speed/v1.0")
            version_tag: The version tag when this entry was created (e.g., "v1.0.0")

        Returns:
            True if a new entry was added, False otherwise
        """
        if not self.should_have_history():
            return False

        if self.specHistory is None:
            self.specHistory = []

        if not self.specHistory or self.specHistory[-1].id != id_value:
            self.specHistory.append(SpecHistoryEntry.create(id_value, version_tag))
            return True

        return False


class SpecHistoryModel(ConceptBaseModel[SpecHistoryNode]):
    """The complete spec history document with history tracking."""


def load_json_file(file_path: Path) -> dict[str, Any]:
    """Load a JSON file and return its contents."""
    with open(file_path) as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {file_path}, got {type(data).__name__}")
    return data


def save_spec_history(spec_history: SpecHistoryModel, file_path: Path) -> None:
    """Save a spec history model to a JSON-LD file."""
    with open(file_path, "w") as f:
        json.dump(spec_history.to_json_ld(), f, indent=2)


def create_jsonld_context(namespace: str, include_spec_history: bool = False) -> dict[str, Any]:
    """Create a JSON-LD context dictionary."""
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
    concept_model: ConceptUriModel, variant_ids: dict[str, str], version_tag: str | None = None
) -> SpecHistoryModel:
    """Convert concept URI model to a spec history model.

    Args:
        concept_model: The concept URI model to convert
        variant_ids: Dictionary mapping concept names to variant IDs
        version_tag: The version tag for this spec history (e.g., "v1.0.0")
    """
    namespace = concept_model.context.get("ns", "")
    updated_context = create_jsonld_context(namespace, include_spec_history=True)

    spec_nodes: list[SpecHistoryNode] = []
    for node in concept_model.graph:
        spec_node_dict = node.to_json_ld()
        spec_node = SpecHistoryNode.model_validate(spec_node_dict)

        if spec_node.should_have_history():
            concept_name = spec_node.get_concept_name()
            if concept_name in variant_ids:
                spec_node.initialize_history(variant_ids[concept_name], version_tag)
            else:
                log.warning(f"No ID found for concept: {concept_name}")

        spec_nodes.append(spec_node)

    return SpecHistoryModel(context=updated_context, graph=spec_nodes)


def update_spec_history_from_concept_uris(
    spec_history: SpecHistoryModel,
    concept_uris: ConceptUriModel,
    variant_ids: dict[str, Any],
    version_tag: str | None = None,
) -> tuple[list[str], list[str]]:
    """Update spec history from concept URIs and IDs.

    Args:
        spec_history: The existing spec history model to update
        concept_uris: The concept URI model with current concepts
        variant_ids: Dictionary mapping concept names to variant IDs
        version_tag: The version tag for new/updated entries (e.g., "v1.0.0")

    Returns:
        Tuple of (new_concepts, updated_ids) lists
    """
    new_concepts: list[str] = []
    updated_ids: list[str] = []
    existing_concepts = spec_history.get_concept_map()

    for uri_node in concept_uris.graph:
        concept_uri = uri_node.id
        concept_name = uri_node.get_concept_name()

        if concept_uri not in existing_concepts:
            spec_node_dict = uri_node.to_json_ld()
            new_node = SpecHistoryNode.model_validate(spec_node_dict)
            if new_node.should_have_history() and concept_name in variant_ids:
                new_node.initialize_history(variant_ids[concept_name], version_tag)
                new_concepts.append(concept_name)
            spec_history.graph.append(new_node)
        elif uri_node.should_have_history():
            existing_node = existing_concepts[concept_uri]
            if not isinstance(existing_node, SpecHistoryNode):
                continue
            if concept_name in variant_ids:
                current_id = variant_ids[concept_name]
                if existing_node.add_history_entry(current_id, version_tag):
                    updated_ids.append(concept_name)

    return new_concepts, updated_ids
