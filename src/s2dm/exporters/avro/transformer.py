from typing import Any, cast

from graphql import (
    DocumentNode,
    GraphQLEnumType,
    GraphQLField,
    GraphQLInterfaceType,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLType,
    GraphQLUnionType,
    is_enum_type,
    is_interface_type,
    is_list_type,
    is_non_null_type,
    is_object_type,
    is_scalar_type,
    is_union_type,
)

from s2dm import log
from s2dm.exporters.utils.annotated_schema import AnnotatedSchema
from s2dm.exporters.utils.extraction import get_all_named_types, get_query_operation_name

from .common import get_avro_scalar_type


class AvroTransformer:
    """
    Transformer class to convert GraphQL schema to Apache Avro schema format.

    This class provides methods to transform various GraphQL types into their
    corresponding Avro schema definitions, handling directives and nested types.
    """

    def __init__(
        self,
        annotated_schema: AnnotatedSchema,
        namespace: str,
        selection_query: DocumentNode,
    ):
        if selection_query is None:
            raise ValueError("selection_query is required")

        self.annotated_schema = annotated_schema
        self.graphql_schema = annotated_schema.schema
        self.namespace = namespace
        self.selection_query = selection_query
        self.transformed_types: set[str] = set()

    def transform(self) -> dict[str, Any]:
        """
        Transform a GraphQL schema to Avro schema format.

        Returns:
            dict[str, Any]: Single Avro schema with nested inline type definitions
        """
        user_defined_types = get_all_named_types(self.graphql_schema)
        log.debug(f"Found {len(user_defined_types)} user-defined types to transform")

        query_type = self.graphql_schema.query_type
        if not query_type:
            raise ValueError("Schema does not have a Query type")

        query_name = get_query_operation_name(self.selection_query, "Query")
        log.debug(f"Transforming with operation name: {query_name}")

        self.transformed_types.add(query_type.name)

        avro_schema = self.transform_graphql_type(query_type)
        if not avro_schema:
            raise ValueError("Failed to transform Query type")

        avro_schema["name"] = query_name
        return avro_schema

    def transform_graphql_type(self, graphql_type: GraphQLType) -> dict[str, Any] | None:
        """
        Transform a single GraphQL type to Avro schema definition.

        Args:
            graphql_type: The GraphQL type to transform

        Returns:
            dict[str, Any] | None: Avro schema definition or None if not transformable
        """
        if is_object_type(graphql_type):
            return self.transform_object_type(cast(GraphQLObjectType, graphql_type))
        elif is_interface_type(graphql_type):
            return self.transform_object_type(cast(GraphQLInterfaceType, graphql_type))
        elif is_enum_type(graphql_type):
            return self.transform_enum_type(cast(GraphQLEnumType, graphql_type))
        elif is_union_type(graphql_type):
            return self.transform_union_type(cast(GraphQLUnionType, graphql_type))
        else:
            log.warning(
                f"Unsupported GraphQL type: {type(graphql_type)} found in element {graphql_type} of the given schema"
            )
            return None

    def _create_avro_record_base(self, name: str, description: str | None = None) -> dict[str, Any]:
        """
        Create a base Avro record structure with name and namespace.

        Args:
            name: The name of the record
            description: Optional description for the record

        Returns:
            dict[str, Any]: Base Avro record structure
        """
        avro_record: dict[str, Any] = {
            "type": "record",
            "name": name,
            "namespace": self.namespace,
            "fields": [],
        }

        if description:
            avro_record["doc"] = description

        return avro_record

    def _get_type_reference(self, type_name: str) -> str:
        """
        Get a fully qualified type reference with namespace.

        Args:
            type_name: The name of the type

        Returns:
            str: Fully qualified type name
        """
        return f"{self.namespace}.{type_name}"

    def transform_object_type(self, object_type: GraphQLObjectType | GraphQLInterfaceType) -> dict[str, Any]:
        """
        Transform a GraphQL object or interface type to Avro record.

        Args:
            object_type: The GraphQL object or interface type

        Returns:
            dict[str, Any]: Avro record definition
        """
        avro_record = self._create_avro_record_base(object_type.name, object_type.description)

        for field_name, field in object_type.fields.items():
            field_definition = self.transform_field(field_name, field)
            avro_record["fields"].append(field_definition)

        return avro_record

    def transform_field(self, field_name: str, field: GraphQLField) -> dict[str, Any]:
        """
        Transform a GraphQL field to Avro field.

        Args:
            field_name: The name of the field
            field: The GraphQL field

        Returns:
            dict[str, Any]: Avro field definition
        """
        field_definition: dict[str, Any] = {
            "name": field_name,
            "type": self.get_field_type_definition(field.type, field),
        }

        if field.description:
            field_definition["doc"] = field.description

        return field_definition

    def get_field_type_definition(self, field_type: GraphQLType, field: GraphQLField | None = None) -> Any:
        """
        Get Avro type definition for a GraphQL field type.

        Args:
            field_type: The GraphQL field type
            field: Optional GraphQL field object for accessing directives

        Returns:
            Any: Avro type definition (can be string, list, or dict)
        """
        is_required = is_non_null_type(field_type)
        if is_required:
            field_type = cast(GraphQLNonNull[Any], field_type).of_type

        avro_type = self._get_avro_type(field_type, field)

        if is_required:
            return avro_type
        return ["null", avro_type]

    def _get_avro_type(self, field_type: GraphQLType, field: GraphQLField | None = None) -> Any:
        """
        Get Avro type for a GraphQL field type without nullability wrapper.

        Args:
            field_type: The GraphQL field type (without NonNull wrapper)
            field: Optional GraphQL field object for accessing directives

        Returns:
            Any: Avro type definition
        """
        if is_list_type(field_type):
            list_type = cast(GraphQLList[Any], field_type)
            item_type = self.get_field_type_definition(list_type.of_type)
            return {"type": "array", "items": item_type}

        if is_scalar_type(field_type):
            scalar_type = cast(GraphQLScalarType, field_type)
            return get_avro_scalar_type(scalar_type, field)

        if is_enum_type(field_type):
            enum_type = cast(GraphQLEnumType, field_type)
            if enum_type.name in self.transformed_types:
                return self._get_type_reference(enum_type.name)
            self.transformed_types.add(enum_type.name)
            return self.transform_enum_type(enum_type)

        if is_object_type(field_type) or is_interface_type(field_type):
            return self._process_field_object_type(field_type)

        if is_union_type(field_type):
            union_type = cast(GraphQLUnionType, field_type)
            if union_type.name in self.transformed_types:
                return self._get_type_reference(union_type.name)
            self.transformed_types.add(union_type.name)
            return self.transform_union_type(union_type)

        log.warning(f"Unsupported GraphQL type '{field_type}' for Avro conversion, using null")
        return "null"

    def _process_field_object_type(self, field_type: GraphQLType) -> Any:
        """
        Process a GraphQL field type that is an object type.

        Args:
            field_type: The GraphQL field type

        Returns:
            Any: Avro type definition for the object type
        """
        named_type = cast(GraphQLObjectType | GraphQLInterfaceType, field_type)

        if named_type.name in self.transformed_types:
            return self._get_type_reference(named_type.name)

        self.transformed_types.add(named_type.name)
        return self.transform_object_type(named_type)

    def transform_enum_type(self, enum_type: GraphQLEnumType) -> dict[str, Any]:
        """
        Transform a GraphQL enum type to Avro enum.

        Args:
            enum_type: The GraphQL enum type

        Returns:
            dict[str, Any]: Avro enum definition
        """
        enum_values = list(enum_type.values.keys())

        avro_enum: dict[str, Any] = {
            "type": "enum",
            "name": enum_type.name,
            "namespace": self.namespace,
            "symbols": enum_values,
        }

        if enum_type.description:
            avro_enum["doc"] = enum_type.description

        return avro_enum

    def transform_union_type(self, union_type: GraphQLUnionType) -> dict[str, Any]:
        """
        Transform a GraphQL union type to Avro record with union field.

        Args:
            union_type: The GraphQL union type

        Returns:
            dict[str, Any]: Avro record definition with union field
        """
        union_members: list[Any] = []
        for member_type in union_type.types:
            if member_type.name in self.transformed_types:
                union_members.append(self._get_type_reference(member_type.name))
                continue

            self.transformed_types.add(member_type.name)
            transformed = self.transform_graphql_type(member_type)
            if transformed:
                union_members.append(transformed)

        avro_record = self._create_avro_record_base(union_type.name, union_type.description)
        avro_record["fields"] = [
            {
                "name": "value",
                "type": ["null"] + union_members,
            }
        ]

        return avro_record
