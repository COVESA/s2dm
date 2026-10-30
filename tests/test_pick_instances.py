from typing import Any, cast

import pytest
from graphql import (
    DirectiveNode,
    DocumentNode,
    GraphQLField,
    GraphQLObjectType,
    GraphQLSchema,
    Visitor,
    build_schema,
    parse,
    print_schema,
    visit,
)

from s2dm.constants.directive import Directive, DirectiveArgument
from s2dm.exporters.utils.directive import get_argument_content
from s2dm.exporters.utils.instance_tag import (
    InstanceTagFieldInfo,
    expand_instances_in_schema,
    get_instance_tag_fields,
)
from s2dm.exporters.utils.pick import ALL, extract_and_validate_picks
from s2dm.exporters.utils.schema_loader import select_schema_content

SCHEMA = """
directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

type Query {
  vehicle: Vehicle
}

type Vehicle {
  doors: [Door]
  cabin: Cabin
}

type Cabin {
  doors: [Door]
}

type Door {
  name: String
  position: DoorPosition @instanceTag
}

type DoorPosition @instanceTag {
  row: Row
  side: Side
}

enum Row {
  ROW1
  ROW2
}

enum Side {
  LEFT
  RIGHT
}
"""

SOURCE_EXCLUDE_SCHEMA = SCHEMA.replace(
    "type DoorPosition @instanceTag", 'type DoorPosition @instanceTag(exclude: ["ROW2.RIGHT"])'
)

THREE_DIMENSION_SCHEMA = """
directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

type Query {
  vehicle: Vehicle
}

type Vehicle {
  doors: [Door]
}

type Door {
  position: DoorPosition @instanceTag
}

type DoorPosition @instanceTag {
  row: Row
  side: Side
  level: Level
}

enum Row {
  ROW1
  ROW2
}

enum Side {
  LEFT
  RIGHT
}

enum Level {
  LOW
  HIGH
}
"""

ENUM_TAG_SCHEMA = """
directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

type Query {
  mirror: Mirror
}

type Mirror {
  position: MirrorPosition @instanceTag(exclude: ["RIGHT"])
}

enum MirrorPosition @instanceTag {
  LEFT
  RIGHT
}
"""


def _applied_directive_names(document: DocumentNode) -> list[str]:
    applied_names: list[str] = []

    class DirectiveCollector(Visitor):
        def enter_directive(self, node: DirectiveNode, *_args: Any) -> None:
            applied_names.append(node.name.value)

    collector = DirectiveCollector()
    visit(document, collector)
    return applied_names


def _doors_query(doors_selection: str) -> DocumentNode:
    return parse(
        f"""
        query {{
          vehicle {{
            doors {{
              {doors_selection}
            }}
          }}
        }}
        """
    )


def test_extract_records_picked_instances_per_tag_field() -> None:
    schema = build_schema(SCHEMA)
    document = parse(
        """
        query {
          vehicle {
            doors {
              position @pick(instances: ["ROW1.LEFT", "ROW1.RIGHT"]) {
                row
                side
              }
            }
          }
        }
        """
    )

    _, picked = extract_and_validate_picks(schema, document)

    assert picked.instances == {("Door", "position"): ["ROW1.LEFT", "ROW1.RIGHT"]}


def test_extract_reads_an_empty_pick_as_every_instance() -> None:
    schema = build_schema(SCHEMA)
    document = parse(
        """
        query {
          vehicle {
            doors {
              position @pick(instances: []) {
                row
              }
            }
          }
        }
        """
    )

    _, picked = extract_and_validate_picks(schema, document)

    assert picked.instances == {("Door", "position"): ALL}


def test_extract_removes_pick_from_the_document() -> None:
    schema = build_schema(SCHEMA)
    document = parse(
        """
        query {
          vehicle {
            doors {
              position @pick(instances: ["ROW1.LEFT"]) @include(if: true) {
                row
                side
              }
            }
          }
        }
        """
    )

    stripped_document, _ = extract_and_validate_picks(schema, document)

    assert _applied_directive_names(stripped_document) == ["include"]
    assert Directive.PICK.value in _applied_directive_names(document)


def test_extract_returns_a_document_without_pick_as_is() -> None:
    schema = build_schema(SCHEMA)
    document = parse(
        """
        query {
          vehicle {
            doors {
              name
            }
          }
        }
        """
    )

    stripped_document, picked = extract_and_validate_picks(schema, document)

    assert stripped_document is document
    assert picked.instances == {}


