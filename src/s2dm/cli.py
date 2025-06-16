import json
import logging
from pathlib import Path

import rich_click as click
from rich.traceback import install

from s2dm import __version__, log
from s2dm.exporters.shacl import translate_to_shacl
from s2dm.exporters.vspec import translate_to_vspec
from s2dm.exporters.graphql_inspector import GraphQLInspector


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
def export(ctx):
    """Export commands."""
    pass


@click.group()
@click.pass_context
def diff(ctx) -> None:
    """Diff commands for multiple input types."""
    pass


@click.group()
@click.pass_context
def validate(ctx) -> None:
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


# YAML
# ----------
@export.command
@schema_option
@output_option
def vspec(schema: Path, output: Path) -> None:
    """Generate VSPEC from a given GraphQL schema."""
    result = translate_to_vspec(schema)
    _ = output.write_text(result)


@validate.command(name="graphql")
@schema_option
@output_option(required=False)
@click.pass_context
def validate_graphql(ctx: click.Context, schema: Path, query: Path, output: Path | None) -> None:
    """ToDo"""
    schema_temp_path = create_tempfile_to_composed_schema(schema)
    inspector = GraphQLInspector(schema_temp_path)
    validation_result = inspector.validate(str(schema_temp_path))

    console = Console()
    if validation_result["returncode"] == 0:
        console.print(validation_result["stdout"])
    else:
        console.print(validation_result["stderr"])

    if output:
        processed = pretty_print_dict_json(validation_result)
        output.write_text(json.dumps(processed, indent=2, sort_keys=True, ensure_ascii=False))


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
    """ToDo"""
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


cli.add_command(export)
cli.add_command(diff)
cli.add_command(validate)

if __name__ == "__main__":
    cli()
