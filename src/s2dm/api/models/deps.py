"""Models for dependency resolution endpoints."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, DirectoryPath, Field, field_validator

from s2dm.api.models.base import ContentInput
from s2dm.deps.helpers import DependencyStatus
from s2dm.deps.models import RemoteIdentityEntry
from s2dm.deps.models.common import (
    DependencyName,
    DependencyVersion,
    RequiredString,
    validate_absolute_path,
)
from s2dm.deps.models.deps_file import DependencySource, parse_dependency_source


class DependencyPathInput(BaseModel):
    """Input referencing a dependency selection file path."""

    type: Literal["path"] = Field(description="Input type discriminator")
    path: str = Field(description="Absolute or relative path to dependency selection file")


DependencySelectionInput = DependencyPathInput | ContentInput


class ApiDependencyEntry(BaseModel):
    """API payload for a single dependency entry."""

    name: DependencyName
    version: DependencyVersion
    source: DependencySource
    artifact: RequiredString
    selection: DependencySelectionInput | None = None
    schema_content: str | None = None

    @field_validator("source", mode="before")
    @classmethod
    def validate_source(cls, value: object) -> object:
        """Route dependency source strings to the correct typed union member."""
        return parse_dependency_source(value)


class GetDependenciesConfigResponse(BaseModel):
    """Response model for retrieving stored dependency configuration."""

    dependencies: list[ApiDependencyEntry] = Field(..., description="Dependency entries to resolve")


class SaveDependenciesConfigRequest(BaseModel):
    """Request model for storing dependency configuration."""

    dependencies: list[ApiDependencyEntry] = Field(..., description="Dependency entries to resolve")

    config_directory: DirectoryPath | None = Field(
        default=None,
        description="Optional absolute parent directory of an imported dependency config file",
    )

    @field_validator("config_directory")
    @classmethod
    def validate_config_directory(cls, value: DirectoryPath | None) -> Path | None:
        """Require config directory paths to be absolute when provided."""
        if value is None:
            return None
        return validate_absolute_path(value, "`config_directory`")


class DependenciesIdentities(BaseModel):
    """Stored dependency identity payload."""

    identities: list[RemoteIdentityEntry] = Field(..., description="Dependency identity entries")


class ResolveDependenciesRequest(BaseModel):
    """Request model for dependency resolution using stored configuration."""

    clean: bool = Field(default=False, description="Whether to clean the API dependency workspace before resolving")


class BuildDependenciesRequest(BaseModel):
    """Request model for dependency build using stored configuration."""

    auto_prefix: bool = Field(
        default=False,
        description="Whether to prefix conflicting dependency types automatically during composition",
    )


class DependenciesApiResponse(BaseModel):
    """Success response model for dependency operations that need to return warnings."""

    warnings: list[str] = Field(description="Warnings collected during dependency resolution")


class DependenciesStatusResponse(BaseModel):
    """Minimal dependency status response."""

    status: DependencyStatus = Field(description="Current dependency resolution status")
