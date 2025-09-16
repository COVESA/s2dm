import json
import sys
from collections.abc import Generator
from pathlib import Path
from typing import Any

from graphql import (
    GraphQLEnumType,
    GraphQLNamedType,
    GraphQLObjectType,
)

from s2dm import log
from s2dm.exporters.utils.extraction import get_all_named_types
from s2dm.exporters.utils.graphql_type import is_id_type, is_introspection_or_root_type
from s2dm.exporters.utils.schema_loader import load_schema
from s2dm.idgen.idgen import fnv1_32_wrapper
from s2dm.idgen.models import IDGenerationSpec


class IDExporter:
    def __init__(
        self,
        schema: Path,
        output: Path | None,
        strict_mode: bool,
        dry_run: bool,
    ):
        self.schema = schema
        self.output = output
        self.strict_mode = strict_mode
        self.dry_run = dry_run

    def iter_all_id_specs(self, named_types: list[GraphQLNamedType]) -> Generator[IDGenerationSpec, None, None]:
        # Only care about enums, objects and their fields
        for named_type in named_types:
            if is_introspection_or_root_type(named_type.name):
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
                    if is_id_type(field_name):
                        continue

                    id_spec = IDGenerationSpec.from_field(
                        parent_name=f"{named_type.name}",
                        field_name=field_name,
                        field=field,
                    )

                    # Only yield leaf fields
                    if id_spec.is_leaf_field():
                        yield id_spec

    def run(self) -> dict[str, Any]:
        """Generate IDs for GraphQL schema fields and enums."""
        log.info(f"Generating IDs from schema '{self.schema}', output is '{self.output}'")

        graphql_schema = load_schema(self.schema)
        all_named_types = get_all_named_types(graphql_schema)

        node_ids = {}
        existing_ids = set()
        for id_spec in self.iter_all_id_specs(named_types=all_named_types):
            generated_id = fnv1_32_wrapper(id_spec, strict_mode=self.strict_mode)

            if generated_id in existing_ids:
                log.warning(f"Duplicate ID found: {generated_id} for {id_spec.name}")
                sys.exit(1)

            existing_ids.add(generated_id)
            node_ids[id_spec.name] = generated_id

            log.debug(f"Type path: {id_spec.name} -> {id_spec.data_type} -> {generated_id}")

        # Write the schema to the output file
        if not self.dry_run and self.output is not None:
            with open(self.output, "w", encoding="utf-8") as output_file:
                log.info(f"Writing data to '{self.output}'")
                json.dump(node_ids, output_file, indent=2)

        return node_ids
