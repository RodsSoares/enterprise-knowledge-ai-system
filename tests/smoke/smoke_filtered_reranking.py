"""RV-013: real cross-encoder scoring on the frozen RV-012 filtered selection.

Retrieval is replayed from RV-011 vectors and the recorded chunk catalog.
No embedding requests or document parsing. --validate-only never loads a model.
"""

import argparse
from datetime import datetime, timezone
import json
from math import isclose
from pathlib import Path
from statistics import mean, median
from time import perf_counter

from app.retrieval.candidate_fusion import ReciprocalRankFusion
from app.retrieval.document_diversifier import DocumentDiversifier
from app.retrieval.lexical_index import BM25LexicalIndex
from app.retrieval.lexical_query_filter import FilteredLexicalRetriever
from app.retrieval.lexical_retriever import LexicalRetriever
from app.retrieval.prefix_preserving_selector import PrefixPreservingSelector
from app.retrieval.reranker import CandidateReranker
from tests.smoke.smoke_candidate_trace import require_equal_metrics, review_result, write_result
from tests.smoke.smoke_lexical_filter_replay import evaluate_selection, replay_trace, restore_catalog, restore_ranking
from tests.smoke.smoke_prefix_reranking_live import canonical_sha256, compare_metrics, load_inputs
from tests.smoke.smoke_reranking_experiment import fingerprints, installed_versions
from tests.smoke.smoke_reranking_replay import METRIC_NAMES, average


ARMS = ("filtered_only", "filtered_reranked", "filtered_prefix_preserved")
DEPTH, TOP_K, RRF_K = 20, 5, 60
FILTER_POLICY_SHA256 = "d179093e1bfeb461b3f52c70f8d4319337cc9c027bf9e37cdd3149838f06cd48"


def validate_saved_replay(saved, fresh):
    """Bind real inference to the already reviewed algorithm and exact selection."""
    if (saved.get("experiment") != "RV-012"
            or saved.get("status") != "OFFLINE_EXPLORATORY_REPLAY_COMPLETE"):
        raise ValueError("A completed RV-012 replay is required.")
    for key in ("source_trace_canonical_sha256", "source_live_canonical_sha256"):
        if saved[key] != fresh[key]:
            raise ValueError(f"RV-012 source binding changed: {key}")
    if (saved["configuration"] != fresh["configuration"]
            or fresh["configuration"]["filter_policy_sha256"] != FILTER_POLICY_SHA256):
        raise ValueError("RV-012 filter/configuration changed; define a new experiment.")
    expected = {q["question_id"]: q for q in fresh["questions"]}
    if (len(saved["questions"]) != len(expected)
            or {q["question_id"] for q in saved["questions"]} != set(expected)):
        raise ValueError("RV-012 question IDs are missing or duplicated.")
    for row in saved["questions"]:
        qid = row["question_id"]
        current = expected[qid]
        if any(row[key] != current[key] for key in ("group", "query", "expected_document_ids", "filtered_lexical_query")):
            raise ValueError(f"RV-012 question definition changed: {qid}")
        recorded_arm = row["arms"]["filtered_hybrid_diverse"]
        fresh_arm = current["arms"]["filtered_hybrid_diverse"]
        if recorded_arm["chunk_ids"] != fresh_arm["chunk_ids"]:
            raise ValueError(f"RV-012 filtered selection changed: {qid}")
        require_equal_metrics(fresh_arm["metrics"], recorded_arm["metrics"], qid)
        if "reference_coverage" in fresh_arm and not isclose(
                fresh_arm["reference_coverage"], recorded_arm["reference_coverage"], abs_tol=1e-9):
            raise ValueError(f"RV-012 reference coverage changed: {qid}")
    for group in ("A", "B"):
        require_equal_metrics(fresh["groups"][group]["metrics"]["filtered_hybrid_diverse"],
                              saved["groups"][group]["metrics"]["filtered_hybrid_diverse"], group)


