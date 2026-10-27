from pathlib import Path

import pytest

from s2dm.tools.embeddings.errors import ModelResolutionError
from s2dm.tools.embeddings.model_spec import ModelSourceReference
from s2dm.tools.embeddings.sources.factory import ModelSourceFactory
from s2dm.tools.embeddings.sources.huggingface_source import HUGGING_FACE_KIND, HuggingFaceSource


def test_create_source_picks_the_matching_source(tmp_path: Path) -> None:
    reference = ModelSourceReference.model_validate(
        {"kind": HUGGING_FACE_KIND, "repo": "org/model", "revision": "abc123"}
    )

    source = ModelSourceFactory.create_source(reference, tmp_path)

    assert isinstance(source, HuggingFaceSource)
    assert source.reference == reference
    assert source.cache_root == tmp_path


def test_create_source_rejects_unknown_kind(tmp_path: Path) -> None:
    reference = ModelSourceReference(kind="unknown")

    with pytest.raises(ModelResolutionError):
        ModelSourceFactory.create_source(reference, tmp_path)


def test_register_rejects_duplicate_source() -> None:
    with pytest.raises(ValueError):
        ModelSourceFactory.register(HuggingFaceSource)
