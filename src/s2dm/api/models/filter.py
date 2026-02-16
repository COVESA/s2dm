"""Models for schema filter endpoint."""

from pydantic import BaseModel, Field

from s2dm.api.models.base import ConfigInput, SchemaInput


class FilterSchemaRequest(BaseModel):
    """Request model for filtering a schema based on selection query."""

    schemas: list[SchemaInput] = Field(..., description="GraphQL schema files to filter")
    selection_query: ConfigInput = Field(..., description="GraphQL query to use for filtering the schema")
