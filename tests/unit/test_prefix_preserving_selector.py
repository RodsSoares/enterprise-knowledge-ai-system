"""Behavioral coverage of opt-in ordering with document-prefix preservation."""

from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.chunking.schemas import RetrievalChunk
from app.retrieval.candidate_fusion import FusedCandidate
from app.retrieval.prefix_preserving_selector import PrefixPreservingSelector
from app.retrieval.reranker import CandidateReranker


def candidate(doc, number=1, fusion_rank=1):
    chunk = RetrievalChunk(
        chunk_id=f"{doc}::chunk-{number:05d}", document_id=doc, order=number,
        text=f"Evidence {doc}/{number}", source_block_ids=(f"b{number}",),
        source_path=Path(f"{doc}.pdf"), page_numbers=(number,), content_types=("text",),
    )
    return FusedCandidate(chunk, 1 / (60 + fusion_rank), fusion_rank, ("vector",))


def score(baseline, scores):
    provider = Mock()
    provider.score_pairs.return_value = scores
    ranked = CandidateReranker(provider).rerank("query", baseline, top_k=max(1, len(baseline)))
    return ranked, provider


def test_only_reorders_inside_protected_document_groups_and_preserves_provenance():
    baseline = tuple(candidate(doc, fusion_rank=rank) for doc, rank in zip("ABCDE", (1, 3, 8, 11, 17)))
    ranked, provider = score(baseline, [2, 5, 1, 8, 7])
    result = PrefixPreservingSelector().select(baseline, ranked)
    assert [c.chunk.document_id for c in ranked] == list("DEBAC")
    assert [c.chunk.document_id for c in result] == list("BACDE")
    assert [c.rank for c in result] == [1, 2, 3, 4, 5]
    assert [c.rerank_rank for c in result] == [3, 4, 5, 1, 2]
    assert [c.source.rank for c in result] == [3, 1, 8, 11, 17]
    assert result[0].source is baseline[1]
    assert result[0].chunk is baseline[1].chunk
    assert result[0].source.score == 1 / 63
    provider.score_pairs.assert_called_once()


def test_duplicate_documents_preserve_unique_document_prefix_not_chunk_positions():
    baseline = (candidate("A"), candidate("A", 2), candidate("B"), candidate("C"), candidate("D"))
    ranked, _ = score(baseline, [1, 2, 4, 3, 9])
    result = PrefixPreservingSelector().select(baseline, ranked)
    assert [c.chunk.document_id for c in result] == ["B", "C", "A", "A", "D"]
    assert set(list(dict.fromkeys(c.chunk.document_id for c in result))[:3]) == {"A", "B", "C"}
    assert {c.chunk.chunk_id for c in result} == {c.chunk.chunk_id for c in baseline}


def test_ties_follow_baseline_order_even_if_scored_sequence_is_reversed():
    baseline = tuple(candidate(doc) for doc in "ABCDE")
    ranked, _ = score(baseline, [-1] * 5)
    result = PrefixPreservingSelector().select(baseline, tuple(reversed(ranked)))
    assert [c.chunk.document_id for c in result] == list("ABCDE")


def test_short_selection_and_empty_selection_are_supported():
    baseline = (candidate("A"), candidate("B"))
    ranked, _ = score(baseline, [1, 2])
    assert [c.chunk.document_id for c in PrefixPreservingSelector().select(baseline, ranked)] == ["B", "A"]
    assert PrefixPreservingSelector().select([], []) == ()


@pytest.mark.parametrize("value", [0, -1, True, 1.5, "3"])
def test_invalid_prefix_configuration_is_rejected(value):
    with pytest.raises(ValueError, match="positive integer"):
        PrefixPreservingSelector(value)


def test_incomplete_or_extra_scored_candidates_are_rejected():
    baseline = (candidate("A"), candidate("B"))
    ranked, _ = score(baseline, [1, 2])
    with pytest.raises(ValueError, match="exactly"):
        PrefixPreservingSelector().select(baseline, ranked[:1])
    with pytest.raises(ValueError, match="exactly"):
        PrefixPreservingSelector().select(baseline[:1], ranked)


def test_duplicate_chunk_ids_are_rejected_on_both_sides():
    baseline = (candidate("A"),)
    ranked, _ = score(baseline, [1])
    with pytest.raises(ValueError, match="duplicate"):
        PrefixPreservingSelector().select(baseline * 2, ranked)
    with pytest.raises(ValueError, match="duplicate"):
        PrefixPreservingSelector().select(baseline, ranked * 2)


@pytest.mark.parametrize("change", ["text", "fusion_score", "fusion_rank"])
def test_same_identity_with_changed_source_is_rejected(change):
    baseline = (candidate("A"),)
    ranked, _ = score(baseline, [1])
    original = baseline[0]
    changed = (replace(original, chunk=replace(original.chunk, text="different evidence")) if change == "text"
               else replace(original, score=0.9) if change == "fusion_score" else replace(original, rank=8))
    with pytest.raises(ValueError, match="provenance"):
        PrefixPreservingSelector().select(baseline, [replace(ranked[0], source=changed)])
