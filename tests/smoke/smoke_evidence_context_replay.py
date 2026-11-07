"""RV-014: bounded evidence contexts over the frozen filtered retrieval pool.

Recomputes RV-013 rankings/metrics from saved scores and RV-011 inputs, then
compares five anchors with anchors plus supplementary passages. No model,
embedding, parser, or external API calls. Reference labels are evaluation only.
"""

import argparse
from dataclasses import asdict
import json
from math import isclose, isfinite
from numbers import Real
from pathlib import Path
from statistics import mean, median

from app.retrieval.candidate_fusion import ReciprocalRankFusion
from app.retrieval.document_diversifier import DocumentDiversifier
from app.retrieval.evidence_context import EvidenceContextBuilder
from app.retrieval.lexical_index import BM25LexicalIndex
from app.retrieval.lexical_query_filter import FilteredLexicalRetriever
from app.retrieval.lexical_retriever import LexicalRetriever
from app.retrieval.search_text import build_search_text
from tests.smoke.smoke_candidate_trace import review_result, write_result
from tests.smoke import smoke_filtered_reranking as rv013
from tests.smoke.smoke_lexical_filter_replay import (
    evaluate_selection, replay_trace, restore_catalog, restore_ranking,
)
from tests.smoke.smoke_prefix_reranking_live import canonical_sha256, load_inputs
from tests.smoke.smoke_reranking_experiment import fingerprints
from tests.smoke.smoke_reranking_replay import average


MAX_CHUNKS, MAX_CHARACTERS, MAX_ADDITIONAL_PER_DOCUMENT = 10, 12000, 1
CONTEXT_ARMS = ("anchors_only", "expanded_context")


def require_equivalent(actual, recorded, where):
    """Compare portable JSON values, allowing only small numeric roundoff."""
    if isinstance(actual, dict) and isinstance(recorded, dict):
        if set(actual) != set(recorded):
            raise ValueError(f"Recorded keys differ: {where}")
        for key in actual:
            require_equivalent(actual[key], recorded[key], f"{where}/{key}")
    elif isinstance(actual, list) and isinstance(recorded, list):
        if len(actual) != len(recorded):
            raise ValueError(f"Recorded length differs: {where}")
        for i, (a, b) in enumerate(zip(actual, recorded)):
            require_equivalent(a, b, f"{where}/{i}")
    elif (isinstance(actual, Real) and not isinstance(actual, bool)
          and isinstance(recorded, Real) and not isinstance(recorded, bool)):
        if not (isfinite(actual) and isfinite(recorded)
                and isclose(actual, recorded, rel_tol=1e-9, abs_tol=1e-9)):
            raise ValueError(f"Recorded number differs: {where}")
    elif type(actual) is not type(recorded) or actual != recorded:
        raise ValueError(f"Recorded value differs: {where}")


def require_seconds(value, where):
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value) or value < 0:
        raise ValueError(f"Invalid recorded latency: {where}")


class SavedScores:
    """Offline adapter only: validates scoring inputs and returns saved logits."""

    def __init__(self, query, baseline, rows):
        by_id = {row["chunk_id"]: row for row in rows}
        if len(by_id) != len(rows) or set(by_id) != {c.chunk.chunk_id for c in baseline}:
            raise ValueError("RV-013 scored selection is missing, duplicated, or changed.")
        self.query = query
        self.passages = tuple(build_search_text(c.chunk) for c in baseline)
        self.scores = tuple(by_id[c.chunk.chunk_id]["rerank_score"] for c in baseline)

    def score_pairs(self, query, passages):
        if query != self.query or tuple(passages) != self.passages:
            raise ValueError("RV-013 scoring inputs changed.")
        return self.scores


