"""Models for schema validate endpoint."""

from pydantic import BaseModel, Field

from s2dm.api.models.base import SchemaInput


class ValidateSchemaRequest(BaseModel):
    """Request model for composing and validating schemas."""

    schemas: list[SchemaInput] = Field(..., description="GraphQL schema files to compose and validate")
