"""RV-010: live scoring of five selected chunks, with separate prospective B.

Run from repository root after saving reranking_challenge_b.json:
    python -m tests.smoke.smoke_prefix_reranking_live

Real embeddings and local model inference are used only when main() runs.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from math import isclose
from pathlib import Path
from statistics import mean, median
from time import perf_counter

from app.retrieval.prefix_preserving_selector import PrefixPreservingSelector
from app.retrieval.reranker import CandidateReranker
from tests.smoke.smoke_reranking_experiment import fingerprints, installed_versions
from tests.smoke.smoke_reranking_replay import METRIC_NAMES, average, question_metrics, replay


CHALLENGE_SHA256 = "f52739b380f00778291aef65d8fdc4be3181a6e9acea92c4f26f5ab3d8cb2b3a"
TOP_K, DEPTH, RRF_K, PROTECTED_DOCUMENTS = 5, 20, 60, 3


def canonical_sha256(value):
    """Freeze JSON meaning without depending on Windows line endings/indentation."""
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def load_inputs(source_path, challenge_path):
    source = json.loads(Path(source_path).read_text(encoding="utf-8-sig"))
    challenge = json.loads(Path(challenge_path).read_text(encoding="utf-8-sig"))
    if canonical_sha256(challenge) != CHALLENGE_SHA256:
        raise ValueError("Challenge B changed after definition; use the frozen file or define a new experiment.")
    if canonical_sha256(source) != challenge["source_artifact"]["canonical_sha256"]:
        raise ValueError("Challenge B and the supplied RV-008 source do not belong to the same snapshot.")
    cached_replay = replay(source)  # validates all source metrics without inference
    cases_a = [{"question_id": q["question_id"], "query": q["query"],
                "expected_document_ids": q["expected_document_ids"]} for q in source["questions"]]
    cases_b = challenge["questions"]
    if len(cases_a) != 13 or len(cases_b) != 12:
        raise ValueError("RV-010 requires the frozen 13 A questions and 12 prospective B questions.")
    if len({q["question_id"] for q in cases_a + cases_b}) != 25:
        raise ValueError("Question IDs must be unique across A and B.")
    if set(q["query"] for q in cases_a).intersection(q["query"] for q in cases_b):
        raise ValueError("B must contain new questions.")
    return source, challenge, cached_replay, cases_a, cases_b


def verify_frozen_data(source, paths):
    """Read only known corpus paths, not arbitrary paths recorded in the JSON."""
    for path in paths:
        expected = source["input_fingerprints"].get(path.as_posix())
        if expected is None or not path.is_file():
            raise ValueError(f"Frozen corpus/ground-truth file missing: {path}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Corpus/ground truth changed since RV-008: {path}")


def validate_reference_passages(challenge, chunks):
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    for question in challenge["questions"]:
        refs = {item["chunk_id"]: item for item in question["source_evidence"]}
        if {item["document_id"] for item in refs.values()} != set(question["expected_document_ids"]):
            raise ValueError(f"{question['question_id']}: inconsistent expected documents")
        for group in question["reference_passage_groups"]:
            if not group["any_of_chunk_ids"] or not set(group["any_of_chunk_ids"]).issubset(refs):
                raise ValueError(f"{question['question_id']}: invalid reference passage group")
        for cid, reference in refs.items():
            chunk = by_id.get(cid)
            if chunk is None or chunk.document_id != reference["document_id"]:
                raise ValueError(f"Reference passage identity changed: {cid}")
            if hashlib.sha256(chunk.text.encode("utf-8")).hexdigest() != reference["text_sha256"]:
                raise ValueError(f"Reference passage content changed: {cid}")


def evaluate_arms(question, arms):
    """Labels enter only evaluation, after retrieval and scoring."""
    pool = {c.chunk.chunk_id: {"document_id": c.chunk.document_id}
            for candidates in arms.values() for c in candidates}
    expected = question["expected_document_ids"]
    return {label: question_metrics([c.chunk.chunk_id for c in candidates], pool, expected)
            for label, candidates in arms.items()}


def compare_metrics(baseline, candidate):
    regressions = [name for name in METRIC_NAMES if candidate[name] < baseline[name] - 1e-9]
    improvements = [name for name in ("Hit@1", "MRR") if candidate[name] > baseline[name] + 1e-9]
    decision = "REGRESSION" if regressions else "IMPROVEMENT" if improvements else "NO_FIRST_RANK_GAIN"
    return {"decision": decision, "regressed_metrics": regressions,
            "improved_first_rank_metrics": improvements, "automatically_promoted": False}


def summarize_group(rows):
    labels = ("hybrid_v03", "unconstrained_top5", "prefix_preserved")
    metrics = {label: average([row["metrics"][label] for row in rows]) for label in labels}
    times = [row["score_seconds"] for row in rows]
    return {"question_count": len(rows), "metrics": metrics,
            "comparisons": {label: compare_metrics(metrics["hybrid_v03"], metrics[label])
                            for label in labels if label != "hybrid_v03"},
            "scoring_latency_seconds": {"mean": mean(times), "median": median(times),
                                        "min": min(times), "max": max(times)}}


def decide_run(groups, baseline_matches, selections_match, snapshot_stable):
    if not snapshot_stable:
        return "INPUT_CHANGED_DURING_RUN"
    if not baseline_matches or not selections_match:
        return "BASELINE_DRIFT"
    if any(groups[name]["comparisons"]["prefix_preserved"]["decision"] == "REGRESSION" for name in ("A", "B")):
        return "REGRESSION"
    return "READY_FOR_REVIEW"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("docs/validation/RV008_RESULTS.json"))
    parser.add_argument("--challenge", type=Path, default=Path("data/ground_truth/reranking_challenge_b.json"))
    parser.add_argument("--output", type=Path, default=Path("docs/validation/RV010_LIVE_RESULTS.json"))
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args(argv)
    if args.output.resolve() in {args.source.resolve(), args.challenge.resolve()}:
        parser.error("Output must not overwrite either input.")
    source, challenge, cached_replay, cases_a, cases_b = load_inputs(args.source, args.challenge)
    print(f"Frozen B: {canonical_sha256(challenge)} | A=13; B=12", flush=True)

    from app.retrieval.candidate_fusion import ReciprocalRankFusion
    from app.retrieval.cross_encoder_scorer import TransformersCrossEncoderScorer
    from app.retrieval.document_diversifier import DocumentDiversifier
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
    controlled_paths = list(SOURCE_PATHS) + [Path("data/ground_truth") / name for name in
                        ("canonical_facts.yaml", "document_registry.yaml", "golden_questions.yaml")]
    verify_frozen_data(source, controlled_paths)
    if len(SOURCE_PATHS) != 10:
        raise ValueError("The frozen corpus has 10 documents.")
    tracked = controlled_paths + list(Path("app").rglob("*.py")) + [
        args.source, args.challenge, Path(__file__),
        Path("tests/smoke/smoke_reranking_replay.py"),
        Path("tests/smoke/smoke_reranking_experiment.py"),
        Path("tests/smoke/smoke_golden_set_vector_retrieval.py"),
    ]
    initial_fingerprints = fingerprints(tracked)
    print("Preparing the frozen corpus...", flush=True)
    chunks = build_chunks()
    validate_global_chunk_identity(chunks)
    if len(chunks) != 79:
        raise ValueError(f"Expected 79 chunks; got {len(chunks)}.")
    validate_reference_passages(challenge, chunks)
    config = source["configuration"]
    scorer = TransformersCrossEncoderScorer(
        config["model"], revision=config["revision"], device=args.device,
        batch_size=8, max_length=512,
    )
    print("Loading the pinned local reranker...", flush=True)
    start = perf_counter()
    scorer.load()
    load_seconds = perf_counter() - start
    reranker = CandidateReranker(scorer)
    selector = PrefixPreservingSelector(PROTECTED_DOCUMENTS)

    print("Building shared indexes; embedding the corpus once...", flush=True)
    provider = OpenAIEmbeddingProvider.from_environment(model="text-embedding-3-small")
    index = NumPyVectorIndex()
    VectorIndexer(embedding_provider=provider, vector_index=index).index(chunks)
    vector = VectorRetriever(embedding_provider=provider, vector_index=index, chunks=chunks)
    lexical_index = BM25LexicalIndex()
    lexical_index.add([c.chunk_id for c in chunks], [c.text for c in chunks])
    lexical = LexicalRetriever(lexical_index=lexical_index, chunks=chunks)
    fusion, diversifier = ReciprocalRankFusion(k=RRF_K), DocumentDiversifier()
    old_a = {q["question_id"]: q for q in source["questions"]}
    cached_a = {q["question_id"]: q for q in cached_replay["questions"]}
    rows = []

    for group_name, questions in (("A", cases_a), ("B", cases_b)):
        for question in questions:
            query, qid = question["query"], question["question_id"]
            start = perf_counter()
            fused = fusion.fuse((vector.retrieve(query, top_k=DEPTH),
                                 lexical.retrieve(query, top_k=DEPTH)), top_k=DEPTH)
            selection = diversifier.select(fused, top_k=TOP_K)
            fused_by_id = {candidate.chunk.chunk_id: candidate for candidate in fused}
            # Restore original RRF ranks: DocumentDiversifier renumbers its output.
            # Input sequence order still expresses the baseline Top-5 selection.
            selected = tuple(fused_by_id[c.chunk.chunk_id] for c in selection)
            retrieval_seconds = perf_counter() - start
            if len(selected) != TOP_K:
                raise RuntimeError(f"{qid}: expected five selected chunks")
            start = perf_counter()
            scored = reranker.rerank(query, selected, top_k=TOP_K)
            scoring_seconds = perf_counter() - start
            constrained = selector.select(selected, scored)
            arms = {"hybrid_v03": selected, "unconstrained_top5": scored,
                    "prefix_preserved": constrained}
            ids = {label: [c.chunk.chunk_id for c in values] for label, values in arms.items()}
            docs = {label: list(dict.fromkeys(c.chunk.document_id for c in values))
                    for label, values in arms.items()}
            if (set(ids["hybrid_v03"]) != set(ids["prefix_preserved"])
                    or set(docs["hybrid_v03"][:3]) != set(docs["prefix_preserved"][:3])):
                raise AssertionError(f"{qid}: prefix or selection invariant failed")
            row = {"group": group_name, "question_id": qid, "query": query,
                   "expected_document_ids": question["expected_document_ids"],
                   "metrics": evaluate_arms(question, arms),
                   "retrieval_seconds": retrieval_seconds, "score_seconds": scoring_seconds,
                   "scored_pairs": len(selected), "chunk_ids": ids, "document_ids": docs,
                   "preserved_selection": True, "preserved_document_top3": True,
                   "scored_selection": [{
                       "chunk_id": c.chunk.chunk_id, "document_id": c.chunk.document_id,
                       "fusion_rank": c.source.rank, "fusion_score": c.source.score,
                       "rerank_rank": c.rerank_rank, "rerank_score": c.score,
                       "section_path": list(c.chunk.section_path), "text": c.chunk.text,
                       "source_path": c.chunk.source_path.as_posix(),
                       "source_block_ids": list(c.chunk.source_block_ids),
                       "page_numbers": list(c.chunk.page_numbers),
                       "slide_numbers": list(c.chunk.slide_numbers),
                       "sheet_names": list(c.chunk.sheet_names),
                   } for c in scored]}
            if group_name == "A":
                cached_order = cached_a[qid]["policies"]["preserve_top3_and_top5"]["chunk_ids"]
                old_scores = {c["chunk_id"]: c["rerank_score"] for c in old_a[qid]["reranked_pool"]}
                row["matches_frozen_selection"] = ids["hybrid_v03"] == old_a[qid]["final_chunk_ids"]["hybrid_v03"]
                row["matches_cached_constrained_order"] = ids["prefix_preserved"] == list(cached_order)
                row["max_score_delta_vs_cached20"] = (
                    max(abs(c.score - old_scores[c.chunk.chunk_id]) for c in scored)
                    if all(c.chunk.chunk_id in old_scores for c in scored) else None)
            else:
                references = question["reference_passage_groups"]
                row["reference_passage_groups"] = references
                row["reference_group_coverage_at_5"] = sum(
                    bool(set(g["any_of_chunk_ids"]).intersection(ids["hybrid_v03"]))
                    for g in references) / len(references)
                row["reference_coverage_note"] = "Same selected set in all arms; diagnostic non-exhaustive labels, not answer accuracy."
            rows.append(row)
            print(f"{group_name}/{qid}: {scoring_seconds:.2f}s; "
                  f"baseline={','.join(docs['hybrid_v03'])}; "
                  f"constrained={','.join(docs['prefix_preserved'])}", flush=True)

    groups = {name: summarize_group([row for row in rows if row["group"] == name]) for name in ("A", "B")}
    baseline_matches = all(isclose(groups["A"]["metrics"]["hybrid_v03"][name], value, rel_tol=0, abs_tol=1e-9)
                           for name, value in source["frozen_v03_metrics"].items())
    selections_match = all(row["matches_frozen_selection"] for row in rows if row["group"] == "A")
    snapshot_stable = initial_fingerprints == fingerprints(tracked)
    try:
        snapshot_stable = snapshot_stable and (
            canonical_sha256(json.loads(args.source.read_text(encoding="utf-8-sig"))) == canonical_sha256(source)
            and canonical_sha256(json.loads(args.challenge.read_text(encoding="utf-8-sig"))) == CHALLENGE_SHA256)
    except (OSError, ValueError):
        snapshot_stable = False
    decision = decide_run(groups, baseline_matches, selections_match, snapshot_stable)
    payload = {
        "experiment": "RV-010", "status": "LIVE_EXPERIMENT_COMPLETE",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "decision": decision, "automatically_promoted": False,
        "metric_scope": source["metric_scope"],
        "configuration": {"model": scorer.model_name, "revision": scorer.revision,
            "device": args.device, "batch_size": 8, "max_length": 512,
            "candidate_depth": DEPTH, "rrf_k": RRF_K, "selected_chunks": TOP_K,
            "protected_documents": PROTECTED_DOCUMENTS, "embedding_model": "text-embedding-3-small",
            "chunk_count": len(chunks), "lexical_text": "chunk.text", "rerank_text": "build_search_text(chunk)"},
        "provenance": {"challenge_canonical_sha256": canonical_sha256(challenge),
            "source_canonical_sha256": canonical_sha256(source),
            "challenge_label_status": challenge["label_status"],
            "new_queries_scored_in_this_run": len(cases_b),
            "blind_external_holdout": False},
        "versions": installed_versions(), "model_load_seconds": load_seconds,
        "model_scoring_calls": len(rows), "model_scored_pairs": sum(row["scored_pairs"] for row in rows),
        "snapshot_stable": snapshot_stable, "input_fingerprints": initial_fingerprints,
        "a_baseline_metrics_reproduced": baseline_matches,
        "a_selections_reproduced": selections_match,
        "a_cached_orders_reproduced": all(row["matches_cached_constrained_order"] for row in rows if row["group"] == "A"),
        "groups": groups, "questions": rows,
        "pending": ["independent review of B labels and passages", "Q25 authority/evidence review",
                    "abstention and answer/citation evaluation", "broader corpus validation"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    for name, group in groups.items():
        print(f"\nGroup {name} | n={group['question_count']}")
        print(f"{'Metric':<12}{'hybrid_v03':>20}{'unconstrained_top5':>22}{'prefix_preserved':>22}")
        for metric in METRIC_NAMES:
            print(f"{metric:<12}" + "".join(f"{group['metrics'][label][metric]:>22.4f}"
                  for label in ("hybrid_v03", "unconstrained_top5", "prefix_preserved")))
        print("Constrained:", group["comparisons"]["prefix_preserved"]["decision"])
        print("Scoring latency:", group["scoring_latency_seconds"])
    print(f"\nRV-010: {decision}; no automatic promotion.\nSaved: {args.output}")


if __name__ == "__main__":
    main()
