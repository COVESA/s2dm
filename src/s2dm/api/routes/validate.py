"""Schema validate route - compose and validate GraphQL schemas."""

from fastapi import APIRouter

from s2dm.api.config import COMMON_RESPONSES
from s2dm.api.models.validate import ValidateSchemaRequest, ValidateSchemaResponse
from s2dm.api.services.response_service import execute_and_respond
from s2dm.api.services.schema_service import process_schema_input, validate_schema_or_raise
from s2dm.api.services.schema_store import store_schema_text
from s2dm.exporters.utils.schema_loader import (
    load_schema_with_source_map,
    print_schema_with_directives_preserved,
)

router = APIRouter(responses=COMMON_RESPONSES)


@router.post("/validate", response_model=ValidateSchemaResponse)
def validate_schema(request: ValidateSchemaRequest) -> ValidateSchemaResponse:
    """Compose and validate GraphQL schemas, storing the composed schema for later reference."""

    def process_request() -> list[str]:
        schema_paths = [process_schema_input(schema_input) for schema_input in request.schemas]

        schema, source_map = load_schema_with_source_map(schema_paths, naming_config=None)

        validate_schema_or_raise(schema)

        validated_schema = print_schema_with_directives_preserved(schema, source_map)
        return [validated_schema]

    response = execute_and_respond(executor=process_request, result_format="graphql")
    composed_schema = response.result[0]
    schema_id = store_schema_text(composed_schema)
    return ValidateSchemaResponse(result=response.result, metadata=response.metadata, schema_id=schema_id)
