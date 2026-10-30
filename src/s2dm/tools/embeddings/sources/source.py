"""The interface every embedding model source implements."""

from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel

from s2dm.tools.embeddings.model_spec import ModelSourceReference


class ModelFiles(BaseModel):
    """The files to download for a model, as model-relative paths.

    ``required`` are files the model cannot run without; ``optional`` are files that some models do not publish.
    """

    required: list[str]
    optional: list[str] = []


class ModelSource(ABC):
    """Base interface for embedding model sources."""

    def __init__(self, reference: ModelSourceReference, cache_root: Path) -> None:
        self.reference = reference
        self.cache_root = cache_root

    @classmethod
    @abstractmethod
    def matches(cls, reference: ModelSourceReference) -> bool:
        """Tell whether this source serves a reference.

        Args:
            reference: The model's source reference.

        Returns:
            Whether this source can download the referenced model.
        """

    @abstractmethod
    def download(self, files: ModelFiles) -> Path:
        """Put the model's files into a local folder, reusing files already there.

        Args:
            files: The files to download; absent optional files are skipped.

        Returns:
            The folder holding the files under their model-relative paths.

        Raises:
            ModelResolutionError: When a required file is absent or any download fails.
        """
