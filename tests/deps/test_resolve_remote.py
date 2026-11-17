import tarfile
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests
import yaml

from s2dm.deps.models import DependencyConfig, ReleaseAsset, RemoteIdentityConfig
from s2dm.deps.resolve.common import (
    DEFAULT_DEPS_CONFIG_FILENAME,
    DEPENDENCY_LOCK_FILENAME,
    METADATA_FILENAME,
    SCHEMA_FILENAME,
)
from s2dm.deps.resolve.context import ResolverContext
from s2dm.deps.resolve.errors import (
    DependencyArtifactError,
    DependencyConfigError,
    DependencySourceError,
    DependencyUpstreamError,
)
from s2dm.deps.resolve.providers import RemoteIdentityProvider
from s2dm.deps.resolve.providers.github_release_provider import RELEASES_PAGE_SIZE
from s2dm.deps.resolve.releases import list_releases
from s2dm.deps.resolve.resolve import resolve_dependencies
from s2dm.deps.resolve.resolvers.remote_resolver import RemoteResolver
from tests.deps.helpers import (
    file_sha256,
    first_lock_dependency,
    write_dependency_config,
    write_dependency_lock,
    write_metadata_file,
)

TEST_REMOTE_HOST = "example.ghe.com"


def _build_release_archive_bytes() -> bytes:
    archive_buffer = BytesIO()
    schema_bytes = b"type Query { ping: String }\n"
    metadata_bytes = yaml.safe_dump(
        {"name": "B", "id": "urn:test:B", "version": "5.1.0"},
        sort_keys=False,
    ).encode("utf-8")

    with tarfile.open(fileobj=archive_buffer, mode="w:gz") as tar_file:
        schema_info = tarfile.TarInfo(name=SCHEMA_FILENAME)
        schema_info.size = len(schema_bytes)
        tar_file.addfile(schema_info, BytesIO(schema_bytes))

        metadata_info = tarfile.TarInfo(name=METADATA_FILENAME)
        metadata_info.size = len(metadata_bytes)
        tar_file.addfile(metadata_info, BytesIO(metadata_bytes))

    return archive_buffer.getvalue()


