from io import StringIO
from pathlib import Path
from unittest.mock import Mock

import click
import pytest
from faker import Faker
from graphql import GraphQLNamedType, build_schema
from hypothesis import given
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, RDFS, SKOS

from s2dm.exporters.skos import (
    SKOSConcept,
    collect_skos_concepts,
    create_skos_graph,
    generate_skos_skeleton,
    validate_skos_graph,
)
from s2dm.tools.validators import validate_language_tag
from tests.conftest import MockFieldData, mock_named_types_strategy


class TestSKOSConceptFormatting:
    """Test SKOS concept creation, formatting, and RDF generation."""

    @pytest.fixture
    def sample_concept(self, faker: Faker) -> SKOSConcept:
        """Create a sample concept for testing."""
        name = faker.word()
        return SKOSConcept(
            name=name,
            pref_label=name,
            language="en",
            definition=faker.sentence(),
        )

    @pytest.fixture
    def sample_graph_and_namespace(self) -> tuple[Graph, Namespace]:
        """Create a sample graph with namespace for testing."""
        return create_skos_graph("https://test.org/", "test")

    def test_add_to_graph_creates_proper_triples(
        self,
        sample_concept: SKOSConcept,
        sample_graph_and_namespace: tuple[Graph, Namespace],
    ) -> None:
        """Test that add_to_graph creates proper RDF triples."""
        graph, namespace = sample_graph_and_namespace

        sample_concept.add_to_graph(graph, namespace)

        # Check that concept was added as SKOS Concept
        concept_ref = namespace[sample_concept.name]

        assert (concept_ref, RDF.type, SKOS.Concept) in graph
        assert (concept_ref, SKOS.prefLabel, None) in graph
        assert (concept_ref, SKOS.definition, None) in graph
        assert (concept_ref, SKOS.note, None) in graph
        assert (concept_ref, RDFS.seeAlso, concept_ref) in graph


class TestLanguageValidation:
    """Test BCP 47 language tag validation."""

    @pytest.fixture
    def mock_click_context(self) -> tuple[click.Context, click.Parameter]:
        """Create mock Click context and parameter for testing."""
        ctx = Mock(spec=click.Context)
        param = Mock(spec=click.Parameter)
        return ctx, param

    @pytest.mark.parametrize("valid_tag", ["en", "en-US", "fr", "de-DE", "zh-CN"])
    def test_accepts_valid_bcp47_tags(
        self, valid_tag: str, mock_click_context: tuple[click.Context, click.Parameter]
    ) -> None:
        """Test that valid BCP 47 language tags are accepted."""
        ctx, param = mock_click_context
        # Should not raise an exception and return the same value
        result = validate_language_tag(ctx=ctx, param=param, value=valid_tag)
        assert result == valid_tag

    @pytest.mark.parametrize(
        "invalid_tag",
        [
            "",  # empty string
            "invalid",  # not a valid language code
            "en-",  # trailing dash
            "en US",  # space character
        ],
    )
    def test_rejects_invalid_language_tags(
        self,
        invalid_tag: str,
        mock_click_context: tuple[click.Context, click.Parameter],
    ) -> None:
        """Test that invalid language tags are rejected."""
        ctx, param = mock_click_context

        with pytest.raises(click.BadParameter):
            validate_language_tag(ctx=ctx, param=param, value=invalid_tag)


class TestGraphQLSchemaProcessing:
    """Test processing of GraphQL schemas into SKOS concepts."""

    @given(named_types_and_fields=mock_named_types_strategy())
    def test_collect_concepts_processes_all_relevant_types(
        self, named_types_and_fields: tuple[list[GraphQLNamedType], list[MockFieldData]]
    ) -> None:
        """Test that collect_skos_concepts processes GraphQL types correctly."""
        named_types, _ = named_types_and_fields

        graph, namespace = create_skos_graph("https://test.org/", "ns")
        collect_skos_concepts(named_types, graph, namespace, "en")

        # Should generate concepts in the graph
        concepts = list(graph.subjects(RDF.type, SKOS.Concept))
        assert len(concepts) > 0

    def test_excludes_query_and_mutation_types(self) -> None:
        """Test that Query and Mutation types are properly excluded."""
        schema_str = """
            type Query { vehicle: Vehicle }
            type Mutation { update: String }
            type Vehicle { name: String }
        """

        schema = build_schema(schema_str)
        named_types = list(schema.type_map.values())

        graph, namespace = create_skos_graph("https://test.org/", "ns")
        collect_skos_concepts(named_types, graph, namespace, "en")

        # Get all concept URIs from the graph
        concepts = list(graph.subjects(RDF.type, SKOS.Concept))
        concept_names = [str(concept).split("/")[-1] for concept in concepts]

        # Should exclude Query and Mutation types
        assert "Query" not in concept_names
        assert "Mutation" not in concept_names
        # Should include Vehicle type
        assert "Vehicle" in concept_names


