import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from s2dm.deps.models import DependencyEntry, DependencySource, ResolvedDependencySource
from s2dm.deps.resolve.common import METADATA_FILENAME, SCHEMA_FILENAME
from s2dm.deps.resolve.extractors.factory import ExtractorFactory


class Resolver(ABC):
    """Base interface for dependency resolvers."""

    @classmethod
    @abstractmethod
    def matches(cls, dependency: DependencyEntry) -> bool:
        """Return whether this resolver supports the dependency."""

    @abstractmethod
    def resolve(self, dependency: DependencyEntry) -> ResolvedDependencySource:
        """Resolve the dependency."""

    def _resolve_artifact(
        self,
        dependency: DependencyEntry,
        artifact_path: Path,
    ) -> DependencySource:
        """Resolve the schema and metadata from an acquired artifact."""
        if self._is_direct_dependency(dependency):
            artifact_name = dependency.artifact
            if artifact_name != SCHEMA_FILENAME:
                raise ValueError(f"GraphQL file name mismatch. Should be: {SCHEMA_FILENAME}. Found: {artifact_name}")
            return self._resolve_direct_dependency(artifact_path)
        return self._resolve_bundled_dependency(artifact_path)


    def _is_direct_dependency(self, dependency: DependencyEntry) -> bool:
        artifact_name = dependency.artifact
        return artifact_name.endswith(".graphql") or artifact_name.endswith(".gql")
    
    def _resolve_direct_dependency(
        self,
        artifact_path: Path,
    ) -> DependencySource:
        metadata_path = artifact_path.parent / METADATA_FILENAME
        if not metadata_path.exists():
            raise ValueError(f"Dependency metadata file not found: {metadata_path}")
        if not metadata_path.is_file():
            raise ValueError(f"Dependency metadata path must be a file: {metadata_path}")
        
        return DependencySource(
            schema_path=artifact_path,
            metadata_path=metadata_path,
        )


    def _resolve_bundled_dependency(
        self,
        artifact_path: Path,
    ) -> DependencySource:
        extraction_directory = Path(tempfile.mkdtemp())
        self._extract_archive(artifact_path, extraction_directory)

        schema_path = extraction_directory / SCHEMA_FILENAME
        metadata_path = extraction_directory / METADATA_FILENAME
        
        self._require_file(schema_path, artifact_path.name)
        self._require_file(metadata_path, artifact_path.name)

        return DependencySource(
            schema_path=schema_path,
            metadata_path=metadata_path,
        )


    def _require_file(self, path: Path, archive_name: str) -> None:
        if not path.is_file():
            raise ValueError(f"Dependency archive '{archive_name}' must contain {path.name}")


    def _extract_archive(self, archive_path: Path, extraction_directory: Path) -> None:
        extractor = ExtractorFactory.create_extractor(archive_path)
        extractor.extract(archive_path, extraction_directory)
