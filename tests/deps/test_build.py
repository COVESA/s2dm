import pytest

from s2dm.deps.compose import (
    DependencyCompositionError,
    DependencySchemaBuilder,
    DependencySchemaInput,
)
from s2dm.deps.helpers import prepare_dependency_schemas_for_composition
from s2dm.deps.models import DependencyMetadata
from s2dm.exporters.utils.schema_loader import compose_schemas_to_string
from tests.deps.helpers import dependency_identities


def test_find_conflicts_reports_duplicate_type_with_dependency_metadata() -> None:
    dependency_schema_contents = [
        DependencySchemaInput(
            schema_content="type Query { vehicle: Vehicle }\ntype Vehicle { vin: String }\n",
            metadata=DependencyMetadata(name="BodyModel", id="urn:test:body", version="1.0.0"),
        ),
        DependencySchemaInput(
            schema_content="type Vehicle { speed: Float }\ntype Powertrain { vehicle: Vehicle }\n",
            metadata=DependencyMetadata(name="PowertrainModel", id="urn:test:powertrain", version="2.0.0"),
        ),
    ]

    (conflict,) = DependencySchemaBuilder(dependency_schema_contents).find_conflicts()

    assert conflict.type_name == "Vehicle"
    assert dependency_identities(conflict.dependencies_metadata) == {
        ("BodyModel", "1.0.0"),
        ("PowertrainModel", "2.0.0"),
    }


def test_type_extensions_do_not_create_type_name_conflicts() -> None:
    dependency_schema_contents = [
        DependencySchemaInput(
            schema_content="type Vehicle { vin: String }\n",
            metadata=DependencyMetadata(name="BaseModel", id="urn:test:base", version="1.0.0"),
        ),
        DependencySchemaInput(
            schema_content="extend type Vehicle { speed: Float }\n",
            metadata=DependencyMetadata(name="ExtensionModel", id="urn:test:extension", version="1.0.0"),
        ),
    ]

    conflicts = DependencySchemaBuilder(dependency_schema_contents).find_conflicts()

    assert conflicts == ()


def test_auto_prefix_renames_conflicting_type_definitions_and_references() -> None:
    dependency_schema_contents = [
        DependencySchemaInput(
            schema_content="type BodyCatalog { vehicle: Vehicle }\ntype Vehicle { vin: String }\n",
            metadata=DependencyMetadata(name="BodyModel", id="urn:test:body", version="1.0.0", preferred_prefix="body"),
        ),
        DependencySchemaInput(
            schema_content="type PowertrainCatalog { vehicle: Vehicle }\ntype Vehicle { speed: Float }\n",
            metadata=DependencyMetadata(
                name="PowertrainModel", id="urn:test:powertrain", version="2.0.0", preferred_prefix="powertrain"
            ),
        ),
    ]

    schema_content = _write_auto_prefixed_schema_content(dependency_schema_contents)

    assert "type body_Vehicle" in schema_content
    assert "type powertrain_Vehicle" in schema_content
    assert "vehicle: body_Vehicle" in schema_content
    assert "vehicle: powertrain_Vehicle" in schema_content


def test_auto_prefix_fails_when_prefixed_type_names_collide() -> None:
    dependency_schema_contents = [
        DependencySchemaInput(
            schema_content="type Vehicle { vin: String }\n",
            metadata=DependencyMetadata(
                name="BodyModel", id="urn:test:body", version="1.0.0", preferred_prefix="vehicle"
            ),
        ),
        DependencySchemaInput(
            schema_content="type Vehicle { speed: Float }\ntype vehicle_Vehicle { id: ID }\n",
            metadata=DependencyMetadata(
                name="PowertrainModel", id="urn:test:powertrain", version="2.0.0", preferred_prefix="powertrain"
            ),
        ),
    ]

    with pytest.raises(ValueError, match="Auto-prefix produced duplicate type definitions: vehicle_Vehicle"):
        DependencySchemaBuilder(dependency_schema_contents).write_auto_prefixed_schema_files()


def test_auto_prefix_keeps_no_conflict_schema_unchanged() -> None:
    dependency_schema_contents = [
        DependencySchemaInput(
            schema_content="type Vehicle { vin: String }\n",
            metadata=DependencyMetadata(name="BodyModel", id="urn:test:body", version="1.0.0"),
        ),
        DependencySchemaInput(
            schema_content="type Powertrain { speed: Float }\n",
            metadata=DependencyMetadata(name="PowertrainModel", id="urn:test:powertrain", version="2.0.0"),
        ),
    ]

    schema_content = _write_auto_prefixed_schema_content(dependency_schema_contents)

    assert "type Vehicle" in schema_content
    assert "type Powertrain" in schema_content
    assert "body_" not in schema_content
    assert "powertrain_" not in schema_content


