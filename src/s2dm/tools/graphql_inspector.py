import json
import subprocess
from enum import Enum
from pathlib import Path
from typing import Any

from s2dm import log
from s2dm.tools.diff_parser import DiffChange, parse_diff_output


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
    def __init__(self, schema_path: Path) -> None:
        self.schema_path = schema_path

    def _run_command(
        self: "GraphQLInspector",
        command: InspectorCommands,
        *args: Any,
        **kwargs: Any,
    ) -> InspectorOutput:
        """Execute command with comprehensive logging and improved error handling"""
        if command in [InspectorCommands.DIFF, InspectorCommands.INTROSPECT, InspectorCommands.SIMILAR]:
            cmd = ["graphql-inspector", command.value, str(self.schema_path)] + [str(a) for a in args]
        elif command == InspectorCommands.VALIDATE:
            cmd = ["graphql-inspector", command.value] + [str(a) for a in args] + [str(self.schema_path)]
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

        This method uses the custom graphql_inspector_diff.js script to get
        structured JSON output instead of text output from the CLI.

        Args:
            other_schema: Path to the schema to compare against

        Returns:
            List of DiffChange instances with structured diff information

        Raises:
            RuntimeError: If the Node.js script fails or returns invalid output
        """
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

        # Find project root (go up from src/s2dm/tools to project root)
        project_root = script_dir.parent.parent.parent

        log.info(f"Running structured diff: {' '.join(node_cmd)}")

        # Run from project root to ensure node_modules can be found
        result = subprocess.run(
            node_cmd,
            capture_output=True,
            text=True,
            check=False,  # Don't raise exception for non-zero exit codes
            cwd=str(project_root),  # Run from project root for module resolution
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
