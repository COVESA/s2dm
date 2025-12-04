from typing import Any, cast

from graphql import (
    DocumentNode,
    GraphQLEnumType,
    GraphQLField,
    GraphQLInterfaceType,
    GraphQLList,
    GraphQLNamedType,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    GraphQLType,
    GraphQLUnionType,
    OperationDefinitionNode,
    OperationType,
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
from s2dm.exporters.utils.directive import get_directive_arguments, has_given_directive
from s2dm.exporters.utils.extraction import get_all_named_types
from s2dm.exporters.utils.field import get_cardinality
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

PROTOBUF_DATA_TYPES = set(GRAPHQL_SCALAR_TO_PROTOBUF.values())


class ProtobufTransformer:
    """
    Transformer class to convert GraphQL schema to Protocol Buffers format.

    This class provides methods to transform various GraphQL types into their
    corresponding Protobuf definitions (messages, enums, etc.).
    """

    def __init__(
        self,
        graphql_schema: GraphQLSchema,
        selection_query: DocumentNode,
        package_name: str | None = None,
        flatten_root_types: list[str] | None = None,
    ):
        if selection_query is None:
            raise ValueError("selection_query is required")

        self.graphql_schema = graphql_schema
        self.package_name = package_name
        self.flatten_root_types = flatten_root_types or []
        self.flatten_naming = len(self.flatten_root_types) > 0
        self.selection_query = selection_query

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

        user_defined_types = get_all_named_types(self.graphql_schema)

        log.debug(f"Found {len(user_defined_types)} user-defined types to transform")

        enum_types: list[GraphQLEnumType] = []
        message_types: list[GraphQLObjectType | GraphQLInterfaceType] = []
        union_types: list[GraphQLUnionType] = []

        for type_def in user_defined_types:
            if is_enum_type(type_def):
                enum_types.append(cast(GraphQLEnumType, type_def))
            elif is_object_type(type_def):
                message_types.append(cast(GraphQLObjectType, type_def))
            elif is_interface_type(type_def):
                message_types.append(cast(GraphQLInterfaceType, type_def))
            elif is_union_type(type_def):
                union_types.append(cast(GraphQLUnionType, type_def))

        proto_schema = ProtoSchema(
            package=self.package_name,
            enums=[],
            flatten_mode=self.flatten_naming,
        )

        if self.flatten_naming:
            # In flatten mode, we need a second filtering pass to remove types that were completely flattened.
            # When object fields are flattened, they become prefixed fields in the parent (e.g., parent_child_field).
            # If no fields reference that object type directly (non-flattened), the type definition is no longer needed.
            # However, unions and enums cannot be flattened and must remain as separate type definitions.
            (
                flattened_fields,
                referenced_type_names,
                flattened_root_types,
            ) = self._build_flattened_fields(message_types)
            message_types = [
                message_type
                for message_type in message_types
                if message_type.name in referenced_type_names and message_type.name not in flattened_root_types
            ]
            union_types = [union_type for union_type in union_types if union_type.name in referenced_type_names]
            enum_types = [enum_type for enum_type in enum_types if enum_type.name in referenced_type_names]

        proto_schema.enums = self._build_enums(enum_types)
        proto_schema.unions = self._build_unions(union_types)
        proto_schema.messages = self._build_messages(message_types)

        if self.flatten_naming:
            root_message_name = self._get_query_operation_name()
            root_message_source = f"query: {root_message_name}"
            root_message = ProtoMessage(
                name=root_message_name,
                fields=flattened_fields,
                source=root_message_source,
            )
            proto_schema.messages.append(root_message)

        template_name = "proto_standard.j2"
        template = self.env.get_template(template_name)

        template_vars = self._build_template_vars(proto_schema)

        result = template.render(template_vars)

        log.info("Successfully transformed GraphQL schema to Protobuf")
        return result

    def _has_field_options(self, proto_schema: ProtoSchema) -> bool:
        """Check if any field in the schema has field options."""

        def check_message(message: ProtoMessage) -> bool:
            if any(field.field_options for field in message.fields):
                return True
            return any(check_message(nested) for nested in message.nested_messages)

        return any(check_message(message) for message in proto_schema.messages)

    def _has_source_option(self, proto_schema: ProtoSchema) -> bool:
        """Check if any type in the schema has a source option."""
        return any(enum.source for enum in proto_schema.enums) or any(
            message.source for message in proto_schema.messages
        )

    def _get_query_operation_name(self) -> str:
        """Extract the operation name from the selection query, defaulting to appropriate fallback."""
        default_name = "Message" if self.flatten_naming else "Query"

        for definition in self.selection_query.definitions:
            if not isinstance(definition, OperationDefinitionNode) or definition.operation != OperationType.QUERY:
                continue

            if definition.name:
                return definition.name.value
            return default_name

        return default_name

    def _build_template_vars(self, proto_schema: ProtoSchema) -> dict[str, Any]:
        """Build all template variables from proto schema."""
        has_source_option = self._has_source_option(proto_schema)
        has_field_options = self._has_field_options(proto_schema)

        imports = []
        if has_source_option:
            imports.append('import "google/protobuf/descriptor.proto";')
        if has_field_options:
            imports.append('import "buf/validate/validate.proto";')

        template_vars = proto_schema.model_dump()
        template_vars["imports"] = imports
        template_vars["has_source_option"] = has_source_option

        return template_vars

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
                    source=enum_type.name,
                )
            )
        return enums

    def _build_messages(self, message_types: list[GraphQLObjectType | GraphQLInterfaceType]) -> list[ProtoMessage]:
        """Build Pydantic models for message types."""
        messages = []
        for message_type in message_types:
            fields, nested_messages = self._build_message_fields(message_type)

            message_name = message_type.name
            source = message_type.name

            if message_type.name == "Query":
                message_name = self._get_query_operation_name()
                source = f"query: {message_name}"

            messages.append(
                ProtoMessage(
                    name=message_name,
                    fields=fields,
                    description=message_type.description,
                    source=source,
                    nested_messages=nested_messages,
                )
            )
        return messages

    def _build_message_fields(
        self, message_type: GraphQLObjectType | GraphQLInterfaceType
    ) -> tuple[list[ProtoField], list[ProtoMessage]]:
        """Build Pydantic models for fields in a message."""
        fields = []
        nested_messages: list[ProtoMessage] = []
        field_number = 1

        for field_name, field in message_type.fields.items():
            proto_field_type = self._get_field_proto_type(field.type)
            field_options = self.process_field_options(field, proto_field_type)
            proto_field_name = self._escape_field_name(field_name)

            fields.append(
                ProtoField(
                    name=proto_field_name,
                    type=proto_field_type,
                    number=field_number,
                    description=field.description,
                    field_options=field_options,
                )
            )
            field_number += 1

        return fields, nested_messages

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
                    source=union_type.name,
                )
            )
        return unions

    def _build_flattened_fields(
        self, message_types: list[GraphQLObjectType | GraphQLInterfaceType]
    ) -> tuple[list[ProtoField], set[str], set[str]]:
        """Build flattened fields for flatten_naming mode.

        Returns:
            tuple: (flattened_fields, referenced_types, flattened_root_types)
        """
        type_cache = {type_def.name: type_def for type_def in message_types}

        if not self.flatten_root_types:
            log.warning("No root-level types provided for flatten mode, creating empty message")
            return [], set(), set()

        all_fields: list[ProtoField] = []
        all_referenced_types: set[str] = set()
        flattened_root_types: set[str] = set()
        field_counter = 1

        for type_name in self.flatten_root_types:
            root_object = type_cache.get(type_name)
            if not root_object:
                log.warning(f"Root-level type '{type_name}' not found in message types")
                continue

            flattened_root_types.add(type_name)
            fields, referenced_types, field_counter = self._flatten_fields(
                root_object, type_name, message_types, field_counter, type_cache
            )
            all_fields.extend(fields)
            all_referenced_types.update(referenced_types)

        return all_fields, all_referenced_types, flattened_root_types

    def _create_proto_field_with_validation(
        self, field: GraphQLField, field_name: str, proto_type: str, field_number: int, source: str | None = None
    ) -> ProtoField:
        """Create a ProtoField with field options from directives and source."""
        field_options = self.process_field_options(field, proto_type, source)
        return ProtoField(
            name=field_name,
            type=proto_type,
            number=field_number,
            description=field.description,
            field_options=field_options,
        )

    def _should_flatten_field(self, unwrapped_type: GraphQLType, is_list: bool) -> bool:
        """Check if a field should be recursively flattened into parent fields."""
        if is_list:
            return False
        if is_union_type(unwrapped_type):
            return False
        return is_object_type(unwrapped_type) or is_interface_type(unwrapped_type)

    def _add_type_with_dependencies(self, type_name: str, referenced_types: set[str]) -> None:
        """Add a type and all its transitive dependencies to the referenced_types set."""
        dependencies = get_referenced_types(self.graphql_schema, type_name, include_instance_tag_fields=True)
        for dependency in dependencies:
            if isinstance(dependency, GraphQLNamedType):
                referenced_types.add(dependency.name)

    def _flatten_fields(
        self,
        object_type: GraphQLObjectType | GraphQLInterfaceType,
        prefix: str,
        all_types: list[GraphQLObjectType | GraphQLInterfaceType],
        field_counter: int,
        type_cache: dict[str, GraphQLObjectType | GraphQLInterfaceType] | None = None,
    ) -> tuple[list[ProtoField], set[str], int]:
        """Recursively flatten fields with prefix."""
        if type_cache is None:
            type_cache = {type_def.name: type_def for type_def in all_types}

        fields: list[ProtoField] = []
        referenced_types: set[str] = set()

        for field_name, field in object_type.fields.items():
            field_type = field.type
            unwrapped_type = get_named_type(field_type)

            inner = field_type.of_type if is_non_null_type(field_type) else field_type
            is_list = is_list_type(inner)
            should_flatten = self._should_flatten_field(unwrapped_type, is_list)

            flattened_name = f"{prefix}_{field_name}"
            proto_type = self._get_field_proto_type(field_type)

            if should_flatten:
                named_unwrapped_type = cast(GraphQLObjectType | GraphQLInterfaceType, unwrapped_type)
                nested_type = type_cache.get(named_unwrapped_type.name)

                if nested_type:
                    nested_fields, nested_referenced, field_counter = self._flatten_fields(
                        nested_type, flattened_name, all_types, field_counter, type_cache
                    )
                    fields.extend(nested_fields)
                    referenced_types.update(nested_referenced)
                else:
                    raise ValueError(f"Type '{named_unwrapped_type.name}' not found in available types")
            else:
                if is_list and (is_object_type(unwrapped_type) or is_interface_type(unwrapped_type)):
                    named_type = cast(GraphQLObjectType | GraphQLInterfaceType, unwrapped_type)
                    self._add_type_with_dependencies(named_type.name, referenced_types)
                elif is_union_type(unwrapped_type):
                    union_type_cast = cast(GraphQLUnionType, unwrapped_type)
                    self._add_type_with_dependencies(union_type_cast.name, referenced_types)
                    for member_type in union_type_cast.types:
                        self._add_type_with_dependencies(member_type.name, referenced_types)

                fields.append(
                    self._create_proto_field_with_validation(
                        field=field,
                        field_name=flattened_name,
                        proto_type=proto_type,
                        field_number=field_counter,
                        source=object_type.name,
                    )
                )
                field_counter += 1

        return fields, referenced_types, field_counter

    def _get_field_proto_type(self, field_type: GraphQLType) -> str:
        """Get the Protobuf type string for a GraphQL field type."""
        proto_type = self._get_base_proto_type(field_type)

        if not is_non_null_type(field_type) and not proto_type.startswith("repeated "):
            return f"optional {proto_type}"
        return proto_type

    def _get_base_proto_type(self, field_type: GraphQLType) -> str:
        """Get the base Protobuf type string without optional prefix."""
        if is_non_null_type(field_type):
            return self._get_base_proto_type(cast(GraphQLNonNull[Any], field_type).of_type)

        if is_list_type(field_type):
            list_type = cast(GraphQLList[Any], field_type)
            item_type = self._get_base_proto_type(list_type.of_type)
            return f"repeated {item_type}"

        if is_scalar_type(field_type):
            scalar_type = cast(GraphQLScalarType, field_type)
            return GRAPHQL_SCALAR_TO_PROTOBUF.get(scalar_type.name, "string")

        if is_enum_type(field_type):
            enum_type = cast(GraphQLEnumType, field_type)
            return f"{enum_type.name}.Enum"

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

    def process_field_options(self, field: GraphQLField, proto_type: str, source: str | None = None) -> str | None:
        """Process GraphQL directives and source, converting them to protobuf field options."""
        rules = []

        if source:
            rules.append(f'(field_source) = "{source}"')

        if is_non_null_type(field.type):
            rules.append("(buf.validate.field).required = true")

        repeated_rules = []
        is_repeated = "repeated" in proto_type

        if has_given_directive(field, "noDuplicates"):
            unwrapped_type = get_named_type(field.type)
            if is_scalar_type(unwrapped_type) or is_enum_type(unwrapped_type):
                repeated_rules.append("unique: true")

        cardinality = get_cardinality(field)
        if cardinality:
            if cardinality.min is not None:
                repeated_rules.append(f"min_items: {cardinality.min}")
            if cardinality.max is not None:
                repeated_rules.append(f"max_items: {cardinality.max}")

        if has_given_directive(field, "range"):
            args = get_directive_arguments(field, "range")
            scalar_type = self._get_validation_type(proto_type)
            if scalar_type:
                range_rules = []
                if "min" in args:
                    range_rules.append(f"gte: {args['min']}")
                if "max" in args:
                    range_rules.append(f"lte: {args['max']}")
                if range_rules:
                    if is_repeated:
                        repeated_rules.append(f"items: {{{scalar_type}: {{{', '.join(range_rules)}}}}}")
                    else:
                        rules.append(f"(buf.validate.field).{scalar_type} = {{{', '.join(range_rules)}}}")

        if repeated_rules:
            rules.append(f"(buf.validate.field).repeated = {{{', '.join(repeated_rules)}}}")

        if rules:
            return f"[{', '.join(rules)}]"
        return None

    def _get_validation_type(self, proto_type: str) -> str | None:
        """Get the protovalidate scalar type from protobuf type."""
        validation_type = proto_type.replace("repeated ", "").replace("optional ", "")
        return validation_type if validation_type in PROTOBUF_DATA_TYPES else None
