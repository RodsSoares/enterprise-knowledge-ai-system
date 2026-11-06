"""Composition and experiment decisions without loading model weights."""

from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.chunking.schemas import RetrievalChunk
from app.retrieval.candidate_fusion import FusedCandidate
from tests.smoke import smoke_filtered_reranking as experiment


def baseline():
    return tuple(FusedCandidate(RetrievalChunk(
        chunk_id=f"{doc}::chunk-00001", document_id=doc, order=1,
        text=f"Evidence {doc}", section_path=("Approval",), source_block_ids=("b1",),
        source_path=Path(f"{doc}.md"), content_types=("text",)),
        score=1 / (60 + rank), rank=rank, retrieval_methods=("vector",))
        for doc, rank in zip("ABCDE", (1, 3, 4, 9, 13)))


def question():
    return {"question_id": "fixture", "query": "A aprovação do SOP não pode ser dispensada?",
            "expected_document_ids": ["A"], "reference_passage_groups": [
                {"any_of_chunk_ids": ["A::chunk-00001"]},
                {"any_of_chunk_ids": ["A::chunk-00002"]}]}


def test_one_scoring_call_uses_original_query_and_preserves_both_score_provenances():
    scorer = Mock()
    scorer.score_pairs.return_value = [1, 5, 2, 9, 8]
    case = question()
    result = experiment.score_case(case, baseline(), scorer)
    scorer.score_pairs.assert_called_once_with(case["query"], tuple(
        f"Section: Approval\n\nEvidence {doc}" for doc in "ABCDE"))
    assert result["arms"]["filtered_only"]["document_ids"] == list("ABCDE")
    assert result["arms"]["filtered_reranked"]["document_ids"] == list("DEBCA")
    assert result["arms"]["filtered_prefix_preserved"]["document_ids"] == list("BCADE")
    top_scored = result["scored_selection"][0]
    assert top_scored["document_id"] == "D"
    assert top_scored["fusion_rank"] == 9 and top_scored["rerank_rank"] == 1
    assert top_scored["fusion_score"] == 1 / 69 and top_scored["rerank_score"] == 9
    assert result["scored_pairs"] == 5


def test_fixed_membership_does_not_claim_to_repair_missing_passages():
    scorer = Mock()
    scorer.score_pairs.return_value = [1, 5, 2, 9, 8]
    result = experiment.score_case(question(), baseline(), scorer)
    for arm in result["arms"].values():
        assert arm["reference_coverage"] == 0.5
        assert arm["missing_reference_groups"] == [{"any_of_chunk_ids": ["A::chunk-00002"]}]
    assert "Hit@1" in result["per_question_regressed_metrics"]["filtered_prefix_preserved"]


def test_score_ties_keep_control_order_and_do_not_invent_a_gain():
    scorer = Mock()
    scorer.score_pairs.return_value = [0] * 5
    result = experiment.score_case(question(), baseline(), scorer)
    group = experiment.summarize([result])
    assert group["comparisons"]["filtered_prefix_preserved"]["decision"] == "NO_FIRST_RANK_GAIN"
    assert group["per_question_regressions"]["filtered_prefix_preserved"] == []


def test_scorer_failure_propagates_without_a_successful_baseline_fallback():
    scorer = Mock()
    scorer.score_pairs.side_effect = RuntimeError("weights unavailable")
    with pytest.raises(RuntimeError, match="weights unavailable"):
        experiment.score_case(question(), baseline(), scorer)


def test_unexpected_selection_size_is_rejected_before_inference():
    scorer = Mock()
    with pytest.raises(ValueError, match="exactly five"):
        experiment.score_case(question(), baseline()[:4], scorer)
    scorer.score_pairs.assert_not_called()


