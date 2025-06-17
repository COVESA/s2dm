import json
import logging
from pathlib import Path

import rich_click as click
from rich.console import Console
from rich.traceback import install

from s2dm import __version__, log
from s2dm.exporters.graphql_inspector import GraphQLInspector
from s2dm.exporters.shacl import translate_to_shacl
from s2dm.exporters.utils import create_tempfile_to_composed_schema, load_schema
from s2dm.exporters.vspec import translate_to_vspec


# Define the common options
def schema_option(f):
    return click.option("--schema", "-s", type=click.Path(exists=True), required=True, help="The GraphQL schema file")(
        f
    )


def output_option(f=None, *, required=True):
    def decorator(func):
        return click.option(
            "--output",
            "-o",
            type=click.Path(dir_okay=False, writable=True, path_type=Path),
            required=required,
            help="Output file",
        )(func)

    if f is None:
        return decorator
    return decorator(f)


# Pretty print JSON with sorted keys and indentation, preserving newlines in string values
# Convert dict values with newlines to lists of lines for better readability
def pretty_print_dict_json(result: dict):
    def multiline_str_representer(obj):
        if isinstance(obj, str) and "\n" in obj:
            return obj.splitlines()
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
def cli(ctx, log_level: str, log_file: Path | None) -> None:
    # Only add handlers if there are none
    if not log.handlers:
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

    ctx.ensure_object(dict)
    ctx.obj["log_level"] = log_level
    ctx.obj["log_file"] = log_file


@click.group()
@click.pass_context
def check(ctx: click.Context) -> None:
    """Check commands for multiple input types."""
    pass


@click.group()
@click.pass_context
def diff(ctx: click.Context) -> None:
    """Diff commands for multiple input types."""
    pass


@click.group()
@click.pass_context
def export(ctx: click.Context):
    """Export commands."""
    pass


@click.group()
@click.pass_context
def stats(ctx: click.Context):
    """Stats commands."""
    pass


@click.group()
@click.pass_context
def validate(ctx: click.Context) -> None:
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
    _ = result.serialize(destination=output, format=serialization_format)


# Export -> yaml
# ----------
@export.command
@schema_option
@output_option
def vspec(schema: Path, output: Path) -> None:
    """Generate VSPEC from a given GraphQL schema."""
    result = translate_to_vspec(schema)
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
@click.pass_context
def version_bump(ctx: click.Context, schema: Path, previous_schema: Path) -> None:
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
@output_option(required=False)
@click.pass_context
def validate_graphql(ctx: click.Context, schema: Path, output: Path | None) -> None:
    """ToDo"""
    schema_temp_path = create_tempfile_to_composed_schema(schema)
    inspector = GraphQLInspector(schema_temp_path)
    validation_result = inspector.introspect()

    console = Console()
    if validation_result["returncode"] == 0:
        console.print(validation_result["stdout"])
    else:
        console.print(validation_result["stderr"])

    if output:
        processed = pretty_print_dict_json(validation_result)
        output.write_text(json.dumps(processed, indent=2, sort_keys=True, ensure_ascii=False))


# Diff -> graphql
# ----------
@diff.command(name="graphql")
@schema_option
@output_option(required=False)
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

    console = Console()
    if diff_result["returncode"] == 0:
        console.print(diff_result["stdout"])
    else:
        console.print(diff_result["stdout"])
        console.print(diff_result["stderr"])

    if output:
        processed = pretty_print_dict_json(diff_result)
        output.write_text(json.dumps(processed, indent=2, sort_keys=True, ensure_ascii=False))


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
    type_counts = {
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

    logging.info(f"Type counts: {type_counts}")


cli.add_command(check)
cli.add_command(diff)
cli.add_command(export)
cli.add_command(stats)
cli.add_command(validate)

if __name__ == "__main__":
    cli()
