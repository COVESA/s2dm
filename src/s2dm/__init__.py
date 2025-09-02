import logging

from rich.logging import RichHandler

__author__ = """Daniel Alvarez-Coello"""
__email__ = "8550265+jdacoello@users.noreply.github.com"
__version__ = "0.6.2"

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)

log = logging.getLogger("s2dm")
