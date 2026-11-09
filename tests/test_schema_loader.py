from pathlib import Path
from typing import cast

import pytest
from graphql import DocumentNode, GraphQLField, GraphQLObjectType, build_schema, parse

from s2dm.exporters.utils.schema_loader import (
    check_correct_schema,
    compose_schemas_to_string,
    load_schema_with_source_map,
    print_schema_with_directives_preserved,
)
from s2dm.exporters.utils.violations import ConstraintCode, Severity


@pytest.fixture
def spec_directory() -> Path:
    return Path(__file__).parent.parent / "src" / "s2dm" / "spec"


def test_load_schema_with_source_map_applies_schema_selection_resolver(tmp_path: Path) -> None:
    selected_schema_path = tmp_path / "selected.graphql"
    selected_schema_path.write_text(
        "type Query { vehicle: Vehicle }\n"
        "type Vehicle {\n"
        "  vin: String\n"
        "  model: String\n"
        "  speed: Speed\n"
        "}\n"
        "type Speed {\n"
        "  value: Float\n"
        "  unit: String\n"
        "}\n",
        encoding="utf-8",
    )
    full_schema_path = tmp_path / "full.graphql"
    full_schema_path.write_text(
        "type Extra {\n  kept: String\n  removed: String\n}\n",
        encoding="utf-8",
    )
    selection_document = parse("query Selection { vehicle { vin } }")

    def resolve_selection(schema_path: Path) -> DocumentNode | None:
        if schema_path.resolve() == selected_schema_path.resolve():
            return selection_document
        return None

    schema, source_map = load_schema_with_source_map(
        [selected_schema_path, full_schema_path],
        schema_selection_resolver=resolve_selection,
    )

    vehicle_type = schema.type_map["Vehicle"]
    extra_type = schema.type_map["Extra"]
    assert isinstance(vehicle_type, GraphQLObjectType)
    assert isinstance(extra_type, GraphQLObjectType)
    assert set(vehicle_type.fields) == {"vin"}
    assert set(extra_type.fields) == {"kept", "removed"}
    assert "Speed" not in schema.type_map
    assert source_map["Vehicle"] == selected_schema_path.name
    assert source_map["Extra"] == full_schema_path.name


def test_reference_directive_only_applied_to_supported_locations(spec_directory: Path) -> None:
    """Test that @reference is only added to types matching directive's allowed locations."""
    schema_str = """
    directive @reference(uri: String, source: String) on OBJECT | ENUM

    type TestObject { field: String }
    scalar TestScalar
    interface TestInterface { field: String }
    enum TestEnum { VALUE1 VALUE2 }
    input TestInput { field: String }
    union TestUnion = TestObject

    type Query { field: String }
    """

    schema = build_schema(schema_str)
    source_map = {
        "TestObject": "test.graphql",
        "TestScalar": "test.graphql",
        "TestInterface": "test.graphql",
        "TestEnum": "test.graphql",
        "TestInput": "test.graphql",
        "TestUnion": "test.graphql",
    }

    result = print_schema_with_directives_preserved(schema, source_map)

    assert 'type TestObject @reference(source: "test.graphql")' in result
    assert 'enum TestEnum @reference(source: "test.graphql")' in result

    assert "scalar TestScalar @reference" not in result
    assert "interface TestInterface @reference" not in result
    assert "input TestInput @reference" not in result
    assert "union TestUnion @reference" not in result


def test_reference_directive_not_applied_when_source_argument_missing() -> None:
    """Test that @reference without source argument is not applied."""
    schema_str = """
    directive @reference(uri: String!, versionTag: String) on OBJECT | ENUM

    type TestObject { field: String }
    enum TestEnum { VALUE1 VALUE2 }

    type Query { field: String }
    """

    schema = build_schema(schema_str)
    source_map = {
        "TestObject": "test.graphql",
        "TestEnum": "test.graphql",
    }

    result = print_schema_with_directives_preserved(schema, source_map)

    assert "type TestObject @reference" not in result
    assert "enum TestEnum @reference" not in result


