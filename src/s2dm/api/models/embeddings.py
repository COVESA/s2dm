"""Request and response models for the embeddings endpoints.

Search responses reuse ``SearchHit`` from `s2dm.tools.embeddings.search` directly.
"""

from pydantic import BaseModel, Field, field_validator

from s2dm.api.models.base import SHA256_ID_PATTERN, SchemasRequest


class EmbeddingsRequest(SchemasRequest):
    """Request model for building the embeddings of a schema."""


class EmbeddingsBuildResponse(BaseModel):
    """Response model identifying a schema's cached embeddings."""

    embeddings_id: str = Field(description="Id of the cached embeddings, used to search them")


class EmbeddingsSearchRequest(BaseModel):
    """Request model for searching cached embeddings."""

    embeddings_id: str = Field(pattern=SHA256_ID_PATTERN, description="Id returned by the build endpoint")
    query: str = Field(description="Free-text search query")
    limit: int = Field(default=10, ge=1, description="Maximum number of results")

    @field_validator("query")
    @classmethod
    def reject_blank_query(cls, query: str) -> str:
        """Reject queries that are empty or only whitespace."""
        if not query.strip():
            raise ValueError("The query is empty")
        return query