def test_identical_directives_and_scalars_across_dependencies_succeed() -> None:
    body_schema = """
        directive @metadata(comment: String) on FIELD_DEFINITION
        scalar DateTime
        type Query {
            body: Body
        }
        type Body {
            color: String @metadata(comment: "exterior paint")
            manufacturedAt: DateTime
        }
    """
    powertrain_schema = """
        directive @metadata(comment: String) on FIELD_DEFINITION
        scalar DateTime
        type Powertrain {
            horsepower: Int @metadata(comment: "peak output")
            assembledAt: DateTime
        }
    """
    dependency_schema_contents = [
        DependencySchemaInput(
            schema_content=body_schema,
            metadata=DependencyMetadata(name="BodyModel", id="urn:test:body", version="1.0.0"),
        ),
        DependencySchemaInput(
            schema_content=powertrain_schema,
            metadata=DependencyMetadata(name="PowertrainModel", id="urn:test:powertrain", version="2.0.0"),
        ),
    ]

    schema_paths = prepare_dependency_schemas_for_composition(dependency_schema_contents, auto_prefix=False)

    composed_schema = compose_schemas_to_string(
        schemas=schema_paths,
        root_type=None,
        selection_query=None,
        naming_config=None,
        expanded_instances=False,
    )

    assert composed_schema.count("scalar DateTime") == 1
    assert composed_schema.count("directive @metadata") == 1


def test_incompatible_directives_fails() -> None:
    body_schema = """
        directive @metadata(comment: String) on FIELD_DEFINITION
        type Body {
            color: String @metadata(comment: "exterior paint")
            doorCount: Int
        }
    """
    powertrain_schema = """
        directive @metadata(comment: String) on OBJECT
        type Powertrain @metadata(comment: "drivetrain") {
            horsepower: Int
        }
    """
    dependency_schema_contents = [
        DependencySchemaInput(
            schema_content=body_schema,
            metadata=DependencyMetadata(name="BodyModel", id="urn:test:body", version="1.0.0"),
        ),
        DependencySchemaInput(
            schema_content=powertrain_schema,
            metadata=DependencyMetadata(name="PowertrainModel", id="urn:test:powertrain", version="2.0.0"),
        ),
    ]

    with pytest.raises(DependencyCompositionError):
        prepare_dependency_schemas_for_composition(dependency_schema_contents, auto_prefix=False)


def test_merge_shared_definitions_uses_superset_directive_and_scalar_definitions() -> None:
    body_schema = """
        directive @format(value: String!) on SCALAR
        directive @metadata(comment: String) on FIELD_DEFINITION
        scalar DateTime @format(value: "iso")
        type Query {
            body: Body
        }
        type Body {
            manufacturedAt: DateTime @metadata(comment: "base")
        }
    """
    powertrain_schema = """
        directive @format(value: String!, source: String) on SCALAR
        directive @metadata(comment: String, source: String) on FIELD_DEFINITION | OBJECT
        scalar DateTime @format(value: "iso", source: "system")
        type Powertrain {
            assembledAt: DateTime
        }
    """
    dependency_schema_contents = [
        DependencySchemaInput(
            schema_content=body_schema,
            metadata=DependencyMetadata(name="BodyModel", id="urn:test:body", version="1.0.0"),
        ),
        DependencySchemaInput(
            schema_content=powertrain_schema,
            metadata=DependencyMetadata(name="PowertrainModel", id="urn:test:powertrain", version="2.0.0"),
        ),
    ]

    schema_paths = prepare_dependency_schemas_for_composition(
        dependency_schema_contents,
        auto_prefix=False,
        merge_shared_definitions=True,
    )

    composed_schema = compose_schemas_to_string(
        schemas=schema_paths,
        root_type=None,
        selection_query=None,
        naming_config=None,
        expanded_instances=False,
    )

    assert "directive @metadata(comment: String, source: String) on FIELD_DEFINITION | OBJECT" in composed_schema
    assert "directive @format(value: String!, source: String) on SCALAR" in composed_schema
    assert 'scalar DateTime @format(value: "iso", source: "system")' in composed_schema


def _write_auto_prefixed_schema_content(dependency_schema_contents: list[DependencySchemaInput]) -> str:
    schema_paths = DependencySchemaBuilder(dependency_schema_contents).write_auto_prefixed_schema_files()
    return "\n".join(schema_path.read_text(encoding="utf-8") for schema_path in schema_paths)


def test_directives_only_dependency_composes_with_type_bearing_dependency() -> None:
    directives_only_schema = """
        directive @metadata(comment: String) on FIELD_DEFINITION
    """
    body_schema = """
        type Query {
            body: Body
        }
        type Body {
            color: String @metadata(comment: "exterior paint")
        }
    """
    dependency_schema_contents = [
        DependencySchemaInput(
            schema_content=directives_only_schema,
            metadata=DependencyMetadata(name="DirectivesModel", id="urn:test:directives", version="1.0.0"),
        ),
        DependencySchemaInput(
            schema_content=body_schema,
            metadata=DependencyMetadata(name="BodyModel", id="urn:test:body", version="1.0.0"),
        ),
    ]

    schema_paths = prepare_dependency_schemas_for_composition(dependency_schema_contents, auto_prefix=False)

    composed_schema = compose_schemas_to_string(
        schemas=schema_paths,
        root_type=None,
        selection_query=None,
        naming_config=None,
        expanded_instances=False,
    )

    assert "directive @metadata(comment: String) on FIELD_DEFINITION" in composed_schema
    assert "type Body" in composed_schema


