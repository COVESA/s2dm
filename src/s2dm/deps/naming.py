import re

INVALID_GRAPHQL_NAME_CHARACTER_PATTERN = re.compile(r"[^_0-9A-Za-z]+")


def sanitize_prefix(raw_prefix: str) -> str:
    """Normalize a raw prefix into a GraphQL-safe identifier fragment."""
    prefix = INVALID_GRAPHQL_NAME_CHARACTER_PATTERN.sub("_", raw_prefix)
    if prefix and prefix[0].isdigit():
        prefix = f"_{prefix}"
    return prefix