def test_reference_directive_not_applied_when_directive_missing() -> None:
    """Test that compose succeeds when @reference directive is not defined."""
    schema_str = """
    type TestObject { field: String }
    enum TestEnum { VALUE1 VALUE2 }

    type Query { field: String }
    """

    schema = build_schema(schema_str)
    source_map = {
        "TestObject": "test.graphql",
        "TestEnum": "test.graphql",
    }

    result = print_schema_with_directives_preserved(schema, source_map)

    assert "@reference" not in result
    assert "type TestObject" in result
    assert "enum TestEnum" in result


def test_reference_directive_not_duplicated_when_already_present() -> None:
    """Test that @reference is not added if it already exists on the type."""
    schema_str = """
    directive @reference(uri: String, source: String) on OBJECT | ENUM

    type TestObject @reference(source: "original.graphql") { field: String }
    enum TestEnum { VALUE1 VALUE2 }

    type Query { field: String }
    """

    schema = build_schema(schema_str)
    source_map = {
        "TestObject": "new.graphql",
        "TestEnum": "test.graphql",
    }

    result = print_schema_with_directives_preserved(schema, source_map)

    assert 'type TestObject @reference(source: "original.graphql")' in result
    assert 'type TestObject @reference(source: "new.graphql")' not in result

    assert 'enum TestEnum @reference(source: "test.graphql")' in result


def test_reference_directive_with_all_standard_locations(spec_directory: Path) -> None:
    """Test @reference with all standard type locations from spec."""
    schema_str = """
    directive @reference(uri: String, source: String, versionTag: String)
        on OBJECT | INTERFACE | UNION | ENUM | ENUM_VALUE | SCALAR | INPUT_OBJECT | FIELD_DEFINITION

    type TestObject { field: String }
    interface TestInterface { field: String }
    union TestUnion = TestObject
    enum TestEnum { VALUE1 VALUE2 }
    scalar TestScalar
    input TestInput { field: String }

    type Query { field: String }
    """

    schema = build_schema(schema_str)
    source_map = {
        "TestObject": "types.graphql",
        "TestInterface": "interfaces.graphql",
        "TestUnion": "unions.graphql",
        "TestEnum": "enums.graphql",
        "TestScalar": "scalars.graphql",
        "TestInput": "inputs.graphql",
    }

    result = print_schema_with_directives_preserved(schema, source_map)

    assert 'type TestObject @reference(source: "types.graphql")' in result
    assert 'interface TestInterface @reference(source: "interfaces.graphql")' in result
    assert 'union TestUnion @reference(source: "unions.graphql")' in result
    assert 'enum TestEnum @reference(source: "enums.graphql")' in result
    assert 'scalar TestScalar @reference(source: "scalars.graphql")' in result
    assert 'input TestInput @reference(source: "inputs.graphql")' in result


def test_compose_preserves_directive_with_list_arguments() -> None:
    """Test that directives with list arguments are serialized correctly."""
    schema_str = """
    directive @vspec(element: String, metadata: [KeyValue]) on ENUM | ENUM_VALUE

    input KeyValue {
      key: String!
      value: String!
    }

    enum LengthUnit @vspec(element: "QUANTITY_KIND", metadata: [{key: "quantity", value: "length"}]) {
      MILLIMETER @vspec(element: "UNIT", metadata: [{key: "unit", value: "mm"}])
      CENTIMETER @vspec(element: "UNIT", metadata: [{key: "unit", value: "cm"}])
      METER @vspec(element: "UNIT", metadata: [{key: "unit", value: "m"}])
    }

    type Query { field: String }
    """

    schema = build_schema(schema_str)
    source_map: dict[str, str] = {}

    result = print_schema_with_directives_preserved(schema, source_map)

    # Verify list arguments are properly serialized, not as "ListValueNode at X:Y"
    assert 'enum LengthUnit @vspec(element: "QUANTITY_KIND", metadata: [{key: "quantity", value: "length"}])' in result
    assert 'MILLIMETER @vspec(element: "UNIT", metadata: [{key: "unit", value: "mm"}])' in result
    assert 'CENTIMETER @vspec(element: "UNIT", metadata: [{key: "unit", value: "cm"}])' in result
    assert 'METER @vspec(element: "UNIT", metadata: [{key: "unit", value: "m"}])' in result

    # Ensure no AST node representations leaked into output
    assert "ListValueNode" not in result
    assert "ObjectValueNode" not in result


