from pydantic import Field

from s2dm.api.models.base import BaseExportRequest, QueryBasedExportRequest


class AvroSchemaExportRequest(QueryBasedExportRequest):
    """Request model for Avro Schema export endpoint."""

    namespace: str = Field(
        description="Avro namespace for types (required)", json_schema_extra={"x-cli-flag": "--namespace"}
    )


class AvroProtocolExportRequest(BaseExportRequest):
    """Request model for Avro Protocol (IDL) export endpoint."""

    namespace: str = Field(
        description="Avro namespace for types (required)", json_schema_extra={"x-cli-flag": "--namespace"}
    )
    strict: bool = Field(
        default=False, description="Enforce strict type translation", json_schema_extra={"x-cli-flag": "--strict"}
    )
