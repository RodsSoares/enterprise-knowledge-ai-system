"""RV-012: paired offline lexical-filter replay over the complete RV-011 trace.

No embedding requests, cross-encoder scoring, or production promotion.
All alternatives are exploratory after examining A/B, not independent validation.
"""

import argparse
import hashlib
import json
from math import isclose, isfinite
from numbers import Real
from pathlib import Path
from statistics import mean

from app.chunking.schemas import RetrievalChunk
from app.retrieval.candidate_fusion import ReciprocalRankFusion
from app.retrieval.document_diversifier import DocumentDiversifier
from app.retrieval.lexical_index import BM25LexicalIndex, tokenize
from app.retrieval.lexical_query_filter import FILTER_VERSION, FUNCTION_WORDS, FilteredLexicalRetriever, filter_lexical_query
from app.retrieval.lexical_retriever import LexicalRetriever
from app.retrieval.schemas import RetrievalCandidate
from tests.smoke.smoke_candidate_trace import capture_stages, diagnose_target, review_result, serialize_stages, write_result
from tests.smoke.smoke_prefix_reranking_live import canonical_sha256, compare_metrics, load_inputs, validate_reference_passages
from tests.smoke.smoke_reranking_experiment import fingerprints
from tests.smoke.smoke_reranking_replay import METRIC_NAMES, average, question_metrics


ARMS = ("hybrid_v03", "vector_diverse", "filtered_hybrid_diverse", "filtered_hybrid_top5")
DEPTH, TOP_K, RRF_K = 20, 5, 60


def restore_catalog(records):
    """Reconstruct scoring inputs; trace_text marks unavailable content-type metadata."""
    chunks = []
    seen = set()
    for item in records:
        cid = item["chunk_id"]
        if cid in seen or not cid.startswith(item["document_id"] + "::chunk-"):
            raise ValueError(f"Invalid or duplicate catalog identity: {cid}")
        seen.add(cid)
        if hashlib.sha256(item["text"].encode("utf-8")).hexdigest() != item["text_sha256"]:
            raise ValueError(f"Catalog text hash mismatch: {cid}")
        chunks.append(RetrievalChunk(chunk_id=cid, document_id=item["document_id"],
            order=item["order"], text=item["text"], source_path=Path(item["source_path"]),
            source_block_ids=tuple(item["source_block_ids"]), section_path=tuple(item["section_path"]),
            page_numbers=tuple(item["page_numbers"]), slide_numbers=tuple(item["slide_numbers"]),
            sheet_names=tuple(item["sheet_names"]), content_types=("trace_text",)))
    return tuple(chunks)


def restore_ranking(records, by_id, method, complete=False):
    ids = [item["chunk_id"] for item in records]
    if len(set(ids)) != len(ids) or (complete and set(ids) != set(by_id)):
        raise ValueError(f"Incomplete or duplicate {method} ranking.")
    previous = float("inf")
    result = []
    for rank, item in enumerate(records, 1):
        cid, score = item["chunk_id"], item["score"]
        if (cid not in by_id or item["document_id"] != by_id[cid].document_id
                or type(item["rank"]) is not int or item["rank"] != rank):
            raise ValueError(f"Invalid {method} identity or rank: {cid}")
        if (isinstance(score, bool) or not isinstance(score, Real) or not isfinite(score)
                or score > previous or (method == "lexical" and score <= 0)):
            raise ValueError(f"Invalid {method} score or ordering: {cid}")
        previous = score
        result.append(RetrievalCandidate(by_id[cid], method, score, rank))
    return tuple(result)


def verify_ranking(actual, recorded, context):
    if len(actual) != len(recorded):
        raise ValueError(f"Ranking length mismatch: {context}")
    for candidate, row in zip(actual, recorded):
        if (candidate.chunk.chunk_id != row["chunk_id"] or candidate.chunk.document_id != row["document_id"]
                or candidate.rank != row["rank"]
                or not isclose(candidate.score, row["score"], rel_tol=1e-9, abs_tol=1e-9)):
            raise ValueError(f"Ranking or score mismatch: {context}/{row['chunk_id']}")


