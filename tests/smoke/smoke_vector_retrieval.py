"""Live smoke test for semantic retrieval against a real corpus document.

Run from the repository root:

    python -m tests.smoke.smoke_vector_retrieval
"""

from pathlib import Path

from app.chunking.structure_aware_chunker import StructureAwareChunker
from app.ingestion.docling_parser import DoclingParser
from app.retrieval.openai_embeddings import OpenAIEmbeddingProvider
from app.retrieval.vector_index import NumPyVectorIndex
from app.retrieval.vector_indexer import VectorIndexer
from app.retrieval.vector_retriever import VectorRetriever


SOURCE_PATH = Path(
    "data/source/corporate_repository/policies/"
    "DOC-005_Data_Sharing_Policy.pdf"
)

QUERY = "What rules apply when confidential information is shared externally?"
TOP_K = 5
TARGET_CHARS = 1200
MAX_CHARS = 1800


def main() -> None:
    if not SOURCE_PATH.is_file():
        raise FileNotFoundError(
            f"Expected corpus document not found: {SOURCE_PATH}"
        )

    print("Real vector retrieval smoke test")
    print(f"Source: {SOURCE_PATH}")
    print(f"Query: {QUERY!r}")
    print()

    print("[1/5] Parsing and normalizing source document...")
    content = DoclingParser().parse(SOURCE_PATH)
    print(f"      Canonical blocks: {len(content.blocks)}")

    print("[2/5] Building structure-aware retrieval chunks...")
    chunker = StructureAwareChunker(
        target_chars=TARGET_CHARS,
        max_chars=MAX_CHARS,
    )
    chunks = chunker.chunk(content, SOURCE_PATH)
    if not chunks:
        raise RuntimeError("Structure-aware chunking produced no chunks.")
    print(f"      Retrieval chunks: {len(chunks)}")

    print("[3/5] Creating real OpenAI embeddings and vector index...")
    provider = OpenAIEmbeddingProvider.from_environment()
    vector_index = NumPyVectorIndex()
    VectorIndexer(
        embedding_provider=provider,
        vector_index=vector_index,
    ).index(chunks)
    print("      Vector index: ready")

    print("[4/5] Running semantic retrieval...")
    candidates = VectorRetriever(
        embedding_provider=provider,
        vector_index=vector_index,
        chunks=chunks,
    ).retrieve(
        query=QUERY,
        top_k=min(TOP_K, len(chunks)),
    )

    if not candidates:
        raise RuntimeError("Vector retrieval returned no candidates.")

    print("[5/5] Top semantic evidence")
    print()

    for candidate in candidates:
        chunk = candidate.chunk

        print(
            f"Rank {candidate.rank} | "
            f"score={candidate.score:.6f} | "
            f"chunk={chunk.chunk_id}"
        )

        if chunk.section_path:
            print(f"Section: {' > '.join(chunk.section_path)}")

        if chunk.page_numbers:
            print(
                "Pages: "
                + ", ".join(str(page) for page in chunk.page_numbers)
            )

        evidence = " ".join(chunk.text.split())
        print(f"Evidence: {evidence}")
        print("-" * 80)

    print()
    print("Real vector retrieval smoke test: PASS")


if __name__ == "__main__":
    main()