def test_extract_accepts_the_same_pick_on_every_occurrence_of_a_field() -> None:
    schema = build_schema(SCHEMA)
    document = parse(
        """
        query {
          vehicle {
            doors {
              position @pick(instances: ["ROW1.LEFT", "ROW2.LEFT"]) {
                row
                side
              }
            }
            cabin {
              doors {
                position @pick(instances: ["ROW2.LEFT", "ROW1.LEFT"]) {
                  row
                  side
                }
              }
            }
          }
        }
        """
    )

    _, picked = extract_and_validate_picks(schema, document)

    assert picked.instances == {("Door", "position"): ["ROW1.LEFT", "ROW2.LEFT"]}


def test_extract_rejects_different_picks_for_one_field() -> None:
    schema = build_schema(SCHEMA)
    document = parse(
        """
        query {
          vehicle {
            doors {
              position @pick(instances: ["ROW1.LEFT"]) {
                row
                side
              }
            }
            cabin {
              doors {
                position @pick(instances: ["ROW2.LEFT"]) {
                  row
                  side
                }
              }
            }
          }
        }
        """
    )

    with pytest.raises(ValueError):
        extract_and_validate_picks(schema, document)


def test_extract_records_picked_values_per_dimension() -> None:
    schema = build_schema(SCHEMA)
    document = parse(
        """
        query {
          vehicle {
            doors {
              position {
                row @pick(instances: ["ROW1"])
                side @pick(instances: [])
              }
            }
          }
        }
        """
    )

    stripped_document, picked = extract_and_validate_picks(schema, document)

    assert picked.dimension_values == {("Door", "position"): {"row": ["ROW1"], "side": ALL}}
    assert picked.instances == {}
    assert _applied_directive_names(stripped_document) == []


def test_extract_rejects_different_values_for_one_dimension() -> None:
    schema = build_schema(SCHEMA)
    document = parse(
        """
        query {
          vehicle {
            doors {
              position {
                row @pick(instances: ["ROW1"])
                side
              }
            }
            cabin {
              doors {
                position {
                  row @pick(instances: ["ROW2"])
                  side
                }
              }
            }
          }
        }
        """
    )

    with pytest.raises(ValueError):
        extract_and_validate_picks(schema, document)


@pytest.mark.parametrize(
    ("first_position", "second_position"),
    [
        pytest.param(
            'position @pick(instances: ["ROW1.LEFT"]) { row side }',
            'position { row @pick(instances: ["ROW1"]) side }',
            id="tag-field-first",
        ),
        pytest.param(
            'position { row @pick(instances: ["ROW1"]) side }',
            'position @pick(instances: ["ROW1.LEFT"]) { row side }',
            id="dimension-first",
        ),
    ],
)
def test_extract_rejects_both_forms_across_occurrences(first_position: str, second_position: str) -> None:
    schema = build_schema(SCHEMA)
    document = parse(
        f"""
        query {{
          vehicle {{
            doors {{
              {first_position}
            }}
            cabin {{
              doors {{
                {second_position}
              }}
            }}
          }}
        }}
        """
    )

    with pytest.raises(ValueError):
        extract_and_validate_picks(schema, document)


@pytest.mark.parametrize(
    "field_selection",
    [
        pytest.param('name @pick(instances: ["ROW1.LEFT"])', id="not-an-instance-tag-field"),
        pytest.param('position @pick(instances: ["ROW1.LEFT"], enums: []) { row side }', id="unknown-argument"),
        pytest.param("position @pick { row side }", id="missing-instances"),
        pytest.param('position @pick(instances: "ROW1.LEFT") { row side }', id="not-a-list"),
        pytest.param("position @pick(instances: [1]) { row side }", id="not-a-name"),
        pytest.param(
            'position @pick(instances: ["ROW1.LEFT"]) @pick(instances: ["ROW1.LEFT"]) { row side }',
            id="applied-twice",
        ),
        pytest.param('position @pick(instances: ["ROW3.LEFT"]) { row side }', id="unknown-instance"),
        pytest.param('position { row @pick(instances: ["ROW3"]) side }', id="unknown-dimension-value"),
        pytest.param("position { __typename @pick(instances: []) }", id="not-an-enum-dimension"),
        pytest.param(
            'position @pick(instances: ["ROW1.LEFT"]) { row @pick(instances: ["ROW1"]) side }',
            id="both-forms-in-one-place",
        ),
    ],
)
def test_extract_rejects_an_invalid_pick(field_selection: str) -> None:
    schema = build_schema(SCHEMA)
    document = _doors_query(field_selection)

    with pytest.raises(ValueError):
        extract_and_validate_picks(schema, document)


