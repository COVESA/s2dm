from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

from s2dm.deps.models import ProviderRelease, ProviderReleasePage, ReleaseAsset
from s2dm.deps.models.github_release import GITHUB_RELEASE_LIST_ADAPTER, GitHubRelease, GitHubReleaseResponse
from s2dm.deps.resolve.errors import DependencyConfigError, DependencySourceError, DependencyUpstreamError
from s2dm.deps.resolve.providers.factory import ReleaseProviderFactory
from s2dm.deps.resolve.providers.release_provider import ReleaseProvider
from s2dm.utils.download import download_url_to_path

ACCESS_FAILURE_STATUS_CODES = frozenset({401, 403, 404})
API_VERSIONED_PATH = "api/v3"
ASSET_ACCEPT_HEADER_VALUE = "application/octet-stream"
GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_HOST_NAME = "github.com"
JSON_ACCEPT_HEADER_VALUE = "application/vnd.github+json"
RELEASES_BY_TAG_PATH = "repos/{owner}/{repository_name}/releases/tags/{version}"
RELEASES_PAGE_SIZE = 5
RELEASES_PATH = "repos/{owner}/{repository_name}/releases"


@dataclass(frozen=True)
class _ReleaseAssetDownloadContext:
    repository: str
    version: str
    download_root: Path
    token: str | None
    release_assets: dict[str, str] | None


