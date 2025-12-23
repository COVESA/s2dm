from typing import cast

from graphql import (
    GraphQLEnumType,
    GraphQLField,
    GraphQLList,
    GraphQLNamedType,
    GraphQLNonNull,
    GraphQLNullableType,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLType,
    GraphQLUnionType,
    get_named_type,
    is_enum_type,
    is_list_type,
    is_non_null_type,
    is_object_type,
    is_scalar_type,
    is_union_type,
)

from s2dm import log
from s2dm.exporters.utils.annotated_schema import AnnotatedSchema

from .common import get_avro_scalar_type


class AvroProtocolTransformer:
    """
    Transformer class to convert GraphQL schema to Avro protocol format.
    """

    def __init__(
        self,
        annotated_schema: AnnotatedSchema,
        namespace: str,
        protocol_name: str,
        referenced_types: set[GraphQLNamedType],
        strict: bool = False,
    ):
        self.annotated_schema = annotated_schema
        self.graphql_schema = annotated_schema.schema
        self.namespace = namespace
        self.protocol_name = protocol_name
        self.referenced_types = referenced_types
        self.strict = strict
        self.processed_types: set[str] = set()

    def transform(self) -> str:
        """
        Transform GraphQL types to Avro IDL protocol.

        Returns:
            str: Avro IDL protocol definition
        """
        lines = [f'@namespace("{self.namespace}")', f"protocol {self.protocol_name} {{"]

        for graphql_type in self.referenced_types:
            type_name = graphql_type.name

            if type_name in self.processed_types:
                continue

            self.processed_types.add(type_name)

            if is_object_type(graphql_type):
                lines.append(self._transform_record(cast(GraphQLObjectType, graphql_type)))
            elif is_enum_type(graphql_type) and self.strict:
                lines.append(self._transform_enum(cast(GraphQLEnumType, graphql_type)))
            elif is_union_type(graphql_type):
                lines.append(self._transform_union(cast(GraphQLUnionType, graphql_type)))

        lines.append("}")

        return "\n".join(lines)

    def _transform_record(self, obj_type: GraphQLObjectType) -> str:
        """Transform GraphQL object type to Avro record."""
        lines = [f"  record {obj_type.name} {{"]

        for field_name, field in obj_type.fields.items():
            field_type_str = self._get_field_type_string(field)
            comment = self._get_field_comment(field)
            if comment:
                lines.append(f"    {field_type_str} {field_name}; {comment}")
            else:
                lines.append(f"    {field_type_str} {field_name};")

        lines.append("  }")

        return "\n".join(lines)

    def _transform_enum(self, enum_type: GraphQLEnumType) -> str:
        """Transform GraphQL enum to Avro enum."""
        values = ", ".join(enum_type.values.keys())
        return f"  enum {enum_type.name} {{ {values} }}"

    def _transform_union(self, union_type: GraphQLUnionType) -> str:
        """Transform GraphQL union to Avro record with union field."""
        lines = [f"  record {union_type.name} {{"]

        union_types = [t.name for t in union_type.types]
        union_str = "union { " + ", ".join(union_types) + " }"
        lines.append(f"    {union_str} value;")

        lines.append("  }")

        return "\n".join(lines)

    def _get_field_type_string(self, field: GraphQLField) -> str:
        """Get Avro IDL type string for a GraphQL field."""
        field_type: GraphQLType = field.type
        is_required = is_non_null_type(field_type)

        if is_required:
            field_type = cast(GraphQLNonNull[GraphQLNullableType], field_type).of_type

        avro_type = self._get_avro_type(field_type, field)

        if self.strict and is_required:
            return avro_type
        return f"{avro_type}?"

    def _get_avro_type(self, field_type: GraphQLType, field: GraphQLField | None = None) -> str:
        """Get Avro IDL type for a GraphQL field type."""
        if is_list_type(field_type):
            list_type = cast(GraphQLList[GraphQLType], field_type)
            element_type: GraphQLType = list_type.of_type

            if is_non_null_type(element_type):
                element_type = cast(GraphQLNonNull[GraphQLNullableType], element_type).of_type

            element_type_str = self._get_avro_type(element_type)
            return f"array<{element_type_str}>"

        if is_scalar_type(field_type):
            scalar_type = cast(GraphQLScalarType, field_type)
            return get_avro_scalar_type(scalar_type, field)

        if is_enum_type(field_type):
            enum_type = cast(GraphQLEnumType, field_type)
            return enum_type.name if self.strict else "string"

        if is_object_type(field_type) or is_union_type(field_type):
            named_type = cast(GraphQLNamedType, field_type)
            return named_type.name

        log.warning(f"Unsupported GraphQL type '{field_type}' for Avro IDL protocol conversion, using string")
        return "string"

    def _get_field_comment(self, field: GraphQLField) -> str:
        """Get comment for enum fields in non-strict mode."""
        if self.strict:
            return ""

        base_type = get_named_type(field.type)
        if is_enum_type(base_type):
            return f"/* enum {base_type.name} */"

        return ""