def test_extract_records_picked_values_for_three_dimensions() -> None:
    schema = build_schema(THREE_DIMENSION_SCHEMA)
    document = parse(
        """
        query {
          vehicle {
            doors {
              position {
                row @pick(instances: ["ROW1"])
                side
                level @pick(instances: ["HIGH"])
              }
            }
          }
        }
        """
    )

    _, picked = extract_and_validate_picks(schema, document)

    assert picked.dimension_values == {("Door", "position"): {"row": ["ROW1"], "level": ["HIGH"]}}


@pytest.mark.parametrize(
    "position_selection",
    [
        pytest.param('position @pick(instances: ["ROW1.LEFT"]) { row }', id="tag-field"),
        pytest.param('position { row @pick(instances: ["ROW1"]) }', id="dimension"),
    ],
)
def test_extract_rejects_a_pick_without_every_dimension(position_selection: str) -> None:
    schema = build_schema(SCHEMA)
    document = _doors_query(position_selection)

    with pytest.raises(ValueError):
        extract_and_validate_picks(schema, document)


def test_extract_accepts_an_empty_dimension_pick_without_every_dimension() -> None:
    schema = build_schema(SCHEMA)
    document = _doors_query("position { row @pick(instances: []) }")

    stripped_document, _ = extract_and_validate_picks(schema, document)

    assert _applied_directive_names(stripped_document) == []


def test_extract_accepts_a_pick_when_the_paths_together_select_every_dimension() -> None:
    schema = build_schema(SCHEMA)
    document = parse(
        """
        query {
          vehicle {
            doors {
              position {
                row @pick(instances: ["ROW1"])
              }
            }
            cabin {
              doors {
                position {
                  row @pick(instances: ["ROW1"])
                  side
                }
              }
            }
          }
        }
        """
    )

    _, picked = extract_and_validate_picks(schema, document)

    assert picked.dimension_values == {("Door", "position"): {"row": ["ROW1"]}}


def _select(schema_content: str, doors_selection: str) -> GraphQLSchema:
    document = _doors_query(doors_selection)
    selected_content = select_schema_content(schema_content, document)
    return build_schema(selected_content)


def _exclude_on(schema: GraphQLSchema, type_name: str, field_name: str | None = None) -> Any:
    named_type = schema.get_type(type_name)
    object_type = cast(GraphQLObjectType, named_type)
    element: GraphQLObjectType | GraphQLField = object_type
    if field_name is not None:
        element = object_type.fields[field_name]
    return get_argument_content(element, Directive.INSTANCE_TAG, DirectiveArgument.EXCLUDE)


@pytest.mark.parametrize(
    "position_selection",
    [
        pytest.param('position @pick(instances: ["ROW1.LEFT", "ROW1.RIGHT"]) { row side }', id="tag-field"),
        pytest.param('position { row @pick(instances: ["ROW1"]) side }', id="dimension"),
    ],
)
def test_select_schema_content_excludes_the_unpicked_instances(position_selection: str) -> None:
    selected_schema = _select(SCHEMA, position_selection)

    assert _exclude_on(selected_schema, "Door", "position") == ["ROW2.LEFT", "ROW2.RIGHT"]
    assert selected_schema.get_directive(Directive.PICK.value) is None


def test_select_schema_content_extends_the_existing_field_exclude() -> None:
    schema_content = SCHEMA.replace(
        "position: DoorPosition @instanceTag", 'position: DoorPosition @instanceTag(exclude: ["ROW2.RIGHT"])'
    )

    selected_schema = _select(schema_content, 'position @pick(instances: ["ROW1.LEFT"]) { row side }')

    assert _exclude_on(selected_schema, "Door", "position") == ["ROW2.RIGHT", "ROW1.RIGHT", "ROW2.LEFT"]


def test_select_schema_content_keeps_the_source_exclude_and_skips_its_instances() -> None:
    selected_schema = _select(SOURCE_EXCLUDE_SCHEMA, 'position { row @pick(instances: ["ROW2"]) side }')

    assert _exclude_on(selected_schema, "Door", "position") == ["ROW1.LEFT", "ROW1.RIGHT"]
    assert _exclude_on(selected_schema, "DoorPosition") == ["ROW2.RIGHT"]


def test_select_schema_content_rejects_an_instance_the_source_excludes() -> None:
    with pytest.raises(ValueError):
        _select(SOURCE_EXCLUDE_SCHEMA, 'position @pick(instances: ["ROW2.RIGHT"]) { row side }')


def test_select_schema_content_rejects_dimension_values_that_keep_no_defined_instance() -> None:
    with pytest.raises(ValueError):
        _select(SOURCE_EXCLUDE_SCHEMA, 'position { row @pick(instances: ["ROW2"]) side @pick(instances: ["RIGHT"]) }')


