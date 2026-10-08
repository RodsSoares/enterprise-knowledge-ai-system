from pathlib import Path

import pytest

from app.chunking.schemas import RetrievalChunk
from app.retrieval.embeddings import Embedding
from app.retrieval.vector_index import NumPyVectorIndex
from app.retrieval.vector_retriever import VectorRetriever


class FakeEmbeddingProvider:
    def __init__(self) -> None:
        self.last_query: str | None = None

    def embed_documents(self, texts: tuple[str, ...]) -> tuple[Embedding, ...]:
        return tuple((1.0, 0.0) for _ in texts)

    def embed_query(self, text: str) -> Embedding:
        self.last_query = text
        return (1.0, 0.0)


def _chunk(chunk_id: str, order: int) -> RetrievalChunk:
    return RetrievalChunk(
        chunk_id=chunk_id,
        order=order,
        text=f"Evidence for {chunk_id}.",
        source_block_ids=(f"block-{order}",),
        source_path=Path("data/source/policy.pdf"),
        section_path=("Governance",),
        page_numbers=(order + 1,),
        content_types=("text",),
    )


def test_vector_retriever_returns_canonical_retrieval_candidates() -> None:
    chunks = (
        _chunk("chunk-a", 0),
        _chunk("chunk-b", 1),
        _chunk("chunk-c", 2),
    )
    index = NumPyVectorIndex()
    index.add(
        chunk_ids=("chunk-a", "chunk-b", "chunk-c"),
        embeddings=((1.0, 0.0), (0.8, 0.2), (0.0, 1.0)),
    )
    provider = FakeEmbeddingProvider()
    retriever = VectorRetriever(provider, index, chunks)

    candidates = retriever.retrieve("security assessment", top_k=2)

    assert provider.last_query == "security assessment"
    assert tuple(candidate.chunk.chunk_id for candidate in candidates) == (
        "chunk-a",
        "chunk-b",
    )
    assert tuple(candidate.retrieval_method for candidate in candidates) == (
        "vector",
        "vector",
    )
    assert tuple(candidate.rank for candidate in candidates) == (1, 2)
    assert candidates[0].score == pytest.approx(1.0)


def test_vector_retriever_returns_original_canonical_chunk_objects() -> None:
    chunks = (_chunk("chunk-a", 0),)
    index = NumPyVectorIndex()
    index.add(
        chunk_ids=("chunk-a",),
        embeddings=((1.0, 0.0),),
    )

    retriever = VectorRetriever(FakeEmbeddingProvider(), index, chunks)
    candidate = retriever.retrieve("governance", top_k=1)[0]

    assert candidate.chunk is chunks[0]


@pytest.mark.parametrize("query", ["", " ", "\n\t"])
def test_vector_retriever_rejects_empty_query(query: str) -> None:
    chunks = (_chunk("chunk-a", 0),)
    index = NumPyVectorIndex()
    index.add(
        chunk_ids=("chunk-a",),
        embeddings=((1.0, 0.0),),
    )
    retriever = VectorRetriever(FakeEmbeddingProvider(), index, chunks)

    with pytest.raises(ValueError, match="query"):
        retriever.retrieve(query)


def test_vector_retriever_rejects_empty_chunk_collection() -> None:
    with pytest.raises(ValueError, match="chunks"):
        VectorRetriever(
            FakeEmbeddingProvider(),
            NumPyVectorIndex(),
            (),
        )


def test_vector_retriever_rejects_duplicate_chunk_ids() -> None:
    chunks = (_chunk("chunk-a", 0), _chunk("chunk-a", 1))

    with pytest.raises(ValueError, match="duplicate"):
        VectorRetriever(
            FakeEmbeddingProvider(),
            NumPyVectorIndex(),
            chunks,
        )


def test_vector_retriever_rejects_unknown_chunk_id_from_index() -> None:
    chunks = (_chunk("chunk-a", 0),)
    index = NumPyVectorIndex()
    index.add(
        chunk_ids=("chunk-unknown",),
        embeddings=((1.0, 0.0),),
    )
    retriever = VectorRetriever(FakeEmbeddingProvider(), index, chunks)

    with pytest.raises(ValueError, match="unknown chunk_id"):
        retriever.retrieve("governance", top_k=1)
