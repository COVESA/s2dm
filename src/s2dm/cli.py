import json
import logging
import os
import queue
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import rich_click as click
from graphql import DocumentNode, GraphQLSchema, parse
from rich.traceback import install

from s2dm import __version__, log
from s2dm.concept.services import iter_all_concepts
from s2dm.exporters.avro import translate_to_avro_protocol, translate_to_avro_schema
from s2dm.exporters.id import IDExporter
from s2dm.exporters.jsonschema import translate_to_jsonschema
from s2dm.exporters.protobuf import translate_to_protobuf
from s2dm.exporters.shacl import translate_to_shacl
from s2dm.exporters.spec_history import SpecHistoryExporter
from s2dm.exporters.utils.extraction import get_all_named_types, get_all_object_types, get_root_level_types_from_query
from s2dm.exporters.utils.graphql_type import is_builtin_scalar_type, is_introspection_type
from s2dm.exporters.utils.naming import load_naming_config
from s2dm.exporters.utils.naming_config import ValidationMode, load_naming_convention_config
from s2dm.exporters.utils.schema import search_schema
from s2dm.exporters.utils.schema_loader import (
    build_schema_str,
    build_schema_with_query,
    check_correct_schema,
    create_tempfile_to_composed_schema,
    download_schema_to_temp,
    is_url,
    load_and_process_schema,
    load_schema,
    load_schema_with_source_map,
    print_schema_with_directives_preserved,
    process_schema,
    resolve_graphql_files,
)
from s2dm.exporters.vspec import translate_to_vspec
from s2dm.registry.concept_uris import create_concept_uri_model
from s2dm.registry.search import NO_LIMIT_KEYWORDS, SearchResult, SKOSSearchService
from s2dm.tools.constraint_checker import ConstraintChecker
from s2dm.tools.diff_parser import DiffChange
from s2dm.tools.graphql_inspector import GraphQLInspector, requires_graphql_inspector
from s2dm.tools.validators import validate_language_tag
from s2dm.units.sync import (
    UNITS_META_FILENAME,
    UNITS_META_VERSION_KEY,
    UnitEnumError,
    get_latest_qudt_version,
    sync_qudt_units,
)

S2DM_HOME = Path.home() / ".s2dm"
DEFAULT_QUDT_UNITS_DIR = S2DM_HOME / "units" / "qudt"


