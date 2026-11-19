import tempfile
from pathlib import Path
from typing import cast

from s2dm.deps.models import DependencyEntry, ResolvedDependencySource
from s2dm.deps.resolve.common import METADATA_FILENAME
from s2dm.deps.resolve.errors import DependencyConfigError
from s2dm.deps.resolve.factory import ResolverFactory
from s2dm.deps.resolve.providers.factory import ReleaseProviderFactory
from s2dm.deps.resolve.resolvers.resolver import Resolver


def _require_asset_file_name(asset_name: str) -> None:
    """Reject a release asset name that is not a plain file name.

    Args:
        asset_name: The asset name from the request or the dependency config.

    Raises:
        DependencyConfigError: When the name holds a path separator, or is empty, ``.`` or ``..``.
    """
    has_separator = "/" in asset_name or "\\" in asset_name
    if has_separator or asset_name in {"", ".", ".."}:
        raise DependencyConfigError(f"Release asset name must be a file name: {asset_name}")


@ResolverFactory.register
class RemoteResolver(Resolver):
    """A resolver that resolves remote dependencies."""

    @classmethod
    def matches(cls, dependency: DependencyEntry) -> bool:
        return isinstance(dependency.source, str)

    def resolve(self, dependency: DependencyEntry) -> ResolvedDependencySource:
        """Resolve a dependency from a remote release source."""
        repository = cast(str, dependency.source)
        return self.resolve_release_asset(repository, dependency.version, dependency.artifact)

    def resolve_release_asset(self, repository: str, version: str, artifact: str) -> ResolvedDependencySource:
        """Download one release asset and resolve the schema and metadata it holds.

        Args:
            repository: The repository URL, ``https://<host>/<owner>/<repository>``.
            version: The release tag.
            artifact: The asset name: ``schema.graphql`` or a supported archive.

        Returns:
            The local schema and metadata paths, and the asset download URL.

        Raises:
            DependencyConfigError: When the asset name is not a plain file name.
        """
        _require_asset_file_name(artifact)
        provider = ReleaseProviderFactory.create_provider(repository, self.context)
        download_root = Path(tempfile.mkdtemp())
        asset_names = [artifact]
        if artifact.endswith(".graphql"):
            asset_names = [METADATA_FILENAME, artifact]
        asset_paths = provider.download_release_assets(repository, version, asset_names, download_root)
        artifact_url = provider.build_release_asset_url(repository, version, artifact)
        artifact_path = asset_paths[artifact]

        source = self._resolve_artifact(
            artifact_name=artifact,
            artifact_path=artifact_path,
        )
        return ResolvedDependencySource(source=source, resolved_path=artifact_url)
