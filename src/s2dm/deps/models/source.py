from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DependencySource:
    """Dependencies source files paths."""

    schema_path: Path
    metadata_path: Path

@dataclass(frozen=True)
class ResolvedDependencySource:
    """Dependencies source files resolved paths."""

    source: DependencySource
    resolved_path: str
