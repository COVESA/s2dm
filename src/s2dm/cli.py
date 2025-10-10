import json
import logging
import sys
from pathlib import Path
from typing import Any

import rich_click as click
import yaml
from rich.console import Console
from rich.traceback import install

from s2dm import __version__, log
from s2dm.concept.services import create_concept_uri_model, iter_all_concepts
from s2dm.exporters.id import IDExporter
from s2dm.exporters.jsonschema import translate_to_jsonschema
from s2dm.exporters.shacl import translate_to_shacl
from s2dm.exporters.spec_history import SpecHistoryExporter
from s2dm.exporters.utils.extraction import get_all_named_types, get_all_object_types
from s2dm.exporters.utils.graphql_type import is_builtin_scalar_type, is_introspection_type
from s2dm.exporters.utils.schema import search_schema
from s2dm.exporters.utils.schema_loader import (
    create_tempfile_to_composed_schema,
    load_schema,
    load_schema_as_str,
    load_schema_as_str_filtered,
    resolve_graphql_files,
)
from s2dm.exporters.vspec import translate_to_vspec
from s2dm.tools.constraint_checker import ConstraintChecker
from s2dm.tools.graphql_inspector import GraphQLInspector
from s2dm.tools.skos_search import NO_LIMIT_KEYWORDS, SearchResult, SKOSSearchService
from s2dm.tools.validators import validate_language_tag
from s2dm.units.sync import UNITS_META_FILENAME, UNITS_META_VERSION_KEY, get_latest_qudt_version, sync_qudt_units

S2DM_HOME = Path.home() / ".s2dm"
DEFAULT_QUDT_UNITS_DIR = S2DM_HOME / "units" / "qudt"


class PathResolverOption(click.Option):
    def process_value(self, ctx: click.Context, value: Any) -> list[Path] | None:
        value = super().process_value(ctx, value)
        if value:
            return resolve_graphql_files(list(value))
        return None


