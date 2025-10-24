from typing import Any, cast

from graphql import (
    GraphQLEnumType,
    GraphQLInterfaceType,
    GraphQLList,
    GraphQLNamedType,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    GraphQLType,
    GraphQLUnionType,
    get_named_type,
    is_enum_type,
    is_interface_type,
    is_list_type,
    is_non_null_type,
    is_object_type,
    is_scalar_type,
    is_union_type,
)
from jinja2 import Environment, PackageLoader, select_autoescape

from s2dm import log
from s2dm.exporters.protobuf.models import ProtoEnum, ProtoEnumValue, ProtoField, ProtoMessage, ProtoSchema, ProtoUnion
from s2dm.exporters.utils.directive import has_given_directive
from s2dm.exporters.utils.extraction import get_all_named_types
from s2dm.exporters.utils.instance_tag import is_instance_tag_field
from s2dm.exporters.utils.schema_loader import get_referenced_types

GRAPHQL_SCALAR_TO_PROTOBUF = {
    # Built-in GraphQL scalars
    "String": "string",
    "Int": "int32",
    "Float": "float",
    "Boolean": "bool",
    "ID": "string",
    # Custom scalars
    "Int8": "int32",
    "UInt8": "uint32",
    "Int16": "int32",
    "UInt16": "uint32",
    "UInt32": "uint32",
    "Int64": "int64",
    "UInt64": "uint64",
}

PROTOBUF_RESERVED_KEYWORDS = {
    "message",
    "enum",
    "service",
    "rpc",
    "option",
    "import",
    "package",
    "syntax",
    "reserved",
    "oneof",
    "repeated",
    "optional",
    "required",
}


