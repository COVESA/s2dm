"""Schema filter route."""

from fastapi import APIRouter

from s2dm.api.config import COMMON_RESPONSES
from s2dm.api.models.base import ApiResponse
from s2dm.api.models.filter import FilterSchemaRequest
from s2dm.api.services.response_service import execute_and_respond
from s2dm.api.services.schema_service import load_and_process_schema_wrapper
from s2dm.exporters.utils.schema_loader import print_schema_with_directives_preserved

router = APIRouter(responses=COMMON_RESPONSES)


@router.post("/filter", response_model=ApiResponse)
def filter_schema(request: FilterSchemaRequest) -> ApiResponse:
    """Filter a GraphQL schema based on selection query."""

    def process_request() -> list[str]:
        annotated_schema, _ = load_and_process_schema_wrapper(
            schemas=request.schemas,
            naming_config_input=None,
            selection_query_input=request.selection_query,
            root_type=None,
            expanded_instances=False,
        )

        filtered_schema = print_schema_with_directives_preserved(annotated_schema.schema, source_map=None)
        return [filtered_schema]

    return execute_and_respond(executor=process_request, result_format="graphql")
