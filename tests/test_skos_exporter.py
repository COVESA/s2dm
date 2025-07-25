from io import StringIO
from pathlib import Path

import pytest
from graphql import build_schema
from rdflib import Graph, Literal
from rdflib.namespace import RDF, SKOS

from s2dm.concept.services import iter_all_concepts
from s2dm.exporters.skos import (
    SKOSConcept,
    collect_skos_concepts,
    create_skos_graph,
    generate_skos_skeleton,
    validate_skos_graph,
)
from s2dm.exporters.utils import get_all_named_types


class TestSKOSConcept:
    """Test SKOS concept creation and RDF generation."""

    @pytest.fixture
    def sample_concept(self) -> SKOSConcept:
        """Create a sample concept for testing."""
        return SKOSConcept(
            name="TestConcept",
            pref_label="Test Concept",
            language="en",
            definition="A test concept for unit testing",
            s2dm_type="ObjectType",
        )

    def test_add_to_graph_with_definition(self, sample_concept: SKOSConcept) -> None:
        """Test that concepts with definitions create proper RDF triples."""
        graph, namespace = create_skos_graph("https://test.org/", "test")
        sample_concept.add_to_graph(graph, namespace)

        concept_ref = namespace[sample_concept.name]
        assert (concept_ref, RDF.type, SKOS.Concept) in graph
        assert (concept_ref, SKOS.prefLabel, Literal("Test Concept", lang="en")) in graph
        assert (concept_ref, SKOS.definition, Literal("A test concept for unit testing")) in graph

    def test_add_to_graph_without_definition(self) -> None:
        """Test that concepts without definitions don't create definition triples."""
        concept = SKOSConcept(
            name="EmptyConcept",
            pref_label="Empty Concept",
            language="en",
            definition="",
            s2dm_type="Field",
        )
        graph, namespace = create_skos_graph("https://test.org/", "test")
        concept.add_to_graph(graph, namespace)

        concept_ref = namespace[concept.name]
        assert (concept_ref, RDF.type, SKOS.Concept) in graph
        assert (concept_ref, SKOS.prefLabel, Literal("Empty Concept", lang="en")) in graph
        # Should not have definition or note triples
        assert not list(graph.objects(concept_ref, SKOS.definition))
        assert not list(graph.objects(concept_ref, SKOS.note))


class TestSKOSGeneration:
    """Test SKOS generation from GraphQL schemas."""

    def test_collect_skos_concepts_creates_proper_structure(self) -> None:
        """Test that collect_skos_concepts creates the expected SKOS structure."""
        schema_str = '''
            type Query { vehicle: Vehicle }

            """Vehicle description"""
            type Vehicle {
                name: String
                adas: Vehicle_ADAS
            }

            type Vehicle_ADAS {
                isActive: Boolean
            }

            enum TestEnum { VALUE1, VALUE2 }
        '''

        schema = build_schema(schema_str)
        named_types = get_all_named_types(schema)
        concepts = iter_all_concepts(named_types)

        graph, namespace = create_skos_graph("https://test.org/", "test")
        collect_skos_concepts(schema, concepts, graph, namespace, "en")

        # Check collections exist
        collections = list(graph.subjects(RDF.type, SKOS.Collection))
        collection_names = [str(coll).split("/")[-1] for coll in collections]
        assert "ObjectConcepts" in collection_names
        assert "FieldConcepts" in collection_names
        assert "TestEnum" in collection_names

        # Check concepts exist
        concept_uris = list(graph.subjects(RDF.type, SKOS.Concept))
        concept_names = [str(concept).split("/")[-1] for concept in concept_uris]
        assert "Vehicle" in concept_names
        assert "Vehicle_ADAS" in concept_names
        assert "Vehicle.name" in concept_names
        assert "Vehicle_ADAS.isActive" in concept_names

    def test_enum_with_description(self) -> None:
        """Test enum processing with descriptions."""
        schema_str = '''
            type Query { test: String }

            """Status enumeration with description"""
            enum Status { ACTIVE, INACTIVE }
        '''

        schema = build_schema(schema_str)
        named_types = get_all_named_types(schema)
        concepts = iter_all_concepts(named_types)

        graph, namespace = create_skos_graph("https://test.org/", "test")
        collect_skos_concepts(schema, concepts, graph, namespace, "en")

        # Check enum collection has description
        status_collection = namespace["Status"]
        definitions = list(graph.objects(status_collection, SKOS.definition))
        assert len(definitions) == 1
        assert str(definitions[0]) == "Status enumeration with description"

    def test_enum_value_descriptions(self) -> None:
        """Test that enum value descriptions are properly extracted and used."""
        schema_str = '''
            type Query { test: String }

            enum Priority {
                """Highest priority item"""
                HIGH

                """Medium priority item"""
                MEDIUM

                LOW
            }
        '''

        schema = build_schema(schema_str)
        named_types = get_all_named_types(schema)
        concepts = iter_all_concepts(named_types)

        graph, namespace = create_skos_graph("https://test.org/", "test")
        collect_skos_concepts(schema, concepts, graph, namespace, "en")

        # Check that enum values with descriptions have them
        high_concept = namespace["Priority.HIGH"]
        high_definitions = list(graph.objects(high_concept, SKOS.definition))
        assert len(high_definitions) == 1
        assert str(high_definitions[0]) == "Highest priority item"

        medium_concept = namespace["Priority.MEDIUM"]
        medium_definitions = list(graph.objects(medium_concept, SKOS.definition))
        assert len(medium_definitions) == 1
        assert str(medium_definitions[0]) == "Medium priority item"

        # Check that enum values without descriptions don't have definition triples
        low_concept = namespace["Priority.LOW"]
        low_definitions = list(graph.objects(low_concept, SKOS.definition))
        assert len(low_definitions) == 0

    def test_excludes_query_and_mutation_types(self) -> None:
        """Test that Query and Mutation types are excluded from SKOS generation."""
        schema_str = """
            type Query { vehicle: Vehicle }
            type Mutation { update: String }
            type Vehicle { name: String }
        """

        schema = build_schema(schema_str)
        named_types = get_all_named_types(schema)
        concepts = iter_all_concepts(named_types)

        graph, namespace = create_skos_graph("https://test.org/", "test")
        collect_skos_concepts(schema, concepts, graph, namespace, "en")

        concept_uris = list(graph.subjects(RDF.type, SKOS.Concept))
        concept_names = [str(concept).split("/")[-1] for concept in concept_uris]

        assert "Query" not in concept_names
        assert "Mutation" not in concept_names
        assert "Vehicle" in concept_names

    def test_field_metadata_extraction(self) -> None:
        """Test that field metadata is correctly extracted and used."""
        schema_str = """
            type Query { test: String }
            type Vehicle {
                "Vehicle name description"
                name: String
                speed: Int
            }
        """
        schema = build_schema(schema_str)
        named_types = get_all_named_types(schema)
        concepts = iter_all_concepts(named_types)

        # Verify field metadata is populated
        assert "Vehicle.name" in concepts.fields
        assert "Vehicle.name" in concepts.field_metadata

        metadata = concepts.field_metadata["Vehicle.name"]
        assert metadata["object_name"] == "Vehicle"
        assert metadata["field_name"] == "name"
        assert hasattr(metadata["field_definition"], "description")


