import tarfile
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml
from fastapi.testclient import TestClient
from httpx2 import Response

import s2dm.api.services.schema_store as schema_store
from s2dm.utils.hashing import sha256_hex

REPOSITORY_URL = "https://github.com/owner/repo"
SCHEMA_TEXT = "type Query { ping: String }\n"
INVALID_SCHEMA_TEXT = "type Query {\n"
RELEASE_TAG = "v1.0.0"
PUBLISH_ARCHIVE_NAME = "release.tar.gz"
PUBLISH_ARCHIVE_URL = f"{REPOSITORY_URL}/releases/download/{RELEASE_TAG}/{PUBLISH_ARCHIVE_NAME}"


@pytest.fixture(autouse=True)
def schema_store_workspace(monkeypatch: pytest.MonkeyPatch, api_workspace: Path) -> Path:
    monkeypatch.setattr(schema_store, "get_api_workspace", lambda: api_workspace)
    return api_workspace


def _add_tar_member(tar_file: tarfile.TarFile, member_name: str, content: str) -> None:
    content_bytes = content.encode("utf-8")
    member_info = tarfile.TarInfo(name=member_name)
    member_info.size = len(content_bytes)
    content_stream = BytesIO(content_bytes)
    tar_file.addfile(member_info, content_stream)


def _build_publish_archive(schema_text: str = SCHEMA_TEXT, include_metadata: bool = True) -> bytes:
    archive_buffer = BytesIO()
    metadata_text = yaml.safe_dump(
        {"name": "Vehicle", "id": "urn:test:vehicle", "version": RELEASE_TAG},
        sort_keys=False,
    )
    with tarfile.open(fileobj=archive_buffer, mode="w:gz") as tar_file:
        _add_tar_member(tar_file, "graphql/schema.graphql", schema_text)
        _add_tar_member(tar_file, "registry/history/Vehicle_v1.0.graphql", SCHEMA_TEXT)
        if include_metadata:
            _add_tar_member(tar_file, "metadata.yaml", metadata_text)
    return archive_buffer.getvalue()


def _asset_response(content: bytes) -> Mock:
    response = Mock()
    response.raise_for_status = Mock()
    response.headers = {}
    response.content = content
    return response


def _load_release(test_client: TestClient, archive_bytes: bytes) -> Response:
    asset_response = _asset_response(archive_bytes)

    def mock_asset_get(url: str, headers: dict[str, str] | None, timeout: int) -> Mock:
        assert url == PUBLISH_ARCHIVE_URL
        return asset_response

    payload = {"repository": REPOSITORY_URL, "tag": RELEASE_TAG, "artifact": PUBLISH_ARCHIVE_NAME}
    with patch("s2dm.utils.download.requests.get", side_effect=mock_asset_get):
        return test_client.post("/api/v1/deps/releases/load", json=payload)


class TestDepsReleasesRoute:
    """Test /api/v1/deps/releases route behavior."""

    def test_list_releases_returns_page(self, test_client: TestClient) -> None:
        github_release = {
            "tag_name": RELEASE_TAG,
            "name": "Release v1.0.0",
            "draft": False,
            "prerelease": False,
            "published_at": "2026-01-02T03:04:05Z",
            "tarball_url": f"https://api.github.com/repos/owner/repo/tarball/{RELEASE_TAG}",
            "zipball_url": f"https://api.github.com/repos/owner/repo/zipball/{RELEASE_TAG}",
            "assets": [
                {
                    "name": PUBLISH_ARCHIVE_NAME,
                    "url": "https://api.github.com/repos/owner/repo/releases/assets/1",
                    "browser_download_url": PUBLISH_ARCHIVE_URL,
                    "size": 1,
                    "content_type": "application/gzip",
                }
            ],
        }
        github_response = Mock()
        github_response.raise_for_status = Mock()
        github_response.json = Mock(return_value=[github_release])
        github_response.links = {}

        with patch("s2dm.deps.resolve.providers.github_release_provider.requests.get", return_value=github_response):
            response = test_client.get("/api/v1/deps/releases", params={"repository": REPOSITORY_URL})

        assert response.status_code == 200
        data = response.json()
        assert data["releases"][0]["candidate_assets"] == [{"name": PUBLISH_ARCHIVE_NAME, "size": 1}]
        assert data["page"] == 1

    @pytest.mark.parametrize("repository", ["https://github.com/owner", "https://github.com/owner/repo.git"])
    def test_list_releases_rejects_invalid_repository_url(self, test_client: TestClient, repository: str) -> None:
        with patch("s2dm.deps.resolve.providers.github_release_provider.requests.get") as mock_get:
            response = test_client.get("/api/v1/deps/releases", params={"repository": repository})

        mock_get.assert_not_called()
        assert response.status_code == 422
        assert response.json()["error"] == "ValidationError"

    def test_list_releases_rejects_page_zero(self, test_client: TestClient) -> None:
        response = test_client.get("/api/v1/deps/releases", params={"repository": REPOSITORY_URL, "page": 0})

        assert response.status_code == 400
        assert response.json()["error"] == "BadRequest"

    def test_load_release_returns_schema_and_metadata(self, test_client: TestClient, api_workspace: Path) -> None:
        archive_bytes = _build_publish_archive()

        response = _load_release(test_client, archive_bytes)

        assert response.status_code == 200
        data = response.json()
        assert data["schema_content"] == SCHEMA_TEXT
        assert data["schema_id"] == sha256_hex(SCHEMA_TEXT)
        assert data["metadata"]["name"] == "Vehicle"
        assert data["metadata"]["version"] == RELEASE_TAG
        assert (api_workspace / "schemas" / f"{data['schema_id']}.graphql").is_file()

    def test_load_release_returns_artifact_error_for_archive_without_metadata(self, test_client: TestClient) -> None:
        archive_bytes = _build_publish_archive(include_metadata=False)

        response = _load_release(test_client, archive_bytes)

        assert response.status_code == 422
        assert response.json()["error"] == "DependencyArtifactError"

    def test_load_release_returns_source_error_for_invalid_schema(self, test_client: TestClient) -> None:
        archive_bytes = _build_publish_archive(schema_text=INVALID_SCHEMA_TEXT)

        response = _load_release(test_client, archive_bytes)

        assert response.status_code == 422
        assert response.json()["error"] == "DependencySourceError"
