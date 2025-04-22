import logging
from dataclasses import dataclass

from graphql import (
    GraphQLArgument,
    GraphQLEnumType,
    GraphQLField,
    GraphQLList,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLType,
)

from tools.utils import get_directive_arguments, has_directive

logger = logging.getLogger(__name__)


class FieldTypeWrapper:
    def __init__(self, field_type: GraphQLType):
        self.field_type = field_type

    @property
    def name(self) -> str:
        return self.field_type.name

    def get_allowed_enum_values(self) -> str:
        if self.is_enum_type():
            return str(list(self.field_type.values.keys()))
        else:
            return ""

    def is_enum_type(self) -> bool:
        return isinstance(self.field_type, GraphQLEnumType)

    def is_scalar_type(self) -> bool:
        return isinstance(self.field_type, GraphQLScalarType)

    def is_list_type(self) -> bool:
        return isinstance(self.field_type, GraphQLList)

    def is_object_type(self) -> bool:
        return isinstance(self.field_type, GraphQLObjectType)

    def is_leaf_node(self) -> bool:
        return self.is_scalar_type() or self.is_enum_type()

    def is_branch_node(self) -> bool:
        return self.is_object_type() or self.is_list_type()


def to_capitalized(name: str) -> str:
    return name[0].upper() + name[1:]


@dataclass(frozen=True)
class IDGenerationSpec:
    """Collection of fields and methods required for ID generation
    @param name: fully qualified name of the field
    @param data_type: datatype of the field: string, int, float, boolean, uint8 etc.
    @param unit: unit of the field if exists
    @param allowed: the enum for allowed values
    @param minimum: min value for the data if exists
    @param maximum: max value for the data if exists
    @param _field_type: the field type
    """

    name: str
    data_type: str
    unit: str = ""
    allowed: str = ""
    minimum: int | float | None = None
    maximum: int | float | None = None

    # Internal fields
    _field_type: FieldTypeWrapper | None = None

    def __eq__(self, other: "IDGenerationSpec") -> bool:
        return (
            self.name == other.name
            and self.data_type == other.data_type
            and self.unit == other.unit
            and self.allowed == other.allowed
            and self.minimum == other.minimum
            and self.maximum == other.maximum
        )

    def __hash__(self) -> int:
        return hash(f"{self.name}:{self.data_type}:{self.unit}:{self.allowed}:{self.minimum}:{self.maximum}")

    def is_concept(self):
        return self._field_type.is_branch_node()

    def is_realization(self):
        return self._field_type.is_leaf_node()

    def get_node_identifier_bytes(
        self,
        strict_mode: bool,
    ) -> bytes:
        """Get a node identifier as bytes. Used as an input for hashing

        @param strict_mode: strict mode means case sensitivity of node qualified names
        @return: a bytes representation of the node
        """

        node_identifier: bytes = (
            f"{self.name}: "
            f"unit: {self.unit}, "
            f"datatype: {self.data_type}, "
            f"allowed: {self.allowed}"
            f"min: {self.minimum if self.minimum is not None else ''}"
            f"max: {self.maximum if self.maximum is not None else ''}"
        ).encode()

        logger.debug(f"{node_identifier=}")

        if strict_mode:
            return node_identifier
        else:
            return node_identifier.lower()

    @classmethod
    def from_field(
        cls,
        *,
        prefix: str,
        field_name: str,
        field: GraphQLField,
        unit_lookup: dict[str, str],
    ) -> "IDGenerationSpec":
        """Create an IDGenerationSpec from a GraphQL field

        @param prefix: the prefix of the fully qualified name
        @param field_name: the name of the field
        @param field: the GraphQL field to extract the ID generation spec from
        @return: an IDGenerationSpec
        """

        _field_type = field.type

        # Unwrap non-null and list types
        while hasattr(_field_type, "of_type"):
            _field_type = _field_type.of_type

        field_type = FieldTypeWrapper(_field_type)

        # Name is resolved from the field's name, type and prefix
        name = IDGenerationSpec._resolve_name(field_name, field_type, prefix)

        # Data type is resolved from the field's type (lower case name)
        data_type = IDGenerationSpec._resolve_data_type(field_type)

        # Allowed values are resolved from the field's type (string of allowed values for enums)
        allowed = IDGenerationSpec._resolve_allowed(field_type)

        # Unit is resolved from the field's "unit" argument
        field_args = field.args or {}
        unit = IDGenerationSpec._resolve_unit(field_args, unit_lookup)

        # Minimum and maximum are resolved from the field's @range directive
        minimum = IDGenerationSpec._resolve_minimum(field)
        maximum = IDGenerationSpec._resolve_maximum(field)

        return cls(
            name=name,
            data_type=data_type,
            unit=unit,
            allowed=allowed,
            minimum=minimum,
            maximum=maximum,
            _field_type=field_type,
        )

    @staticmethod
    def _resolve_data_type(field: FieldTypeWrapper) -> str:
        if field.is_scalar_type():
            # Use lowercase name for scalar types
            return field.name.lower()
        elif field.is_enum_type():
            # Use string for enum types
            return "string"
        else:
            # Use empty string for unknown types
            return ""

    @staticmethod
    def _resolve_allowed(field: FieldTypeWrapper) -> str:
        return field.get_allowed_enum_values()

    @staticmethod
    def _resolve_unit(field_args: dict, unit_lookup: dict[str, str]) -> str:
        unit = field_args.get("unit", "")
        if unit and isinstance(unit, GraphQLArgument):
            unit = unit.default_value
            return unit_lookup[unit]
        return ""

    @staticmethod
    def _resolve_name(
        field_name: str,
        field: FieldTypeWrapper,
        prefix: str = "",
    ) -> str:
        if field.is_branch_node():
            # Use the name as it is for branch nodes
            # E.g. "Vehicle_ADAS"
            return field.name

        elif field.is_leaf_node():
            # Use the field_name for leaf nodes
            # E.g. "steeringWheel"
            return f"{prefix}.{field_name}"

        raise ValueError(f"Unknown field type: {field}")

    @staticmethod
    def _resolve_range(
        field: GraphQLField,
    ) -> dict[str, int | float | None]:
        if has_directive(field, "range"):
            return get_directive_arguments(field, "range")
        return {}

    @staticmethod
    def _resolve_minimum(field: GraphQLField) -> int | float | None:
        return IDGenerationSpec._resolve_range(field).get("min")

    @staticmethod
    def _resolve_maximum(field: GraphQLField) -> int | float | None:
        return IDGenerationSpec._resolve_range(field).get("max")
