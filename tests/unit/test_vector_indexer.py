from pathlib import Path

import pytest

from app.chunking.schemas import RetrievalChunk
from app.retrieval.embeddings import Embedding
from app.retrieval.vector_index import NumPyVectorIndex
from app.retrieval.vector_indexer import VectorIndexer


class RecordingEmbeddingProvider:
    def __init__(self) -> None:
        self.document_inputs: tuple[str, ...] | None = None

    def embed_documents(self, texts: tuple[str, ...]) -> tuple[Embedding, ...]:
        self.document_inputs = texts
        return tuple(
            (1.0, 0.0) if "Security" in text else (0.0, 1.0)
            for text in texts
        )

    def embed_query(self, text: str) -> Embedding:
        return (1.0, 0.0)


class BrokenEmbeddingProvider(RecordingEmbeddingProvider):
    def embed_documents(self, texts: tuple[str, ...]) -> tuple[Embedding, ...]:
        return ((1.0, 0.0),)


def _chunk(
    chunk_id: str,
    text: str,
    section_path: tuple[str, ...],
    order: int,
) -> RetrievalChunk:
    return RetrievalChunk(
        chunk_id=chunk_id,
        order=order,
        text=text,
        source_block_ids=(f"block-{order}",),
        source_path=Path("data/source/policy.pdf"),
        section_path=section_path,
        page_numbers=(order + 1,),
        content_types=("text",),
    )


def test_vector_indexer_builds_search_text_and_indexes_embeddings() -> None:
    chunks = (
        _chunk(
            "chunk-security",
            "External vendors require assessment.",
            ("Governance", "Security"),
            0,
        ),
        _chunk(
            "chunk-finance",
            "Invoices require approval.",
            ("Finance",),
            1,
        ),
    )
    provider = RecordingEmbeddingProvider()
    index = NumPyVectorIndex()
    indexer = VectorIndexer(provider, index)

    indexer.index(chunks)

    assert provider.document_inputs == (
        "Section: Governance > Security\n\nExternal vendors require assessment.",
        "Section: Finance\n\nInvoices require approval.",
    )

    hits = index.search((1.0, 0.0), top_k=2)
    assert hits[0].chunk_id == "chunk-security"


def test_vector_indexer_rejects_empty_chunk_collection() -> None:
    indexer = VectorIndexer(
        RecordingEmbeddingProvider(),
        NumPyVectorIndex(),
    )

    with pytest.raises(ValueError, match="chunks"):
        indexer.index(())


def test_vector_indexer_rejects_embedding_count_mismatch() -> None:
    chunks = (
        _chunk("chunk-a", "A", ("Security",), 0),
        _chunk("chunk-b", "B", ("Finance",), 1),
    )
    indexer = VectorIndexer(
        BrokenEmbeddingProvider(),
        NumPyVectorIndex(),
    )

    with pytest.raises(ValueError, match="one embedding"):
        indexer.index(chunks)
