from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

PydanticModel = TypeVar("PydanticModel", bound=BaseModel)

# TODO: add a read_yaml_model helper (yaml.safe_load, then model_validate) and switch
#   s2dm.deps.models.lock_file to it, which reads its YAML lock file into a model the same way.


def read_json_model(path: Path, model_type: type[PydanticModel]) -> PydanticModel:
    """Read a JSON file and validate its contents into a pydantic model.

    Args:
        path: The JSON file.
        model_type: The pydantic model describing the file's contents.

    Returns:
        The validated contents.

    Raises:
        OSError: When the file cannot be read.
        ValidationError: When the file is not valid JSON or does not match ``model_type``.
    """
    text = path.read_text()
    return model_type.model_validate_json(text)
