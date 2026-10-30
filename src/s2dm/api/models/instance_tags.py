"""Models for the schema instance tags endpoint."""

from pydantic import RootModel

from s2dm.api.models.base import SchemasRequest
from s2dm.exporters.utils.instance_tag import InstanceTagFieldInfo


class InstanceTagsRequest(SchemasRequest):
    """Request model for indexing the instance tag fields of a schema."""


class InstanceTagsResponse(RootModel[dict[str, InstanceTagFieldInfo]]):
    """The instance tag fields of a schema, by `Type.field`."""