def test_resolve_dependencies_from_remote_release(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    config_path = workspace / DEFAULT_DEPS_CONFIG_FILENAME
    write_dependency_config(config_path, "https://github.com/owner/repo", SCHEMA_FILENAME)

    schema_response = Mock()
    schema_response.raise_for_status = Mock()
    schema_response.headers = {}
    schema_response.content = b"type Query { ping: String }\n"

    metadata_response = Mock()
    metadata_response.raise_for_status = Mock()
    metadata_response.headers = {}
    metadata_response.content = yaml.safe_dump(
        {"name": "B", "id": "urn:test:B", "version": "5.1.0"},
        sort_keys=False,
    ).encode("utf-8")

    def mock_get(url: str, headers: dict[str, str] | None, timeout: int) -> Mock:
        assert timeout == 30
        assert headers is None
        response = None
        if url == "https://github.com/owner/repo/releases/download/5.1.0/schema.graphql":
            response = schema_response
        if url == "https://github.com/owner/repo/releases/download/5.1.0/metadata.yaml":
            response = metadata_response
        if response is None:
            raise AssertionError(f"Unexpected URL requested: {url}")

        return response

    with patch("s2dm.utils.download.requests.get", side_effect=mock_get):
        lock_file = resolve_dependencies(DependencyConfig.load(config_path), workspace)

    lock_path = workspace / DEPENDENCY_LOCK_FILENAME
    lock_file.save(lock_path)

    dependency = first_lock_dependency(lock_path)
    assert dependency["resolved_path"] == "https://github.com/owner/repo/releases/download/5.1.0/schema.graphql"


def test_resolve_dependencies_skips_remote_release_when_lock_and_vendor_exist(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    config_path = workspace / DEFAULT_DEPS_CONFIG_FILENAME
    write_dependency_config(config_path, "https://github.com/owner/repo", SCHEMA_FILENAME)

    vendored_directory = workspace / ".s2dm" / "vendor" / "B" / "5.1.0"
    vendored_directory.mkdir(parents=True)
    vendored_schema_path = vendored_directory / SCHEMA_FILENAME
    vendored_schema_path.write_text("type Query { cached: String }\n", encoding="utf-8")
    write_metadata_file(vendored_directory / METADATA_FILENAME)
    write_dependency_lock(
        workspace / DEPENDENCY_LOCK_FILENAME,
        resolved_path="https://github.com/owner/repo/releases/download/5.1.0/schema.graphql",
        integrity=file_sha256(vendored_schema_path),
    )

    with patch("s2dm.utils.download.requests.get") as mock_get:
        lock_file = resolve_dependencies(DependencyConfig.load(config_path), workspace)

    mock_get.assert_not_called()
    lock_path = workspace / DEPENDENCY_LOCK_FILENAME
    lock_file.save(lock_path)

    dependency = first_lock_dependency(lock_path)
    assert dependency["resolved_path"] == "https://github.com/owner/repo/releases/download/5.1.0/schema.graphql"
    assert vendored_schema_path.read_text(encoding="utf-8") == "type Query { cached: String }\n"


def test_resolve_dependencies_from_authenticated_remote_archive_release(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    config_path = workspace / DEFAULT_DEPS_CONFIG_FILENAME
    identity_path = workspace / ".s2dm.identity.yaml"
    write_dependency_config(config_path, f"https://{TEST_REMOTE_HOST}/owner/repo", "bundle.tgz")
    identity_path.write_text(
        yaml.safe_dump(
            {"identities": [{"host": TEST_REMOTE_HOST, "token": "test-token"}]},
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    release_response = Mock()
    release_response.raise_for_status = Mock()
    release_response.json = Mock(
        return_value={
            "assets": [
                {
                    "name": "bundle.tgz",
                    "url": f"https://{TEST_REMOTE_HOST}/api/v3/repos/owner/repo/releases/assets/123",
                    "size": 1,
                }
            ]
        }
    )

    asset_response = Mock()
    asset_response.raise_for_status = Mock()
    asset_response.headers = {}
    asset_response.content = _build_release_archive_bytes()
    requested_asset_urls: list[str] = []

    def mock_request_get(url: str, headers: dict[str, str], timeout: int) -> Mock:
        assert timeout == 30
        if url == f"https://{TEST_REMOTE_HOST}/api/v3/repos/owner/repo/releases/tags/5.1.0":
            assert headers == {
                "Authorization": "Bearer test-token",
                "Accept": "application/vnd.github+json",
            }
            return release_response
        requested_asset_urls.append(url)
        assert url == f"https://{TEST_REMOTE_HOST}/api/v3/repos/owner/repo/releases/assets/123"
        assert headers == {
            "Authorization": "Bearer test-token",
            "Accept": "application/octet-stream",
        }
        return asset_response

    remote_identity_config = RemoteIdentityConfig.load(identity_path)
    remote_identity_provider = RemoteIdentityProvider(remote_identity_config)
    resolver_context = ResolverContext(remote_identity_provider=remote_identity_provider)

    with patch("s2dm.deps.resolve.providers.github_release_provider.requests.get", side_effect=mock_request_get):
        lock_file = resolve_dependencies(
            DependencyConfig.load(config_path),
            workspace,
            resolver_context,
        )

    lock_path = workspace / DEPENDENCY_LOCK_FILENAME
    lock_file.save(lock_path)

    vendored_schema_path = workspace / ".s2dm" / "vendor" / "B" / "5.1.0" / SCHEMA_FILENAME
    assert vendored_schema_path.read_text(encoding="utf-8") == "type Query { ping: String }\n"
    assert requested_asset_urls == [f"https://{TEST_REMOTE_HOST}/api/v3/repos/owner/repo/releases/assets/123"]

    dependency = first_lock_dependency(lock_path)
    assert dependency["resolved_path"] == f"https://{TEST_REMOTE_HOST}/owner/repo/releases/download/5.1.0/bundle.tgz"


def test_resolve_dependencies_from_unauthenticated_remote_archive_release(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    config_path = workspace / DEFAULT_DEPS_CONFIG_FILENAME
    write_dependency_config(config_path, "https://github.com/owner/repo", "bundle.tgz")

    asset_response = Mock()
    asset_response.raise_for_status = Mock()
    asset_response.headers = {}
    asset_response.content = _build_release_archive_bytes()

    def mock_asset_get(url: str, headers: dict[str, str] | None, timeout: int) -> Mock:
        assert timeout == 30
        assert headers is None
        assert url == "https://github.com/owner/repo/releases/download/5.1.0/bundle.tgz"
        return asset_response

    with (
        patch("s2dm.deps.resolve.providers.github_release_provider.requests.get") as mock_release_get,
        patch("s2dm.utils.download.requests.get", side_effect=mock_asset_get),
    ):
        lock_file = resolve_dependencies(DependencyConfig.load(config_path), workspace)

    mock_release_get.assert_not_called()
    lock_path = workspace / DEPENDENCY_LOCK_FILENAME
    lock_file.save(lock_path)

    vendored_schema_path = workspace / ".s2dm" / "vendor" / "B" / "5.1.0" / SCHEMA_FILENAME
    assert vendored_schema_path.read_text(encoding="utf-8") == "type Query { ping: String }\n"

    dependency = first_lock_dependency(lock_path)
    assert dependency["resolved_path"] == "https://github.com/owner/repo/releases/download/5.1.0/bundle.tgz"


GITHUB_RELEASES_URL = "https://api.github.com/repos/owner/repo/releases"
GITHUB_JSON_HEADERS = {"Accept": "application/vnd.github+json"}


def _github_asset(name: str) -> dict[str, object]:
    return {
        "name": name,
        "url": f"https://api.github.com/repos/owner/repo/releases/assets/{name}",
        "browser_download_url": f"https://github.com/owner/repo/releases/download/v1/{name}",
        "size": 1,
        "content_type": "application/octet-stream",
    }


def _github_release(
    tag: str,
    asset_names: list[str],
    *,
    draft: bool = False,
    prerelease: bool = False,
) -> dict[str, object]:
    return {
        "tag_name": tag,
        "name": f"Release {tag}",
        "draft": draft,
        "prerelease": prerelease,
        "published_at": "2026-01-02T03:04:05Z",
        "tarball_url": f"https://api.github.com/repos/owner/repo/tarball/{tag}",
        "zipball_url": f"https://api.github.com/repos/owner/repo/zipball/{tag}",
        "assets": [_github_asset(name) for name in asset_names],
    }


def _releases_response(releases: list[dict[str, object]], links: dict[str, dict[str, str]]) -> Mock:
    response = Mock()
    response.raise_for_status = Mock()
    response.json = Mock(return_value=releases)
    response.links = links
    return response


def _failed_response(status_code: int) -> Mock:
    error_response = Mock(status_code=status_code)
    http_error = requests.HTTPError(response=error_response)
    response = Mock()
    response.raise_for_status = Mock(side_effect=http_error)
    response.links = {}
    return response


def _page_link(page: int) -> dict[str, str]:
    return {"url": f"{GITHUB_RELEASES_URL}?per_page={RELEASES_PAGE_SIZE}&page={page}"}


def test_list_releases_returns_candidate_assets() -> None:
    releases = [
        _github_release("v3", [SCHEMA_FILENAME, METADATA_FILENAME, "bundle.zip"]),
        _github_release("v2", ["release.tar.gz", "notes.txt"], prerelease=True),
        _github_release("v1", []),
    ]
    response = _releases_response(releases, {})

    with patch("s2dm.deps.resolve.providers.github_release_provider.requests.get", return_value=response) as mock_get:
        page = list_releases("https://github.com/owner/repo", 2, None)

    mock_get.assert_called_once_with(
        GITHUB_RELEASES_URL,
        headers=GITHUB_JSON_HEADERS,
        params={"per_page": RELEASES_PAGE_SIZE, "page": 2},
        timeout=30,
    )
    assert [release.tag for release in page.releases] == ["v3", "v2", "v1"]
    assert [release.prerelease for release in page.releases] == [False, True, False]
    assert [release.candidate_assets for release in page.releases] == [
        [ReleaseAsset(name=SCHEMA_FILENAME, size=1), ReleaseAsset(name="bundle.zip", size=1)],
        [ReleaseAsset(name="release.tar.gz", size=1)],
        [],
    ]


def test_list_releases_keeps_asset_sizes() -> None:
    release = _github_release("v1", [])
    release["assets"] = [
        {**_github_asset(METADATA_FILENAME), "size": 117},
        {**_github_asset(SCHEMA_FILENAME), "size": 2242042},
        {**_github_asset("model.zip"), "size": 1536},
    ]
    response = _releases_response([release], {})

    with patch("s2dm.deps.resolve.providers.github_release_provider.requests.get", return_value=response):
        page = list_releases("https://github.com/owner/repo", 1, None)

    assert page.releases[0].candidate_assets == [
        ReleaseAsset(name=SCHEMA_FILENAME, size=2242042),
        ReleaseAsset(name="model.zip", size=1536),
    ]


def test_list_releases_drops_drafts_and_keeps_paging() -> None:
    releases = [_github_release("v2", ["release.tar.gz"], draft=True)]
    response = _releases_response(releases, {"next": _page_link(2)})

    with patch("s2dm.deps.resolve.providers.github_release_provider.requests.get", return_value=response):
        page = list_releases("https://github.com/owner/repo", 1, None)

    assert page.releases == []
    assert page.has_next is True


def test_list_releases_reads_paging_links() -> None:
    links = {"next": _page_link(3), "prev": _page_link(1), "last": _page_link(5)}
    response = _releases_response([], links)

    with patch("s2dm.deps.resolve.providers.github_release_provider.requests.get", return_value=response):
        page = list_releases("https://github.com/owner/repo", 2, None)

    assert (page.page, page.has_next, page.has_previous, page.last_page) == (2, True, True, 5)


def test_list_releases_without_link_header() -> None:
    response = _releases_response([], {})

    with patch("s2dm.deps.resolve.providers.github_release_provider.requests.get", return_value=response):
        page = list_releases("https://github.com/owner/repo", 1, None)

    assert (page.has_next, page.has_previous, page.last_page) == (False, False, 1)


def test_list_releases_reports_current_page_as_last_page() -> None:
    links = {"prev": _page_link(4), "first": _page_link(1)}
    response = _releases_response([], links)

    with patch("s2dm.deps.resolve.providers.github_release_provider.requests.get", return_value=response):
        page = list_releases("https://github.com/owner/repo", 5, None)

    assert (page.has_next, page.has_previous, page.last_page) == (False, True, 5)


def test_list_releases_keeps_unknown_last_page_with_next_link() -> None:
    response = _releases_response([], {"next": _page_link(3)})

    with patch("s2dm.deps.resolve.providers.github_release_provider.requests.get", return_value=response):
        page = list_releases("https://github.com/owner/repo", 2, None)

    assert (page.has_next, page.last_page) == (True, None)


def test_list_releases_uses_token_on_enterprise_host() -> None:
    remote_identity_config = RemoteIdentityConfig.model_validate(
        {"identities": [{"host": TEST_REMOTE_HOST, "token": "test-token"}]}
    )
    remote_identity_provider = RemoteIdentityProvider(remote_identity_config)
    resolver_context = ResolverContext(remote_identity_provider=remote_identity_provider)
    response = _releases_response([], {})

    with patch("s2dm.deps.resolve.providers.github_release_provider.requests.get", return_value=response) as mock_get:
        list_releases(f"https://{TEST_REMOTE_HOST}/owner/repo", 1, resolver_context)

    mock_get.assert_called_once_with(
        f"https://{TEST_REMOTE_HOST}/api/v3/repos/owner/repo/releases",
        headers={"Authorization": "Bearer test-token", **GITHUB_JSON_HEADERS},
        params={"per_page": RELEASES_PAGE_SIZE, "page": 1},
        timeout=30,
    )


@pytest.mark.parametrize("status_code", [401, 403, 404])
def test_list_releases_maps_access_failure_to_source_error(status_code: int) -> None:
    response = _failed_response(status_code)

    with (
        patch("s2dm.deps.resolve.providers.github_release_provider.requests.get", return_value=response),
        pytest.raises(DependencySourceError) as error_info,
    ):
        list_releases("https://github.com/owner/repo", 1, None)

    assert not isinstance(error_info.value, DependencyArtifactError)


def test_list_releases_maps_server_failure_to_upstream_error() -> None:
    response = _failed_response(500)

    with (
        patch("s2dm.deps.resolve.providers.github_release_provider.requests.get", return_value=response),
        pytest.raises(DependencyUpstreamError),
    ):
        list_releases("https://github.com/owner/repo", 1, None)


@pytest.mark.parametrize("asset_name", ["../schema.graphql", "nested/schema.graphql", "nested\\schema.zip", ".."])
def test_resolve_release_asset_rejects_asset_name_with_path(asset_name: str) -> None:
    with (
        patch("s2dm.deps.resolve.providers.github_release_provider.requests.get", side_effect=AssertionError),
        patch("s2dm.deps.resolve.providers.github_release_provider.download_url_to_path", side_effect=AssertionError),
        pytest.raises(DependencyConfigError),
    ):
        RemoteResolver().resolve_release_asset("https://github.com/owner/repo", "v1.0.0", asset_name)
