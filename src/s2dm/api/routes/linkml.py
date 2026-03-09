"""LinkML export route."""

from fastapi import APIRouter

from s2dm.api.config import COMMON_RESPONSES
from s2dm.api.models.base import ApiResponse
from s2dm.api.models.linkml import LinkmlExportRequest
from s2dm.api.services.response_service import execute_and_respond
from s2dm.api.services.schema_service import load_and_process_schema_wrapper
from s2dm.exporters.linkml import translate_to_linkml
from s2dm.exporters.utils.schema_loader import check_correct_schema

router = APIRouter(responses=COMMON_RESPONSES)


@router.post(
    "/linkml",
    response_model=ApiResponse,
    openapi_extra={"x-exporter-name": "LinkML", "x-cli-command-name": "linkml"},
)
def export_linkml(request: LinkmlExportRequest) -> ApiResponse:
    """Export GraphQL schema to LinkML."""

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

        linkml_content = translate_to_linkml(
            annotated_schema,
            request.id,
            request.name,
            request.default_prefix,
            request.default_prefix_url,
        )
        return [linkml_content]

    return execute_and_respond(executor=process_request, result_format="yaml")
