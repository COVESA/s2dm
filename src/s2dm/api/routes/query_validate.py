"""Query validate route - validate GraphQL query against schema."""

from fastapi import APIRouter
from graphql import parse, print_schema, validate

from s2dm.api.config import COMMON_RESPONSES
from s2dm.api.models.base import ApiResponse
from s2dm.api.models.query_validate import ValidateQueryRequest
from s2dm.api.services.response_service import execute_and_respond
from s2dm.api.services.schema_service import path_for_content, process_schema_input
from s2dm.exporters.utils.schema_loader import load_schema

router = APIRouter(responses=COMMON_RESPONSES)


@router.post("/validate", response_model=ApiResponse)
def validate_query(request: ValidateQueryRequest) -> ApiResponse:
    """Validate a GraphQL query against a schema. Returns the schema if validation succeeds."""

    def process_request() -> list[str]:
        schema_paths = [process_schema_input(schema_input) for schema_input in request.schemas]

        schema = load_schema(schema_paths)

        query_path = path_for_content(request.selection_query, "selection_query", ".graphql")
        query_text = query_path.read_text(encoding="utf-8")

        query_document = parse(query_text)

        validation_errors = validate(schema, query_document)

        if validation_errors:
            error_messages = [f"  - {error.message}" for error in validation_errors]
            raise ValueError(f"Query validation failed: {'; '.join(error_messages)}")

        schema_content = print_schema(schema)
        return [schema_content]

    return execute_and_respond(executor=process_request, result_format="graphql")
