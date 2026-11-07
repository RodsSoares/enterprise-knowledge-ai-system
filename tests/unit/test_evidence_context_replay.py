"""Offline audit rejects corrupted evidence and distinguishes context coverage."""

from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.chunking.schemas import RetrievalChunk
from app.retrieval.candidate_fusion import FusedCandidate
from app.retrieval.evidence_context import EvidenceContextBuilder
from tests.smoke import smoke_evidence_context_replay as replay
from tests.smoke import smoke_filtered_reranking as rv013


def fixture_pool():
    return tuple(FusedCandidate(RetrievalChunk(chunk_id=f"{doc}::chunk-{number:05}",
        document_id=doc, order=number, text=f"Source {doc}/{number}",
        source_block_ids=(f"b{number}",), source_path=Path(f"{doc}.md"), content_types=("text",)),
        score=1 / (60 + rank), rank=rank, retrieval_methods=("vector",))
        for rank, (doc, number) in enumerate([(d, 1) for d in "ABCDE"] + [("A", 2)], 1))


def audit_fixture():
    pool = fixture_pool()
    source = {"configuration": {"model": "fixture-model", "revision": "fixture-revision"}}
    trace = {"status": "BASELINE_DRIFT"}
    replayed = {"drift_from_rv010": [{"question_id": "B11"}]}
    prepared, rows = [], []
    for group in ("A", "B"):
        case = {"question_id": group + "01", "query": "Qual regra se aplica?",
                "expected_document_ids": ["A"]}
        if group == "B":
            case["reference_passage_groups"] = [{"any_of_chunk_ids": ["A::chunk-00002"]}]
        scorer = Mock()
        scorer.score_pairs.return_value = [1, 5, 2, 9, 8]
        row = rv013.score_case(case, pool[:5], scorer)
        row.update(group=group, score_seconds=1.25)
        rows.append(row)
        prepared.append((group, case, pool[:5], pool))
    groups = {g: rv013.summarize([row for row in rows if row["group"] == g]) for g in ("A", "B")}
    recorded = {"experiment": "RV-013", "status": "LIVE_RERANK_ON_FROZEN_RETRIEVAL_COMPLETE",
        "snapshot_stable": True, "automatically_promoted": False,
        "configuration": {"retrieval_mode": "frozen RV-011 vectors + recomputed filtered BM25/RRF/diversity",
            "cross_encoder_mode": "real inference", **source["configuration"], "device": "cpu",
            "batch_size": 8, "max_length": 512, "protected_documents": 3, "selected_chunks": 5,
            "candidate_depth": 20, "rrf_k": 60, "filter_policy_sha256": rv013.FILTER_POLICY_SHA256,
            "rerank_text": "build_search_text(chunk)", "rerank_query": "original unfiltered query"},
        "provenance": {"rv011_canonical_sha256": replay.canonical_sha256(trace),
            "rv011_source_status": trace["status"], "rv011_drift_from_rv010": replayed["drift_from_rv010"],
            "rv012_filtered_selections_reproduced": True, "rv012_saved_canonical_sha256": "local RV012 hash"},
        "groups": groups, "questions": rows, "decision": rv013.decide(groups, True),
        "new_embedding_calls": 0, "cross_encoder_scoring_calls": 2, "cross_encoder_pairs": 10,
        "model_load_seconds": 25.0, "input_fingerprints": {"C:/project/file.py": "hash"}}
    return recorded, source, trace, replayed, prepared


def test_audit_reuses_saved_scores_and_original_latency_without_loading_a_model(monkeypatch):
    import app.retrieval.cross_encoder_scorer as cross_encoder
    loader = Mock(side_effect=AssertionError("No model loading is allowed"))
    monkeypatch.setattr(cross_encoder.TransformersCrossEncoderScorer, "load", loader)
    inputs = audit_fixture()
    original = deepcopy(inputs[0])
    result = replay.audit_rv013(*inputs)
    assert result["rankings_metrics_and_passage_provenance_reproduced"] is True
    assert result["groups"]["A"]["scoring_latency_seconds"]["mean"] == 1.25
    assert result["recorded_model_load_seconds"] == 25.0
    assert result["rv012_saved_file_hash_revalidated"] is False
    assert inputs[0] == original
    loader.assert_not_called()


