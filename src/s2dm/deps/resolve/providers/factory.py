from typing import TypeVar

from s2dm.deps.resolve.context import ResolverContext
from s2dm.deps.resolve.errors import DependencyConfigError
from s2dm.deps.resolve.providers.release_provider import ReleaseProvider

ReleaseProviderClass = TypeVar("ReleaseProviderClass", bound=type[ReleaseProvider])


class ReleaseProviderFactory:
    _registered_providers: list[type[ReleaseProvider]] = []

    @classmethod
    def register(cls, provider_class: ReleaseProviderClass) -> ReleaseProviderClass:
        if not issubclass(provider_class, ReleaseProvider):
            raise TypeError(
                f"Release provider registration requires a ReleaseProvider subclass, got {provider_class.__name__}"
            )
        if provider_class in cls._registered_providers:
            raise ValueError(f"Release provider already registered: {provider_class.__name__}")
        cls._registered_providers.append(provider_class)
        return provider_class

    @classmethod
    def get_registered_providers(cls) -> tuple[type[ReleaseProvider], ...]:
        return tuple(cls._registered_providers)

    @classmethod
    def create_provider(cls, repository: str, context: ResolverContext | None = None) -> ReleaseProvider:
        """Create the matching release provider for the given repository URL."""
        provider_classes = cls.get_registered_providers()
        for provider_class in provider_classes:
            if provider_class.matches(repository):
                return provider_class(context)

        raise DependencyConfigError(f"Unsupported release repository: {repository}")
