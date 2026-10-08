from dataclasses import dataclass

import pytest

from app.retrieval.embeddings import EmbeddingProvider
from app.retrieval.openai_embeddings import (
    DEFAULT_EMBEDDING_MODEL,
    OpenAIEmbeddingProvider,
)


@dataclass(frozen=True)
class FakeEmbeddingItem:
    index: int
    embedding: list[float]


@dataclass(frozen=True)
class FakeEmbeddingResponse:
    data: list[FakeEmbeddingItem]


class FakeEmbeddingsResource:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs) -> FakeEmbeddingResponse:
        self.calls.append(kwargs)
        input_value = kwargs["input"]

        if isinstance(input_value, list):
            return FakeEmbeddingResponse(
                data=[
                    FakeEmbeddingItem(
                        index=index,
                        embedding=[float(len(text)), float(index)],
                    )
                    for index, text in enumerate(input_value)
                ]
            )

        return FakeEmbeddingResponse(
            data=[
                FakeEmbeddingItem(
                    index=0,
                    embedding=[float(len(input_value)), 1.0],
                )
            ]
        )


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.embeddings = FakeEmbeddingsResource()


class OutOfOrderEmbeddingsResource(FakeEmbeddingsResource):
    def create(self, **kwargs) -> FakeEmbeddingResponse:
        response = super().create(**kwargs)
        return FakeEmbeddingResponse(data=list(reversed(response.data)))


class OutOfOrderOpenAIClient:
    def __init__(self) -> None:
        self.embeddings = OutOfOrderEmbeddingsResource()


class MissingEmbeddingResource(FakeEmbeddingsResource):
    def create(self, **kwargs) -> FakeEmbeddingResponse:
        super().create(**kwargs)
        return FakeEmbeddingResponse(
            data=[FakeEmbeddingItem(index=0, embedding=[1.0, 0.0])]
        )


class MissingEmbeddingClient:
    def __init__(self) -> None:
        self.embeddings = MissingEmbeddingResource()


def test_openai_provider_satisfies_embedding_provider_protocol() -> None:
    provider = OpenAIEmbeddingProvider(FakeOpenAIClient())

    assert isinstance(provider, EmbeddingProvider)


def test_embed_documents_calls_openai_with_expected_contract() -> None:
    client = FakeOpenAIClient()
    provider = OpenAIEmbeddingProvider(client)

    embeddings = provider.embed_documents(("policy", "security"))

    assert embeddings == ((6.0, 0.0), (8.0, 1.0))
    assert client.embeddings.calls == [
        {
            "input": ["policy", "security"],
            "model": DEFAULT_EMBEDDING_MODEL,
            "encoding_format": "float",
        }
    ]


def test_embed_documents_restores_response_order_using_openai_index() -> None:
    provider = OpenAIEmbeddingProvider(OutOfOrderOpenAIClient())

    embeddings = provider.embed_documents(("a", "abcd", "xy"))

    assert embeddings == (
        (1.0, 0.0),
        (4.0, 1.0),
        (2.0, 2.0),
    )


def test_embed_documents_returns_empty_tuple_without_api_call() -> None:
    client = FakeOpenAIClient()
    provider = OpenAIEmbeddingProvider(client)

    assert provider.embed_documents(()) == ()
    assert client.embeddings.calls == []


def test_embed_query_calls_openai_with_single_text() -> None:
    client = FakeOpenAIClient()
    provider = OpenAIEmbeddingProvider(client)

    embedding = provider.embed_query("governance")

    assert embedding == (10.0, 1.0)
    assert client.embeddings.calls == [
        {
            "input": "governance",
            "model": DEFAULT_EMBEDDING_MODEL,
            "encoding_format": "float",
        }
    ]


def test_provider_supports_explicit_model_configuration() -> None:
    client = FakeOpenAIClient()
    provider = OpenAIEmbeddingProvider(
        client,
        model="text-embedding-3-large",
    )

    provider.embed_query("governance")

    assert client.embeddings.calls[0]["model"] == "text-embedding-3-large"


@pytest.mark.parametrize("text", ["", " ", "\n\t"])
def test_embed_query_rejects_empty_text(text: str) -> None:
    provider = OpenAIEmbeddingProvider(FakeOpenAIClient())

    with pytest.raises(ValueError, match="query text"):
        provider.embed_query(text)


def test_embed_documents_rejects_empty_document_text() -> None:
    provider = OpenAIEmbeddingProvider(FakeOpenAIClient())

    with pytest.raises(ValueError, match="document texts"):
        provider.embed_documents(("valid", " "))


def test_provider_rejects_empty_model_name() -> None:
    with pytest.raises(ValueError, match="model"):
        OpenAIEmbeddingProvider(FakeOpenAIClient(), model=" ")


def test_embed_documents_rejects_incomplete_openai_response() -> None:
    provider = OpenAIEmbeddingProvider(MissingEmbeddingClient())

    with pytest.raises(ValueError, match="different number"):
        provider.embed_documents(("first", "second"))
