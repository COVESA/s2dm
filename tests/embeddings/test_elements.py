import pytest
from graphql import GraphQLSchema

from s2dm.tools.embeddings.elements import SchemaElement, extract_elements


@pytest.fixture(scope="module")
def elements_by_id(embeddings_schema: GraphQLSchema) -> dict[str, SchemaElement]:
    elements = extract_elements(embeddings_schema)
    return {element.id: element for element in elements}


def test_extract_elements_ids_in_schema_order_and_kinds(embeddings_schema: GraphQLSchema) -> None:
    elements = extract_elements(embeddings_schema)

    assert [(element.id, element.kind) for element in elements] == [
        ("Vehicle_Cabin_Door", "type"),
        ("Vehicle_Cabin_Door.isOpen", "field"),
        ("Vehicle_Cabin_Door.position", "field"),
        ("Node", "type"),
        ("Node.id", "field"),
        ("HVDoorState", "enum"),
        ("HVDoorState.OPEN", "enum_value"),
        ("HVDoorState.CLOSED", "enum_value"),
        ("Side", "enum"),
        ("Side.LEFT", "enum_value"),
    ]


@pytest.mark.parametrize(
    ("element_id", "expected_text"),
    [
        ("Vehicle_Cabin_Door", "vehicle cabin door: A vehicle door."),
        ("Vehicle_Cabin_Door.isOpen", "vehicle cabin door is open (Boolean): Is the door open or closed."),
        ("HVDoorState", "hv door state: Door state."),
        ("HVDoorState.OPEN", "open (value of hv door state: Door state.): Fully open."),
        ("Side.LEFT", "left (value of side)"),
    ],
)
def test_element_text(elements_by_id: dict[str, SchemaElement], element_id: str, expected_text: str) -> None:
    assert elements_by_id[element_id].text == expected_text
