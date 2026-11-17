from pathlib import Path
from typing import TypeVar

from s2dm.deps.resolve.errors import DependencyConfigError
from s2dm.deps.resolve.extractors.extractor import Extractor

ExtractorClass = TypeVar("ExtractorClass", bound=type[Extractor])


class ExtractorFactory:
    _registered_extractors: list[type[Extractor]] = []

    @classmethod
    def register(cls, extractor_class: ExtractorClass) -> ExtractorClass:
        if not issubclass(extractor_class, Extractor):
            raise TypeError(f"Extractor registration requires an Extractor subclass, got {extractor_class.__name__}")
        if extractor_class in cls._registered_extractors:
            raise ValueError(f"Extractor already registered: {extractor_class.__name__}")
        cls._registered_extractors.append(extractor_class)
        return extractor_class

    @classmethod
    def get_registered_extractors(cls) -> tuple[type[Extractor], ...]:
        return tuple(cls._registered_extractors)

    @classmethod
    def _find_extractor_class(cls, archive_name: str) -> type[Extractor] | None:
        """Return the registered extractor class that handles the archive name, or None."""
        extractor_classes = cls.get_registered_extractors()
        for extractor_class in extractor_classes:
            if archive_name.endswith(extractor_class.file_formats):
                return extractor_class
        return None

    @classmethod
    def supports(cls, archive_name: str) -> bool:
        """Return whether a registered extractor handles the archive name."""
        extractor_class = cls._find_extractor_class(archive_name)
        return extractor_class is not None

    @classmethod
    def create_extractor(cls, archive_path: Path) -> Extractor:
        """Create the matching extractor for the given archive path."""
        extractor_class = cls._find_extractor_class(archive_path.name)
        if extractor_class is None:
            raise DependencyConfigError(f"Unsupported dependency archive format: {archive_path.name}")
        return extractor_class()
