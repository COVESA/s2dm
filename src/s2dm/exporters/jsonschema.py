"""Convert GraphQL schema to JSON Schema.

This module provides functionality to convert GraphQL schemas to JSON Schema Draft 2020-12
format with full property expansion and directive support.
"""

import subprocess
import tempfile
from pathlib import Path

import click

from s2dm import log
from s2dm.exporters.utils import build_schema_str


def find_project_root(marker_file: str = "pyproject.toml") -> Path | None:
    """Find the project root by looking for a marker file.

    Args:
        marker_file: Name of the file that indicates project root

    Returns:
        Path to project root, or None if not found
    """
    current_path = Path(__file__).resolve()

    for parent in current_path.parents:
        if (parent / marker_file).exists():
            return parent

    return None


def check_nodejs_requirements() -> tuple[bool, list[str]]:
    """Check if Node.js and npm are installed and accessible.

    Returns:
        Tuple of (requirements_met, missing_requirements)
    """
    missing = []

    # Check Node.js
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            missing.append("Node.js (node command failed)")
        else:
            log.debug(f"Found Node.js version: {result.stdout.strip()}")
    except FileNotFoundError:
        missing.append("Node.js (node command not found)")

    # Check npm
    try:
        result = subprocess.run(
            ["npm", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            missing.append("npm (npm command failed)")
        else:
            log.debug(f"Found npm version: {result.stdout.strip()}")
    except FileNotFoundError:
        missing.append("npm (npm command not found)")

    return len(missing) == 0, missing


def build_jsonschema_cli(project_root: Path) -> bool:
    """Build the jsonschema CLI if not already built.

    Args:
        project_root: Path to the project root

    Returns:
        True if build was successful or already exists, False otherwise
    """
    jsonschema_dir = project_root / "jsonschema"
    local_cli = jsonschema_dir / "dist" / "index.js"

    # If already built and working, return True
    if local_cli.exists():
        try:
            result = subprocess.run(
                ["node", str(local_cli), "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return True
        except FileNotFoundError:
            pass

    # Check Node.js and npm requirements first
    requirements_met, missing = check_nodejs_requirements()
    if not requirements_met:
        log.error("Missing required dependencies:")
        for missing_item in missing:
            log.error(f"  - {missing_item}")
        log.error("Please install Node.js and npm before proceeding")
        return False

    # Check if jsonschema directory exists
    if not jsonschema_dir.exists():
        log.error(f"jsonschema directory not found at {jsonschema_dir}")
        return False

    # Check if package.json exists
    package_json = jsonschema_dir / "package.json"
    if not package_json.exists():
        log.error(f"package.json not found at {package_json}")
        return False

    log.info("Building jsonschema CLI...")

    try:
        # Install dependencies
        log.info("Installing npm dependencies...")
        result = subprocess.run(
            ["npm", "install"],
            cwd=jsonschema_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            log.error(f"npm install failed: {result.stderr}")
            return False

        # Build the project
        log.info("Building TypeScript...")
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=jsonschema_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            log.error(f"npm run build failed: {result.stderr}")
            return False

        # Verify the build was successful
        if local_cli.exists():
            try:
                result = subprocess.run(
                    ["node", str(local_cli), "--version"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode == 0:
                    log.info("jsonschema CLI built successfully!")
                    return True
            except FileNotFoundError:
                pass

        log.error("Build completed but CLI is not working")
        return False

    except Exception as e:
        log.error(f"Error building jsonschema CLI: {e}")
        return False


def find_gql2json_command() -> str | None:
    """Find the s2dm-gql2jsonschema command, either global or local.

    Returns:
        Path to the s2dm-gql2jsonschema command if found, None otherwise
    """
    # Try global command first
    try:
        result = subprocess.run(
            ["s2dm-gql2jsonschema", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return "s2dm-gql2jsonschema"
    except FileNotFoundError:
        pass

    # Try local build in jsonschema directory
    project_root = find_project_root()
    if project_root is None:
        return None

    # Build the CLI if needed
    if not build_jsonschema_cli(project_root):
        return None

    local_cli = project_root / "jsonschema" / "dist" / "index.js"
    return f"node {local_cli}"


def translate_to_jsonschema(schema_path: Path, output_path: Path) -> None:
    """Translate a GraphQL schema to JSON Schema.

    Args:
        schema_path: Path to the GraphQL schema file
        output_path: Path to write the JSON Schema output

    Raises:
        RuntimeError: If the conversion fails
    """
    # Find the converter command
    gql2json_cmd = find_gql2json_command()
    if not gql2json_cmd:
        raise RuntimeError(
            "GraphQL to JSON Schema converter is not available.\n"
            "Please ensure Node.js and npm are installed, and the jsonschema directory exists."
        )

    # Build the complete schema string
    schema_string = build_schema_str(schema_path)

    # Create a temporary file for the schema
    with tempfile.NamedTemporaryFile(mode="w", suffix=".graphql", delete=False) as temp_file:
        temp_file.write(schema_string)
        temp_file_path = temp_file.name

    try:
        # Build the command with output file
        if gql2json_cmd.startswith("node "):
            cmd = gql2json_cmd.split() + ["-o", str(output_path), temp_file_path]
        else:
            cmd = [gql2json_cmd, "-o", str(output_path), temp_file_path]

        # Run the command
        log.info(f"Running command: {' '.join(cmd)}")
        subprocess.run(cmd, capture_output=True, text=True, check=True)

        log.info(f"JSON Schema written to {output_path}")

    except subprocess.CalledProcessError as e:
        log.error(f"Command failed with return code {e.returncode}")
        log.error(f"Error output: {e.stderr}")
        raise RuntimeError("Failed to convert GraphQL schema to JSON Schema") from e

    finally:
        # Clean up the temporary file
        try:
            Path(temp_file_path).unlink()
        except OSError as e:
            log.warning(f"Failed to remove temporary file {temp_file_path}: {e}")


@click.command()
@click.argument("schema", type=click.Path(exists=True), required=True)
@click.argument(
    "output",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    required=True,
)
def main(schema: Path, output: Path) -> None:
    """Convert GraphQL schema to JSON Schema.

    This tool converts a GraphQL schema file to JSON Schema format
    using the s2dm-gql2jsonschema command-line tool.

    Args:
        schema: Path to the GraphQL schema file
        output: Path to write the JSON Schema output
    """
    try:
        # Convert to JSON Schema
        translate_to_jsonschema(schema, output)

    except Exception as e:
        log.error(f"Error converting GraphQL to JSON Schema: {e}")
        raise click.ClickException(str(e)) from e


if __name__ == "__main__":
    main()
