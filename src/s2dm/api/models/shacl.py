from pydantic import Field

from s2dm.api.models.base import BaseExportRequest


class ShaclExportRequest(BaseExportRequest):
    """Request model for SHACL export endpoint."""

    serialization_format: str = Field(
        default="ttl",
        description="RDF serialization format",
        json_schema_extra={"x-cli-flag": "--serialization-format"},
    )
    shapes_namespace: str = Field(
        default="http://example.ns/shapes#",
        description="Namespace for SHACL shapes",
        json_schema_extra={"x-cli-flag": "--shapes-namespace"},
    )
    shapes_namespace_prefix: str = Field(
        default="shapes",
        description="Prefix for SHACL shapes namespace",
        json_schema_extra={"x-cli-flag": "--shapes-namespace-prefix"},
    )
    model_namespace: str = Field(
        default="http://example.ns/model#",
        description="Namespace for the data model",
        json_schema_extra={"x-cli-flag": "--model-namespace"},
    )
    model_namespace_prefix: str = Field(
        default="model",
        description="Prefix for the data model namespace",
        json_schema_extra={"x-cli-flag": "--model-namespace-prefix"},
    )
