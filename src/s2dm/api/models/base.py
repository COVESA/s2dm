from typing import Any, Literal

from pydantic import AnyHttpUrl, BaseModel, Field, FilePath


class PathInput(BaseModel):
    """Input referencing a file path on the server filesystem."""

    type: Literal["path"] = Field(description="Input type discriminator")
    path: FilePath = Field(description="Absolute or relative path to file on server filesystem")


class UrlInput(BaseModel):
    """Input referencing a remote URL."""

    type: Literal["url"] = Field(description="Input type discriminator")
    url: AnyHttpUrl = Field(description="URL to fetch the resource from")


class ContentInput(BaseModel):
    """Input with inline content."""

    type: Literal["content"] = Field(description="Input type discriminator")
    content: str = Field(description="Inline content as string")


BaseInput = PathInput | ContentInput
ConfigInput = BaseInput
SchemaInput = BaseInput | UrlInput


class BaseExportRequest(BaseModel):
    """Base request model for all export endpoints with common parameters."""

    schemas: list[SchemaInput] = Field(
        description="Array of schema inputs (paths or URLs)",
        json_schema_extra={"x-property-format": "graphql", "x-cli-flag": "--schema"},
    )
    selection_query: ConfigInput | None = Field(
        default=None,
        description="Optional GraphQL query for filtering (path or inline content)",
        json_schema_extra={"x-property-format": "graphql", "x-cli-flag": "--selection-query"},
    )
    naming_config: ConfigInput | None = Field(
        default=None,
        description="Optional YAML naming configuration (path or inline content)",
        json_schema_extra={"x-property-format": "yaml", "x-cli-flag": "--naming-config"},
    )
    root_type: str | None = Field(
        default=None,
        description="Optional root type name for filtering the schema",
        json_schema_extra={"x-cli-flag": "--root-type"},
    )
    expanded_instances: bool = Field(
        default=False,
        description="Whether to expand instance tags into nested structures",
        json_schema_extra={"x-cli-flag": "--expanded-instances"},
    )


class QueryBasedExportRequest(BaseExportRequest):
    """Export request that requires a selection query."""

    selection_query: ConfigInput = Field(
        description="GraphQL query for filtering (path or inline content)",
        json_schema_extra={"x-property-format": "graphql", "x-cli-flag": "--selection-query"},
    )


class ResponseMetadata(BaseModel):
    """Metadata for API responses."""

    result_format: str = Field(description="Format of the result content")
    processing_time_ms: int | None = Field(default=None, description="Processing time in milliseconds")


class ApiResponse(BaseModel):
    """Standard response model for API endpoints."""

    result: list[str] = Field(description="Array of result content strings (schemas, exports, etc.)")
    metadata: ResponseMetadata | None = Field(
        default=None, description="Response metadata (only present if there is a result)"
    )


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(description="Error type or category")
    message: str = Field(description="Detailed error message")
    details: dict[str, Any] | None = Field(default=None, description="Additional error context")
