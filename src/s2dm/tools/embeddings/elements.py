"""Schema elements and the field-card text embedded for each one."""

from typing import Literal

from boltons.strutils import camel2under
from graphql import (
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLField,
    GraphQLInterfaceType,
    GraphQLNamedType,
    GraphQLObjectType,
    GraphQLSchema,
    get_named_type,
)
from pydantic import BaseModel

from s2dm.exporters.utils.extraction import select_types
from s2dm.exporters.utils.graphql_type import is_introspection_or_root_type

ElementKind = Literal["type", "field", "enum", "enum_value"]
DescribedEntity = GraphQLNamedType | GraphQLField | GraphQLEnumValue


class SchemaElement(BaseModel):
    """One searchable schema element: a type, field, enum, or enum value, with the text embedded for it.

    ``id`` is ``Type`` or ``Enum`` for types and enums, and ``Parent.member`` for fields and enum values.

    ``text`` is the element's field card. Examples: a field ``Base.isOpen: Boolean`` documented as ``"Is it open."``
    becomes ``base is open (Boolean): Is it open.``; a value ``A`` of an enum ``Mode`` documented as ``"Mode."``
    becomes ``a (value of mode: Mode.)``. The ``: {description}`` part is left out when there is no description.
    """

    id: str
    kind: ElementKind
    description: str
    text: str


def _split_words(name: str) -> str:
    """Split an identifier into lowercase words.

    Examples: ``isOpen`` -> ``is open``, ``Base_Child`` -> ``base child``, ``ABCode`` -> ``ab code``.

    Args:
        name: A GraphQL type, field, or enum value name.

    Returns:
        The name as space-separated lowercase words.
    """
    snake_name = camel2under(name)
    words = [word for word in snake_name.split("_") if word]
    return " ".join(words)


def _description_of(entity: DescribedEntity) -> str:
    return (entity.description or "").strip()


def _build_element(element_id: str, kind: ElementKind, label: str, description: str) -> SchemaElement:
    text = label
    if description:
        text = f"{label}: {description}"

    return SchemaElement(id=element_id, kind=kind, description=description, text=text)


def _container_elements(container: GraphQLObjectType | GraphQLInterfaceType) -> list[SchemaElement]:
    container_words = _split_words(container.name)
    container_description = _description_of(container)
    type_element = _build_element(
        element_id=container.name, kind="type", label=container_words, description=container_description
    )
    elements = [type_element]

    for field_name, field in container.fields.items():
        field_type = get_named_type(field.type)
        field_words = _split_words(field_name)
        field_id = f"{container.name}.{field_name}"
        label = f"{container_words} {field_words} ({field_type.name})"
        field_description = _description_of(field)
        field_element = _build_element(element_id=field_id, kind="field", label=label, description=field_description)
        elements.append(field_element)

    return elements


def _enum_elements(enum_type: GraphQLEnumType) -> list[SchemaElement]:
    enum_words = _split_words(enum_type.name)
    enum_description = _description_of(enum_type)

    enum_context = enum_words
    if enum_description:
        enum_context = f"{enum_words}: {enum_description}"

    enum_element = _build_element(
        element_id=enum_type.name, kind="enum", label=enum_words, description=enum_description
    )
    elements = [enum_element]

    for value_name, value in enum_type.values.items():
        value_words = _split_words(value_name)
        value_id = f"{enum_type.name}.{value_name}"
        label = f"{value_words} (value of {enum_context})"
        value_description = _description_of(value)
        value_element = _build_element(
            element_id=value_id, kind="enum_value", label=label, description=value_description
        )
        elements.append(value_element)

    return elements


def extract_elements(schema: GraphQLSchema) -> list[SchemaElement]:
    """Collect every searchable element of a schema, with the text embedded for it.

    Object and interface types with their fields, and enums with their values, are included.
    Introspection types and the root types (``Query``, ``Mutation``, ``Subscription``) are excluded.

    Args:
        schema: The composed GraphQL schema.

    Returns:
        The elements in schema order, each type or enum followed by its members.
    """
    elements: list[SchemaElement] = []
    selected_types = select_types(
        schema,
        GraphQLObjectType,
        GraphQLInterfaceType,
        GraphQLEnumType,
        exclude_by_name=is_introspection_or_root_type,
    )
    for _, named_type in selected_types:
        if isinstance(named_type, GraphQLObjectType | GraphQLInterfaceType):
            container_elements = _container_elements(named_type)
            elements.extend(container_elements)
        elif isinstance(named_type, GraphQLEnumType):
            enum_elements = _enum_elements(named_type)
            elements.extend(enum_elements)

    return elements