@ReleaseProviderFactory.register
class GitHubReleaseProvider(ReleaseProvider):
    """Reads releases and release assets from GitHub and GitHub Enterprise."""

    @classmethod
    def matches(cls, repository: str) -> bool:
        """Return True. GitHub and GitHub Enterprise share one API, so this provider serves every host."""
        return True

    def build_release_asset_url(self, repository: str, version: str, asset_name: str) -> str:
        normalized_repository_url = repository.rstrip("/")
        return f"{normalized_repository_url}/releases/download/{version}/{asset_name}"

    def download_release_assets(
        self,
        repository: str,
        version: str,
        asset_names: list[str],
        download_root: Path,
    ) -> dict[str, Path]:
        """Download release assets into the download root.

        With an access token, the assets download through the API. Without one, they download
        from their public URLs.
        """
        token = self._resolve_token(repository)
        release_assets = None
        if token is not None:
            release = self._get_release(repository, version, token)
            release_assets = {asset.name: asset.url for asset in release.assets}

        download_context = _ReleaseAssetDownloadContext(
            repository=repository,
            version=version,
            download_root=download_root,
            token=token,
            release_assets=release_assets,
        )
        return {asset_name: self._download_asset(download_context, asset_name) for asset_name in asset_names}

    def get_release_page(self, repository: str, page: int) -> ProviderReleasePage:
        releases_url = self._build_repository_api_url(repository, RELEASES_PATH)
        token = self._resolve_token(repository)
        headers = self._build_json_headers(token)

        try:
            response = requests.get(
                releases_url,
                headers=headers,
                params={"per_page": RELEASES_PAGE_SIZE, "page": page},
                timeout=30,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise self._translate_release_list_error(error=error, repository=repository) from error

        releases_payload = response.json()
        github_releases = GITHUB_RELEASE_LIST_ADAPTER.validate_python(releases_payload)
        published_releases = [github_release for github_release in github_releases if not github_release.draft]
        releases = [self._build_provider_release(github_release) for github_release in published_releases]

        has_next = "next" in response.links
        last_page: int | None = None
        last_link = response.links.get("last")
        if last_link is not None:
            last_page = self._read_page_number(last_link["url"])
        if not has_next:
            last_page = page

        return ProviderReleasePage(
            releases=releases,
            page=page,
            has_next=has_next,
            has_previous="prev" in response.links,
            last_page=last_page,
        )

    def _build_provider_release(self, github_release: GitHubRelease) -> ProviderRelease:
        assets = [ReleaseAsset(name=asset.name, size=asset.size) for asset in github_release.assets]
        return ProviderRelease(
            tag=github_release.tag_name,
            name=github_release.name,
            published_at=github_release.published_at,
            prerelease=github_release.prerelease,
            assets=assets,
        )

    def _read_page_number(self, page_url: str) -> int:
        page_query = urlparse(page_url).query
        query_values = parse_qs(page_query)
        return int(query_values["page"][0])

    def _resolve_token(self, repository: str) -> str | None:
        if self.context is None or self.context.remote_identity_provider is None:
            return None

        return self.context.remote_identity_provider.resolve_token(repository)

    def _get_release(self, repository: str, version: str, token: str) -> GitHubReleaseResponse:
        release_url = self._build_repository_api_url(repository, RELEASES_BY_TAG_PATH, version=version)
        headers = self._build_json_headers(token)
        response = requests.get(release_url, headers=headers, timeout=30)
        try:
            response.raise_for_status()
        except requests.RequestException as error:
            raise self._translate_request_error(error=error, repository=repository, version=version) from error

        release_payload = response.json()
        return GitHubReleaseResponse.model_validate(release_payload)

    def _download_asset(self, download_context: _ReleaseAssetDownloadContext, asset_name: str) -> Path:
        destination_path = download_context.download_root / asset_name
        resource_label = f"dependency asset '{asset_name}'"

        if download_context.token is None or download_context.release_assets is None:
            asset_url = self.build_release_asset_url(download_context.repository, download_context.version, asset_name)
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

    def _build_repository_api_url(self, repository: str, path_template: str, **path_values: str) -> str:
        owner, repository_name = self._parse_repository_details(repository)
        repository_host = urlparse(repository).netloc
        api_base_url = self._build_api_base_url(repository_host)
        api_path = path_template.format(owner=owner, repository_name=repository_name, **path_values)
        return f"{api_base_url}/{api_path}"

    def _build_json_headers(self, token: str | None) -> dict[str, str]:
        headers = {"Accept": JSON_ACCEPT_HEADER_VALUE}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _build_api_base_url(self, repository_host: str) -> str:
        if repository_host.lower() == GITHUB_HOST_NAME:
            return GITHUB_API_BASE_URL
        return f"https://{repository_host}/{API_VERSIONED_PATH}"

    def _parse_repository_details(self, repository: str) -> tuple[str, str]:
        repository_path = urlparse(repository).path
        repository_scope = self._resolve_identity_scope(repository_path)
        if repository_scope is None:
            raise DependencyConfigError(f"Dependency repository URL must include owner and repository: {repository}")
        owner, repository_name = repository_scope.split("/", maxsplit=1)
        return owner, repository_name

    def _resolve_identity_scope(self, repository_path: str) -> str | None:
        path_segments = [path_segment for path_segment in repository_path.split("/") if path_segment]
        if len(path_segments) < 2:
            return None
        return "/".join(path_segments[:2])

    def _is_access_failure(self, error: requests.RequestException) -> bool:
        response = error.response
        return response is not None and response.status_code in ACCESS_FAILURE_STATUS_CODES

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
        if self._is_access_failure(error):
            return DependencySourceError(self._build_source_message(repository, version, asset_name=asset_name))
        return DependencyUpstreamError(self._build_upstream_message(repository, version, error, asset_name=asset_name))

    def _translate_release_list_error(
        self,
        error: requests.RequestException,
        repository: str,
    ) -> DependencySourceError | DependencyUpstreamError:
        if self._is_access_failure(error):
            source_message = self._build_release_list_source_message(repository)
            return DependencySourceError(source_message)
        upstream_message = self._build_release_list_upstream_message(repository, error)
        return DependencyUpstreamError(upstream_message)

    def _build_release_list_source_message(self, repository: str) -> str:
        return (
            f"Unable to access releases for '{repository}'. The repository may not exist or may require authentication."
        )

    def _build_release_list_upstream_message(self, repository: str, error: Exception) -> str:
        return f"Failed to load releases for '{repository}': {error}"

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
        return f"Failed to download dependency asset '{asset_name}' for '{repository}' version '{version}': {error}"

    def _build_resource_label(self, asset_name: str | None) -> str:
        if asset_name is None:
            return "dependency release metadata"
        return f"dependency asset '{asset_name}'"
