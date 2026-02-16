"""S2DM Export REST API application."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from graphql import GraphQLError, GraphQLSyntaxError

from s2dm import __version__, log
from s2dm.api.models.base import ErrorResponse
from s2dm.api.routes import avro, filter, jsonschema, protobuf, query_validate, shacl, validate, vspec

app = FastAPI(
    title="S2DM Export API",
    description="REST API for exporting GraphQL schemas to various formats and validating schemas and queries.",
    version=__version__,
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/capabilities",
)

# FIXME: In production, CORS should be configured more restrictively to allow only trusted origins.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
def request_validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic request validation errors."""
    errors = exc.errors()
    validation_errors = [{"loc": err["loc"], "msg": err["msg"], "type": err["type"]} for err in errors]
    error_response = ErrorResponse(
        error="BadRequest",
        message="Request contains missing fields or incorrect types",
        details={"validation_errors": validation_errors},
    )
    log.warning(f"Request validation error: {exc}")
    return JSONResponse(status_code=400, content=error_response.model_dump())


@app.exception_handler(FileNotFoundError)
def file_not_found_handler(request: Request, exc: FileNotFoundError) -> JSONResponse:
    """Handle file not found errors."""
    error_response = ErrorResponse(error="FileNotFound", message="Requested file not found", details=None)
    log.warning(f"File not found: {exc}")
    return JSONResponse(status_code=400, content=error_response.model_dump())


@app.exception_handler(RuntimeError)
def runtime_error_handler(request: Request, exc: RuntimeError) -> JSONResponse:
    """Handle runtime errors (e.g., URL download failures)."""
    error_response = ErrorResponse(error="RuntimeError", message="A runtime error occurred", details=None)
    log.warning(f"Runtime error: {exc}")
    return JSONResponse(status_code=400, content=error_response.model_dump())


@app.exception_handler(ValueError)
def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle validation errors."""
    error_response = ErrorResponse(error="ValidationError", message="Invalid input provided", details=None)
    log.warning(f"Validation error: {exc}")
    return JSONResponse(status_code=422, content=error_response.model_dump())


@app.exception_handler(TypeError)
def type_error_handler(request: Request, exc: TypeError) -> JSONResponse:
    """Handle type errors (e.g., GraphQL directive errors)."""
    error_response = ErrorResponse(error="ValidationError", message="Invalid type provided", details=None)
    log.warning(f"Type error: {exc}")
    return JSONResponse(status_code=422, content=error_response.model_dump())


@app.exception_handler(GraphQLSyntaxError)
def graphql_syntax_error_handler(request: Request, exc: GraphQLSyntaxError) -> JSONResponse:
    """Handle GraphQL syntax errors."""
    error_response = ErrorResponse(error="GraphQLSyntaxError", message="Invalid GraphQL syntax", details=None)
    log.warning(f"GraphQL syntax error: {exc}")
    return JSONResponse(status_code=422, content=error_response.model_dump())


@app.exception_handler(GraphQLError)
def graphql_error_handler(request: Request, exc: GraphQLError) -> JSONResponse:
    """Handle GraphQL errors."""
    error_response = ErrorResponse(error="GraphQLError", message="GraphQL validation failed", details=None)
    log.warning(f"GraphQL error: {exc}")
    return JSONResponse(status_code=422, content=error_response.model_dump())


@app.exception_handler(Exception)
def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors."""
    error_response = ErrorResponse(error="ServerError", message="An internal server error occurred", details=None)
    log.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content=error_response.model_dump())


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "version": __version__}


app.include_router(shacl.router, prefix="/api/v1/export", tags=["export"])
app.include_router(vspec.router, prefix="/api/v1/export", tags=["export"])
app.include_router(jsonschema.router, prefix="/api/v1/export", tags=["export"])
app.include_router(avro.router, prefix="/api/v1/export", tags=["export"])
app.include_router(protobuf.router, prefix="/api/v1/export", tags=["export"])
app.include_router(filter.router, prefix="/api/v1/schema", tags=["schema"])
app.include_router(validate.router, prefix="/api/v1/schema", tags=["schema"])
app.include_router(query_validate.router, prefix="/api/v1/query", tags=["query"])