def test_compose_preserves_directive_with_nested_objects() -> None:
    """Test that directives with nested object structures are serialized correctly."""
    schema_str = """
    directive @metadata(config: ConfigInput) on OBJECT

    input ConfigInput {
      settings: SettingsInput
      name: String
    }

    input SettingsInput {
      enabled: Boolean
      count: Int
    }

    type TestType @metadata(config: {settings: {enabled: true, count: 42}, name: "test"}) {
      field: String
    }

    type Query { field: String }
    """

    schema = build_schema(schema_str)
    source_map: dict[str, str] = {}

    result = print_schema_with_directives_preserved(schema, source_map)

    # Verify nested objects are properly serialized
    assert '@metadata(config: {settings: {enabled: true, count: 42}, name: "test"})' in result
    assert "ObjectValueNode" not in result


def test_compose_preserves_directive_with_various_scalar_types() -> None:
    """Test that directives with different scalar types are serialized correctly."""
    schema_str = """
    directive @config(
      name: String
      count: Int
      ratio: Float
      enabled: Boolean
      status: StatusEnum
    ) on OBJECT

    enum StatusEnum {
      ACTIVE
      INACTIVE
    }

    type TestType @config(name: "test", count: 123, ratio: 3.14, enabled: true, status: ACTIVE) {
      field: String
    }

    type Query { field: String }
    """

    schema = build_schema(schema_str)
    source_map: dict[str, str] = {}

    result = print_schema_with_directives_preserved(schema, source_map)

    # Verify all scalar types are properly serialized
    assert '@config(name: "test", count: 123, ratio: 3.14, enabled: true, status: ACTIVE)' in result
    # Ensure strings are properly quoted
    assert 'name: "test"' in result
    # Ensure numbers are not quoted
    assert "count: 123" in result
    assert "ratio: 3.14" in result
    # Ensure booleans are lowercase
    assert "enabled: true" in result
    # Ensure enums are not quoted
    assert "status: ACTIVE" in result


def test_compose_merges_identical_shared_directives_and_scalars(tmp_path: Path) -> None:
    first_schema_path = tmp_path / "first.graphql"
    first_schema_path.write_text(
        """
        directive @metadata(comment: String) on FIELD_DEFINITION
        scalar DateTime

        type Query {
          vehicle: Vehicle
        }

        type Vehicle {
          manufacturedAt: DateTime @metadata(comment: "built")
        }
        """,
        encoding="utf-8",
    )
    second_schema_path = tmp_path / "second.graphql"
    second_schema_path.write_text(
        """
        directive @metadata(comment: String) on FIELD_DEFINITION
        scalar DateTime

        type ServiceRecord {
          servicedAt: DateTime @metadata(comment: "serviced")
        }
        """,
        encoding="utf-8",
    )

    composed_schema = compose_schemas_to_string(
        schemas=[first_schema_path, second_schema_path],
        root_type=None,
        selection_query=None,
        naming_config=None,
        expanded_instances=False,
    )

    assert composed_schema.count("directive @metadata") == 1
    assert composed_schema.count("scalar DateTime") == 1
    assert "type Vehicle" in composed_schema
    assert "type ServiceRecord" in composed_schema


