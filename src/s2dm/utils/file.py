"""File utility functions."""

import tempfile
from collections.abc import Iterable
from pathlib import Path


def temp_file_from_content(
    content: str,
    suffix: str = ".graphql",
    prefix: str = "",
    filename: str | None = None,
    delete: bool = False,
    encoding: str = "utf-8",
) -> Path:
    """
    Write string content to a temporary file and return its path.

    Args:
        content: String content to write to the file
        suffix: File extension including dot (e.g., ".graphql", ".yaml")
        prefix: Prefix for the temp filename
        filename: Optional filename to preserve in a temp directory
        delete: Whether to delete the file when closed (default: False).
                When False, the file persists for downstream processing.
                When True, the file is automatically deleted when closed.
        encoding: File encoding (default: "utf-8")

    Returns:
        Path object pointing to the created temporary file

    Raises:
        ValueError: If filename is empty after sanitization
    """
    if filename is not None:
        sanitized_name = Path(filename).name.strip()
        if not sanitized_name:
            raise ValueError("Filename cannot be empty")

        temp_dir = Path(tempfile.mkdtemp())
        target_path = temp_dir / sanitized_name
        target_path.write_text(content, encoding=encoding)
        return target_path

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=suffix,
        prefix=prefix,
        delete=delete,
        encoding=encoding,
    ) as temp_file:
        temp_file.write(content)
        temp_file.flush()
        return Path(temp_file.name)


def write_text_atomically(path: Path, content: str, encoding: str = "utf-8") -> None:
    """
    Write a text file through a temporary sibling, so readers never see a partial file.

    Args:
        path: Destination file. Its parent directories are created if absent.
        content: Text to write
        encoding: File encoding (default: "utf-8")
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f"{path.name}.tmp")
    temporary_path.write_text(content, encoding=encoding)
    temporary_path.replace(path)


def temp_files_from_contents(
    contents: Iterable[str],
    suffix: str = ".graphql",
    prefix: str = "",
    delete: bool = False,
    encoding: str = "utf-8",
) -> list[Path]:
    """Write string contents to temporary files and return their paths."""
    return [
        temp_file_from_content(
            content=content,
            suffix=suffix,
            prefix=prefix,
            delete=delete,
            encoding=encoding,
        )
        for content in contents
    ]
