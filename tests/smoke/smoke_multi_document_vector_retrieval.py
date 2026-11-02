"""RV-002 v2 — Multi-document vector retrieval benchmark.

Purpose
-------
Validate semantic retrieval across a controlled five-document enterprise corpus
and establish a quantitative baseline before hybrid retrieval / reranking.

Metrics
-------
- Hit@1
- Hit@3
- Hit@5
- Mean Reciprocal Rank (MRR)

Run from repository root:
    python -m tests.smoke.smoke_multi_document_vector_retrieval_v2
"""

from dataclasses import dataclass
from pathlib import Path

from app.chunking.structure_aware_chunker import StructureAwareChunker
from app.ingestion.docling_parser import DoclingParser
from app.retrieval.openai_embeddings import OpenAIEmbeddingProvider
from app.retrieval.vector_index import NumPyVectorIndex
from app.retrieval.vector_indexer import VectorIndexer
from app.retrieval.vector_retriever import VectorRetriever


SOURCE_PATHS = (
    Path("data/source/corporate_repository/policies/DOC-005_Data_Sharing_Policy.pdf"),
    Path("data/source/corporate_repository/policies/DOC-006_Information_Security_Policy.pdf"),
    Path("data/source/corporate_repository/policies/DOC-022_Supplier_Management_Policy.pdf"),
    Path("data/source/corporate_repository/policies/DOC-023_AI_Governance_Policy.pdf"),
    Path("data/source/corporate_repository/standards/DOC-024_AI_Security_Standard.pdf"),
)

TOP_K = 5
TARGET_CHARS = 1200
MAX_CHARS = 1800


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    query: str
    expected_document_id: str


BENCHMARK_CASES = (
    BenchmarkCase(
        name="Data sharing",
        query="What rules apply when confidential information is shared externally?",
        expected_document_id="DOC-005",
    ),
    BenchmarkCase(
        name="Information security",
        query=(
            "What controls apply when confidential information is transmitted "
            "to an external party?"
        ),
        expected_document_id="DOC-006",
    ),
    BenchmarkCase(
        name="Supplier management",
        query=(
            "What requirements apply to the management and oversight "
            "of external suppliers?"
        ),
        expected_document_id="DOC-022",
    ),
    BenchmarkCase(
        name="AI governance",
        query=(
            "What governance requirements apply to the approval "
            "and oversight of AI systems?"
        ),
        expected_document_id="DOC-023",
    ),
    BenchmarkCase(
        name="AI security",
        query=(
            "What security controls and requirements apply specifically "
            "to AI systems?"
        ),
        expected_document_id="DOC-024",
    ),
)


def document_id_from_path(source_path: Path) -> str:
    """Extract canonical document ID from a controlled corpus filename."""
    return source_path.stem.split("_", 1)[0]


def validate_sources() -> None:
    """Fail fast if any configured corpus document is unavailable."""
    missing = [path for path in SOURCE_PATHS if not path.is_file()]
    if missing:
        formatted = "\n".join(f"  - {path}" for path in missing)
        raise FileNotFoundError(
            "Expected corpus documents were not found:\n"
            f"{formatted}"
        )


def build_chunks():
    """Parse, normalize, and chunk all configured corpus documents."""
    parser = DoclingParser()
    chunker = StructureAwareChunker(
        target_chars=TARGET_CHARS,
        max_chars=MAX_CHARS,
    )
    all_chunks = []

    for source_path in SOURCE_PATHS:
        expected_document_id = document_id_from_path(source_path)

        print(f"      Processing: {source_path.name}")
        content = parser.parse(source_path)
        chunks = chunker.chunk(
            content,
            source_path,
            expected_document_id,
        )

        if not chunks:
            raise RuntimeError(
                f"No retrieval chunks produced for {source_path}."
            )

        actual_document_ids = {chunk.document_id for chunk in chunks}
        if actual_document_ids != {expected_document_id}:
            raise RuntimeError(
                f"Unexpected document identity for {source_path.name}. "
                f"Expected {expected_document_id!r}; "
                f"got {sorted(actual_document_ids)}."
            )

        print(
            f"      {expected_document_id}: "
            f"{len(content.blocks)} canonical blocks -> "
            f"{len(chunks)} chunks"
        )
        all_chunks.extend(chunks)

    return all_chunks


