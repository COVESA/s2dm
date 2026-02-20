"""Schema processing service for API endpoints."""

from pathlib import Path

from graphql import DocumentNode

from s2dm.api.models.base import BaseInput, ConfigInput, SchemaInput
from s2dm.exporters.utils.annotated_schema import AnnotatedSchema
from s2dm.exporters.utils.schema_loader import download_schema_to_temp, load_and_process_schema
from s2dm.utils.file import temp_file_from_content


def process_schema_input(schema_input: SchemaInput) -> Path:
    """Process schema input (path, URL, or content) and return Path object."""
    if schema_input.type == "url":
        return download_schema_to_temp(str(schema_input.url))
    else:
        return path_for_content(schema_input, "schema", ".graphql")


def path_for_content(source: BaseInput, filename: str, extension: str) -> Path:
    """
    Get a Path for a BaseInput, creating a temp file if needed.

    Args:
        source: Input (PathInput or ContentInput)
        filename: Base filename for temp file (if needed)
        extension: File extension including dot (e.g., ".yaml", ".graphql")

    Returns:
        Path object - either the original path or newly created temp file

    Raises:
        FileNotFoundError: If PathInput path doesn't exist
    """
    if source.type == "path":
        return Path(source.path)
    else:
        return temp_file_from_content(
            content=source.content,
            suffix=extension,
            prefix=f"{filename}_",
        )


def load_and_process_schema_wrapper(
    schemas: list[SchemaInput],
    naming_config_input: ConfigInput | None,
    selection_query_input: ConfigInput | None,
    root_type: str | None,
    expanded_instances: bool,
) -> tuple[AnnotatedSchema, DocumentNode | None]:
    """
    Wrapper for load_and_process_schema that handles API input types.

    Args:
        schemas: List of schema inputs (paths or URLs)
        naming_config_input: Optional naming configuration (path or content)
        selection_query_input: Optional selection query (path or content)
        root_type: Optional root type for filtering
        expanded_instances: Whether to expand instance tags

    Returns:
        Tuple of (AnnotatedSchema, selection query DocumentNode)

    Raises:
        FileNotFoundError: If any path doesn't exist
        ValueError: If schema validation fails
        GraphQLSyntaxError: If query parsing fails
    """
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

    return annotated_schema, query_document
