import json
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
    ) -> dict[str, float | str | int | Any]:
        """Execute command with comprehensive logging"""
        if command in [InspectorCommands.DIFF, InspectorCommands.INTROSPECT, InspectorCommands.SIMILAR]:
            cmd = ["npm", "run", "graphql-inspect", "--", command.value, str(self.schema_path)] + [str(a) for a in args]
        elif command == InspectorCommands.VALIDATE:
            cmd = (
                ["npm", "run", "graphql-inspect", "--", command.value]
                + [str(a) for a in args]
                + [str(self.schema_path)]
            )
        else:
            raise ValueError(f"Unknown command: {command.value}")
        logging.debug(f"COMMAND: {' '.join(cmd)}")

        start_time = datetime.now()

        try:
            # Log the attempt
            logging.debug("Starting subprocess...")

            process = subprocess.Popen(  # ignore: type [type-arg]
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                **kwargs,
            )

            # logging.debug(f"Process started with PID: {process.pid}")

            # Capture output in real-time
            stdout_lines = []
            stderr_lines = []

            while True:
                if process.poll() is not None:
                    break

                # Read and log stdout
                if process.stdout:
                    stdout = process.stdout.read()
                    if stdout:
                        line = stdout.strip()
                        stdout_lines.append(line)
                        logging.debug(f"STDOUT: {line}")

                # Read and log stderr
                if process.stderr:
                    stderr = process.stderr.read()
                    if stderr:
                        line = stderr.strip()
                        stderr_lines.append(line)
                        logging.debug(f"STDERR: {line}")

            # Get any remaining output
            remaining_stdout, remaining_stderr = process.communicate()

            if remaining_stdout:
                for line in remaining_stdout.strip().split("\n"):
                    if line:
                        stdout_lines.append(line)
                        logging.debug(f"STDOUT: {line}")

            if remaining_stderr:
                for line in remaining_stderr.strip().split("\n"):
                    if line:
                        stderr_lines.append(line)
                        logging.debug(f"STDERR: {line}")

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            result = {
                "command": " ".join(cmd),
                "returncode": process.returncode,
                "stdout": "\n".join(stdout_lines),
                "stderr": "\n".join(stderr_lines),
                "duration": duration,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            }

            logging.debug(f"Process completed in {duration:.2f}s with return code: {process.returncode}")

            # Log the full result
            logging.debug(f"FULL_RESULT: {json.dumps(result, indent=2)}")

            return result

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logging.debug(f"Exception after {duration:.2f}s: {e}")
            logging.debug(f"Exception type: {type(e).__name__}")

            raise

    def validate(self, query: str) -> dict[str, Any]:
        """Validate schema with logging"""
        return self._run_command(InspectorCommands.VALIDATE, query)

    def diff(self, other_schema: Path) -> dict[str, Any]:
        """Compare schemas with logging"""
        return self._run_command(InspectorCommands.DIFF, str(other_schema))

    def introspect(self) -> dict[str, Any]:
        """Introspect schema."""
        return self._run_command(InspectorCommands.INTROSPECT)

    def similar(self) -> dict[str, Any]:
        """Similar table"""
        return self._run_command(InspectorCommands.SIMILAR)
