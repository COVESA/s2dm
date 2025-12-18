"""ID Exporter for generating variant-based concept IDs from GraphQL schemas.

This module generates unique identifiers for schema elements in the format
`Concept/vN` where `N` is an incremental variant number that increments
when a concept's specification changes according to graphql-inspector diff.
"""

import json
from collections.abc import Generator
from pathlib import Path

from graphql import (
    GraphQLEnumType,
    GraphQLNamedType,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    get_named_type,
    is_scalar_type,
)

from s2dm import log
from s2dm.exporters.utils.extraction import get_all_named_types
from s2dm.exporters.utils.graphql_type import is_id_type, is_introspection_or_root_type
from s2dm.registry.variant_ids import VariantEntry, VariantIDFile
from s2dm.tools.diff_parser import DiffChange


class IDExporter:
    """Generate variant-based IDs for GraphQL schema concepts.

    Uses graphql-inspector diff output to determine which concepts changed.
    ANY change to a concept (field type change, enum change, directive change, etc.)
    will increment its variant ID. This ensures that each version of a concept
    gets a unique variant number.
    """

    @staticmethod
    def is_breaking_change(criticality: str) -> bool:
        """Check if a criticality level represents a breaking change.

        Treats both 'BREAKING' and 'DANGEROUS' as breaking changes.
        Only 'NON_BREAKING' is considered non-breaking.

        Args:
            criticality: Criticality level from graphql-inspector

        Returns:
            True if the change is breaking, False if non-breaking
        """
        return criticality in ("BREAKING", "DANGEROUS")

    def __init__(
        self,
        schema: GraphQLSchema,
        version_tag: str,
        output: Path | None = None,
        previous_ids_path: Path | None = None,
        diff_output: list[DiffChange] | None = None,
    ):
        """Initialize IDExporter with diff-based ID generation.

        Args:
            schema: The GraphQL schema to process
            output: Path to write IDs JSON file (optional, if None prints to console)
            previous_ids_path: Path to previous ID file for comparison (optional)
            diff_output: Structured diff output from graphql-inspector (optional)
            version_tag: Version tag/identifier for metadata (required)
        """
        self.schema = schema
        self.output = output
        self.previous_ids_path = previous_ids_path
        self.diff_output = diff_output
        self.version_tag = version_tag

    def iter_all_concept_names(self, named_types: list[GraphQLNamedType]) -> Generator[str, None, None]:
        """Iterate over all concept names for enums, object types, and object fields.

        Args:
            named_types: List of GraphQL named types to process

        Yields:
            Concept names (e.g., "Vehicle", "Vehicle.averageSpeed", "WarningTypeEnum")
        """
        # Process enums, object types, and their fields
        for named_type in named_types:
            if is_introspection_or_root_type(named_type.name):
                continue

            if isinstance(named_type, GraphQLEnumType):
                log.debug(f"Processing enum: {named_type.name}")
                yield named_type.name

            elif isinstance(named_type, GraphQLObjectType):
                log.debug(f"Processing object: {named_type.name}")
                # Yield the object type itself
                yield named_type.name
                # Get the ID of all fields in the object
                for field_name, field in named_type.fields.items():
                    # Check if field's type is ID scalar - skip ID fields
                    field_type = get_named_type(field.type)
                    if (
                        is_scalar_type(field_type)
                        and isinstance(field_type, GraphQLScalarType)
                        and is_id_type(field_type.name)
                    ):
                        continue

                    # Check if it's a leaf field (not an object type)
                    if not isinstance(field_type, GraphQLObjectType):
                        concept_name = f"{named_type.name}.{field_name}"
                        yield concept_name

    def get_fields_using_enum(self, enum_name: str) -> set[str]:
        """Find all fields in the schema that use a specific enum type.

        Args:
            enum_name: Name of the enum type

        Returns:
            Set of field paths (e.g., "Vehicle.warningType") that use this enum
        """
        fields_using_enum: set[str] = set()
        enum_type = self.schema.type_map.get(enum_name)

        if not isinstance(enum_type, GraphQLEnumType):
            return fields_using_enum

        # Iterate through all object types and their fields
        for type_name, type_obj in self.schema.type_map.items():
            if not isinstance(type_obj, GraphQLObjectType):
                continue

            for field_name, field in type_obj.fields.items():
                # Check if field's return type is the enum
                field_type = get_named_type(field.type)
                if isinstance(field_type, GraphQLEnumType) and field_type.name == enum_name:
                    fields_using_enum.add(f"{type_name}.{field_name}")

                # Check if any field arguments use the enum
                for arg in field.args.values():
                    arg_type = get_named_type(arg.type)
                    if isinstance(arg_type, GraphQLEnumType) and arg_type.name == enum_name:
                        # For arguments, we still track the field itself
                        fields_using_enum.add(f"{type_name}.{field_name}")

        return fields_using_enum

    def increment_semantic_version(
        self,
        concept_name: str,
        previous_ids: VariantIDFile | None,
        is_breaking: bool,
    ) -> tuple[int, int]:
        """Get the semantic version for a concept, incrementing based on change type.

        Args:
            concept_name: The concept name (e.g., "Vehicle.averageSpeed")
            previous_ids: VariantIDFile instance with previous variant IDs
            is_breaking: True if the change is breaking, False if non-breaking

        Returns:
            Tuple of (major, minor) version numbers
        """
        if previous_ids is None or concept_name not in previous_ids.concepts:
            # New concept - start at v1.0
            return (1, 0)

        previous_entry = previous_ids.concepts[concept_name]
        major, minor = previous_entry.variant

        # Increment based on change type
        if is_breaking:
            # Breaking changes increment major version
            return (major + 1, 0)
        else:
            # Non-breaking changes increment minor version
            return (major, minor + 1)

    def generate_variant_id(self, concept_name: str, major: int, minor: int) -> str:
        """Generate variant-based ID in format: Concept/vM.m (semantic version).

        Args:
            concept_name: The fully qualified concept name
            major: Major version number
            minor: Minor version number

        Returns:
            A variant ID string in the format: "Concept/vM.m" (e.g., "Concept/v1.0")
        """
        return f"{concept_name}/v{major}.{minor}"

    def run(self) -> VariantIDFile:
        """Generate variant-based IDs for GraphQL schema fields and enums.

        Returns:
            VariantIDFile instance with metadata and concepts
        """
        log.info(f"Generating variant IDs from schema '{self.schema}', output is '{self.output}'")

        # Load previous IDs if path is provided
        previous_ids: VariantIDFile | None = None
        if self.previous_ids_path:
            try:
                previous_ids = VariantIDFile.load(self.previous_ids_path)
            except (OSError, json.JSONDecodeError, ValueError) as e:
                error_msg = f"Failed to load previous IDs from {self.previous_ids_path}: {e}"
                log.error(error_msg)
                raise RuntimeError(error_msg) from e

        # Collect all changed concepts from diff output with their breaking status
        # Using a dict ensures that each concept appears only once, regardless of
        # how many changes affect it (e.g., multiple enum values added = one increment).
        changed_concepts: dict[str, bool] = {}  # concept_name -> is_breaking
        if self.diff_output:
            # Extract changed concepts directly from diff
            # Note: The Node.js script always sets concept_name (initialized from path,
            # or set to typeName for enum changes), so we can use it directly.
            for change in self.diff_output:
                concept_name = change.concept_name
                if concept_name:
                    is_breaking = self.is_breaking_change(change.criticality)
                    # Track whether concept has any breaking changes
                    # Multiple changes to the same concept are deduplicated here
                    if concept_name not in changed_concepts:
                        changed_concepts[concept_name] = is_breaking
                    else:
                        # Update to breaking if any change is breaking
                        changed_concepts[concept_name] = changed_concepts[concept_name] or is_breaking

                    # If this is a field change (contains a dot), also mark the parent object type as changed
                    if "." in concept_name:
                        parent_type_name = concept_name.split(".")[0]
                        if parent_type_name not in changed_concepts:
                            changed_concepts[parent_type_name] = is_breaking
                        else:
                            # Update to breaking if any change is breaking
                            changed_concepts[parent_type_name] = changed_concepts[parent_type_name] or is_breaking
                        log.debug(
                            f"Field {concept_name} changed ({change.type}), "
                            f"also marking parent type {parent_type_name} as changed"
                        )

                    # If this is an enum change, find all fields using this enum
                    # The Node.js script sets concept_name to the enum name for enum changes
                    concept_type = self.schema.type_map.get(concept_name)
                    if isinstance(concept_type, GraphQLEnumType):
                        fields_using_enum = self.get_fields_using_enum(concept_name)
                        for field_name in fields_using_enum:
                            if field_name not in changed_concepts:
                                changed_concepts[field_name] = is_breaking
                            else:
                                # Update to breaking if any change is breaking
                                changed_concepts[field_name] = changed_concepts[field_name] or is_breaking
                        if fields_using_enum:
                            log.debug(f"Enum {concept_name} changed, affecting fields: {sorted(fields_using_enum)}")

            log.info(f"Found {len(changed_concepts)} changed concepts that will get variant increments")

        # Generate IDs for all concepts in current schema
        all_named_types = get_all_named_types(schema=self.schema)
        concepts: dict[str, VariantEntry] = {}

        for concept_name in self.iter_all_concept_names(named_types=all_named_types):
            # Determine semantic version: increment if changed, keep if unchanged, start at v1.0 if new
            if concept_name in changed_concepts:
                is_breaking = changed_concepts[concept_name]
                major, minor = self.increment_semantic_version(concept_name, previous_ids, is_breaking)
                # Increment variant_counter for this concept by exactly 1
                # Note: Even if multiple changes affect this concept, changed_concepts
                # deduplicates them, so this increments only once per update.
                if previous_ids and concept_name in previous_ids.concepts:
                    variant_counter = previous_ids.concepts[concept_name].variant_counter + 1
                else:
                    variant_counter = 1
            elif previous_ids and concept_name in previous_ids.concepts:
                previous_entry = previous_ids.concepts[concept_name]
                major, minor = previous_entry.variant
                variant_counter = previous_entry.variant_counter
            else:
                # New concept - start at v1.0 with counter 1
                major, minor = (1, 0)
                variant_counter = 1

            concepts[concept_name] = VariantEntry(
                id=self.generate_variant_id(concept_name, major, minor),
                variant_counter=variant_counter,
                removed_in_version=None,
            )

            log.debug(f"Concept: {concept_name} -> {concepts[concept_name].id} (counter: {variant_counter})")

        # Add removed concepts that are no longer in schema
        if previous_ids:
            for concept_name, previous_entry in previous_ids.concepts.items():
                if concept_name not in concepts:
                    removed_version = (
                        previous_entry.removed_in_version
                        if previous_entry.removed_in_version is not None
                        else self.version_tag
                    )
                    major, minor = previous_entry.variant
                    concepts[concept_name] = VariantEntry(
                        id=self.generate_variant_id(concept_name, major, minor),
                        variant_counter=previous_entry.variant_counter,
                        removed_in_version=removed_version,
                    )

        # Build result with metadata
        result = VariantIDFile(
            version_tag=self.version_tag,
            concepts=concepts,
        )

        # Write the IDs to the output file (if output path provided)
        if self.output is not None:
            log.info(f"Writing variant IDs to '{self.output}'")
            result.save(self.output)

        return result
