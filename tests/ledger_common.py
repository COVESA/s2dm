"""Shared ledger test data and helpers used by the unit and e2e ledger tests."""

import textwrap
from collections.abc import Iterable
from typing import Protocol, TypeVar

from graphql import DocumentNode
from graphql.language.ast import (
    EnumTypeDefinitionNode,
    EnumValueDefinitionNode,
    FieldDefinitionNode,
    NameNode,
    ObjectTypeDefinitionNode,
    StringValueNode,
)

from s2dm.constants.directive import Directive


class _Named(Protocol):
    name: NameNode


_N = TypeVar("_N", bound=_Named)


def _find_by_name(nodes: Iterable[_N], name: str) -> _N | None:
    return next((node for node in nodes if node.name.value == name), None)


def dedent_csv(content: str) -> str:
    return textwrap.dedent(content).lstrip("\n")


FULL_CONCEPTS = dedent_csv(
    """
    serial,concept_uri,current_label,previous_labels,kind,status,parent_uri,instances
    0,http://ex/concepts/0,Car,,ENTITY,ACTIVE,,
    1,http://ex/concepts/1,Person,,ENTITY,ACTIVE,,
    2,http://ex/concepts/2,Car.id,,PROPERTY,ACTIVE,http://ex/concepts/0,
    3,http://ex/concepts/3,Car.owner,,PROPERTY,ACTIVE,http://ex/concepts/0,
    4,http://ex/concepts/4,Person.id,,PROPERTY,ACTIVE,http://ex/concepts/1,
    5,http://ex/concepts/5,Person.name,,PROPERTY,ACTIVE,http://ex/concepts/1,
    6,http://ex/concepts/6,DriveType,,ENUMERATION_SET,ACTIVE,,
    7,http://ex/concepts/7,DriveType.FWD,,ENUM_VALUE,ACTIVE,http://ex/concepts/6,
    8,http://ex/concepts/8,DriveType.RWD,,ENUM_VALUE,ACTIVE,http://ex/concepts/6,
    9,http://ex/concepts/9,DriveType.AWD,,ENUM_VALUE,ACTIVE,http://ex/concepts/6,
    """
)

FULL_CONTRACTS = dedent_csv(
    """
    serial,concept_uri,contract_uri,revision_uri,status
    0,http://ex/concepts/0,http://ex/contracts/0,http://ex/revisions/0,ACTIVE
    1,http://ex/concepts/1,http://ex/contracts/1,http://ex/revisions/1,ACTIVE
    2,http://ex/concepts/2,http://ex/contracts/2,http://ex/revisions/2,ACTIVE
    3,http://ex/concepts/3,http://ex/contracts/3,http://ex/revisions/3,ACTIVE
    4,http://ex/concepts/4,http://ex/contracts/4,http://ex/revisions/4,ACTIVE
    5,http://ex/concepts/5,http://ex/contracts/5,http://ex/revisions/5,ACTIVE
    6,http://ex/concepts/6,http://ex/contracts/6,http://ex/revisions/6,ACTIVE
    7,http://ex/concepts/7,http://ex/contracts/7,http://ex/revisions/7,ACTIVE
    8,http://ex/concepts/8,http://ex/contracts/8,http://ex/revisions/8,ACTIVE
    9,http://ex/concepts/9,http://ex/contracts/9,http://ex/revisions/9,ACTIVE
    """
)

FULL_REVISIONS = dedent_csv(
    """
    serial,concept_uri,revision_uri,previous_revision_uri,status
    0,http://ex/concepts/0,http://ex/revisions/0,,ACTIVE
    1,http://ex/concepts/1,http://ex/revisions/1,,ACTIVE
    2,http://ex/concepts/2,http://ex/revisions/2,,ACTIVE
    3,http://ex/concepts/3,http://ex/revisions/3,,ACTIVE
    4,http://ex/concepts/4,http://ex/revisions/4,,ACTIVE
    5,http://ex/concepts/5,http://ex/revisions/5,,ACTIVE
    6,http://ex/concepts/6,http://ex/revisions/6,,ACTIVE
    7,http://ex/concepts/7,http://ex/revisions/7,,ACTIVE
    8,http://ex/concepts/8,http://ex/revisions/8,,ACTIVE
    9,http://ex/concepts/9,http://ex/revisions/9,,ACTIVE
    """
)

FULL_BINDINGS = dedent_csv(
    """
    serial,contract_uri,binding_uri,instance_tags,runtime_path,status
    0,http://ex/contracts/2,http://ex/bindings/0,{},Car.id,ACTIVE
    1,http://ex/contracts/3,http://ex/bindings/1,{},Car.owner,ACTIVE
    2,http://ex/contracts/4,http://ex/bindings/2,{},Person.id,ACTIVE
    3,http://ex/contracts/5,http://ex/bindings/3,{},Person.name,ACTIVE
    """
)

FULL_REVISION_ASPECTS = dedent_csv(
    """
    revision_uri,aspect_key,operation,previous_value,newer_value,reason
    """
)

FULL_CONTRACT_REFERENCES = dedent_csv(
    """
    contract_uri,role,target_contract_uri
    """
)


def modl_args(document: DocumentNode, type_name: str, member_name: str | None = None) -> dict[str, str] | None:
    """Return the ``@modl`` argument values on a type (or one of its members), or ``None`` if absent.

    A member is a field of an object type or a value of an enum type.
    """
    type_def = next(
        (
            definition
            for definition in document.definitions
            if isinstance(definition, ObjectTypeDefinitionNode | EnumTypeDefinitionNode)
            and definition.name.value == type_name
        ),
        None,
    )
    if type_def is None:
        return None

    if member_name is None:
        directives = type_def.directives
    else:
        members: Iterable[FieldDefinitionNode | EnumValueDefinitionNode] = (
            type_def.fields if isinstance(type_def, ObjectTypeDefinitionNode) else type_def.values
        )
        member = _find_by_name(members, member_name)
        if member is None:
            return None
        directives = member.directives

    modl = _find_by_name(directives, Directive.MODL.value)
    if modl is None:
        return None
    return {
        argument.name.value: argument.value.value
        for argument in modl.arguments
        if isinstance(argument.value, StringValueNode)
    }
