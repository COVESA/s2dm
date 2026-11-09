"""Structured schema-validation violations shared across the constraint checker and schema loader."""

from dataclasses import dataclass
from enum import StrEnum


class ConstraintCode(StrEnum):
    SCHEMA_SPEC = "schema.spec"
    ENUM_DEFAULT = "schema.enum_default"
    INSTANCE_TAG_INVALID_EXCLUDE = "instanceTag.invalid_exclude"
    INSTANCE_TAG_INVALID_REFERENCE = "instanceTag.invalid_reference"
    INSTANCE_TAG_MULTIPLE_FIELDS = "instanceTag.multiple_fields"
    INSTANCE_TAG_NON_ENUM_FIELD = "instanceTag.non_enum_field"
    INSTANCE_TAG_NOT_EXPANDED = "instanceTag.not_expanded"
    INSTANCE_TAG_SINGLE_DIMENSION = "instanceTag.single_dimension"
    INSTANCE_TAG_SOURCE_FIELD_TAGGED = "instanceTag.source_field_tagged"
    MIN_GREATER_THAN_MAX = "min_greater_than_max"
    INVALID_MIN_MAX = "invalid_min_max"
    NAMING_CONVENTION = "naming_convention"


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class ConstraintViolation:
    code: ConstraintCode
    message: str
    severity: Severity = Severity.ERROR

    def __str__(self) -> str:
        return self.message
