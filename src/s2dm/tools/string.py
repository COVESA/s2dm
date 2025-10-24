import re


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text by collapsing multiple spaces/newlines."""
    return re.sub(r"\s+", " ", text).strip()