@pytest.mark.parametrize("decision_a, decision_b, individual_loss, stable, expected", [
    ("IMPROVEMENT", "REGRESSION", False, True, "REGRESSION_KEEP_FILTER_ONLY"),
    ("IMPROVEMENT", "NO_FIRST_RANK_GAIN", True, True, "MIXED_RESULTS_REVIEW_REQUIRED"),
    ("IMPROVEMENT", "NO_FIRST_RANK_GAIN", False, True, "CANDIDATE_FOR_REVIEW"),
    ("NO_FIRST_RANK_GAIN", "NO_FIRST_RANK_GAIN", False, True, "NO_MEASURED_GAIN_KEEP_FILTER_ONLY"),
    ("IMPROVEMENT", "REGRESSION", True, False, "INPUT_CHANGED_DURING_RUN"),
])
def test_decision_reports_losses_separately_from_aggregate_improvement(
    decision_a, decision_b, individual_loss, stable, expected,
):
    arm = "filtered_prefix_preserved"
    groups = {group: {"comparisons": {arm: {"decision": decision}},
        "per_question_regressions": {arm: ([{"question_id": "Q25"}] if group == "A" and individual_loss else [])}}
        for group, decision in (("A", decision_a), ("B", decision_b))}
    assert experiment.decide(groups, stable) == expected


def replay_fixture():
    values = {metric: 1.0 for metric in experiment.METRIC_NAMES}
    rows = [{"question_id": qid, "group": group, "query": query,
             "expected_document_ids": ["A"], "filtered_lexical_query": query,
             "arms": {"filtered_hybrid_diverse": {"chunk_ids": ["A::chunk-00001"],
                 "metrics": dict(values), "reference_coverage": 1.0}}}
            for qid, group, query in (("Q01", "A", "old"), ("B01", "B", "new"))]
    fresh = {"experiment": "RV-012", "status": "OFFLINE_EXPLORATORY_REPLAY_COMPLETE",
        "source_trace_canonical_sha256": "trace", "source_live_canonical_sha256": "live",
        "configuration": {"filter_policy_sha256": experiment.FILTER_POLICY_SHA256},
        "questions": rows, "groups": {g: {"metrics": {"filtered_hybrid_diverse": dict(values)}} for g in ("A", "B")}}
    return deepcopy(fresh), fresh


def test_local_paths_do_not_make_an_identical_saved_selection_fail_validation():
    saved, fresh = replay_fixture()
    saved["input_fingerprints"] = {"C:/user/project/fixture.json": "hash"}
    fresh["input_fingerprints"] = {"/scratch/fixture.json": "hash"}
    experiment.validate_saved_replay(saved, fresh)


@pytest.mark.parametrize("change, error", [
    ("selection", "selection changed"), ("query", "definition changed"),
    ("binding", "binding changed"), ("policy", "configuration changed"),
    ("group_metrics", "Metric mismatch"), ("duplicates", "missing or duplicated"),
    ("coverage", "coverage changed"),
])
def test_changed_replay_is_rejected_before_model_loading(change, error):
    saved, fresh = replay_fixture()
    if change == "selection":
        saved["questions"][0]["arms"]["filtered_hybrid_diverse"]["chunk_ids"] = ["B::chunk-00001"]
    elif change == "query":
        saved["questions"][0]["query"] = "edited query"
    elif change == "binding":
        saved["source_trace_canonical_sha256"] = "another trace"
    elif change == "policy":
        saved["configuration"]["filter_policy_sha256"] = "changed"
        fresh["configuration"]["filter_policy_sha256"] = "changed"
    elif change == "group_metrics":
        saved["groups"]["A"]["metrics"]["filtered_hybrid_diverse"]["Hit@1"] = 0.5
    elif change == "duplicates":
        saved["questions"][1] = deepcopy(saved["questions"][0])
    elif change == "coverage":
        saved["questions"][0]["arms"]["filtered_hybrid_diverse"]["reference_coverage"] = 0
    with pytest.raises(ValueError, match=error):
        experiment.validate_saved_replay(saved, fresh)
