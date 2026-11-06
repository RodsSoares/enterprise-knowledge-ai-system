"""Offline evidence and stage diagnostics; no providers, weights, or corpus."""

from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from app.chunking.schemas import RetrievalChunk
from app.retrieval.schemas import RetrievalCandidate
from app.retrieval.vector_index import NumPyVectorIndex
from tests.smoke import smoke_candidate_trace as trace


def candidate(doc, rank, method="vector", number=1, text="A source does not authorize a tool."):
    chunk = RetrievalChunk(chunk_id=f"{doc}::chunk-{number:05d}", document_id=doc,
        order=number, text=text, source_block_ids=(f"b{number}",),
        source_path=Path(f"{doc}.md"), content_types=("text",))
    return RetrievalCandidate(chunk=chunk, retrieval_method=method, rank=rank, score=1 / rank)


def test_full_vector_ranking_has_the_same_top20_as_a_top20_request_including_ties():
    index = NumPyVectorIndex()
    ids = tuple(f"c{i}" for i in range(29))
    vectors = tuple((1.0, float(i // 2)) for i in range(29))
    index.add(ids, vectors)
    assert index.search((1.0, 1.0), 29)[:20] == index.search((1.0, 1.0), 20)


def test_document_present_does_not_mean_the_reference_passage_was_selected():
    vector = (candidate("A", 1), candidate("A", 2, number=2),
              candidate("B", 3), candidate("C", 4), candidate("D", 5), candidate("E", 6))
    stages = trace.capture_stages(vector, ())
    reference = trace.diagnose_target(stages, [vector[1].chunk.chunk_id])
    document = trace.diagnose_target(stages, [c.chunk.chunk_id for c in vector if c.chunk.document_id == "A"])
    assert reference["outcome"] == "SAME_DOCUMENT_OTHER_PASSAGE_SELECTED"
    assert reference["ranks"]["fused_top20"] == 2
    assert reference["ranks"]["selected_top5"] is None
    assert document["outcome"] == "SELECTED"


def test_full_rank_does_not_leak_candidates_past_top20_into_baseline():
    vector = tuple(candidate(f"D{i}", i) for i in range(1, 24))
    stages = trace.capture_stages(vector, ())
    result = trace.diagnose_target(stages, [vector[20].chunk.chunk_id])
    assert result["outcome"] == "OUTSIDE_RETRIEVER_TOP20"
    assert result["ranks"]["vector_full"] == 21
    assert result["ranks"]["fused_union"] is None
    assert len(stages["fused_union"]) == 20


def test_rrf_cutoff_is_distinguished_from_retriever_depth():
    vector = tuple(candidate(f"V{i}", i) for i in range(1, 21))
    lexical = tuple(candidate(f"L{i}", i, method="lexical") for i in range(1, 21))
    result = trace.diagnose_target(trace.capture_stages(vector, lexical), [vector[-1].chunk.chunk_id])
    assert result["outcome"] == "FUSION_TOP20_CUTOFF"
    assert result["ranks"]["vector_full"] == 20
    assert result["ranks"]["fused_union"] == 39
    assert result["ranks"]["fused_top20"] is None


def test_final_selection_cutoff_is_distinguished_from_same_document_passage_loss():
    vector = tuple(candidate(f"D{i}", i) for i in range(1, 8))
    result = trace.diagnose_target(trace.capture_stages(vector, ()), [vector[5].chunk.chunk_id])
    assert result["outcome"] == "FINAL_TOP5_SELECTION"
    assert result["ranks"]["fused_top20"] == 6


def test_reference_group_uses_any_acceptable_alternative():
    vector = tuple(candidate(f"D{i}", i) for i in range(1, 25))
    result = trace.diagnose_target(trace.capture_stages(vector, ()),
                                   [vector[0].chunk.chunk_id, vector[-1].chunk.chunk_id])
    assert result["outcome"] == "SELECTED"
    assert result["ranks"]["selected_top5"] == 1


def test_empty_target_is_rejected():
    with pytest.raises(ValueError, match="empty"):
        trace.diagnose_target(trace.capture_stages((candidate("A", 1),), ()), [])


def test_trace_exposes_literal_collision_and_separate_rrf_contributions():
    vector = (candidate("A", 1),)
    lexical = (candidate("A", 1, method="lexical"),)
    serialized = trace.serialize_stages("a empresa autoriza?", trace.capture_stages(vector, lexical))
    assert serialized["lexical_positive"][0]["matched_query_tokens"] == ["a"]
    fused = serialized["fused_union"][0]
    assert set(fused["rrf_components"]) == {"vector", "lexical"}
    assert fused["score"] == pytest.approx(sum(v["rrf_contribution"] for v in fused["rrf_components"].values()))


def test_windows_absolute_helper_fingerprint_uses_only_known_local_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = Path("tests/smoke/helper.py")
    path.parent.mkdir(parents=True)
    path.write_text("original")
    live = {"input_fingerprints": {
        "C:/Users/user/repo/tests/smoke/helper.py": hashlib.sha256(path.read_bytes()).hexdigest()}}
    trace.verify_helper_fingerprints(live, [path])
    path.write_text("changed")
    with pytest.raises(ValueError, match="fingerprint"):
        trace.verify_helper_fingerprints(live, [path])


def review_fixture():
    cases_a = [{"question_id": "Q01", "query": "old query", "expected_document_ids": ["A"]}]
    cases_b = [{"question_id": "B01", "query": "new query", "expected_document_ids": ["A"],
                "reference_passage_groups": [{"fact_to_check": "detail in another passage",
                                              "any_of_chunk_ids": ["A::chunk-00002"]}]}]
    pool = [{"chunk_id": f"{doc}::chunk-00001", "document_id": doc,
             "rerank_score": float(6 - rank), "text": f"Introduction for {doc}"}
            for rank, doc in enumerate("ABCDE", 1)]
    ids = [c["chunk_id"] for c in pool]
    values = trace.question_metrics(ids, {c["chunk_id"]: c for c in pool}, ["A"])
    rows = []
    for group, case in (("A", cases_a[0]), ("B", cases_b[0])):
        row = dict(case, group=group, scored_selection=deepcopy(pool),
                   chunk_ids={arm: ids[:] for arm in trace.ARMS},
                   document_ids={arm: list("ABCDE") for arm in trace.ARMS},
                   metrics={arm: dict(values) for arm in trace.ARMS})
        if group == "B":
            row["reference_group_coverage_at_5"] = 0.0
        rows.append(row)
    source = {"questions": [{"question_id": "Q01", "final_chunk_ids": {"hybrid_v03": ids}}]}
    challenge = {"questions": cases_b}
    cached = {"questions": [{"question_id": "Q01", "policies": {"preserve_top3_and_top5": {"chunk_ids": ids}}}]}
    live = {"experiment": "RV-010", "status": "LIVE_EXPERIMENT_COMPLETE", "snapshot_stable": True,
        "provenance": {"source_canonical_sha256": trace.canonical_sha256(source),
                       "challenge_canonical_sha256": trace.canonical_sha256(challenge)},
        "configuration": {"candidate_depth": 20, "rrf_k": 60, "selected_chunks": 5,
            "protected_documents": 3, "chunk_count": 79,
            "embedding_model": "text-embedding-3-small", "lexical_text": "chunk.text"},
        "questions": rows, "groups": {g: {"question_count": 1,
            "metrics": {arm: dict(values) for arm in trace.ARMS}} for g in ("A", "B")}}
    return live, source, challenge, cached, cases_a, cases_b


def test_review_distinguishes_document_hit_from_missing_reference_evidence():
    report = trace.review_result(*review_fixture())
    assert report["group_metrics"]["B"]["prefix_preserved"]["Hit@1"] == 1
    assert report["b_reference_coverage"]["macro_mean"] == 0
    assert report["b_reference_coverage"]["zero_reference_questions"] == ["B01"]
    assert report["questions_b"][0]["missing_expected_documents"] == []
    assert report["automatically_promoted"] is False


@pytest.mark.parametrize("mutation, message", [
    ("row_metric", "Metric mismatch"), ("group_metric", "Metric mismatch"),
    ("query", "definition changed"), ("coverage", "coverage mismatch"),
    ("duplicate_question", "missing or duplicated"), ("score_order", "order disagrees"),
    ("source_binding", "binding mismatch"), ("unstable", "stable RV-010"),
])
def test_review_rejects_inconsistent_evidence(mutation, message):
    args = review_fixture()
    live = args[0]
    if mutation == "row_metric":
        live["questions"][1]["metrics"]["prefix_preserved"]["Hit@1"] = 0.5
    elif mutation == "group_metric":
        live["groups"]["B"]["metrics"]["prefix_preserved"]["MRR"] = 0.5
    elif mutation == "query":
        live["questions"][1]["query"] = "another query"
    elif mutation == "coverage":
        live["questions"][1]["reference_group_coverage_at_5"] = 1
    elif mutation == "duplicate_question":
        live["questions"][1] = deepcopy(live["questions"][0])
    elif mutation == "score_order":
        live["questions"][1]["scored_selection"][1]["rerank_score"] = 99
    elif mutation == "source_binding":
        live["provenance"]["source_canonical_sha256"] = "changed"
    elif mutation == "unstable":
        live["snapshot_stable"] = False
    with pytest.raises(ValueError, match=message):
        trace.review_result(*args)