def prepare_inputs(source_path, live_path, trace_path, challenge_path, replay_path):
    source, challenge, cached, cases_a, cases_b = load_inputs(source_path, challenge_path)
    live = json.loads(live_path.read_text(encoding="utf-8-sig"))
    trace = json.loads(trace_path.read_text(encoding="utf-8-sig"))
    saved_replay = json.loads(replay_path.read_text(encoding="utf-8-sig"))
    review_result(live, source, challenge, cached, cases_a, cases_b)
    fresh = replay_trace(trace, live, cases_a, cases_b, challenge)
    validate_saved_replay(saved_replay, fresh)
    chunks = restore_catalog(trace["chunk_catalog"])
    by_id = {c.chunk_id: c for c in chunks}
    index = BM25LexicalIndex()
    index.add([c.chunk_id for c in chunks], [c.text for c in chunks])
    lexical = FilteredLexicalRetriever(LexicalRetriever(index, chunks))
    fusion, diversity = ReciprocalRankFusion(RRF_K), DocumentDiversifier()
    traced = {q["question_id"]: q for q in trace["questions"]}
    replayed = {q["question_id"]: q for q in fresh["questions"]}
    prepared = []
    for group, cases in (("A", cases_a), ("B", cases_b)):
        for case in cases:
            qid, query = case["question_id"], case["query"]
            vector = restore_ranking(traced[qid]["stages"]["vector_full"], by_id, "vector", complete=True)
            fused = fusion.fuse((vector[:DEPTH], lexical.retrieve(query, top_k=DEPTH)), top_k=DEPTH)
            selection = diversity.select(fused, top_k=TOP_K)
            # Diversity renumbers ranks. Restore source RRF ranks and retain selection order.
            fused_by_id = {c.chunk.chunk_id: c for c in fused}
            baseline = tuple(fused_by_id[c.chunk.chunk_id] for c in selection)
            expected_ids = replayed[qid]["arms"]["filtered_hybrid_diverse"]["chunk_ids"]
            if [c.chunk.chunk_id for c in baseline] != expected_ids or len(baseline) != TOP_K:
                raise ValueError(f"Prepared selection disagrees with RV-012: {qid}")
            prepared.append((group, case, baseline))
    return source, trace, saved_replay, fresh, prepared


def score_case(case, baseline, scorer):
    """Exactly one real scorer call; the original query goes to the reranker."""
    if len(baseline) != TOP_K:
        raise ValueError("RV-013 scores exactly five selected chunks per question.")
    start = perf_counter()
    ranked = CandidateReranker(scorer).rerank(case["query"], baseline, top_k=TOP_K)
    elapsed = perf_counter() - start
    constrained = PrefixPreservingSelector(protected_documents=3).select(baseline, ranked)
    arms = {"filtered_only": baseline, "filtered_reranked": ranked, "filtered_prefix_preserved": constrained}
    pool = {c.chunk.chunk_id: {"document_id": c.chunk.document_id} for c in baseline}
    evaluated = {name: evaluate_selection(candidates, case, pool) for name, candidates in arms.items()}
    baseline_ids = evaluated["filtered_only"]["chunk_ids"]
    for name, result in evaluated.items():
        if set(result["chunk_ids"]) != set(baseline_ids):
            raise AssertionError(f"Scoring changed the selected evidence: {name}")
        if "reference_coverage" in result and result["reference_coverage"] != evaluated["filtered_only"]["reference_coverage"]:
            raise AssertionError("Reranking changed reference coverage at five.")
    if (set(evaluated["filtered_only"]["document_ids"][:3])
            != set(evaluated["filtered_prefix_preserved"]["document_ids"][:3])):
        raise AssertionError("Document prefix was not preserved.")
    per_case = {name: [metric for metric in METRIC_NAMES
        if evaluated[name]["metrics"][metric] < evaluated["filtered_only"]["metrics"][metric] - 1e-9]
        for name in ARMS[1:]}
    return {"question_id": case["question_id"], "query": case["query"],
        "expected_document_ids": case["expected_document_ids"],
        "score_seconds": elapsed, "scored_pairs": len(baseline), "arms": evaluated,
        "per_question_regressed_metrics": per_case,
        "scored_selection": [{"chunk_id": c.chunk.chunk_id, "document_id": c.chunk.document_id,
            "fusion_rank": c.source.rank, "fusion_score": c.source.score,
            "retrieval_methods": list(c.retrieval_methods), "rerank_rank": c.rerank_rank, "rerank_score": c.score,
            "text": c.chunk.text, "section_path": list(c.chunk.section_path),
            "source_path": c.chunk.source_path.as_posix(), "source_block_ids": list(c.chunk.source_block_ids),
            "page_numbers": list(c.chunk.page_numbers), "slide_numbers": list(c.chunk.slide_numbers),
            "sheet_names": list(c.chunk.sheet_names)} for c in ranked]}


