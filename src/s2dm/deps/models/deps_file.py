from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

from s2dm.deps.models.common import (
    RequiredString,
    create_absolute_path_validator,
    load_yaml_mapping,
    validate_required_string,
)

LocalDependencySource = Annotated[Path, create_absolute_path_validator("`source`")]
RemoteDependencySource = str
DependencySource = LocalDependencySource | RemoteDependencySource


def is_dependency_source_url(value: str) -> bool:
    """Check whether a value is a supported dependency source URL."""
    try:
        parsed = urlparse(value)
    except Exception:
        return False

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False
    if parsed.query or parsed.fragment:
        return False

    path_segments = [path_segment for path_segment in parsed.path.split("/") if path_segment]
    return len(path_segments) >= 2


class DependencyEntry(BaseModel):
    """Single dependency entry from the dependency configuration file."""

    model_config = ConfigDict(extra="forbid")

    name: RequiredString
    version: RequiredString
    source: DependencySource
    artifact: RequiredString

    @field_validator("source", mode="before")
    @classmethod
    def validate_source(cls, value: object) -> object:
        """Route dependency source strings to the correct typed union member."""
        if not isinstance(value, str):
            return value
        validate_required_string(value)
        source_path = Path(value)
        if source_path.is_absolute():
            return source_path
        if is_dependency_source_url(value):
            return value
        raise ValueError("Dependency source must be an absolute path or a valid repository URL")


class DependencyConfig(BaseModel):
    """Root structure of the dependencies file."""

    model_config = ConfigDict(extra="forbid")

    dependencies: list[DependencyEntry] = Field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "DependencyConfig":
        """Load dependency configuration from a YAML file."""
        mapping = load_yaml_mapping(path, "Dependency config root")
        return cls.model_validate(mapping)
