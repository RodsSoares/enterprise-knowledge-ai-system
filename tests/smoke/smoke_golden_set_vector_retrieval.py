"""Golden Set A — multi-format real vector retrieval benchmark.

The benchmark deliberately consumes the public IngestionRouter instead of
selecting format-specific parsers. This validates the same ingestion boundary
that a future UI/API will use.

Run from repository root:
    python -m tests.smoke.smoke_golden_set_vector_retrieval
"""

from pathlib import Path

from app.chunking.structure_aware_chunker import StructureAwareChunker
from app.evaluation.golden_set_loader import GoldenSetLoader
from app.evaluation.retrieval_evaluator import RetrievalEvaluator
from app.ingestion.ingestion_router import IngestionRouter
from app.retrieval.openai_embeddings import OpenAIEmbeddingProvider
from app.retrieval.vector_index import NumPyVectorIndex
from app.retrieval.vector_indexer import VectorIndexer
from app.retrieval.vector_retriever import VectorRetriever


SOURCE_PATHS = (
    Path("data/source/corporate_repository/policies/DOC-005_Data_Sharing_Policy.pdf"),
    Path("data/source/corporate_repository/policies/DOC-006_Information_Security_Policy.pdf"),
    Path("data/source/corporate_repository/policies/DOC-007_Document_Governance_Policy.pdf"),
    Path("data/source/corporate_repository/sops/DOC-010_Security_Incident_SOP.docx"),
    Path("data/source/corporate_repository/governance/DOC-012_Approval_Authority_Matrix.xlsx"),
    Path("data/source/corporate_repository/policies/DOC-022_Supplier_Management_Policy.pdf"),
    Path("data/source/corporate_repository/policies/DOC-023_AI_Governance_Policy.pdf"),
    Path("data/source/corporate_repository/standards/DOC-024_AI_Security_Standard.pdf"),
    Path("data/source/corporate_repository/guidelines/DOC-025_AI_Procurement_Guidelines.md"),
    Path("data/source/corporate_repository/guidelines/DOC-026_AI_Workforce_Enablement_Guide.pptx"),
)

TOP_K = 5
TARGET_CHARS = 1200
MAX_CHARS = 1800


def document_id_from_path(source_path: Path) -> str:
    return source_path.stem.split("_", 1)[0]


def validate_sources() -> None:
    missing = [path for path in SOURCE_PATHS if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Expected corpus documents were not found:\n"
            + "\n".join(f"  - {path}" for path in missing)
        )


def build_chunks():
    ingestion = IngestionRouter()
    chunker = StructureAwareChunker(
        target_chars=TARGET_CHARS,
        max_chars=MAX_CHARS,
    )
    all_chunks = []

    for source_path in SOURCE_PATHS:
        document_id = document_id_from_path(source_path)
        print(f"      Processing: {source_path.name}")

        content = ingestion.parse(source_path)
        chunks = chunker.chunk(content, source_path, document_id)

        if not chunks:
            raise RuntimeError(f"No retrieval chunks produced for {source_path}.")

        actual_ids = {chunk.document_id for chunk in chunks}
        if actual_ids != {document_id}:
            raise RuntimeError(
                f"Unexpected document identity for {source_path.name}. "
                f"Expected {document_id!r}; got {sorted(actual_ids)}."
            )

        print(
            f"      {document_id}: "
            f"{len(content.blocks)} canonical blocks -> {len(chunks)} chunks"
        )
        all_chunks.extend(chunks)

    return all_chunks


def validate_global_chunk_identity(chunks) -> None:
    chunk_ids = [chunk.chunk_id for chunk in chunks]
    if len(set(chunk_ids)) != len(chunk_ids):
        raise RuntimeError("Duplicate global chunk IDs detected.")

    expected_documents = {document_id_from_path(path) for path in SOURCE_PATHS}
    actual_documents = {chunk.document_id for chunk in chunks}

    if actual_documents != expected_documents:
        raise RuntimeError(
            "Corpus document identities do not match configuration. "
            f"Expected {sorted(expected_documents)}; "
            f"got {sorted(actual_documents)}."
        )

    for chunk in chunks:
        if not chunk.chunk_id.startswith(f"{chunk.document_id}::chunk-"):
            raise RuntimeError(
                f"Chunk {chunk.chunk_id!r} does not preserve "
                f"document identity {chunk.document_id!r}."
            )

    print(f"      Documents represented: {len(actual_documents)}")
    print(f"      Unique chunk IDs: {len(set(chunk_ids))}/{len(chunk_ids)}")
    print("      Global chunk identity: PASS")


def unique_ranked_document_ids(candidates) -> tuple[str, ...]:
    """Project chunk-level retrieval into first-occurrence document ranking."""
    seen: set[str] = set()
    ranked: list[str] = []

    for candidate in candidates:
        document_id = candidate.chunk.document_id
        if document_id not in seen:
            seen.add(document_id)
            ranked.append(document_id)

    return tuple(ranked)


