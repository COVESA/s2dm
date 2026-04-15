"""GraphQL Inspector Python wrapper.

This module provides a Python interface to the @graphql-inspector/cli Node.js tool
for GraphQL schema analysis, validation, and comparison.

The decorator pattern automatically locates the GraphQL Inspector installation and injects
it to CLI commands, eliminating the need for global state or repeated lookups.

Example:
    @requires_graphql_inspector
    def my_command(..., inspector_path: Path | None = None) -> None:
        inspector = GraphQLInspector(schema_path, node_modules_path=inspector_path)
        result = inspector.diff(other_schema)
"""

import json
import shutil
import subprocess
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from typing import Any

from s2dm import log
from s2dm.tools.diff_parser import DiffChange, parse_diff_output


def locate_graphql_inspector(node_modules_path: Path | None = None, start_path: Path | None = None) -> Path | None:
    """Locate the GraphQL Inspector installation by finding the node_modules directory.

    If an explicit node_modules_path is provided (e.g. via --node-modules-path in CI),
    it is used directly. Otherwise, searches upward from the start path for a
    node_modules directory.

    Args:
        node_modules_path: Explicit path to a node_modules directory. Takes priority
            over directory-tree search when provided.
        start_path: Path to start searching from (defaults to current working directory)

    Returns:
        Path to node_modules directory where graphql-inspector is installed, or None if not found
    """
    if node_modules_path is not None:
        node_modules = Path(node_modules_path)
        if node_modules.exists() and node_modules.is_dir():
            return node_modules

    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()

    # Walk up the directory tree looking for node_modules
    for parent in [current, *current.parents]:
        node_modules = parent / "node_modules"
        if node_modules.exists() and node_modules.is_dir():
            return node_modules

    return None