def test_compose_rejects_incompatible_shared_directives_and_scalars(tmp_path: Path) -> None:
    first_schema_path = tmp_path / "first.graphql"
    first_schema_path.write_text(
        """
        directive @metadata(comment: String) on FIELD_DEFINITION
        directive @format(value: String) on SCALAR
        scalar DateTime @format(value: "iso")

        type Query {
          vehicle: Vehicle
        }

        type Vehicle {
          manufacturedAt: DateTime @metadata(comment: "built")
        }
        """,
        encoding="utf-8",
    )
    second_schema_path = tmp_path / "second.graphql"
    second_schema_path.write_text(
        """
        directive @metadata(label: String) on OBJECT
        directive @format(value: String) on SCALAR
        scalar DateTime @format(value: "epoch")

        type ServiceRecord {
          servicedAt: DateTime
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        compose_schemas_to_string(
            schemas=[first_schema_path, second_schema_path],
            root_type=None,
            selection_query=None,
            naming_config=None,
            expanded_instances=False,
        )


def test_compose_rejects_directive_superset_without_merge_shared_definitions(tmp_path: Path) -> None:
    first_schema_path = tmp_path / "first.graphql"
    first_schema_path.write_text(
        """
        directive @metadata(comment: String) on FIELD_DEFINITION

        type Query {
          vehicle: Vehicle
        }

        type Vehicle {
          vin: String @metadata(comment: "base")
        }
        """,
        encoding="utf-8",
    )
    second_schema_path = tmp_path / "second.graphql"
    second_schema_path.write_text(
        """
        directive @metadata(comment: String, source: String) on FIELD_DEFINITION | OBJECT

        type ServiceRecord {
          servicedAt: String
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        compose_schemas_to_string(
            schemas=[first_schema_path, second_schema_path],
            root_type=None,
            selection_query=None,
            naming_config=None,
            expanded_instances=False,
        )


def test_compose_uses_directive_superset_with_merge_shared_definitions(tmp_path: Path) -> None:
    first_schema_path = tmp_path / "first.graphql"
    first_schema_path.write_text(
        """
        directive @metadata(comment: String) on FIELD_DEFINITION

        type Query {
          vehicle: Vehicle
        }

        type Vehicle {
          vin: String @metadata(comment: "base")
        }
        """,
        encoding="utf-8",
    )
    second_schema_path = tmp_path / "second.graphql"
    second_schema_path.write_text(
        """
        directive @metadata(comment: String, source: String) on FIELD_DEFINITION | OBJECT

        type ServiceRecord {
          servicedAt: String
        }
        """,
        encoding="utf-8",
    )

    composed_schema = compose_schemas_to_string(
        schemas=[first_schema_path, second_schema_path],
        root_type=None,
        selection_query=None,
        naming_config=None,
        expanded_instances=False,
        merge_shared_definitions=True,
    )

    assert "directive @metadata(comment: String, source: String) on FIELD_DEFINITION | OBJECT" in composed_schema


def test_compose_uses_scalar_applied_directive_superset_with_merge_shared_definitions(tmp_path: Path) -> None:
    first_schema_path = tmp_path / "first.graphql"
    first_schema_path.write_text(
        """
        directive @format(value: String!) on SCALAR
        scalar DateTime @format(value: "iso")

        type Query {
          vehicle: Vehicle
        }

        type Vehicle {
          manufacturedAt: DateTime
        }
        """,
        encoding="utf-8",
    )
    second_schema_path = tmp_path / "second.graphql"
    second_schema_path.write_text(
        """
        directive @format(value: String!, source: String) on SCALAR
        scalar DateTime @format(value: "iso", source: "system")

        type ServiceRecord {
          servicedAt: DateTime
        }
        """,
        encoding="utf-8",
    )

    composed_schema = compose_schemas_to_string(
        schemas=[first_schema_path, second_schema_path],
        root_type=None,
        selection_query=None,
        naming_config=None,
        expanded_instances=False,
        merge_shared_definitions=True,
    )

    assert "directive @format(value: String!, source: String) on SCALAR" in composed_schema
    assert 'scalar DateTime @format(value: "iso", source: "system")' in composed_schema


def test_compose_merges_identical_shared_enums(tmp_path: Path) -> None:
    first_schema_path = tmp_path / "first.graphql"
    first_schema_path.write_text(
        """
        enum Drivetrain { FWD RWD AWD }

        type Query {
          vehicle: Vehicle
        }

        type Vehicle {
          drivetrain: Drivetrain
        }
        """,
        encoding="utf-8",
    )
    second_schema_path = tmp_path / "second.graphql"
    second_schema_path.write_text(
        """
        enum Drivetrain { FWD RWD AWD }

        type ServiceRecord {
          drivetrain: Drivetrain
        }
        """,
        encoding="utf-8",
    )

    composed_schema = compose_schemas_to_string(
        schemas=[first_schema_path, second_schema_path],
        root_type=None,
        selection_query=None,
        naming_config=None,
        expanded_instances=False,
    )

    assert composed_schema.count("enum Drivetrain") == 1
    assert "type Vehicle" in composed_schema
    assert "type ServiceRecord" in composed_schema


def test_compose_rejects_incompatible_shared_enums(tmp_path: Path) -> None:
    first_schema_path = tmp_path / "first.graphql"
    first_schema_path.write_text(
        """
        enum Drivetrain { FWD RWD }

        type Query {
          vehicle: Vehicle
        }

        type Vehicle {
          drivetrain: Drivetrain
        }
        """,
        encoding="utf-8",
    )
    second_schema_path = tmp_path / "second.graphql"
    second_schema_path.write_text(
        """
        enum Drivetrain { FWD AWD }

        type ServiceRecord {
          drivetrain: Drivetrain
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        compose_schemas_to_string(
            schemas=[first_schema_path, second_schema_path],
            root_type=None,
            selection_query=None,
            naming_config=None,
            expanded_instances=False,
        )


def test_compose_uses_enum_value_superset_with_merge_shared_definitions(tmp_path: Path) -> None:
    first_schema_path = tmp_path / "first.graphql"
    first_schema_path.write_text(
        """
        enum Drivetrain { FWD RWD }

        type Query {
          vehicle: Vehicle
        }

        type Vehicle {
          drivetrain: Drivetrain
        }
        """,
        encoding="utf-8",
    )
    second_schema_path = tmp_path / "second.graphql"
    second_schema_path.write_text(
        """
        enum Drivetrain { FWD RWD AWD }

        type ServiceRecord {
          drivetrain: Drivetrain
        }
        """,
        encoding="utf-8",
    )

    composed_schema = compose_schemas_to_string(
        schemas=[first_schema_path, second_schema_path],
        root_type=None,
        selection_query=None,
        naming_config=None,
        expanded_instances=False,
        merge_shared_definitions=True,
    )

    assert composed_schema.count("enum Drivetrain") == 1
    assert "AWD" in composed_schema


def _query_fields(composed_schema: str) -> dict[str, GraphQLField]:
    schema = build_schema(composed_schema)
    assert isinstance(schema.query_type, GraphQLObjectType)
    return cast(dict[str, GraphQLField], schema.query_type.fields)


def test_compose_stitches_query_fields_from_multiple_schemas(tmp_path: Path) -> None:
    first_schema_path = tmp_path / "first.graphql"
    first_schema_path.write_text(
        """
        type Query {
          vehicle: Vehicle
        }

        type Vehicle {
          vin: String
        }
        """,
        encoding="utf-8",
    )
    second_schema_path = tmp_path / "second.graphql"
    second_schema_path.write_text(
        """
        type Query {
          powertrain: Powertrain
        }

        type Powertrain {
          range: Float
        }
        """,
        encoding="utf-8",
    )

    composed_schema = compose_schemas_to_string(
        schemas=[first_schema_path, second_schema_path],
        root_type=None,
        selection_query=None,
        naming_config=None,
        expanded_instances=False,
    )

    fields = _query_fields(composed_schema)
    assert set(fields) == {"vehicle", "powertrain"}
    assert str(fields["vehicle"].type) == "Vehicle"
    assert str(fields["powertrain"].type) == "Powertrain"


def test_compose_merges_identical_query_field_redeclaration(tmp_path: Path) -> None:
    first_schema_path = tmp_path / "first.graphql"
    first_schema_path.write_text(
        """
        type Query {
          vehicle: Vehicle
        }

        type Vehicle {
          vin: String
        }
        """,
        encoding="utf-8",
    )
    second_schema_path = tmp_path / "second.graphql"
    second_schema_path.write_text(
        """
        type Query {
          vehicle: Vehicle
        }

        type ServiceRecord {
          vin: String
        }
        """,
        encoding="utf-8",
    )

    composed_schema = compose_schemas_to_string(
        schemas=[first_schema_path, second_schema_path],
        root_type=None,
        selection_query=None,
        naming_config=None,
        expanded_instances=False,
    )

    fields = _query_fields(composed_schema)
    assert set(fields) == {"vehicle"}
    assert str(fields["vehicle"].type) == "Vehicle"


def test_compose_rejects_incompatible_query_field_redeclaration(tmp_path: Path) -> None:
    first_schema_path = tmp_path / "first.graphql"
    first_schema_path.write_text(
        """
        type Query {
          vehicle: Vehicle
        }

        type Vehicle {
          vin: String
        }
        """,
        encoding="utf-8",
    )
    second_schema_path = tmp_path / "second.graphql"
    second_schema_path.write_text(
        """
        type Query {
          vehicle: String
        }

        type ServiceRecord {
          vin: String
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        compose_schemas_to_string(
            schemas=[first_schema_path, second_schema_path],
            root_type=None,
            selection_query=None,
            naming_config=None,
            expanded_instances=False,
        )


def test_check_correct_schema_flags_multiple_instance_tag_fields() -> None:
    schema_str = """
    directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

    type SeatPosition @instanceTag {
      level: HeightLevel
    }
    enum HeightLevel { LOW HIGH }

    type Vehicle {
      position: SeatPosition @instanceTag
      trim: SeatPosition @instanceTag
    }

    type Query { vehicle: Vehicle }
    """
    schema = build_schema(schema_str)
    codes = [violation.code for violation in check_correct_schema(schema)]
    assert ConstraintCode.INSTANCE_TAG_MULTIPLE_FIELDS in codes


def test_check_correct_schema_allows_single_instance_tag_field() -> None:
    schema_str = """
    directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

    type SeatPosition @instanceTag {
      level: HeightLevel
    }
    enum HeightLevel { LOW HIGH }

    type Vehicle {
      position: SeatPosition @instanceTag
    }

    type Query { vehicle: Vehicle }
    """
    schema = build_schema(schema_str)
    codes = [violation.code for violation in check_correct_schema(schema)]
    assert ConstraintCode.INSTANCE_TAG_MULTIPLE_FIELDS not in codes


def test_check_correct_schema_includes_instance_tag_rule_violations() -> None:
    schema_str = """
    directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

    type EngineSpecs {
      power: String
    }

    type Vehicle {
      engine: EngineSpecs @instanceTag
    }

    type Query { vehicle: Vehicle }
    """
    schema = build_schema(schema_str)
    codes = [violation.code for violation in check_correct_schema(schema)]
    assert ConstraintCode.INSTANCE_TAG_INVALID_REFERENCE in codes


def test_check_correct_schema_excludes_warning_severity_violations() -> None:
    schema_str = """
    directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

    type SeatPosition @instanceTag {
      level: HeightLevel
    }
    enum HeightLevel { LOW HIGH }

    type Door {
      position: SeatPosition @instanceTag
      isLocked: Boolean
    }

    type Cabin {
      door: Door
    }

    type Query { cabin: Cabin }
    """
    schema = build_schema(schema_str)
    violations = check_correct_schema(schema)
    assert all(violation.severity == Severity.ERROR for violation in violations)
