import json
import logging
from pathlib import Path

import click

from concept.models import ConceptUriModel, SpecHistory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_json_file(file_path: Path) -> dict:
    with open(file_path) as f:
        return json.load(f)


def save_spec_history(spec_history: SpecHistory, file_path: Path) -> None:
    with open(file_path, "w") as f:
        # Use by_alias=True to ensure proper JSON-LD attribute names (@id, @type, etc.)
        json.dump(spec_history.to_json_ld(), f, indent=2)


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
def main(
    concept_uri: Path,
    ids: Path,
    init: bool,
    spec_history: Path | None,
    output: Path | None,
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
    """
    # Load the concept URIs and IDs
    concept_uris_data = load_json_file(concept_uri)
    concept_ids = load_json_file(ids)

    # Parse the concept URIs as a model
    concept_uri_model = ConceptUriModel.model_validate(concept_uris_data)

    if init:
        # Initialize a new spec history
        logger.info(f"Initializing new spec history from {concept_uri} and {ids}")
        result = concept_uri_model.to_spec_history(concept_ids)
        save_spec_history(result, output)
        logger.info(f"Spec history initialized and saved to {output}")
        return

    # Update an existing spec history
    if not spec_history:
        raise click.UsageError("--spec-history is required when using --update")

    logger.info(f"Updating spec history {spec_history} with {concept_uri} and {ids}")

    # Load and validate the existing spec history
    existing_history_data = load_json_file(spec_history)
    existing_history = SpecHistory.model_validate(existing_history_data)

    # Update the spec history
    new_concepts, updated_ids = existing_history.update_from_concept_uris(concept_uri_model, concept_ids)

    # Log changes
    if new_concepts:
        logger.info(f"Added {len(new_concepts)} new concepts:")
        for new_concept in new_concepts:
            logger.info(f"  {new_concept}")
    if updated_ids:
        logger.info(f"Updated IDs for {len(updated_ids)} concepts:")
        for updated_id in updated_ids:
            logger.info(f"  {updated_id}")

    if output:
        save_spec_history(existing_history, output)
        logger.info(f"Updated spec history saved to {output}")
    else:
        print(existing_history.model_dump(by_alias=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