def get_free_port() -> int:
    """Get a free port allocated by the OS."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        port: int = sock.getsockname()[1]
        return port


class SchemaResolverOption(click.Option):
    def process_value(self, ctx: click.Context, value: Any) -> list[Path] | None:
        value = super().process_value(ctx, value)
        if not value:
            return None

        resolved_paths = []

        for item in value:
            item_str = str(item)

            if is_url(item_str):
                try:
                    temp_path = download_schema_to_temp(item_str)
                    resolved_paths.append(temp_path)
                except RuntimeError as e:
                    raise click.BadParameter(str(e), ctx=ctx, param=self) from e
            else:
                path = Path(item_str)
                if not path.exists():
                    raise click.BadParameter(f"Path '{path}' does not exist.", ctx=ctx, param=self)
                resolved_paths.append(path)

        return resolve_graphql_files(resolved_paths)


schema_option = click.option(
    "--schema",
    "-s",
    "schemas",
    type=str,
    cls=SchemaResolverOption,
    required=True,
    multiple=True,
    help="GraphQL schema file, directory, or URL. Can be specified multiple times.",
)


def selection_query_option(required: bool = False) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    return click.option(
        "--selection-query",
        "-q",
        type=click.Path(exists=True, dir_okay=False, path_type=Path),
        required=required,
        help="GraphQL query file to filter the passed schema",
    )


root_type_option = click.option(
    "--root-type",
    "-r",
    type=str,
    help="Root type name for filtering/scoping the schema",
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


def apply_version_tag_suffix(output: Path, version_tag: str) -> Path:
    """Append version tag to output filename if provided and not already suffixed."""
    if not output.stem.endswith(f"_{version_tag}"):
        return output.with_name(f"{output.stem}_{version_tag}{output.suffix}")
    return output


def ensure_output_parent(output: Path | None) -> None:
    """Create parent directory for the given output path if provided."""
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)


def derive_variant_ids_path(base_dir: Path, version_tag: str) -> Path:
    """Build variant IDs filename using version tag."""
    filename = f"variant_ids_{version_tag}.json"
    return base_dir / filename


units_directory_option = click.option(
    "--directory",
    "-d",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_QUDT_UNITS_DIR,
    help="Directory for QUDT unit enums",
    show_default=True,
)


expanded_instances_option = click.option(
    "--expanded-instances",
    "-e",
    is_flag=True,
    default=False,
    help="Expand instance tags into nested structure instead of arrays/repeated fields",
)


strict_option = click.option(
    "--strict",
    "-S",
    is_flag=True,
    default=False,
    help="Enforce strict type translation from GraphQL schema",
)


avro_namespace_option = click.option(
    "--namespace",
    "-ns",
    type=str,
    required=True,
    help="Avro namespace for types",
)


naming_config_option = click.option(
    "--naming-config",
    type=click.Path(exists=True, path_type=Path),
    help="YAML file containing naming configuration",
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


def assert_correct_schema(schema: GraphQLSchema) -> None:
    schema_errors = check_correct_schema(schema)
    if schema_errors:
        log.error("Schema validation failed:")
        for error in schema_errors:
            log.error(error)
        log.error(f"Found {len(schema_errors)} validation error(s). Please fix the schema before exporting.")
        sys.exit(1)


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
    if log_file:
        file_handler = logging.FileHandler(log_file, mode="w")
        file_handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(message)s"))
        log.addHandler(file_handler)

    log.setLevel(log_level)
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
def generate() -> None:
    """Generate commands."""
    pass


@click.group()
def registry() -> None:
    """Registry commands for variant IDs and spec history tracking.

    This group includes commands for:
    - Generating variant-based concept IDs (registry id)
    - Initializing spec history with variant tracking (registry init)
    - Updating spec history with schema changes (registry update)
    - Generating concept URIs (registry concept-uri)
    """
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
        "QUDT version tag (e.g., 3.1.6). Defaults to the latest tag, falls back to 'main' when tags are unavailable."
    ),
)
@units_directory_option
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be generated without actually writing files",
)
def units_sync(version: str | None, directory: Path, dry_run: bool) -> None:
    """Fetch QUDT quantity kinds and generate GraphQL enums under the specified directory.

    Args:
        version: QUDT version tag. Defaults to the latest tag.
        directory: Output directory for generated QUDT unit enums (default: ~/.s2dm/units/qudt)
        dry_run: Show what would be generated without actually writing files
    """

    version_to_use = version or get_latest_qudt_version()

    try:
        written = sync_qudt_units(directory, version_to_use, dry_run=dry_run)
    except UnitEnumError as e:
        log.error(f"Units sync failed: {e}")
        sys.exit(1)

    if dry_run:
        log.info(f"Would generate {len(written)} enum files under {directory}")
        log.print(f"Version: {version_to_use}")
        log.hint("Use without --dry-run to actually write files")
    else:
        log.success(f"Generated {len(written)} enum files under {directory}")
        log.print(f"Version: {version_to_use}")


@units.command(name="check-version")
@units_directory_option
def units_check_version(directory: Path) -> None:
    """Compare local synced QUDT version with the latest remote version and print a message.

    Args:
        directory: Directory containing generated QUDT unit enums (default: ~/.s2dm/units/qudt)
    """

    meta_path = directory / UNITS_META_FILENAME
    if not meta_path.exists():
        log.warning("No metadata.json found. Run 's2dm units sync' first.")
        sys.exit(1)

    try:
        local_version = json.loads(meta_path.read_text(encoding="utf-8"))[UNITS_META_VERSION_KEY]
    except (json.JSONDecodeError, KeyError) as e:
        log.error(f"Invalid metadata.json: {e}")
        sys.exit(1)

    latest = get_latest_qudt_version()

    if latest == local_version:
        log.success("Units are up to date.")
    else:
        log.warning(f"A newer release is available. Local: {local_version}, Latest: {latest}")


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


@click.group()
def playground() -> None:
    """GUI playground commands."""
    pass


@playground.command(name="init")
def playground_init() -> None:
    """Initialize the GUI playground by installing its dependencies and building it."""
    playground_dir = Path.cwd() / "playground"

    if not playground_dir.exists():
        log.error(f"Playground directory not found at {playground_dir}")
        sys.exit(1)

    if not (playground_dir / "package.json").exists():
        log.error(f"package.json not found in {playground_dir}")
        sys.exit(1)

    log.info("Installing playground dependencies...")
    try:
        subprocess.run(
            ["npm", "install"],
            cwd=playground_dir,
            check=True,
        )
        log.success("Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        log.error(f"Failed to install dependencies: {e}")
        sys.exit(1)
    except FileNotFoundError:
        log.error("npm not found. Please install Node.js and npm.")
        sys.exit(1)

    log.info("Building playground...")
    try:
        subprocess.run(
            ["npm", "run", "build"],
            cwd=playground_dir,
            check=True,
        )
        log.success("Playground built successfully")
    except subprocess.CalledProcessError as e:
        log.error(f"Failed to build playground: {e}")
        sys.exit(1)

    log.success("Playground initialization complete!")


@playground.command(name="start")
def playground_start() -> None:
    """Launch the GUI playground."""
    playground_dir = Path.cwd() / "playground"

    if not playground_dir.exists():
        log.error(f"Playground directory not found at {playground_dir}")
        sys.exit(1)

    if not (playground_dir / "node_modules").exists():
        log.error("node_modules not found. Run 's2dm playground init' first.")
        sys.exit(1)

    api_process: subprocess.Popen[str] | None = None
    react_process: subprocess.Popen[str] | None = None

    def stop_process(process: subprocess.Popen[str] | None) -> None:
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    def cleanup() -> None:
        log.info("Stopping servers...")
        stop_process(react_process)
        stop_process(api_process)
        log.success("All servers stopped")

    def stream_output(process: subprocess.Popen[str], prefix: str) -> None:
        if process.stdout:
            for line in process.stdout:
                print(f"{prefix}: {line}", end="")

    shutdown_events: queue.SimpleQueue[str] = queue.SimpleQueue()

    def watch_process(process: subprocess.Popen[str], process_name: str) -> None:
        process.wait()
        shutdown_events.put(process_name)

    def wait_for_react_server(
        host: str, port: int, process: subprocess.Popen[str], timeout_seconds: float = 15.0
    ) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if process.poll() is not None:
                return False
            try:
                with socket.create_connection((host, port), timeout=0.5):
                    return True
            except OSError:
                time.sleep(0.1)
        return False

    exit_code = 0

    try:
        api_port = get_free_port()
        api_url = f"http://127.0.0.1:{api_port}"
        react_port = get_free_port()
        react_url = f"http://localhost:{react_port}"

        log.info(f"Starting API server on {api_url}")
        api_process = subprocess.Popen(
            ["uvicorn", "s2dm.api.main:app", "--reload", "--host", "127.0.0.1", "--port", str(api_port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        api_thread = threading.Thread(target=stream_output, args=(api_process, "API"), daemon=True)
        api_thread.start()

        log.info(f"Starting React dev server on {react_url}")
        react_env = {**os.environ, "VITE_API_BASE_URL": api_url}
        react_process = subprocess.Popen(
            ["npm", "run", "dev", "--", "--port", str(react_port), "--strictPort"],
            cwd=playground_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=react_env,
        )

        react_thread = threading.Thread(target=stream_output, args=(react_process, "React"), daemon=True)
        react_thread.start()

        if not wait_for_react_server(host="127.0.0.1", port=react_port, process=react_process):
            log.error(f"React dev server did not become ready at {react_url}")
            exit_code = 1

        if exit_code == 0:
            log.info(f"Opening browser at {react_url}")
            webbrowser.open(react_url)

            log.success("Both servers running. Press Ctrl+C to stop.")

            threading.Thread(target=watch_process, args=(api_process, "API server"), daemon=True).start()
            threading.Thread(target=watch_process, args=(react_process, "React dev server"), daemon=True).start()

            stopped_process_name = shutdown_events.get()
            log.error(f"{stopped_process_name} stopped unexpectedly")
            exit_code = 1

    except FileNotFoundError as error:
        log.error(f"Command not found: {error}. Ensure Node.js/npm and uvicorn are installed.")
        exit_code = 1
    except OSError as error:
        log.error(f"Failed to start playground processes: {error}")
        exit_code = 1
    except KeyboardInterrupt:
        log.info("Interrupted by user")
    finally:
        cleanup()

    if exit_code != 0:
        sys.exit(exit_code)


@click.command()
@schema_option
@selection_query_option()
@root_type_option
@naming_config_option
@output_option
@expanded_instances_option
def compose(
    schemas: list[Path],
    root_type: str | None,
    selection_query: Path | None,
    naming_config: Path | None,
    output: Path,
    expanded_instances: bool,
) -> None:
    """Compose GraphQL schema files into a single output file."""
    try:
        graphql_schema, source_map = load_schema_with_source_map(schemas)
        assert_correct_schema(graphql_schema)

        query_document = None
        if selection_query:
            query_document = parse(selection_query.read_text())

        naming_config_dict = load_naming_config(naming_config)

        annotated_schema = process_schema(
            schema=graphql_schema,
            source_map=source_map,
            naming_config=naming_config_dict,
            query_document=query_document,
            root_type=root_type,
            expanded_instances=expanded_instances,
        )
        composed_schema_str = print_schema_with_directives_preserved(annotated_schema.schema, source_map)

        output.write_text(composed_schema_str)

        if selection_query:
            log.success(f"Successfully composed and filtered schema based on selection query to {output}")
        elif root_type:
            log.success(f"Successfully composed schema with root type '{root_type}' to {output}")
        else:
            log.success(f"Successfully composed schema to {output}")

    except OSError as e:
        log.error(f"File I/O error: {e}")
        sys.exit(1)
    except ValueError as e:
        log.error(f"Invalid schema: {e}")
        sys.exit(1)
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        sys.exit(1)


# SHACL
# ----------
@export.command
@schema_option
@selection_query_option()
@output_option
@root_type_option
@naming_config_option
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
@expanded_instances_option
def shacl(
    schemas: list[Path],
    selection_query: Path | None,
    output: Path,
    root_type: str | None,
    naming_config: Path | None,
    serialization_format: str,
    shapes_namespace: str,
    shapes_namespace_prefix: str,
    model_namespace: str,
    model_namespace_prefix: str,
    expanded_instances: bool,
) -> None:
    """Generate SHACL shapes from a given GraphQL schema."""
    annotated_schema, naming_config_dict, _ = load_and_process_schema(
        schema_paths=schemas,
        naming_config_path=naming_config,
        selection_query_path=selection_query,
        root_type=root_type,
        expanded_instances=expanded_instances,
    )
    assert_correct_schema(annotated_schema.schema)

    result = translate_to_shacl(
        annotated_schema,
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
@selection_query_option()
@output_option
@root_type_option
@naming_config_option
@expanded_instances_option
def vspec(
    schemas: list[Path],
    selection_query: Path | None,
    output: Path,
    root_type: str | None,
    naming_config: Path | None,
    expanded_instances: bool,
) -> None:
    """Generate VSPEC from a given GraphQL schema."""
    annotated_schema, _, _ = load_and_process_schema(
        schema_paths=schemas,
        naming_config_path=naming_config,
        selection_query_path=selection_query,
        root_type=root_type,
        expanded_instances=expanded_instances,
    )
    assert_correct_schema(annotated_schema.schema)

    result = translate_to_vspec(annotated_schema)
    output.parent.mkdir(parents=True, exist_ok=True)
    _ = output.write_text(result)


# Export -> json schema
# ----------
@export.command
@schema_option
@selection_query_option()
@output_option
@root_type_option
@naming_config_option
@strict_option
@expanded_instances_option
def jsonschema(
    schemas: list[Path],
    selection_query: Path | None,
    output: Path,
    root_type: str | None,
    naming_config: Path | None,
    strict: bool,
    expanded_instances: bool,
) -> None:
    """Generate JSON Schema from a given GraphQL schema."""
    annotated_schema, _, _ = load_and_process_schema(
        schema_paths=schemas,
        naming_config_path=naming_config,
        selection_query_path=selection_query,
        root_type=root_type,
        expanded_instances=expanded_instances,
    )
    assert_correct_schema(annotated_schema.schema)

    result = translate_to_jsonschema(annotated_schema, root_type, strict)
    _ = output.write_text(result)


# Export -> avro
# ----------
@click.group()
def avro() -> None:
    """Apache Avro export commands."""
    pass


@avro.command
@schema_option
@selection_query_option(required=True)
@output_option
@root_type_option
@naming_config_option
@avro_namespace_option
@expanded_instances_option
def schema(
    schemas: list[Path],
    selection_query: Path,
    output: Path,
    root_type: str | None,
    naming_config: Path | None,
    namespace: str,
    expanded_instances: bool,
) -> None:
    """Generate Apache Avro schema from a given GraphQL schema."""
    annotated_schema, _, query_document = load_and_process_schema(
        schema_paths=schemas,
        naming_config_path=naming_config,
        selection_query_path=selection_query,
        root_type=root_type,
        expanded_instances=expanded_instances,
    )
    assert_correct_schema(annotated_schema.schema)

    result = translate_to_avro_schema(annotated_schema, namespace, cast(DocumentNode, query_document))
    _ = output.write_text(result)


@avro.command
@schema_option
@selection_query_option(required=False)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=False, writable=True, path_type=Path),
    required=True,
    help="Output directory for .avdl files",
)
@root_type_option
@naming_config_option
@avro_namespace_option
@expanded_instances_option
@strict_option
def protocol(
    schemas: list[Path],
    selection_query: Path | None,
    output: Path,
    root_type: str | None,
    naming_config: Path | None,
    namespace: str,
    expanded_instances: bool,
    strict: bool,
) -> None:
    """Generate Avro IDL protocols for types marked with @struct directive."""
    annotated_schema, _, _ = load_and_process_schema(
        schema_paths=schemas,
        naming_config_path=naming_config,
        selection_query_path=selection_query,
        root_type=root_type,
        expanded_instances=expanded_instances,
    )
    assert_correct_schema(annotated_schema.schema)

    avro_protocols = translate_to_avro_protocol(annotated_schema, namespace, strict)

    output.mkdir(parents=True, exist_ok=True)

    for type_name, protocol in avro_protocols.items():
        output_file = output / f"{type_name}.avdl"
        _ = output_file.write_text(protocol)

    log.info(f"Generated {len(avro_protocols)} IDL protocol(s) in {output}")


# Export -> protobuf
# ----------
@export.command
@schema_option
@selection_query_option(required=True)
@output_option
@root_type_option
@naming_config_option
@click.option(
    "--flatten-naming",
    "-f",
    is_flag=True,
    default=False,
    help="Flatten nested field names.",
)
@click.option(
    "--package-name",
    "-p",
    type=str,
    help="Protobuf package name",
)
@expanded_instances_option
def protobuf(
    schemas: list[Path],
    selection_query: Path,
    output: Path,
    root_type: str | None,
    naming_config: Path | None,
    flatten_naming: bool,
    package_name: str | None,
    expanded_instances: bool,
) -> None:
    """Generate Protocol Buffers (.proto) file from GraphQL schema."""
    annotated_schema, _, query_document = load_and_process_schema(
        schema_paths=schemas,
        naming_config_path=naming_config,
        selection_query_path=selection_query,
        root_type=root_type,
        expanded_instances=expanded_instances,
    )
    assert_correct_schema(annotated_schema.schema)

    flatten_root_types = None
    if flatten_naming:
        flatten_root_types = get_root_level_types_from_query(annotated_schema.schema, query_document)

    result = translate_to_protobuf(
        annotated_schema, cast(DocumentNode, query_document), package_name, flatten_root_types
    )
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
    type=str,
    cls=SchemaResolverOption,
    required=True,
    multiple=True,
    help=("Previous GraphQL schema file, directory, or URL to validate against. Can be specified multiple times."),
)
@click.option(
    "--output-type",
    is_flag=True,
    default=False,
    help="Output the version bump type for pipeline usage",
)
@requires_graphql_inspector
def version_bump(
    schemas: list[Path], previous: list[Path], output_type: bool, inspector_path: Path | None = None
) -> None:
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
    inspector = GraphQLInspector(previous_schema_temp_path, node_modules_path=inspector_path)

    schema_temp_path = create_tempfile_to_composed_schema(schemas)
    diff_result = inspector.diff(schema_temp_path)

    # Determine version bump type based on output analysis
    version_bump_type = None

    if diff_result.returncode == 0:
        if "No changes detected" in diff_result.output:
            log.success("No version bump needed")
            version_bump_type = None
        elif "No breaking changes detected" in diff_result.output:
            # Check for dangerous changes (⚠ symbols)
            if "⚠" in diff_result.output:
                log.warning("Minor version bump needed")
                version_bump_type = "minor"
            else:
                log.success("Patch version bump needed")
                version_bump_type = "patch"
        else:
            log.error("Unknown state, please check your input with 'diff' tool.")
    else:
        if "Detected" in diff_result.output and "breaking changes" in diff_result.output:
            log.error("Detected breaking changes, major version bump needed")
            version_bump_type = "major"
        else:
            log.error("Unknown error occurred during schema comparison")

    # Output the version bump type for pipeline usage
    if output_type:
        if version_bump_type:
            log.print(version_bump_type)
        else:
            log.print("none")

    # Exit with success code
    sys.exit(0)


@check.command(name="constraints")
@schema_option
@naming_config_option
def check_constraints(schemas: list[Path], naming_config: Path | None) -> None:
    """
    Enforce intended use of custom directives and naming conventions.
    Checks:
    - instanceTag field and object rules
    - @range and @cardinality min/max
    - Naming conventions (optional, if --naming-config provided)
    """
    gql_schema = load_schema(schemas)
    objects = get_all_object_types(gql_schema)
    naming_convention_config = load_naming_convention_config(naming_config, ValidationMode.CHECK)

    constraint_checker = ConstraintChecker(gql_schema, naming_convention_config)
    errors = constraint_checker.run(objects)

    if errors:
        log.rule("Constraint Violations", style="bold red")
        for err in errors:
            log.error(f"- {err}")
        raise sys.exit(1)
    else:
        log.success("All constraints passed!")


# validate -> graphql
# ----------
@validate.command(name="graphql")
@schema_option
@output_option
@requires_graphql_inspector
def validate_graphql(schemas: list[Path], output: Path, inspector_path: Path | None = None) -> None:
    """Validates the given GraphQL schema and returns the whole introspection file if valid graphql schema provided."""
    schema_temp_path = create_tempfile_to_composed_schema(schemas)
    inspector = GraphQLInspector(schema_temp_path, node_modules_path=inspector_path)
    validation_result = inspector.introspect(output)

    log.print(validation_result.output)
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
    type=str,
    cls=SchemaResolverOption,
    required=True,
    multiple=True,
    help=("GraphQL schema file, directory, or URL to validate against. Can be specified multiple times."),
)
@requires_graphql_inspector
def diff_graphql(
    schemas: list[Path], val_schemas: list[Path], output: Path | None, inspector_path: Path | None = None
) -> None:
    """Diff for two GraphQL schemas.

    Uses the schema composer which includes all directives and types.
    """
    log.info(f"Comparing schemas: {schemas} and {val_schemas} and writing output to {output}")

    # Use schema composer to create composed schemas (includes directives and all types)
    input_temp_path = create_tempfile_to_composed_schema(schemas)
    val_temp_path = create_tempfile_to_composed_schema(val_schemas)

    try:
        # Use GraphQLInspector's structured diff method
        inspector = GraphQLInspector(input_temp_path, node_modules_path=inspector_path)
        try:
            structured_diff = inspector.diff_structured(val_temp_path)
        except RuntimeError as e:
            log.error(f"Failed to get structured diff: {e}")
            sys.exit(2)

        # Format JSON output as a direct array
        json_output = json.dumps([change.model_dump() for change in structured_diff], indent=2, ensure_ascii=False)

        if output is not None:
            log.info(f"writing file to {output=}")
            output.parent.mkdir(parents=True, exist_ok=True)
            # Write file synchronously to ensure it's on disk before exit
            with open(output, "w", encoding="utf-8") as f:
                f.write(json_output)
                f.flush()
                os.fsync(f.fileno())
        else:
            # If no output file specified, still print structured format
            log.print(json_output)

        # Exit with code 1 if breaking changes detected, 0 otherwise
        has_breaking = any(change.criticality != "NON_BREAKING" for change in structured_diff)
        exit_code = 1 if has_breaking else 0
        sys.exit(exit_code)
    finally:
        # Clean up temporary files
        input_temp_path.unlink(missing_ok=True)
        val_temp_path.unlink(missing_ok=True)


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
def export_concept_uri(schemas: list[Path], output: Path | None, namespace: str, prefix: str) -> None:
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
        log.success(f"Concept URIs written to {output}")

    log.rule("Concept URIs (JSON-LD)")
    log.print_dict(data)


# registry -> id
@registry.command(name="id")
@schema_option
@optional_output_option
@click.option(
    "--previous-ids",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to previous ID file for comparison",
)
@click.option(
    "--diff-file",
    "diff_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to structured diff JSON output from 'diff graphql' command",
)
@click.option(
    "--version-tag",
    type=str,
    required=True,
    help="Version tag/identifier for metadata",
)
def export_id(
    schemas: list[Path],
    output: Path | None,
    previous_ids: Path | None,
    diff_file: Path | None,
    version_tag: str,
) -> None:
    """Generate variant-based concept IDs for GraphQL schema fields and enums.

    Uses graphql-inspector diff to detect changes and only increments
    variants for fields that actually changed.

    The workflow will provide:
    - previous_ids: Previous variant-ids.json file
    - diff_file: Path to structured diff JSON from 'diff graphql' command (required if previous_ids provided)
    - version-tag: Version tag/identifier for metadata (required)
    """
    composed_schema = load_schema(schemas)

    # Validate: if previous_ids is provided, diff_file must also be provided
    # Without diff_file, variant increments won't work correctly
    # Note: Click already validates that previous_ids exists (exists=True)
    if previous_ids and not diff_file:
        log.error(
            "When --previous-ids is provided, --diff-file is required. "
            "The diff file is needed to determine which concepts changed and should have their variants incremented."
        )
        sys.exit(1)

    # Use version tag as postfix for output file when provided
    if output:
        output = apply_version_tag_suffix(output, version_tag)

    # Load diff output if provided
    diff_output: list[DiffChange] | None = None
    if diff_file:
        try:
            with open(diff_file, encoding="utf-8") as f:
                json_data = json.load(f)
                if not isinstance(json_data, list):
                    raise ValueError("Invalid diff file: expected a JSON array")
                diff_output = [DiffChange.model_validate(change) for change in json_data]
        except (json.JSONDecodeError, OSError, ValueError) as e:
            log.error(f"Failed to load diff file from {diff_file}: {e}")
            sys.exit(1)

    exporter = IDExporter(
        schema=composed_schema,
        version_tag=version_tag,
        output=output,
        previous_ids_path=previous_ids,
        diff_output=diff_output,
    )
    result = exporter.run()

    log.rule("Variant IDs")
    log.print_dict(result.to_dict())


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
@click.option(
    "--version-tag",
    type=str,
    required=True,
    help="Version tag/identifier for metadata",
)
def registry_init(
    schemas: list[Path],
    output: Path,
    concept_namespace: str,
    concept_prefix: str,
    version_tag: str,
) -> None:
    """Initialize spec history with variant tracking for the given schema.

    This creates a spec history file with concept IDs.
    Use 'registry update' to update an existing spec history with schema changes.
    """
    output = apply_version_tag_suffix(output, version_tag)
    ensure_output_parent(output)

    composed_schema_str = build_schema_str(schemas)
    composed_schema = build_schema_with_query(composed_schema_str)

    # Generate variant IDs file path (same directory as output)
    variant_ids_output = derive_variant_ids_path(output.parent, version_tag)

    id_exporter = IDExporter(
        schema=composed_schema,
        version_tag=version_tag,
        output=variant_ids_output,
    )
    id_result = id_exporter.run()

    # Extract variant IDs dict (format: {"concept_name": "Concept/vN"})
    variant_ids: dict[str, str] = {}
    for concept_name, variant_entry in id_result.concepts.items():
        variant_ids[concept_name] = variant_entry.id

    # Generate concept URIs
    all_named_types = get_all_named_types(composed_schema)
    concepts = iter_all_concepts(all_named_types)
    concept_uri_model = create_concept_uri_model(concepts, concept_namespace, concept_prefix)
    concept_uris = concept_uri_model.to_json_ld()

    # Determine history_dir based on output path if output is given, else default to "history"
    output_real = output.resolve()
    history_dir = output_real.parent / "history"

    spec_history_exporter = SpecHistoryExporter(
        schema_content=composed_schema_str,
        output=output,
        history_dir=history_dir,
    )
    spec_history_result = spec_history_exporter.init_spec_history_model(
        concept_uris, variant_ids, concept_uri_model, version_tag
    )

    log.rule("Variant IDs")
    log.print_dict(variant_ids)
    log.rule("Concept URIs")
    log.print_dict(concept_uris)
    log.rule("Spec history (updated)")
    log.print_dict(spec_history_result.model_dump())


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
@click.option(
    "--previous-ids",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to previous variant IDs file (e.g., variant_ids_v1.0.0.json)",
)
@click.option(
    "--diff-file",
    "diff_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to structured diff JSON output from 'diff graphql' command",
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
@click.option(
    "--version-tag",
    type=str,
    required=True,
    help="Version tag/identifier for metadata",
)
def registry_update(
    schemas: list[Path],
    spec_history: Path,
    output: Path,
    previous_ids: Path,
    diff_file: Path | None,
    concept_namespace: str,
    concept_prefix: str,
    version_tag: str,
) -> None:
    """Update a spec history file with schema changes, tracking variant increments.

    Uses graphql-inspector diff to detect changes and only increments
    variants for fields that actually changed.
    """
    output = apply_version_tag_suffix(output, version_tag)
    ensure_output_parent(output)

    # Load diff output if provided
    diff_output: list[DiffChange] | None = None
    if diff_file:
        try:
            with open(diff_file, encoding="utf-8") as f:
                json_data = json.load(f)
                if not isinstance(json_data, list):
                    raise ValueError("Invalid diff file: expected a JSON array")
                diff_output = [DiffChange.model_validate(change) for change in json_data]
        except (json.JSONDecodeError, OSError, ValueError) as e:
            log.error(f"Failed to load diff file from {diff_file}: {e}")
            sys.exit(1)

    composed_schema_str = build_schema_str(schemas)
    composed_schema = build_schema_with_query(composed_schema_str)

    # Determine variant IDs output path based on the existing output option.
    variant_ids_output = derive_variant_ids_path(output.parent, version_tag)

    id_exporter = IDExporter(
        schema=composed_schema,
        version_tag=version_tag,
        output=variant_ids_output,
        previous_ids_path=previous_ids,
        diff_output=diff_output,
    )
    id_result = id_exporter.run()

    # Extract variant IDs dict (format: {"concept_name": "Concept/vN"})
    variant_ids: dict[str, str] = {}
    for concept_name, variant_entry in id_result.concepts.items():
        variant_ids[concept_name] = variant_entry.id

    # Generate concept URIs
    all_named_types = get_all_named_types(composed_schema)
    concepts = iter_all_concepts(all_named_types)
    concept_uri_model = create_concept_uri_model(concepts, concept_namespace, concept_prefix)
    concept_uris = concept_uri_model.to_json_ld()

    # Determine history_dir based on output path if output is given, else default to "history"
    output_real = output.resolve()
    history_dir = output_real.parent / "history"

    spec_history_exporter = SpecHistoryExporter(
        schema_content=composed_schema_str,
        output=output,
        history_dir=history_dir,
    )
    spec_history_result = spec_history_exporter.update_spec_history_model(
        concept_uris=concept_uris,
        variant_ids=variant_ids,
        concept_uri_model=concept_uri_model,
        spec_history_path=spec_history,
        version_tag=version_tag,
    )

    log.rule("Variant IDs")
    log.print_dict(variant_ids)
    log.rule("Concept URIs")
    log.print_dict(concept_uris)
    log.rule("Spec history (updated)")
    log.print_dict(spec_history_result.model_dump())


# search -> graphql
@search.command(name="graphql")
@schema_option
@click.option("--type", "-t", required=True, help="Type or field you want to search the graphql schema for.")
@click.option("--case-insensitive", "-i", is_flag=True, default=False, help="Perform a case-insensitive search.")
@click.option("--exact", is_flag=True, default=False, help="Perform an exact match search.")
def search_graphql(schemas: list[Path], type: str, case_insensitive: bool, exact: bool) -> None:
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
    log.rule(f"Search results for '{type}'")
    if not type_results and not field_results:
        log.warning(f"No matches found for '{type}'.")
    else:
        for tname, fields in type_results.items():
            log.colored(tname, style="green")
            if fields:
                for field in fields:
                    log.list_item(str(field), prefix="  •")
        for tname, fields in field_results.items():
            if fields:
                log.key_value(tname, str(fields), key_style="green")


def display_search_results(
    results: list[SearchResult],
    term: str,
    limit_value: int | None = None,
    total_count: int | None = None,
) -> None:
    """Display SKOS search results in a formatted way.

    Args:
        results: List of SearchResult objects
        term: The search term that was used
        limit_value: The parsed limit value (None if unlimited, 0 if zero limit)
        total_count: Total number of matches found (before applying limit)
    """
    if not results:
        log.warning(f"No matches found for '{term}'")
        return

    # Show result count with appropriate message format
    if total_count is not None and limit_value is not None and limit_value > 0 and len(results) < total_count:
        # Limited results: show "Found X matches, showing only Y:"
        log.success(f"Found {total_count} match(es) for '{term}', showing only {len(results)}:")
    else:
        # Unlimited results or showing all: show "Found X matches for 'term':"
        actual_count = total_count if total_count is not None else len(results)
        log.success(f"Found {actual_count} match(es) for '{term}':")

    log.print("")

    for i, result in enumerate(results, 1):
        concept_uri = result.subject
        concept_name = concept_uri.split("#")[-1] if "#" in concept_uri else concept_uri
        property_type = result.predicate
        value = result.object_value
        match_type = result.match_type

        # Display numbered item with match type
        log.colored(f"{i}. {concept_name}")
        log.hint(f"   ({match_type} match)")

        # Display structured key-value pairs with indentation
        log.key_value("\tURI", concept_uri)
        log.key_value("\tProperty", property_type)
        log.key_value("\tValue", value)
        log.print("")


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
def search_skos(ttl_file: Path, term: str, case_insensitive: bool, limit: str) -> None:
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
        log.error(f"File not found: {e}")
        raise click.ClickException(f"TTL file not found: {e}") from e
    except ValueError as e:
        log.error(f"Invalid TTL file: {e}")
        raise click.ClickException(f"TTL file parsing failed: {e}") from e

    with service:
        # Parse limit value
        limit_value = service.parse_limit(limit)

        # Get total count first (for accurate reporting)
        try:
            total_count = service.count_keyword_matches(term, ignore_case=case_insensitive)
        except ValueError as e:
            log.error(f"Count query failed: {e}")
            raise click.ClickException(f"SKOS count query failed: {e}") from e

        # Get limited results
        try:
            results = service.search_keyword(term, ignore_case=case_insensitive, limit_value=limit_value)
        except ValueError as e:
            log.error(f"Search query failed: {e}")
            raise click.ClickException(f"SKOS search query failed: {e}") from e

    log.rule(f"SKOS Search Results for '{term}'")
    display_search_results(results, term, limit_value, total_count)


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
@requires_graphql_inspector
def similar_graphql(schemas: list[Path], keyword: str, output: Path | None, inspector_path: Path | None = None) -> None:
    """Search a type (and only types) in the provided grahql schema. Provide '-k all' for all similarities across the
    whole schema (in %)."""
    schema_temp_path = create_tempfile_to_composed_schema(schemas)
    inspector = GraphQLInspector(schema_temp_path, node_modules_path=inspector_path)
    if output:
        log.info(f"Search will write file to {output}")

    # if keyword == "all" search all elements otherwise only keyword
    search_result = inspector.similar(output) if keyword == "all" else inspector.similar_keyword(keyword, output)

    log.rule(f"Search result for '{keyword}'")
    log.print(search_result.output)
    sys.exit(search_result.returncode)


# stats -> graphql
# ----------
@stats.command(name="graphql")
@schema_option
def stats_graphql(schemas: list[Path]) -> None:
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

    log.rule("GraphQL Schema Type Counts")
    log.print_dict(type_counts)


cli.add_command(check)
cli.add_command(compose)
cli.add_command(diff)

export.add_command(avro)
cli.add_command(export)
cli.add_command(generate)
cli.add_command(playground)
cli.add_command(registry)
cli.add_command(similar)
cli.add_command(search)
cli.add_command(stats)
cli.add_command(validate)
cli.add_command(units)

if __name__ == "__main__":
    cli()
