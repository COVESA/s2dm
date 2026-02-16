"""Schema validate route - compose and validate GraphQL schemas."""

from fastapi import APIRouter

from s2dm.api.config import COMMON_RESPONSES
from s2dm.api.models.base import ApiResponse
from s2dm.api.models.validate import ValidateSchemaRequest
from s2dm.api.services.response_service import execute_and_respond
from s2dm.api.services.schema_service import process_schema_input
from s2dm.exporters.utils.schema_loader import (
    check_correct_schema,
    load_schema_with_source_map,
    print_schema_with_directives_preserved,
)

router = APIRouter(responses=COMMON_RESPONSES)


@router.post("/validate", response_model=ApiResponse)
def validate_schema(request: ValidateSchemaRequest) -> ApiResponse:
    """Compose and validate GraphQL schemas."""

    def process_request() -> list[str]:
        schema_paths = [process_schema_input(schema_input) for schema_input in request.schemas]

        schema, source_map = load_schema_with_source_map(schema_paths, naming_config=None)

        errors = check_correct_schema(schema)
        if errors:
            raise ValueError(f"Schema validation failed: {'; '.join(errors)}")

        validated_schema = print_schema_with_directives_preserved(schema, source_map)
        return [validated_schema]

    return execute_and_respond(executor=process_request, result_format="graphql")
