"""The pooling module of a sentence-transformers model: listed in ``modules.json``, set up by its ``config.json``."""

from pathlib import Path, PurePosixPath

from pydantic import BaseModel, RootModel

from s2dm.tools.embeddings.errors import ModelResolutionError
from s2dm.tools.embeddings.model_spec import TokenPooling
from s2dm.tools.embeddings.sentence_transformers.files import read_config_file

MODULES_FILE = "modules.json"
MODULE_CONFIG_FILE = "config.json"
POOLING_MODULE_TYPE = "sentence_transformers.models.Pooling"


class _ModuleEntry(BaseModel):
    """One module of a sentence-transformers model, as listed in ``modules.json``."""

    path: str
    type: str


class _ModuleList(RootModel[list[_ModuleEntry]]):
    """Contents of ``modules.json``."""

    def pooling_config_file(self) -> str | None:
        """Find the config file of the first pooling module in the list.

        Returns:
            The model-relative path of the pooling module's ``config.json``, or ``None`` when no pooling module
            is listed.
        """
        pooling_modules = [module for module in self.root if module.type == POOLING_MODULE_TYPE]
        if not pooling_modules:
            return None

        pooling_config_path = PurePosixPath(pooling_modules[0].path) / MODULE_CONFIG_FILE
        return str(pooling_config_path)


class _PoolingConfig(BaseModel):
    """Contents of the pooling module's ``config.json``."""

    pooling_mode_cls_token: bool = False
    pooling_mode_mean_tokens: bool = False

    def mode(self) -> TokenPooling | None:
        """Tell how the config turns token outputs into one vector.

        Returns:
            ``"cls"`` or ``"mean"``, or ``None`` when the config enables neither.
        """
        if self.pooling_mode_cls_token:
            return "cls"
        if self.pooling_mode_mean_tokens:
            return "mean"

        return None


def find_pooling_config_file(directory: Path) -> str | None:
    """Find the pooling module's config file through the module list in ``modules.json``.

    Args:
        directory: Folder holding the model's files.

    Returns:
        The model-relative path of the pooling module's ``config.json``, or ``None`` when the model has no
        ``modules.json`` or lists no pooling module.

    Raises:
        ModelResolutionError: When ``modules.json`` cannot be read or is not a list of modules.
    """
    module_list = read_config_file(directory / MODULES_FILE, _ModuleList)
    if module_list is None:
        return None

    return module_list.pooling_config_file()


def read_pooling(directory: Path) -> TokenPooling:
    """Read how the pooling module turns token outputs into one vector.

    Args:
        directory: Folder holding the model's files.

    Returns:
        ``"cls"`` or ``"mean"``, as the pooling module's config enables.

    Raises:
        ModelResolutionError: When the model lists no pooling module, its config is missing or cannot be read, or
            the config enables neither CLS nor mean pooling.
    """
    pooling_config_file = find_pooling_config_file(directory)
    if pooling_config_file is None:
        raise ModelResolutionError("Model lists no pooling module")

    pooling_config = read_config_file(directory / pooling_config_file, _PoolingConfig)
    if pooling_config is None:
        raise ModelResolutionError(f"Pooling config {pooling_config_file} is missing")

    pooling_mode = pooling_config.mode()
    if pooling_mode is None:
        raise ModelResolutionError("Pooling config enables neither CLS nor mean pooling")

    return pooling_mode
