from dataclasses import dataclass
from typing import Any

from graphql import (
    GraphQLArgument,
    GraphQLEnumType,
    GraphQLField,
    GraphQLList,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLType,
)

from s2dm import log
from s2dm.exporters.utils.directive import get_directive_arguments, has_given_directive


class FieldTypeWrapper:
    """Wrapper for GraphQL field types to provide consistent interface.

    Args:
        field_type: The GraphQL type to wrap
    """

    def __init__(self, field_type: GraphQLType) -> None:
        self._field_type = field_type

    @property
    def name(self) -> str:
        """Get the name of the GraphQL type.

        Returns:
            The name of the type

        Raises:
            AttributeError: If the type does not have a name attribute
        """
        if not hasattr(self._field_type, "name"):
            raise AttributeError(f"GraphQL type {type(self._field_type).__name__} has no 'name' attribute")
        # Cast to str to satisfy mypy since we've verified the attribute exists
        return str(self._field_type.name)

    @property
    def internal_type(self) -> "FieldTypeWrapper":
        """Get the internal type by unwrapping list and non-null wrappers.

        Returns:
            A FieldTypeWrapper containing the internal type
        """
        internal_type = self._field_type
        if self.is_list_type():
            # Unwrap non-null and list types
            while hasattr(internal_type, "of_type"):
                internal_type = internal_type.of_type
        return FieldTypeWrapper(internal_type)

    def get_allowed_enum_values(self) -> str:
        """Get allowed enum values as a string.

        Returns:
            String representation of sorted enum values, or empty string if not an enum
        """
        if not self.is_enum_type() or not hasattr(self._field_type, "values"):
            return ""

        return str(sorted(list(self._field_type.values.keys())))

    def is_enum_type(self) -> bool:
        """Check if this is an enum type.

        Returns:
            True if this is a GraphQL enum type
        """
        return isinstance(self._field_type, GraphQLEnumType)

    def is_scalar_type(self) -> bool:
        """Check if this is a scalar type.

        Returns:
            True if this is a GraphQL scalar type
        """
        return isinstance(self._field_type, GraphQLScalarType)

    def is_list_type(self) -> bool:
        """Check if this is a list type.

        Returns:
            True if this is a GraphQL list type
        """
        return isinstance(self._field_type, GraphQLList)

    def is_object_type(self) -> bool:
        """Check if this is an object type.

        Returns:
            True if this is a GraphQL object type
        """
        return isinstance(self._field_type, GraphQLObjectType)


