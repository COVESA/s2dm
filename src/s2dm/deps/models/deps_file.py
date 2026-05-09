from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from s2dm.deps.models.common import (
    RequiredString,
    create_absolute_path_validator,
    load_yaml_mapping,
    validate_required_string,
)

LocalDependencySource = Annotated[Path, create_absolute_path_validator("`source`")]
RemoteDependencySource = str
DependencySource = LocalDependencySource | RemoteDependencySource
DependencySelection = Annotated[Path, create_absolute_path_validator("`selection`")]
GRAPHQL_FILE_EXTENSIONS = frozenset({".graphql", ".gql"})


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
    selection: DependencySelection | None = None

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

    @field_validator("selection")
    @classmethod
    def validate_selection(cls, value: Path | None) -> Path | None:
        """Require dependency selection files to be existing GraphQL files."""
        if value is None:
            return None
        if value.suffix.lower() not in GRAPHQL_FILE_EXTENSIONS:
            raise ValueError("Dependency selection must be a .graphql or .gql file")
        if not value.is_file():
            raise ValueError(f"Dependency selection file does not exist: {value}")
        return value


class DependencyConfig(BaseModel):
    """Root structure of the dependencies file."""

    model_config = ConfigDict(extra="forbid")

    dependencies: list[DependencyEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_dependency_targets(self) -> "DependencyConfig":
        """Reject duplicate dependency name/version targets."""
        seen_dependency_targets: set[tuple[str, str]] = set()
        for dependency in self.dependencies:
            dependency_target = (dependency.name, dependency.version)
            if dependency_target in seen_dependency_targets:
                raise ValueError(
                    f"Duplicate dependency target '{dependency.name}/{dependency.version}' is not allowed"
                )
            seen_dependency_targets.add(dependency_target)
        return self

    @classmethod
    def load(cls, path: Path) -> "DependencyConfig":
        """Load dependency configuration from a YAML file."""
        mapping = load_yaml_mapping(path, "Dependency config root")
        return cls.model_validate(mapping)