def requires_graphql_inspector(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that resolves the graphql-inspector path and injects it as inspector_path.

    This decorator:
    - Reads the node_modules_path kwarg (provided by the node_modules_path_option click option)
    - Locates the graphql-inspector installation (using the explicit path if given,
      otherwise searching upward from cwd)
    - Injects the result as 'inspector_path' parameter to the wrapped function

    The wrapped function must accept an 'inspector_path: Path | None' parameter.
    Commands using this decorator should also apply @node_modules_path_option.
    """

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        node_modules_path = kwargs.pop("node_modules_path", None)
        inspector_path = locate_graphql_inspector(node_modules_path=node_modules_path)
        kwargs["inspector_path"] = inspector_path
        return func(*args, **kwargs)

    # Preserve the original function's metadata for click
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


def _check_node_dependencies(node_modules_path: Path) -> bool:
    """Check if required Node.js dependencies are installed by attempting to require them.

    This is more reliable than checking file existence as it verifies the actual
    runtime environment and catches issues like broken installations.

    Args:
        node_modules_path: Path to the node_modules directory

    Returns:
        True if all required dependencies can be loaded, False otherwise
    """

    # Check if node is available
    if not shutil.which("node"):
        return False

    # Try to require the modules to verify they're installed and accessible
    # Run from node_modules parent to ensure node_modules can be resolved
    try:
        result = subprocess.run(
            [
                "node",
                "-e",
                "require('@graphql-inspector/core'); require('graphql');",
            ],
            cwd=str(node_modules_path.parent),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


class InspectorCommands(Enum):
    DIFF = "diff"
    VALIDATE = "validate"
    INTROSPECT = "introspect"
    SIMILAR = "similar"


class InspectorOutput:
    def __init__(
        self,
        command: str,
        returncode: int,
        output: str,
    ):
        self.command = command
        self.returncode = returncode
        self.output = output

    def as_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "returncode": self.returncode,
            "output": self.output,
        }


class GraphQLInspector:
    def __init__(self, schema_path: Path, node_modules_path: Path | None = None) -> None:
        """Initialize GraphQL Inspector.

        Args:
            schema_path: Path to the GraphQL schema file
            node_modules_path: Path to node_modules directory (for finding local binaries).
                              Optional - if None, will only use globally installed CLI.

        Raises:
            RuntimeError: If graphql-inspector CLI is not found
        """
        self.schema_path = schema_path
        self.node_modules_path = node_modules_path

        # Resolve CLI path once during initialization
        self.cli_cmd = self._resolve_cli_path()

    def _resolve_cli_path(self) -> str:
        """Resolve the graphql-inspector CLI path.

        Returns:
            Path to the graphql-inspector CLI command

        Raises:
            RuntimeError: If graphql-inspector CLI is not found
        """
        # Try local installation first if node_modules_path is provided
        if self.node_modules_path:
            local_cli_path = self.node_modules_path / ".bin" / "graphql-inspector"
            if local_cli_path.exists():
                return str(local_cli_path)

        # Fall back to global installation
        if shutil.which("graphql-inspector"):
            return "graphql-inspector"

        # Not found - provide helpful error message
        raise RuntimeError(
            "graphql-inspector CLI not found. Please run 'npm install' in the project root "
            "to install @graphql-inspector/cli, or install it globally with "
            "'npm install -g @graphql-inspector/cli'."
        )

    def _run_command(
        self: "GraphQLInspector",
        command: InspectorCommands,
        *args: Any,
        **kwargs: Any,
    ) -> InspectorOutput:
        """Execute command with comprehensive logging and improved error handling.

        Args:
            command: The inspector command to run
            *args: Additional command arguments
            **kwargs: Additional subprocess arguments

        Returns:
            InspectorOutput containing command results
        """
        # Build command using the pre-resolved CLI path
        if command in [InspectorCommands.DIFF, InspectorCommands.INTROSPECT, InspectorCommands.SIMILAR]:
            cmd = [self.cli_cmd, command.value, str(self.schema_path)] + [str(a) for a in args]
        elif command == InspectorCommands.VALIDATE:
            cmd = [self.cli_cmd, command.value] + [str(a) for a in args] + [str(self.schema_path)]
        else:
            raise ValueError(f"Unknown command: {command.value}")

        log.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            **kwargs,
        )
        stdout = result.stdout.strip() if result.stdout else ""
        stderr = result.stderr.strip() if result.stderr else ""
        output = stdout
        if stderr:
            if output:
                output += "\n" + stderr
            else:
                output = stderr

        if output:
            log.debug(f"OUTPUT:\n{output}")
        if result.returncode != 0:
            log.warning(f"Command failed with return code {result.returncode}")
        log.info(f"Process completed with return code: {result.returncode}")

        return InspectorOutput(
            command=" ".join(cmd),
            returncode=result.returncode,
            output=output,
        )

    def validate(self, query: str) -> InspectorOutput:
        """Validate schema with logging"""
        return self._run_command(InspectorCommands.VALIDATE, query)

    def diff(self, other_schema: Path) -> InspectorOutput:
        """Compare schemas with logging"""
        return self._run_command(InspectorCommands.DIFF, str(other_schema))

    def introspect(self, output: Path) -> InspectorOutput:
        """Introspect schema."""
        return self._run_command(InspectorCommands.INTROSPECT, "--write", output)

    def similar(self, output: Path | None) -> InspectorOutput:
        """Similar table"""
        if output:
            return self._run_command(InspectorCommands.SIMILAR, "--write", output)
        else:
            return self._run_command(InspectorCommands.SIMILAR)

    def similar_keyword(self, keyword: str, output: Path | None) -> InspectorOutput:
        """Search single type in schema"""
        if output:
            return self._run_command(InspectorCommands.SIMILAR, "-n", keyword, "--write", output)
        else:
            return self._run_command(InspectorCommands.SIMILAR, "-n", keyword)

    def diff_structured(self, other_schema: Path) -> list[DiffChange]:
        """Compare schemas using custom Node.js script and return structured diff changes.

        This method uses a custom Node.js script that directly requires the npm packages
        (@graphql-inspector/core and graphql) to get structured JSON output.

        Note: Unlike other methods that use the CLI binary, this requires the actual npm
        packages to be installed locally.

        Args:
            other_schema: Path to the schema to compare against

        Returns:
            List of DiffChange instances with structured diff information

        Raises:
            RuntimeError: If node_modules_path wasn't provided, npm packages aren't installed,
                         or the Node.js script fails
        """
        # Ensure node_modules_path was provided (required for npm package resolution)
        if not self.node_modules_path:
            raise RuntimeError(
                "diff_structured requires node_modules_path. Please ensure npm packages are installed "
                "in the project root and provide the path during initialization."
            )

        # Verify the npm packages are installed (not just the CLI binary)
        if not _check_node_dependencies(self.node_modules_path):
            raise RuntimeError(
                "Required npm packages (@graphql-inspector/core, graphql) not found. "
                "Please run 'npm install' in the project root."
            )

        # Find the Node.js script relative to this file
        script_dir = Path(__file__).parent
        node_script_path = script_dir / "graphql_inspector_diff.js"

        if not node_script_path.exists():
            raise RuntimeError(f"Node.js script not found at {node_script_path}")

        # Use absolute paths for script and schema files
        node_cmd = [
            "node",
            str(node_script_path.absolute()),
            str(self.schema_path.absolute()),
            str(other_schema.absolute()),
        ]

        log.info(f"Running structured diff: {' '.join(node_cmd)}")

        # Run from node_modules parent to ensure node_modules can be found
        result = subprocess.run(
            node_cmd,
            capture_output=True,
            text=True,
            check=False,  # Don't raise exception for non-zero exit codes
            cwd=str(self.node_modules_path.parent),  # Run from node_modules parent for module resolution
        )

        # Exit code 1 is OK - it means breaking changes were detected
        # Exit code 2 means an error occurred
        if result.returncode == 2:
            base_error_msg = "Node.js script encountered an error (exit code 2)"
            # Try to parse stderr as JSON (error output from script) for better error message
            if result.stderr:
                try:
                    error_json = json.loads(result.stderr)
                    base_error_msg = f"{base_error_msg}: {error_json.get('error', 'Unknown error')}"
                    # If JSON parsing succeeded, we already have the error message,
                    # so don't append stderr again (format_error_with_stderr will log it at debug)
                except json.JSONDecodeError:
                    # Non-JSON error output - format_error_with_stderr will append it
                    pass
            error_msg = log.format_error_with_stderr(base_error_msg, result.stderr)
            raise RuntimeError(error_msg)

        output_text = result.stdout.strip()
        if not output_text:
            error_msg = log.format_error_with_stderr(
                "graphql_inspector_diff.js script returned empty output", result.stderr
            )
            raise RuntimeError(error_msg)

        try:
            # Parse JSON output from Node.js script
            diff_output = parse_diff_output(raw_output=output_text)
            log.info("Successfully obtained structured diff from Node.js script")
            return diff_output
        except (json.JSONDecodeError, ValueError) as e:
            error_msg = log.format_error_with_stderr(f"Failed to parse Node.js script output: {e}", result.stderr)
            raise RuntimeError(error_msg) from e
