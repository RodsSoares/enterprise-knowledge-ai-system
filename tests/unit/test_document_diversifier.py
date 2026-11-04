"""Tests for deterministic document-aware candidate selection."""

from pathlib import Path

import pytest

from app.chunking.schemas import RetrievalChunk
from app.retrieval.candidate_fusion import FusedCandidate
from app.retrieval.document_diversifier import DocumentDiversifier


def candidate(doc: str, suffix: str, rank: int) -> FusedCandidate:
    chunk = RetrievalChunk(
        chunk_id=f"{doc}::{suffix}", document_id=doc, order=rank,
        text=f"Evidence {suffix}", source_block_ids=("block-1",),
        source_path=Path(f"{doc}.pdf"), content_types=("text",),
    )
    return FusedCandidate(chunk=chunk, score=1 / (60 + rank), rank=rank, retrieval_methods=("vector",))


def test_diversifies_and_pins_first():
    pool = [candidate("A", "1", 1), candidate("A", "2", 2), candidate("B", "1", 3),
            candidate("A", "3", 4), candidate("C", "1", 5)]
    result = DocumentDiversifier().select(pool, top_k=3)
    assert [x.chunk.chunk_id for x in result] == ["A::1", "B::1", "C::1"]
    assert [x.rank for x in result] == [1, 2, 3]
    assert result[1].score == pool[2].score
    assert result[1].retrieval_methods == pool[2].retrieval_methods
    assert pool[2].rank == 3  # original objects are unchanged


def test_backfills_in_original_order():
    pool = [candidate("A", "1", 1), candidate("A", "2", 2), candidate("B", "1", 3),
            candidate("A", "3", 4)]
    result = DocumentDiversifier().select(pool, top_k=4)
    assert [x.chunk.chunk_id for x in result] == ["A::1", "B::1", "A::2", "A::3"]
    assert [x.rank for x in result] == [1, 2, 3, 4]


def test_top_k_one_keeps_original_leader():
    pool = [candidate("A", "1", 1), candidate("B", "1", 2)]
    assert DocumentDiversifier().select(pool, 1)[0].chunk == pool[0].chunk


def test_empty_pool_returns_empty_tuple():
    assert DocumentDiversifier().select([], 5) == ()


def test_top_k_larger_than_pool():
    pool = [candidate("A", "1", 1), candidate("B", "1", 2)]
    assert len(DocumentDiversifier().select(pool, 10)) == 2


def test_all_chunks_from_one_document_are_backfilled():
    pool = [candidate("A", str(i), i) for i in range(1, 5)]
    assert [x.chunk.chunk_id for x in DocumentDiversifier().select(pool, 3)] == ["A::1", "A::2", "A::3"]


def test_rejects_duplicate_chunk_ids():
    pool = [candidate("A", "1", 1), candidate("A", "1", 2)]
    with pytest.raises(ValueError, match="duplicate chunk_id"):
        DocumentDiversifier().select(pool, 2)


@pytest.mark.parametrize("top_k", [0, -1, True, 1.5, "5"])
def test_rejects_invalid_top_k(top_k):
    with pytest.raises(ValueError, match="top_k"):
        DocumentDiversifier().select([], top_k)