@dataclass(frozen=True)
class IDGenerationSpec:
    """Collection of fields and methods required for ID generation.

    Args:
        name: fully qualified name of the field
        data_type: datatype of the field: string, int, float, boolean, uint8 etc.
        unit: unit of the field if exists
        allowed: the enum for allowed values
        minimum: min value for the data if exists
        maximum: max value for the data if exists
        _field_type: the field type
    """

    name: str
    data_type: str
    unit: str = ""
    allowed: str = ""
    minimum: int | float | None = None
    maximum: int | float | None = None

    # Internal fields
    _field_type: FieldTypeWrapper | None = None

    def __eq__(self, other: object) -> bool:
        """Check equality with another IDGenerationSpec.

        Args:
            other: The object to compare with

        Returns:
            True if objects are equal, False otherwise
        """
        if not isinstance(other, IDGenerationSpec):
            return NotImplemented
        return (
            self.name == other.name
            and self.data_type == other.data_type
            and self.unit == other.unit
            and self.allowed == other.allowed
            and self.minimum == other.minimum
            and self.maximum == other.maximum
        )

    def __hash__(self) -> int:
        """Generate hash for the IDGenerationSpec.

        Returns:
            Hash value for this instance
        """
        return hash(f"{self.name}:{self.data_type}:{self.unit}:{self.allowed}:{self.minimum}:{self.maximum}")

    def is_object_type(self) -> bool:
        """Check if this field is an object type.

        Returns:
            True if this field is an object type

        Raises:
            AttributeError: If _field_type is None
        """
        if self._field_type is None:
            raise AttributeError("_field_type is None")
        return self._field_type.internal_type.is_object_type()

    def is_leaf_field(self) -> bool:
        """Check if this field is a leaf field.

        Returns:
            True if this field is a leaf field
        """
        return not self.is_object_type()

    def get_node_identifier_bytes(
        self,
        strict_mode: bool,
    ) -> bytes:
        """Get a node identifier as bytes. Used as an input for hashing.

        Args:
            strict_mode: strict mode means case sensitivity of node qualified names

        Returns:
            a bytes representation of the node
        """

        node_identifier: bytes = (
            f"{self.name}: "
            f"unit: {self.unit}, "
            f"datatype: {self.data_type}, "
            f"allowed: {self.allowed}"
            f"min: {self.minimum if self.minimum is not None else ''}"
            f"max: {self.maximum if self.maximum is not None else ''}"
        ).encode()

        log.debug(f"{node_identifier=}")

        if strict_mode:
            return node_identifier
        else:
            return node_identifier.lower()

    @classmethod
    def from_enum(
        cls,
        *,
        field: GraphQLEnumType,
    ) -> "IDGenerationSpec":
        """Create an IDGenerationSpec from a GraphQL enum type.

        Args:
            field: The GraphQL enum type

        Returns:
            An IDGenerationSpec for the enum

        Raises:
            ValueError: If field is not a GraphQLEnumType
        """
        if not isinstance(field, GraphQLEnumType):
            raise ValueError(f"Field is not a GraphQLEnumType: {field}")

        _field_type = FieldTypeWrapper(field)
        allowed = IDGenerationSpec._resolve_allowed(_field_type)

        return cls(
            name=field.name,
            data_type="string",
            allowed=allowed,
            _field_type=_field_type,
        )

    @classmethod
    def from_field(
        cls,
        *,
        parent_name: str,
        field_name: str,
        field: GraphQLField,
    ) -> "IDGenerationSpec":
        """Create an IDGenerationSpec from a GraphQL field.

        Args:
            parent_name: Parent name of the field
            field_name: the name of the field
            field: the GraphQL field to extract the ID generation spec from
            unit_lookup: Dictionary mapping unit names to unit values

        Returns:
            an IDGenerationSpec

        Raises:
            ValueError: If field is not a GraphQLField
        """

        if not isinstance(field, GraphQLField):
            raise ValueError(f"Field is not a GraphQLField: {field}")

        original_field_type = field.type
        original_field_type_wrapped = FieldTypeWrapper(original_field_type)

        inside_field_type_wrapped = original_field_type_wrapped.internal_type

        # Name is resolved from the field's name, type and prefix
        name = IDGenerationSpec._resolve_name(parent_name, field_name)

        # Data type is resolved from the field's type (lower case name)
        data_type = IDGenerationSpec._resolve_data_type(original_field_type_wrapped)

        # Allowed values are resolved from the field's type (string of allowed values for enums)
        allowed = IDGenerationSpec._resolve_allowed(inside_field_type_wrapped)

        # Unit is resolved from the field's "unit" argument (enum default value)
        field_args = field.args or {}
        unit = IDGenerationSpec._resolve_unit(field_args)

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
            _field_type=original_field_type_wrapped,
        )

    @staticmethod
    def _resolve_data_type(original_field_type: FieldTypeWrapper) -> str:
        """Resolve the data type from original and inside field types.

        If the original field type is a list, wrap the inside field type with "list[]"

        Args:
            original_field_type: the original field type

        Returns:
            the data type
        """

        internal_field_type = original_field_type.internal_type
        field_type_name = ""
        if internal_field_type.is_scalar_type():
            # Use lowercase name for scalar types
            field_type_name = internal_field_type.name.lower()
        elif internal_field_type.is_enum_type():
            # Use string for enum types
            field_type_name = "string"

        surrounding_type = original_field_type
        while surrounding_type.is_list_type():
            field_type_name = f"{field_type_name}[]"
            if hasattr(surrounding_type._field_type, "of_type"):
                surrounding_type = FieldTypeWrapper(surrounding_type._field_type.of_type)
            else:
                break

        return field_type_name

    @staticmethod
    def _resolve_allowed(field: FieldTypeWrapper) -> str:
        """Resolve allowed enum values from a field type.

        Args:
            field: The field type wrapper

        Returns:
            String representation of allowed values
        """
        return field.get_allowed_enum_values()

    @staticmethod
    def _resolve_unit(field_args: dict[str, GraphQLArgument]) -> str:
        """Resolve unit from field arguments.

        Args:
            field_args: Dictionary of field arguments

        Returns:
            The resolved unit symbol string (enum default) or empty string

        Raises:
            None
        """
        unit = field_args.get("unit", "")
        if unit and isinstance(unit, GraphQLArgument):
            unit = unit.default_value
            return str(unit)
        return ""

    @staticmethod
    def _resolve_name(
        parent_name: str,
        field_name: str,
    ) -> str:
        """Resolve the fully qualified name from parent and field names.

        Args:
            parent_name: The parent type name
            field_name: The field name

        Returns:
            The fully qualified name
        """
        return f"{parent_name}.{field_name}"

    @staticmethod
    def _resolve_range(
        field: GraphQLField,
    ) -> dict[str, Any]:
        """Resolve range directive from a GraphQL field.

        Args:
            field: The GraphQL field

        Returns:
            Dictionary with range values or empty dict if no range directive
        """
        if has_given_directive(field, "range"):
            return get_directive_arguments(field, "range")
        return {}

    @staticmethod
    def _resolve_minimum(field: GraphQLField) -> int | float | None:
        """Resolve minimum value from range directive.

        Args:
            field: The GraphQL field

        Returns:
            The minimum value or None if not specified
        """
        return IDGenerationSpec._resolve_range(field).get("min")

    @staticmethod
    def _resolve_maximum(field: GraphQLField) -> int | float | None:
        """Resolve maximum value from range directive.

        Args:
            field: The GraphQL field

        Returns:
            The maximum value or None if not specified
        """
        return IDGenerationSpec._resolve_range(field).get("max")
