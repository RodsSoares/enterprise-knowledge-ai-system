"""RV-007: End-to-end validation of HybridRetriever v0.3.

Destination: tests/smoke/smoke_hybrid_v03_end_to_end.py
Run: python -m tests.smoke.smoke_hybrid_v03_end_to_end

Uses the original Portuguese questions and the same 10-document corpus.
Checks backward compatibility and document-diversity performance, without
introducing translated queries or changing the evaluation definitions.
"""

from math import isclose

from app.evaluation.golden_set_loader import GoldenSetLoader
from app.evaluation.retrieval_evaluator import RetrievalEvaluator
from app.retrieval.candidate_fusion import ReciprocalRankFusion
from app.retrieval.document_diversifier import DocumentDiversifier
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.lexical_index import BM25LexicalIndex
from app.retrieval.lexical_retriever import LexicalRetriever
from app.retrieval.openai_embeddings import OpenAIEmbeddingProvider
from app.retrieval.vector_index import NumPyVectorIndex
from app.retrieval.vector_indexer import VectorIndexer
from app.retrieval.vector_retriever import VectorRetriever
from tests.smoke.smoke_golden_set_vector_retrieval import (
    SOURCE_PATHS,
    TOP_K,
    build_chunks,
    document_id_from_path,
    unique_ranked_document_ids,
    validate_global_chunk_identity,
    validate_sources,
)

CANDIDATE_DEPTH = 20
RRF_K = 60
TOLERANCE = 1e-9
METRICS = (
    ("Hit@1", "mean_hit_at_1"),
    ("Hit@3", "mean_hit_at_3"),
    ("Hit@5", "mean_hit_at_5"),
    ("Recall@1", "mean_recall_at_1"),
    ("Recall@3", "mean_recall_at_3"),
    ("Recall@5", "mean_recall_at_5"),
    ("MRR", "mean_reciprocal_rank"),
)


def assert_close(actual, expected, label):
    if not isclose(actual, expected, rel_tol=0, abs_tol=TOLERANCE):
        raise AssertionError(f"{label}: expected {expected:.9f}, got {actual:.9f}")


def evaluate(label, golden_set, available_ids, rankings):
    report = RetrievalEvaluator().evaluate(
        golden_set=golden_set,
        available_document_ids=available_ids,
        ranked_results_by_question=rankings,
    )
    print(f"\n{label} | n={report.evaluated_questions}")
    for name, attr in METRICS:
        value = getattr(report, attr)
        print(f"  {name:<9} {value:.4f}" if name == "MRR" else f"  {name:<9} {value:.1%}")
    return report


def main():
    validate_sources()
    golden_set = GoldenSetLoader().load()
    available_ids = {document_id_from_path(path) for path in SOURCE_PATHS}
    questions = [
        item.question
        for item in golden_set.classify_for_corpus(available_ids)
        if item.evaluable and item.question.expected_evidence
    ]
    if len(questions) != 13:
        raise AssertionError(f"Expected 13 eligible positive questions, got {len(questions)}")

    print("RV-007 — Integrated HybridRetriever v0.3 E2E validation")
    print(f"Documents={len(SOURCE_PATHS)}; questions={len(questions)}; "
          f"Top-{TOP_K}; candidate_depth={CANDIDATE_DEPTH}; RRF k={RRF_K}")
    chunks = build_chunks()
    validate_global_chunk_identity(chunks)
    print(f"Chunks={len(chunks)}")

    provider = OpenAIEmbeddingProvider.from_environment()
    vector_index = NumPyVectorIndex()
    VectorIndexer(embedding_provider=provider, vector_index=vector_index).index(chunks)
    vector = VectorRetriever(embedding_provider=provider, vector_index=vector_index, chunks=chunks)

    lexical_index = BM25LexicalIndex()
    lexical_index.add([chunk.chunk_id for chunk in chunks], [chunk.text for chunk in chunks])
    lexical = LexicalRetriever(lexical_index=lexical_index, chunks=chunks)
    fusion = ReciprocalRankFusion(k=RRF_K)
    legacy = HybridRetriever(vector, lexical, fusion, candidate_depth=CANDIDATE_DEPTH)
    diversified = HybridRetriever(
        vector, lexical, fusion, candidate_depth=CANDIDATE_DEPTH,
        document_diversifier=DocumentDiversifier(),
    )

    labels = ("Vector-only", "Hybrid v0.2-compatible", "Hybrid v0.3 + diversity")
    rankings = {label: {} for label in labels}
    print("\nPer-question rankings (unique documents from final Top-5):")
    for question in questions:
        qid = question.question_id
        query = question.question
        vector_top = vector.retrieve(query, top_k=TOP_K)
        legacy_top = legacy.retrieve(query, top_k=TOP_K)
        diverse_top = diversified.retrieve(query, top_k=TOP_K)

        # Verify unchanged legacy behavior against direct fusion.
        depth = max(TOP_K, CANDIDATE_DEPTH)
        direct = fusion.fuse(
            (vector.retrieve(query, top_k=depth), lexical.retrieve(query, top_k=depth)),
            top_k=TOP_K,
        )
        if [c.chunk.chunk_id for c in legacy_top] != [c.chunk.chunk_id for c in direct]:
            raise AssertionError(f"{qid}: legacy HybridRetriever differs from direct RRF")

        for label, candidates in zip(labels, (vector_top, legacy_top, diverse_top)):
            if [c.rank for c in candidates] != list(range(1, len(candidates) + 1)):
                raise AssertionError(f"{qid}: nonconsecutive ranks in {label}")
            if len({c.chunk.chunk_id for c in candidates}) != len(candidates):
                raise AssertionError(f"{qid}: duplicate chunk in {label}")
            docs = unique_ranked_document_ids(candidates)
            rankings[label][qid] = docs
            missing = sorted(set(question.expected_evidence) - set(docs))
            print(f"  {qid} {label:<24} docs={','.join(docs):<39} "
                  f"missing={','.join(missing) if missing else '-'}")

    reports = {
        label: evaluate(label, golden_set, available_ids, rankings[label])
        for label in labels
    }
    baseline = reports["Hybrid v0.2-compatible"]
    current = reports["Hybrid v0.3 + diversity"]
    if baseline.evaluated_questions != 13 or current.evaluated_questions != 13:
        raise AssertionError("Evaluation must include exactly 13 positive questions")

    # Reproduce the RV-006B metrics in the integrated production interface.
    assert_close(baseline.mean_recall_at_5, 12 / 13, "Legacy Recall@5")
    assert_close(current.mean_recall_at_5, 1.0, "Diversified Recall@5")
    for name, attr in METRICS:
        if name == "Recall@5":
            continue
        assert_close(getattr(current, attr), getattr(baseline, attr), f"No-regression {name}")
    assert_close(current.mean_hit_at_1, 10 / 13, "Diversified Hit@1")
    assert_close(current.mean_hit_at_3, 1.0, "Diversified Hit@3")
    assert_close(current.mean_hit_at_5, 1.0, "Diversified Hit@5")
    assert_close(current.mean_reciprocal_rank, 0.8846153846153846, "Diversified MRR")

    print("\nRV-007: PASS — v0.2 compatibility and v0.3 diversified retrieval verified")
    print("Note: document-level retrieval metrics do not validate answer correctness or citations.")


if __name__ == "__main__":
    main()
