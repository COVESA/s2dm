"""Models for query validate endpoint."""

from pydantic import BaseModel, Field

from s2dm.api.models.base import ConfigInput, SchemaInput


class ValidateQueryRequest(BaseModel):
    """Request model for validating a GraphQL query against a schema."""

    schemas: list[SchemaInput] = Field(..., description="GraphQL schema files to validate against")
    selection_query: ConfigInput = Field(..., description="GraphQL query to validate")
