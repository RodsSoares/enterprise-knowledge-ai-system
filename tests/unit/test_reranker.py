"""Offline behavioral tests: ordering, evidence identity and final selection."""

from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.chunking.schemas import RetrievalChunk
from app.retrieval.candidate_fusion import FusedCandidate, ReciprocalRankFusion
from app.retrieval.document_diversifier import DocumentDiversifier
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.reranker import CandidateReranker, select_reranked_candidates
from app.retrieval.schemas import RetrievalCandidate


def candidate(document, number=1, rank=1):
    chunk = RetrievalChunk(
        chunk_id=f"{document}::chunk-{number:05d}", document_id=document,
        order=number, text=f"Evidence from {document}, passage {number}.",
        source_block_ids=(f"block-{number}",), source_path=Path(f"{document}.pdf"),
        section_path=("Policy", "Approved channels"), page_numbers=(number,),
        content_types=("text",),
    )
    return FusedCandidate(chunk, 1 / (60 + rank), rank, ("vector", "lexical"))


def make_reranker(scores):
    scorer = Mock()
    scorer.score_pairs.return_value = scores
    return CandidateReranker(scorer), scorer


def test_scores_entire_pool_before_selecting_top_k_and_preserves_provenance():
    pool = [candidate("DOC-A"), candidate("DOC-B", rank=2), candidate("DOC-C", rank=3)]
    original = tuple(pool)
    reranker, scorer = make_reranker([-2.0, 9.0, 3.0])
    result = reranker.rerank("Quais canais são aprovados?", pool, top_k=1)
    assert result[0].source is pool[1]
    assert result[0].chunk is pool[1].chunk
    assert result[0].score == 9.0
    assert result[0].source.score == 1 / 62
    assert result[0].source.rank == 2
    assert result[0].rank == result[0].rerank_rank == 1
    assert result[0].retrieval_methods == pool[1].retrieval_methods
    assert tuple(pool) == original
    query, passages = scorer.score_pairs.call_args.args
    assert query == "Quais canais são aprovados?"
    assert len(passages) == 3
    assert passages[0] == "Section: Policy > Approved channels\n\n" + pool[0].chunk.text
    with pytest.raises(FrozenInstanceError):
        result[0].score = 0


def test_equal_scores_keep_input_order_including_negative_scores():
    pool = [candidate("DOC-B", rank=2), candidate("DOC-A", rank=1)]
    reranker, _ = make_reranker([-3.0, -3.0])
    result = reranker.rerank("query", pool, top_k=20)
    assert [item.source for item in result] == pool
    assert [item.rank for item in result] == [1, 2]


def test_empty_pool_does_not_call_scorer():
    reranker, scorer = make_reranker([])
    assert reranker.rerank("query", []) == ()
    scorer.score_pairs.assert_not_called()


@pytest.mark.parametrize("query", ["", "  ", None, 42])
def test_invalid_queries_fail_before_scoring(query):
    reranker, scorer = make_reranker([1])
    with pytest.raises(ValueError, match="query"):
        reranker.rerank(query, [candidate("DOC-A")])
    scorer.score_pairs.assert_not_called()


@pytest.mark.parametrize("top_k", [0, -1, 1.5, True])
def test_invalid_output_depth_rejected(top_k):
    reranker, scorer = make_reranker([1])
    with pytest.raises(ValueError, match="top_k"):
        reranker.rerank("query", [], top_k=top_k)
    with pytest.raises(ValueError, match="top_k"):
        select_reranked_candidates([], top_k=top_k)
    scorer.score_pairs.assert_not_called()


def test_duplicate_identity_rejected_before_scoring():
    item = candidate("DOC-A")
    reranker, scorer = make_reranker([1, 2])
    with pytest.raises(ValueError, match="duplicate"):
        reranker.rerank("query", [item, replace(item, rank=2)])
    scorer.score_pairs.assert_not_called()


@pytest.mark.parametrize("scores", [[], [1, 2], [float("nan")], [float("inf")],
                                   [float("-inf")], [True], ["0.9"], [None]])
def test_malformed_provider_scores_are_not_silently_accepted(scores):
    reranker, _ = make_reranker(scores)
    with pytest.raises(ValueError):
        reranker.rerank("query", [candidate("DOC-A")])


