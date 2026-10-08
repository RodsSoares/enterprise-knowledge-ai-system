from app.retrieval.embeddings import Embedding, EmbeddingProvider


class FakeEmbeddingProvider:
    """Small deterministic provider used only to verify the contract."""

    def embed_documents(self, texts: tuple[str, ...]) -> tuple[Embedding, ...]:
        return tuple((float(len(text)), 1.0) for text in texts)

    def embed_query(self, text: str) -> Embedding:
        return (float(len(text)), 1.0)


def test_fake_provider_satisfies_embedding_provider_protocol() -> None:
    provider = FakeEmbeddingProvider()

    assert isinstance(provider, EmbeddingProvider)


def test_embedding_provider_preserves_document_order() -> None:
    provider: EmbeddingProvider = FakeEmbeddingProvider()

    embeddings = provider.embed_documents(("a", "abcd", "xy"))

    assert embeddings == (
        (1.0, 1.0),
        (4.0, 1.0),
        (2.0, 1.0),
    )


def test_embedding_provider_returns_single_query_embedding() -> None:
    provider: EmbeddingProvider = FakeEmbeddingProvider()

    embedding = provider.embed_query("query")

    assert embedding == (5.0, 1.0)
