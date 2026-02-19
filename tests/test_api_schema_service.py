"""Tests for API schema service wiring and input dispatch."""

from pathlib import Path
from typing import cast
from unittest.mock import Mock, patch

from pydantic import AnyHttpUrl

from s2dm.api.models.base import ContentInput, PathInput, UrlInput
from s2dm.api.services import schema_service
from s2dm.exporters.utils import schema_loader


class TestLoadAndProcessSchemaWrapper:
    """Test argument forwarding in load_and_process_schema_wrapper."""

    def test_wrapper_forwards_all_arguments(self, tmp_path: Path) -> None:
        """Wrapper forwards converted paths and options to load_and_process_schema."""
        first_schema = ContentInput(type="content", content="type Query { a: String }")
        second_schema = ContentInput(type="content", content="type Query { b: String }")
        naming_config = ContentInput(type="content", content="field:\n  object: snake_case\n")
        selection_query = ContentInput(type="content", content="query Selection { a }")

        first_schema_path = tmp_path / "first.graphql"
        second_schema_path = tmp_path / "second.graphql"
        naming_path = tmp_path / "naming.yaml"
        query_path = tmp_path / "query.graphql"

        expected_annotated_schema = object()
        expected_query_document = object()

        with (
            patch(
                "s2dm.api.services.schema_service.process_schema_input",
                side_effect=[first_schema_path, second_schema_path],
            ) as process_schema_input_mock,
            patch(
                "s2dm.api.services.schema_service.path_for_content",
                side_effect=[naming_path, query_path],
            ) as path_for_content_mock,
            patch(
                "s2dm.api.services.schema_service.load_and_process_schema",
                return_value=(expected_annotated_schema, None, expected_query_document),
            ) as load_and_process_schema_mock,
        ):
            annotated_schema, query_document = schema_service.load_and_process_schema_wrapper(
                schemas=[first_schema, second_schema],
                naming_config_input=naming_config,
                selection_query_input=selection_query,
                root_type="Vehicle",
                expanded_instances=True,
            )

        assert process_schema_input_mock.call_count == 2
        process_schema_input_mock.assert_any_call(first_schema)
        process_schema_input_mock.assert_any_call(second_schema)
        path_for_content_mock.assert_any_call(naming_config, "naming_config", ".yaml")
        path_for_content_mock.assert_any_call(selection_query, "selection_query", ".graphql")
        load_and_process_schema_mock.assert_called_once_with(
            schema_paths=[first_schema_path, second_schema_path],
            naming_config_path=naming_path,
            selection_query_path=query_path,
            root_type="Vehicle",
            expanded_instances=True,
        )
        assert annotated_schema is expected_annotated_schema
        assert query_document is expected_query_document

    def test_wrapper_omits_optional_paths_when_not_provided(self) -> None:
        """Wrapper forwards None for optional config/query inputs when omitted."""
        schema_input = ContentInput(type="content", content="type Query { a: String }")
        expected_schema_path = Path("/tmp/schema.graphql")
        expected_annotated_schema = object()

        with (
            patch(
                "s2dm.api.services.schema_service.process_schema_input",
                return_value=expected_schema_path,
            ) as process_schema_input_mock,
            patch("s2dm.api.services.schema_service.path_for_content") as path_for_content_mock,
            patch(
                "s2dm.api.services.schema_service.load_and_process_schema",
                return_value=(expected_annotated_schema, None, None),
            ) as load_and_process_schema_mock,
        ):
            annotated_schema, query_document = schema_service.load_and_process_schema_wrapper(
                schemas=[schema_input],
                naming_config_input=None,
                selection_query_input=None,
                root_type=None,
                expanded_instances=False,
            )

        process_schema_input_mock.assert_called_once_with(schema_input)
        path_for_content_mock.assert_not_called()
        load_and_process_schema_mock.assert_called_once_with(
            schema_paths=[expected_schema_path],
            naming_config_path=None,
            selection_query_path=None,
            root_type=None,
            expanded_instances=False,
        )
        assert annotated_schema is expected_annotated_schema
        assert query_document is None


class TestProcessSchemaInputDispatch:
    """Test dispatch logic in process_schema_input."""

    def test_url_input_uses_downloader(self, tmp_path: Path) -> None:
        """URL inputs are resolved by download_schema_to_temp."""
        downloaded_path = tmp_path / "downloaded.graphql"
        schema_input = UrlInput(type="url", url=cast(AnyHttpUrl, "https://example.com/schema.graphql"))

        with patch(
            "s2dm.api.services.schema_service.download_schema_to_temp",
            return_value=downloaded_path,
        ) as download_mock:
            result = schema_service.process_schema_input(schema_input)

        download_mock.assert_called_once_with("https://example.com/schema.graphql")
        assert result == downloaded_path

    def test_schema_service_url_path_calls_schema_loader_downloader(self) -> None:
        """URL dispatch calls schema_service downloader wired to schema_loader logic."""
        schema_input = UrlInput(type="url", url=cast(AnyHttpUrl, "https://example.com/schema.graphql"))
        mock_response = Mock()
        mock_response.text = "type Query { ping: String }"
        mock_response.headers = {}
        mock_response.raise_for_status = Mock()

        with (
            patch("s2dm.exporters.utils.schema_loader.requests.get", return_value=mock_response),
            patch(
                "s2dm.api.services.schema_service.download_schema_to_temp",
                wraps=schema_loader.download_schema_to_temp,
            ) as download_spy,
        ):
            result = schema_service.process_schema_input(schema_input)

        download_spy.assert_called_once_with("https://example.com/schema.graphql")
        assert result.exists()
        assert result.suffix == ".graphql"
        result.unlink()

    def test_content_input_converts_to_temp_path(self, tmp_path: Path) -> None:
        """Content inputs are delegated to path_for_content with schema parameters."""
        expected_path = tmp_path / "schema.graphql"
        schema_input = ContentInput(type="content", content="type Query { ping: String }")

        with patch("s2dm.api.services.schema_service.path_for_content", return_value=expected_path) as path_mock:
            result = schema_service.process_schema_input(schema_input)

        path_mock.assert_called_once_with(schema_input, "schema", ".graphql")
        assert result == expected_path

    def test_path_input_preserves_path(self, tmp_path: Path) -> None:
        """Path inputs are delegated to path_for_content with schema parameters."""
        source_path = tmp_path / "schema.graphql"
        source_path.write_text("type Query { ping: String }", encoding="utf-8")
        schema_input = PathInput(type="path", path=source_path)

        with patch("s2dm.api.services.schema_service.path_for_content", return_value=source_path) as path_mock:
            result = schema_service.process_schema_input(schema_input)

        path_mock.assert_called_once_with(schema_input, "schema", ".graphql")
        assert result == source_path
