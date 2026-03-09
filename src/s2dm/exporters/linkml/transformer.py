from collections.abc import Mapping
from typing import Any

import yaml
from graphql import (
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLField,
    GraphQLInputField,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLList,
    GraphQLNamedType,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLUnionType,
    Undefined,
    get_named_type,
)
from graphql.language.ast import ValueNode
from graphql.language.printer import print_ast
from linkml_runtime.linkml_model.meta import (
    AnonymousSlotExpression,
    ClassDefinition,
    EnumDefinition,
    PermissibleValue,
    SchemaDefinition,
    SlotDefinition,
    TypeDefinition,
)
from linkml_runtime.linkml_model.units import UnitOfMeasure
from linkml_runtime.utils.schema_as_dict import schema_as_dict

from s2dm.exporters.utils.annotated_schema import AnnotatedSchema
from s2dm.exporters.utils.directive import get_argument_content, get_directive_arguments, has_given_directive
from s2dm.exporters.utils.field import FieldCase, get_cardinality, get_field_case
from s2dm.exporters.utils.graphql_type import is_builtin_scalar_type

SCALAR_RANGE_MAP: Mapping[str, str] = {
    "String": "string",
    "Int": "integer",
    "Float": "float",
    "Boolean": "boolean",
    "ID": "string",
    "Int8": "integer",
    "UInt8": "integer",
    "Int16": "integer",
    "UInt16": "integer",
    "UInt32": "integer",
    "Int64": "integer",
    "UInt64": "integer",
}


