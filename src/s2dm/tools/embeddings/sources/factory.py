from pathlib import Path
from typing import TypeVar

from s2dm.tools.embeddings.errors import ModelResolutionError
from s2dm.tools.embeddings.model_spec import ModelSourceReference
from s2dm.tools.embeddings.sources.source import ModelSource

ModelSourceClass = TypeVar("ModelSourceClass", bound=type[ModelSource])


class ModelSourceFactory:
    _registered_sources: list[type[ModelSource]] = []

    @classmethod
    def register(cls, source_class: ModelSourceClass) -> ModelSourceClass:
        if not issubclass(source_class, ModelSource):
            raise TypeError(f"Model source registration requires a ModelSource subclass, got {source_class.__name__}")

        if source_class in cls._registered_sources:
            raise ValueError(f"Model source already registered: {source_class.__name__}")

        cls._registered_sources.append(source_class)
        return source_class

    @classmethod
    def get_registered_sources(cls) -> tuple[type[ModelSource], ...]:
        return tuple(cls._registered_sources)

    @classmethod
    def create_source(cls, reference: ModelSourceReference, cache_root: Path) -> ModelSource:
        """Create the registered source that serves a reference.

        Args:
            reference: The model's source reference.
            cache_root: Root folder of the model cache.

        Returns:
            The first registered source whose ``matches`` accepts the reference.

        Raises:
            ModelResolutionError: When no registered source serves the reference.
        """
        source_classes = cls.get_registered_sources()

        for source_class in source_classes:
            if source_class.matches(reference):
                return source_class(reference, cache_root)

        raise ModelResolutionError(f"Unsupported model source: {reference.kind}")
