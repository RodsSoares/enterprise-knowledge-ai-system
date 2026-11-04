"""Tests for reciprocal rank fusion."""
from pathlib import Path
import pytest

from app.chunking.schemas import RetrievalChunk
from app.retrieval.schemas import RetrievalCandidate
from app.retrieval.candidate_fusion import ReciprocalRankFusion


def chunk(name: str, text: str = "evidence") -> RetrievalChunk:
    return RetrievalChunk(
        chunk_id=f"DOC-001::{name}", document_id="DOC-001", order=0,
        text=text, source_block_ids=(name,), source_path=Path("doc.pdf"),
        content_types=("text",),
    )


def candidate(item: RetrievalChunk, method: str, rank: int) -> RetrievalCandidate:
    return RetrievalCandidate(item, method, 0.5, rank)


def test_empty_rankings():
    assert ReciprocalRankFusion().fuse([[], []]) == ()


def test_shared_candidate_is_promoted():
    a, b, c = chunk("a"), chunk("b"), chunk("c")
    result = ReciprocalRankFusion().fuse([
        [candidate(a, "vector", 1), candidate(b, "vector", 2)],
        [candidate(c, "lexical", 1), candidate(b, "lexical", 2)],
    ])
    assert result[0].chunk == b
    assert result[0].retrieval_methods == ("lexical", "vector")
    assert result[0].rank == 1


def test_scores_use_ranks_not_source_scores():
    a = chunk("a")
    result = ReciprocalRankFusion(k=60).fuse([
        [RetrievalCandidate(a, "vector", -100.0, 1)],
        [RetrievalCandidate(a, "lexical", 999.0, 2)],
    ])
    assert result[0].score == pytest.approx(1 / 61 + 1 / 62)


def test_ties_follow_first_seen_order():
    a, b = chunk("a"), chunk("b")
    result = ReciprocalRankFusion().fuse([
        [candidate(a, "vector", 1)], [candidate(b, "lexical", 1)]
    ])
    assert [r.chunk.chunk_id for r in result] == [a.chunk_id, b.chunk_id]


def test_top_k_limits_output_and_reassigns_rank():
    a, b = chunk("a"), chunk("b")
    result = ReciprocalRankFusion().fuse([[candidate(a, "vector", 1), candidate(b, "vector", 2)]], top_k=1)
    assert len(result) == 1
    assert result[0].rank == 1


@pytest.mark.parametrize("k", [0, -1, 1.2, True])
def test_invalid_rrf_k(k):
    with pytest.raises(ValueError):
        ReciprocalRankFusion(k=k)


@pytest.mark.parametrize("top_k", [0, -1, 1.2, True])
def test_invalid_top_k(top_k):
    with pytest.raises(ValueError):
        ReciprocalRankFusion().fuse([], top_k=top_k)


def test_rejects_duplicate_methods():
    a, b = chunk("a"), chunk("b")
    with pytest.raises(ValueError, match="duplicate retrieval method"):
        ReciprocalRankFusion().fuse([[candidate(a, "vector", 1)], [candidate(b, "vector", 1)]])


def test_rejects_duplicate_chunk_within_ranking():
    a = chunk("a")
    with pytest.raises(ValueError, match="chunk_ids"):
        ReciprocalRankFusion().fuse([[candidate(a, "vector", 1), candidate(a, "vector", 2)]])


def test_rejects_conflicting_chunk_provenance():
    a = chunk("a")
    altered = chunk("a", text="different")
    with pytest.raises(ValueError, match="conflicting chunk provenance"):
        ReciprocalRankFusion().fuse([[candidate(a, "vector", 1)], [candidate(altered, "lexical", 1)]])


def test_rejects_duplicate_ranks():
    a, b = chunk("a"), chunk("b")
    with pytest.raises(ValueError, match="ranks"):
        ReciprocalRankFusion().fuse([[candidate(a, "vector", 1), candidate(b, "vector", 1)]])


def test_rejects_mixed_methods_in_ranking():
    a, b = chunk("a"), chunk("b")
    with pytest.raises(ValueError, match="single retrieval method"):
        ReciprocalRankFusion().fuse([[candidate(a, "vector", 1), candidate(b, "lexical", 2)]])
