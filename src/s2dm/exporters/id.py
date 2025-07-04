import json
import re
import sys
from collections.abc import Generator
from pathlib import Path

import click
import yaml
from graphql import (
    GraphQLEnumType,
    GraphQLNamedType,
    GraphQLObjectType,
)

from s2dm import log
from s2dm.exporters.utils import get_all_named_types, load_schema
from s2dm.idgen.idgen import fnv1_32_wrapper
from s2dm.idgen.models import IDGenerationSpec


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


def iter_all_id_specs(
    named_types: list[GraphQLNamedType], unit_lookup: dict[str, str]
) -> Generator[IDGenerationSpec, None, None]:
    # Only care about enums, objects and their fields
    for named_type in named_types:
        if named_type.name in ("Query", "Mutation"):
            continue

        if isinstance(named_type, GraphQLEnumType):
            log.debug(f"Processing enum: {named_type.name}")
            id_spec = IDGenerationSpec.from_enum(
                field=named_type,
            )
            yield id_spec

        elif isinstance(named_type, GraphQLObjectType):
            log.debug(f"Processing object: {named_type.name}")
            # Get the ID of all fields in the object
            for field_name, field in named_type.fields.items():
                if field_name.lower() == "id":
                    continue

                id_spec = IDGenerationSpec.from_field(
                    parent_name=f"{named_type.name}",
                    field_name=field_name,
                    field=field,
                    unit_lookup=unit_lookup,
                )

                # Only yield leaf fields
                if id_spec.is_leaf_field():
                    yield id_spec


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
def main(
    schema: Path,
    units_file: Path,
    output: Path | None,
    strict_mode: bool,
    dry_run: bool,
) -> None:
    """Generate IDs for GraphQL schema fields and enums.

    Args:
        schema: Path to the GraphQL schema file
        units_file: Path to the units YAML file
        output: Optional output file path
        strict_mode: Whether to use strict mode for ID generation
        dry_run: Whether to perform a dry run without writing files
    """
    log.info(f"Using units file '{units_file}', input is '{schema}', and output is '{output}'")

    # Pass the schema content to build_schema
    graphql_schema = load_schema(schema)

    unit_lookup = load_unit_lookup(units_file)

    all_named_types = get_all_named_types(graphql_schema)

    node_ids = {}
    existing_ids = set()
    for id_spec in iter_all_id_specs(named_types=all_named_types, unit_lookup=unit_lookup):
        generated_id = fnv1_32_wrapper(id_spec, strict_mode=strict_mode)

        if generated_id in existing_ids:
            log.warning(f"Duplicate ID found: {generated_id} for {id_spec.name}")
            sys.exit(1)

        existing_ids.add(generated_id)
        node_ids[id_spec.name] = generated_id

        log.debug(f"Type path: {id_spec.name} -> {id_spec.data_type} -> {generated_id}")

    # Write the schema to the output file
    if not dry_run and output is not None:
        with open(output, "w", encoding="utf-8") as output_file:
            log.info(f"Writing data to '{output}'")
            json.dump(node_ids, output_file, indent=2)
    else:
        print("-" * 80)
        print(json.dumps(node_ids, indent=2))


if __name__ == "__main__":
    main()
