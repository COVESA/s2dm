from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from s2dm.deps.models.common import RequiredString, load_yaml_mapping


class RemoteIdentityEntry(BaseModel):
    """Single token identity entry.

    Scope-specific entries take precedence over host-wide fallback entries.
    """

    model_config = ConfigDict(extra="forbid")

    host: RequiredString
    scope: RequiredString | None = None
    token: RequiredString

    @field_validator("host")
    @classmethod
    def validate_host(cls, value: str) -> str:
        """Require host-only identity values with optional port."""
        parsed = urlparse(f"//{value}")
        if not parsed.netloc or parsed.path or parsed.query or parsed.fragment:
            raise ValueError("Identity host must be a host name with optional port only")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Identity host must not include credentials")
        if parsed.hostname is None:
            raise ValueError("Identity host must be a valid host name")
        return value


class RemoteIdentityConfig(BaseModel):
    """Root structure of the dependency identity file."""

    model_config = ConfigDict(extra="forbid")

    identities: list[RemoteIdentityEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_identity_targets(self) -> "RemoteIdentityConfig":
        """Reject duplicate host and scope identity entries."""
        seen_identity_targets: set[tuple[str, str | None]] = set()
        for identity in self.identities:
            identity_target = (identity.host, identity.scope)
            if identity_target in seen_identity_targets:
                duplicate_label = identity.host if identity.scope is None else f"{identity.host}/{identity.scope}"
                raise ValueError(f"Duplicate identity target '{duplicate_label}' is not allowed")
            seen_identity_targets.add(identity_target)
        return self

    @classmethod
    def load(cls, path: Path) -> "RemoteIdentityConfig":
        """Load dependency identities from a YAML file."""
        mapping = load_yaml_mapping(path, "Dependency identity root")
        return cls.model_validate(mapping)
