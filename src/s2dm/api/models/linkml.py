from pydantic import Field, field_validator

from s2dm.api.models.base import BaseExportRequest
from s2dm.tools.validators import validate_linkml_uri_value


class LinkmlExportRequest(BaseExportRequest):
    """Request model for LinkML export endpoint."""

    id: str = Field(description="LinkML schema id (required)", json_schema_extra={"x-cli-flag": "--id"})
    name: str = Field(description="LinkML schema name (required)", json_schema_extra={"x-cli-flag": "--name"})
    default_prefix: str = Field(
        description="LinkML default prefix (required)",
        json_schema_extra={"x-cli-flag": "--default-prefix"},
    )
    default_prefix_url: str = Field(
        description="LinkML default prefix URL (required)",
        json_schema_extra={"x-cli-flag": "--default-prefix-url"},
    )

    @field_validator("id", "default_prefix_url")
    @classmethod
    def validate_linkml_uri_fields(cls, value: str) -> str:
        return validate_linkml_uri_value(value)