def build_arms(vector, raw_lexical, filtered_lexical):
    """Rank without labels; only fixed algorithm alternatives enter this function."""
    fusion, diversify = ReciprocalRankFusion(RRF_K), DocumentDiversifier()
    baseline = fusion.fuse((vector[:DEPTH], raw_lexical[:DEPTH]), top_k=DEPTH)
    vector_only = fusion.fuse((vector[:DEPTH],), top_k=DEPTH)
    filtered = fusion.fuse((vector[:DEPTH], filtered_lexical[:DEPTH]), top_k=DEPTH)
    return {"hybrid_v03": diversify.select(baseline, TOP_K),
            "vector_diverse": diversify.select(vector_only, TOP_K),
            "filtered_hybrid_diverse": diversify.select(filtered, TOP_K),
            "filtered_hybrid_top5": filtered[:TOP_K]}


def evaluate_selection(candidates, case, pool):
    ids = [candidate.chunk.chunk_id for candidate in candidates]
    result = {"chunk_ids": ids,
        "document_ids": list(dict.fromkeys(pool[cid]["document_id"] for cid in ids)),
        "metrics": question_metrics(ids, pool, case["expected_document_ids"])}
    references = case.get("reference_passage_groups")
    if references:
        covered = [bool(set(ref["any_of_chunk_ids"]) & set(ids)) for ref in references]
        result["reference_groups_found"] = sum(covered)
        result["reference_groups_total"] = len(covered)
        result["reference_coverage"] = sum(covered) / len(covered)
        result["missing_reference_groups"] = [ref for ref, hit in zip(references, covered) if not hit]
    return result


def summarize(rows):
    metrics = {arm: average([row["arms"][arm]["metrics"] for row in rows]) for arm in ARMS}
    result = {"question_count": len(rows), "metrics": metrics,
        "comparisons": {arm: compare_metrics(metrics["hybrid_v03"], metrics[arm]) for arm in ARMS[1:]}}
    if all("reference_coverage" in row["arms"]["hybrid_v03"] for row in rows):
        result["reference_passages"] = {arm: {
            "macro_coverage": mean(row["arms"][arm]["reference_coverage"] for row in rows),
            "groups_found": sum(row["arms"][arm]["reference_groups_found"] for row in rows),
            "groups_total": sum(row["arms"][arm]["reference_groups_total"] for row in rows),
            "fully_covered_questions": [row["question_id"] for row in rows if row["arms"][arm]["reference_coverage"] == 1]}
            for arm in ARMS}
    return result


