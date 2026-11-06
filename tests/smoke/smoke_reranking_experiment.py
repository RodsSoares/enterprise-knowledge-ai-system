"""RV-008: paired local cross-encoder experiment; no automatic promotion.

Run from repository root:
    python -m tests.smoke.smoke_reranking_experiment

This explicitly invoked smoke downloads a model on first use and calls the
existing OpenAI embedding provider. Unit-test collection does neither.
"""

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
from math import isclose
from pathlib import Path
import platform
from time import perf_counter

from app.retrieval.cross_encoder_scorer import (
    DEFAULT_MODEL, TransformersCrossEncoderScorer,
)
from app.retrieval.reranker import CandidateReranker, select_reranked_candidates


DEPTH = 20
RRF_K = 60
EMBEDDING_MODEL = "text-embedding-3-small"
METRICS = {
    "Hit@1": "mean_hit_at_1", "Hit@3": "mean_hit_at_3",
    "Hit@5": "mean_hit_at_5", "Recall@1": "mean_recall_at_1",
    "Recall@3": "mean_recall_at_3", "Recall@5": "mean_recall_at_5",
    "MRR": "mean_reciprocal_rank",
}
FROZEN_V03 = {
    "Hit@1": 10 / 13, "Hit@3": 1.0, "Hit@5": 1.0,
    "Recall@1": 17 / 39, "Recall@3": 34 / 39, "Recall@5": 1.0,
    "MRR": 23 / 26,
}
EXPECTED_QIDS = {"Q05", "Q20", "Q21", "Q22", "Q23", "Q25", "Q26",
                 "Q31", "Q32", "Q33", "Q34", "Q35", "Q36"}


def assess_experiment(baseline, candidate):
    """Eligibility for passage review, never a claim of answer quality."""
    reproduced = all(isclose(baseline[name], expected, rel_tol=0, abs_tol=1e-9)
                     for name, expected in FROZEN_V03.items())
    regressions = [name for name in METRICS if candidate[name] < baseline[name] - 1e-9]
    improved = [name for name in ("Hit@1", "MRR") if candidate[name] > baseline[name] + 1e-9]
    if not reproduced:
        decision = "BASELINE_DRIFT"
    elif regressions:
        decision = "REGRESSION"
    elif not improved:
        decision = "NO_FIRST_RANK_GAIN"
    else:
        decision = "READY_FOR_PASSAGE_REVIEW"
    return dict(decision=decision, baseline_reproduced=reproduced,
                regressed_metrics=regressions, improved_first_rank_metrics=improved,
                automatically_promoted=False)


def make_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--revision", default=None, help="Explicit revision required for custom models")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--output", type=Path, default=Path("docs/validation/RV008_RESULTS.json"))
    return parser


def fingerprints(paths):
    return {path.as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(set(paths)) if path.is_file()}


def installed_versions():
    result = {"python": platform.python_version()}
    for package in ("torch", "transformers", "tokenizers", "numpy", "openai", "docling"):
        try:
            result[package] = version(package)
        except PackageNotFoundError:
            result[package] = "not installed"
    return result


