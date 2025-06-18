import json
import logging
import tempfile
from pathlib import Path
from typing import Any

import rich_click as click
from rich.console import Console
from rich.traceback import install

from s2dm import __version__, log
from s2dm.concept.services import create_concept_uri_model, iter_all_concepts
from s2dm.exporters.id import IDExporter
from s2dm.exporters.shacl import translate_to_shacl
from s2dm.exporters.spec_history import SpecHistoryExporter
from s2dm.exporters.utils import create_tempfile_to_composed_schema, get_all_named_types, load_schema
from s2dm.exporters.vspec import translate_to_vspec
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
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable verbose console output",
)
@click.version_option(__version__)
@click.pass_context
def cli(ctx: click.Context, log_level: str, log_file: Path | None, verbose: bool) -> None:
    ctx.ensure_object(dict)
    ctx.obj["VERBOSE"] = verbose
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(message)s"))
    log.addHandler(console_handler)
    if log_file:
        file_handler = logging.FileHandler(log_file, mode="w")
        file_handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(message)s"))
        log.addHandler(file_handler)
    log.setLevel(log_level)
    logging.getLogger().setLevel(log_level)
    if log_level == "DEBUG":
        _ = install(show_locals=True)


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
    """Registry commands e.g for spec history generation and updates"""
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


# Check -> version bump
# ----------
@check.command
@schema_option
@click.option(
    "--previous-schema",
    "-ps",
    type=click.Path(exists=True),
    required=True,
    help="The GraphQL schema file to validate against",
)
def version_bump(schema: Path, previous_schema: Path) -> None:
    """Check if version bump needed. Uses GraphQL inspector's diff to search for (breaking) changes.

    No changes: No bump needed
    Changes but no breaking changes: Patch or minor version bump needed
    Breaking changes: Major version bump needed
    """
    schema_temp_path = create_tempfile_to_composed_schema(schema)
    inspector = GraphQLInspector(schema_temp_path)

    previous_schema_temp_path = create_tempfile_to_composed_schema(previous_schema)
    diff_result = inspector.diff(previous_schema_temp_path)

    if diff_result["returncode"] == 0:
        logging.debug(f"diff_result in check = {diff_result}")
        if "No changes detected" in diff_result["stdout"]:
            logging.info("No version bump needed")
        elif "No breaking changes detected" in diff_result["stdout"]:
            logging.info("Minor or patch version bump needed!")
        else:
            logging.error("Unknown state, please check your input with 'diff' tool.")
    else:
        logging.debug(f"diff_result in check = {diff_result}")
        if "Detected" in diff_result["stdout"] and "breaking changes" in diff_result["stdout"]:
            logging.info("Detected breaking changes, major version bump needed. Please run diff to get more details")


# Validate -> graphql
# ----------
@validate.command(name="graphql")
@schema_option
@optional_output_option
@click.pass_context
def validate_graphql(ctx: click.Context, schema: Path, output: Path | None) -> None:
    """ToDo"""
    schema_temp_path = create_tempfile_to_composed_schema(schema)
    inspector = GraphQLInspector(schema_temp_path)
    validation_result = inspector.introspect()

    if ctx.obj.get("VERBOSE"):
        console = Console()
        if validation_result["returncode"] == 0:
            console.print(validation_result["stdout"])
        else:
            console.print(validation_result["stderr"])

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        processed = pretty_print_dict_json(validation_result)
        output.write_text(json.dumps(processed, indent=2, sort_keys=True, ensure_ascii=False))


# Diff -> graphql
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
@click.pass_context
def diff_graphql(ctx: click.Context, schema: Path, val_schema: Path, output: Path | None) -> None:
    """Diff for two GraphQL schemas."""
    logging.info(f"Comparing schemas: {schema} and {val_schema}")

    input_temp_path = create_tempfile_to_composed_schema(schema)
    inspector = GraphQLInspector(input_temp_path)

    val_temp_path = create_tempfile_to_composed_schema(val_schema)
    diff_result = inspector.diff(val_temp_path)

    if ctx.obj.get("VERBOSE"):
        console = Console()
        if diff_result["returncode"] == 0:
            console.print(diff_result["stdout"])
        else:
            console.print(diff_result["stdout"])
            console.print(diff_result["stderr"])

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        processed = pretty_print_dict_json(diff_result)
        output.write_text(json.dumps(processed, indent=2, sort_keys=True, ensure_ascii=False))


# Registry -> Init
@registry.command(name="init")
@schema_option
@click.option(
    "--units",
    "-u",
    type=click.Path(exists=True),
    required=True,
    help="Path to your units.yaml",
)
@optional_output_option
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
@click.pass_context
def registry_init(
    ctx: click.Context,
    schema: Path,
    units: Path,
    output: Path | None,
    concept_namespace: str,
    concept_prefix: str,
) -> None:
    if output:
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

    # Generate initial spec history
    # Write concept_uris and concept_ids to temp files if needed, or pass as objects if supported
    with (
        tempfile.NamedTemporaryFile("w+", suffix=".json", delete=True) as concept_uri_file,
        tempfile.NamedTemporaryFile("w+", suffix=".json", delete=True) as concept_ids_file,
    ):
        json.dump(concept_uris, concept_uri_file)
        concept_uri_file.flush()
        json.dump(concept_ids, concept_ids_file)
        concept_ids_file.flush()

        # Determine history_dir based on output path if output is given, else default to "history"
        if output:
            output_real = output.resolve()
            history_dir = output_real.parent / "history"
        else:
            history_dir = Path("history")

        spec_history_exporter = SpecHistoryExporter(
            concept_uri=Path(concept_uri_file.name),
            ids=Path(concept_ids_file.name),
            schema=schema,
            init=True,
            spec_history=None,
            output=output,
            history_dir=history_dir,
        )
        spec_history = spec_history_exporter.run()

    if ctx.obj.get("VERBOSE"):
        console = Console()
        console.rule("[bold blue]Concept IDs")
        console.print(concept_ids)
        console.rule("[bold blue]Concept URIs")
        console.print(concept_uris)
        console.rule("[bold blue]Spec history")
        console.print(spec_history)


# Registry -> Update
@registry.command(name="update")
@schema_option
def registry_update(schema: Path) -> None:
    pass


# Stats -> graphQL
# ----------
@stats.command(name="graphql")
@schema_option
@click.pass_context
def stats_graphql(ctx: click.Context, schema: Path) -> None:
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

    if ctx.obj.get("VERBOSE"):
        console = Console()
        console.rule("[bold blue]GraphQL Schema Type Counts")
        console.print(type_counts)


cli.add_command(check)
cli.add_command(diff)
cli.add_command(export)
cli.add_command(registry)
cli.add_command(stats)
cli.add_command(validate)

if __name__ == "__main__":
    cli()
