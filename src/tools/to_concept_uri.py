import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import click
from graphql import (
    GraphQLEnumType,
    GraphQLList,
    GraphQLNamedType,
    GraphQLObjectType,
)

from concept.models import ConceptUriModel, ConceptUriNode, create_jsonld_context
from tools.utils import get_all_named_types, load_schema

logger = logging.getLogger(__name__)


def generate_concept_uri(
    prefix: str,
    name: str,
) -> str:
    """Generate a concept URI for a field.

    Args:
        prefix: The prefix for the URI (e.g., "ns")
        name: The name of the field or type

    Returns:
        The generated concept URI
    """
    return f"{prefix}:{name}"


@dataclass
class Concepts:
    fields: list[str] = field(default_factory=list)
    enums: list[str] = field(default_factory=list)
    objects: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    nested_objects: dict[str, str] = field(default_factory=dict)


def iter_all_concepts(named_types: list[GraphQLNamedType]):
    concepts = Concepts()
    for named_type in named_types:
        if named_type.name in ("Query", "Mutation"):
            continue

        if isinstance(named_type, GraphQLEnumType):
            logging.debug(f"Processing enum: {named_type.name}")
            concepts.enums.append(named_type.name)

        elif isinstance(named_type, GraphQLObjectType):
            logging.debug(f"Processing object: {named_type.name}")
            # Get the ID of all fields in the object
            for field_name, field in named_type.fields.items():
                if field_name.lower() == "id":
                    continue

                field_fqn = f"{named_type.name}.{field_name}"

                if isinstance(field.type, GraphQLObjectType):
                    # field uses the object type
                    concepts.nested_objects[field_fqn] = field.type.name
                elif isinstance(field.type, GraphQLList):
                    # field uses a list of the object type
                    internal_type = field.type
                    while hasattr(internal_type, "of_type"):
                        internal_type = internal_type.of_type
                    concepts.nested_objects[field_fqn] = internal_type.name
                else:
                    # field uses a scalar type or enum type
                    concepts.objects[named_type.name].append(field_fqn)
                    concepts.fields.append(field_fqn)

    return concepts


def create_concept_uri_model(concepts: Concepts, namespace: str, prefix: str) -> ConceptUriModel:
    """Create a ConceptUriModel from Concepts.

    Args:
        concepts: The Concepts object with fields, enums, objects, and nested objects
        namespace: The namespace URI
        prefix: The prefix for the URIs

    Returns:
        A ConceptUriModel representing the concepts
    """
    # Create the JSON-LD context
    context = create_jsonld_context(namespace)

    # Create all nodes
    graph: list[ConceptUriNode] = []

    # Helper function to create a URI
    def uri(name: str) -> str:
        return f"{prefix}:{name}"

    # Object nodes
    for type_name, fields in concepts.objects.items():
        graph.append(
            ConceptUriNode(
                id=uri(type_name),
                type="Object",
                hasField=[uri(field) for field in fields],
            )
        )

    # Field nodes
    for field_id in concepts.fields:
        graph.append(
            ConceptUriNode(
                id=uri(field_id),
                type="Field",
            )
        )

    # Enum nodes
    for enum in concepts.enums:
        graph.append(
            ConceptUriNode(
                id=uri(enum),
                type="Enum",
            )
        )

    # Nested object relationships
    for field_id, object_type in concepts.nested_objects.items():
        graph.append(
            ConceptUriNode(
                id=uri(field_id),
                type="ObjectField",
                hasNestedObject=uri(object_type),
            )
        )

    # Create and return the model
    return ConceptUriModel(context=context, graph=graph)


@click.command()
@click.argument("schema", type=click.Path(exists=True), required=True)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="Output file path for the JSON-LD file",
)
@click.option(
    "--namespace",
    default="https://example.org/vss#",
    help="The namespace for the URIs",
)
@click.option(
    "--prefix",
    default="ns",
    help="The prefix to use for the URIs",
)
def main(
    schema: Path,
    output: Path | None,
    namespace: str,
    prefix: str,
):
    """Generate concept URIs for a GraphQL schema.

    The script will generate concept URIs for all objects, fields, and enums in the schema,
    excluding cross-references and ID fields. The URIs will be output in JSON-LD format.
    """
    logging.info(f"Processing schema '{schema}'")

    # Load the schema
    graphql_schema = load_schema(schema)

    # Process the schema to get concepts
    concepts = iter_all_concepts(get_all_named_types(graphql_schema))

    # Create concept URI model
    concept_uri_model = create_concept_uri_model(concepts, namespace, prefix)

    # Output options
    if output:
        with open(output, "w", encoding="utf-8") as output_file:
            logging.info(f"Writing data to '{output}'")
            json.dump(concept_uri_model.to_json_ld(), output_file, indent=2)
    else:
        print("-" * 80)
        print(json.dumps(concept_uri_model.to_json_ld(), indent=2))


if __name__ == "__main__":
    main()
