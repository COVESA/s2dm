from pydantic import Field

from s2dm.api.models.base import BaseExportRequest


class JsonSchemaExportRequest(BaseExportRequest):
    """Request model for JSON Schema export endpoint."""

    strict: bool = Field(
        default=False,
        description="Enforce strict type translation from GraphQL schema",
        json_schema_extra={"x-cli-flag": "--strict"},
    )
