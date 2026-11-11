from graphql import GraphQLObjectType, GraphQLSchema, build_schema

from s2dm.exporters.utils.extraction import get_all_object_types
from s2dm.exporters.utils.violations import ConstraintCode, Severity
from s2dm.tools.constraint_checker import ConstraintChecker


def make_schema(sdl: str) -> GraphQLSchema:
    schema = build_schema(sdl)
    return schema


def get_objects(schema: GraphQLSchema) -> list[GraphQLObjectType]:
    return get_all_object_types(schema)


def test_instance_tag_field_must_reference_instance_tag_object() -> None:
    sdl = """
    directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

    type Query {
      ping: String
    }

    type SeatPosition @instanceTag {
      level: HeightLevel
    }
    enum HeightLevel { LOW HIGH }

    type Vehicle {
      position: SeatPosition @instanceTag
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    violations = checker.run(objects)
    assert not any(violation.code == ConstraintCode.INSTANCE_TAG_INVALID_REFERENCE for violation in violations)


def test_instance_tag_field_wrong_type() -> None:
    sdl = """
    directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

    type EngineSpecs {
      power: String
    }

    type Vehicle {
      engine: EngineSpecs @instanceTag
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    violations = checker.run(objects)
    assert any(violation.code == ConstraintCode.INSTANCE_TAG_INVALID_REFERENCE for violation in violations)


def test_instance_tag_object_fields_must_be_enum() -> None:
    sdl = """
    directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

    type SeatPosition @instanceTag {
      notEnum: String
    }

    type Vehicle {
      position: SeatPosition @instanceTag
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    violations = checker.run(objects)
    assert any(violation.code == ConstraintCode.INSTANCE_TAG_NON_ENUM_FIELD for violation in violations)


def test_instance_tag_source_type_field_cannot_be_tagged() -> None:
    sdl = """
    directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

    type SeatPosition @instanceTag {
      level: HeightLevel @instanceTag
    }
    enum HeightLevel { LOW HIGH }

    type Vehicle {
      position: SeatPosition @instanceTag
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    violations = checker.run(objects)
    assert any(violation.code == ConstraintCode.INSTANCE_TAG_SOURCE_FIELD_TAGGED for violation in violations)


def test_instance_tag_source_type_field_not_tagged_is_valid() -> None:
    sdl = """
    directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

    type SeatPosition @instanceTag {
      level: HeightLevel
    }
    enum HeightLevel { LOW HIGH }

    type Vehicle {
      position: SeatPosition @instanceTag
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    violations = checker.run(objects)
    assert not any(violation.code == ConstraintCode.INSTANCE_TAG_SOURCE_FIELD_TAGGED for violation in violations)


def test_instance_tag_at_most_one_field_per_type() -> None:
    sdl = """
    directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

    type SeatPosition @instanceTag {
      level: HeightLevel
    }
    enum HeightLevel { LOW HIGH }

    type Vehicle {
      position: SeatPosition @instanceTag
      trim: SeatPosition @instanceTag
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    violations = checker.run(objects)
    assert any(violation.code == ConstraintCode.INSTANCE_TAG_MULTIPLE_FIELDS for violation in violations)


def test_instance_tag_single_field_is_allowed() -> None:
    sdl = """
    directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

    type Query {
      ping: String
    }

    type SeatPosition @instanceTag {
      level: HeightLevel
    }
    enum HeightLevel { LOW HIGH }

    type Vehicle {
      position: SeatPosition @instanceTag
      model: String
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    violations = checker.run(objects)
    assert not any(violation.code == ConstraintCode.INSTANCE_TAG_MULTIPLE_FIELDS for violation in violations)


def test_instance_tag_field_may_reference_instance_tag_enum() -> None:
    sdl = """
    directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM | ENUM

    type Query {
      ping: String
    }

    enum HeightLevel @instanceTag {
      LOW
      HIGH
    }

    type Vehicle {
      position: HeightLevel @instanceTag
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    violations = checker.run(objects)
    assert not violations


def test_instance_tag_field_referencing_plain_enum_is_invalid() -> None:
    sdl = """
    directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM | ENUM

    enum HeightLevel {
      LOW
      HIGH
    }

    type Vehicle {
      position: HeightLevel @instanceTag
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    violations = checker.run(objects)
    assert any(violation.code == ConstraintCode.INSTANCE_TAG_INVALID_REFERENCE for violation in violations)


def test_instance_tag_expandable_field_not_list_warns() -> None:
    sdl = """
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
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    violations = checker.run(objects)
    warning = next(v for v in violations if v.code == ConstraintCode.INSTANCE_TAG_NOT_EXPANDED)
    assert warning.severity == Severity.WARNING


def test_instance_tag_expandable_field_as_list_does_not_warn() -> None:
    sdl = """
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
      doors: [Door]
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    violations = checker.run(objects)
    assert not any(v.code == ConstraintCode.INSTANCE_TAG_NOT_EXPANDED for v in violations)


def test_instance_tag_single_dimension_warns() -> None:
    sdl = """
    directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

    type Query {
      ping: String
    }

    type SeatPosition @instanceTag {
      level: HeightLevel
    }
    enum HeightLevel { LOW HIGH }

    type Vehicle {
      position: SeatPosition @instanceTag
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    violations = checker.run(objects)
    warning = next(v for v in violations if v.code == ConstraintCode.INSTANCE_TAG_SINGLE_DIMENSION)
    assert warning.severity == Severity.WARNING


def test_instance_tag_multiple_dimensions_does_not_warn() -> None:
    sdl = """
    directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

    type Query {
      ping: String
    }

    type SeatPosition @instanceTag {
      row: RowEnum
      level: HeightLevel
    }
    enum RowEnum { ROW1 ROW2 }
    enum HeightLevel { LOW HIGH }

    type Vehicle {
      position: SeatPosition @instanceTag
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    violations = checker.run(objects)
    assert not any(v.code == ConstraintCode.INSTANCE_TAG_SINGLE_DIMENSION for v in violations)


def test_instance_tag_exclude_list_invalid_entry_flagged() -> None:
    sdl = """
    directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

    type Query {
      ping: String
    }

    type SeatPosition @instanceTag {
      row: RowEnum
    }
    enum RowEnum { ROW1 ROW2 }

    type Door {
      position: SeatPosition @instanceTag(exclude: ["ROW3"])
    }

    type Cabin {
      doors: [Door]
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    violations = checker.run(objects)
    assert any(violation.code == ConstraintCode.INSTANCE_TAG_INVALID_EXCLUDE for violation in violations)


def test_instance_tag_exclude_list_valid_entry_not_flagged() -> None:
    sdl = """
    directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

    type Query {
      ping: String
    }

    type SeatPosition @instanceTag {
      row: RowEnum
    }
    enum RowEnum { ROW1 ROW2 }

    type Door {
      position: SeatPosition @instanceTag(exclude: ["ROW1"])
    }

    type Cabin {
      doors: [Door]
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    violations = checker.run(objects)
    assert not any(violation.code == ConstraintCode.INSTANCE_TAG_INVALID_EXCLUDE for violation in violations)


def test_run_includes_schema_spec_violations() -> None:
    sdl = """
    type Query {
      vehicle: Vehicle
    }

    interface Node {
      id: ID
    }

    type Vehicle implements Node {
      name: String
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    violations = checker.run(objects)
    assert any(violation.code == ConstraintCode.SCHEMA_SPEC for violation in violations)


def test_run_reports_invalid_enum_default_as_spec_violation() -> None:
    sdl = """
    enum Color { RED BLUE }

    type Query {
      foo: String
    }

    input VehicleInput {
      color: Color = GREEN
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    violations = checker.run(objects)
    assert any(violation.code == ConstraintCode.SCHEMA_SPEC for violation in violations)


def test_check_schema_spec_flags_invalid_schema() -> None:
    sdl = """
    type Query {
      vehicle: Vehicle
    }

    interface Node {
      id: ID
    }

    type Vehicle implements Node {
      name: String
    }
    """
    schema = make_schema(sdl)
    checker = ConstraintChecker(schema)
    violations = checker.check_schema_spec()
    assert any(violation.code == ConstraintCode.SCHEMA_SPEC for violation in violations)


def test_check_schema_spec_allows_valid_schema() -> None:
    sdl = """
    type Query {
      foo: String
    }
    """
    schema = make_schema(sdl)
    checker = ConstraintChecker(schema)
    violations = checker.check_schema_spec()
    assert not violations


def test_check_directive_enum_values_flags_invalid_value() -> None:
    sdl = """
    directive @color(value: Color) on FIELD_DEFINITION

    enum Color { RED BLUE }

    type Vehicle {
      name: String @color(value: GREEN)
    }
    """
    schema = make_schema(sdl)
    checker = ConstraintChecker(schema)
    violations = checker.check_directive_enum_values()
    assert any(violation.code == ConstraintCode.DIRECTIVE_ENUM_VALUE for violation in violations)


def test_check_directive_enum_values_allows_valid_value() -> None:
    sdl = """
    directive @color(value: Color) on FIELD_DEFINITION

    enum Color { RED BLUE }

    type Vehicle {
      name: String @color(value: RED)
    }
    """
    schema = make_schema(sdl)
    checker = ConstraintChecker(schema)
    violations = checker.check_directive_enum_values()
    assert not violations


def test_range_min_leq_max() -> None:
    sdl = """
    directive @range(min: Float, max: Float) on FIELD_DEFINITION

    type Query {
      ping: String
    }

    type Vehicle {
      topSpeed: Int @range(min: 0, max: 10)
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    violations = checker.run(objects)
    assert not violations


def test_range_min_gt_max() -> None:
    sdl = """
    directive @range(min: Float, max: Float) on FIELD_DEFINITION

    type Vehicle {
      topSpeed: Int @range(min: 10, max: 5)
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    violations = checker.run(objects)
    assert any(violation.code == ConstraintCode.MIN_GREATER_THAN_MAX for violation in violations)


def test_cardinality_min_leq_max() -> None:
    sdl = """
    directive @cardinality(min: Int, max: Int) on FIELD_DEFINITION

    type Query {
      ping: String
    }

    type Vehicle {
      doorCount: Int @cardinality(min: 0, max: 2)
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    violations = checker.run(objects)
    assert not violations


def test_cardinality_min_gt_max() -> None:
    sdl = """
    directive @cardinality(min: Int, max: Int) on FIELD_DEFINITION

    type Vehicle {
      doorCount: Int @cardinality(min: 3, max: 2)
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    violations = checker.run(objects)
    assert any(violation.code == ConstraintCode.MIN_GREATER_THAN_MAX for violation in violations)


def test_range_null_min_is_not_flagged() -> None:
    sdl = """
    directive @range(min: Float, max: Float) on FIELD_DEFINITION

    type Query {
      ping: String
    }

    type Vehicle {
      topSpeed: Int @range(min: null, max: 5)
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    violations = checker.run(objects)
    assert not violations


def test_cardinality_null_min_is_not_flagged() -> None:
    sdl = """
    directive @cardinality(min: Int, max: Int) on FIELD_DEFINITION

    type Query {
      ping: String
    }

    type Vehicle {
      doorCount: Int @cardinality(min: null, max: 2)
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    violations = checker.run(objects)
    assert not violations
