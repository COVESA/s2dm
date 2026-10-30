"""Errors raised by semantic search: resolving embedding models and reading embeddings files."""


class ModelResolutionError(Exception):
    """Raised when a model cannot be downloaded or does not publish what is needed to run it."""


class EmbeddingsFileError(Exception):
    """Raised when an embeddings file cannot be read or does not match its model."""
