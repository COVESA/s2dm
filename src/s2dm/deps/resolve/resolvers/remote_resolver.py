import tempfile
from pathlib import Path
from typing import cast

from s2dm.deps.models import DependencyEntry, ResolvedDependencySource
from s2dm.deps.resolve.common import METADATA_FILENAME
from s2dm.deps.resolve.factory import ResolverFactory
from s2dm.deps.resolve.resolvers.resolver import Resolver
from s2dm.utils.download import download_url_to_path


@ResolverFactory.register
class RemoteResolver(Resolver):
    """A resolver that resolves remote dependencies."""

    @classmethod
    def matches(cls, dependency: DependencyEntry) -> bool:
        return isinstance(dependency.source, str)

    def resolve(self, dependency: DependencyEntry) -> ResolvedDependencySource:
        """Resolve a dependency from a remote release source."""
        repository = cast(str, dependency.source)
        download_root = Path(tempfile.mkdtemp())

        if dependency.artifact.endswith(".graphql"):
            metadata_url = self._build_release_asset_url(repository, dependency.version, METADATA_FILENAME)
            download_url_to_path(
                url=metadata_url,
                destination_path=download_root / METADATA_FILENAME,
                resource_label=f"dependency asset '{METADATA_FILENAME}'",
                overwrite=False,
            )

        artifact_url = self._build_release_asset_url(repository, dependency.version, dependency.artifact)
        artifact_path = download_url_to_path(
            url=artifact_url,
            destination_path=download_root / dependency.artifact,
            resource_label=f"dependency asset '{dependency.artifact}'",
            overwrite=False,
        )

        source = self._resolve_artifact(
            dependency=dependency,
            artifact_path=artifact_path,
        )
        return ResolvedDependencySource(source=source, resolved_path=artifact_url)

    def _build_release_asset_url(self, repository: str, version: str, asset_name: str) -> str:
        normalized_repository_url = repository.rstrip("/")
        return f"{normalized_repository_url}/releases/download/{version}/{asset_name}"