def validate_global_chunk_identity(chunks) -> None:
    """Validate uniqueness and document provenance of retrieval chunk IDs."""
    chunk_ids = [chunk.chunk_id for chunk in chunks]

    if len(set(chunk_ids)) != len(chunk_ids):
        seen = set()
        duplicates = set()

        for chunk_id in chunk_ids:
            if chunk_id in seen:
                duplicates.add(chunk_id)
            seen.add(chunk_id)

        raise RuntimeError(
            "Duplicate global chunk IDs detected: "
            + ", ".join(sorted(duplicates))
        )

    expected_document_ids = {
        document_id_from_path(path) for path in SOURCE_PATHS
    }
    actual_document_ids = {chunk.document_id for chunk in chunks}

    if actual_document_ids != expected_document_ids:
        raise RuntimeError(
            "Corpus document identities do not match configuration. "
            f"Expected {sorted(expected_document_ids)}; "
            f"got {sorted(actual_document_ids)}."
        )

    for chunk in chunks:
        expected_prefix = f"{chunk.document_id}::chunk-"
        if not chunk.chunk_id.startswith(expected_prefix):
            raise RuntimeError(
                f"Chunk {chunk.chunk_id!r} does not preserve "
                f"document identity {chunk.document_id!r}."
            )

    print(f"      Documents represented: {len(actual_document_ids)}")
    print(f"      Unique chunk IDs: {len(set(chunk_ids))}/{len(chunk_ids)}")
    print("      Global chunk identity: PASS")


def expected_document_rank(candidates, expected_document_id: str):
    """Return first rank containing the expected document, else None."""
    for candidate in candidates:
        if candidate.chunk.document_id == expected_document_id:
            return candidate.rank
    return None


def main() -> None:
    validate_sources()

    print("RV-002 v2 multi-document vector retrieval benchmark")
    print(f"Documents: {len(SOURCE_PATHS)}")
    print(f"Queries: {len(BENCHMARK_CASES)}")
    print(f"Retrieval depth: Top-{TOP_K}")
    print()

    print("[1/4] Parsing, normalizing, and chunking corpus...")
    chunks = build_chunks()

    if not chunks:
        raise RuntimeError("Multi-document corpus produced no chunks.")

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

    print("      Shared vector index: ready")

    print("[4/4] Running benchmark...")
    print()

    results = []
    hit_1 = 0
    hit_3 = 0
    hit_5 = 0
    reciprocal_rank_sum = 0.0

    for number, case in enumerate(BENCHMARK_CASES, start=1):
        candidates = VectorRetriever(
            embedding_provider=provider,
            vector_index=vector_index,
            chunks=chunks,
        ).retrieve(
            query=case.query,
            top_k=min(TOP_K, len(chunks)),
        )

        if not candidates:
            raise RuntimeError(
                f"No retrieval candidates returned for {case.name!r}."
            )

        rank = expected_document_rank(
            candidates,
            case.expected_document_id,
        )

        if rank is not None:
            reciprocal_rank_sum += 1.0 / rank
            hit_1 += int(rank <= 1)
            hit_3 += int(rank <= 3)
            hit_5 += int(rank <= 5)

        results.append((case, rank))

        rank_text = str(rank) if rank is not None else "MISS"

        print(
            f"Query {number}: {case.name} | "
            f"expected={case.expected_document_id} | "
            f"rank={rank_text}"
        )
        print(f"  {case.query}")

        for candidate in candidates:
            chunk = candidate.chunk
            marker = (
                "*"
                if chunk.document_id == case.expected_document_id
                else " "
            )
            print(
                f"  {marker} Rank {candidate.rank} | "
                f"score={candidate.score:.6f} | "
                f"document={chunk.document_id} | "
                f"chunk={chunk.chunk_id}"
            )

        print()

    total = len(BENCHMARK_CASES)
    mrr = reciprocal_rank_sum / total

    print("=" * 80)
    print("RV-002 v2 BENCHMARK SUMMARY")
    print("=" * 80)
    print(
        f"{'Case':<24} "
        f"{'Expected':<10} "
        f"{'Rank':<8} "
        f"{'Hit@1':<7} "
        f"{'Hit@3':<7} "
        f"{'Hit@5':<7}"
    )
    print("-" * 80)

    for case, rank in results:
        rank_text = str(rank) if rank is not None else "MISS"
        print(
            f"{case.name:<24} "
            f"{case.expected_document_id:<10} "
            f"{rank_text:<8} "
            f"{'PASS' if rank is not None and rank <= 1 else '-':<7} "
            f"{'PASS' if rank is not None and rank <= 3 else '-':<7} "
            f"{'PASS' if rank is not None and rank <= 5 else '-':<7}"
        )

    print("-" * 80)
    print(f"Hit@1: {hit_1}/{total} ({hit_1 / total:.1%})")
    print(f"Hit@3: {hit_3}/{total} ({hit_3 / total:.1%})")
    print(f"Hit@5: {hit_5}/{total} ({hit_5 / total:.1%})")
    print(f"MRR:   {mrr:.4f}")
    print()

    if hit_5 != total:
        failed_cases = [
            case.name
            for case, rank in results
            if rank is None or rank > 5
        ]
        raise RuntimeError(
            "RV-002 v2 failed: expected document absent from Top-5 for: "
            + ", ".join(failed_cases)
        )

    print("RV-002 v2 multi-document vector retrieval benchmark: PASS")


if __name__ == "__main__":
    main()
