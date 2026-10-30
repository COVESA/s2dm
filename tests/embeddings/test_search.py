import numpy as np
import pytest

from s2dm.tools.embeddings.errors import EmbeddingsFileError
from s2dm.tools.embeddings.file import EmbeddingsFile
from s2dm.tools.embeddings.search import rank_elements
from tests.embeddings.fake_embedder import FakeEmbedder

IS_OPEN_TEXT = "vehicle cabin door is open (Boolean): Is the door open or closed."


def test_rank_orders_by_score(lean_embeddings: EmbeddingsFile) -> None:
    query_vector = FakeEmbedder().embed_query(IS_OPEN_TEXT)

    hits = rank_elements(lean_embeddings, query_vector, limit=3)

    assert [hit.rank for hit in hits] == [1, 2, 3]
    assert hits[0].id == "Vehicle_Cabin_Door.isOpen"
    scores = [hit.score for hit in hits]
    assert scores == sorted(scores, reverse=True)


def test_rank_verbose_file_hits_carry_details(verbose_embeddings: EmbeddingsFile) -> None:
    query_vector = FakeEmbedder().embed_query(IS_OPEN_TEXT)

    hits = rank_elements(verbose_embeddings, query_vector, limit=1)

    assert (hits[0].kind, hits[0].description) == ("field", "Is the door open or closed.")


def test_rank_rejects_query_vector_of_other_size(lean_embeddings: EmbeddingsFile) -> None:
    query_vector = np.ones(lean_embeddings.model.settings.dim + 1, dtype=np.float32)

    with pytest.raises(EmbeddingsFileError):
        rank_elements(lean_embeddings, query_vector, limit=3)