def main(argv=None):
    args = make_parser().parse_args(argv)
    scorer = TransformersCrossEncoderScorer(
        args.model, revision=args.revision, device=args.device,
        batch_size=args.batch_size, max_length=args.max_length,
    )
    # Heavy corpus/provider imports are deliberately deferred until execution.
    from app.evaluation.golden_set_loader import GoldenSetLoader
    from app.evaluation.retrieval_evaluator import RetrievalEvaluator
    from app.retrieval.candidate_fusion import ReciprocalRankFusion
    from app.retrieval.document_diversifier import DocumentDiversifier
    from app.retrieval.lexical_index import BM25LexicalIndex
    from app.retrieval.lexical_retriever import LexicalRetriever
    from app.retrieval.openai_embeddings import OpenAIEmbeddingProvider
    from app.retrieval.vector_index import NumPyVectorIndex
    from app.retrieval.vector_indexer import VectorIndexer
    from app.retrieval.vector_retriever import VectorRetriever
    from tests.smoke.smoke_golden_set_vector_retrieval import (
        SOURCE_PATHS, TOP_K, build_chunks, document_id_from_path,
        unique_ranked_document_ids, validate_global_chunk_identity, validate_sources,
    )

    validate_sources()
    golden_set = GoldenSetLoader().load()
    available_ids = {document_id_from_path(path) for path in SOURCE_PATHS}
    questions = [item.question for item in golden_set.classify_for_corpus(available_ids)
                 if item.evaluable and item.question.expected_evidence]
    actual_qids = [question.question_id for question in questions]
    if len(actual_qids) != 13 or set(actual_qids) != EXPECTED_QIDS:
        raise RuntimeError("Golden Set scope changed; establish a new baseline before RV-008.")
    if len(SOURCE_PATHS) != 10 or len(available_ids) != 10 or TOP_K != 5:
        raise RuntimeError("RV-008 requires the frozen 10-document, Top-5 configuration.")

    print("RV-008: corpus preparation", flush=True)
    chunks = build_chunks()
    validate_global_chunk_identity(chunks)
    if len(chunks) != 79:
        raise RuntimeError(f"Expected 79 frozen-corpus chunks, got {len(chunks)}; investigate drift.")
    initial_fingerprints = fingerprints(
        list(SOURCE_PATHS) + list(Path("data/ground_truth").glob("*.yaml"))
        + list(Path("app").rglob("*.py")) + [Path(__file__)]
    )
    print(f"Loading local reranker: {scorer.model_name} @ {scorer.revision}", flush=True)
    start = perf_counter()
    scorer.load()
    model_load_seconds = perf_counter() - start
    reranker = CandidateReranker(scorer)

    print("Building shared vector and lexical indexes...", flush=True)
    provider = OpenAIEmbeddingProvider.from_environment(model=EMBEDDING_MODEL)
    vector_index = NumPyVectorIndex()
    VectorIndexer(embedding_provider=provider, vector_index=vector_index).index(chunks)
    vector = VectorRetriever(embedding_provider=provider, vector_index=vector_index, chunks=chunks)
    lexical_index = BM25LexicalIndex()
    # Match RV-007 exactly; do not change lexical representation in this experiment.
    lexical_index.add([chunk.chunk_id for chunk in chunks], [chunk.text for chunk in chunks])
    lexical = LexicalRetriever(lexical_index=lexical_index, chunks=chunks)
    fusion, diversifier = ReciprocalRankFusion(k=RRF_K), DocumentDiversifier()
    labels = ("vector", "hybrid_v02", "hybrid_v03", "reranked", "reranked_diverse")
    rankings = {label: {} for label in labels}
    traces = []

    for question in questions:
        query, qid = question.question, question.question_id
        # One vector call, one lexical call and one reranker call per question.
        # Every arm shares the same candidates; no per-strategy query embeddings.
        start = perf_counter()
        vector_pool = vector.retrieve(query, top_k=DEPTH)
        lexical_pool = lexical.retrieve(query, top_k=DEPTH)
        fused_pool = fusion.fuse((vector_pool, lexical_pool), top_k=DEPTH)
        retrieval_seconds = perf_counter() - start
        if not fused_pool:
            raise RuntimeError(f"{qid}: empty fused pool")
        start = perf_counter()
        reranked_pool = reranker.rerank(query, fused_pool, top_k=DEPTH)
        rerank_seconds = perf_counter() - start
        arms = {
            "vector": vector_pool[:TOP_K],
            "hybrid_v02": fused_pool[:TOP_K],
            "hybrid_v03": diversifier.select(fused_pool, top_k=TOP_K),
            "reranked": select_reranked_candidates(reranked_pool, TOP_K),
            "reranked_diverse": select_reranked_candidates(reranked_pool, TOP_K, diversifier),
        }
        for label, candidates in arms.items():
            rankings[label][qid] = unique_ranked_document_ids(candidates)
        # Expected evidence is used only for evaluation, never supplied to the scorer.
        traces.append({
            "question_id": qid, "query": query,
            "expected_document_ids": list(question.expected_evidence),
            "retrieval_seconds": retrieval_seconds, "rerank_seconds": rerank_seconds,
            "final_chunk_ids": {label: [c.chunk.chunk_id for c in values]
                                for label, values in arms.items()},
            "final_document_ids": {label: list(rankings[label][qid]) for label in labels},
            "reranked_pool": [{
                "chunk_id": c.chunk.chunk_id, "document_id": c.chunk.document_id,
                "fusion_rank": c.source.rank, "fusion_score": c.source.score,
                "rerank_rank": c.rerank_rank, "rerank_score": c.score,
                "retrieval_methods": list(c.retrieval_methods),
                "source_path": c.chunk.source_path.as_posix(),
                "source_block_ids": list(c.chunk.source_block_ids),
                "section_path": list(c.chunk.section_path),
                "page_numbers": list(c.chunk.page_numbers),
                "slide_numbers": list(c.chunk.slide_numbers),
                "sheet_names": list(c.chunk.sheet_names), "text": c.chunk.text,
            } for c in reranked_pool],
        })
        print(f"{qid}: rerank={rerank_seconds:.2f}s; "
              f"v0.3={','.join(rankings['hybrid_v03'][qid])}; "
              f"rerank+diversity={','.join(rankings['reranked_diverse'][qid])}", flush=True)

    reports = {label: RetrievalEvaluator().evaluate(
        golden_set=golden_set, available_document_ids=available_ids,
        ranked_results_by_question=rankings[label],
    ) for label in labels}
    if any(report.evaluated_questions != 13 for report in reports.values()):
        raise RuntimeError("Every arm must evaluate the same 13 positive questions.")
    metrics = {label: {name: getattr(report, attr) for name, attr in METRICS.items()}
               for label, report in reports.items()}
    assessments = {label: assess_experiment(metrics["hybrid_v03"], metrics[label])
                   for label in ("reranked", "reranked_diverse")}
    current_fingerprints = fingerprints(Path(path) for path in initial_fingerprints)
    snapshot_stable = initial_fingerprints == current_fingerprints
    if not snapshot_stable:
        for assessment in assessments.values():
            assessment["decision"] = "INPUT_CHANGED_DURING_RUN"
    payload = {
        "experiment": "RV-008", "status": "EXPERIMENT_COMPLETE",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "metric_scope": "RV-007-compatible: first-occurrence document ranking from final Top-5 chunks",
        "configuration": {"model": scorer.model_name, "revision": scorer.revision,
            "device": scorer.device, "batch_size": scorer.batch_size,
            "max_length": scorer.max_length, "truncation": "only_second",
            "rerank_text": "build_search_text(chunk)", "lexical_text": "chunk.text",
            "candidate_depth": DEPTH, "rrf_k": RRF_K, "top_k": TOP_K,
            "document_count": 10, "chunk_count": 79, "positive_questions": 13,
            "query_language": "original Portuguese", "translation": False,
            "embedding_model": EMBEDDING_MODEL},
        "versions": installed_versions(), "model_load_seconds": model_load_seconds,
        "input_fingerprints": initial_fingerprints, "snapshot_stable": snapshot_stable,
        "frozen_v03_metrics": FROZEN_V03, "metrics": metrics,
        "assessments": assessments, "questions": traces,
        "pending_validation": ["manual passage relevance and sufficiency",
            "same-document multi-passage evidence", "abstention (Q29)",
            "answer grounding, citations, freshness and authority"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("\n" + f"{'Metric':<12}" + "".join(f"{label:>19}" for label in labels))
    for name in METRICS:
        print(f"{name:<12}" + "".join(f"{metrics[label][name]:>19.4f}" for label in labels))
    for label, assessment in assessments.items():
        print(f"{label}: {assessment['decision']}")
    print(f"\nSaved: {args.output}")
    print("Experiment completed. No production configuration was changed; passage review remains pending.")


if __name__ == "__main__":
    main()
