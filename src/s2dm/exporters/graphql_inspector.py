import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from s2dm import log


class GraphQLInspector:
    def __init__(self, schema_path: Path, log_level=logging.INFO):
        self.schema_path = schema_path

    def _run_command(self, command: str, *args, **kwargs) -> dict:
        """Execute command with comprehensive logging"""
        cmd = ["graphql-inspector", command, self.schema_path] + list(args)

        log.debug(f"COMMAND: {' '.join(cmd)}")

        start_time = datetime.now()

        try:
            # Log the attempt
            log.debug("Starting subprocess...")

            process: subprocess.Popen = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                **kwargs,
            )

            log.debug(f"Process started with PID: {process.pid}")

            # Capture output in real-time
            stdout_lines = []
            stderr_lines = []

            while True:
                if process.poll() is not None:
                    break

                # Read and log stdout
                stdout_line = process.stdout.readline()
                if stdout_line:
                    line = stdout_line.strip()
                    stdout_lines.append(line)
                    log.debug(f"STDOUT: {line}")

                # Read and log stderr
                stderr_line = process.stderr.readline()
                if stderr_line:
                    line = stderr_line.strip()
                    stderr_lines.append(line)
                    log.debug(f"STDERR: {line}")

            # Get any remaining output
            remaining_stdout, remaining_stderr = process.communicate()

            if remaining_stdout:
                for line in remaining_stdout.strip().split("\n"):
                    if line:
                        stdout_lines.append(line)
                        log.debug(f"STDOUT: {line}")

            if remaining_stderr:
                for line in remaining_stderr.strip().split("\n"):
                    if line:
                        stderr_lines.append(line)
                        log.debug(f"STDERR: {line}")

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

            log.debug(f"Process completed in {duration:.2f}s with return code: {process.returncode}")

            # Log the full result
            log.debug(f"FULL_RESULT: {json.dumps(result, indent=2)}")

            return result

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            log.debug(f"Exception after {duration:.2f}s: {e}")
            log.debug(f"Exception type: {type(e).__name__}")

            raise

    def validate(self) -> dict:
        """Validate schema with logging"""
        log.info("Starting schema validation...")
        result = self._run_command("validate")

        if result["returncode"] == 0:
            log.info("✅ Schema validation PASSED")
        else:
            log.error("❌ Schema validation FAILED")

        return result

    def diff(self, other_schema: Path) -> dict:
        """Compare schemas with logging"""
        log.info(f"Comparing schemas: {self.schema_path} vs {other_schema}")
        result = self._run_command("diff", other_schema)

        if result["returncode"] == 0:
            log.info("✅ Schema comparison completed")
        else:
            log.error("❌ Schema comparison failed")

        return result
