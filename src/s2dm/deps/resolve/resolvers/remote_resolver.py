import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, ConfigDict

from s2dm.deps.models import DependencyEntry, ResolvedDependencySource
from s2dm.deps.resolve.common import METADATA_FILENAME
from s2dm.deps.resolve.errors import DependencyConfigError, DependencySourceError, DependencyUpstreamError
from s2dm.deps.resolve.factory import ResolverFactory
from s2dm.deps.resolve.resolvers.resolver import Resolver
from s2dm.utils.download import download_url_to_path

API_VERSIONED_PATH = "api/v3"
ASSET_ACCEPT_HEADER_VALUE = "application/octet-stream"
GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_HOST_NAME = "github.com"
JSON_ACCEPT_HEADER_VALUE = "application/vnd.github+json"
RELEASES_BY_TAG_PATH = "repos/{owner}/{repository_name}/releases/tags/{version}"


class _GitHubReleaseAsset(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    url: str


class _GitHubReleaseResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    assets: list[_GitHubReleaseAsset]


@dataclass(frozen=True)
class _ReleaseAssetDownloadContext:
    repository: str
    version: str
    download_root: Path
    token: str | None
    release_assets: dict[str, str] | None


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
        token = self._resolve_identity_token(repository)
        release_assets = None

        if token is not None:
            release_assets = self._load_release_assets(repository, dependency.version, token)

        download_context = _ReleaseAssetDownloadContext(
            repository=repository,
            version=dependency.version,
            download_root=download_root,
            token=token,
            release_assets=release_assets,
        )

        if dependency.artifact.endswith(".graphql"):
            self._download_release_asset(
                download_context=download_context,
                asset_name=METADATA_FILENAME,
            )

        artifact_url = self._build_release_asset_url(repository, dependency.version, dependency.artifact)
        artifact_path = self._download_release_asset(
            download_context=download_context,
            asset_name=dependency.artifact,
        )

        source = self._resolve_artifact(
            dependency=dependency,
            artifact_path=artifact_path,
        )
        return ResolvedDependencySource(source=source, resolved_path=artifact_url)

    def _build_release_asset_url(self, repository: str, version: str, asset_name: str) -> str:
        normalized_repository_url = repository.rstrip("/")
        return f"{normalized_repository_url}/releases/download/{version}/{asset_name}"

    def _load_release_assets(self, repository: str, version: str, token: str) -> dict[str, str]:
        owner, repository_name = self._parse_repository_details(repository)
        repository_host = urlparse(repository).netloc
        api_base_url = self._build_api_base_url(repository_host)
        release_path = RELEASES_BY_TAG_PATH.format(
            owner=owner,
            repository_name=repository_name,
            version=version,
        )
        release_url = f"{api_base_url}/{release_path}"
        response = requests.get(
            release_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": JSON_ACCEPT_HEADER_VALUE,
            },
            timeout=30,
        )
        try:
            response.raise_for_status()
        except requests.RequestException as error:
            raise self._translate_request_error(error=error, repository=repository, version=version) from error

        release_payload = response.json()
        release = _GitHubReleaseResponse.model_validate(release_payload)
        return {asset.name: asset.url for asset in release.assets}

    def _download_release_asset(
        self,
        download_context: _ReleaseAssetDownloadContext,
        asset_name: str,
    ) -> Path:
        destination_path = download_context.download_root / asset_name
        resource_label = f"dependency asset '{asset_name}'"

        if download_context.token is None or download_context.release_assets is None:
            asset_url = self._build_release_asset_url(download_context.repository, download_context.version, asset_name)
            try:
                return download_url_to_path(
                    url=asset_url,
                    destination_path=destination_path,
                    resource_label=resource_label,
                    overwrite=False,
                )
            except RuntimeError as error:
                raise self._translate_download_error(
                    error=error,
                    repository=download_context.repository,
                    version=download_context.version,
                    asset_name=asset_name,
                ) from error

        asset_api_url = download_context.release_assets.get(asset_name)
        if asset_api_url is None:
            raise DependencySourceError(f"Dependency release asset not found: {asset_name}")

        try:
            return download_url_to_path(
                url=asset_api_url,
                destination_path=destination_path,
                resource_label=resource_label,
                overwrite=False,
                headers={
                    "Authorization": f"Bearer {download_context.token}",
                    "Accept": ASSET_ACCEPT_HEADER_VALUE,
                },
            )
        except RuntimeError as error:
            raise self._translate_download_error(
                error=error,
                repository=download_context.repository,
                version=download_context.version,
                asset_name=asset_name,
            ) from error

    def _build_api_base_url(self, repository_host: str) -> str:
        if repository_host.lower() == GITHUB_HOST_NAME:
            return GITHUB_API_BASE_URL
        return f"https://{repository_host}/{API_VERSIONED_PATH}"

    def _parse_repository_details(self, repository: str) -> tuple[str, str]:
        repository_scope = self._resolve_identity_scope(urlparse(repository).path)
        if repository_scope is None:
            raise DependencyConfigError(f"Dependency repository URL must include owner and repository: {repository}")
        owner, repository_name = repository_scope.split("/", maxsplit=1)
        return owner, repository_name

    def _translate_download_error(
        self,
        error: RuntimeError,
        repository: str,
        version: str,
        asset_name: str,
    ) -> DependencySourceError | DependencyUpstreamError:
        cause = error.__cause__
        if isinstance(cause, requests.RequestException):
            return self._translate_request_error(
                error=cause,
                repository=repository,
                version=version,
                asset_name=asset_name,
            )
        return DependencyUpstreamError(self._build_upstream_message(repository, version, error, asset_name=asset_name))

    def _translate_request_error(
        self,
        error: requests.RequestException,
        repository: str,
        version: str,
        asset_name: str | None = None,
    ) -> DependencySourceError | DependencyUpstreamError:
        response = error.response
        if response is not None and response.status_code in {401, 403, 404}:
            return DependencySourceError(self._build_source_message(repository, version, asset_name=asset_name))
        return DependencyUpstreamError(self._build_upstream_message(repository, version, error, asset_name=asset_name))

    def _build_source_message(self, repository: str, version: str, asset_name: str | None = None) -> str:
        resource_label = self._build_resource_label(asset_name)
        return (
            f"Unable to access {resource_label} for '{repository}' version '{version}'. "
            "The dependency may not exist or may require authentication."
        )

    def _build_upstream_message(
        self,
        repository: str,
        version: str,
        error: Exception,
        asset_name: str | None = None,
    ) -> str:
        if asset_name is None:
            return f"Failed to load dependency release metadata for '{repository}' version '{version}': {error}"
        return f"Failed to download dependency asset '{asset_name}' for '{repository}' " f"version '{version}': {error}"

    def _build_resource_label(self, asset_name: str | None) -> str:
        if asset_name is None:
            return "dependency release metadata"
        return f"dependency asset '{asset_name}'"

    def _resolve_identity_token(self, repository: str) -> str | None:
        if self.context is None or self.context.remote_identity_provider is None:
            return None

        return self.context.remote_identity_provider.resolve_token(repository)

    def _resolve_identity_scope(self, repository_path: str) -> str | None:
        path_segments = [path_segment for path_segment in repository_path.split("/") if path_segment]
        if len(path_segments) < 2:
            return None
        return "/".join(path_segments[:2])
