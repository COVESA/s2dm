"""JSON Schema export route."""

from fastapi import APIRouter

from s2dm.api.config import COMMON_RESPONSES
from s2dm.api.models.base import ApiResponse
from s2dm.api.models.jsonschema import JsonSchemaExportRequest
from s2dm.api.services.response_service import execute_and_respond
from s2dm.api.services.schema_service import load_and_process_schema_wrapper
from s2dm.exporters.jsonschema import translate_to_jsonschema
from s2dm.exporters.utils.schema_loader import check_correct_schema

router = APIRouter(responses=COMMON_RESPONSES)


@router.post(
    "/jsonschema",
    response_model=ApiResponse,
    openapi_extra={"x-exporter-name": "JSON Schema", "x-cli-command-name": "jsonschema"},
)
def export_jsonschema(request: JsonSchemaExportRequest) -> ApiResponse:
    """Export GraphQL schema to JSON Schema."""

    def process_request() -> list[str]:
        annotated_schema, _ = load_and_process_schema_wrapper(
            schemas=request.schemas,
            naming_config_input=request.naming_config,
            selection_query_input=request.selection_query,
            root_type=request.root_type,
            expanded_instances=request.expanded_instances,
        )

        schema_errors = check_correct_schema(annotated_schema.schema)
        if schema_errors:
            raise ValueError(f"Schema validation failed: {'; '.join(schema_errors)}")

        json_schema = translate_to_jsonschema(annotated_schema, request.root_type, request.strict)
        return [json_schema]

    return execute_and_respond(executor=process_request, result_format="json")
