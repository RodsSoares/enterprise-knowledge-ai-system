"""Canonical retrieval adapter for BM25 lexical search."""

from collections.abc import Sequence

from app.chunking.schemas import RetrievalChunk
from app.retrieval.lexical_index import BM25LexicalIndex
from app.retrieval.schemas import RetrievalCandidate


class LexicalRetriever:
    def __init__(self, lexical_index: BM25LexicalIndex, chunks: Sequence[RetrievalChunk]) -> None:
        if not chunks:
            raise ValueError("chunks must not be empty.")
        self._index = lexical_index
        self._chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
        if len(self._chunks_by_id) != len(chunks):
            raise ValueError("chunks must not contain duplicate chunk_ids.")

    def retrieve(self, query: str, top_k: int = 5) -> tuple[RetrievalCandidate, ...]:
        if not query.strip():
            raise ValueError("query must not be empty.")
        candidates = []
        for hit in self._index.search(query, top_k=top_k):
            try:
                chunk = self._chunks_by_id[hit.chunk_id]
            except KeyError as exc:
                raise ValueError(f"lexical index returned unknown chunk_id: {hit.chunk_id}") from exc
            candidates.append(RetrievalCandidate(chunk, "lexical", hit.score, hit.rank))
        return tuple(candidates)
