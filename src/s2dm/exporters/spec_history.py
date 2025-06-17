import re
from datetime import UTC, datetime
from pathlib import Path

import click

from s2dm import log
from s2dm.concept.models import ConceptUriModel, SpecHistoryModel
from s2dm.concept.services import (
    convert_concept_uri_to_spec_history,
    load_json_file,
    save_spec_history,
    update_spec_history_from_concept_uris,
)
from s2dm.exporters.utils import build_schema_str


def extract_type_definition(content: str, type_name: str) -> str | None:
    """Extract a GraphQL type definition from the schema file.

    Args:
        schema_path: Path to the GraphQL schema file
        type_name: Name of the type to extract

    Returns:
        The complete type definition as a string, or None if not found
    """

    # Pattern matches: type TypeName { ... } or enum TypeName { ... }
    pattern = rf"(type|enum)\s+{re.escape(type_name)}\s*{{[^{{}}]*}}"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(0)

    log.warning(f"Could not find type definition for {type_name} in schema")
    return None


def generate_history_filename(type_name: str, id_value: str, timestamp: datetime) -> str:
    """Generate a filename for a type definition history file.

    Args:
        type_name: The name of the GraphQL type
        id_value: The ID value for the concept
        timestamp: The timestamp to use
    Returns:
        Filename in the format <type_name>_<YYYYMMDDHHMMSS>_<id>.graphql
    """
    timestamp_str = timestamp.strftime("%Y%m%d%H%M%S")
    return f"{type_name}_{timestamp_str}_{id_value}.graphql"


def save_type_definition(
    id_value: str,
    parent_type: str,
    type_def: str,
    history_dir: Path,
    timestamp: datetime,
) -> None:
    """Save a type definition to a file in the history directory.

    Args:
        id_value: The ID value for the concept
        parent_type: The parent type name
        type_def: The complete type definition as a string
        history_dir: Directory to save the file in
        timestamp: The timestamp to use (defaults to current UTC time)
    """
    # Create history directory if it doesn't exist
    history_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    filename = generate_history_filename(parent_type, id_value, timestamp)

    # Create file path
    file_path = history_dir / filename

    # Write type definition to file
    with open(file_path, "w") as f:
        f.write(type_def)

    log.info(f"Saved type definition for {parent_type} to {file_path}")


def process_type_definitions(
    new_concepts: list[str],
    updated_ids: list[str],
    concept_ids: dict[str, str],
    schema_path: Path,
    history_dir: Path,
) -> None:
    """Process and save type definitions for new or updated concepts.

    Args:
        new_concepts: List of new concept names
        updated_ids: List of updated concept names
        concept_ids: Dictionary mapping concept names to their IDs
        schema_path: Path to the GraphQL schema file
        history_dir: Directory to save type definitions in
    """
    log.info(f"Processing type definitions for {len(new_concepts)} new and {len(updated_ids)} updated concepts")

    # Use the same timestamp for all files in this batch
    timestamp = datetime.now(UTC)

    # Process both new concepts and updated IDs
    concepts_to_process = new_concepts + updated_ids

    schema_content = build_schema_str(schema_path)

    for concept_name in concepts_to_process:
        if concept_name not in concept_ids:
            log.warning(f"No ID found for concept {concept_name}, skipping")
            continue

        # Extract parent type from concept name (format: "parent.field" or "enum_type")
        parent_type = concept_name.split(".")[0] if "." in concept_name else concept_name
        id_value = concept_ids[concept_name]

        # Extract type definition from schema file
        type_def = extract_type_definition(schema_content, parent_type)
        if type_def:
            # Save to history file
            save_type_definition(id_value, parent_type, type_def, history_dir, timestamp)
        else:
            log.warning(f"Could not extract type definition for {parent_type}")


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
    schema: Path,
    init: bool,
    spec_history: Path | None,
    output: Path | None,
    history_dir: Path,
) -> None:
    """Generate or update a spec history registry to track changes in concept realizations.

    This script tracks the history of realization IDs for each concept over time.
    It can either initialize a new spec history or update an existing one.

    For initialization (--init), provide:
    - A concept URI file (--concept-uri)
    - An IDs file (--ids)
    - An output path (--output)

    For updates (--update), also provide:
    - An existing spec history file (--spec-history)

    For saving type definitions:
    - A GraphQL schema file (--schema)
    - Optionally, a directory to store type history (--history-dir, default: "./history")
    """
    # Load the concept URIs and IDs
    concept_uris_data = load_json_file(concept_uri)
    concept_ids = load_json_file(ids)

    # Parse the concept URIs as a model
    concept_uri_model = ConceptUriModel.model_validate(concept_uris_data)

    if init:
        # Initialize a new spec history
        log.info(f"Initializing new spec history from {concept_uri} and {ids}")
        result = convert_concept_uri_to_spec_history(concept_uri_model, concept_ids)

        if output:
            save_spec_history(result, output)
            log.info(f"Spec history initialized and saved to {output}")
        else:
            print(result.model_dump(by_alias=True))

        # Save type definitions for all concepts if schema is provided
        process_type_definitions(list(concept_ids.keys()), [], concept_ids, schema, history_dir)

        return

    # Update an existing spec history
    if not spec_history:
        raise click.UsageError("--spec-history is required when using --update")

    log.info(f"Updating spec history {spec_history} with {concept_uri} and {ids}")

    # Load and validate the existing spec history
    existing_history_data = load_json_file(spec_history)
    existing_history = SpecHistoryModel.model_validate(existing_history_data)

    # Update the spec history
    new_concepts, updated_ids = update_spec_history_from_concept_uris(existing_history, concept_uri_model, concept_ids)

    # Log changes
    if new_concepts:
        log.info(f"Added {len(new_concepts)} new concepts:")
        for new_concept in new_concepts:
            log.info(f"  {new_concept}")
    if updated_ids:
        log.info(f"Updated IDs for {len(updated_ids)} concepts:")
        for updated_id in updated_ids:
            log.info(f"  {updated_id}")

    # Process type definitions if schema is provided and we have new or updated concepts
    if new_concepts or updated_ids:
        process_type_definitions(new_concepts, updated_ids, concept_ids, schema, history_dir)

    if output:
        save_spec_history(existing_history, output)
        log.info(f"Updated spec history saved to {output}")
    else:
        print(existing_history.model_dump(by_alias=True))


if __name__ == "__main__":
    main()
