"""VSPEC export route."""

from fastapi import APIRouter

from s2dm.api.config import COMMON_RESPONSES
from s2dm.api.models.base import ApiResponse, BaseExportRequest
from s2dm.api.services.response_service import execute_and_respond
from s2dm.api.services.schema_service import load_and_process_schema_wrapper
from s2dm.exporters.utils.schema_loader import check_correct_schema
from s2dm.exporters.vspec import translate_to_vspec

router = APIRouter(responses=COMMON_RESPONSES)


@router.post(
    "/vspec", response_model=ApiResponse, openapi_extra={"x-exporter-name": "VSpec", "x-cli-command-name": "vspec"}
)
def export_vspec(request: BaseExportRequest) -> ApiResponse:
    """Export GraphQL schema to VSPEC."""

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

        vspec_content = translate_to_vspec(annotated_schema)
        return [vspec_content]

    return execute_and_respond(executor=process_request, result_format="vspec")