def test_directive_and_enums_only_dependency_composes_with_type_bearing_dependency() -> None:
    directive_and_enums_schema = """
        directive @metadata(comment: String) on FIELD_DEFINITION
        enum Color {
            RED
            BLUE
        }
    """
    body_schema = """
        type Query {
            body: Body
        }
        type Body {
            color: String
        }
    """
    dependency_schema_contents = [
        DependencySchemaInput(
            schema_content=directive_and_enums_schema,
            metadata=DependencyMetadata(name="EnumsModel", id="urn:test:enums", version="1.0.0"),
        ),
        DependencySchemaInput(
            schema_content=body_schema,
            metadata=DependencyMetadata(name="BodyModel", id="urn:test:body", version="1.0.0"),
        ),
    ]

    schema_paths = prepare_dependency_schemas_for_composition(dependency_schema_contents, auto_prefix=False)

    composed_schema = compose_schemas_to_string(
        schemas=schema_paths,
        root_type=None,
        selection_query=None,
        naming_config=None,
        expanded_instances=False,
    )

    assert "enum Color" in composed_schema
    assert "RED" in composed_schema
    assert "type Body" in composed_schema


def test_only_shared_definition_dependencies_compose_without_type_bearing_dependency() -> None:
    directives_only_schema = """
        directive @metadata(comment: String) on FIELD_DEFINITION
    """
    enums_only_schema = """
        enum Color {
            RED
            BLUE
        }
    """
    dependency_schema_contents = [
        DependencySchemaInput(
            schema_content=directives_only_schema,
            metadata=DependencyMetadata(name="DirectivesModel", id="urn:test:directives", version="1.0.0"),
        ),
        DependencySchemaInput(
            schema_content=enums_only_schema,
            metadata=DependencyMetadata(name="EnumsModel", id="urn:test:enums", version="1.0.0"),
        ),
    ]

    schema_paths = prepare_dependency_schemas_for_composition(dependency_schema_contents, auto_prefix=False)

    composed_schema = compose_schemas_to_string(
        schemas=schema_paths,
        root_type=None,
        selection_query=None,
        naming_config=None,
        expanded_instances=False,
    )

    assert "directive @metadata(comment: String) on FIELD_DEFINITION" in composed_schema
    assert "enum Color" in composed_schema


def test_shared_only_dependency_does_not_hide_type_name_conflicts() -> None:
    directives_only_schema = """
        directive @metadata(comment: String) on FIELD_DEFINITION
    """
    dependency_schema_contents = [
        DependencySchemaInput(
            schema_content=directives_only_schema,
            metadata=DependencyMetadata(name="DirectivesModel", id="urn:test:directives", version="1.0.0"),
        ),
        DependencySchemaInput(
            schema_content="type Vehicle { vin: String }\n",
            metadata=DependencyMetadata(name="BodyModel", id="urn:test:body", version="1.0.0"),
        ),
        DependencySchemaInput(
            schema_content="type Vehicle { speed: Float }\n",
            metadata=DependencyMetadata(name="PowertrainModel", id="urn:test:powertrain", version="2.0.0"),
        ),
    ]

    with pytest.raises(DependencyCompositionError):
        prepare_dependency_schemas_for_composition(dependency_schema_contents, auto_prefix=False)


def test_shared_only_dependency_composes_with_auto_prefixed_conflicting_types() -> None:
    directives_only_schema = """
        directive @metadata(comment: String) on FIELD_DEFINITION
    """
    dependency_schema_contents = [
        DependencySchemaInput(
            schema_content=directives_only_schema,
            metadata=DependencyMetadata(name="DirectivesModel", id="urn:test:directives", version="1.0.0"),
        ),
        DependencySchemaInput(
            schema_content="type Vehicle { vin: String }\n",
            metadata=DependencyMetadata(name="BodyModel", id="urn:test:body", version="1.0.0", preferred_prefix="body"),
        ),
        DependencySchemaInput(
            schema_content="type Vehicle { speed: Float }\n",
            metadata=DependencyMetadata(
                name="PowertrainModel", id="urn:test:powertrain", version="2.0.0", preferred_prefix="powertrain"
            ),
        ),
    ]

    schema_paths = prepare_dependency_schemas_for_composition(dependency_schema_contents, auto_prefix=True)

    composed_schema = compose_schemas_to_string(
        schemas=schema_paths,
        root_type=None,
        selection_query=None,
        naming_config=None,
        expanded_instances=False,
    )

    assert "directive @metadata(comment: String) on FIELD_DEFINITION" in composed_schema
    assert "type body_Vehicle" in composed_schema
    assert "type powertrain_Vehicle" in composed_schema
