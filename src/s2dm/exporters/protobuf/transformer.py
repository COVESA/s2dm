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
from s2dm.exporters.utils.extraction import get_all_named_types, get_root_level_types_from_query
from s2dm.exporters.utils.field import get_cardinality
from s2dm.exporters.utils.instance_tag import expand_instance_tag, get_instance_tag_object, is_instance_tag_field
from s2dm.exporters.utils.naming import convert_name, get_target_case_for_element
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
        root_type: str | None = None,
        flatten_naming: bool = False,
        package_name: str | None = None,
        naming_config: dict[str, Any] | None = None,
        expanded_instances: bool = False,
        selection_query: DocumentNode | None = None,
    ):
        self.graphql_schema = graphql_schema
        self.root_type = root_type
        self.flatten_naming = flatten_naming
        self.package_name = package_name
        self.naming_config = naming_config
        self.expanded_instances = expanded_instances
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

        if self.root_type:
            referenced_types = get_referenced_types(self.graphql_schema, self.root_type, not self.expanded_instances)
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
                if not (has_given_directive(object_type, "instanceTag") and self.expanded_instances):
                    message_types.append(object_type)
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
                proto_schema.flattened_fields,
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

        template_name = "proto_flattened.j2" if self.flatten_naming else "proto_standard.j2"
        template = self.env.get_template(template_name)

        template_vars = self._build_template_vars(proto_schema)

        result = template.render(template_vars)

        log.info("Successfully transformed GraphQL schema to Protobuf")
        return result

    def _has_validation_rules(self, proto_schema: ProtoSchema) -> bool:
        """Check if any field in the schema has validation rules."""

        def check_message(message: ProtoMessage) -> bool:
            if any(field.validation_rules for field in message.fields):
                return True
            return any(check_message(nested) for nested in message.nested_messages)

        return any(field.validation_rules for field in proto_schema.flattened_fields) or any(
            check_message(message) for message in proto_schema.messages
        )

    def _has_source_option(self, proto_schema: ProtoSchema) -> bool:
        """Check if any type in the schema has a source option."""
        return any(enum.source for enum in proto_schema.enums) or any(
            message.source for message in proto_schema.messages
        )

    def _build_template_vars(self, proto_schema: ProtoSchema) -> dict[str, Any]:
        """Build all template variables from proto schema."""
        has_source_option = self._has_source_option(proto_schema)
        has_validation_rules = self._has_validation_rules(proto_schema)

        imports = []
        if has_source_option:
            imports.append('import "google/protobuf/descriptor.proto";')
        if has_validation_rules:
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

            messages.append(
                ProtoMessage(
                    name=message_type.name,
                    fields=fields,
                    description=message_type.description,
                    source=message_type.name,
                    nested_messages=nested_messages,
                )
            )
        return messages

    def _build_message_fields(
        self, message_type: GraphQLObjectType | GraphQLInterfaceType
    ) -> tuple[list[ProtoField], list[ProtoMessage]]:
        """Build Pydantic models for fields in a message."""
        fields = []
        nested_messages = []
        field_number = 1

        for field_name, field in message_type.fields.items():
            if is_instance_tag_field(field_name) and self.expanded_instances:
                continue

            field_type = field.type
            unwrapped_type = get_named_type(field_type)

            proto_field_name = field_name
            proto_field_type = None
            expanded_message_name = None

            if is_object_type(unwrapped_type):
                object_type = cast(GraphQLObjectType, unwrapped_type)
                expanded_instances = self._get_expanded_instances(object_type)
                if expanded_instances:
                    proto_field_name, proto_field_type, nested_message = self._handle_expanded_instance_field(
                        object_type, message_type, expanded_instances
                    )
                    nested_messages.append(nested_message)
                    expanded_message_name = proto_field_type

            if proto_field_type is None:
                proto_field_type = self._get_field_proto_type(field.type)
                proto_field_name = self._escape_field_name(field_name)

            validation_rules = None if expanded_message_name else self.process_directives(field, proto_field_type)

            fields.append(
                ProtoField(
                    name=proto_field_name,
                    type=proto_field_type,
                    number=field_number,
                    description=field.description,
                    validation_rules=validation_rules,
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

        if self.root_type:
            root_object = type_cache.get(self.root_type)
            if not root_object:
                log.warning(f"Root type '{self.root_type}' not found, creating empty message")
                return [], set(), set()

            fields, referenced_types, _ = self._flatten_fields(root_object, root_object.name, message_types, 1)
            return fields, referenced_types, {self.root_type}

        root_level_type_names = get_root_level_types_from_query(self.graphql_schema, self.selection_query)
        if not root_level_type_names:
            log.warning("No root-level types found in selection query, creating empty message")
            return [], set(), set()

        all_fields: list[ProtoField] = []
        all_referenced_types: set[str] = set()
        flattened_root_types: set[str] = set()
        field_counter = 1

        for type_name in root_level_type_names:
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
        self, field: GraphQLField, field_name: str, proto_type: str, field_number: int
    ) -> ProtoField:
        """Create a ProtoField with validation rules from directives."""
        validation_rules = self.process_directives(field, proto_type)
        return ProtoField(
            name=field_name,
            type=proto_type,
            number=field_number,
            description=field.description,
            validation_rules=validation_rules,
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
            if is_instance_tag_field(field_name) and self.expanded_instances:
                continue

            field_type = field.type
            unwrapped_type = get_named_type(field_type)

            if is_object_type(unwrapped_type):
                object_type_cast = cast(GraphQLObjectType, unwrapped_type)
                expanded_instances = self._get_expanded_instances(object_type_cast)
                if expanded_instances:
                    nested_type = type_cache.get(object_type_cast.name)
                    if nested_type:
                        for expanded_instance in expanded_instances:
                            expanded_prefix = f"{prefix}_{field_name}_{expanded_instance.replace('.', '_')}"
                            nested_fields, nested_referenced, field_counter = self._flatten_fields(
                                nested_type, expanded_prefix, all_types, field_counter, type_cache
                            )
                            fields.extend(nested_fields)
                            referenced_types.update(nested_referenced)
                    continue

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
                    self._create_proto_field_with_validation(field, flattened_name, proto_type, field_counter)
                )
                field_counter += 1

        return fields, referenced_types, field_counter

    def _get_field_proto_type(self, field_type: GraphQLType) -> str:
        """Get the Protobuf type string for a GraphQL field type."""
        proto_type = self._get_base_proto_type(field_type)

        if not is_non_null_type(field_type):
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

    def process_directives(self, field: GraphQLField, proto_type: str) -> str | None:
        """Process GraphQL directives and convert them to protovalidate constraints."""
        rules = []

        if is_non_null_type(field.type):
            rules.append("(buf.validate.field).required = true")

        repeated_rules = []

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

        if repeated_rules:
            rules.append(f"(buf.validate.field).repeated = {{{', '.join(repeated_rules)}}}")

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
                    rules.append(f"(buf.validate.field).{scalar_type} = {{{', '.join(range_rules)}}}")

        if rules:
            return f"[{', '.join(rules)}]"
        return None

    def _get_validation_type(self, proto_type: str) -> str | None:
        """Get the protovalidate scalar type from protobuf type."""
        validation_type = proto_type.replace("repeated ", "").replace("optional ", "")
        return validation_type if validation_type in PROTOBUF_DATA_TYPES else None

    def _handle_expanded_instance_field(
        self,
        object_type: GraphQLObjectType,
        message_type: GraphQLObjectType | GraphQLInterfaceType,
        expanded_instances: list[str],
    ) -> tuple[str, str, ProtoMessage]:
        """Handle expanded instance fields, returning field name, type, and nested message."""
        prefixed_message_name = f"{message_type.name}_{object_type.name}"
        nested_message = self._build_nested_message_structure(
            prefixed_message_name, expanded_instances, object_type.name
        )

        field_name_to_use = object_type.name
        if self.naming_config:
            target_case = get_target_case_for_element("field", "object", self.naming_config)
            if target_case:
                field_name_to_use = convert_name(object_type.name, target_case)

        return (self._escape_field_name(field_name_to_use), nested_message.name, nested_message)

    def _build_nested_message_structure(
        self,
        message_name: str,
        instance_paths: list[str],
        target_type: str,
    ) -> ProtoMessage:
        """Create nested message structure for expanded instance tags."""
        message = ProtoMessage(name=message_name, fields=[], nested_messages=[], source=None)
        child_paths_by_level: dict[str, list[str]] = {}
        field_counter = 1

        for instance_path in instance_paths:
            instance_path_parts = instance_path.split(".")
            if len(instance_path_parts) > 1:
                root_level_name = instance_path_parts[0]
                remaining_path = ".".join(instance_path_parts[1:])
                child_paths_by_level.setdefault(root_level_name, []).append(remaining_path)
            else:
                message.fields.append(ProtoField(name=instance_path_parts[0], type=target_type, number=field_counter))
                field_counter += 1

        for root_level_name, child_paths in child_paths_by_level.items():
            child_message_name = f"{message_name}_{root_level_name}"
            child_message = self._build_nested_message_structure(child_message_name, child_paths, target_type)
            message.nested_messages.append(child_message)
            message.fields.append(ProtoField(name=root_level_name, type=child_message.name, number=field_counter))
            field_counter += 1

        return message

    def _get_expanded_instances(self, object_type: GraphQLObjectType) -> list[str] | None:
        """Get expanded instances if the type has a valid instance tag."""
        if not self.expanded_instances:
            return None

        instance_tag_object = get_instance_tag_object(object_type, self.graphql_schema)
        if not instance_tag_object:
            return None

        return expand_instance_tag(instance_tag_object, self.naming_config)
