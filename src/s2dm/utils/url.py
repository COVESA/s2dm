from urllib.parse import urlparse


def is_url(value: str) -> bool:
    """Check whether a value is a valid HTTP or HTTPS URL.

    Args:
        value: String to validate.

    Returns:
        bool: ``True`` when the value is a valid HTTP/HTTPS URL, otherwise ``False``.
    """
    try:
        parsed = urlparse(value)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False
