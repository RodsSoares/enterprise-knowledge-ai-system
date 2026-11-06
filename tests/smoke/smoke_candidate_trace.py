"""RV-010 offline review and RV-011 retrieval-stage trace; no reranker calls.

Run from repository root. --review-only needs only saved JSON inputs.
The default trace rebuilds the corpus and calls the existing embedding API.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from math import isclose
from pathlib import Path
from statistics import mean
from time import perf_counter

from app.retrieval.candidate_fusion import ReciprocalRankFusion
from app.retrieval.document_diversifier import DocumentDiversifier
from app.retrieval.lexical_index import tokenize
from tests.smoke.smoke_prefix_reranking_live import (
    canonical_sha256, load_inputs, validate_reference_passages, verify_frozen_data,
)
from tests.smoke.smoke_reranking_experiment import fingerprints, installed_versions
from tests.smoke.smoke_reranking_replay import (
    METRIC_NAMES, average, question_metrics, reorder_ids,
)


DEPTH, TOP_K, RRF_K = 20, 5, 60
ARMS = ("hybrid_v03", "unconstrained_top5", "prefix_preserved")


def require_equal_metrics(actual, recorded, context):
    for name in METRIC_NAMES:
        if not isclose(actual[name], recorded[name], rel_tol=0, abs_tol=1e-9):
            raise ValueError(f"Metric mismatch: {context}/{name}")


def review_result(live, source, challenge, cached_replay, cases_a, cases_b):
    """Recompute recorded metrics and reference coverage from actual selections."""
    if (live.get("experiment") != "RV-010"
            or live.get("status") != "LIVE_EXPERIMENT_COMPLETE"
            or live.get("snapshot_stable") is not True):
        raise ValueError("A completed, stable RV-010 artifact is required.")
    for key, value in (("source_canonical_sha256", canonical_sha256(source)),
                       ("challenge_canonical_sha256", canonical_sha256(challenge))):
        if live["provenance"][key] != value:
            raise ValueError(f"RV-010 snapshot binding mismatch: {key}")
    required = {"candidate_depth": DEPTH, "rrf_k": RRF_K, "selected_chunks": TOP_K,
                "protected_documents": 3, "chunk_count": 79,
                "embedding_model": "text-embedding-3-small", "lexical_text": "chunk.text"}
    if any(live["configuration"].get(k) != v for k, v in required.items()):
        raise ValueError("RV-010 retrieval configuration differs from this trace.")
    definitions = {q["question_id"]: (group, q)
                   for group, cases in (("A", cases_a), ("B", cases_b)) for q in cases}
    rows = live["questions"]
    if (len(rows) != len(definitions)
            or {q["question_id"] for q in rows} != set(definitions)):
        raise ValueError("RV-010 question IDs are missing or duplicated.")
    old = {q["question_id"]: q for q in source["questions"]}
    replayed = {q["question_id"]: q for q in cached_replay["questions"]}
    evaluated = {g: {arm: [] for arm in ARMS} for g in ("A", "B")}
    changes = {g: {"improved": [], "regressed": []} for g in ("A", "B")}
    details, cached_orders_match = [], True
    for row in rows:
        qid = row["question_id"]
        group, definition = definitions[qid]
        if (row["group"] != group or row["query"] != definition["query"]
                or row["expected_document_ids"] != definition["expected_document_ids"]):
            raise ValueError(f"Question definition changed: {qid}")
        pool = {c["chunk_id"]: c for c in row["scored_selection"]}
        ids = row["chunk_ids"]
        if len(pool) != TOP_K or len(row["scored_selection"]) != TOP_K:
            raise ValueError(f"{qid}: five unique scored chunks required")
        for arm in ARMS:
            if len(ids[arm]) != TOP_K or set(ids[arm]) != set(pool):
                raise ValueError(f"{qid}: selection membership changed in {arm}")
            docs = list(dict.fromkeys(pool[cid]["document_id"] for cid in ids[arm]))
            if docs != row["document_ids"][arm]:
                raise ValueError(f"{qid}: document IDs disagree with chunks")
            metrics = question_metrics(ids[arm], pool, definition["expected_document_ids"])
            require_equal_metrics(metrics, row["metrics"][arm], f"{qid}/{arm}")
            evaluated[group][arm].append(metrics)
        for arm, policy in (("unconstrained_top5", "fixed_top5"),
                            ("prefix_preserved", "preserve_top3_and_top5")):
            expected = reorder_ids(ids["hybrid_v03"], pool, policy)
            if list(expected) != ids[arm]:
                raise ValueError(f"{qid}: order disagrees with cached scores in {arm}")
        delta = row["metrics"]["prefix_preserved"]["Hit@1"] - row["metrics"]["hybrid_v03"]["Hit@1"]
        if delta:
            changes[group]["improved" if delta > 0 else "regressed"].append(qid)
        if group == "A":
            if ids["hybrid_v03"] != old[qid]["final_chunk_ids"]["hybrid_v03"]:
                raise ValueError(f"{qid}: baseline selection differs from RV-008")
            cached_orders_match &= ids["prefix_preserved"] == list(
                replayed[qid]["policies"]["preserve_top3_and_top5"]["chunk_ids"])
            continue
        references = definition["reference_passage_groups"]
        if row["reference_passage_groups"] != references:
            raise ValueError(f"{qid}: reference definitions changed")
        found = [bool(set(g["any_of_chunk_ids"]) & set(pool)) for g in references]
        coverage = sum(found) / len(found)
        if not isclose(coverage, row["reference_group_coverage_at_5"], abs_tol=1e-9):
            raise ValueError(f"{qid}: reference coverage mismatch")
        details.append({"question_id": qid, "reference_groups_found": sum(found),
            "reference_groups_total": len(found), "reference_coverage": coverage,
            "missing_expected_documents": sorted(set(definition["expected_document_ids"])
                - set(row["document_ids"]["hybrid_v03"])),
            "missing_reference_groups": [g for g, hit in zip(references, found) if not hit],
            "selected_literal_overlaps": [{"chunk_id": cid,
                "query_tokens_in_passage": sorted(set(tokenize(row["query"])) & set(tokenize(pool[cid]["text"])))}
                for cid in ids["hybrid_v03"]]})
    metrics = {g: {arm: average(values) for arm, values in arms.items()}
               for g, arms in evaluated.items()}
    for group, arms in metrics.items():
        if live["groups"][group]["question_count"] != len(evaluated[group]["hybrid_v03"]):
            raise ValueError(f"Question count mismatch: {group}")
        for arm, values in arms.items():
            require_equal_metrics(values, live["groups"][group]["metrics"][arm], f"{group}/{arm}")
    return {"experiment": "RV-010-REVIEW", "status": "OFFLINE_REVIEW_COMPLETE",
        "source_live_canonical_sha256": canonical_sha256(live),
        "metrics_reproduced": True, "a_cached_orders_reproduced": cached_orders_match,
        "group_metrics": metrics, "first_rank_changes": changes,
        "b_reference_coverage": {
            "macro_mean": mean(q["reference_coverage"] for q in details),
            "groups_found": sum(q["reference_groups_found"] for q in details),
            "groups_total": sum(q["reference_groups_total"] for q in details),
            "fully_covered_questions": [q["question_id"] for q in details if q["reference_coverage"] == 1],
            "partially_covered_questions": [q["question_id"] for q in details if 0 < q["reference_coverage"] < 1],
            "zero_reference_questions": [q["question_id"] for q in details if q["reference_coverage"] == 0]},
        "questions_b": details, "automatically_promoted": False,
        "independent_human_review": False, "new_api_calls": 0,
        "limits": ["Reference passages are non-exhaustive; coverage is not answer accuracy.",
                   "RV-010 records final chunks only; losses before selection require a fresh stage trace."]}


def capture_stages(vector_full, lexical_full):
    """Trace the unchanged algorithm; no labels or expected evidence enter here."""
    fusion = ReciprocalRankFusion(k=RRF_K)
    fused = fusion.fuse((vector_full[:DEPTH], lexical_full[:DEPTH]), top_k=2 * DEPTH)
    selected = DocumentDiversifier().select(fused[:DEPTH], top_k=TOP_K)
    return {"vector_full": vector_full, "lexical_positive": lexical_full,
            "fused_union": fused, "fused_top20": fused[:DEPTH], "selected_top5": selected}


def diagnose_target(stages, target_ids):
    """Classify the earliest missing stage for any acceptable target passage."""
    target_ids = set(target_ids)
    if not target_ids:
        raise ValueError("Target IDs must not be empty.")
    ranks = {name: next((c.rank for c in candidates if c.chunk.chunk_id in target_ids), None)
             for name, candidates in stages.items()}
    if ranks["selected_top5"] is not None:
        loss = "SELECTED"
    elif ranks["fused_union"] is None:
        loss = "OUTSIDE_RETRIEVER_TOP20"
    elif ranks["fused_top20"] is None:
        loss = "FUSION_TOP20_CUTOFF"
    else:
        target_docs = {c.chunk.document_id for c in stages["fused_top20"] if c.chunk.chunk_id in target_ids}
        selected_docs = {c.chunk.document_id for c in stages["selected_top5"]}
        loss = ("SAME_DOCUMENT_OTHER_PASSAGE_SELECTED" if target_docs & selected_docs
                else "FINAL_TOP5_SELECTION")
    return {"target_chunk_ids": sorted(target_ids), "ranks": ranks, "outcome": loss}


def serialize_stages(query, stages):
    query_terms = set(tokenize(query))
    components = {method: {c.chunk.chunk_id: c for c in stages[name][:DEPTH]}
                  for method, name in (("vector", "vector_full"), ("lexical", "lexical_positive"))}
    def record(candidate, stage):
        cid = candidate.chunk.chunk_id
        item = {"chunk_id": cid, "document_id": candidate.chunk.document_id,
                "rank": candidate.rank, "score": candidate.score}
        if stage == "lexical_positive":
            item["matched_query_tokens"] = sorted(query_terms & set(tokenize(candidate.chunk.text)))
        if stage.startswith("fused") or stage == "selected_top5":
            item["rrf_components"] = {method: {"rank": rows[cid].rank,
                "score": rows[cid].score, "rrf_contribution": 1 / (RRF_K + rows[cid].rank)}
                for method, rows in components.items() if cid in rows}
        return item
    return {name: [record(c, name) for c in candidates] for name, candidates in stages.items()}


def chunk_record(chunk):
    return {"chunk_id": chunk.chunk_id, "document_id": chunk.document_id,
            "order": chunk.order, "text": chunk.text,
            "text_sha256": hashlib.sha256(chunk.text.encode("utf-8")).hexdigest(),
            "section_path": list(chunk.section_path), "source_path": chunk.source_path.as_posix(),
            "source_block_ids": list(chunk.source_block_ids), "page_numbers": list(chunk.page_numbers),
            "slide_numbers": list(chunk.slide_numbers), "sheet_names": list(chunk.sheet_names)}


def verify_helper_fingerprints(live, paths):
    """Resolve known local files even when __file__ was recorded as a Windows path."""
    recorded = live["input_fingerprints"]
    for path in paths:
        relative = path.as_posix()
        matches = [value for name, value in recorded.items()
                   if name.replace("\\", "/") == relative
                   or name.replace("\\", "/").endswith("/" + relative)]
        # Never read a recorded absolute path; only the explicit local path.
        if (len(matches) != 1 or not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != matches[0]):
            raise ValueError(f"RV-010 helper fingerprint missing, ambiguous, or changed: {path}")


def write_result(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Saved: {path}", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("docs/validation/RV008_RESULTS.json"))
    parser.add_argument("--live", type=Path, default=Path("docs/validation/RV010_LIVE_RESULTS.json"))
    parser.add_argument("--challenge", type=Path, default=Path("data/ground_truth/reranking_challenge_b.json"))
    parser.add_argument("--review-only", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    output = args.output or Path("docs/validation/" + (
        "RV010_REVIEW_RESULTS.json" if args.review_only else "RV011_CANDIDATE_TRACE.json"))
    if output.resolve() in {p.resolve() for p in (args.source, args.live, args.challenge)}:
        parser.error("Output must not overwrite any input.")
    source, challenge, cached, cases_a, cases_b = load_inputs(args.source, args.challenge)
    live = json.loads(args.live.read_text(encoding="utf-8-sig"))
    review = review_result(live, source, challenge, cached, cases_a, cases_b)
    coverage = review["b_reference_coverage"]
    print(f"RV-010 metrics: reproduced; B reference groups: {coverage['groups_found']}/{coverage['groups_total']}; "
          f"fully covered: {len(coverage['fully_covered_questions'])}/12", flush=True)
    if args.review_only:
        write_result(output, review)
        return

    from app.retrieval.lexical_index import BM25LexicalIndex
    from app.retrieval.lexical_retriever import LexicalRetriever
    from app.retrieval.openai_embeddings import OpenAIEmbeddingProvider
    from app.retrieval.vector_index import NumPyVectorIndex
    from app.retrieval.vector_indexer import VectorIndexer
    from app.retrieval.vector_retriever import VectorRetriever
    from tests.smoke.smoke_golden_set_vector_retrieval import (
        SOURCE_PATHS, build_chunks, validate_global_chunk_identity, validate_sources,
    )

    validate_sources()
    controlled = list(SOURCE_PATHS) + [Path("data/ground_truth") / name for name in
        ("canonical_facts.yaml", "document_registry.yaml", "golden_questions.yaml")]
    app_paths = list(Path("app").rglob("*.py"))
    verify_frozen_data(source, controlled)
    verify_frozen_data(live, controlled + app_paths)
    inputs = [args.source, args.live, args.challenge]
    helpers = [Path("tests/smoke") / name for name in (
        "smoke_prefix_reranking_live.py", "smoke_reranking_experiment.py",
        "smoke_reranking_replay.py", "smoke_golden_set_vector_retrieval.py")]
    verify_helper_fingerprints(live, helpers)
    tracked = controlled + app_paths + helpers + inputs + [Path(__file__)]
    initial = fingerprints(tracked)
    print("RV-011: rebuilding frozen corpus; no cross-encoder inference...", flush=True)
    chunks = build_chunks()
    validate_global_chunk_identity(chunks)
    if len(chunks) != 79 or len(SOURCE_PATHS) != 10:
        raise ValueError("RV-011 requires the frozen 79-chunk, ten-document corpus.")
    validate_reference_passages(challenge, chunks)
    by_id = {c.chunk_id: c for c in chunks}
    for row in live["questions"]:
        for previous in row["scored_selection"]:
            current = by_id.get(previous["chunk_id"])
            if current is None or current.document_id != previous["document_id"] or current.text != previous["text"]:
                raise ValueError(f"RV-010 passage changed: {previous['chunk_id']}")
    provider = OpenAIEmbeddingProvider.from_environment(model="text-embedding-3-small")
    vector_index = NumPyVectorIndex()
    VectorIndexer(embedding_provider=provider, vector_index=vector_index).index(chunks)
    vector = VectorRetriever(embedding_provider=provider, vector_index=vector_index, chunks=chunks)
    lexical_index = BM25LexicalIndex()
    lexical_index.add([c.chunk_id for c in chunks], [c.text for c in chunks])
    lexical = LexicalRetriever(lexical_index=lexical_index, chunks=chunks)
    previous = {row["question_id"]: row for row in live["questions"]}
    rows = []
    for group, cases in (("A", cases_a), ("B", cases_b)):
        for case in cases:
            query, qid = case["query"], case["question_id"]
            start = perf_counter()
            # Both existing exact indexes sort the full list before applying k.
            # Slicing these rankings reproduces the usual Top-20 inputs.
            vector_full = vector.retrieve(query, top_k=len(chunks))
            lexical_full = lexical.retrieve(query, top_k=len(chunks))
            if len(vector_full) != len(chunks):
                raise ValueError(f"{qid}: full vector ranking is incomplete")
            stages = capture_stages(vector_full, lexical_full)
            elapsed = perf_counter() - start
            ids = [c.chunk.chunk_id for c in stages["selected_top5"]]
            document_traces = {doc: diagnose_target(stages, [c.chunk_id for c in chunks if c.document_id == doc])
                               for doc in case["expected_document_ids"]}
            passage_traces = [dict(g, trace=diagnose_target(stages, g["any_of_chunk_ids"]))
                              for g in case.get("reference_passage_groups", [])]
            matches = ids == previous[qid]["chunk_ids"]["hybrid_v03"]
            rows.append({"group": group, "question_id": qid, "query": query,
                "query_tokens": sorted(set(tokenize(query))), "retrieval_seconds": elapsed,
                "expected_document_ids": case["expected_document_ids"],
                "matches_rv010_selection": matches, "stages": serialize_stages(query, stages),
                "expected_document_traces": document_traces, "reference_passage_traces": passage_traces})
            outcomes = [g["trace"]["outcome"] for g in passage_traces]
            print(f"{group}/{qid}: baseline_match={matches}; reference_outcomes={outcomes}", flush=True)
    stable = initial == fingerprints(tracked)
    try:
        stable = stable and all(canonical_sha256(json.loads(path.read_text(encoding="utf-8-sig"))) == canonical_sha256(value)
                                for path, value in zip(inputs, (source, live, challenge)))
    except (ValueError, OSError):
        stable = False
    matches = all(row["matches_rv010_selection"] for row in rows)
    decision = "INPUT_CHANGED_DURING_RUN" if not stable else "BASELINE_DRIFT" if not matches else "TRACE_COMPLETE"
    payload = {"experiment": "RV-011", "status": decision,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "retrieval_diagnostic_only", "automatically_promoted": False,
        "snapshot_stable": stable, "all_rv010_selections_reproduced": matches,
        "input_fingerprints": initial, "versions": installed_versions(),
        "configuration": {"candidate_depth": DEPTH, "selected_chunks": TOP_K, "rrf_k": RRF_K,
            "embedding_model": "text-embedding-3-small", "lexical_text": "chunk.text",
            "chunk_count": len(chunks), "query_embedding_requests": len(rows), "cross_encoder_inference_calls": 0},
        "source_review": review, "chunk_catalog": [chunk_record(c) for c in chunks], "questions": rows,
        "limits": ["Full vector ranks are diagnostic; only Top-20 per method feed the unchanged baseline.",
                   "Lexical absence means no positive BM25 score, not a missing corpus chunk.",
                   "Reference labels are non-exhaustive and have not had independent human review."]}
    write_result(output, payload)
    print(f"RV-011: {decision}; cross-encoder calls=0; no retrieval configuration changes.")


if __name__ == "__main__":
    main()
