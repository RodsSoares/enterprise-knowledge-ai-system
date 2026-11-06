"""Offline replay invariants and metric-consistency checks."""

from copy import deepcopy

import pytest

from tests.smoke.smoke_reranking_replay import assess, average, question_metrics, reorder_ids, replay


def fixture():
    pool = {letter: {"chunk_id": letter, "document_id": "DOC-" + letter,
                    "rerank_score": score}
            for letter, score in zip("abcde", (2.0, 5.0, 1.0, 8.0, 7.0))}
    ids = list(pool)
    metrics = question_metrics(ids, pool, ["DOC-b", "DOC-e"])
    source = {
        "experiment": "RV-008", "status": "EXPERIMENT_COMPLETE", "snapshot_stable": True,
        "metric_scope": "unique-document ranking", "configuration": {"top_k": 5, "positive_questions": 1},
        "metrics": {"hybrid_v03": metrics}, "frozen_v03_metrics": metrics,
        "questions": [{"question_id": "QX", "query": "query", "expected_document_ids": ["DOC-b", "DOC-e"],
                       "reranked_pool": list(pool.values()), "final_chunk_ids": {"hybrid_v03": ids}}],
    }
    return pool, source


def test_global_sort_and_banded_sort_have_distinct_membership_invariants():
    pool, _ = fixture()
    baseline = list(pool)
    assert reorder_ids(baseline, pool, "fixed_top5") == tuple("debac")
    constrained = reorder_ids(baseline, pool, "preserve_top3_and_top5")
    assert constrained == tuple("bacde")
    assert set(constrained[:3]) == set(baseline[:3])
    assert set(constrained) == set(baseline)


def test_ties_preserve_baseline_order_inside_each_band():
    pool, _ = fixture()
    for item in pool.values():
        item["rerank_score"] = -2.0
    for policy in ("fixed_top5", "preserve_top3_and_top5"):
        assert reorder_ids(list("baced"), pool, policy) == tuple("baced")


@pytest.mark.parametrize("score", [float("nan"), float("inf"), True, "0.5"])
def test_invalid_cached_scores_rejected(score):
    pool, _ = fixture()
    pool["b"]["rerank_score"] = score
    with pytest.raises(ValueError, match="score"):
        reorder_ids(list(pool), pool, "fixed_top5")


@pytest.mark.parametrize("ids", [[], ["a", "a"], ["a", "z"], list("abcdef")])
def test_invalid_candidate_selection_rejected(ids):
    pool, _ = fixture()
    with pytest.raises(ValueError):
        reorder_ids(ids, pool, "fixed_top5")


def test_document_duplicates_rejected_for_document_prefix_constraint():
    pool, _ = fixture()
    pool["b"]["document_id"] = pool["a"]["document_id"]
    with pytest.raises(ValueError, match="distinct"):
        reorder_ids(list(pool), pool, "preserve_top3_and_top5")


def test_metric_definition_deduplicates_documents_like_original_evaluator():
    pool, _ = fixture()
    pool["b"]["document_id"] = "DOC-a"
    values = question_metrics(list("abcde"), pool, ["DOC-c", "DOC-e"])
    assert values["MRR"] == 0.5
    assert values["Recall@3"] == 0.5
    assert values["Recall@5"] == 1.0


def test_replay_reproduces_source_and_never_mutates_input():
    _, source = fixture()
    original = deepcopy(source)
    result = replay(source)
    assert source == original
    assert result["source_metrics_reproduced"] is True
    assert result["api_calls"] == result["model_inference_calls"] == 0
    assert result["replay_metrics"]["preserve_top3_and_top5"]["Recall@3"] == 0.5
    assert result["replay_metrics"]["preserve_top3_and_top5"]["Recall@5"] == 1


def test_expected_documents_do_not_influence_ordering():
    _, source = fixture()
    first = replay(source)
    source["questions"][0]["expected_document_ids"] = ["DOC-d"]
    pool = {item["chunk_id"]: item for item in source["questions"][0]["reranked_pool"]}
    values = question_metrics(list(pool), pool, ["DOC-d"])
    source["metrics"]["hybrid_v03"] = values
    source["frozen_v03_metrics"] = values
    second = replay(source)
    for policy in first["replay_metrics"]:
        assert first["questions"][0]["policies"][policy]["chunk_ids"] == second["questions"][0]["policies"][policy]["chunk_ids"]


def test_source_metric_inconsistency_stops_replay():
    _, source = fixture()
    source["metrics"]["hybrid_v03"] = dict(source["metrics"]["hybrid_v03"], MRR=0.2)
    with pytest.raises(ValueError, match="metric mismatch"):
        replay(source)


def test_unstable_source_is_rejected():
    _, source = fixture()
    source["snapshot_stable"] = False
    with pytest.raises(ValueError, match="unstable"):
        replay(source)


def test_same_average_gate_is_applied_without_relaxing_recall_at_3():
    _, source = fixture()
    baseline = source["metrics"]["hybrid_v03"]
    degraded = dict(baseline, **{"Hit@1": 1, "Recall@3": 0})
    result = assess(baseline, degraded)
    assert result["decision"] == "REGRESSION"
    assert result["automatically_promoted"] is False
    improved = dict(baseline, **{"Hit@1": 1, "MRR": 1})
    assert assess(baseline, improved)["decision"] == "EXPLORATORY_CANDIDATE"
    assert average([baseline, improved])["MRR"] == 0.75
