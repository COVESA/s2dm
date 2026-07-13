import tarfile
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

import yaml

from s2dm.deps.models import DependencyConfig, RemoteIdentityConfig
from s2dm.deps.resolve.common import (
    DEFAULT_DEPS_CONFIG_FILENAME,
    DEPENDENCY_LOCK_FILENAME,
    METADATA_FILENAME,
    SCHEMA_FILENAME,
)
from s2dm.deps.resolve.context import ResolverContext
from s2dm.deps.resolve.providers import RemoteIdentityProvider
from s2dm.deps.resolve.resolve import resolve_dependencies
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

    with patch("s2dm.deps.resolve.resolvers.remote_resolver.requests.get", side_effect=mock_request_get):
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
        patch("s2dm.deps.resolve.resolvers.remote_resolver.requests.get") as mock_release_get,
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
