"""File utility functions."""

import tempfile
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