def test_select_schema_content_narrows_an_enum_backed_tag() -> None:
    schema_content = """
    directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

    type Query {
      vehicle: Vehicle
    }

    type Vehicle {
      doors: [Door]
    }

    type Door {
      side: Side @instanceTag
    }

    enum Side @instanceTag {
      LEFT
      RIGHT
    }
    """

    selected_schema = _select(schema_content, 'side @pick(instances: ["LEFT"])')

    assert _exclude_on(selected_schema, "Door", "side") == ["RIGHT"]


def test_select_schema_content_with_an_empty_pick_matches_no_pick() -> None:
    picked_schema = _select(SCHEMA, "position @pick(instances: []) { row side }")
    unpicked_schema = _select(SCHEMA, "position { row side }")

    assert print_schema(picked_schema) == print_schema(unpicked_schema)
    assert _exclude_on(picked_schema, "Door", "position") is None


def test_select_schema_content_excludes_the_unpicked_instances_of_three_dimensions() -> None:
    selected_schema = _select(
        THREE_DIMENSION_SCHEMA,
        'position @pick(instances: ["ROW1.LEFT.LOW", "ROW2.RIGHT.HIGH"]) { row side level }',
    )

    assert _exclude_on(selected_schema, "Door", "position") == [
        "ROW1.LEFT.HIGH",
        "ROW1.RIGHT.LOW",
        "ROW1.RIGHT.HIGH",
        "ROW2.LEFT.LOW",
        "ROW2.LEFT.HIGH",
        "ROW2.RIGHT.LOW",
    ]


def test_select_schema_content_keeps_every_value_of_an_unpicked_dimension_among_three() -> None:
    selected_schema = _select(
        THREE_DIMENSION_SCHEMA,
        'position { row @pick(instances: ["ROW1"]) side level @pick(instances: ["HIGH"]) }',
    )

    assert _exclude_on(selected_schema, "Door", "position") == [
        "ROW1.LEFT.LOW",
        "ROW1.RIGHT.LOW",
        "ROW2.LEFT.LOW",
        "ROW2.LEFT.HIGH",
        "ROW2.RIGHT.LOW",
        "ROW2.RIGHT.HIGH",
    ]


@pytest.mark.parametrize(
    "picked_instances",
    [
        pytest.param('["ROW1.LEFT"]', id="too-few-segments"),
        pytest.param('["ROW1.LEFT.LOW.EXTRA"]', id="too-many-segments"),
        pytest.param('["ROW1.LEFT.MIDDLE"]', id="no-such-value"),
    ],
)
def test_select_schema_content_rejects_an_instance_that_is_not_one_of_three_dimensions(picked_instances: str) -> None:
    with pytest.raises(ValueError):
        _select(THREE_DIMENSION_SCHEMA, f"position @pick(instances: {picked_instances}) {{ row side level }}")


def test_expansion_creates_only_the_picked_instances_of_three_dimensions() -> None:
    selected_schema = _select(
        THREE_DIMENSION_SCHEMA,
        'position { row @pick(instances: ["ROW2"]) side @pick(instances: ["LEFT"]) level }',
    )

    _, _, field_metadata = expand_instances_in_schema(selected_schema)

    assert field_metadata[("Vehicle", "Door")].resolved_names == ["Door.ROW2.LEFT.LOW", "Door.ROW2.LEFT.HIGH"]


def test_get_instance_tag_fields_indexes_the_dimensions_and_instances() -> None:
    schema = build_schema(SCHEMA)

    tag_fields = get_instance_tag_fields(schema)

    assert tag_fields == {
        "Door.position": InstanceTagFieldInfo(
            dimensions={"row": ["ROW1", "ROW2"], "side": ["LEFT", "RIGHT"]},
            instances=["ROW1.LEFT", "ROW1.RIGHT", "ROW2.LEFT", "ROW2.RIGHT"],
        )
    }


def test_get_instance_tag_fields_leaves_out_the_source_excluded_instances() -> None:
    schema = build_schema(SOURCE_EXCLUDE_SCHEMA)

    tag_fields = get_instance_tag_fields(schema)

    assert tag_fields["Door.position"].instances == ["ROW1.LEFT", "ROW1.RIGHT", "ROW2.LEFT"]


def test_get_instance_tag_fields_uses_the_field_as_the_dimension_of_an_enum_tag() -> None:
    schema = build_schema(ENUM_TAG_SCHEMA)

    tag_fields = get_instance_tag_fields(schema)

    tag_field = tag_fields["Mirror.position"]
    assert tag_field.dimensions == {"position": ["LEFT", "RIGHT"]}
    assert tag_field.instances == ["LEFT"]
