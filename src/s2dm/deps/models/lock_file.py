from pathlib import Path
from typing import Annotated

import yaml
from pydantic import (
    AnyUrl,
    BaseModel,
    ConfigDict,
    Field,
    UrlConstraints,
    field_validator,
)

from s2dm.deps.models.common import RequiredString, create_absolute_path_validator, validate_required_string
from s2dm.utils.url import is_url

ResolvedLocalPath = Annotated[Path, create_absolute_path_validator("`resolved_path`")]
ResolvedRemotePath = Annotated[
    AnyUrl,
    UrlConstraints(allowed_schemes=["https"], host_required=True),
]
ResolvedPath = ResolvedLocalPath | ResolvedRemotePath


class ResolvedDependencyLockEntry(BaseModel):
    """Single resolved dependency entry in the dependencies lock file."""

    model_config = ConfigDict(extra="forbid")

    name: RequiredString
    version: RequiredString
    resolved_path: ResolvedPath
    integrity: RequiredString

    @field_validator("resolved_path", mode="before")
    @classmethod
    def validate_resolved_path_input(cls, value: object) -> object:
        """Route string inputs to the correct union member explicitly."""
        if not isinstance(value, str):
            return value
        validate_required_string(value)
        resolved_path = Path(value)
        if resolved_path.is_absolute():
            return resolved_path
        if is_url(value):
            return value

        raise ValueError("resolved_path must be an absolute path or a full HTTPS URL")


class DependencyLockFile(BaseModel):
    """Root structure of the dependencies lock file."""

    model_config = ConfigDict(extra="forbid")

    dependencies: list[ResolvedDependencyLockEntry] = Field(default_factory=list)

    def save(self, path: Path) -> None:
        """Write the dependency lock file to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_data = self.model_dump(exclude_none=True, mode="json")
        serialized_lock_data = yaml.safe_dump(lock_data, sort_keys=False)
        path.write_text(serialized_lock_data, encoding="utf-8")