class ProtobufTransformer:
    """
    Transformer class to convert GraphQL schema to Protocol Buffers format.

    This class provides methods to transform various GraphQL types into their
    corresponding Protobuf definitions (messages, enums, etc.).
    """

    def __init__(
        self,
        graphql_schema: GraphQLSchema,
        root_type: str | None = None,
        flatten_naming: bool = False,
        package_name: str | None = None,
        naming_config: dict[str, Any] | None = None,
        expanded_instances: bool = False,
    ):
        self.graphql_schema = graphql_schema
        self.root_type = root_type
        self.flatten_naming = flatten_naming
        self.package_name = package_name
        self.naming_config = naming_config
        self.expanded_instances = expanded_instances

        self.env = Environment(
            loader=PackageLoader("s2dm.exporters.protobuf", "templates"),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def transform(self) -> str:
        """
        Transform a GraphQL schema to Protocol Buffers format.

        Returns:
            str: Protobuf string representation of the GraphQL schema.
        """
        log.info("Starting GraphQL to Protobuf transformation")

        if self.root_type:
            referenced_types = get_referenced_types(self.graphql_schema, self.root_type)
            user_defined_types: list[GraphQLNamedType] = [
                referenced_type for referenced_type in referenced_types if isinstance(referenced_type, GraphQLNamedType)
            ]
        else:
            user_defined_types = get_all_named_types(self.graphql_schema)

        log.debug(f"Found {len(user_defined_types)} user-defined types to transform")

        enum_types: list[GraphQLEnumType] = []
        message_types: list[GraphQLObjectType | GraphQLInterfaceType] = []
        union_types: list[GraphQLUnionType] = []

        for type_def in user_defined_types:
            if is_enum_type(type_def):
                enum_types.append(cast(GraphQLEnumType, type_def))
            elif is_object_type(type_def):
                object_type = cast(GraphQLObjectType, type_def)
                if not has_given_directive(object_type, "instanceTag"):
                    message_types.append(object_type)
            elif is_interface_type(type_def):
                message_types.append(cast(GraphQLInterfaceType, type_def))
            elif is_union_type(type_def):
                union_types.append(cast(GraphQLUnionType, type_def))

        proto_schema = ProtoSchema(
            package=self.package_name,
            enums=self._build_enums(enum_types),
            flatten_mode=self.flatten_naming and self.root_type is not None,
        )

        if self.flatten_naming and self.root_type:
            proto_schema.flattened_fields, referenced_type_names = self._build_flattened_fields(message_types)
            message_types = [
                message_type for message_type in message_types if message_type.name in referenced_type_names
            ]
        else:
            proto_schema.unions = self._build_unions(union_types)

        proto_schema.messages = self._build_messages(message_types)

        template = self.env.get_template("proto.j2")
        result = template.render(proto_schema.model_dump())

        log.info("Successfully transformed GraphQL schema to Protobuf")
        return result

    def _build_enums(self, enum_types: list[GraphQLEnumType]) -> list[ProtoEnum]:
        """Build Pydantic models for enum types."""
        enums = []
        for enum_type in enum_types:
            enum_values = [
                ProtoEnumValue(
                    name=value_name,
                    number=index + 1,
                    description=enum_type.values[value_name].description,
                )
                for index, value_name in enumerate(enum_type.values)
            ]
            enums.append(
                ProtoEnum(
                    name=enum_type.name,
                    enum_values=enum_values,
                    description=enum_type.description,
                )
            )
        return enums

    def _build_messages(self, message_types: list[GraphQLObjectType | GraphQLInterfaceType]) -> list[ProtoMessage]:
        """Build Pydantic models for message types."""
        messages = []
        for message_type in message_types:
            fields = self._build_message_fields(message_type)

            messages.append(
                ProtoMessage(
                    name=message_type.name,
                    fields=fields,
                    description=message_type.description,
                )
            )
        return messages

    def _build_message_fields(self, message_type: GraphQLObjectType | GraphQLInterfaceType) -> list[ProtoField]:
        """Build Pydantic models for fields in a message."""
        fields = []
        field_number = 1

        for field_name, field in message_type.fields.items():
            if is_instance_tag_field(field_name):
                continue

            proto_field_type = self._get_field_proto_type(field.type)
            proto_field_name = self._escape_field_name(field_name)

            fields.append(
                ProtoField(
                    name=proto_field_name,
                    type=proto_field_type,
                    number=field_number,
                    description=field.description,
                )
            )
            field_number += 1

        return fields

    def _build_unions(self, union_types: list[GraphQLUnionType]) -> list[ProtoUnion]:
        """Build Pydantic models for union types."""
        unions = []
        for union_type in union_types:
            members = [
                ProtoField(
                    name=member_type.name,
                    type=member_type.name,
                    number=index + 1,
                )
                for index, member_type in enumerate(union_type.types)
            ]
            unions.append(
                ProtoUnion(
                    name=union_type.name,
                    members=members,
                    description=union_type.description,
                )
            )
        return unions

    def _build_flattened_fields(
        self, message_types: list[GraphQLObjectType | GraphQLInterfaceType]
    ) -> tuple[list[ProtoField], set[str]]:
        """Build flattened fields for flatten_naming mode."""
        root_object = None
        for message_type in message_types:
            if message_type.name == self.root_type:
                root_object = message_type
                break

        if not root_object:
            log.warning(f"Root type '{self.root_type}' not found, creating empty message")
            return [], set()

        fields, referenced_types, _ = self._flatten_fields(root_object, root_object.name, message_types, 1)
        return fields, referenced_types

    def _flatten_fields(
        self,
        object_type: GraphQLObjectType | GraphQLInterfaceType,
        prefix: str,
        all_types: list[GraphQLObjectType | GraphQLInterfaceType],
        field_counter: int,
    ) -> tuple[list[ProtoField], set[str], int]:
        """Recursively flatten fields with prefix."""
        fields: list[ProtoField] = []
        referenced_types: set[str] = set()
        if not hasattr(object_type, "fields"):
            return fields, referenced_types, field_counter

        for field_name, field in object_type.fields.items():
            if is_instance_tag_field(field_name):
                continue

            field_type = field.type
            unwrapped_type = get_named_type(field_type)

            inner = field_type.of_type if is_non_null_type(field_type) else field_type
            is_list = is_list_type(inner)

            flattened_name = f"{prefix}_{field_name}"
            proto_type = self._get_field_proto_type(field_type)

            is_object_interface_type = is_object_type(unwrapped_type) or is_interface_type(unwrapped_type)

            if is_list:
                if is_object_interface_type:
                    named_type = cast(GraphQLObjectType | GraphQLInterfaceType, unwrapped_type)
                    referenced_types.add(named_type.name)
                fields.append(
                    ProtoField(
                        name=flattened_name,
                        type=proto_type,
                        number=field_counter,
                        description=field.description,
                    )
                )
                field_counter += 1
                continue

            if not is_object_interface_type:
                fields.append(
                    ProtoField(
                        name=flattened_name,
                        type=proto_type,
                        number=field_counter,
                        description=field.description,
                    )
                )
                field_counter += 1
                continue

            named_unwrapped_type = cast(GraphQLObjectType | GraphQLInterfaceType, unwrapped_type)
            nested_type = self._get_type(named_unwrapped_type.name, all_types)

            if nested_type:
                nested_fields, nested_referenced, field_counter = self._flatten_fields(
                    nested_type, flattened_name, all_types, field_counter
                )
                fields.extend(nested_fields)
                referenced_types.update(nested_referenced)
            else:
                raise ValueError(f"Type '{named_unwrapped_type.name}' not found in available types")

        return fields, referenced_types, field_counter

    def _get_type(
        self, type_name: str, all_types: list[GraphQLObjectType | GraphQLInterfaceType]
    ) -> GraphQLObjectType | GraphQLInterfaceType | None:
        """Get a GraphQL type by name from a list of types."""
        for type_def in all_types:
            if type_def.name == type_name:
                return type_def
        return None

    def _get_field_proto_type(self, field_type: GraphQLType) -> str:
        """Get the Protobuf type string for a GraphQL field type."""
        if is_non_null_type(field_type):
            return self._get_field_proto_type(cast(GraphQLNonNull[Any], field_type).of_type)

        if is_list_type(field_type):
            list_type = cast(GraphQLList[Any], field_type)
            item_type = self._get_field_proto_type(list_type.of_type)
            return f"repeated {item_type}"

        if is_scalar_type(field_type):
            scalar_type = cast(GraphQLScalarType, field_type)
            return GRAPHQL_SCALAR_TO_PROTOBUF.get(scalar_type.name, "string")

        if is_enum_type(field_type):
            enum_type = cast(GraphQLEnumType, field_type)
            return enum_type.name

        if is_object_type(field_type) or is_interface_type(field_type):
            named_type = cast(GraphQLObjectType | GraphQLInterfaceType, field_type)
            return named_type.name

        if is_union_type(field_type):
            union_type = cast(GraphQLUnionType, field_type)
            return union_type.name

        return "string"

    def _escape_field_name(self, name: str) -> str:
        """Escape field names that conflict with Protobuf reserved keywords."""
        if name in PROTOBUF_RESERVED_KEYWORDS:
            return f"_{name}_"
        return name
