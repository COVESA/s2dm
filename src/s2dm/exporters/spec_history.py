import re
from pathlib import Path
from typing import Any

from s2dm import log
from s2dm.registry.concept_uris import ConceptUriModel
from s2dm.registry.spec_history import (
    SpecHistoryModel,
    convert_concept_uri_to_spec_history,
    load_json_file,
    save_spec_history,
    update_spec_history_from_concept_uris,
)


class SpecHistoryExporter:
    def __init__(
        self,
        schema_content: str,
        output: Path | None,
        history_dir: Path,
    ):
        """
        Args:
            concept_uri: Path to the concept URI JSON-LD file
            ids: Path to the IDs JSON file
            schemas: List of paths to GraphQL schema files to extract type definitions
            init: Whether to initialize a new spec history (True) or update (False)
            spec_history: Path to an existing spec history JSON-LD file (for updates)
            output: Path to the output spec history JSON-LD file
            history_dir: Directory to store type history files
        """
        self.schema_content = schema_content
        self.output = output
        self.history_dir = history_dir

    def _extract_type_definition(self, type_name: str) -> str | None:
        """
        Extract a GraphQL type definition from the schema file.

        Args:
            type_name: Name of the type to extract

        Returns:
            The complete type definition as a string, or None if not found
        """
        pattern = rf"(type|enum)\s+{re.escape(type_name)}\s*{{[^{{}}]*}}"
        match = re.search(pattern, self.schema_content, re.DOTALL)
        if match:
            return match.group(0)
        return None

    def init_spec_history_model(
        self,
        concept_uris: dict[str, Any],
        variant_ids: dict[str, Any],
        concept_uri_model: ConceptUriModel,
        version_tag: str | None = None,
    ) -> SpecHistoryModel:
        """
        Generate a first spec history registry to track changes in concept realizations.

        This method tracks the history of realization IDs for each concept over time.
        It can either initialize a new spec history or update an existing one.

        For initialization (self.init == True), provide:
        - A concept URI file (self.concept_uri)
        - An IDs file (self.ids)
        - An output path (self.output)

        For updates (self.init == False), also provide:
        - An existing spec history file (self.spec_history)

        For saving type definitions:
        - A GraphQL schema file (self.schemas)
        - Optionally, a directory to store type history (self.history_dir, default: "./history")

        Args:
            concept_uris: Dictionary of concept URIs
            variant_ids: Dictionary mapping concept names to variant IDs
            concept_uri_model: The concept URI model
            version_tag: The version tag for this spec history (e.g., "v1.0.0")
        """
        log.debug(f"Initializing new spec history from {concept_uris} and {variant_ids}")
        result = convert_concept_uri_to_spec_history(concept_uri_model, variant_ids, version_tag)
        if self.output:
            save_spec_history(result, self.output)
            log.info(f"Spec history initialized and saved to {self.output}")
        else:
            log.debug(result.model_dump(by_alias=True))
        self.process_type_definitions(list(variant_ids.keys()), [], variant_ids, self.history_dir)
        return result

    def update_spec_history_model(
        self,
        concept_uris: dict[str, Any],
        variant_ids: dict[str, Any],
        concept_uri_model: ConceptUriModel,
        spec_history_path: Path,
        version_tag: str | None = None,
    ) -> SpecHistoryModel:
        """
        Update a spec history registry to track changes in concept realizations.

        This method tracks the history of realization IDs for each concept over time.
        It can either initialize a new spec history or update an existing one.

        For update provide:
        - A concept URI file (self.concept_uri)
        - A variant IDs file (self.ids)
        - An output path (self.output)
        - An existing spec history file (self.spec_history)

        For saving type definitions:
        - A GraphQL schema file (self.schemas)
        - Optionally, a directory to store type history (self.history_dir, default: "./history")

        Args:
            concept_uris: Dictionary of concept URIs
            variant_ids: Dictionary mapping concept names to variant IDs
            concept_uri_model: The concept URI model
            spec_history_path: Path to the existing spec history file
            version_tag: The version tag for new/updated entries (e.g., "v1.0.0")
        """
        log.info(f"Updating spec history {spec_history_path} with {concept_uris} and {variant_ids}")
        existing_history_data = load_json_file(spec_history_path)
        existing_history = SpecHistoryModel.model_validate(existing_history_data)
        new_concepts, updated_ids = update_spec_history_from_concept_uris(
            existing_history, concept_uri_model, variant_ids, version_tag
        )
        if new_concepts:
            log.info(f"Added {len(new_concepts)} new concepts:")
            for new_concept in new_concepts:
                log.info(f"  {new_concept}")
        if updated_ids:
            log.info(f"Updated IDs for {len(updated_ids)} concepts:")
            for updated_id in updated_ids:
                log.info(f"  {updated_id}")
        if new_concepts or updated_ids:
            self.process_type_definitions(new_concepts, updated_ids, variant_ids, self.history_dir)
        if self.output:
            save_spec_history(existing_history, self.output)
            log.info(f"Updated spec history saved to {self.output}")
        else:
            log.info(existing_history.model_dump(by_alias=True))

        return existing_history

    def process_type_definitions(
        self,
        new_concepts: list[str],
        updated_ids: list[str],
        variant_ids: dict[str, str],
        history_dir: Path,
    ) -> None:
        """
        Process and save type definitions for new or updated concepts.

        Args:
            new_concepts: List of new concept names
            updated_ids: List of updated concept names
            variant_ids: Dictionary mapping concept names to their variant IDs
            history_dir: Directory to save type definitions in
        """
        log.info(f"Processing type definitions for {len(new_concepts)} new and {len(updated_ids)} updated concepts")
        concepts_to_process = new_concepts + updated_ids
        for concept_name in concepts_to_process:
            if concept_name not in variant_ids:
                log.warning(f"No variant ID found for concept {concept_name}, skipping")
                continue
            parent_type = concept_name.split(".")[0] if "." in concept_name else concept_name
            id_value = variant_ids[concept_name]
            type_def = self._extract_type_definition(parent_type)
            if type_def:
                self.save_type_definition(id_value, parent_type, type_def, history_dir)
            else:
                log.debug(f"Could not extract type definition for {parent_type}")

    def run(
        self, concept_uris_path: Path, variant_ids_path: Path, init: bool, spec_history_path: Path | None = None
    ) -> SpecHistoryModel:
        """
        Generate or update a spec history registry to track changes in concept realizations.

        This method tracks the history of realization IDs for each concept over time.
        It can either initialize a new spec history or update an existing one.

        For initialization (init == True), provide:
        - A concept URI file (self.concept_uri)
        - An IDs file (self.ids)
        - An output path (self.output)

        For updates (init == False), also provide:
        - An existing spec history file (self.spec_history)

        For saving type definitions:
        - A GraphQL schema file (self.schemas)
        - Optionally, a directory to store type history (self.history_dir, default: "./history")
        """
        # Load the concept URIs and IDs
        concept_uris_data = load_json_file(concept_uris_path)
        variant_ids = load_json_file(variant_ids_path)
        concept_uri_model = ConceptUriModel.model_validate(concept_uris_data)

        if init:
            return self.init_spec_history_model(concept_uris_data, variant_ids, concept_uri_model)

        if not spec_history_path:
            raise ValueError("spec history is required when using update")

        return self.update_spec_history_model(concept_uris_data, variant_ids, concept_uri_model, spec_history_path)

    @staticmethod
    def generate_history_filename(id_value: str) -> str:
        """Generate a filename for a type definition history file.

        Args:
            id_value: The ID value for the concept (variant ID format: Concept/vN)

        Returns:
            Filename in the format <sanitized_id>.graphql
            The ID is sanitized for filesystem compatibility by replacing '/' with '_'.
        """
        # Sanitize ID for filesystem: replace '/' with '_'
        sanitized_id = id_value.replace("/", "_")
        return f"{sanitized_id}.graphql"

    @staticmethod
    def save_type_definition(
        id_value: str,
        parent_type: str,
        type_def: str,
        history_dir: Path,
    ) -> None:
        """Save a type definition to a file in the history directory.

        Args:
            id_value: The ID value for the concept (variant ID format: Concept/vN)
            parent_type: The parent type name
            type_def: The complete type definition as a string
            history_dir: Directory to save the file in
        """
        history_dir.mkdir(parents=True, exist_ok=True)
        filename = SpecHistoryExporter.generate_history_filename(id_value)
        file_path: Path = history_dir / filename

        with open(file_path, "w") as f:
            f.write(type_def)
        log.debug(f"Saved type definition for {parent_type} to {file_path}")
