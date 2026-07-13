from collections.abc import MutableSequence
from typing import Protocol

from s2dm import log


class WarningCollector(Protocol):
    """Collector for dependency-resolution warnings."""

    def warn(self, message: str) -> None:
        """Handle a warning message."""


class LoggingWarningCollector:
    """Warning collector that forwards messages to the application logger."""

    def warn(self, message: str) -> None:
        log.warning(message)


class ListWarningCollector:
    """Warning collector that appends messages to a mutable sequence."""

    def __init__(self, warnings: MutableSequence[str]) -> None:
        self.warnings = warnings

    def warn(self, message: str) -> None:
        self.warnings.append(message)
