import re
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from s2dm.deps.models.common import (
    RequiredString,
    create_absolute_path_validator,
    load_yaml_mapping,
    validate_required_string,
)

REMOTE_REPOSITORY_PATTERN = re.compile(r"^[^/\s]+/[^/\s]+$")
LocalDependencySource = Annotated[Path, create_absolute_path_validator("`source`")]
RemoteDependencySource = Annotated[str, StringConstraints(pattern=REMOTE_REPOSITORY_PATTERN.pattern)]
DependencySource = LocalDependencySource | RemoteDependencySource


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
        if REMOTE_REPOSITORY_PATTERN.fullmatch(value):
            return value
        raise ValueError("Dependency source must be an absolute path or an exact remote '<owner>/<repo>' reference")


class DependencyConfig(BaseModel):
    """Root structure of the dependencies file."""

    model_config = ConfigDict(extra="forbid")

    dependencies: list[DependencyEntry] = Field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "DependencyConfig":
        """Load dependency configuration from a YAML file."""
        mapping = load_yaml_mapping(path, "Dependency config root")
        return cls.model_validate(mapping)
