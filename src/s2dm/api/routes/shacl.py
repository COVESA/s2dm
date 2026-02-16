"""SHACL export route."""

from fastapi import APIRouter

from s2dm.api.config import COMMON_RESPONSES
from s2dm.api.models.base import ApiResponse
from s2dm.api.models.shacl import ShaclExportRequest
from s2dm.api.services.response_service import execute_and_respond
from s2dm.api.services.schema_service import load_and_process_schema_wrapper
from s2dm.exporters.shacl import translate_to_shacl
from s2dm.exporters.utils.schema_loader import check_correct_schema

router = APIRouter(responses=COMMON_RESPONSES)


@router.post(
    "/shacl",
    response_model=ApiResponse,
    openapi_extra={"x-exporter-name": "SHACL", "x-cli-command-name": "shacl"},
)
def export_shacl(request: ShaclExportRequest) -> ApiResponse:
    """Export GraphQL schema to SHACL shapes."""

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

        graph = translate_to_shacl(
            annotated_schema,
            request.shapes_namespace,
            request.shapes_namespace_prefix,
            request.model_namespace,
            request.model_namespace_prefix,
        )

        result_str = graph.serialize(format=request.serialization_format)
        if isinstance(result_str, bytes):
            result_str = result_str.decode("utf-8")
        return [result_str]

    return execute_and_respond(executor=process_request, result_format=request.serialization_format)
