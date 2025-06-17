import logging
from pathlib import Path

import rich_click as click
from rich.traceback import install

from s2dm import __version__, log
from s2dm.exporters.shacl import translate_to_shacl
from s2dm.exporters.vspec import translate_to_vspec

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
def cli(log_level: str, log_file: Path | None) -> None:
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
def export() -> None:
    """Export commands."""
    pass


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


@export.command
@schema_option
@output_option
def vspec(schema: Path, output: Path) -> None:
    """Generate VSPEC from a given GraphQL schema."""
    result = translate_to_vspec(schema)
    _ = output.write_text(result)


cli.add_command(export)

if __name__ == "__main__":
    cli()
