import logging
import subprocess
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class InspectorCommands(Enum):
    DIFF = "diff"
    VALIDATE = "validate"
    INTROSPECT = "introspect"
    SIMILAR = "similar"


class GraphQLInspector:
    def __init__(self, schema_path: Path) -> None:
        self.schema_path = schema_path

    def _run_command(
        self: "GraphQLInspector",
        command: InspectorCommands,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute command with comprehensive logging and improved error handling"""
        if command in [InspectorCommands.DIFF, InspectorCommands.INTROSPECT, InspectorCommands.SIMILAR]:
            cmd = ["graphql-inspector", command.value, str(self.schema_path)] + [str(a) for a in args]
        elif command == InspectorCommands.VALIDATE:
            cmd = ["graphql-inspector", command.value] + [str(a) for a in args] + [str(self.schema_path)]
        else:
            raise ValueError(f"Unknown command: {command.value}")

        logging.info(f"Running command: {' '.join(cmd)}")
        start_time = datetime.now()
        output: dict[str, Any] = {
            "command": " ".join(cmd),
            "start_time": start_time.isoformat(),
        }
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            **kwargs,
        )
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        stdout = result.stdout.strip() if result.stdout else ""
        stderr = result.stderr.strip() if result.stderr else ""

        if stdout:
            for line in stdout.split("\n"):
                logging.debug(f"STDOUT: {line}")
        if stderr:
            for line in stderr.split("\n"):
                logging.debug(f"STDERR: {line}")
        output["returncode"] = result.returncode
        output["stdout"] = stdout
        output["stderr"] = stderr
        output["duration"] = duration
        output["end_time"] = end_time.isoformat()
        if result.returncode != 0:
            logging.warning(f"Command failed with return code {result.returncode}")
        logging.info(f"Process completed in {duration:.2f}s with return code: {result.returncode}")

        return output

    def validate(self, query: str) -> dict[str, Any]:
        """Validate schema with logging"""
        return self._run_command(InspectorCommands.VALIDATE, query)

    def diff(self, other_schema: Path) -> dict[str, Any]:
        """Compare schemas with logging"""
        return self._run_command(InspectorCommands.DIFF, str(other_schema))

    def introspect(self, output: Path) -> dict[str, Any]:
        """Introspect schema."""
        return self._run_command(InspectorCommands.INTROSPECT, "--write", output)

    def similar(self, output: Path | None) -> dict[str, Any]:
        """Similar table"""
        if output:
            return self._run_command(InspectorCommands.SIMILAR, "--write", output)
        else:
            return self._run_command(InspectorCommands.SIMILAR)

    def similar_keyword(self, keyword: str, output: Path | None) -> dict[str, Any]:
        """Search single type in schema"""
        if output:
            return self._run_command(InspectorCommands.SIMILAR, "-n", keyword, "--write", output)
        else:
            return self._run_command(InspectorCommands.SIMILAR, "-n", keyword)
