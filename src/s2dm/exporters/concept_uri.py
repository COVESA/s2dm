import json
from pathlib import Path

from s2dm import log
from s2dm.concept.services import create_concept_uri_model, iter_all_concepts
from s2dm.exporters.utils.extraction import get_all_named_types
from s2dm.exporters.utils.schema_loader import load_schema


def process_schema(
    schema: Path,
    output: Path | None,
    namespace: str,
    prefix: str,
) -> None:
    """Generate concept URIs for a GraphQL schema.

    The script will generate concept URIs for all objects, fields, and enums in the schema,
    excluding cross-references and ID fields. The URIs will be output in JSON-LD format.

    Args:
        schema: Path to the GraphQL schema file
        output: Optional output file path
        namespace: The namespace for the URIs
        prefix: The prefix to use for the URIs
    """
    log.info(f"Processing schema '{schema}'")

    # Load the schema
    graphql_schema = load_schema(schema)

    # Process the schema to get concepts
    concepts = iter_all_concepts(get_all_named_types(graphql_schema))

    # Create concept URI model
    concept_uri_model = create_concept_uri_model(concepts, namespace, prefix)

    # Output options
    if output:
        with open(output, "w", encoding="utf-8") as output_file:
            log.info(f"Writing data to '{output}'")
            json.dump(concept_uri_model.to_json_ld(), output_file, indent=2)
    else:
        print("-" * 80)
        print(json.dumps(concept_uri_model.to_json_ld(), indent=2))
