"""Protocol Buffers export route."""

from typing import cast

from fastapi import APIRouter
from graphql import DocumentNode

from s2dm.api.config import COMMON_RESPONSES
from s2dm.api.models.base import ApiResponse
from s2dm.api.models.protobuf import ProtobufExportRequest
from s2dm.api.services.response_service import execute_and_respond
from s2dm.api.services.schema_service import load_and_process_schema_wrapper
from s2dm.exporters.protobuf import translate_to_protobuf
from s2dm.exporters.utils.extraction import get_root_level_types_from_query
from s2dm.exporters.utils.schema_loader import check_correct_schema

router = APIRouter(responses=COMMON_RESPONSES)


@router.post(
    "/protobuf",
    response_model=ApiResponse,
    openapi_extra={"x-exporter-name": "Protobuf", "x-cli-command-name": "protobuf"},
)
def export_protobuf(request: ProtobufExportRequest) -> ApiResponse:
    """Export GraphQL schema to Protocol Buffers."""

    def process_request() -> list[str]:
        annotated_schema, query_document = load_and_process_schema_wrapper(
            schemas=request.schemas,
            naming_config_input=request.naming_config,
            selection_query_input=request.selection_query,
            root_type=request.root_type,
            expanded_instances=request.expanded_instances,
        )

        schema_errors = check_correct_schema(annotated_schema.schema)
        if schema_errors:
            raise ValueError(f"Schema validation failed: {'; '.join(schema_errors)}")

        query_document = cast(DocumentNode, query_document)

        flatten_root_types = None
        if request.flatten_naming:
            flatten_root_types = get_root_level_types_from_query(annotated_schema.schema, query_document)

        proto_content = translate_to_protobuf(
            annotated_schema, query_document, request.package_name, flatten_root_types
        )
        return [proto_content]

    return execute_and_respond(executor=process_request, result_format="proto")
