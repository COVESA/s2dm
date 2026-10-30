import pytest
from graphql import GraphQLSchema

from s2dm.tools.embeddings.file import EmbeddingsFile, build_embeddings_file
from tests.embeddings.fake_embedder import FakeEmbedder


@pytest.fixture(scope="session")
def lean_embeddings(embeddings_schema: GraphQLSchema) -> EmbeddingsFile:
    return build_embeddings_file(embeddings_schema, FakeEmbedder(), verbose=False)


@pytest.fixture(scope="session")
def verbose_embeddings(embeddings_schema: GraphQLSchema) -> EmbeddingsFile:
    return build_embeddings_file(embeddings_schema, FakeEmbedder(), verbose=True)