def replay_trace(trace, live, cases_a, cases_b, challenge):
    if (trace.get("experiment") != "RV-011" or trace.get("snapshot_stable") is not True
            or trace.get("status") not in ("TRACE_COMPLETE", "BASELINE_DRIFT")):
        raise ValueError("A stable completed RV-011 trace is required.")
    expected_config = {"candidate_depth": DEPTH, "selected_chunks": TOP_K, "rrf_k": RRF_K,
        "embedding_model": "text-embedding-3-small", "lexical_text": "chunk.text", "chunk_count": 79}
    if any(trace["configuration"].get(key) != value for key, value in expected_config.items()):
        raise ValueError("Unexpected RV-011 retrieval configuration.")
    if trace["source_review"]["source_live_canonical_sha256"] != canonical_sha256(live):
        raise ValueError("RV-011 belongs to a different RV-010 artifact.")
    chunks = restore_catalog(trace["chunk_catalog"])
    by_id = {c.chunk_id: c for c in chunks}
    if len(chunks) != 79 or len({c.document_id for c in chunks}) != 10:
        raise ValueError("Expected 79 chunks from ten documents.")
    validate_reference_passages(challenge, chunks)
    for question in live["questions"]:
        for old in question["scored_selection"]:
            current = by_id.get(old["chunk_id"])
            if current is None or current.text != old["text"] or current.document_id != old["document_id"]:
                raise ValueError(f"Passage differs from RV-010: {old['chunk_id']}")
    definitions = {q["question_id"]: (group, q)
        for group, cases in (("A", cases_a), ("B", cases_b)) for q in cases}
    if (len(trace["questions"]) != len(definitions)
            or {q["question_id"] for q in trace["questions"]} != set(definitions)):
        raise ValueError("RV-011 question IDs are missing or duplicated.")
    old_rows = {q["question_id"]: q for q in live["questions"]}
    pool = {c.chunk_id: {"document_id": c.document_id} for c in chunks}
    index = BM25LexicalIndex()
    index.add([c.chunk_id for c in chunks], [c.text for c in chunks])
    raw = LexicalRetriever(index, chunks)
    filtered = FilteredLexicalRetriever(raw)
    rows, drift = [], []
    for recorded in trace["questions"]:
        qid = recorded["question_id"]
        group, case = definitions[qid]
        if (recorded["group"] != group or recorded["query"] != case["query"]
                or recorded["expected_document_ids"] != case["expected_document_ids"]):
            raise ValueError(f"Question definition mismatch: {qid}")
        query = case["query"]
        vector = restore_ranking(recorded["stages"]["vector_full"], by_id, "vector", complete=True)
        restore_ranking(recorded["stages"]["lexical_positive"], by_id, "lexical")
        raw_lexical = raw.retrieve(query, top_k=len(chunks))
        stages = capture_stages(vector, raw_lexical)
        serialized = serialize_stages(query, stages)
        for name, candidates in stages.items():
            verify_ranking(candidates, recorded["stages"][name], f"{qid}/{name}")
            for actual, saved in zip(serialized[name], recorded["stages"][name]):
                if name == "lexical_positive" and actual["matched_query_tokens"] != saved["matched_query_tokens"]:
                    raise ValueError(f"Literal token mismatch: {qid}")
                if "rrf_components" in actual:
                    for method in ("vector", "lexical"):
                        component = actual["rrf_components"].get(method)
                        prior = saved["rrf_components"].get(method)
                        if (component is None) != (prior is None):
                            raise ValueError(f"RRF component mismatch: {qid}")
                        if component and (component["rank"] != prior["rank"] or any(
                            not isclose(component[key], prior[key], rel_tol=1e-9, abs_tol=1e-9)
                            for key in ("score", "rrf_contribution"))):
                            raise ValueError(f"RRF contribution mismatch: {qid}")
        references = case.get("reference_passage_groups", [])
        expected_traces = [dict(ref, trace=diagnose_target(stages, ref["any_of_chunk_ids"])) for ref in references]
        if expected_traces != recorded["reference_passage_traces"]:
            raise ValueError(f"Reference trace mismatch: {qid}")
        filtered_lexical = filtered.retrieve(query, top_k=DEPTH)
        arms = build_arms(vector, raw_lexical, filtered_lexical)
        results = {name: evaluate_selection(values, case, pool) for name, values in arms.items()}
        old_ids = old_rows[qid]["chunk_ids"]["hybrid_v03"]
        new_ids = results["hybrid_v03"]["chunk_ids"]
        matches = old_ids == new_ids
        if matches != recorded["matches_rv010_selection"]:
            raise ValueError(f"Incorrect drift flag: {qid}")
        if not matches:
            removed = [cid for cid in old_ids if cid not in new_ids]
            added = [cid for cid in new_ids if cid not in old_ids]
            old_metrics = question_metrics(old_ids, pool, case["expected_document_ids"])
            drift.append({"question_id": qid, "rv010_chunk_ids": old_ids, "rv011_chunk_ids": new_ids,
                "removed_chunk_ids": removed, "added_chunk_ids": added,
                "first_four_identical": old_ids[:4] == new_ids[:4],
                "document_metrics_unchanged": old_metrics == results["hybrid_v03"]["metrics"],
                "swapped_passages_have_identical_text_and_section": len(removed) == len(added) == 1
                    and by_id[removed[0]].text == by_id[added[0]].text
                    and by_id[removed[0]].section_path == by_id[added[0]].section_path,
                "source_flag_preserved": "BASELINE_DRIFT",
                "upstream_numeric_cause": "Not established: RV-010 did not retain raw vector scores or embeddings."})
        regressions = {arm: [name for name in METRIC_NAMES
            if results[arm]["metrics"][name] < results["hybrid_v03"]["metrics"][name] - 1e-9]
            for arm in ARMS[1:]}
        rows.append({"group": group, "question_id": qid, "query": query,
            "expected_document_ids": case["expected_document_ids"],
            "matches_rv010_selection": matches, "filtered_lexical_query": filter_lexical_query(query),
            "removed_query_tokens": sorted(set(tokenize(query)) & FUNCTION_WORDS),
            "filtered_lexical_top20": [{"chunk_id": c.chunk.chunk_id, "rank": c.rank, "score": c.score}
                                       for c in filtered_lexical],
            "arms": results, "per_question_regressed_metrics": regressions})
    all_match = not drift
    if (trace["all_rv010_selections_reproduced"] != all_match
            or (trace["status"] == "BASELINE_DRIFT") == all_match):
        raise ValueError("Inconsistent RV-011 drift summary.")
    groups = {group: summarize([row for row in rows if row["group"] == group]) for group in ("A", "B")}
    stable_b = [row for row in rows if row["group"] == "B" and row["matches_rv010_selection"]]
    if stable_b:
        groups["B_matching_rv010"] = summarize(stable_b)
    return {"experiment": "RV-012", "status": "OFFLINE_EXPLORATORY_REPLAY_COMPLETE",
        "paired_baseline": "RV-011 rankings; original BASELINE_DRIFT flag is preserved below",
        "source_trace_status": trace["status"], "source_trace_canonical_sha256": canonical_sha256(trace),
        "source_live_canonical_sha256": canonical_sha256(live),
        "source_rankings_and_scores_reproduced": True, "drift_from_rv010": drift,
        "configuration": {"candidate_depth": DEPTH, "selected_chunks": TOP_K, "rrf_k": RRF_K,
            "lexical_filter_version": FILTER_VERSION, "function_words": sorted(FUNCTION_WORDS),
            "filter_policy_sha256": canonical_sha256(sorted(FUNCTION_WORDS)),
            "vector_query_changed": False, "document_index_changed": False},
        "new_embedding_calls": 0, "cross_encoder_calls": 0, "automatically_promoted": False,
        "groups": groups, "questions": rows,
        "limits": ["Alternatives were designed after inspecting A/B; both are development sets for this change.",
            "These are retrieval results without reranking. Scores for new passages cannot be inferred from RV-010.",
            "Reference labels are non-exhaustive; coverage is not answer accuracy.",
            "Query filtering removes grammatical tokens; it does not translate or calibrate lexical evidence.",
            "The filter is opt-in and does not change the existing HybridRetriever defaults."]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, default=Path("docs/validation/RV011_CANDIDATE_TRACE.json"))
    parser.add_argument("--live", type=Path, default=Path("docs/validation/RV010_LIVE_RESULTS.json"))
    parser.add_argument("--source", type=Path, default=Path("docs/validation/RV008_RESULTS.json"))
    parser.add_argument("--challenge", type=Path, default=Path("data/ground_truth/reranking_challenge_b.json"))
    parser.add_argument("--output", type=Path, default=Path("docs/validation/RV012_LEXICAL_REPLAY_RESULTS.json"))
    args = parser.parse_args(argv)
    inputs = [args.trace, args.live, args.source, args.challenge]
    if args.output.resolve() in {path.resolve() for path in inputs}:
        parser.error("Output must not overwrite an input.")
    tracked = inputs + [Path(__file__)] + [Path("app/retrieval") / name for name in (
        "lexical_query_filter.py", "lexical_index.py", "lexical_retriever.py", "candidate_fusion.py", "document_diversifier.py")]
    before = fingerprints(tracked)
    source, challenge, cached, cases_a, cases_b = load_inputs(args.source, args.challenge)
    live = json.loads(args.live.read_text(encoding="utf-8-sig"))
    trace = json.loads(args.trace.read_text(encoding="utf-8-sig"))
    review_result(live, source, challenge, cached, cases_a, cases_b)
    result = replay_trace(trace, live, cases_a, cases_b, challenge)
    if before != fingerprints(tracked):
        raise ValueError("Inputs or implementation changed during replay.")
    result["input_fingerprints"] = before
    for group in ("A", "B"):
        summary = result["groups"][group]
        print(f"\nGroup {group} | n={summary['question_count']}")
        print(f"{'Metric':<12}" + "".join(f"{arm:>26}" for arm in ARMS))
        for metric in METRIC_NAMES:
            print(f"{metric:<12}" + "".join(f"{summary['metrics'][arm][metric]:>26.4f}" for arm in ARMS))
        if group == "B":
            print("Reference coverage:", {arm: values["macro_coverage"] for arm, values in summary["reference_passages"].items()})
        print("Comparisons:", {arm: values["decision"] for arm, values in summary["comparisons"].items()})
    print("RV-010 selection differences:", [row["question_id"] for row in result["drift_from_rv010"]])
    write_result(args.output, result)
    print("RV-012: exploratory offline replay; zero new embedding/reranker calls; no automatic promotion.")


if __name__ == "__main__":
    main()
