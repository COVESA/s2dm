"""Read a model's sentence-transformers config files, reporting every problem as a ``ModelResolutionError``."""

from pathlib import Path

from pydantic import ValidationError

from s2dm.tools.embeddings.errors import ModelResolutionError
from s2dm.utils.pydantic_file import PydanticModel, read_json_model


def read_config_file(path: Path, config_model: type[PydanticModel]) -> PydanticModel | None:
    """Read and validate one of the model's JSON config files.

    Args:
        path: The config file.
        config_model: The pydantic model describing the file's contents.

    Returns:
        The validated contents, or ``None`` when the model does not publish the file.

    Raises:
        ModelResolutionError: When the file exists but cannot be read or does not match ``config_model``.
    """
    try:
        return read_json_model(path, config_model)
    except FileNotFoundError:
        return None
    except (OSError, ValidationError) as error:
        raise ModelResolutionError(f"Cannot read {path.name}: {error}") from error
