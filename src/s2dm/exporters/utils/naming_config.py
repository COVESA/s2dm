from enum import Enum
from pathlib import Path
from typing import Any, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator

from s2dm import log


class CaseFormat(str, Enum):
    CAMEL_CASE = "camelCase"
    PASCAL_CASE = "PascalCase"
    SNAKE_CASE = "snake_case"
    KEBAB_CASE = "kebab-case"
    MACRO_CASE = "MACROCASE"
    COBOL_CASE = "COBOL-CASE"
    FLAT_CASE = "flatcase"
    TITLE_CASE = "TitleCase"


class ValidationMode(str, Enum):
    CONVERSION = "conversion"
    CHECK = "check"


class ElementType(str, Enum):
    TYPE = "type"
    FIELD = "field"
    ARGUMENT = "argument"
    ENUM_VALUE = "enumValue"
    INSTANCE_TAG = "instanceTag"


class ContextType(str, Enum):
    OBJECT = "object"
    INTERFACE = "interface"
    INPUT = "input"
    SCALAR = "scalar"
    UNION = "union"
    ENUM = "enum"
    FIELD = "field"


class TypeNamingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    object: CaseFormat | None = None
    interface: CaseFormat | None = None
    input: CaseFormat | None = None
    scalar: CaseFormat | None = None
    union: CaseFormat | None = None
    enum: CaseFormat | None = None


class FieldNamingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    object: CaseFormat | None = None
    interface: CaseFormat | None = None
    input: CaseFormat | None = None


class ArgumentNamingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: CaseFormat | None = None


class NamingConventionConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    type: TypeNamingConfig | None = None
    field: FieldNamingConfig | None = None
    argument: ArgumentNamingConfig | None = None
    enum_value: CaseFormat | None = Field(None, alias="enumValue")
    instance_tag: CaseFormat | None = Field(None, alias="instanceTag")
    exceptions: dict[str, str] | None = None

    @model_validator(mode="after")
    def validate_enum_value_requires_instance_tag(self, info: ValidationInfo) -> "NamingConventionConfig":
        mode = info.context.get("mode", ValidationMode.CONVERSION) if info.context else ValidationMode.CONVERSION
        if mode == ValidationMode.CONVERSION and self.enum_value is not None and self.instance_tag is None:
            raise ValueError("If 'enumValue' is present, 'instanceTag' must also be present")
        return self


ELEMENT_TYPE_TO_ATTRIBUTE = {
    ElementType.ENUM_VALUE: "enum_value",
    ElementType.INSTANCE_TAG: "instance_tag",
}


def get_case_for_element(
    element_type: ElementType,
    context: ContextType | None,
    config: NamingConventionConfig,
) -> CaseFormat | None:
    """Get the expected case format for an element type and context.

    Args:
        element_type: The element type
        context: The context (object, interface, input, etc.)
        config: The naming convention configuration

    Returns:
        The expected case format or None if not configured
    """
    config_attribute = ELEMENT_TYPE_TO_ATTRIBUTE.get(element_type, element_type)
    config_section = getattr(config, config_attribute, None)

    if config_section is None:
        return None

    if isinstance(config_section, CaseFormat):
        return config_section

    if context:
        return getattr(config_section, context.value, None)

    return None


def load_naming_convention_config(
    config_path: Path | None,
    mode: ValidationMode = ValidationMode.CONVERSION,
) -> NamingConventionConfig | None:
    """
    Load and validate a naming convention configuration from a YAML file.

    Args:
        config_path: Path to the YAML configuration file, or None to skip loading.
        mode: Validation mode used during validation.

    Returns:
        A validated NamingConventionConfig, or None if config_path is None.

    Raises:
        OSError: If the file cannot be read.
        yaml.YAMLError: If the file is not valid YAML.
        TypeError: If the YAML root is not a mapping.
        ValidationError: If validation against NamingConventionConfig fails.
    """
    if config_path is None:
        log.debug("No naming config provided")
        return None

    raw: Any
    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    log.debug("Loaded naming config from %s", config_path)

    # Treat empty file or explicit YAML null as "defaults"
    if raw is None or raw == {}:
        return NamingConventionConfig.model_validate({}, context={"mode": mode})

    if not isinstance(raw, dict):
        raise TypeError(f"Naming config root must be a mapping (YAML object), got {type(raw).__name__}")

    raw_dict = cast(dict[str, Any], raw)
    return NamingConventionConfig.model_validate(raw_dict, context={"mode": mode})
