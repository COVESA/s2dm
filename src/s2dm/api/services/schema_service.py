"""Schema processing service for API endpoints."""

from pathlib import Path

from graphql import DocumentNode, GraphQLSchema

from s2dm.api.errors import ResponseError, format_error_list, to_response_error
from s2dm.api.models.base import (
    BaseInput,
    ConfigInput,
    DependencyInput,
    FileContentInput,
    SchemaIdInput,
    SchemaInput,
)
from s2dm.api.services.schema_store import resolve_schema_reference
from s2dm.exporters.utils.annotated_schema import AnnotatedSchema
from s2dm.exporters.utils.schema_loader import (
    check_correct_schema,
    download_schema_to_temp,
    load_and_process_schema,
)
from s2dm.utils.file import temp_file_from_content


def process_schema_input(schema_input: SchemaInput) -> Path:
    """Process schema input (path, URL, content, or schema reference) and return Path object."""
    if schema_input.type == "url":
        return download_schema_to_temp(str(schema_input.url))
    if isinstance(schema_input, SchemaIdInput | DependencyInput):
        return resolve_schema_reference(schema_input)
    return path_for_content(schema_input, "schema", ".graphql")


def path_for_content(source: BaseInput | FileContentInput, filename: str, extension: str) -> Path:
    """
    Get a Path for a BaseInput, creating a temp file if needed.

    Args:
        source: Input (PathInput, ContentInput, or FileContentInput)
        filename: Base filename for temp file (if needed)
        extension: File extension including dot (e.g., ".yaml", ".graphql")

    Returns:
        Path object - either the original path or newly created temp file

    Raises:
        FileNotFoundError: If PathInput path doesn't exist
    """
    if source.type == "path":
        return Path(source.path)
    if source.type == "file_content":
        return temp_file_from_content(content=source.content, filename=source.filename)
    return temp_file_from_content(
        content=source.content,
        suffix=extension,
        prefix=f"{filename}_",
    )


def load_validated_schema(
    schemas: list[SchemaInput],
    naming_config_input: ConfigInput | None,
    selection_query_input: ConfigInput | None,
    root_type: str | None,
    expanded_instances: bool,
) -> tuple[AnnotatedSchema, DocumentNode | None]:
    """
    Load, process, and validate schema inputs coming from the API.

    Args:
        schemas: List of schema inputs (paths or URLs)
        naming_config_input: Optional naming configuration (path or content)
        selection_query_input: Optional selection query (path or content)
        root_type: Optional root type for filtering
        expanded_instances: Whether to expand instance tags

    Returns:
        Tuple of (AnnotatedSchema, selection query DocumentNode)
    """
    try:
        schema_paths = [process_schema_input(schema_input) for schema_input in schemas]

        naming_config_path = (
            path_for_content(naming_config_input, "naming_config", ".yaml") if naming_config_input else None
        )
        selection_query_path = (
            path_for_content(selection_query_input, "selection_query", ".graphql") if selection_query_input else None
        )

        annotated_schema, _, query_document = load_and_process_schema(
            schema_paths=schema_paths,
            naming_config_path=naming_config_path,
            selection_query_path=selection_query_path,
            root_type=root_type,
            expanded_instances=expanded_instances,
        )

        validate_schema_or_raise(annotated_schema.schema)
    except Exception as error:
        response_error = to_response_error(error)
        if response_error is not None:
            raise response_error from error
        if isinstance(error, ValueError | TypeError):
            raise ResponseError(str(error)) from error
        raise

    return annotated_schema, query_document


def validate_schema_or_raise(schema: GraphQLSchema) -> None:
    """Run schema correctness checks and raise a ResponseError if any fail."""
    schema_errors = check_correct_schema(schema)
    if schema_errors:
        raise ResponseError(format_error_list("Schema validation failed", schema_errors))
