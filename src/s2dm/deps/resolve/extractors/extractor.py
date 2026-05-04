from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar


class Extractor(ABC):
    """Base interface for dependency archive extractors."""

    file_formats: ClassVar[tuple[str, ...]]

    @abstractmethod
    def extract(self, archive_path: Path, extraction_directory: Path) -> None:
        """Extract the archive into the target directory."""
