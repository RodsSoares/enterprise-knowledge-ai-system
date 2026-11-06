"""RV-009: offline replay of cached RV-008 scores; no model/API calls.

Experiments are exploratory on Golden Set A, not held-out validation.
Run: python -m tests.smoke.smoke_reranking_replay
"""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from math import fsum, isclose, isfinite
from numbers import Real
from pathlib import Path


METRIC_NAMES = ("Hit@1", "Hit@3", "Hit@5", "Recall@1", "Recall@3", "Recall@5", "MRR")
POLICIES = ("fixed_top5", "preserve_top3_and_top5")


def reorder_ids(baseline_ids, pool, policy):
    """Ordering has no access to questions, answer keys or expected documents."""
    if policy not in POLICIES:
        raise ValueError(f"Unknown policy: {policy}")
    ids = tuple(baseline_ids)
    if not ids or len(ids) > 5 or len(ids) != len(set(ids)):
        raise ValueError("The baseline must contain 1-5 unique chunk IDs.")
    for cid in ids:
        if cid not in pool:
            raise ValueError(f"Missing cached candidate: {cid}")
        score = pool[cid]["rerank_score"]
        if isinstance(score, bool) or not isinstance(score, Real) or not isfinite(score):
            raise ValueError(f"Invalid cached score for {cid}")
    if policy == "preserve_top3_and_top5":
        # RV-007/008 evaluate a deduplicated document ranking. Enforce the
        # distinct-document precondition so chunk bands preserve those cutoffs.
        docs = [pool[cid]["document_id"] for cid in ids]
        if len(docs) != len(set(docs)):
            raise ValueError("The constrained policy requires distinct baseline documents.")
        bands = (ids[:3], ids[3:])
    else:
        bands = (ids,)
    return tuple(cid for band in bands
                 for cid in sorted(band, key=lambda cid: -pool[cid]["rerank_score"]))


def question_metrics(chunk_ids, pool, expected_document_ids):
    """Match RV-008: unique-document first-occurrence rank from final chunks."""
    expected = set(expected_document_ids)
    if not expected:
        raise ValueError("Positive retrieval evaluation requires expected documents.")
    docs = tuple(dict.fromkeys(pool[cid]["document_id"] for cid in chunk_ids))
    result = {}
    for k in (1, 3, 5):
        found = expected.intersection(docs[:k])
        result[f"Hit@{k}"] = float(bool(found))
        result[f"Recall@{k}"] = len(found) / len(expected)
    result["MRR"] = next((1 / rank for rank, doc in enumerate(docs, 1) if doc in expected), 0.0)
    return result


def average(rows):
    if not rows:
        raise ValueError("No positive questions to evaluate.")
    return {name: fsum(row[name] for row in rows) / len(rows) for name in METRIC_NAMES}


def assess(baseline, candidate):
    regressions = [name for name in METRIC_NAMES if candidate[name] < baseline[name] - 1e-9]
    improvements = [name for name in ("Hit@1", "MRR") if candidate[name] > baseline[name] + 1e-9]
    decision = ("REGRESSION" if regressions else "EXPLORATORY_CANDIDATE"
                if improvements else "NO_FIRST_RANK_GAIN")
    return {"decision": decision, "regressed_metrics": regressions,
            "improved_first_rank_metrics": improvements,
            "held_out_validation": False, "automatically_promoted": False}