class TestSKOSValidation:
    """Test SKOS graph validation functionality."""

    def test_validate_skos_graph_catches_missing_preflabel(self) -> None:
        """Test that validation catches concepts missing prefLabel."""
        graph, namespace = create_skos_graph("https://test.org/", "test")

        # Add a concept without prefLabel
        concept_ref = namespace["TestConcept"]
        graph.add((concept_ref, RDF.type, SKOS.Concept))

        errors = validate_skos_graph(graph)
        assert len(errors) == 1
        assert "missing required skos:prefLabel" in errors[0]

    def test_validate_skos_graph_allows_optional_definition(self) -> None:
        """Test that validation allows concepts without definition (optional)."""
        graph, namespace = create_skos_graph("https://test.org/", "test")

        # Add a concept with only prefLabel
        concept_ref = namespace["TestConcept"]
        graph.add((concept_ref, RDF.type, SKOS.Concept))
        graph.add((concept_ref, SKOS.prefLabel, Literal("Test Concept")))

        errors = validate_skos_graph(graph)
        assert len(errors) == 0


class TestIntegration:
    """Test end-to-end SKOS generation workflow."""

    def test_complete_workflow_generates_valid_skos(self, tmp_path: Path) -> None:
        """Test the complete workflow from GraphQL schema to SKOS output."""
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

        # Test both StringIO and file output in one test
        output_stream = StringIO()
        generate_skos_skeleton(
            schema_path=schema_file,
            output_stream=output_stream,
            namespace="https://test.org/",
            prefix="test",
            language="en",
        )

        content = output_stream.getvalue()

        # Verify essential SKOS elements
        assert "@prefix skos:" in content
        assert "@prefix s2dm:" in content
        assert "test:Vehicle" in content
        assert "skos:prefLabel" in content
        assert "Vehicle description" in content
        assert "test:ObjectConcepts" in content
        assert "test:FieldConcepts" in content

    def test_validation_disabled(self, tmp_path: Path) -> None:
        """Test SKOS generation with validation disabled."""
        schema_content = "type Query { test: String }"
        schema_file = tmp_path / "test.graphql"
        schema_file.write_text(schema_content)

        output_stream = StringIO()
        # Should not raise even if there were validation issues
        generate_skos_skeleton(
            schema_path=schema_file,
            output_stream=output_stream,
            namespace="https://test.org/",
            prefix="test",
            language="en",
            validate=False,
        )

        content = output_stream.getvalue()
        assert "@prefix skos:" in content

    def test_validation_error_handling(self, tmp_path: Path) -> None:
        """Test that validation errors are properly raised."""
        schema_content = "type Query { test: String }"
        schema_file = tmp_path / "test.graphql"
        schema_file.write_text(schema_content)

        # Create an invalid graph by manually breaking validation
        from unittest.mock import patch

        def mock_validate_skos_graph(graph: Graph) -> list[str]:
            return ["Test validation error"]

        with patch("s2dm.exporters.skos.validate_skos_graph", side_effect=mock_validate_skos_graph):
            output_stream = StringIO()
            with pytest.raises(ValueError, match="Generated SKOS has validation errors"):
                generate_skos_skeleton(
                    schema_path=schema_file,
                    output_stream=output_stream,
                    namespace="https://test.org/",
                    prefix="test",
                    language="en",
                    validate=True,
                )
