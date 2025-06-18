import json
import logging
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
from rich.console import Console

from s2dm.exporters.utils import get_all_named_types, load_schema
from s2dm.idgen.idgen import fnv1_32_wrapper
from s2dm.idgen.models import IDGenerationSpec


class IDExporter:
    def __init__(
        self,
        schema: Path,
        units_file: Path,
        output: Path | None,
        strict_mode: bool,
        dry_run: bool,
    ):
        self.schema = schema
        self.units_file = units_file
        self.output = output
        self.strict_mode = strict_mode
        self.dry_run = dry_run

    @staticmethod
    def str_to_screaming_snake_case(text: str) -> str:
        """Converts a string to screaming snake case (i.e., CAPITAL LETTERS)"""
        text = re.sub(r"[^a-zA-Z0-9]", " ", text)
        words = text.split()
        return "_".join(word.upper() for word in words)

    def load_unit_lookup(self, units_file: Path) -> dict[str, str]:
        unit_lookup = {}
        with open(units_file) as f:
            units = yaml.safe_load(f)
        for unit in units:
            key = self.str_to_screaming_snake_case(units[unit]["unit"])
            value = unit
            unit_lookup[key] = value
        return unit_lookup

    def iter_all_id_specs(
        self, named_types: list[GraphQLNamedType], unit_lookup: dict[str, str]
    ) -> Generator[IDGenerationSpec, None, None]:
        # Only care about enums, objects and their fields
        for named_type in named_types:
            if named_type.name in ("Query", "Mutation"):
                continue

            if isinstance(named_type, GraphQLEnumType):
                logging.debug(f"Processing enum: {named_type.name}")
                id_spec = IDGenerationSpec.from_enum(
                    field=named_type,
                )
                yield id_spec

            elif isinstance(named_type, GraphQLObjectType):
                logging.debug(f"Processing object: {named_type.name}")
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

    def run(self) -> dict[str, str] | None:
        """Generate IDs for GraphQL schema fields and enums."""
        logging.info(f"Using units file '{self.units_file}', input is '{self.schema}', and output is '{self.output}'")

        graphql_schema = load_schema(self.schema)
        unit_lookup = self.load_unit_lookup(self.units_file)
        all_named_types = get_all_named_types(graphql_schema)

        node_ids = {}
        existing_ids = set()
        for id_spec in self.iter_all_id_specs(named_types=all_named_types, unit_lookup=unit_lookup):
            generated_id = fnv1_32_wrapper(id_spec, strict_mode=self.strict_mode)

            if generated_id in existing_ids:
                logging.warning(f"Duplicate ID found: {generated_id} for {id_spec.name}")
                sys.exit(1)

            existing_ids.add(generated_id)
            node_ids[id_spec.name] = generated_id

            logging.debug(f"Type path: {id_spec.name} -> {id_spec.data_type} -> {generated_id}")

        # Write the schema to the output file
        if not self.dry_run and self.output is not None:
            with open(self.output, "w", encoding="utf-8") as output_file:
                logging.info(f"Writing data to '{self.output}'")
                json.dump(node_ids, output_file, indent=2)

        return node_ids


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
    """CLI entrypoint: instantiate IDExporter and run."""
    exporter = IDExporter(
        schema=schema,
        units_file=units_file,
        output=output,
        strict_mode=strict_mode,
        dry_run=dry_run,
    )
    node_ids = exporter.run()

    console = Console()
    console.rule("[bold blue]Concept IDs")
    console.print(node_ids)


if __name__ == "__main__":
    main()
