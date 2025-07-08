import subprocess
from enum import Enum
from pathlib import Path
from typing import Any

from s2dm import log


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
