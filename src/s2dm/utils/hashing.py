"""Hashing utility functions."""

import hashlib


def sha256_hex(text: str) -> str:
    """
    Return the SHA-256 digest of a text as a hex string.

    Args:
        text: Text to hash, encoded as UTF-8

    Returns:
        The 64-character lowercase hex digest
    """
    text_bytes = text.encode()
    return hashlib.sha256(text_bytes).hexdigest()
