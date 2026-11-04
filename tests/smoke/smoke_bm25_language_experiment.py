"""RV-006A — Controlled language-alignment experiment for BM25.

Run: python -m tests.smoke.smoke_bm25_language_experiment

The vector branch ALWAYS receives the original Portuguese Golden Set question.
Only the BM25 branch receives either Portuguese or a fixed English translation.
Translations are experimental fixtures, not production translation logic.
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
from tests.smoke.smoke_golden_set_vector_retrieval import (
    SOURCE_PATHS, TOP_K, build_chunks, document_id_from_path,
    unique_ranked_document_ids, validate_global_chunk_identity, validate_sources,
)

CANDIDATE_DEPTH = 20
RRF_K = 60

# Fixed, manually authored translations. Do not edit the Golden Set source questions.
ENGLISH_QUERIES = {
    "Q05": "What is the financial limit for contracting without executive management approval?",
    "Q20": "Which internal policies apply to sharing data with transportation carriers?",
    "Q21": "What information is classified as confidential in logistics documents?",
    "Q22": "Can an employee email customer data to a transportation carrier?",
    "Q23": "What is the correct procedure if confidential data is accidentally sent to a supplier?",
    "Q25": "Which document takes precedence when an SOP conflicts with a corporate policy?",
    "Q26": "What is the current effective version of the supplier management policy?",
    "Q31": "Can I use AI to analyze supplier contracts?",
    "Q32": "What approvals are required to use AI with supplier data?",
    "Q33": "What security requirements apply to the use of AI?",
    "Q34": "Who approves a new AI tool?",
    "Q35": "Can I enter confidential data into an AI tool?",
    "Q36": "What training is mandatory for employees who use AI?",
}


def evaluate(label, golden_set, available_ids, rankings):
    report = RetrievalEvaluator().evaluate(
        golden_set=golden_set,
        available_document_ids=available_ids,
        ranked_results_by_question=rankings,
    )
    print(f"\n{label} | n={report.evaluated_questions}")
    for metric, attr, fmt in (
        ("Hit@1", "mean_hit_at_1", ".1%"),
        ("Hit@3", "mean_hit_at_3", ".1%"),
        ("Hit@5", "mean_hit_at_5", ".1%"),
        ("Recall@1", "mean_recall_at_1", ".1%"),
        ("Recall@3", "mean_recall_at_3", ".1%"),
        ("Recall@5", "mean_recall_at_5", ".1%"),
        ("MRR", "mean_reciprocal_rank", ".4f"),
    ):
        print(f"  {metric:<9} {format(getattr(report, attr), fmt)}")
    return report


def main():
    validate_sources()
    golden_set = GoldenSetLoader().load()
    available_ids = {document_id_from_path(path) for path in SOURCE_PATHS}
    eligibility = golden_set.classify_for_corpus(available_ids)
    questions = [item.question for item in eligibility
                 if item.evaluable and item.question.expected_evidence]
    actual_ids = {question.question_id for question in questions}
    if actual_ids != set(ENGLISH_QUERIES):
        raise RuntimeError(
            "Translation fixtures do not match eligible positive questions. "
            f"Missing={sorted(actual_ids - set(ENGLISH_QUERIES))}; "
            f"Extra={sorted(set(ENGLISH_QUERIES) - actual_ids)}"
        )

    print("RV-006A — BM25 Portuguese vs fixed English translation")
    print(f"Documents={len(SOURCE_PATHS)}, questions={len(questions)}, "
          f"top_k={TOP_K}, candidate_depth={CANDIDATE_DEPTH}, rrf_k={RRF_K}")
    chunks = build_chunks()
    validate_global_chunk_identity(chunks)
    print(f"Chunks={len(chunks)}")

    provider = OpenAIEmbeddingProvider.from_environment()
    index = NumPyVectorIndex()
    VectorIndexer(embedding_provider=provider, vector_index=index).index(chunks)
    vector = VectorRetriever(embedding_provider=provider, vector_index=index, chunks=chunks)
    lexical_index = BM25LexicalIndex()
    lexical_index.add([chunk.chunk_id for chunk in chunks],
                      [chunk.text for chunk in chunks])
    lexical = LexicalRetriever(lexical_index=lexical_index, chunks=chunks)
    fusion = ReciprocalRankFusion(k=RRF_K)
    depth = min(CANDIDATE_DEPTH, len(chunks))

    rankings = {"Vector-only": {}, "Hybrid PT": {}, "Hybrid EN-BM25": {}}
    print("\nPer-question results (first occurrence of each document):")
    for question in questions:
        qid = question.question_id
        vector_candidates = vector.retrieve(query=question.question, top_k=depth)
        lexical_pt = lexical.retrieve(query=question.question, top_k=depth)
        lexical_en = lexical.retrieve(query=ENGLISH_QUERIES[qid], top_k=depth)
        if not vector_candidates:
            raise RuntimeError(f"Vector retrieval returned no candidates for {qid}")
        outputs = {
            "Vector-only": vector_candidates[:TOP_K],
            "Hybrid PT": fusion.fuse((vector_candidates, lexical_pt), top_k=TOP_K),
            "Hybrid EN-BM25": fusion.fuse((vector_candidates, lexical_en), top_k=TOP_K),
        }
        print(f"\n  {qid}: expected={','.join(question.expected_evidence)}; "
              f"BM25_PT={len(lexical_pt)} BM25_EN={len(lexical_en)}")
        for label, candidates in outputs.items():
            docs = unique_ranked_document_ids(candidates)
            rankings[label][qid] = docs
            print(f"    {label:<15} {','.join(docs)}")
        for label, candidates in (("BM25 PT", lexical_pt), ("BM25 EN", lexical_en)):
            docs = unique_ranked_document_ids(candidates)
            print(f"    {label:<15} {','.join(docs[:8]) or 'NONE'}")

    reports = {label: evaluate(label, golden_set, available_ids, data)
               for label, data in rankings.items()}
    baseline = reports["Hybrid PT"]
    experimental = reports["Hybrid EN-BM25"]
    print("\nDelta (Hybrid EN-BM25 minus Hybrid PT):")
    for metric, attr in (
        ("Hit@1", "mean_hit_at_1"),
        ("Hit@3", "mean_hit_at_3"),
        ("Hit@5", "mean_hit_at_5"),
        ("Recall@5", "mean_recall_at_5"),
        ("MRR", "mean_reciprocal_rank"),
    ):
        delta = getattr(experimental, attr) - getattr(baseline, attr)
        print(f"  {metric:<9} {delta:+.4f}" +
              (" (fraction; multiply by 100 for percentage points)" if metric != "MRR" else ""))
    print("\nRV-006A: COMPLETE (diagnostic experiment; no quality gate)")


if __name__ == "__main__":
    main()