@pytest.mark.parametrize("change", [
    "text", "fusion_score", "source_block_ids", "rerank_score", "metric", "query", "selection",
    "duplicate_question", "duplicate_passage", "trace_hash", "filter_policy", "group_metrics",
    "decision", "latency", "pair_count", "unstable",
])
def test_audit_rejects_changed_or_inconsistent_results(change):
    inputs = audit_fixture()
    recorded = inputs[0]
    row = recorded["questions"][0]
    if change in ("text", "source_block_ids"):
        row["scored_selection"][0][change] = "Changed evidence"
    elif change == "fusion_score":
        row["scored_selection"][0][change] = 0.99
    elif change == "rerank_score":
        row["scored_selection"][0][change] = float("nan")
    elif change == "metric":
        row["arms"]["filtered_only"]["metrics"]["Hit@1"] = 0.25
    elif change == "query":
        row["query"] = "Changed question"
    elif change == "selection":
        row["arms"]["filtered_only"]["chunk_ids"].reverse()
    elif change == "duplicate_question":
        recorded["questions"][1] = deepcopy(row)
    elif change == "duplicate_passage":
        row["scored_selection"][1] = deepcopy(row["scored_selection"][0])
    elif change == "trace_hash":
        recorded["provenance"]["rv011_canonical_sha256"] = "changed"
    elif change == "filter_policy":
        recorded["configuration"]["filter_policy_sha256"] = "changed"
    elif change == "group_metrics":
        recorded["groups"]["A"]["metrics"]["filtered_only"]["Hit@1"] = 0.25
    elif change == "decision":
        recorded["decision"] = "AUTOMATIC_PASS"
    elif change == "latency":
        row["score_seconds"] = -1
    elif change == "pair_count":
        recorded["cross_encoder_pairs"] = 9
    elif change == "unstable":
        recorded["snapshot_stable"] = False
    with pytest.raises(ValueError):
        replay.audit_rv013(*inputs)


def test_context_coverage_is_measured_separately_and_labels_do_not_change_selection():
    pool = fixture_pool()
    case = {"question_id": "fixture", "query": "Regra?", "expected_document_ids": ["A"],
            "reference_passage_groups": [{"any_of_chunk_ids": ["A::chunk-00002"]}]}
    control = EvidenceContextBuilder(max_chunks=5, max_additional_per_document=0)
    expanded = EvidenceContextBuilder()
    row = replay.context_case(case, pool[:5], pool, control, expanded)
    assert row["retrieval_at_5"]["metrics"]["Recall@5"] == 1.0
    assert row["retrieval_at_5"]["reference_coverage"] == 0.0
    assert row["contexts"]["expanded_context"]["reference_coverage_in_context"] == 1.0
    assert row["contexts"]["expanded_context"]["passage_count"] == 6
    changed = dict(case, expected_document_ids=["X"], reference_passage_groups=[{"any_of_chunk_ids": ["unseen"]}])
    other = replay.context_case(changed, pool[:5], pool, control, expanded)
    for arm in replay.CONTEXT_ARMS:
        assert row["contexts"][arm]["rendered_context"] == other["contexts"][arm]["rendered_context"]
    summary = replay.summarize_contexts([row])
    assert summary["total_rendered_character_ratio"] > 1
    assert "Recall@5" not in summary["contexts"]["expanded_context"]


def test_no_reference_labels_does_not_mean_perfect_passage_coverage():
    pool = fixture_pool()
    case = {"question_id": "unlabeled", "query": "Regra?", "expected_document_ids": ["A"]}
    row = replay.context_case(case, pool[:5], pool, EvidenceContextBuilder(max_chunks=5), EvidenceContextBuilder())
    summary = replay.summarize_contexts([row])
    assert "reference_passages" not in summary["contexts"]["expanded_context"]
    assert "reference_coverage_in_context" not in row["contexts"]["expanded_context"]


def test_output_cannot_overwrite_a_source_file(tmp_path):
    source = tmp_path / "source.json"
    source.write_text("Original bytes", encoding="utf-8")
    with pytest.raises(SystemExit) as caught:
        replay.main(["--source", str(source), "--output", str(source)])
    assert caught.value.code == 2
    assert source.read_text(encoding="utf-8") == "Original bytes"
