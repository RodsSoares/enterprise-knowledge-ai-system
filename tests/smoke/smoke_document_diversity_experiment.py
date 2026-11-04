"""RV-006B — Controlled document-diversity experiment.

Destination: tests/smoke/smoke_document_diversity_experiment.py
Run: python -m tests.smoke.smoke_document_diversity_experiment

No production retriever changes. Compare Top-5 from the same Top-20 RRF pool.
The diversity selector preserves rank #1, then selects one candidate per unseen
source document, then fills any remaining slots by original RRF order.
"""

from app.evaluation.golden_set_loader import GoldenSetLoader
from app.evaluation.retrieval_evaluator import RetrievalEvaluator
from app.retrieval.candidate_fusion import ReciprocalRankFusion
from app.retrieval.lexical_index import BM25LexicalIndex
from app.retrieval.lexical_retriever import LexicalRetriever
from app.retrieval.openai_embeddings import OpenAIEmbeddingProvider
from app.retrieval.vector_index import NumPyVectorIndex
from app.retrieval.vector_indexer import VectorIndexer
from app.retrieval.vector_retriever import VectorRetriever
from tests.smoke.smoke_bm25_language_experiment import ENGLISH_QUERIES
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


def diversify_by_document(candidates, top_k=TOP_K):
    """Rank-preserving document coverage, with original #1 pinned.

    Return original candidate objects: the rank property remains the original
    RRF rank, while list order defines the new evaluation rank. This function
    is for benchmark output only, not a production ranking contract.
    """
    if top_k < 1:
        raise ValueError("top_k must be >= 1")
    if not candidates:
        return ()

    selected = [candidates[0]]
    seen_chunks = {candidates[0].chunk.chunk_id}
    seen_documents = {candidates[0].chunk.document_id}

    for candidate in candidates[1:]:
        if len(selected) >= top_k:
            break
        doc_id = candidate.chunk.document_id
        if doc_id not in seen_documents:
            selected.append(candidate)
            seen_chunks.add(candidate.chunk.chunk_id)
            seen_documents.add(doc_id)

    for candidate in candidates[1:]:
        if len(selected) >= top_k:
            break
        if candidate.chunk.chunk_id not in seen_chunks:
            selected.append(candidate)
            seen_chunks.add(candidate.chunk.chunk_id)

    return tuple(selected)


def evaluate(label, golden_set, available_ids, rankings):
    report = RetrievalEvaluator().evaluate(
        golden_set=golden_set,
        available_document_ids=available_ids,
        ranked_results_by_question=rankings,
    )
    print(f"\n{label} | n={report.evaluated_questions}")
    for name, attribute, spec in (
        ("Hit@1", "mean_hit_at_1", ".1%"),
        ("Hit@3", "mean_hit_at_3", ".1%"),
        ("Hit@5", "mean_hit_at_5", ".1%"),
        ("Recall@1", "mean_recall_at_1", ".1%"),
        ("Recall@3", "mean_recall_at_3", ".1%"),
        ("Recall@5", "mean_recall_at_5", ".1%"),
        ("MRR", "mean_reciprocal_rank", ".4f"),
    ):
        print(f"  {name:<9} {format(getattr(report, attribute), spec)}")
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
    question_ids = {q.question_id for q in questions}
    if question_ids != set(ENGLISH_QUERIES):
        raise RuntimeError("Golden Set and RV-006A translation fixtures differ")

    print("RV-006B — RRF document diversity (experimental, not production)")
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
    lexical_index.add(
        [chunk.chunk_id for chunk in chunks],
        [chunk.text for chunk in chunks],
    )
    lexical = LexicalRetriever(lexical_index=lexical_index, chunks=chunks)
    fusion = ReciprocalRankFusion(k=RRF_K)
    depth = min(CANDIDATE_DEPTH, len(chunks))

    labels = (
        "Vector-only",
        "Hybrid PT",
        "Hybrid PT + diversity",
        "Hybrid EN",
        "Hybrid EN + diversity",
    )
    rankings = {label: {} for label in labels}

    print("\nPer-question document rankings (first occurrence in final Top-5):")
    for question in questions:
        qid = question.question_id
        vector_candidates = vector.retrieve(query=question.question, top_k=depth)
        if not vector_candidates:
            raise RuntimeError(f"No vector candidates for {qid}")
        lexical_pt = lexical.retrieve(query=question.question, top_k=depth)
        lexical_en = lexical.retrieve(query=ENGLISH_QUERIES[qid], top_k=depth)

        # Fuse at depth 20 BEFORE diversity. Diversifying an already truncated
        # Top-5 would not expose relevant evidence at ranks 6-20.
        fused_pt = fusion.fuse((vector_candidates, lexical_pt), top_k=depth)
        fused_en = fusion.fuse((vector_candidates, lexical_en), top_k=depth)
        outputs = {
            "Vector-only": vector_candidates[:TOP_K],
            "Hybrid PT": fused_pt[:TOP_K],
            "Hybrid PT + diversity": diversify_by_document(fused_pt, TOP_K),
            "Hybrid EN": fused_en[:TOP_K],
            "Hybrid EN + diversity": diversify_by_document(fused_en, TOP_K),
        }
        print(f"\n  {qid} expected={','.join(question.expected_evidence)}")
        for label in labels:
            candidates = outputs[label]
            docs = unique_ranked_document_ids(candidates)
            rankings[label][qid] = docs
            missing = sorted(set(question.expected_evidence) - set(docs))
            print(f"    {label:<23} {','.join(docs):<40} "
                  f"missing={','.join(missing) if missing else '-'}")

    reports = {
        label: evaluate(label, golden_set, available_ids, rankings[label])
        for label in labels
    }
    print("\nDelta versus corresponding non-diversified hybrid:")
    for base_label, diverse_label in (
        ("Hybrid PT", "Hybrid PT + diversity"),
        ("Hybrid EN", "Hybrid EN + diversity"),
    ):
        print(f"  {diverse_label} - {base_label}")
        for name, attr in (
            ("Hit@1", "mean_hit_at_1"),
            ("Hit@3", "mean_hit_at_3"),
            ("Hit@5", "mean_hit_at_5"),
            ("Recall@5", "mean_recall_at_5"),
            ("MRR", "mean_reciprocal_rank"),
        ):
            delta = getattr(reports[diverse_label], attr) - getattr(reports[base_label], attr)
            suffix = " pp" if name != "MRR" else ""
            scale = 100 if suffix else 1
            print(f"    {name:<9} {delta * scale:+.2f}{suffix}")

    print("\nRV-006B: COMPLETE (no quality threshold imposed)")


if __name__ == "__main__":
    main()
