"""The prompts a sentence-transformers model expects before queries and documents."""

from pathlib import Path

from pydantic import BaseModel

from s2dm.tools.embeddings.sentence_transformers.files import read_config_file

PROMPTS_FILE = "config_sentence_transformers.json"


class PromptsConfig(BaseModel):
    """Contents of ``config_sentence_transformers.json``."""

    prompts: dict[str, str] = {}

    @property
    def query_prompt(self) -> str:
        """The prefix for queries; empty when the model sets none."""
        return self.prompts.get("query", "")

    @property
    def document_prompt(self) -> str:
        """The prefix for documents; empty when the model sets none."""
        return self.prompts.get("document", "")


def read_prompts(directory: Path) -> PromptsConfig:
    """Read the prefixes the model expects before queries and documents.

    Args:
        directory: Folder holding the model's files.

    Returns:
        The model's prompts; both are empty when the model publishes no prompts file.

    Raises:
        ModelResolutionError: When the prompts file exists but cannot be read or is malformed.
    """
    prompts_config = read_config_file(directory / PROMPTS_FILE, PromptsConfig)
    if prompts_config is None:
        return PromptsConfig()

    return prompts_config
