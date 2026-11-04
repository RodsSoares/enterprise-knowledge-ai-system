"""RV-004 — paired Vector-only vs Hybrid RRF benchmark on Golden Set A.

Run from repository root:
    python -m tests.smoke.smoke_golden_set_hybrid_retrieval

Uses the RV-003 corpus, ingestion, chunking, eligibility and evaluation logic.
Does not modify or overwrite the RV-003 baseline script.
"""

from app.evaluation.golden_set_loader import GoldenSetLoader
from app.evaluation.retrieval_evaluator import RetrievalEvaluator
from app.retrieval.candidate_fusion import ReciprocalRankFusion
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


def run_retrieval(questions, retriever, *, label: str, top_k: int):
    ranked_results = {}
    print(f"\n[{label}] Retrieval results")
    for question in questions:
        candidates = retriever.retrieve(query=question.question, top_k=top_k)
        if not candidates:
            raise RuntimeError(f"{label} returned no candidates for {question.question_id}")
        documents = unique_ranked_document_ids(candidates)
        ranked_results[question.question_id] = documents
        print(f"  {question.question_id}: expected={','.join(question.expected_evidence)}; "
              f"retrieved={','.join(documents)}")
    return ranked_results


def print_report(label, report):
    print(f"\n{label} | n={report.evaluated_questions}")
    print(f"  Hit@1:    {report.mean_hit_at_1:.1%}")
    print(f"  Hit@3:    {report.mean_hit_at_3:.1%}")
    print(f"  Hit@5:    {report.mean_hit_at_5:.1%}")
    print(f"  Recall@1: {report.mean_recall_at_1:.1%}")
    print(f"  Recall@3: {report.mean_recall_at_3:.1%}")
    print(f"  Recall@5: {report.mean_recall_at_5:.1%}")
    print(f"  MRR:      {report.mean_reciprocal_rank:.4f}")


def main():
    validate_sources()
    golden_set = GoldenSetLoader().load()
    available_document_ids = {document_id_from_path(path) for path in SOURCE_PATHS}
    eligibility = golden_set.classify_for_corpus(available_document_ids)
    positives = [item.question for item in eligibility
                 if item.evaluable and item.question.expected_evidence]
    deferred = [item.question.question_id for item in eligibility
                if item.evaluable and not item.question.expected_evidence]
    if not positives:
        raise RuntimeError("No corpus-eligible positive Golden Set questions")

    print("RV-004 — Paired Golden Set A Vector vs Hybrid RRF")
    print(f"Documents={len(SOURCE_PATHS)}, positive_questions={len(positives)}, "
          f"deferred={deferred}, top_k={TOP_K}, candidate_depth={CANDIDATE_DEPTH}, "
          f"rrf_k={RRF_K}")
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
    hybrid = HybridRetriever(vector_retriever=vector, lexical_retriever=lexical,
                             fusion=ReciprocalRankFusion(k=RRF_K),
                             candidate_depth=CANDIDATE_DEPTH)

    vector_rankings = run_retrieval(positives, vector, label="Vector-only", top_k=TOP_K)
    hybrid_rankings = run_retrieval(positives, hybrid, label="Hybrid RRF", top_k=TOP_K)

    evaluator = RetrievalEvaluator()
    vector_report = evaluator.evaluate(golden_set=golden_set,
        available_document_ids=available_document_ids,
        ranked_results_by_question=vector_rankings)
    hybrid_report = evaluator.evaluate(golden_set=golden_set,
        available_document_ids=available_document_ids,
        ranked_results_by_question=hybrid_rankings)
    if vector_report.evaluated_questions != hybrid_report.evaluated_questions:
        raise RuntimeError("Evaluation denominators differ")
    print_report("RV-004 Vector-only (same-run control)", vector_report)
    print_report("RV-004 Hybrid RRF", hybrid_report)

    print("\nPer-question first expected-document rank (document-level):")
    for question in positives:
        expected = set(question.expected_evidence)
        def rank_of(ranking):
            return next((i for i, doc in enumerate(ranking, start=1) if doc in expected), None)
        vr = rank_of(vector_rankings[question.question_id])
        hr = rank_of(hybrid_rankings[question.question_id])
        print(f"  {question.question_id}: vector={vr or 'MISS'}, hybrid={hr or 'MISS'}")

    print("\nDelta (Hybrid - Vector):")
    for label, attr, percent in (
        ("Hit@1", "mean_hit_at_1", True),
        ("Hit@3", "mean_hit_at_3", True),
        ("Hit@5", "mean_hit_at_5", True),
        ("Recall@5", "mean_recall_at_5", True),
        ("MRR", "mean_reciprocal_rank", False),
    ):
        delta = getattr(hybrid_report, attr) - getattr(vector_report, attr)
        print(f"  {label}: {delta:+.1%} pp" if percent else f"  {label}: {delta:+.4f}")
    print("\nRV-004 comparison: COMPLETE (no minimum metric threshold imposed)")


if __name__ == "__main__":
    main()
