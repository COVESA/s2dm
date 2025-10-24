"""Unified logging system for S2DM with CLI output support."""

import json
import logging
from typing import Any

from rich.console import Console
from rich.logging import RichHandler


class S2DMLogger(logging.Logger):
    """
    Enhanced logger that combines Python logging with CLI formatting methods.

    Provides both standard logging levels (debug, info, warning, error, critical)
    and semantic CLI output methods (success, highlight, key_value, etc.).
    """

    def __init__(self, name: str, level: int = logging.INFO) -> None:
        """
        Initialize the S2DM logger.

        Args:
            name: Logger name
            level: Initial log level
        """
        super().__init__(name, level)
        self.console = Console()

        # Add RichHandler for colored console output
        handler = RichHandler(
            console=self.console,
            rich_tracebacks=True,
            show_time=True,
            show_path=False,
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.addHandler(handler)

    def print(self, message: str) -> None:
        """
        Print a plain message (with Rich markup support).

        Args:
            message: Message to display
        """
        self.console.print(message)

    def colored(self, message: str, style: str = "bold cyan") -> None:
        """
        Print a message with a specific style/color.

        Args:
            message: Message to display
            style: Rich style string (e.g., "green", "red", "bold cyan", "dim")
        """
        self.print(f"[{style}]{message}[/{style}]")

    def success(self, message: str) -> None:
        """
        Print a success message in green with checkmark icon.

        This is the only special display method - use standard logging methods
        (info, warning, error) for everything else.

        Args:
            message: Message to display
        """
        self.print(f"[green]✓[/green] {message}")

    def hint(self, message: str) -> None:
        """
        Print a dimmed hint/secondary message.

        Args:
            message: Message to display
        """
        self.colored(message, "dim")

    def rule(self, title: str, style: str = "bold blue") -> None:
        """
        Print a horizontal rule with a title.

        The name 'rule' comes from Rich's console.rule() method, which draws
        a horizontal separator line with an optional title.

        Args:
            title: Title text for the rule
            style: Rich style string (default: "bold blue")
        """
        self.console.rule(f"[{style}]{title}")

    def print_dict(self, data: dict[str, Any]) -> None:
        """
        Print dictionary data with syntax highlighting.

        The dictionary is converted to a JSON string and then printed with syntax highlighting.

        Args:
            data: Dictionary to display
        """
        self.console.print_json(json.dumps(data, indent=2))

    def key_value(self, key: str, value: Any, key_style: str = "dim") -> None:
        """
        Print a formatted key-value pair.

        Useful for displaying structured data like "Property: value".

        Args:
            key: The key/label to display
            value: The value to display
            key_style: Style for the key (default: "dim")
        """
        self.print(f"[{key_style}]{key}:[/{key_style}] {value}")

    def list_item(self, text: str, prefix: str = "-", style: str = "") -> None:
        """
        Print a list item with optional styling.

        Args:
            text: Text to display
            prefix: Prefix character (default: "-")
            style: Optional style for the entire item
        """
        if style:
            self.colored(f"{prefix} {text}", style)
        else:
            self.print(f"{prefix} {text}")


def get_logger(name: str = "s2dm") -> S2DMLogger:
    """
    Get or create an S2DM logger instance.

    Args:
        name: Logger name (default: "s2dm")

    Returns:
        S2DMLogger instance
    """
    # Set custom logger class
    logging.setLoggerClass(S2DMLogger)
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        if isinstance(logger, S2DMLogger):
            pass  # Already initialized in __init__
        else:
            # Convert to S2DMLogger if needed
            logging.setLoggerClass(S2DMLogger)
            logger = logging.getLogger(name)

    return logger  # type: ignore[return-value]
