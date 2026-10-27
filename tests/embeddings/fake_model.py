"""Replaces model loading with ``FakeEmbedder`` for CLI and API tests."""

from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import NamedTuple

import pytest

from s2dm.tools.embeddings.model_spec import ModelSourceReference, ModelSpec
from s2dm.tools.embeddings.sources.source import ModelSource
from tests.embeddings.fake_embedder import FakeEmbedder


class ModelLoad(NamedTuple):
    """One ``load_model`` call made against the fake model."""

    reference: ModelSourceReference
    cache_root: Path
    full_size: bool


@dataclass(frozen=True)
class FakeLoadedModel:
    """Stands in for a ``LoadedModel``: only its spec is read before the fake ``OnnxEmbedder`` takes over."""

    spec: ModelSpec


@dataclass
class FakeModelCalls:
    """Every ``load_model`` call and ``OnnxEmbedder`` creation made against the fake model."""

    model_loads: list[ModelLoad] = field(default_factory=list)
    embedder_loads: list[ModelSpec] = field(default_factory=list)


def install_fake_model(monkeypatch: pytest.MonkeyPatch, modules: list[ModuleType]) -> FakeModelCalls:
    """Make ``load_model`` and ``OnnxEmbedder`` in each module serve ``FakeEmbedder`` without network."""
    calls = FakeModelCalls()

    def fake_load_model(source: ModelSource, full_size: bool) -> FakeLoadedModel:
        model_load = ModelLoad(reference=source.reference, cache_root=source.cache_root, full_size=full_size)
        calls.model_loads.append(model_load)
        return FakeLoadedModel(spec=FakeEmbedder.spec)

    def fake_onnx_embedder(model: FakeLoadedModel) -> FakeEmbedder:
        calls.embedder_loads.append(model.spec)
        return FakeEmbedder()

    for module in modules:
        monkeypatch.setattr(module, "load_model", fake_load_model)
        monkeypatch.setattr(module, "OnnxEmbedder", fake_onnx_embedder)
    return calls
