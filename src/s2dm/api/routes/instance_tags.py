"""Schema instance tags route."""

from fastapi import APIRouter

from s2dm.api.config import COMMON_RESPONSES
from s2dm.api.models.instance_tags import InstanceTagsRequest, InstanceTagsResponse
from s2dm.api.services.schema_service import load_validated_schema
from s2dm.exporters.utils.instance_tag import get_instance_tag_fields

router = APIRouter(responses=COMMON_RESPONSES)


@router.post("/instance-tags", response_model=InstanceTagsResponse)
def get_instance_tags(request: InstanceTagsRequest) -> InstanceTagsResponse:
    """Index the instance tag fields of a schema by `Type.field`, with what @pick can name on each."""
    annotated_schema, _ = load_validated_schema(
        schemas=request.schemas,
        naming_config_input=None,
        selection_query_input=None,
        root_type=None,
        expanded_instances=False,
    )

    tag_fields = get_instance_tag_fields(annotated_schema.schema)
    return InstanceTagsResponse(tag_fields)
