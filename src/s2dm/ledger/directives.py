"""Annotate a composed GraphQL schema with ``@modl`` directives sourced from a ledger."""

from dataclasses import replace

from graphql import (
    ConstArgumentNode,
    ConstDirectiveNode,
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLField,
    GraphQLObjectType,
    GraphQLSchema,
    NameNode,
    StringValueNode,
)
from modl.models import ElementKind

from s2dm.constants.directive import Directive, DirectiveArgument
from s2dm.exporters.utils.extraction import select_types
from s2dm.exporters.utils.graphql_type import is_introspection_or_root_type
from s2dm.ledger.models import Ledger, LedgerEntry
from s2dm.ledger.validation import ModlElement, validate_modl_annotation
from s2dm.utils.sequence import get_sequence_or_empty

_AnnotatableElement = GraphQLObjectType | GraphQLEnumType | GraphQLField | GraphQLEnumValue


def annotate_schema_with_ledger(schema: GraphQLSchema, ledger: Ledger) -> None:
    """Attach ``@modl`` directives to a schema's types and members in place, sourced from the ledger.

    Object and enum types are matched to a ledger concept by name and kind, and their members — fields
    and enum values — by ``Type.member`` label and kind. Every matched element is validated against
    the ledger first as a ``(label, kind, parent_label)`` triple, where ``parent_label`` is ``None``
    for a type and the type name for a member; if validation fails the schema is left untouched.
    Otherwise each matched node with a ledger entry gains a ``@modl(concept, contract)`` directive on
    its AST node, so it is emitted when the schema is printed with directives preserved. Root
    operation and introspection types are ignored.
    """
    matches: list[tuple[LedgerEntry | None, _AnnotatableElement]] = []
    elements: list[ModlElement] = []
    annotatable_types = select_types(
        schema, GraphQLObjectType, GraphQLEnumType, exclude_by_name=is_introspection_or_root_type
    )
    for type_name, graphql_type in annotatable_types:
        if isinstance(graphql_type, GraphQLObjectType):
            members: dict[str, GraphQLField] | dict[str, GraphQLEnumValue] = graphql_type.fields
            type_kind, member_kind = ElementKind.ENTITY, ElementKind.PROPERTY
        elif isinstance(graphql_type, GraphQLEnumType):
            members = graphql_type.values
            type_kind, member_kind = ElementKind.ENUMERATION_SET, ElementKind.ENUM_VALUE
        else:
            continue

        type_entry = ledger.entry_for(type_name, type_kind)
        matches.append((type_entry, graphql_type))
        type_element = ModlElement(label=type_name, kind=type_kind, parent_label=None)
        elements.append(type_element)
        for member_name, member in members.items():
            label = f"{type_name}.{member_name}"
            member_entry = ledger.entry_for(label, member_kind)
            matches.append((member_entry, member))
            member_element = ModlElement(label=label, kind=member_kind, parent_label=type_name)
            elements.append(member_element)

    if not validate_modl_annotation(elements, ledger.directory):
        return
    for entry, element in matches:
        ast_node = element.ast_node
        if entry is None or ast_node is None:
            continue
        existing_directives = get_sequence_or_empty(ast_node.directives)
        modl_directive = _modl_directive_node(entry)
        element.ast_node = replace(ast_node, directives=(*existing_directives, modl_directive))


def _modl_directive_node(entry: LedgerEntry) -> ConstDirectiveNode:
    return ConstDirectiveNode(
        name=NameNode(value=Directive.MODL.value),
        arguments=(
            ConstArgumentNode(
                name=NameNode(value=DirectiveArgument.CONCEPT.value),
                value=StringValueNode(value=entry.concept_uri),
            ),
            ConstArgumentNode(
                name=NameNode(value=DirectiveArgument.CONTRACT.value),
                value=StringValueNode(value=entry.contract_uri),
            ),
        ),
    )
