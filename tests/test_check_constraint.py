from graphql import GraphQLObjectType, GraphQLSchema, build_schema

from s2dm.exporters.utils import get_all_object_types
from s2dm.tools.constraint_checker import ConstraintChecker


def make_schema(sdl: str) -> GraphQLSchema:
    schema = build_schema(sdl)
    return schema


def get_objects(schema: GraphQLSchema) -> list[GraphQLObjectType]:
    return get_all_object_types(schema)


def test_instance_tag_field_must_reference_instance_tag_object() -> None:
    sdl = """
    directive @instanceTag on OBJECT

    type TagObj @instanceTag {
      level: TagEnum
    }
    enum TagEnum { A B }

    type Foo {
      instanceTag: TagObj
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    errors = checker.run(objects)
    assert not errors


def test_instance_tag_field_wrong_type() -> None:
    sdl = """
    directive @instanceTag on OBJECT

    type NotTagObj {
      foo: String
    }

    type Foo {
      instanceTag: NotTagObj
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    errors = checker.run(objects)
    assert any("must reference an object type with @instanceTag" in e for e in errors)


def test_instance_tag_object_fields_must_be_enum() -> None:
    sdl = """
    directive @instanceTag on OBJECT

    type TagObj @instanceTag {
      notEnum: String
    }

    type Foo {
      instanceTag: TagObj
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    errors = checker.run(objects)
    assert any("must be an enum" in e for e in errors)


def test_range_min_leq_max() -> None:
    sdl = """
    directive @range(min: Float, max: Float) on FIELD_DEFINITION

    type Foo {
      bar: Int @range(min: 0, max: 10)
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    errors = checker.run(objects)
    assert not errors


def test_range_min_gt_max() -> None:
    sdl = """
    directive @range(min: Float, max: Float) on FIELD_DEFINITION

    type Foo {
      bar: Int @range(min: 10, max: 5)
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    errors = checker.run(objects)
    assert any("has min > max" in e for e in errors)


def test_cardinality_min_leq_max() -> None:
    sdl = """
    directive @cardinality(min: Int, max: Int) on FIELD_DEFINITION

    type Foo {
      bar: Int @cardinality(min: 0, max: 2)
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    errors = checker.run(objects)
    assert not errors


def test_cardinality_min_gt_max() -> None:
    sdl = """
    directive @cardinality(min: Int, max: Int) on FIELD_DEFINITION

    type Foo {
      bar: Int @cardinality(min: 3, max: 2)
    }
    """
    schema = make_schema(sdl)
    objects = get_objects(schema)
    checker = ConstraintChecker(schema)
    errors = checker.run(objects)
    assert any("has min > max" in e for e in errors)