def audit_rv013(recorded, source, trace, replayed, prepared):
    if (recorded.get("experiment") != "RV-013"
            or recorded.get("status") != "LIVE_RERANK_ON_FROZEN_RETRIEVAL_COMPLETE"
            or recorded.get("snapshot_stable") is not True
            or recorded.get("automatically_promoted") is not False):
        raise ValueError("A stable, completed, unpromoted RV-013 artifact is required.")
    expected_configuration = {
        "retrieval_mode": "frozen RV-011 vectors + recomputed filtered BM25/RRF/diversity",
        "cross_encoder_mode": "real inference", "model": source["configuration"]["model"],
        "revision": source["configuration"]["revision"],
        "device": recorded["configuration"].get("device"),
        "batch_size": 8, "max_length": 512, "protected_documents": 3,
        "selected_chunks": rv013.TOP_K, "candidate_depth": rv013.DEPTH, "rrf_k": rv013.RRF_K,
        "filter_policy_sha256": rv013.FILTER_POLICY_SHA256,
        "rerank_text": "build_search_text(chunk)", "rerank_query": "original unfiltered query",
    }
    if not isinstance(expected_configuration["device"], str) or not expected_configuration["device"].strip():
        raise ValueError("RV-013 device is missing.")
    require_equivalent(expected_configuration, recorded["configuration"], "RV-013/configuration")
    provenance = recorded["provenance"]
    for key, expected in (
        ("rv011_canonical_sha256", canonical_sha256(trace)),
        ("rv011_source_status", trace["status"]),
        ("rv011_drift_from_rv010", replayed["drift_from_rv010"]),
        ("rv012_filtered_selections_reproduced", True),
    ):
        require_equivalent(expected, provenance[key], f"RV-013/provenance/{key}")
    saved = {row["question_id"]: row for row in recorded["questions"]}
    if (len(saved) != len(recorded["questions"])
            or set(saved) != {case["question_id"] for _, case, _, _ in prepared}):
        raise ValueError("RV-013 question IDs are missing or duplicated.")
    rows = []
    for group, case, baseline, _ in prepared:
        qid = case["question_id"]
        old = saved[qid]
        adapter = SavedScores(case["query"], baseline, old["scored_selection"])
        current = rv013.score_case(case, baseline, adapter)
        # Retain measured Windows latencies; replay time is not inference time.
        require_seconds(old["score_seconds"], qid)
        current["score_seconds"] = old["score_seconds"]
        current["group"] = group
        require_equivalent(current, old, f"RV-013/{qid}")
        rows.append(current)
    groups = {g: rv013.summarize([row for row in rows if row["group"] == g]) for g in ("A", "B")}
    require_equivalent(groups, recorded["groups"], "RV-013/groups")
    require_equivalent(rv013.decide(groups, True), recorded["decision"], "RV-013/decision")
    for key, expected in (("new_embedding_calls", 0), ("cross_encoder_scoring_calls", len(rows)),
                          ("cross_encoder_pairs", len(rows) * rv013.TOP_K)):
        require_equivalent(expected, recorded[key], f"RV-013/{key}")
    require_seconds(recorded["model_load_seconds"], "model load")
    return {"source_canonical_sha256": canonical_sha256(recorded),
        "rankings_metrics_and_passage_provenance_reproduced": True,
        "decision": recorded["decision"], "groups": groups,
        "recorded_model_load_seconds": recorded["model_load_seconds"],
        "rv012_controls_recomputed_from_rv011": True,
        "rv012_saved_file_hash_revalidated": False,
        "note": "RV-012 controls are recomputed; no equality claim about a local RV-012 file or new model inference."}


def prepare_pools(trace, cases_a, cases_b, replayed):
    chunks = restore_catalog(trace["chunk_catalog"])
    by_id = {c.chunk_id: c for c in chunks}
    index = BM25LexicalIndex()
    index.add([c.chunk_id for c in chunks], [c.text for c in chunks])
    lexical = FilteredLexicalRetriever(LexicalRetriever(index, chunks))
    fusion, diversity = ReciprocalRankFusion(rv013.RRF_K), DocumentDiversifier()
    traced = {q["question_id"]: q for q in trace["questions"]}
    replayed_rows = {q["question_id"]: q for q in replayed["questions"]}
    prepared = []
    for group, cases in (("A", cases_a), ("B", cases_b)):
        for case in cases:
            qid = case["question_id"]
            vector = restore_ranking(traced[qid]["stages"]["vector_full"], by_id, "vector", complete=True)
            pool = fusion.fuse((vector[:rv013.DEPTH], lexical.retrieve(case["query"], rv013.DEPTH)), rv013.DEPTH)
            by_pool_id = {c.chunk.chunk_id: c for c in pool}
            selected = diversity.select(pool, rv013.TOP_K)
            anchors = tuple(by_pool_id[c.chunk.chunk_id] for c in selected)
            expected = replayed_rows[qid]["arms"]["filtered_hybrid_diverse"]["chunk_ids"]
            require_equivalent(expected, [c.chunk.chunk_id for c in anchors], f"RV-012/control/{qid}")
            prepared.append((group, case, anchors, pool))
    return prepared