def summarize(rows):
    metrics = {arm: average([row["arms"][arm]["metrics"] for row in rows]) for arm in ARMS}
    times = [row["score_seconds"] for row in rows]
    result = {"question_count": len(rows), "metrics": metrics,
        "comparisons": {arm: compare_metrics(metrics["filtered_only"], metrics[arm]) for arm in ARMS[1:]},
        "per_question_regressions": {arm: [{"question_id": row["question_id"], "metrics": row["per_question_regressed_metrics"][arm]}
            for row in rows if row["per_question_regressed_metrics"][arm]] for arm in ARMS[1:]},
        "scoring_latency_seconds": {"mean": mean(times), "median": median(times), "min": min(times), "max": max(times)}}
    if all("reference_coverage" in row["arms"]["filtered_only"] for row in rows):
        result["reference_coverage_at_5"] = {
            "macro_mean_all_arms": mean(row["arms"]["filtered_only"]["reference_coverage"] for row in rows),
            "fully_covered_questions": [row["question_id"] for row in rows if row["arms"]["filtered_only"]["reference_coverage"] == 1],
            "incomplete_questions": [row["question_id"] for row in rows if row["arms"]["filtered_only"]["reference_coverage"] < 1]}
    return result


def decide(groups, stable):
    """Require no aggregate loss; surface individual losses even if means improve."""
    if not stable:
        return "INPUT_CHANGED_DURING_RUN"
    arm = "filtered_prefix_preserved"
    if any(groups[g]["comparisons"][arm]["decision"] == "REGRESSION" for g in ("A", "B")):
        return "REGRESSION_KEEP_FILTER_ONLY"
    if any(groups[g]["per_question_regressions"][arm] for g in ("A", "B")):
        return "MIXED_RESULTS_REVIEW_REQUIRED"
    if any(groups[g]["comparisons"][arm]["decision"] == "IMPROVEMENT" for g in ("A", "B")):
        return "CANDIDATE_FOR_REVIEW"
    return "NO_MEASURED_GAIN_KEEP_FILTER_ONLY"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("docs/validation/RV008_RESULTS.json"))
    parser.add_argument("--live", type=Path, default=Path("docs/validation/RV010_LIVE_RESULTS.json"))
    parser.add_argument("--trace", type=Path, default=Path("docs/validation/RV011_CANDIDATE_TRACE.json"))
    parser.add_argument("--challenge", type=Path, default=Path("data/ground_truth/reranking_challenge_b.json"))
    parser.add_argument("--replay", type=Path, default=Path("docs/validation/RV012_LEXICAL_REPLAY_RESULTS_local.json"))
    parser.add_argument("--output", type=Path, default=Path("docs/validation/RV013_FILTERED_RERANK_RESULTS.json"))
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    inputs = [args.source, args.live, args.trace, args.challenge, args.replay]
    if args.output.resolve() in {path.resolve() for path in inputs}:
        parser.error("Output must not overwrite an input.")
    tracked = inputs + list(Path("app").rglob("*.py")) + list(Path("tests/smoke").glob("*.py"))
    before = fingerprints(tracked)
    source, trace, saved, replayed, prepared = prepare_inputs(*inputs)
    print("RV-013 inputs validated: A=13; B=12; five filtered chunks each; no new embeddings.", flush=True)
    for group in ("A", "B"):
        control = replayed["groups"][group]["metrics"]["filtered_hybrid_diverse"]
        print(f"Control {group}: Hit@1={control['Hit@1']:.4f}; Recall@5={control['Recall@5']:.4f}", flush=True)
    if args.validate_only:
        if before != fingerprints(tracked):
            raise ValueError("Inputs changed during validation.")
        print("VALIDATION_ONLY_COMPLETE; no model loaded and no inference results generated.")
        return

    from app.retrieval.cross_encoder_scorer import TransformersCrossEncoderScorer
    scorer = TransformersCrossEncoderScorer(source["configuration"]["model"],
        revision=source["configuration"]["revision"], device=args.device, batch_size=8, max_length=512)
    print("Loading the pinned local reranker...", flush=True)
    start = perf_counter()
    scorer.load()
    model_load_seconds = perf_counter() - start
    rows = []
    for group, case, baseline in prepared:
        row = score_case(case, baseline, scorer)
        row["group"] = group
        rows.append(row)
        print(f"{group}/{case['question_id']}: {row['score_seconds']:.2f}s; "
              f"control={','.join(row['arms']['filtered_only']['document_ids'])}; "
              f"constrained={','.join(row['arms']['filtered_prefix_preserved']['document_ids'])}", flush=True)
    groups = {g: summarize([row for row in rows if row["group"] == g]) for g in ("A", "B")}
    for g in ("A", "B"):
        require_equal_metrics(groups[g]["metrics"]["filtered_only"],
                              replayed["groups"][g]["metrics"]["filtered_hybrid_diverse"], g)
    stable = before == fingerprints(tracked)
    result = {"experiment": "RV-013", "status": "LIVE_RERANK_ON_FROZEN_RETRIEVAL_COMPLETE",
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "decision": decide(groups, stable),
        "automatically_promoted": False, "snapshot_stable": stable, "input_fingerprints": before,
        "configuration": {"retrieval_mode": "frozen RV-011 vectors + recomputed filtered BM25/RRF/diversity",
            "cross_encoder_mode": "real inference", "model": scorer.model_name, "revision": scorer.revision,
            "device": args.device, "batch_size": 8, "max_length": 512, "protected_documents": 3,
            "selected_chunks": TOP_K, "candidate_depth": DEPTH, "rrf_k": RRF_K,
            "filter_policy_sha256": FILTER_POLICY_SHA256, "rerank_text": "build_search_text(chunk)",
            "rerank_query": "original unfiltered query"},
        "provenance": {"rv012_saved_canonical_sha256": canonical_sha256(saved),
            "rv011_canonical_sha256": canonical_sha256(trace), "rv011_source_status": trace["status"],
            "rv011_drift_from_rv010": replayed["drift_from_rv010"], "rv012_filtered_selections_reproduced": True},
        "versions": installed_versions(), "model_load_seconds": model_load_seconds,
        "new_embedding_calls": 0, "cross_encoder_scoring_calls": len(rows),
        "cross_encoder_pairs": sum(row["scored_pairs"] for row in rows),
        "groups": groups, "questions": rows,
        "limits": ["Real reranker inference over replayed retrieval; not a fresh end-to-end retrieval run.",
            "A/B are development cases for this composition, not an independent test set.",
            "Fixed membership cannot repair missing B07/B11 reference passages.",
            "Raw relevance logits are not calibrated answer-confidence probabilities."]}
    for group, summary in groups.items():
        print(f"\nGroup {group} | n={summary['question_count']}")
        print(f"{'Metric':<12}" + "".join(f"{arm:>28}" for arm in ARMS))
        for metric in METRIC_NAMES:
            print(f"{metric:<12}" + "".join(f"{summary['metrics'][arm][metric]:>28.4f}" for arm in ARMS))
        print("Comparisons:", {arm: c["decision"] for arm, c in summary["comparisons"].items()})
        print("Individual regressions:", summary["per_question_regressions"])
        print("Scoring latency:", summary["scoring_latency_seconds"])
    write_result(args.output, result)
    print(f"RV-013: {result['decision']}; no automatic promotion.")


if __name__ == "__main__":
    main()
