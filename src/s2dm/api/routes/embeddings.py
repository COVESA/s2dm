"""Schema embeddings routes: build cached embeddings and search them."""

from fastapi import APIRouter

from s2dm.api.config import COMMON_RESPONSES
from s2dm.api.models.embeddings import EmbeddingsBuildResponse, EmbeddingsRequest, EmbeddingsSearchRequest
from s2dm.api.services.embeddings_service import build_schema_embeddings, search_schema_embeddings
from s2dm.tools.embeddings.search import SearchHit

router = APIRouter(responses=COMMON_RESPONSES)


@router.post("/build", response_model=EmbeddingsBuildResponse)
def build_embeddings(request: EmbeddingsRequest) -> EmbeddingsBuildResponse:
    """Build and cache the embeddings of a schema, or reuse cached ones, and return their id."""
    embeddings_id = build_schema_embeddings(request.schemas)
    return EmbeddingsBuildResponse(embeddings_id=embeddings_id)


@router.post("/search", response_model=list[SearchHit], response_model_exclude_none=True)
def search_embeddings(request: EmbeddingsSearchRequest) -> list[SearchHit]:
    """Rank the elements of cached embeddings by meaning against a free-text query."""
    return search_schema_embeddings(request.embeddings_id, request.query, request.limit)
