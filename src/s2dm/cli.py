import json
import logging
import sys
from pathlib import Path
from typing import Any

import rich_click as click
from rich.console import Console
from rich.traceback import install

from s2dm import __version__, log
from s2dm.concept.services import create_concept_uri_model, iter_all_concepts
from s2dm.exporters.id import IDExporter
from s2dm.exporters.jsonschema import translate_to_jsonschema
from s2dm.exporters.shacl import translate_to_shacl
from s2dm.exporters.spec_history import SpecHistoryExporter
from s2dm.exporters.utils import (
    create_tempfile_to_composed_schema,
    get_all_named_types,
    get_all_object_types,
    load_schema,
    search_schema,
)
from s2dm.exporters.vspec import translate_to_vspec
from s2dm.tools.constraint_checker import ConstraintChecker
from s2dm.tools.graphql_inspector import GraphQLInspector

schema_option = click.option(
    "--schema",
    "-s",
    type=click.Path(exists=True),
    required=True,
    help="The GraphQL schema file",
)


output_option = click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    required=True,
    help="Output file",
)

optional_output_option = click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    required=False,
    help="Output file",
)


def pretty_print_dict_json(result: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively pretty-print a dict for JSON output:
    - Converts string values with newlines to lists of lines.
    - Processes nested dicts and lists.
    Returns a new dict suitable for pretty JSON output.
    """

    def multiline_str_representer(obj: Any) -> Any:
        if isinstance(obj, str) and "\n" in obj:
            return obj.splitlines()
        elif isinstance(obj, dict):
            return {k: multiline_str_representer(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [multiline_str_representer(i) for i in obj]
        return obj

    return {k: multiline_str_representer(v) for k, v in result.items()}


@click.group(context_settings={"auto_envvar_prefix": "s2dm"})
@click.option(
    "-l",
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    default="INFO",
    help="Log level",
    show_default=True,
)
@click.option(
    "--log-file",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="Log file",
)
@click.version_option(__version__)
@click.pass_context
def cli(ctx: click.Context, log_level: str, log_file: Path | None) -> None:
    if log_file:
        file_handler = logging.FileHandler(log_file, mode="w")
        file_handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(message)s"))
        log.addHandler(file_handler)

    log.setLevel(log_level)
    if log_level == "DEBUG":
        _ = install(show_locals=True)
    ctx.obj = Console()


@click.group()
def check() -> None:
    """Check commands for multiple input types."""
    pass


@click.group()
def diff() -> None:
    """Diff commands for multiple input types."""
    pass


@click.group()
def export() -> None:
    """Export commands."""
    pass


@click.group()
def registry() -> None:
    """Spec history generation/updating"""
    pass


@click.group()
def search() -> None:
    """Search commands e.g. search graphql for one specific type."""
    pass


@click.group()
def similar() -> None:
    """Find similar types of a graphql schema"""
    pass


@click.group()
def stats() -> None:
    """Stats commands."""
    pass


@click.group()
def validate() -> None:
    """Diff commands for multiple input types."""
    pass


# SHACL
# ----------
@export.command
@schema_option
@output_option
@click.option(
    "--serialization-format",
    "-f",
    type=str,
    default="ttl",
    help="RDF serialization format of the output file",
    show_default=True,
)
@click.option(
    "--shapes-namespace",
    "-sn",
    type=str,
    default="http://example.ns/shapes#",
    help="The namespace for SHACL shapes",
    show_default=True,
)
@click.option(
    "--shapes-namespace-prefix",
    "-snpref",
    type=str,
    default="shapes",
    help="The prefix for the SHACL shapes",
    show_default=True,
)
@click.option(
    "--model-namespace",
    "-mn",
    type=str,
    default="http://example.ns/model#",
    help="The namespace for the data model",
    show_default=True,
)
@click.option(
    "--model-namespace-prefix",
    "-mnpref",
    type=str,
    default="model",
    help="The prefix for the data model",
    show_default=True,
)
def shacl(
    schema: Path,
    output: Path,
    serialization_format: str,
    shapes_namespace: str,
    shapes_namespace_prefix: str,
    model_namespace: str,
    model_namespace_prefix: str,
) -> None:
    """Generate SHACL shapes from a given GraphQL schema."""
    result = translate_to_shacl(
        schema,
        shapes_namespace,
        shapes_namespace_prefix,
        model_namespace,
        model_namespace_prefix,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    _ = result.serialize(destination=output, format=serialization_format)


# Export -> yaml
# ----------
@export.command
@schema_option
@output_option
def vspec(schema: Path, output: Path) -> None:
    """Generate VSPEC from a given GraphQL schema."""
    result = translate_to_vspec(schema)
    output.parent.mkdir(parents=True, exist_ok=True)
    _ = output.write_text(result)


# Export -> json schema
# ----------
@export.command
@schema_option
@output_option
@click.option(
    "--root-type",
    "-r",
    type=str,
    help="Root type name for the JSON schema",
)
@click.option(
    "--strict",
    "-S",
    is_flag=True,
    default=False,
    help="Enforce strict field nullability translation from GraphQL to JSON Schema",
)
def jsonschema(schema: Path, output: Path, root_type: str | None, strict: bool) -> None:
    """Generate JSON Schema from a given GraphQL schema."""
    result = translate_to_jsonschema(schema, root_type, strict)
    _ = output.write_text(result)


# Check -> version bump
# ----------
@check.command
@schema_option
@click.option(
    "--previous",
    "-p",
    type=click.Path(exists=True),
    required=True,
    help="The GraphQL schema file to validate against",
)
@click.option(
    "--output-type",
    is_flag=True,
    default=False,
    help="Output the version bump type for pipeline usage",
)
@click.pass_obj
def version_bump(console: Console, schema: Path, previous: Path, output_type: bool) -> None:
    """Check if version bump needed. Uses GraphQL inspector's diff to search for (breaking) changes.

    Returns:
    - None: No changes detected
    - "patch": Non-breaking changes only (✔ symbols)
    - "minor": Dangerous changes detected (⚠ symbols)
    - "major": Breaking changes detected (✖ symbols)
    """
    # Note: GraphQL Inspector expects old schema first, then new schema
    # So we pass previous first, then schema (current)
    previous_schema_temp_path = create_tempfile_to_composed_schema(previous)
    inspector = GraphQLInspector(previous_schema_temp_path)

    schema_temp_path = create_tempfile_to_composed_schema(schema)
    diff_result = inspector.diff(schema_temp_path)

    # Determine version bump type based on output analysis
    version_bump_type = None

    if diff_result.returncode == 0:
        if "No changes detected" in diff_result.output:
            console.print("[green]No version bump needed")
            version_bump_type = None
        elif "No breaking changes detected" in diff_result.output:
            # Check for dangerous changes (⚠ symbols)
            if "⚠" in diff_result.output:
                console.print("[yellow]Minor version bump needed")
                version_bump_type = "minor"
            else:
                console.print("[green]Patch version bump needed")
                version_bump_type = "patch"
        else:
            console.print("[red]Unknown state, please check your input with 'diff' tool.")
    else:
        if "Detected" in diff_result.output and "breaking changes" in diff_result.output:
            console.print("[red]Detected breaking changes, major version bump needed")
            version_bump_type = "major"
        else:
            console.print("[red]Unknown error occurred during schema comparison")

    # Output the version bump type for pipeline usage
    if output_type:
        if version_bump_type:
            console.print(version_bump_type)
        else:
            console.print("none")

    # Exit with success code
    sys.exit(0)


@check.command(name="constraints")
@schema_option
@click.pass_obj
def check_constraints(console: Console, schema: Path) -> None:
    """
    Enforce intended use of custom directives and naming conventions.
    Checks:
    - instanceTag field and object rules
    - @range and @cardinality min/max
    - Naming conventions (TBD)
    """
    gql_schema = load_schema(schema)
    objects = get_all_object_types(gql_schema)

    constraint_checker = ConstraintChecker(gql_schema)
    errors = constraint_checker.run(objects)

    if errors:
        console.rule("[bold red]Constraint Violations")
        for err in errors:
            console.print(f"[red]- {err}")
        raise sys.exit(1)
    else:
        console.print("[green]All constraints passed!")


# validate -> graphql
# ----------
@validate.command(name="graphql")
@schema_option
@output_option
@click.pass_obj
def validate_graphql(console: Console, schema: Path, output: Path) -> None:
    """Validates the given GraphQL schema and returns the whole introspection file if valid graphql schema provided."""
    schema_temp_path = create_tempfile_to_composed_schema(schema)
    inspector = GraphQLInspector(schema_temp_path)
    validation_result = inspector.introspect(output)

    console.print(validation_result.output)
    sys.exit(validation_result.returncode)


# diff -> graphql
# ----------
@diff.command(name="graphql")
@schema_option
@optional_output_option
@click.option(
    "--val-schema",
    "-v",
    type=click.Path(exists=True),
    required=True,
    help="The GraphQL schema file to validate against",
)
@click.pass_obj
def diff_graphql(console: Console, schema: Path, val_schema: Path, output: Path | None) -> None:
    """Diff for two GraphQL schemas."""
    log.info(f"Comparing schemas: {schema} and {val_schema} and writing output to {output}")

    input_temp_path = create_tempfile_to_composed_schema(schema)
    inspector = GraphQLInspector(input_temp_path)

    val_temp_path = create_tempfile_to_composed_schema(val_schema)
    diff_result = inspector.diff(val_temp_path)

    if output is not None:
        log.info(f"writing file to {output=}")
        output.parent.mkdir(parents=True, exist_ok=True)
        processed = pretty_print_dict_json(diff_result.as_dict())
        output.write_text(json.dumps(processed, indent=2, sort_keys=True, ensure_ascii=False))

    console.print(diff_result.output)
    sys.exit(diff_result.returncode)


# registry -> concept-uri
@registry.command(name="concept-uri")
@schema_option
@optional_output_option
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
@click.pass_obj
def export_concept_uri(console: Console, schema: Path, output: Path | None, namespace: str, prefix: str) -> None:
    """Generate concept URIs for a GraphQL schema and output as JSON-LD."""
    graphql_schema = load_schema(schema)
    concepts = iter_all_concepts(get_all_named_types(graphql_schema))
    concept_uri_model = create_concept_uri_model(concepts, namespace, prefix)
    data = concept_uri_model.to_json_ld()

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as output_file:
            log.info(f"Writing data to '{output}'")
            json.dump(data, output_file, indent=2)
        console.print(f"[green]Concept URIs written to {output}")

    console.rule("[bold blue]Concept URIs (JSON-LD)")
    console.print_json(json.dumps(data, indent=2))


# registry -> id
@registry.command(name="id")
@schema_option
@click.option(
    "--units",
    "-u",
    type=click.Path(exists=True),
    required=True,
    help="Path to your units.yaml",
)
@optional_output_option
@click.option("--strict-mode/--no-strict-mode", default=False)
@click.pass_obj
def export_id(console: Console, schema: Path, units: Path, output: Path | None, strict_mode: bool) -> None:
    """Generate concept IDs for GraphQL schema fields and enums."""
    exporter = IDExporter(
        schema=schema,
        units_file=units,
        output=output,
        strict_mode=strict_mode,
        dry_run=output is None,
    )
    node_ids = exporter.run()

    console.rule("[bold blue]Concept IDs")
    console.print(node_ids)


# registry -> init
@registry.command(name="init")
@schema_option
@click.option(
    "--units",
    "-u",
    type=click.Path(exists=True),
    required=True,
    help="Path to your units.yaml",
)
@output_option
@click.option(
    "--concept-namespace",
    default="https://example.org/vss#",
    help="The namespace for the concept URIs",
)
@click.option(
    "--concept-prefix",
    default="ns",
    help="The prefix to use for the concept URIs",
)
@click.pass_obj
def registry_init(
    console: Console,
    schema: Path,
    units: Path,
    output: Path,
    concept_namespace: str,
    concept_prefix: str,
) -> None:
    """Initialize your spec history with the given schema."""
    output.parent.mkdir(parents=True, exist_ok=True)

    # Generate concept IDs
    id_exporter = IDExporter(schema, units, None, strict_mode=False, dry_run=False)
    concept_ids = id_exporter.run()

    # Generate concept URIs
    graphql_schema = load_schema(schema)
    all_named_types = get_all_named_types(graphql_schema)
    concepts = iter_all_concepts(all_named_types)
    concept_uri_model = create_concept_uri_model(concepts, concept_namespace, concept_prefix)
    concept_uris = concept_uri_model.to_json_ld()

    # Determine history_dir based on output path if output is given, else default to "history"
    output_real = output.resolve()
    history_dir = output_real.parent / "history"

    spec_history_exporter = SpecHistoryExporter(
        schema=schema,
        output=output,
        history_dir=history_dir,
    )
    spec_history_result = spec_history_exporter.init_spec_history_model(concept_uris, concept_ids, concept_uri_model)

    console.rule("[bold blue]Concept IDs")
    console.print(concept_ids)
    console.rule("[bold blue]Concept URIs")
    console.print(concept_uris)
    console.rule("[bold blue]Spec history (updated)")
    console.print(spec_history_result)


# registry -> update
@registry.command(name="update")
@schema_option
@click.option(
    "--units",
    "-u",
    type=click.Path(exists=True),
    required=True,
    help="Path to your units.yaml",
)
@click.option(
    "--spec-history",
    "-sh",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to the previously generated spec history file",
)
@output_option
@click.option(
    "--concept-namespace",
    default="https://example.org/vss#",
    help="The namespace for the concept URIs",
)
@click.option(
    "--concept-prefix",
    default="ns",
    help="The prefix to use for the concept URIs",
)
@click.pass_obj
def registry_update(
    console: Console,
    schema: Path,
    units: Path,
    spec_history: Path,
    output: Path,
    concept_namespace: str,
    concept_prefix: str,
) -> None:
    """Update a given spec history file with your new schema."""
    output.parent.mkdir(parents=True, exist_ok=True)

    # Generate concept IDs
    id_exporter = IDExporter(schema, units, None, strict_mode=False, dry_run=False)
    concept_ids = id_exporter.run()

    # Generate concept URIs
    graphql_schema = load_schema(schema)
    all_named_types = get_all_named_types(graphql_schema)
    concepts = iter_all_concepts(all_named_types)
    concept_uri_model = create_concept_uri_model(concepts, concept_namespace, concept_prefix)
    concept_uris = concept_uri_model.to_json_ld()

    # Determine history_dir based on output path if output is given, else default to "history"
    output_real = output.resolve()
    history_dir = output_real.parent / "history"

    spec_history_exporter = SpecHistoryExporter(
        schema=schema,
        output=output,
        history_dir=history_dir,
    )
    spec_history_result = spec_history_exporter.update_spec_history_model(
        concept_uris=concept_uris,
        concept_ids=concept_ids,
        concept_uri_model=concept_uri_model,
        spec_history_path=spec_history,
    )

    console.rule("[bold blue]Concept IDs")
    console.print(concept_ids)
    console.rule("[bold blue]Concept URIs")
    console.print(concept_uris)
    console.rule("[bold blue]Spec history (updated)")
    console.print(spec_history_result)


# search -> graphql
@search.command(name="graphql")
@schema_option
@click.option("--type", "-t", required=True, help="Type or field you want to search the graphql schema for.")
@click.option("--case-insensitive", "-i", is_flag=True, default=False, help="Perform a case-insensitive search.")
@click.option("--exact", is_flag=True, default=False, help="Perform an exact match search.")
@click.pass_obj
def search_graphql(console: Console, schema: Path, type: str, case_insensitive: bool, exact: bool) -> None:
    """Search for a type or field in the GraphQL schema. If type was found returns type including all fields,
    if fields was found returns only field in parent type"""

    gql_schema = load_schema(schema)

    type_results = search_schema(
        gql_schema,
        type_name=type,
        field_name=None,
        partial=not exact,
        case_insensitive=case_insensitive,
    )
    field_results = search_schema(
        gql_schema,
        type_name=None,
        field_name=type,
        partial=not exact,
        case_insensitive=case_insensitive,
    )
    console.rule(f"[bold blue] Search results for '{type}'")
    if not type_results and not field_results:
        console.print(f"[yellow]No matches found for '{type}'.")
    else:
        for tname, fields in type_results.items():
            console.print(f"[green]{tname}[/green]: {fields}")
        for tname, fields in field_results.items():
            if fields:
                console.print(f"[green]{tname}[/green]: {fields}")


# similar -> graphql
@similar.command(name="graphql")
@schema_option
@click.option(
    "--keyword", "-k", required=True, help="Name of the keyword or type you want to search the graphql schema for."
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    required=False,
    help="Output file, only .json allowed here",
)
@click.pass_obj
def similar_graphql(console: Console, schema: Path, keyword: str, output: Path | None) -> None:
    """Search a type (and only types) in the provided grahql schema. Provide '-k all' for all similarities across the
    whole schema (in %)."""
    schema_temp_path = create_tempfile_to_composed_schema(schema)
    inspector = GraphQLInspector(schema_temp_path)
    if output:
        log.info(f"Search will write file to {output}")

    # if keyword == "all" search all elements otherwise only keyword
    search_result = inspector.similar(output) if keyword == "all" else inspector.similar_keyword(keyword, output)

    console.rule(f"[bold blue] Search result for '{keyword}'")
    console.print(search_result.output)
    sys.exit(search_result.returncode)


# stats -> graphql
# ----------
@stats.command(name="graphql")
@schema_option
@click.pass_obj
def stats_graphql(console: Console, schema: Path) -> None:
    """Get stats of schema."""
    gql_schema = load_schema(schema)

    # Count types by kind
    type_map = gql_schema.type_map
    type_counts: dict[str, Any] = {
        "object": 0,
        "enum": 0,
        "scalar": 0,
        "interface": 0,
        "union": 0,
        "input_object": 0,
        "custom_types": {},
    }
    for t in type_map.values():
        name = getattr(t, "name", "")
        if name.startswith("__"):
            continue
        kind = type(t).__name__
        if kind == "GraphQLObjectType":
            type_counts["object"] += 1
        elif kind == "GraphQLEnumType":
            type_counts["enum"] += 1
        elif kind == "GraphQLScalarType":
            type_counts["scalar"] += 1
        elif kind == "GraphQLInterfaceType":
            type_counts["interface"] += 1
        elif kind == "GraphQLUnionType":
            type_counts["union"] += 1
        elif kind == "GraphQLInputObjectType":
            type_counts["input_object"] += 1
        # Detect custom types e.g. (not built-in scalars)
        if kind == "GraphQLScalarType" and name not in ("Int", "Float", "String", "Boolean", "ID"):
            type_counts["custom_types"][name] = type_counts["custom_types"].get(name, 0) + 1

    console.rule("[bold blue]GraphQL Schema Type Counts")
    console.print(type_counts)


cli.add_command(check)
cli.add_command(diff)


cli.add_command(export)
cli.add_command(registry)
cli.add_command(similar)
cli.add_command(search)
cli.add_command(stats)
cli.add_command(validate)

if __name__ == "__main__":
    cli()
