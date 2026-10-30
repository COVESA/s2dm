"""Models for schema validate endpoint."""

from pydantic import Field

from s2dm.api.models.base import ApiResponse, SchemasRequest


class ValidateSchemaRequest(SchemasRequest):
    """Request model for composing and validating schemas."""


class ValidateSchemaResponse(ApiResponse):
    """Response model for composing and validating schemas."""

    schema_id: str = Field(
        description="Id of the stored composed schema; send it as a `schema_id` schema input to reuse it"
    )
