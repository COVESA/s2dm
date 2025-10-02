import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click

from s2dm import log
from s2dm.concept.models import ConceptUriModel, SpecHistoryModel
from s2dm.concept.services import (
    convert_concept_uri_to_spec_history,
    load_json_file,
    save_spec_history,
    update_spec_history_from_concept_uris,
)
from s2dm.exporters.utils.schema_loader import build_schema_str


class SpecHistoryExporter:
    def __init__(
        self,
        schemas: list[Path],
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
        self.schemas = schemas
        self.output = output
        self.history_dir = history_dir

    @staticmethod
    def extract_type_definition(content: str, type_name: str) -> str | None:
        """
        Extract a GraphQL type definition from the schema file.

        Args:
            content: The schema file content as a string
            type_name: Name of the type to extract

        Returns:
            The complete type definition as a string, or None if not found
        """
        pattern = rf"(type|enum)\s+{re.escape(type_name)}\s*{{[^{{}}]*}}"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(0)
        log.warning(f"Could not find type definition for {type_name} in schema")
        return None

    @staticmethod
    def generate_history_filename(type_name: str, id_value: str, timestamp: datetime) -> str:
        """
        Generate a filename for a type definition history file.

        Args:
            type_name: The name of the GraphQL type
            id_value: The ID value for the concept
            timestamp: The timestamp to use

        Returns:
            Filename in the format <type_name>_<YYYYMMDDHHMMSS>_<id>.graphql
        """
        timestamp_str = timestamp.strftime("%Y%m%d%H%M%S")
        return f"{type_name}_{timestamp_str}_{id_value}.graphql"

    @staticmethod
    def save_type_definition(
        id_value: str,
        parent_type: str,
        type_def: str,
        history_dir: Path,
        timestamp: datetime,
    ) -> None:
        """
        Save a type definition to a file in the history directory.

        Args:
            id_value: The ID value for the concept
            parent_type: The parent type name
            type_def: The complete type definition as a string
            history_dir: Directory to save the file in
            timestamp: The timestamp to use (defaults to current UTC time)
        """
        history_dir.mkdir(parents=True, exist_ok=True)
        filename = SpecHistoryExporter.generate_history_filename(parent_type, id_value, timestamp)
        file_path = history_dir / filename
        with open(file_path, "w") as f:
            f.write(type_def)
        log.debug(f"Saved type definition for {parent_type} to {file_path}")

    def process_type_definitions(
        self,
        new_concepts: list[str],
        updated_ids: list[str],
        concept_ids: dict[str, str],
        schema_paths: list[Path],
        history_dir: Path,
    ) -> None:
        """
        Process and save type definitions for new or updated concepts.

        Args:
            new_concepts: List of new concept names
            updated_ids: List of updated concept names
            concept_ids: Dictionary mapping concept names to their IDs
            schema_paths: List of paths to the GraphQL schema files
            history_dir: Directory to save type definitions in
        """
        log.info(f"Processing type definitions for {len(new_concepts)} new and {len(updated_ids)} updated concepts")
        timestamp = datetime.now(UTC)
        concepts_to_process = new_concepts + updated_ids
        schema_content = build_schema_str(schema_paths)
        for concept_name in concepts_to_process:
            if concept_name not in concept_ids:
                log.warning(f"No ID found for concept {concept_name}, skipping")
                continue
            parent_type = concept_name.split(".")[0] if "." in concept_name else concept_name
            id_value = concept_ids[concept_name]
            type_def = self.extract_type_definition(schema_content, parent_type)
            if type_def:
                self.save_type_definition(id_value, parent_type, type_def, history_dir, timestamp)
            else:
                log.warning(f"Could not extract type definition for {parent_type}")

    def init_spec_history_model(
        self, concept_uris: dict[str, Any], concept_ids: dict[str, Any], concept_uri_model: ConceptUriModel
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
        """
        log.debug(f"Initializing new spec history from {concept_uris} and {concept_ids}")
        result = convert_concept_uri_to_spec_history(concept_uri_model, concept_ids)
        if self.output:
            save_spec_history(result, self.output)
            log.info(f"Spec history initialized and saved to {self.output}")
        else:
            log.debug(result.model_dump(by_alias=True))
        self.process_type_definitions(list(concept_ids.keys()), [], concept_ids, self.schemas, self.history_dir)
        return result

    def update_spec_history_model(
        self,
        concept_uris: dict[str, Any],
        concept_ids: dict[str, Any],
        concept_uri_model: ConceptUriModel,
        spec_history_path: Path,
    ) -> SpecHistoryModel:
        """
        Update a spec history registry to track changes in concept realizations.

        This method tracks the history of realization IDs for each concept over time.
        It can either initialize a new spec history or update an existing one.

        For update provide:
        - A concept URI file (self.concept_uri)
        - An IDs file (self.ids)
        - An output path (self.output)
        - An existing spec history file (self.spec_history)

        For saving type definitions:
        - A GraphQL schema file (self.schemas)
        - Optionally, a directory to store type history (self.history_dir, default: "./history")
        """
        if spec_history_path is None:
            raise click.UsageError("spec history is required when using --update")

        log.info(f"Updating spec history {spec_history_path} with {concept_uris} and {concept_ids}")
        existing_history_data = load_json_file(spec_history_path)
        existing_history = SpecHistoryModel.model_validate(existing_history_data)
        new_concepts, updated_ids = update_spec_history_from_concept_uris(
            existing_history, concept_uri_model, concept_ids
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
            self.process_type_definitions(new_concepts, updated_ids, concept_ids, self.schemas, self.history_dir)
        if self.output:
            save_spec_history(existing_history, self.output)
            log.info(f"Updated spec history saved to {self.output}")
        else:
            log.info(existing_history.model_dump(by_alias=True))

        return existing_history

    def run(
        self, concept_uris_path: Path, concept_ids_path: Path, init: bool, spec_history_path: Path | None = None
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
        concept_ids = load_json_file(concept_ids_path)
        concept_uri_model = ConceptUriModel.model_validate(concept_uris_data)

        if init:
            return self.init_spec_history_model(concept_uris_data, concept_ids, concept_uri_model)

        if not spec_history_path:
            raise click.UsageError("spec history is required when using update")

        return self.update_spec_history_model(concept_uris_data, concept_ids, concept_uri_model, spec_history_path)


@click.command()
@click.option(
    "--concept-uri",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to the concept URI JSON-LD file",
)
@click.option(
    "--ids",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to the IDs JSON file",
)
@click.option(
    "--schema",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to GraphQL schema file to extract type definitions",
)
@click.option(
    "--init/--update",
    default=True,
    help="Initialize a new spec history or update an existing one",
)
@click.option(
    "--spec-history",
    type=click.Path(exists=True, path_type=Path),
    help="Path to an existing spec history JSON-LD file (for updates)",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="Path to the output spec history JSON-LD file",
)
@click.option(
    "--history-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default="history",
    help="Directory to store type history files",
)
def main(
    concept_uri: Path,
    ids: Path,
    schemas: list[Path],
    init: bool,
    spec_history: Path | None,
    output: Path | None,
    history_dir: Path,
) -> None:
    """CLI entrypoint: instantiate SpecHistoryExporter and run."""
    exporter = SpecHistoryExporter(
        schemas=schemas,
        output=output,
        history_dir=history_dir,
    )
    spec_history_model = exporter.run(
        concept_uris_path=concept_uri,
        concept_ids_path=ids,
        init=init,
        spec_history_path=spec_history,
    )
    log.info(f"{spec_history_model=}")


if __name__ == "__main__":
    main()
