from collections.abc import Sequence

from app.chunking.schemas import RetrievalChunk
from app.retrieval.embeddings import EmbeddingProvider
from app.retrieval.schemas import RetrievalCandidate
from app.retrieval.vector_index import NumPyVectorIndex


class VectorRetriever:
    """Retrieves canonical chunks by semantic similarity."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_index: NumPyVectorIndex,
        chunks: Sequence[RetrievalChunk],
    ) -> None:
        if not chunks:
            raise ValueError("chunks must not be empty.")

        self._embedding_provider = embedding_provider
        self._vector_index = vector_index
        self._chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}

        if len(self._chunks_by_id) != len(chunks):
            raise ValueError("chunks must not contain duplicate chunk_ids.")

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> tuple[RetrievalCandidate, ...]:
        if not query.strip():
            raise ValueError("query must not be empty.")

        query_embedding = self._embedding_provider.embed_query(query)
        hits = self._vector_index.search(query_embedding, top_k=top_k)

        candidates: list[RetrievalCandidate] = []

        for hit in hits:
            try:
                chunk = self._chunks_by_id[hit.chunk_id]
            except KeyError as exc:
                raise ValueError(
                    f"vector index returned unknown chunk_id: {hit.chunk_id}"
                ) from exc

            candidates.append(
                RetrievalCandidate(
                    chunk=chunk,
                    retrieval_method="vector",
                    score=hit.score,
                    rank=hit.rank,
                )
            )

        return tuple(candidates)
