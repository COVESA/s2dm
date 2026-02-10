"""Concept extraction models for GraphQL schema elements.

This module defines data models used for extracting and organizing concepts
from GraphQL schemas. These are general-purpose utilities used by various
exporters (SKOS, concept URI, etc.).

For spec history models (Concept URI, Spec History, Concept ID), see
s2dm.registry.* modules.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from graphql import GraphQLField
from typing_extensions import TypedDict


class FieldMetadata(TypedDict):
    """Metadata for a GraphQL field in the concepts extraction.

    This provides structured access to GraphQL field information without
    requiring string parsing, ensuring type safety and consistency.
    """

    object_name: str  # The GraphQL object type name (e.g., "Vehicle")
    field_name: str  # The GraphQL field name (e.g., "averageSpeed")
    field_definition: GraphQLField  # The GraphQL field definition object


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
