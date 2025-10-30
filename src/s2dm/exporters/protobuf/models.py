"""Pydantic models for Protobuf schema structures."""

from pydantic import BaseModel, Field, field_validator


class ProtoEnumValue(BaseModel):
    """Represents a value in a Protocol Buffers enum."""

    name: str
    number: int = Field(ge=1)
    description: str | None = None


class ProtoEnum(BaseModel):
    """Represents a Protocol Buffers enum type."""

    name: str
    enum_values: list[ProtoEnumValue]
    description: str | None = None
    source: str | None = None

    @field_validator("enum_values")
    @classmethod
    def validate_unique_numbers(cls, enum_values: list[ProtoEnumValue]) -> list[ProtoEnumValue]:
        numbers = [v.number for v in enum_values]
        if len(numbers) != len(set(numbers)):
            raise ValueError("Enum values must have unique numbers")
        return enum_values


class ProtoField(BaseModel):
    """Represents a field in a Protocol Buffers message."""

    name: str
    type: str
    number: int = Field(ge=1)
    description: str | None = None
    validation_rules: str | None = None


class ProtoMessage(BaseModel):
    """Represents a Protocol Buffers message type."""

    name: str
    fields: list[ProtoField]
    description: str | None = None
    source: str | None = None
    nested_messages: list["ProtoMessage"] = Field(default_factory=list)

    @field_validator("fields")
    @classmethod
    def validate_unique_field_numbers(cls, fields: list[ProtoField]) -> list[ProtoField]:
        numbers = [f.number for f in fields]
        if len(numbers) != len(set(numbers)):
            raise ValueError("Fields must have unique numbers")
        return fields


class ProtoUnion(BaseModel):
    """Represents a Protocol Buffers union (oneof)."""

    name: str
    members: list[ProtoField]
    description: str | None = None
    source: str | None = None


class ProtoSchema(BaseModel):
    """Represents a complete Protocol Buffers schema."""

    syntax: str = "proto3"
    package: str | None = None
    enums: list[ProtoEnum] = Field(default_factory=list)
    messages: list[ProtoMessage] = Field(default_factory=list)
    unions: list[ProtoUnion] = Field(default_factory=list)
    flatten_mode: bool = False
    flattened_fields: list[ProtoField] = Field(default_factory=list)