schema_option = click.option(
    "--schema",
    "-s",
    "schemas",
    type=click.Path(exists=True, path_type=Path),
    cls=PathResolverOption,
    required=True,
    multiple=True,
    help="The GraphQL schema file or directory containing schema files. Can be specified multiple times.",
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

qudt_units_dir_option = click.option(
    "--qudt-units-dir",
    type=click.Path(path_type=Path, file_okay=False),
    required=False,
    help="Directory containing generated QUDT unit enums",
    default=DEFAULT_QUDT_UNITS_DIR,
    show_default=True,
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


def validate_naming_config(config: dict[str, Any]) -> None:
    VALID_CASES = {
        "camelCase",
        "PascalCase",
        "snake_case",
        "kebab-case",
        "MACROCASE",
        "COBOL-CASE",
        "flatcase",
        "TitleCase",
    }

    VALID_ELEMENT_TYPES = {"type", "field", "argument", "enumValue", "instanceTag"}
    VALID_CONTEXTS = {
        "type": {"object", "interface", "input", "scalar", "union", "enum"},
        "field": {"object", "interface", "input"},
        "argument": {"field"},
    }

    valid_cases = ", ".join(sorted(VALID_CASES))

    for element_type, value in config.items():
        if element_type not in VALID_ELEMENT_TYPES:
            raise click.ClickException(
                f"Invalid element type '{element_type}'. Valid types: {', '.join(sorted(VALID_ELEMENT_TYPES))}"
            )

        if element_type in ("enumValue", "instanceTag"):
            if isinstance(value, dict):
                raise click.ClickException(f"Element type '{element_type}' cannot have contexts")
            if not isinstance(value, str) or value not in VALID_CASES:
                raise click.ClickException(
                    f"Invalid case type for '{element_type}': '{value}'. Valid cases: {valid_cases}"
                )
        elif isinstance(value, str):
            if value not in VALID_CASES:
                raise click.ClickException(
                    f"Invalid case type for '{element_type}': '{value}'. Valid cases: {valid_cases}"
                )
        elif isinstance(value, dict):
            if element_type not in VALID_CONTEXTS:
                raise click.ClickException(f"Element type '{element_type}' cannot have contexts")

            for context, case_type in value.items():
                if context not in VALID_CONTEXTS[element_type]:
                    valid_contexts = ", ".join(sorted(VALID_CONTEXTS[element_type]))
                    raise click.ClickException(
                        f"Invalid context '{context}' for '{element_type}'. Valid contexts: {valid_contexts}"
                    )

                if not isinstance(case_type, str) or case_type not in VALID_CASES:
                    raise click.ClickException(
                        f"Invalid case type for '{element_type}.{context}': '{case_type}'. Valid cases: {valid_cases}"
                    )
        else:
            raise click.ClickException(
                f"Invalid value type for '{element_type}'. Expected string or dict, got {type(value).__name__}"
            )

    if "enumValue" in config and "instanceTag" not in config:
        raise click.ClickException("If 'enumValue' is present, 'instanceTag' must also be present")


def load_naming_config(config_path: Path | None) -> dict[str, Any] | None:
    if config_path is None:
        log.info("No naming config provided")
        return None

    try:
        config_file_handle = config_path.open("r", encoding="utf-8")
    except OSError as e:
        raise click.ClickException(f"Failed to open naming config file {config_path}: {e}") from e

    with config_file_handle:
        log.info(f"Loaded naming config: {config_path}")

        try:
            result = yaml.safe_load(config_file_handle)
        except yaml.YAMLError as e:
            raise click.ClickException(f"Failed to load naming config from {config_path}: {e}") from e

        config = result if isinstance(result, dict) else {}
        if config:
            validate_naming_config(config)
        return config


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
@click.option(
    "--naming-config",
    "-n",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="YAML file containing naming configuration",
)
@click.pass_context
def export(ctx: click.Context, naming_config: Path | None) -> None:
    """Export commands."""
    ctx.ensure_object(dict)
    ctx.obj["naming_config"] = load_naming_config(naming_config)


@click.group()
def generate() -> None:
    """Generate commands."""
    pass


@click.group()
def registry() -> None:
    """Spec history generation/updating"""
    pass


@click.group()
def search() -> None:
    """Search commands e.g. search graphql for one specific type."""
    pass


# units
# ----------
@click.group()
def units() -> None:
    """QUDT-based unit utilities."""
    pass


@units.command(name="sync")
@click.option(
    "--version",
    "version",
    type=str,
    required=False,
    help=(
        "QUDT version tag (e.g., 3.1.4). Defaults to the latest tag, falls back to 'main' when tags are unavailable."
    ),
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path, file_okay=False),
    required=False,
    help="Directory where generated QUDT unit enums will be written",
    default=DEFAULT_QUDT_UNITS_DIR,
    show_default=True,
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be generated without actually writing files",
)
@click.pass_obj
def units_sync(console: Console, version: str | None, output_dir: Path, dry_run: bool) -> None:
    """Fetch QUDT quantity kinds and generate GraphQL enums under the output directory."""

    try:
        version_to_use = version or get_latest_qudt_version()
    except Exception as e:  # pragma: no cover - generic guard for CLI UX
        console.print(f"[red]✗[/red] Version check failed: {e}")
        sys.exit(1)

    try:
        written = sync_qudt_units(output_dir, version_to_use, dry_run=dry_run)
        if dry_run:
            console.print(f"[blue]ℹ[/blue] Would generate {len(written)} enum files under {output_dir}")
            console.print(f"Version: {version_to_use}")
            console.print("[dim]Use without --dry-run to actually write files[/dim]")
        else:
            console.print(f"[green]✓[/green] Generated {len(written)} enum files under {output_dir}")
            console.print(f"Version: {version_to_use}")
    except Exception as e:  # pragma: no cover - generic guard for CLI UX
        console.print(f"[red]✗[/red] Units sync failed: {e}")
        sys.exit(1)


@units.command(name="check-version")
@qudt_units_dir_option
@click.pass_obj
def units_check_version(console: Console, qudt_units_dir: Path) -> None:
    """Compare local synced QUDT version with the latest remote version and print a message."""

    meta_path = qudt_units_dir / UNITS_META_FILENAME
    if not meta_path.exists():
        console.print("[yellow]![/yellow] No metadata.json found. Run 's2dm units sync' first.")
        sys.exit(1)

    try:
        local_version = json.loads(meta_path.read_text(encoding="utf-8")).get(UNITS_META_VERSION_KEY, "main")
    except json.JSONDecodeError as e:
        console.print(f"[red]✗[/red] Invalid metadata.json: {e}")
        sys.exit(1)

    try:
        latest = get_latest_qudt_version()
    except Exception as e:  # pragma: no cover - generic guard for CLI UX
        console.print(f"[red]✗[/red] Version check failed: {e}")
        sys.exit(1)

    if latest == local_version:
        console.print("[green]✓[/green] Units are up to date.")
    else:
        console.print(f"[yellow]![/yellow] A newer release is available. Local: {local_version}, Latest: {latest}")


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


@click.command()
@schema_option
@click.option(
    "--root-type",
    "-r",
    type=str,
    help="Root type name for filtering the schema",
)
@output_option
@click.pass_obj
def compose(console: Console, schemas: list[Path], root_type: str | None, output: Path) -> None:
    """Compose GraphQL schema files into a single output file."""
    try:
        if root_type:
            composed_schema_str = load_schema_as_str_filtered(schemas, root_type, add_references=True)
        else:
            composed_schema_str = load_schema_as_str(schemas, add_references=True)

        output.write_text(composed_schema_str)

        if root_type:
            console.print(f"[green]✓[/green] Successfully composed schema with root type '{root_type}' to {output}")
        else:
            console.print(f"[green]✓[/green] Successfully composed schema to {output}")

    except OSError as e:
        console.print(f"[red]✗[/red] File I/O error: {e}")
        sys.exit(1)
    except ValueError as e:
        console.print(f"[red]✗[/red] Invalid schema: {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Unexpected error: {e}")
        sys.exit(1)


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
@click.pass_context
def shacl(
    ctx: click.Context,
    schemas: list[Path],
    output: Path,
    serialization_format: str,
    shapes_namespace: str,
    shapes_namespace_prefix: str,
    model_namespace: str,
    model_namespace_prefix: str,
) -> None:
    """Generate SHACL shapes from a given GraphQL schema."""
    naming_config = ctx.obj.get("naming_config")
    result = translate_to_shacl(
        schemas,
        shapes_namespace,
        shapes_namespace_prefix,
        model_namespace,
        model_namespace_prefix,
        naming_config,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    _ = result.serialize(destination=output, format=serialization_format)


# Export -> yaml
# ----------
@export.command
@schema_option
@output_option
@click.pass_context
def vspec(ctx: click.Context, schemas: list[Path], output: Path) -> None:
    """Generate VSPEC from a given GraphQL schema."""
    naming_config = ctx.obj.get("naming_config")
    result = translate_to_vspec(schemas, naming_config)
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
@click.option(
    "--expanded-instances",
    "-e",
    is_flag=True,
    default=False,
    help="Expand instance tags into nested structure instead of arrays",
)
@click.pass_context
def jsonschema(
    ctx: click.Context, schemas: list[Path], output: Path, root_type: str | None, strict: bool, expanded_instances: bool
) -> None:
    """Generate JSON Schema from a given GraphQL schema."""
    naming_config = ctx.obj.get("naming_config")
    result = translate_to_jsonschema(schemas, root_type, strict, expanded_instances, naming_config)
    _ = output.write_text(result)


# Export -> skos
# ----------
@generate.command
@schema_option
@output_option
@click.option(
    "--namespace",
    default="https://example.org/vss#",
    help="The namespace for the concept URIs",
)
@click.option(
    "--prefix",
    default="ns",
    help="The prefix to use for the concept URIs",
)
@click.option(
    "--language",
    default="en",
    callback=validate_language_tag,
    help="BCP 47 language tag for prefLabels",
    show_default=True,
)
def skos_skeleton(
    schemas: list[Path],
    output: Path,
    namespace: str,
    prefix: str,
    language: str,
) -> None:
    """Generate SKOS skeleton RDF file from GraphQL schema."""
    from s2dm.exporters.skos import generate_skos_skeleton

    try:
        with output.open("w") as output_stream:
            generate_skos_skeleton(
                schema_paths=schemas,
                output_stream=output_stream,
                namespace=namespace,
                prefix=prefix,
                language=language,
                validate=True,
            )
    except ValueError as e:
        raise click.ClickException(f"SKOS generation failed: {e}") from e
    except OSError as e:
        raise click.ClickException(f"Failed to write output file: {e}") from e


# Check -> version bump
# ----------
@check.command
@schema_option
@click.option(
    "--previous",
    "-p",
    type=click.Path(exists=True, path_type=Path),
    cls=PathResolverOption,
    required=True,
    multiple=True,
    help=(
        "The previous GraphQL schema file or directory containing schema files "
        "to validate against. Can be specified multiple times."
    ),
)
@click.option(
    "--output-type",
    is_flag=True,
    default=False,
    help="Output the version bump type for pipeline usage",
)
@click.pass_obj
def version_bump(console: Console, schemas: list[Path], previous: list[Path], output_type: bool) -> None:
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

    schema_temp_path = create_tempfile_to_composed_schema(schemas)
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
def check_constraints(console: Console, schemas: list[Path]) -> None:
    """
    Enforce intended use of custom directives and naming conventions.
    Checks:
    - instanceTag field and object rules
    - @range and @cardinality min/max
    - Naming conventions (TBD)
    """
    gql_schema = load_schema(schemas)
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
def validate_graphql(console: Console, schemas: list[Path], output: Path) -> None:
    """Validates the given GraphQL schema and returns the whole introspection file if valid graphql schema provided."""
    schema_temp_path = create_tempfile_to_composed_schema(schemas)
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
    "val_schemas",
    type=click.Path(exists=True, path_type=Path),
    cls=PathResolverOption,
    required=True,
    multiple=True,
    help=(
        "The GraphQL schema file or directory containing schema files "
        "to validate against. Can be specified multiple times."
    ),
)
@click.pass_obj
def diff_graphql(console: Console, schemas: list[Path], val_schemas: list[Path], output: Path | None) -> None:
    """Diff for two GraphQL schemas."""
    log.info(f"Comparing schemas: {schemas} and {val_schemas} and writing output to {output}")

    input_temp_path = create_tempfile_to_composed_schema(schemas)
    inspector = GraphQLInspector(input_temp_path)

    val_temp_path = create_tempfile_to_composed_schema(val_schemas)
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
def export_concept_uri(console: Console, schemas: list[Path], output: Path | None, namespace: str, prefix: str) -> None:
    """Generate concept URIs for a GraphQL schema and output as JSON-LD."""
    graphql_schema = load_schema(schemas)
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
@optional_output_option
@click.option("--strict-mode/--no-strict-mode", default=False)
@click.pass_obj
def export_id(console: Console, schema: Path, output: Path | None, strict_mode: bool) -> None:
    """Generate concept IDs for GraphQL schema fields and enums."""

    exporter = IDExporter(schema=schema, output=output, strict_mode=strict_mode, dry_run=output is None)
    node_ids = exporter.run()

    console.rule("[bold blue]Concept IDs")
    console.print(node_ids)


# registry -> init
@registry.command(name="init")
@schema_option
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
@qudt_units_dir_option
@click.pass_obj
def registry_init(
    console: Console,
    schemas: list[Path],
    output: Path,
    concept_namespace: str,
    concept_prefix: str,
    qudt_units_dir: Path,
) -> None:
    """Initialize your spec history with the given schema."""
    output.parent.mkdir(parents=True, exist_ok=True)

    # Generate concept IDs
    id_exporter = IDExporter(schemas, None, strict_mode=False, dry_run=False)
    concept_ids = id_exporter.run()

    # Generate concept URIs
    graphql_schema = load_schema(schemas)
    all_named_types = get_all_named_types(graphql_schema)
    concepts = iter_all_concepts(all_named_types)
    concept_uri_model = create_concept_uri_model(concepts, concept_namespace, concept_prefix)
    concept_uris = concept_uri_model.to_json_ld()

    # Determine history_dir based on output path if output is given, else default to "history"
    output_real = output.resolve()
    history_dir = output_real.parent / "history"

    spec_history_exporter = SpecHistoryExporter(
        schemas=schemas,
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
@qudt_units_dir_option
@click.pass_obj
def registry_update(
    console: Console,
    schemas: list[Path],
    spec_history: Path,
    output: Path,
    concept_namespace: str,
    concept_prefix: str,
    qudt_units_dir: Path,
) -> None:
    """Update a given spec history file with your new schema."""
    output.parent.mkdir(parents=True, exist_ok=True)

    # Generate concept IDs
    id_exporter = IDExporter(schemas, None, strict_mode=False, dry_run=False)
    concept_ids = id_exporter.run()

    # Generate concept URIs
    graphql_schema = load_schema(schemas)
    all_named_types = get_all_named_types(graphql_schema)
    concepts = iter_all_concepts(all_named_types)
    concept_uri_model = create_concept_uri_model(concepts, concept_namespace, concept_prefix)
    concept_uris = concept_uri_model.to_json_ld()

    # Determine history_dir based on output path if output is given, else default to "history"
    output_real = output.resolve()
    history_dir = output_real.parent / "history"

    spec_history_exporter = SpecHistoryExporter(
        schemas=schemas,
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
def search_graphql(console: Console, schemas: list[Path], type: str, case_insensitive: bool, exact: bool) -> None:
    """Search for a type or field in the GraphQL schema. If type was found returns type including all fields,
    if fields was found returns only field in parent type"""
    gql_schema = load_schema(schemas)

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


def display_search_results(
    console: Console,
    results: list[SearchResult],
    term: str,
    limit_value: int | None = None,
    total_count: int | None = None,
) -> None:
    """Display SKOS search results in a formatted way.

    Args:
        console: Rich console for output
        results: List of SearchResult objects
        term: The search term that was used
        limit_value: The parsed limit value (None if unlimited, 0 if zero limit)
        total_count: Total number of matches found (before applying limit)
    """
    if not results:
        console.print(f"[yellow]No matches found for '{term}'[/yellow]")
        return

    # Show result count with appropriate message format
    if total_count is not None and limit_value is not None and limit_value > 0 and len(results) < total_count:
        # Limited results: show "Found X matches, showing only Y:"
        result_message = f"[green]Found {total_count} match(es) for '{term}', showing only {len(results)}:[/green]"
    else:
        # Unlimited results or showing all: show "Found X matches for 'term':"
        actual_count = total_count if total_count is not None else len(results)
        result_message = f"[green]Found {actual_count} match(es) for '{term}':[/green]"

    console.print(result_message)
    console.print()

    for i, result in enumerate(results, 1):
        concept_uri = result.subject
        concept_name = concept_uri.split("#")[-1] if "#" in concept_uri else concept_uri
        property_type = result.predicate
        value = result.object_value
        match_type = result.match_type

        console.print(f"[bold cyan]{i}. {concept_name}[/bold cyan] [dim]({match_type} match)[/dim]")
        console.print(f"   [dim]URI:[/dim] {concept_uri}")
        console.print(f"   [dim]Property:[/dim] {property_type}")
        console.print(f"   [dim]Value:[/dim] {value}")
        console.print()


@search.command(name="skos")
@click.option(
    "--ttl-file",
    "-f",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to the TTL/RDF file containing SKOS concepts",
)
@click.option(
    "--term",
    "-t",
    required=True,
    help="Term to search for in SKOS concepts",
)
@click.option(
    "--case-insensitive",
    "-i",
    is_flag=True,
    default=False,
    help="Perform case-insensitive search (default: case-sensitive)",
)
@click.option(
    "--limit",
    "-l",
    default="10",
    show_default=True,
    help=f"Maximum number of results to return. Use {list(NO_LIMIT_KEYWORDS)} for unlimited results.",
)
@click.pass_obj
def search_skos(console: Console, ttl_file: Path, term: str, case_insensitive: bool, limit: str) -> None:
    """Search for terms in SKOS concepts using SPARQL.

    This command searches through RDF/Turtle files containing SKOS concepts,
    looking for the specified term in concept URIs and object values.
    By default, search is case-sensitive unless --case-insensitive is specified.

    Results are limited to 10 by default. Use --limit to change this number,
    or specify any of these keywords for unlimited results: NO_LIMIT_KEYWORDS.

    The search uses SPARQL to query the RDF graph for subjects and objects
    that contain the search term, focusing on meaningful content while
    excluding predicates from the search scope.
    """
    # Create search service
    try:
        service = SKOSSearchService(ttl_file)
    except FileNotFoundError as e:
        console.print(f"[red]File not found: {e}[/red]")
        raise click.ClickException(f"TTL file not found: {e}") from e
    except ValueError as e:
        console.print(f"[red]Invalid TTL file: {e}[/red]")
        raise click.ClickException(f"TTL file parsing failed: {e}") from e

    with service:
        # Parse limit value
        limit_value = service.parse_limit(limit)

        # Get total count first (for accurate reporting)
        try:
            total_count = service.count_keyword_matches(term, ignore_case=case_insensitive)
        except ValueError as e:
            console.print(f"[red]Count query failed: {e}[/red]")
            raise click.ClickException(f"SKOS count query failed: {e}") from e

        # Get limited results
        try:
            results = service.search_keyword(term, ignore_case=case_insensitive, limit_value=limit_value)
        except ValueError as e:
            console.print(f"[red]Search query failed: {e}[/red]")
            raise click.ClickException(f"SKOS search query failed: {e}") from e

    console.rule(f"[bold blue]SKOS Search Results for '{term}'")
    display_search_results(console, results, term, limit_value, total_count)


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
def similar_graphql(console: Console, schemas: list[Path], keyword: str, output: Path | None) -> None:
    """Search a type (and only types) in the provided grahql schema. Provide '-k all' for all similarities across the
    whole schema (in %)."""
    schema_temp_path = create_tempfile_to_composed_schema(schemas)
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
def stats_graphql(console: Console, schemas: list[Path]) -> None:
    """Get stats of schema."""
    gql_schema = load_schema(schemas)

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
        if is_introspection_type(name):
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
        if kind == "GraphQLScalarType" and not is_builtin_scalar_type(name):
            type_counts["custom_types"][name] = type_counts["custom_types"].get(name, 0) + 1

    console.rule("[bold blue]GraphQL Schema Type Counts")
    console.print(type_counts)


cli.add_command(check)
cli.add_command(compose)
cli.add_command(diff)


cli.add_command(export)
cli.add_command(generate)
cli.add_command(registry)
cli.add_command(similar)
cli.add_command(search)
cli.add_command(stats)
cli.add_command(validate)
cli.add_command(units)

if __name__ == "__main__":
    cli()
