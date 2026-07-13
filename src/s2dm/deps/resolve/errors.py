class DependencyResolutionError(RuntimeError):
    """Base error for dependency resolution failures surfaced to API callers."""


class DependencyConfigError(DependencyResolutionError):
    """Dependency resolution failed due to an invalid dependency configuration."""


class DependencySourceError(DependencyResolutionError):
    """Dependency resolution failed because the configured dependency source was unusable."""


class DependencyUpstreamError(DependencyResolutionError):
    """Dependency resolution failed because an upstream dependency provider could not be used."""


class DependencyInternalError(Exception):
    """Dependency resolution failed unexpectedly due to an internal error."""