def evaluate_context(context, reference_groups):
    """Reference labels are consulted only after context selection and rendering."""
    ids = [passage.chunk.chunk_id for passage in context.passages]
    result = {"chunk_ids": ids, "passage_count": len(ids),
        "selected_document_ids": list(context.selected_document_ids),
        "rendered_characters": context.character_count, "rendered_context": context.text,
        "citations": context.citations,
        "passage_provenance": [{"citation_id": p.citation_id, "role": p.role,
            "chunk_id": p.chunk.chunk_id, "fusion_rank": p.source.rank,
            "fusion_score": p.source.score, "retrieval_methods": list(p.source.retrieval_methods)}
            for p in context.passages],
        "skipped": [asdict(item) for item in context.skipped]}
    if reference_groups:
        found = [bool(set(ref["any_of_chunk_ids"]) & set(ids)) for ref in reference_groups]
        result["reference_coverage_in_context"] = sum(found) / len(found)
        result["reference_groups_found"] = sum(found)
        result["reference_groups_total"] = len(found)
        result["missing_reference_groups"] = [ref for ref, hit in zip(reference_groups, found) if not hit]
    return result


def context_case(case, anchors, pool, control_builder, expanded_builder):
    # Neither builder receives the question, expected documents, or reference labels.
    small = control_builder.build(anchors, pool)
    large = expanded_builder.build(anchors, pool)
    anchor_ids = [c.chunk.chunk_id for c in anchors]
    if [p.chunk.chunk_id for p in large.passages[:len(anchors)]] != anchor_ids:
        raise AssertionError("Context assembly changed the selected anchors/order.")
    if small.selected_document_ids != large.selected_document_ids:
        raise AssertionError("Context assembly changed the selected documents.")
    references = case.get("reference_passage_groups", [])
    contexts = {name: evaluate_context(context, references)
        for name, context in zip(CONTEXT_ARMS, (small, large))}
    if references and (contexts["expanded_context"]["reference_coverage_in_context"]
                       < contexts["anchors_only"]["reference_coverage_in_context"]):
        raise AssertionError("Expanded context lost an anchor reference.")
    pool_metadata = {c.chunk.chunk_id: {"document_id": c.chunk.document_id} for c in pool}
    return {"question_id": case["question_id"], "query": case["query"],
        "expected_document_ids": case["expected_document_ids"],
        "retrieval_at_5": evaluate_selection(anchors, case, pool_metadata),
        "anchors_preserved_in_order": True, "contexts": contexts}


def statistics(values):
    return {"mean": mean(values), "median": median(values), "min": min(values), "max": max(values)}


