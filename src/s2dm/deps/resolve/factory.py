from typing import TypeVar

from s2dm.deps.models import DependencyEntry
from s2dm.deps.resolve.resolvers.resolver import Resolver

ResolverClass = TypeVar("ResolverClass", bound=type[Resolver])


class ResolverFactory:
    _registered_resolvers: list[type[Resolver]] = []

    @classmethod
    def register(cls, resolver_class: ResolverClass) -> ResolverClass:
        if not issubclass(resolver_class, Resolver):
            raise TypeError(f"Resolver registration requires a Resolver subclass, got {resolver_class.__name__}")
        if resolver_class in cls._registered_resolvers:
            raise ValueError(f"Resolver already registered: {resolver_class.__name__}")
        cls._registered_resolvers.append(resolver_class)
        return resolver_class
    
    @classmethod
    def get_registered_resolvers(cls) -> tuple[type[Resolver], ...]:
        return tuple(cls._registered_resolvers)
    
    @classmethod
    def create_resolver(cls, dependency: DependencyEntry) -> Resolver:
        """Create the matching resolver for the given dependency."""
        resolver_classes = cls.get_registered_resolvers()
        for resolver_class in resolver_classes:
            if resolver_class.matches(dependency):
                return resolver_class()

        raise ValueError(f"Unsupported dependency source: {dependency.source}")
