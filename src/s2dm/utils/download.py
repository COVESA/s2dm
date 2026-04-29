import tempfile
from pathlib import Path

import requests

from s2dm import log


def download_url_to_path(
    url: str,
    destination_path: Path,
    resource_label: str,
    overwrite: bool,
    max_size_mb: int = 10,
) -> Path:
    """Download a remote file to a destination path.

    Args:
        url: HTTP/HTTPS URL to download.
        destination_path: Path where the downloaded file should be written.
        resource_label: Human-readable label used in log and error messages.
        overwrite: Whether to overwrite an existing destination file.
        max_size_mb: Maximum allowed file size in megabytes.

    Returns:
        Path to the downloaded file.

    Raises:
        FileExistsError: If the destination file exists and overwrite is false.
        RuntimeError: If the download fails or the file exceeds the size limit.
    """
    if destination_path.exists() and not overwrite:
        raise FileExistsError(f"Destination path already exists: {destination_path}")

    max_size_bytes = max_size_mb * 1024 * 1024

    try:
        log.info(f"Downloading {resource_label} from {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > max_size_bytes:
            raise RuntimeError(
                f"{resource_label} file too large: "
                f"{int(content_length) / 1024 / 1024:.1f} MB (max {max_size_mb} MB)"
            )

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_bytes(response.content)

        log.debug(f"{resource_label} downloaded to: {destination_path}")
        return destination_path

    except requests.RequestException as e:
        raise RuntimeError(f"Failed to download {resource_label} from {url}: {e}") from e


def download_url_to_temp(url: str, suffix: str, resource_label: str, max_size_mb: int = 10) -> Path:
    """Download a remote file to a named temporary file.

    Args:
        url: HTTP/HTTPS URL to download.
        suffix: File extension for the temp file (e.g. ``.graphql``, ``.ttl``).
        resource_label: Human-readable label used in log and error messages (e.g. ``"schema"``).
        max_size_mb: Maximum allowed file size in megabytes.

    Returns:
        Path to the downloaded temporary file.

    Raises:
        RuntimeError: If the download fails or the file exceeds the size limit.
    """
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = Path(tmp.name)

        download_url_to_path(
            url=url,
            destination_path=tmp_path,
            resource_label=resource_label,
            overwrite=True,
            max_size_mb=max_size_mb,
        )
        log.debug(f"{resource_label} downloaded to temporary file: {tmp_path}")
        return tmp_path

    except Exception:
        if "tmp_path" in locals():
            tmp_path.unlink(missing_ok=True)
        raise
