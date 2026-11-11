"""Concept counts, member names, container-type field composition, and enum value counts."""

from graphql import (
    GraphQLEnumType,
    GraphQLField,
    GraphQLInputField,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    GraphQLType,
    GraphQLUnionType,
    get_named_type,
    specified_directives,
)

from s2dm.exporters.utils.extraction import get_all_named_types
from s2dm.exporters.utils.graphql_type import is_builtin_scalar_type
from s2dm.tools.insights.models import (
    ConceptCounts,
    ConceptMembers,
    ConceptsResult,
    EnumUsage,
    EnumValueCount,
    FieldInfo,
    ScalarUsage,
    TypeFields,
)


def _field_infos(fields: dict[str, GraphQLField] | dict[str, GraphQLInputField]) -> list[FieldInfo]:
    infos: list[FieldInfo] = []
    for field_name, field_def in fields.items():
        named_output_type = get_named_type(field_def.type)
        is_leaf = isinstance(named_output_type, GraphQLScalarType | GraphQLEnumType)
        infos.append(FieldInfo(name=field_name, type=str(field_def.type), is_relationship=not is_leaf))
    return infos


def _tally_scalar_usage(
    fields: dict[str, GraphQLField] | dict[str, GraphQLInputField],
    scalar_counts: dict[str, int],
) -> None:
    for field_def in fields.values():
        named_output_type = get_named_type(field_def.type)
        if isinstance(named_output_type, GraphQLScalarType):
            scalar_counts[named_output_type.name] = scalar_counts.get(named_output_type.name, 0) + 1


def _bump_if_enum(graphql_type: GraphQLType, enum_counts: dict[str, int]) -> None:
    named_type = get_named_type(graphql_type)
    if isinstance(named_type, GraphQLEnumType):
        enum_counts[named_type.name] = enum_counts.get(named_type.name, 0) + 1


def _tally_enum_usage(
    fields: dict[str, GraphQLField] | dict[str, GraphQLInputField],
    enum_counts: dict[str, int],
) -> None:
    for field_def in fields.values():
        _bump_if_enum(field_def.type, enum_counts)
        if isinstance(field_def, GraphQLField):
            for arg in field_def.args.values():
                _bump_if_enum(arg.type, enum_counts)


def _tally_directive_enum_usage(schema: GraphQLSchema, enum_counts: dict[str, int]) -> None:
    for directive in schema.directives:
        for arg in directive.args.values():
            _bump_if_enum(arg.type, enum_counts)


def compute_concepts(schema: GraphQLSchema) -> ConceptsResult:
    """Compute type counts, member names by kind, container-type field breakdown, and enum value counts."""
    objects: list[str] = []
    interfaces: list[str] = []
    enums: list[str] = []
    unions: list[str] = []
    scalars: list[str] = []
    inputs: list[str] = []
    fields_by_type: list[TypeFields] = []
    enum_value_counts: list[EnumValueCount] = []
    scalar_counts: dict[str, int] = {}
    enum_counts: dict[str, int] = {}

    for named_type in get_all_named_types(schema):
        if isinstance(named_type, GraphQLObjectType):
            objects.append(named_type.name)
            fields_by_type.append(
                TypeFields(type=named_type.name, kind="object", fields=_field_infos(named_type.fields))
            )
            _tally_scalar_usage(named_type.fields, scalar_counts)
            _tally_enum_usage(named_type.fields, enum_counts)
        elif isinstance(named_type, GraphQLInterfaceType):
            interfaces.append(named_type.name)
            fields_by_type.append(
                TypeFields(type=named_type.name, kind="interface", fields=_field_infos(named_type.fields))
            )
            _tally_scalar_usage(named_type.fields, scalar_counts)
            _tally_enum_usage(named_type.fields, enum_counts)
        elif isinstance(named_type, GraphQLInputObjectType):
            inputs.append(named_type.name)
            fields_by_type.append(
                TypeFields(type=named_type.name, kind="input", fields=_field_infos(named_type.fields))
            )
            _tally_scalar_usage(named_type.fields, scalar_counts)
            _tally_enum_usage(named_type.fields, enum_counts)
        elif isinstance(named_type, GraphQLEnumType):
            enums.append(named_type.name)
            enum_value_counts.append(EnumValueCount(name=named_type.name, values=len(named_type.values)))
        elif isinstance(named_type, GraphQLUnionType):
            unions.append(named_type.name)
        elif isinstance(named_type, GraphQLScalarType) and not is_builtin_scalar_type(named_type.name):
            scalars.append(named_type.name)

    custom_directives = sorted(
        f"@{directive.name}" for directive in schema.directives if directive not in specified_directives
    )
    fields_by_type.sort(key=lambda entry: len(entry.fields), reverse=True)
    enum_value_counts.sort(key=lambda entry: (-entry.values, entry.name))

    scalar_usage = [
        ScalarUsage(name=name, count=count, is_builtin=is_builtin_scalar_type(name))
        for name, count in scalar_counts.items()
    ]
    scalar_usage.sort(key=lambda entry: (-entry.count, entry.name))

    _tally_directive_enum_usage(schema, enum_counts)
    enum_usage = [EnumUsage(name=name, count=count) for name, count in enum_counts.items()]
    enum_usage.sort(key=lambda entry: (-entry.count, entry.name))

    total_fields = sum(len(entry.fields) for entry in fields_by_type)
    leaf_fields = sum(1 for entry in fields_by_type for field in entry.fields if not field.is_relationship)

    counts = ConceptCounts(
        object=len(objects),
        interface=len(interfaces),
        enum=len(enums),
        union=len(unions),
        scalar=len(scalars),
        input=len(inputs),
        field=total_fields,
        leaf_field=leaf_fields,
        relationship_field=total_fields - leaf_fields,
        directive=len(custom_directives),
    )
    members = ConceptMembers(
        object=sorted(objects),
        interface=sorted(interfaces),
        enum=sorted(enums),
        union=sorted(unions),
        scalar=sorted(scalars),
        input=sorted(inputs),
        directive=custom_directives,
    )

    return ConceptsResult(
        counts=counts,
        members=members,
        fields_by_type=fields_by_type,
        enum_value_counts=enum_value_counts,
        scalar_usage=scalar_usage,
        enum_usage=enum_usage,
    )
