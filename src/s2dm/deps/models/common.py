from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Annotated, Any, cast

import yaml
from pydantic import AfterValidator


def validate_required_string(value: str) -> str:
    """Reject empty strings and hidden surrounding whitespace."""
    if not value:
        raise ValueError("Field value cannot be empty")
    if value != value.strip():
        raise ValueError("Field value must not contain leading or trailing whitespace")
    return value


RequiredString = Annotated[str, AfterValidator(validate_required_string)]


def validate_absolute_path(path: Path, value_label: str) -> Path:
    """Require a path value to be absolute."""
    if not path.is_absolute():
        raise ValueError(f"{value_label} must be an absolute path")
    return path


def create_absolute_path_validator(value_label: str) -> AfterValidator:
    """Create a pydantic validator for absolute paths with a contextual label."""
    validator: Callable[[Path], Path] = partial(validate_absolute_path, value_label=value_label)
    return AfterValidator(validator)


def load_yaml_mapping(path: Path, root_label: str) -> dict[str, Any]:
    """Load a YAML file whose root value must be a mapping."""
    raw: Any
    with path.open("r", encoding="utf-8") as file_handle:
        raw = yaml.safe_load(file_handle)

    if not isinstance(raw, dict):
        raise TypeError(f"{root_label} must be a valid mapping (YAML object), got {type(raw).__name__}")

    return cast(dict[str, Any], raw)