class LinkmlTransformer:
    """Transform an annotated GraphQL schema to a LinkML schema document."""

    def __init__(
        self,
        annotated_schema: AnnotatedSchema,
        schema_id: str,
        schema_name: str,
        default_prefix: str,
        default_prefix_url: str,
    ) -> None:
        self.annotated_schema = annotated_schema
        self.schema_id = schema_id
        self.schema_name = schema_name
        self.default_prefix = default_prefix
        self.default_prefix_url = default_prefix_url

    def transform(self) -> str:
        """Return a LinkML schema YAML string."""
        schema_definition = SchemaDefinition(
            id=self.schema_id,
            name=self.schema_name,
            prefixes={
                "linkml": "https://w3id.org/linkml/",
                self.default_prefix: self.default_prefix_url,
            },
            default_prefix=self.default_prefix,
            imports=["linkml:types"],
            default_range="string",
            classes=self._build_classes(),
        )

        enum_definitions = self._build_enums()
        if enum_definitions:
            schema_definition.enums = enum_definitions

        type_definitions = self._build_custom_scalar_types()
        if type_definitions:
            schema_definition.types = type_definitions

        return yaml.safe_dump(schema_as_dict(schema_definition), sort_keys=False)

    def _build_classes(self) -> dict[str, ClassDefinition]:
        class_definitions: dict[str, ClassDefinition] = {}

        for type_name in self.annotated_schema.schema.type_map:
            named_type = self.annotated_schema.schema.type_map[type_name]
            if not isinstance(named_type, GraphQLObjectType | GraphQLInputObjectType | GraphQLInterfaceType) or (
                self._is_intermediate_type(named_type.name)
            ):
                continue

            class_definition = ClassDefinition(
                name=named_type.name,
                attributes=self._build_attributes(named_type),
            )

            if named_type.description:
                class_definition.description = named_type.description

            if isinstance(named_type, GraphQLInterfaceType):
                class_definition.abstract = True

            if isinstance(named_type, GraphQLObjectType):
                interface_names = [
                    interface.name
                    for interface in named_type.interfaces
                    if not self._is_intermediate_type(interface.name)
                ]
                if interface_names:
                    class_definition.is_a = interface_names[0]
                    class_definition.mixins = interface_names[1:]

            self._apply_metadata_annotations_from_source(class_definition, named_type)
            class_definitions[named_type.name] = class_definition

        return class_definitions

    def _build_enums(self) -> dict[str, EnumDefinition]:
        enum_definitions: dict[str, EnumDefinition] = {}

        for type_name in self.annotated_schema.schema.type_map:
            named_type = self.annotated_schema.schema.type_map[type_name]
            if not isinstance(named_type, GraphQLEnumType) or self._is_intermediate_type(named_type.name):
                continue

            enum_definition = EnumDefinition(
                name=named_type.name,
                permissible_values={
                    enum_value_name: PermissibleValue(text=enum_value_name) for enum_value_name in named_type.values
                },
            )
            if named_type.description:
                enum_definition.description = named_type.description
            enum_definitions[named_type.name] = enum_definition

        return enum_definitions

    def _build_custom_scalar_types(self) -> dict[str, TypeDefinition]:
        type_definitions: dict[str, TypeDefinition] = {}

        for type_name in self.annotated_schema.schema.type_map:
            named_type = self.annotated_schema.schema.type_map[type_name]
            if not isinstance(named_type, GraphQLScalarType) or self._is_intermediate_type(named_type.name):
                continue
            if is_builtin_scalar_type(named_type.name):
                continue
            if named_type.name in SCALAR_RANGE_MAP:
                continue

            type_definition = TypeDefinition(name=named_type.name, base="string")
            if named_type.description:
                type_definition.description = named_type.description
            type_definitions[named_type.name] = type_definition

        return type_definitions

    def _build_attributes(
        self,
        named_type: GraphQLObjectType | GraphQLInputObjectType | GraphQLInterfaceType,
    ) -> dict[str, SlotDefinition]:
        attributes: dict[str, SlotDefinition] = {}

        for field_name in named_type.fields:
            field = named_type.fields[field_name]
            attributes[field_name] = self._build_slot_definition(named_type.name, field_name, field)

        return attributes

    def _build_slot_definition(
        self,
        parent_type_name: str,
        field_name: str,
        field: GraphQLField | GraphQLInputField,
    ) -> SlotDefinition:
        named_type = get_named_type(field.type)
        required, multivalued, list_item_required = self._extract_multiplicity(field)

        field_metadata = self.annotated_schema.field_metadata.get((parent_type_name, field_name))
        if field_metadata and field_metadata.is_expanded:
            slot_definition = SlotDefinition(name=field_name, range=field_metadata.resolved_type)
        else:
            slot_definition = self._build_slot_with_range(field_name, named_type)

        if required:
            slot_definition.required = True
        if multivalued:
            slot_definition.multivalued = True
        if list_item_required and multivalued:
            self._merge_annotations(slot_definition, {"s2dm_list_item_required": "true"})

        if field.description:
            slot_definition.description = field.description

        self._apply_unit_mapping(slot_definition, field)
        self._apply_field_constraints(slot_definition, field, multivalued)
        self._apply_metadata_annotations_from_source(slot_definition, field)

        return slot_definition

    def _build_slot_with_range(self, field_name: str, named_type: GraphQLNamedType) -> SlotDefinition:
        if isinstance(named_type, GraphQLUnionType):
            any_of_ranges = [
                AnonymousSlotExpression(range=member_type.name)
                for member_type in named_type.types
                if not self._is_intermediate_type(member_type.name)
            ]
            if any_of_ranges:
                return SlotDefinition(name=field_name, any_of=any_of_ranges)
            return SlotDefinition(name=field_name, range="string")

        return SlotDefinition(name=field_name, range=self._to_linkml_range(named_type))

    def _extract_multiplicity(self, field: GraphQLField | GraphQLInputField) -> tuple[bool, bool, bool]:
        if isinstance(field, GraphQLField):
            field_case = get_field_case(field)
            return self._multiplicity_from_field_case(field_case)

        field_type = field.type
        if isinstance(field_type, GraphQLNonNull):
            required = True
            unwrapped_type = field_type.of_type
        else:
            required = False
            unwrapped_type = field_type

        if isinstance(unwrapped_type, GraphQLList):
            multivalued = True
            item_required = isinstance(unwrapped_type.of_type, GraphQLNonNull)
        else:
            multivalued = False
            item_required = False

        return required, multivalued, item_required

    def _multiplicity_from_field_case(self, field_case: FieldCase) -> tuple[bool, bool, bool]:
        """Map a GraphQL field case to required/list/item-nullability flags.

        Returns:
            tuple[bool, bool, bool]: A tuple of `(required, multivalued, list_item_required)` where
                `required` indicates whether the slot itself is non-null,
                `multivalued` indicates whether the slot is a list,
                and `list_item_required` indicates whether list items are non-null.
        """
        if field_case == FieldCase.DEFAULT:
            return False, False, False
        if field_case == FieldCase.NON_NULL:
            return True, False, False
        if field_case == FieldCase.LIST:
            return False, True, False
        if field_case == FieldCase.NON_NULL_LIST:
            return True, True, False
        if field_case == FieldCase.LIST_NON_NULL:
            return False, True, True

        return True, True, True

    def _apply_field_constraints(
        self,
        slot_definition: SlotDefinition,
        field: GraphQLField | GraphQLInputField,
        multivalued: bool,
    ) -> None:
        range_arguments = get_directive_arguments(field, "range") if has_given_directive(field, "range") else {}
        min_value = range_arguments.get("min")
        max_value = range_arguments.get("max")
        if isinstance(min_value, int | float):
            slot_definition.minimum_value = min_value
        if isinstance(max_value, int | float):
            slot_definition.maximum_value = max_value

        cardinality = get_cardinality(field)
        if cardinality:
            if cardinality.min is not None:
                slot_definition.minimum_cardinality = cardinality.min
            if cardinality.max is not None:
                slot_definition.maximum_cardinality = cardinality.max

        if multivalued and has_given_directive(field, "noDuplicates"):
            slot_definition.list_elements_unique = True

    def _apply_unit_mapping(self, slot_definition: SlotDefinition, field: GraphQLField | GraphQLInputField) -> None:
        if not isinstance(field, GraphQLField):
            return

        unit_argument = field.args.get("unit")
        if unit_argument is None:
            return

        default_unit = unit_argument.default_value
        if default_unit is None or default_unit is Undefined:
            return

        unit_type = get_named_type(unit_argument.type)
        if not isinstance(unit_type, GraphQLEnumType):
            return

        enum_match = self._resolve_enum_value(unit_type, str(default_unit))
        if enum_match is None:
            return

        unit_symbol, enum_value = enum_match
        unit_payload: dict[str, Any] = {"symbol": unit_symbol}

        unit_uri = get_argument_content(enum_value, "reference", "uri")
        if unit_uri:
            unit_payload["exact_mappings"] = [unit_uri]

        quantity_kind_uri = get_argument_content(unit_type, "reference", "uri")
        if quantity_kind_uri:
            unit_payload["has_quantity_kind"] = quantity_kind_uri

        slot_definition.unit = UnitOfMeasure(**unit_payload)

    def _resolve_enum_value(
        self,
        enum_type: GraphQLEnumType,
        default_symbol: str,
    ) -> tuple[str, GraphQLEnumValue] | None:
        direct_match = enum_type.values.get(default_symbol)
        if direct_match is not None:
            return default_symbol, direct_match

        for enum_symbol, enum_value in enum_type.values.items():
            if str(enum_value.value) == default_symbol:
                return enum_symbol, enum_value

        return None

    def _apply_metadata_annotations_from_source(
        self,
        target_definition: SlotDefinition | ClassDefinition,
        source_element: GraphQLField
        | GraphQLInputField
        | GraphQLObjectType
        | GraphQLInputObjectType
        | GraphQLInterfaceType,
    ) -> None:
        if not has_given_directive(source_element, "metadata"):
            return

        metadata_arguments = get_directive_arguments(source_element, "metadata")
        annotations = {
            f"s2dm_metadata_{key}": self._stringify_directive_value(value)
            for key, value in metadata_arguments.items()
            if value is not None
        }
        self._merge_annotations(target_definition, annotations)

    def _merge_annotations(
        self,
        target_definition: SlotDefinition | ClassDefinition,
        annotations: dict[str, str],
    ) -> None:
        if not annotations:
            return

        existing_annotations = target_definition.annotations or {}
        merged_annotations: dict[str, Any] = {str(key): value for key, value in existing_annotations.items()}
        merged_annotations.update(annotations)
        target_definition.annotations = merged_annotations

    def _stringify_directive_value(self, value: Any) -> str:
        if isinstance(value, ValueNode):
            return print_ast(value)
        return str(value)

    def _to_linkml_range(self, named_type: GraphQLNamedType) -> str:
        if isinstance(named_type, GraphQLScalarType):
            return SCALAR_RANGE_MAP.get(named_type.name, named_type.name)
        return named_type.name

    def _is_intermediate_type(self, type_name: str) -> bool:
        type_metadata = self.annotated_schema.type_metadata.get(type_name)
        return bool(type_metadata and type_metadata.is_intermediate_type)
