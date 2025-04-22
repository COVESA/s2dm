import json
import logging
import os
import re
import sys
from collections.abc import Generator
from pathlib import Path

import click
import yaml
from graphql import (
    GraphQLField,
    GraphQLObjectType,
)

from idgen.idgen import fnv1_32_wrapper
from idgen.spec import IDGenerationSpec
from tools.utils import load_schema

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s - %(levelname)s - %(message)s")


def str_to_screaming_snake_case(text: str) -> str:
    """Converts a string to screaming snake case (i.e., CAPITAL LETTERS)"""
    text = re.sub(r"[^a-zA-Z0-9]", " ", text)
    words = text.split()
    return "_".join(word.upper() for word in words)


def load_unit_lookup(units_file: Path) -> dict[str, str]:
    unit_lookup = {}
    with open(units_file) as f:
        units = yaml.safe_load(f)
    for unit in units:
        key = str_to_screaming_snake_case(units[unit]["unit"])
        value = unit
        unit_lookup[key] = value
    return unit_lookup


def iter_all_nodes(
    schema: GraphQLObjectType,
    unit_lookup: dict[str, str],
    current_path: str = "",
    visited=None,
) -> Generator[IDGenerationSpec, None, None]:
    """
    Recursively yield fully qualified names (FQNs) for all fields in a GraphQLObjectType,
    traversing all the way down nested object types.

    Args:
        schema (GraphQLObjectType): The GraphQL object type to traverse.
        current_path (str): The current FQN prefix.
        visited (set): Set of visited (type, path) to avoid infinite recursion.

    Yields:
        tuple[str, GraphQLObjectType]: The FQN of each field and the type of the field.
    """

    if visited is None:
        visited = set()

    for field_name, field in schema.fields.items():
        # Skip the id field
        if field_name.lower() == "id":
            continue

        assert isinstance(field_name, str)
        assert isinstance(field, GraphQLField)

        id_spec = IDGenerationSpec.from_field(
            prefix=current_path,
            field_name=field_name,
            field=field,
            unit_lookup=unit_lookup,
        )

        field_type = id_spec._field_type.field_type

        yield id_spec

        # Avoid infinite recursion on circular references
        if isinstance(field_type, GraphQLObjectType) and id_spec.name not in visited:
            visited.add(id_spec.name)
            yield from iter_all_nodes(
                schema=field_type,
                unit_lookup=unit_lookup,
                current_path=id_spec.name,
                visited=visited,
            )


@click.command()
@click.argument("schema", type=click.Path(exists=True), required=True)
@click.argument("units_file", type=click.Path(exists=True), required=True)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
)
@click.option("--strict-mode/--no-strict-mode", default=False)
@click.option("--dry-run/--no-dry-run", default=False)
def main(schema: Path, units_file: Path, output: Path, strict_mode: bool, dry_run: bool):
    logging.info(f"Using units file '{units_file}', input is '{schema}', and output is '{output}'")

    # Pass the schema content to build_schema
    graphql_schema = load_schema(schema)

    unit_lookup = load_unit_lookup(units_file)

    node_ids = {}
    existing_ids = set()

    # Start from the root Query type and recursively traverse all paths
    if graphql_schema.query_type is not None:
        for node in iter_all_nodes(graphql_schema.query_type, unit_lookup=unit_lookup):
            if node.is_realization():
                generated_id = fnv1_32_wrapper(node, strict_mode=strict_mode)

                if generated_id in existing_ids:
                    logging.warning(f"Duplicate ID found: {generated_id} for {node.name}")
                    sys.exit(1)
                else:
                    existing_ids.add(generated_id)

                node_ids[node.name] = generated_id
                logging.debug(f"Type path: {node.name} -> {node.data_type} -> {generated_id}")

    # Write the schema to the output file
    if not dry_run and output:
        with open(output, "w", encoding="utf-8") as output_file:
            logging.info(f"Writing data to '{output}'")
            json.dump(node_ids, output_file, indent=2)
    else:
        print("-" * 80)
        print(json.dumps(node_ids, indent=2))


if __name__ == "__main__":
    main()
