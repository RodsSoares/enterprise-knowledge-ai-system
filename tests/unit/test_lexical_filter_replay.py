"""Integrity checks and evidence tradeoffs for the offline lexical replay."""

import hashlib
from pathlib import Path

import pytest

from app.chunking.schemas import RetrievalChunk
from app.retrieval.schemas import RetrievalCandidate
from tests.smoke import smoke_lexical_filter_replay as replay


def chunk(doc, number=1):
    return RetrievalChunk(chunk_id=f"{doc}::chunk-{number:05d}", document_id=doc,
        order=number, text=f"Evidence {doc}/{number}", source_block_ids=(f"b{number}",),
        source_path=Path(f"{doc}.md"), content_types=("text",))


def records(chunks):
    return [{"chunk_id": c.chunk_id, "document_id": c.document_id, "score": 1 / i, "rank": i}
            for i, c in enumerate(chunks, 1)]


def test_replay_rejects_changed_catalog_text():
    record = {"chunk_id": "D::chunk-00001", "document_id": "D", "text": "changed",
              "text_sha256": hashlib.sha256(b"original").hexdigest()}
    with pytest.raises(ValueError, match="text hash"):
        replay.restore_catalog([record])


@pytest.mark.parametrize("fault", ["missing", "duplicate"])
def test_full_vector_trace_must_include_each_catalog_chunk_exactly_once(fault):
    chunks = (chunk("A"), chunk("B"))
    ranking = records(chunks)
    ranking = ranking[:1] if fault == "missing" else ranking[:1] * 2
    with pytest.raises(ValueError, match="Incomplete or duplicate"):
        replay.restore_ranking(ranking, {c.chunk_id: c for c in chunks}, "vector", complete=True)


@pytest.mark.parametrize("fault", ["nan", "unsorted", "wrong_document"])
def test_cached_vector_evidence_must_be_finite_sorted_and_provenanced(fault):
    chunks = (chunk("A"), chunk("B"))
    ranking = records(chunks)
    if fault == "nan":
        ranking[0]["score"] = float("nan")
    elif fault == "unsorted":
        ranking[1]["score"] = 2
    else:
        ranking[0]["document_id"] = "OTHER"
    with pytest.raises(ValueError, match="Invalid"):
        replay.restore_ranking(ranking, {c.chunk_id: c for c in chunks}, "vector", complete=True)


def test_reproduced_ranks_with_different_scores_do_not_count_as_valid_reproduction():
    c = chunk("A")
    actual = (RetrievalCandidate(c, "vector", 0.8, 1),)
    saved = [{"chunk_id": c.chunk_id, "document_id": "A", "rank": 1, "score": 0.2}]
    with pytest.raises(ValueError, match="score mismatch"):
        replay.verify_ranking(actual, saved, "fixture")


def test_disabling_diversity_can_lose_required_documents_even_with_same_top1():
    chunks = tuple(chunk("A", i) for i in range(1, 6)) + (chunk("B"),)
    vector = tuple(RetrievalCandidate(c, "vector", 1 / rank, rank) for rank, c in enumerate(chunks, 1))
    arms = replay.build_arms(vector, (), ())
    case = {"expected_document_ids": ["A", "B"]}
    pool = {c.chunk_id: {"document_id": c.document_id} for c in chunks}
    diverse = replay.evaluate_selection(arms["filtered_hybrid_diverse"], case, pool)
    plain = replay.evaluate_selection(arms["filtered_hybrid_top5"], case, pool)
    assert diverse["metrics"]["Hit@1"] == plain["metrics"]["Hit@1"] == 1
    assert diverse["metrics"]["Recall@5"] == 1
    assert plain["metrics"]["Recall@5"] == 0.5


def test_diagnostic_full_vector_ranking_does_not_expand_the_algorithm_input_depth():
    chunks = tuple(chunk(f"D{i}") for i in range(1, 25))
    vector = tuple(RetrievalCandidate(c, "vector", 1 / rank, rank) for rank, c in enumerate(chunks, 1))
    arms = replay.build_arms(vector, (), ())
    allowed = {c.chunk_id for c in chunks[:20]}
    for selected in arms.values():
        assert len(selected) == 5
        assert all(c.chunk.chunk_id in allowed for c in selected)
