from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator

from s2dm.deps.models.common import RequiredString, load_yaml_mapping


class DependencyMetadata(BaseModel):
    """Metadata bundled with a dependency."""

    model_config = ConfigDict(extra="forbid")

    name: RequiredString
    id: RequiredString
    version: RequiredString
    preferred_prefix: str | None = None

    @field_validator("preferred_prefix")
    @classmethod
    def validate_preferred_prefix(cls, value: str | None) -> str | None:
        """Reject empty optional prefixes when the key is explicitly provided."""
        if value is None:
            return None
        if not value:
            raise ValueError("preferred_prefix cannot be empty")
        if value != value.strip():
            raise ValueError("preferred_prefix must not contain leading or trailing whitespace")
        return value

    @classmethod
    def load(cls, path: Path) -> "DependencyMetadata":
        """Load dependency metadata from the metadata file."""
        mapping = load_yaml_mapping(path, "Dependency metadata root")
        return cls.model_validate(mapping)
