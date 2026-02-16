"""Avro export routes."""

from typing import cast

from fastapi import APIRouter
from graphql import DocumentNode

from s2dm.api.config import COMMON_RESPONSES
from s2dm.api.models.avro import AvroProtocolExportRequest, AvroSchemaExportRequest
from s2dm.api.models.base import ApiResponse
from s2dm.api.services.response_service import execute_and_respond
from s2dm.api.services.schema_service import load_and_process_schema_wrapper
from s2dm.exporters.avro import translate_to_avro_protocol, translate_to_avro_schema
from s2dm.exporters.utils.schema_loader import check_correct_schema

router = APIRouter(responses=COMMON_RESPONSES)


@router.post(
    "/avro/schema",
    response_model=ApiResponse,
    openapi_extra={"x-exporter-name": "Avro Schema", "x-cli-command-name": "avro schema"},
)
def export_avro_schema(request: AvroSchemaExportRequest) -> ApiResponse:
    """Export GraphQL schema to Avro Schema."""

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

        avro_schema = translate_to_avro_schema(annotated_schema, request.namespace, cast(DocumentNode, query_document))
        return [avro_schema]

    return execute_and_respond(executor=process_request, result_format="avsc")


@router.post(
    "/avro/protocol",
    response_model=ApiResponse,
    openapi_extra={"x-exporter-name": "Avro Protocol", "x-cli-command-name": "avro protocol"},
)
def export_avro_protocol(request: AvroProtocolExportRequest) -> ApiResponse:
    """Export GraphQL schema to Avro Protocol (IDL)."""

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

        protocols = translate_to_avro_protocol(annotated_schema, request.namespace, request.strict)
        return list(protocols.values())

    return execute_and_respond(executor=process_request, result_format="avdl")
