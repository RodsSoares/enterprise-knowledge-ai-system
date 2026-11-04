"""RV-005 — Inspect Vector, BM25 and RRF candidate rankings without changing RV-004.

Run from repository root:
    python -m tests.smoke.smoke_retrieval_diagnostics

Uses the same corpus and Golden Set eligibility as RV-003/RV-004.
"""

from app.evaluation.golden_set_loader import GoldenSetLoader
from app.retrieval.candidate_fusion import ReciprocalRankFusion
from app.retrieval.lexical_index import BM25LexicalIndex
from app.retrieval.lexical_retriever import LexicalRetriever
from app.retrieval.openai_embeddings import OpenAIEmbeddingProvider
from app.retrieval.vector_index import NumPyVectorIndex
from app.retrieval.vector_indexer import VectorIndexer
from app.retrieval.vector_retriever import VectorRetriever
from tests.smoke.smoke_golden_set_vector_retrieval import (
    SOURCE_PATHS,
    build_chunks,
    document_id_from_path,
    validate_global_chunk_identity,
    validate_sources,
)

DIAGNOSTIC_QUESTION_IDS = ("Q20", "Q26", "Q32", "Q34")
CANDIDATE_DEPTH = 20
FINAL_TOP_K = 5
RRF_K = 60


def document_ranks(candidates):
    """First occurrence of each document in a chunk-level ranking (1-based)."""
    ranks = {}
    for position, candidate in enumerate(candidates, start=1):
        ranks.setdefault(candidate.chunk.document_id, position)
    return ranks


def print_ranking(label, candidates, expected):
    print(f"\n  {label}: {len(candidates)} chunks")
    for position, candidate in enumerate(candidates, start=1):
        document_id = candidate.chunk.document_id
        marker = "*" if document_id in expected else " "
        methods = getattr(candidate, "retrieval_methods", None)
        method_info = f" methods={','.join(methods)}" if methods else ""
        print(
            f"    {marker} {position:02d} doc={document_id} "
            f"chunk={candidate.chunk.chunk_id} "
            f"score={candidate.score:.6f}{method_info}"
        )


def print_expected_positions(expected, vector, lexical, fused, final):
    rankings = {
        "Vector@20": document_ranks(vector),
        "BM25@20": document_ranks(lexical),
        "RRF@20": document_ranks(fused),
        "RRF@5": document_ranks(final),
    }
    print("\n  Expected-document first chunk positions:")
    print("    Document  Vector@20  BM25@20  RRF@20  RRF@5")
    for document_id in expected:
        positions = [str(rankings[name].get(document_id, "MISS")) for name in rankings]
        print(f"    {document_id:<9} {positions[0]:<10} {positions[1]:<8} "
              f"{positions[2]:<7} {positions[3]}")

    missing_vector = set(expected) - set(rankings["Vector@20"])
    missing_lexical = set(expected) - set(rankings["BM25@20"])
    missing_union = missing_vector & missing_lexical
    missing_fusion = set(expected) - set(rankings["RRF@5"])
    print(f"  Missing from both candidate pools: {sorted(missing_union) or 'NONE'}")
    print(f"  Missing from final Top-5: {sorted(missing_fusion) or 'NONE'}")
    if missing_fusion and not missing_union:
        print("  Diagnosis: expected evidence entered at least one pool but not final Top-5.")
    elif missing_union:
        print("  Diagnosis: at least one expected document absent from both Top-20 pools.")


def main():
    validate_sources()
    golden_set = GoldenSetLoader().load()
    available_ids = {document_id_from_path(path) for path in SOURCE_PATHS}
    eligibility = golden_set.classify_for_corpus(available_ids)
    positives = {
        item.question.question_id: item.question
        for item in eligibility
        if item.evaluable and item.question.expected_evidence
    }
    unavailable = set(DIAGNOSTIC_QUESTION_IDS) - set(positives)
    if unavailable:
        raise RuntimeError(f"Diagnostic questions not eligible: {sorted(unavailable)}")

    print("RV-005 — Retrieval Diagnostics")
    print(f"Corpus documents={len(SOURCE_PATHS)}; candidate_depth={CANDIDATE_DEPTH}; "
          f"final_top_k={FINAL_TOP_K}; rrf_k={RRF_K}")
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
    depth = min(CANDIDATE_DEPTH, len(chunks))

    for question_id in DIAGNOSTIC_QUESTION_IDS:
        question = positives[question_id]
        expected = tuple(question.expected_evidence)
        print("\n" + "=" * 100)
        print(f"{question_id}: {question.question}")
        print(f"Expected documents: {', '.join(expected)}")
        vector_candidates = vector.retrieve(query=question.question, top_k=depth)
        lexical_candidates = lexical.retrieve(query=question.question, top_k=depth)
        fused_candidates = fusion.fuse((vector_candidates, lexical_candidates), top_k=depth)
        final_candidates = fused_candidates[:FINAL_TOP_K]
        print_ranking("Vector", vector_candidates, expected)
        print_ranking("BM25", lexical_candidates, expected)
        print_ranking("RRF candidate pool", fused_candidates, expected)
        print_ranking("RRF final Top-5", final_candidates, expected)
        print_expected_positions(expected, vector_candidates, lexical_candidates,
                                 fused_candidates, final_candidates)

    print("\nRV-005 diagnostics: COMPLETE (diagnostic only; no pass/fail quality threshold)")


if __name__ == "__main__":
    main()