def main() -> None:
    validate_sources()

    golden_set = GoldenSetLoader().load()
    available_document_ids = {
        document_id_from_path(path) for path in SOURCE_PATHS
    }
    eligibility = golden_set.classify_for_corpus(available_document_ids)

    corpus_eligible = [item for item in eligibility if item.evaluable]
    positive_questions = [
        item.question
        for item in corpus_eligible
        if item.question.expected_evidence
    ]
    deferred_questions = [
        item.question
        for item in corpus_eligible
        if not item.question.expected_evidence
    ]

    print("Golden Set A — real vector retrieval benchmark")
    print(f"Golden questions: {len(golden_set.questions)}")
    print(f"Materialized documents: {len(SOURCE_PATHS)}")
    print(f"Corpus-eligible questions: {len(corpus_eligible)}")
    print(f"Positive retrieval questions: {len(positive_questions)}")
    print(f"Deferred non-positive questions: {len(deferred_questions)}")
    print(f"Retrieval depth: Top-{TOP_K} chunks")
    print()

    print("[1/4] Format-agnostic ingestion, normalization, and chunking...")
    chunks = build_chunks()
    print(f"      Total retrieval chunks: {len(chunks)}")

    print("[2/4] Validating global chunk identity...")
    validate_global_chunk_identity(chunks)

    print("[3/4] Creating embeddings and shared vector index...")
    provider = OpenAIEmbeddingProvider.from_environment()
    vector_index = NumPyVectorIndex()

    VectorIndexer(
        embedding_provider=provider,
        vector_index=vector_index,
    ).index(chunks)

    retriever = VectorRetriever(
        embedding_provider=provider,
        vector_index=vector_index,
        chunks=chunks,
    )
    print("      Shared vector index: ready")

    print("[4/4] Running Golden Set retrieval...")
    print()

    ranked_results_by_question: dict[str, tuple[str, ...]] = {}

    for number, question in enumerate(positive_questions, start=1):
        candidates = retriever.retrieve(
            query=question.question,
            top_k=min(TOP_K, len(chunks)),
        )
        if not candidates:
            raise RuntimeError(
                f"No retrieval candidates returned for {question.question_id}."
            )

        ranked_documents = unique_ranked_document_ids(candidates)
        ranked_results_by_question[question.question_id] = ranked_documents

        print(
            f"{number:02d}. {question.question_id} | "
            f"expected={','.join(question.expected_evidence)}"
        )
        print(f"    {question.question}")
        print(
            "    retrieved_documents="
            + (", ".join(ranked_documents) if ranked_documents else "NONE")
        )

        for candidate in candidates:
            chunk = candidate.chunk
            marker = "*" if chunk.document_id in question.expected_evidence else " "
            print(
                f"    {marker} Rank {candidate.rank} | "
                f"score={candidate.score:.6f} | "
                f"document={chunk.document_id} | "
                f"chunk={chunk.chunk_id}"
            )
        print()

    report = RetrievalEvaluator().evaluate(
        golden_set=golden_set,
        available_document_ids=available_document_ids,
        ranked_results_by_question=ranked_results_by_question,
    )

    print("=" * 96)
    print("GOLDEN SET A — VECTOR RETRIEVAL BASELINE")
    print("=" * 96)
    print(
        f"{'QID':<6}{'Expected':<31}{'Hit@1':>8}{'Hit@3':>8}{'Hit@5':>8}"
        f"{'R@1':>8}{'R@3':>8}{'R@5':>8}{'RR':>8}"
    )
    print("-" * 96)

    for result in report.results:
        expected = ",".join(result.expected_document_ids)
        print(
            f"{result.question_id:<6}{expected:<31}"
            f"{result.hit_at_1:>8.2f}"
            f"{result.hit_at_3:>8.2f}"
            f"{result.hit_at_5:>8.2f}"
            f"{result.recall_at_1:>8.2f}"
            f"{result.recall_at_3:>8.2f}"
            f"{result.recall_at_5:>8.2f}"
            f"{result.reciprocal_rank:>8.3f}"
        )

    print("-" * 96)
    print(f"Golden Set questions:       {len(golden_set.questions)}")
    print(f"Corpus-eligible:            {len(corpus_eligible)}")
    print(f"Retrieval-scored:           {report.evaluated_questions}")
    print(f"Deferred / blocked:         {report.skipped_questions}")
    print()
    print(f"Hit@1:                      {report.mean_hit_at_1:.1%}")
    print(f"Hit@3:                      {report.mean_hit_at_3:.1%}")
    print(f"Hit@5:                      {report.mean_hit_at_5:.1%}")
    print(f"Recall@1:                   {report.mean_recall_at_1:.1%}")
    print(f"Recall@3:                   {report.mean_recall_at_3:.1%}")
    print(f"Recall@5:                   {report.mean_recall_at_5:.1%}")
    print(f"MRR:                        {report.mean_reciprocal_rank:.4f}")
    print()

    if deferred_questions:
        print(
            "Deferred eligible questions: "
            + ", ".join(
                question.question_id for question in deferred_questions
            )
        )
        print(
            "Reason: no positive expected evidence; "
            "evaluate in abstention/answer layer."
        )
        print()

    print("Golden Set A real vector retrieval benchmark: COMPLETE")


if __name__ == "__main__":
    main()
