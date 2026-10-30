"""The embedding model as stored in the embeddings file: its source and settings, without any model runtime."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

TokenPooling = Literal["cls", "mean"]
Pooling = Literal["sentence_embedding"] | TokenPooling


class ModelSourceReference(BaseModel):
    """Where a model comes from, as stored in the embeddings file.

    ``kind`` names the source. The other fields belong to that source and are read by the source whose
    ``matches`` accepts the reference.
    """

    model_config = ConfigDict(extra="allow")

    kind: str


class ModelSettings(BaseModel):
    """Everything needed to embed text with a model, as read from its files."""

    onnx_file: str
    pooling: Pooling
    query_prompt: str
    document_prompt: str
    dim: int


class ModelSpec(BaseModel):
    """A model's source and settings, as stored in the embeddings file."""

    source: ModelSourceReference
    settings: ModelSettings
