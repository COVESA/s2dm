from pathlib import Path
from typing import cast

from s2dm.deps.models import DependencyEntry, ResolvedDependencySource
from s2dm.deps.resolve.factory import ResolverFactory
from s2dm.deps.resolve.resolvers.resolver import Resolver


@ResolverFactory.register
class LocalResolver(Resolver):
    """A resolver that resolves local dependencies."""

    @classmethod
    def matches(cls, dependency: DependencyEntry) -> bool:
        return isinstance(dependency.source, Path)

    def resolve(self, dependency: DependencyEntry) -> ResolvedDependencySource:
        """Resolve a dependency from a local source directory."""
        source_directory = cast(Path, dependency.source)
        if not source_directory.exists():
            raise ValueError(f"Dependency source directory does not exist: {source_directory}")
        if not source_directory.is_dir():
            raise ValueError(f"Dependency source must be a directory: {source_directory}")
        
        artifact_path = source_directory / dependency.artifact
        if not artifact_path.exists():
            raise ValueError(f"Dependency artifact not found: {artifact_path}")
        if not artifact_path.is_file():
            raise ValueError(f"Dependency artifact must be a file: {artifact_path}")
        
        source = self._resolve_artifact(
            dependency=dependency,
            artifact_path=artifact_path,
        )
        return ResolvedDependencySource(
            source=source,
            resolved_path=str(artifact_path.absolute())
        )
