"""Dependency resolution routes."""

from fastapi import APIRouter, Query, Response
from fastapi.responses import JSONResponse

from s2dm.api.config import COMMON_RESPONSES
from s2dm.api.errors import ResourceNotFoundError
from s2dm.api.models.base import ApiResponse, ErrorResponse
from s2dm.api.models.deps import (
    BuildDependenciesRequest,
    DependenciesApiResponse,
    DependenciesIdentities,
    DependenciesStatusResponse,
    GetDependenciesConfigResponse,
    LoadReleaseRequest,
    LoadReleaseResponse,
    ResolveDependenciesRequest,
    SaveDependenciesConfigRequest,
)
from s2dm.api.services.deps_service import (
    build_api_dependencies,
    delete_dependencies_identities,
    list_api_releases,
    load_api_release,
    load_dependencies_config,
    load_dependencies_identities,
    load_dependencies_status,
    resolve_api_dependencies,
    save_dependencies_config,
    save_dependencies_identities,
)
from s2dm.api.services.response_service import execute_and_respond
from s2dm.deps.models import ReleasePage
from s2dm.deps.resolve.errors import (
    DependencyConfigError,
    DependencyInternalError,
    DependencySourceError,
    DependencyUpstreamError,
)

CONFIG_RESPONSES = {
    **COMMON_RESPONSES,
    404: {"model": ErrorResponse, "description": "Dependency config is not stored"},
}

IDENTITIES_RESPONSES = {
    **COMMON_RESPONSES,
    404: {"model": ErrorResponse, "description": "Dependency identities are not stored"},
}

RESOLVE_RESPONSES = {
    **COMMON_RESPONSES,
    200: {"model": DependenciesApiResponse, "description": "Dependency resolution succeeded with warnings"},
    204: {"description": "Dependency resolution succeeded without warnings"},
    404: {"model": ErrorResponse, "description": "Dependency config is not stored"},
    422: {"model": ErrorResponse, "description": "Dependency resolution failed due to invalid config or source issues"},
    502: {
        "model": ErrorResponse,
        "description": "Dependency resolution failed because an upstream dependency provider failed",
    },
}

BUILD_RESPONSES = {
    **COMMON_RESPONSES,
    200: {"model": ApiResponse, "description": "Dependency build succeeded"},
    404: {"model": ErrorResponse, "description": "Dependency config is not stored"},
    422: {"model": ErrorResponse, "description": "Dependency build failed due to invalid config or schema issues"},
}

RELEASES_RESPONSES = {
    **COMMON_RESPONSES,
    422: {
        "model": ErrorResponse,
        "description": "The repository URL is invalid, the release is inaccessible, or its asset is unusable",
    },
    502: {"model": ErrorResponse, "description": "The release provider failed"},
}

router = APIRouter()


@router.get(
    "/config",
    response_model=GetDependenciesConfigResponse,
    response_model_exclude_unset=True,
    responses=CONFIG_RESPONSES,
)
def get_dependencies_config() -> GetDependenciesConfigResponse:
    """Retrieve the stored dependency configuration."""
    return load_dependencies_config()


@router.get("/status", response_model=DependenciesStatusResponse, responses=COMMON_RESPONSES)
def get_dependencies_status() -> DependenciesStatusResponse:
    """Retrieve dependency resolution status."""
    return load_dependencies_status()


@router.post("/config", status_code=204, responses=CONFIG_RESPONSES)
def store_dependencies_config(request: SaveDependenciesConfigRequest) -> Response:
    """Store dependency configuration in the API-managed workspace."""
    save_dependencies_config(request)
    return Response(status_code=204)


@router.get("/identities", response_model=DependenciesIdentities, responses=IDENTITIES_RESPONSES)
def get_dependencies_identities() -> DependenciesIdentities:
    """Retrieve the stored dependency identities."""
    return load_dependencies_identities()


@router.post("/identities", status_code=204, responses=IDENTITIES_RESPONSES)
def store_dependencies_identities(request: DependenciesIdentities) -> Response:
    """Store dependency identities in the API-managed workspace."""
    save_dependencies_identities(request)
    return Response(status_code=204)


@router.delete("/identities", status_code=204, responses=IDENTITIES_RESPONSES)
def remove_dependencies_identities() -> Response:
    """Delete stored dependency identities from the API-managed workspace."""
    delete_dependencies_identities()
    return Response(status_code=204)


@router.post("/resolve", status_code=204, responses=RESOLVE_RESPONSES)
def resolve_dependencies(request: ResolveDependenciesRequest) -> Response:
    """Resolve dependencies in the API-managed workspace."""
    try:
        warnings = resolve_api_dependencies(request.clean)
    except (DependencyConfigError, DependencySourceError, DependencyUpstreamError, ResourceNotFoundError):
        # Will be handled by the global exception handler. No need to wrap the error here.
        raise
    except Exception as error:
        raise DependencyInternalError from error

    if not warnings:
        return Response(status_code=204)

    response = DependenciesApiResponse(warnings=warnings)
    return JSONResponse(status_code=200, content=response.model_dump())


@router.post("/build", response_model=ApiResponse, responses=BUILD_RESPONSES)
def build_dependencies(request: BuildDependenciesRequest) -> ApiResponse:
    """Compose vendored dependencies in the API-managed workspace."""

    def process_request() -> list[str]:
        return [build_api_dependencies(request.auto_prefix, request.preserve_query_type)]

    return execute_and_respond(executor=process_request, result_format="graphql")


@router.get("/releases", response_model=ReleasePage, responses=RELEASES_RESPONSES)
def list_releases(
    repository: str = Query(description="Repository URL, https://<host>/<owner>/<repository>"),
    page: int = Query(default=1, ge=1, description="Page number, starting at 1"),
) -> ReleasePage:
    """List one page of the published releases of a remote repository."""
    return list_api_releases(repository, page)


@router.post("/releases/load", response_model=LoadReleaseResponse, responses=RELEASES_RESPONSES)
def load_release(request: LoadReleaseRequest) -> LoadReleaseResponse:
    """Load the schema and metadata of one remote release asset."""
    return load_api_release(request)