class TestGraphOperations:
    """Test graph creation, population, and validation functionality."""

    def test_collect_skos_concepts_populates_graph(self) -> None:
        """Test that collect_skos_concepts properly populates a graph."""
        schema_str = """
            type Query { vehicle: Vehicle }
            type Vehicle {
                name: String
                adas: Vehicle_ADAS
            }
            type Vehicle_ADAS {
                isActive: Boolean
            }
        """

        schema = build_schema(schema_str)
        named_types = list(schema.type_map.values())

        graph, namespace = create_skos_graph("https://test.org/", "test")
        collect_skos_concepts(named_types, graph, namespace, "en")

        # Check that concepts were added to the graph
        concepts = list(graph.subjects(RDF.type, SKOS.Concept))
        assert len(concepts) > 0

    def test_validate_skos_graph_catches_missing_preflabel(self) -> None:
        """Test that validation catches concepts missing prefLabel."""
        graph, namespace = create_skos_graph("https://test.org/", "test")

        # Manually add a concept without prefLabel
        concept_ref = namespace["TestConcept"]
        graph.add((concept_ref, RDF.type, SKOS.Concept))
        graph.add((concept_ref, SKOS.definition, Literal("A test definition")))

        errors = validate_skos_graph(graph)
        assert len(errors) == 1
        assert "missing required skos:prefLabel" in errors[0]

    def test_validate_skos_graph_catches_missing_definition_and_note(self) -> None:
        """Test that validation catches concepts missing both definition and note."""
        graph, namespace = create_skos_graph("https://test.org/", "test")

        # Manually add a concept with only prefLabel
        concept_ref = namespace["TestConcept"]
        graph.add((concept_ref, RDF.type, SKOS.Concept))
        graph.add((concept_ref, SKOS.prefLabel, Literal("Test Concept")))

        errors = validate_skos_graph(graph)
        assert len(errors) == 1
        assert "missing both skos:definition and skos:note" in errors[0]


class TestIntegration:
    """Test end-to-end SKOS generation workflow."""

    def test_complete_workflow_produces_valid_skos_output(self, tmp_path: Path) -> None:
        """Test the complete workflow from GraphQL schema to SKOS output."""
        # Create test schema
        schema_content = '''
            type Query { vehicle: Vehicle }

            """Vehicle description"""
            type Vehicle {
                name: String
                adas: Vehicle_ADAS
            }

            type Vehicle_ADAS {
                isActive: Boolean
            }
        '''

        schema_file = tmp_path / "test.graphql"
        schema_file.write_text(schema_content)
        output_file = tmp_path / "output.ttl"

        with open(output_file, "w", encoding="utf-8") as output_stream:
            # Generate SKOS
            generate_skos_skeleton(
                schema_path=schema_file,
                output_stream=output_stream,
                namespace="https://test.org/",
                prefix="test",
                language="en",
            )

        content = output_file.read_text()

        # Verify essential SKOS elements are present
        assert "@prefix skos:" in content
        assert "test:Vehicle" in content
        assert "skos:prefLabel" in content
        assert "Vehicle description" in content
        assert "test:Vehicle.adas" in content


class TestGenerateSkosSkeleton:
    """Test the generate_skos_skeleton function."""

    def test_generate_skos_skeleton_writes_ttl_to_stream(self, tmp_path: Path) -> None:
        """Test that generate_skos_skeleton writes TTL output to a stream."""
        schema_content = '''
            type Query { vehicle: Vehicle }

            """Vehicle description"""
            type Vehicle {
                name: String
                adas: Vehicle_ADAS
            }

            type Vehicle_ADAS {
                isActive: Boolean
            }
        '''

        # Create temporary schema file
        schema_file = tmp_path / "test.graphql"
        schema_file.write_text(schema_content)

        # Use StringIO for output instead of file
        output_stream = StringIO()
        generate_skos_skeleton(
            schema_path=schema_file,
            output_stream=output_stream,
            namespace="https://test.org/",
            prefix="test",
            language="en",
        )

        content = output_stream.getvalue()

        # Verify essential SKOS elements are present
        assert "@prefix skos:" in content
        assert "test:Vehicle" in content
        assert "skos:prefLabel" in content
        assert "Vehicle description" in content
        assert "test:Vehicle.adas" in content