def summarize_contexts(rows):
    contexts = {arm: {"passage_count": statistics([r["contexts"][arm]["passage_count"] for r in rows]),
        "rendered_characters": statistics([r["contexts"][arm]["rendered_characters"] for r in rows])}
        for arm in CONTEXT_ARMS}
    if all("reference_coverage_in_context" in row["contexts"]["anchors_only"] for row in rows):
        for arm in CONTEXT_ARMS:
            contexts[arm]["reference_passages"] = {
                "macro_coverage": mean(row["contexts"][arm]["reference_coverage_in_context"] for row in rows),
                "groups_found": sum(row["contexts"][arm]["reference_groups_found"] for row in rows),
                "groups_total": sum(row["contexts"][arm]["reference_groups_total"] for row in rows),
                "fully_covered_questions": [row["question_id"] for row in rows
                    if row["contexts"][arm]["reference_coverage_in_context"] == 1]}
    return {"question_count": len(rows), "retrieval_at_5_unchanged": True,
        "retrieval_metrics_at_5": average([row["retrieval_at_5"]["metrics"] for row in rows]),
        "contexts": contexts,
        "total_rendered_character_ratio": sum(r["contexts"]["expanded_context"]["rendered_characters"] for r in rows)
            / sum(r["contexts"]["anchors_only"]["rendered_characters"] for r in rows)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("docs/validation/RV008_RESULTS.json"))
    parser.add_argument("--live", type=Path, default=Path("docs/validation/RV010_LIVE_RESULTS.json"))
    parser.add_argument("--trace", type=Path, default=Path("docs/validation/RV011_CANDIDATE_TRACE.json"))
    parser.add_argument("--rerank", type=Path, default=Path("docs/validation/RV013_FILTERED_RERANK_RESULTS.json"))
    parser.add_argument("--challenge", type=Path, default=Path("data/ground_truth/reranking_challenge_b.json"))
    parser.add_argument("--output", type=Path, default=Path("docs/validation/RV014_CONTEXT_REPLAY_RESULTS.json"))
    args = parser.parse_args(argv)
    inputs = [args.source, args.live, args.trace, args.rerank, args.challenge]
    tracked = inputs + list(Path("app").rglob("*.py")) + list(Path("tests/smoke").glob("*.py"))
    if args.output.resolve() in {path.resolve() for path in tracked}:
        parser.error("Output must not overwrite an input or implementation file.")
    before = fingerprints(tracked)
    source, challenge, cached, cases_a, cases_b = load_inputs(args.source, args.challenge)
    live, trace, rerank = [json.loads(path.read_text(encoding="utf-8-sig"))
                           for path in (args.live, args.trace, args.rerank)]
    review_result(live, source, challenge, cached, cases_a, cases_b)
    replayed = replay_trace(trace, live, cases_a, cases_b, challenge)
    if replayed["configuration"]["filter_policy_sha256"] != rv013.FILTER_POLICY_SHA256:
        raise ValueError("RV-012 filter policy changed; define a new experiment.")
    prepared = prepare_pools(trace, cases_a, cases_b, replayed)
    audit = audit_rv013(rerank, source, trace, replayed, prepared)
    print(f"RV-013 audited from saved scores: {audit['decision']}; no model inference.")
    control = EvidenceContextBuilder(max_chunks=5, max_characters=MAX_CHARACTERS, max_additional_per_document=0)
    expanded = EvidenceContextBuilder(max_chunks=MAX_CHUNKS, max_characters=MAX_CHARACTERS,
                                      max_additional_per_document=MAX_ADDITIONAL_PER_DOCUMENT)
    rows = []
    for group, case, anchors, pool in prepared:
        row = context_case(case, anchors, pool, control, expanded)
        row["group"] = group
        rows.append(row)
    groups = {g: summarize_contexts([r for r in rows if r["group"] == g]) for g in ("A", "B")}
    if before != fingerprints(tracked):
        raise ValueError("Inputs or implementation changed during replay.")
    result = {"experiment": "RV-014", "status": "OFFLINE_CONTEXT_REPLAY_COMPLETE",
        "decision": "CONTEXT_CANDIDATE_FOR_REVIEW", "automatically_promoted": False,
        "snapshot_stable": True, "input_fingerprints": before,
        "configuration": {"candidate_depth": rv013.DEPTH, "anchor_chunks": rv013.TOP_K,
            "max_chunks": MAX_CHUNKS, "max_characters": MAX_CHARACTERS,
            "max_additional_per_document": MAX_ADDITIONAL_PER_DOCUMENT,
            "addition_order": "original fusion rank; only already selected documents",
            "rendering": "JSON evidence with citation locations; source text untruncated",
            "budget_unit": "Unicode characters including rendered metadata; not model tokens"},
        "source_trace_status": trace["status"], "source_trace_canonical_sha256": canonical_sha256(trace),
        "drift_from_rv010": replayed["drift_from_rv010"], "rv013_audit": audit,
        "new_embedding_calls": 0, "new_model_inference_calls": 0,
        "groups": groups, "overall": summarize_contexts(rows), "questions": rows,
        "limits": ["A/B are development cases; no independent holdout or generated answers were evaluated.",
            "Expansion uses more passages and characters, not an improvement at the same five-chunk budget.",
            "Reference labels are non-exhaustive; coverage does not prove answer correctness or citation entailment.",
            "JSON serialization is not a prompt-injection security boundary.",
            "Source location metadata does not enforce permissions, effective dates, or policy precedence.",
            "Missing reference labels in A mean passage coverage is unmeasured there.",
            "Citation IDs are local to one context; no automatic configuration promotion."]}
    for group, summary in groups.items():
        print(f"\nGroup {group} | n={summary['question_count']} | original top-5 unchanged")
        for arm in CONTEXT_ARMS:
            context = summary["contexts"][arm]
            message = (f"{arm}: mean chunks={context['passage_count']['mean']:.2f}; "
                       f"mean characters={context['rendered_characters']['mean']:.0f}")
            if "reference_passages" in context:
                refs = context["reference_passages"]
                message += (f"; reference coverage={refs['macro_coverage']:.4f}; "
                            f"groups={refs['groups_found']}/{refs['groups_total']}")
            print(message)
    write_result(args.output, result)
    print("RV-014: CONTEXT_CANDIDATE_FOR_REVIEW; zero new model/embedding calls; no automatic promotion.")


if __name__ == "__main__":
    main()
