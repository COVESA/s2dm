from abc import ABC, abstractmethod
from pathlib import Path

from s2dm.deps.models import ProviderReleasePage
from s2dm.deps.resolve.context import ResolverContext


class ReleaseProvider(ABC):
    """Base interface for the hosts that publish remote releases."""

    def __init__(self, context: ResolverContext | None = None) -> None:
        self.context = context

    @classmethod
    @abstractmethod
    def matches(cls, repository: str) -> bool:
        """Return whether this provider serves the repository URL."""

    @abstractmethod
    def build_release_asset_url(self, repository: str, version: str, asset_name: str) -> str:
        """Return the public download URL of a release asset."""

    @abstractmethod
    def download_release_assets(
        self,
        repository: str,
        version: str,
        asset_names: list[str],
        download_root: Path,
    ) -> dict[str, Path]:
        """Download release assets into the download root.

        Args:
            repository: The repository URL.
            version: The release tag.
            asset_names: The asset names, in download order.
            download_root: The directory that receives the assets.

        Returns:
            The path of each downloaded asset, keyed by asset name.

        Raises:
            DependencyConfigError: When the repository URL is not usable.
            DependencySourceError: When the release or an asset does not exist or needs other credentials.
            DependencyUpstreamError: When the provider fails in any other way.
        """

    @abstractmethod
    def get_release_page(self, repository: str, page: int) -> ProviderReleasePage:
        """Load one page of the published releases of a repository.

        Args:
            repository: The repository URL.
            page: The page number, starting at 1.

        Returns:
            The published releases on the page, without drafts, and the paging state.

        Raises:
            DependencyConfigError: When the repository URL is not usable.
            DependencySourceError: When the repository does not exist or needs other credentials.
            DependencyUpstreamError: When the provider fails in any other way.
        """
