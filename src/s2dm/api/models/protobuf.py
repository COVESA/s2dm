from pydantic import Field

from s2dm.api.models.base import QueryBasedExportRequest


class ProtobufExportRequest(QueryBasedExportRequest):
    """Request model for Protocol Buffers export endpoint."""

    flatten_naming: bool = Field(
        default=False, description="Flatten nested field names", json_schema_extra={"x-cli-flag": "--flatten-naming"}
    )
    package_name: str | None = Field(
        default=None, description="Protobuf package name", json_schema_extra={"x-cli-flag": "--package-name"}
    )