def replay(source):
    if source.get("experiment") != "RV-008" or source.get("status") != "EXPERIMENT_COMPLETE":
        raise ValueError("A completed RV-008 artifact is required.")
    if source.get("snapshot_stable") is not True:
        raise ValueError("The source reports an unstable snapshot.")
    if source["configuration"]["top_k"] != 5:
        raise ValueError("This experiment is defined for Top-5 selection.")
    questions = source["questions"]
    if len(questions) != source["configuration"]["positive_questions"]:
        raise ValueError("Question count differs from the source configuration.")
    seen_qids = set()
    recorded = {label: [] for label in source["metrics"]}
    rows = {policy: [] for policy in POLICIES}
    details = []
    for question in questions:
        qid = question["question_id"]
        if qid in seen_qids:
            raise ValueError(f"Duplicate question ID: {qid}")
        seen_qids.add(qid)
        pool = {item["chunk_id"]: item for item in question["reranked_pool"]}
        if len(pool) != len(question["reranked_pool"]):
            raise ValueError(f"{qid}: duplicate cached chunk ID")
        expected = question["expected_document_ids"]
        for label in recorded:
            ids = question["final_chunk_ids"][label]
            if len(ids) > 5 or len(ids) != len(set(ids)):
                raise ValueError(f"{qid}: invalid final candidate IDs for {label}")
            recorded[label].append(question_metrics(ids, pool, expected))
        baseline_ids = tuple(question["final_chunk_ids"]["hybrid_v03"])
        baseline_metrics = question_metrics(baseline_ids, pool, expected)
        detail = {"question_id": qid, "query": question["query"],
                  "expected_document_ids": expected,
                  "baseline_chunk_ids": baseline_ids,
                  "baseline_metrics": baseline_metrics, "policies": {}}
        for policy in POLICIES:
            ordered = reorder_ids(baseline_ids, pool, policy)
            values = question_metrics(ordered, pool, expected)
            rows[policy].append(values)
            if set(ordered) != set(baseline_ids):
                raise AssertionError("Replay changed selection membership.")
            detail["policies"][policy] = {
                "chunk_ids": ordered,
                "document_ids": [pool[cid]["document_id"] for cid in ordered],
                "cached_scores": [pool[cid]["rerank_score"] for cid in ordered],
                "metrics": values,
                "deltas": {name: values[name] - baseline_metrics[name] for name in METRIC_NAMES},
                "top5_membership_preserved": True,
                "top3_membership_preserved": set(ordered[:3]) == set(baseline_ids[:3]),
            }
        details.append(detail)

    # Recompute all original arms before trusting any comparison.
    reproduced = {label: average(values) for label, values in recorded.items()}
    for label, values in reproduced.items():
        for name in METRIC_NAMES:
            if not isclose(values[name], source["metrics"][label][name], rel_tol=0, abs_tol=1e-9):
                raise ValueError(f"Source metric mismatch: {label}/{name}")
    baseline = reproduced["hybrid_v03"]
    for name in METRIC_NAMES:
        if not isclose(baseline[name], source["frozen_v03_metrics"][name], rel_tol=0, abs_tol=1e-9):
            raise ValueError(f"Frozen baseline mismatch: {name}")
    replay_metrics = {policy: average(values) for policy, values in rows.items()}
    return {
        "experiment": "RV-009", "status": "OFFLINE_EXPLORATORY_REPLAY_COMPLETE",
        "metric_scope": source["metric_scope"],
        "source_metrics_reproduced": True, "api_calls": 0, "model_inference_calls": 0,
        "source_configuration": deepcopy(source["configuration"]),
        "source_metrics": reproduced, "replay_metrics": replay_metrics,
        "assessments": {policy: assess(baseline, values) for policy, values in replay_metrics.items()},
        "latency": {"new_model_inference_measured": False,
                    "note": "Cached 20-candidate scores do not measure a live 5-candidate run."},
        "methodology": {
            "fixed_top5": "Sort the same five baseline chunks by cached reranker score.",
            "preserve_top3_and_top5": "Sort baseline positions 1-3 and 4-5 separately.",
            "tie_breaker": "Stable order inside the original baseline band.",
            "selection_uses_expected_evidence": False,
            "exploratory_design": "The prefix restriction was added after observing fixed_top5 Recall@3 regression.",
            "limitations": ["Same 13-question development set; no independent validation.",
                "The constrained policy prevents positions 4-5 from reaching positions 1-3.",
                "Preserved document IDs do not prove complete or authoritative passage evidence.",
                "Cached logits can differ slightly from a future live batch configuration."],
        },
        "questions": details,
    }


def audit_tokenization(source, tokenizer_path):
    """Optional audit of the exact tokenizer JSON; tokenization only, no model."""
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    tokenizer.no_truncation()
    rows = []
    limit = source["configuration"]["max_length"]
    for question in source["questions"]:
        for item in question["reranked_pool"]:
            sections = item["section_path"]
            passage = ("Section: " + " > ".join(sections) + "\n\n" if sections else "") + item["text"]
            count = len(tokenizer.encode(question["query"], passage).ids)
            rows.append({"question_id": question["question_id"], "chunk_id": item["chunk_id"],
                         "pair_tokens_including_special_tokens": count, "exceeds_limit": count > limit})
    return {
        "method": "Replay tokenizer JSON encoding with the recorded query and build_search_text representation.",
        "runtime_input_capture": False,
        "tokenizers_version": version("tokenizers"),
        "tokenizer_sha256": hashlib.sha256(Path(tokenizer_path).read_bytes()).hexdigest(),
        "model": source["configuration"]["model"], "revision": source["configuration"]["revision"],
        "pair_count": len(rows), "max_length": limit,
        "maximum_observed_pair_tokens": max(row["pair_tokens_including_special_tokens"] for row in rows),
        "pairs_exceeding_limit": sum(row["exceeds_limit"] for row in rows), "pairs": rows,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("docs/validation/RV008_RESULTS.json"))
    parser.add_argument("--output", type=Path, default=Path("docs/validation/RV009_REPLAY_RESULTS.json"))
    parser.add_argument("--tokenizer-json", type=Path,
                        help="Optional local tokenizer.json from the source model's pinned revision")
    args = parser.parse_args(argv)
    if args.input.resolve() == args.output.resolve():
        parser.error("Input and output must differ; the RV-008 source is immutable.")
    raw = args.input.read_bytes()
    source = json.loads(raw.decode("utf-8-sig"))
    result = replay(source)
    result["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    result["source_artifact"] = {"name": args.input.name, "sha256": hashlib.sha256(raw).hexdigest()}
    if args.tokenizer_json:
        result["tokenization_audit"] = audit_tokenization(source, args.tokenizer_json)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    values = {"hybrid_v03": result["source_metrics"]["hybrid_v03"], **result["replay_metrics"]}
    print(f"{'Metric':<12}" + "".join(f"{label:>27}" for label in values))
    for name in METRIC_NAMES:
        print(f"{name:<12}" + "".join(f"{metrics[name]:>27.4f}" for metrics in values.values()))
    for policy, assessment in result["assessments"].items():
        print(f"{policy}: {assessment['decision']}")
    print(f"Saved: {args.output}")
    print("Exploratory replay; no API/model inference calls and no production promotion.")


if __name__ == "__main__":
    main()
