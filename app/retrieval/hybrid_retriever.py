"""Orchestrate semantic and lexical retrieval with reciprocal rank fusion."""

from app.retrieval.candidate_fusion import FusedCandidate, ReciprocalRankFusion
from app.retrieval.lexical_retriever import LexicalRetriever
from app.retrieval.vector_retriever import VectorRetriever


class HybridRetriever:
    """Retrieve independent candidate pools and fuse their rankings."""

    def __init__(
        self,
        vector_retriever: VectorRetriever,
        lexical_retriever: LexicalRetriever,
        fusion: ReciprocalRankFusion,
        candidate_depth: int = 20,
    ) -> None:
        if isinstance(candidate_depth, bool) or not isinstance(candidate_depth, int) or candidate_depth < 1:
            raise ValueError("candidate_depth must be a positive integer.")
        self._vector_retriever = vector_retriever
        self._lexical_retriever = lexical_retriever
        self._fusion = fusion
        self._candidate_depth = candidate_depth

    def retrieve(self, query: str, top_k: int = 5) -> tuple[FusedCandidate, ...]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string.")
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be a positive integer.")

        depth = max(top_k, self._candidate_depth)
        vector_candidates = self._vector_retriever.retrieve(query, top_k=depth)
        lexical_candidates = self._lexical_retriever.retrieve(query, top_k=depth)
        return self._fusion.fuse((vector_candidates, lexical_candidates), top_k=top_k)