def test_provider_failure_propagates_without_baseline_substitution():
    reranker, scorer = make_reranker([])
    scorer.score_pairs.side_effect = RuntimeError("model unavailable")
    with pytest.raises(RuntimeError, match="model unavailable"):
        reranker.rerank("query", [candidate("DOC-A")])


def test_diversity_uses_reranker_leader_and_keeps_both_original_rankings():
    pool = [candidate("DOC-A"), candidate("DOC-A", 2, 2),
            candidate("DOC-B", rank=3), candidate("DOC-C", rank=4)]
    reranker, scorer = make_reranker([8, 9, 5, 4])
    ranked = reranker.rerank("query", pool, top_k=20)
    normal = select_reranked_candidates(ranked, top_k=3)
    diverse = select_reranked_candidates(ranked, 3, DocumentDiversifier())
    assert [item.chunk.document_id for item in normal] == ["DOC-A", "DOC-A", "DOC-B"]
    assert [item.chunk.document_id for item in diverse] == ["DOC-A", "DOC-B", "DOC-C"]
    assert diverse[0].source is pool[1]
    assert [item.rank for item in diverse] == [1, 2, 3]
    assert [item.rerank_rank for item in diverse] == [1, 3, 4]
    assert [item.source.rank for item in diverse] == [2, 3, 4]
    assert [item.score for item in diverse] == [9, 5, 4]
    scorer.score_pairs.assert_called_once()


def test_selection_backfills_same_document_and_handles_short_empty_pools():
    pool = [candidate("DOC-A"), candidate("DOC-A", 2, 2)]
    reranker, _ = make_reranker([2, 1])
    ranked = reranker.rerank("query", pool)
    assert select_reranked_candidates(ranked, 5, DocumentDiversifier()) == ranked
    assert select_reranked_candidates([], 5, DocumentDiversifier()) == ()
    with pytest.raises(ValueError, match="duplicate"):
        select_reranked_candidates([ranked[0], ranked[0]])


def test_real_hybrid_fusion_composes_with_reranking_before_diversity():
    chunks = [candidate("DOC-A").chunk, candidate("DOC-A", 2).chunk,
              candidate("DOC-B").chunk]
    vector, lexical = Mock(), Mock()
    vector.retrieve.return_value = tuple(
        RetrievalCandidate(chunk, "vector", 0.9, rank)
        for rank, chunk in enumerate(chunks, 1)
    )
    lexical.retrieve.return_value = ()
    hybrid = HybridRetriever(vector, lexical, ReciprocalRankFusion())
    pool = hybrid.retrieve("query", top_k=20)
    reranker, _ = make_reranker([1, 2, 8])
    result = select_reranked_candidates(
        reranker.rerank("query", pool, top_k=20), 2, DocumentDiversifier()
    )
    assert [item.chunk.document_id for item in result] == ["DOC-B", "DOC-A"]
    assert result[0].chunk is chunks[2]
    assert result[0].source.rank == 3
    assert result[0].source.score == pytest.approx(1 / 63)


@pytest.mark.parametrize("changes,expected", [
    ({}, "NO_FIRST_RANK_GAIN"),
    ({"Hit@1": 11 / 13, "MRR": 24 / 26}, "READY_FOR_PASSAGE_REVIEW"),
    ({"Hit@1": 11 / 13, "Recall@5": 12 / 13}, "REGRESSION"),
    ({"MRR": 0.8}, "REGRESSION"),
])
def test_benchmark_gate_requires_gain_without_metric_regression(changes, expected):
    from tests.smoke.smoke_reranking_experiment import FROZEN_V03, assess_experiment
    result = assess_experiment(FROZEN_V03, dict(FROZEN_V03, **changes))
    assert result["decision"] == expected
    assert result["automatically_promoted"] is False


def test_benchmark_does_not_promote_against_a_drifted_baseline():
    from tests.smoke.smoke_reranking_experiment import FROZEN_V03, assess_experiment
    baseline = dict(FROZEN_V03, **{"Hit@1": 0.5})
    assert assess_experiment(baseline, FROZEN_V03)["decision"] == "BASELINE_DRIFT"
