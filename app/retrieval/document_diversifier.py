"""Document-aware selection of fused retrieval candidates."""

from dataclasses import replace
from collections.abc import Sequence

from app.retrieval.candidate_fusion import FusedCandidate


class DocumentDiversifier:
    """Pin the leading candidate, prefer distinct documents, then backfill.

    The input must already be sorted by retrieval relevance. Output ranks are
    consecutive; original RRF scores and provenance remain unchanged.
    """

    def select(
        self, candidates: Sequence[FusedCandidate], top_k: int = 5
    ) -> tuple[FusedCandidate, ...]:
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be a positive integer.")
        if not candidates:
            return ()

        seen_ids: set[str] = set()
        for candidate in candidates:
            chunk_id = candidate.chunk.chunk_id
            if chunk_id in seen_ids:
                raise ValueError(f"duplicate chunk_id: {chunk_id}")
            seen_ids.add(chunk_id)

        selected = [candidates[0]]
        selected_ids = {candidates[0].chunk.chunk_id}
        seen_documents = {candidates[0].chunk.document_id}

        for candidate in candidates[1:]:
            if len(selected) >= top_k:
                break
            document_id = candidate.chunk.document_id
            if document_id not in seen_documents:
                selected.append(candidate)
                selected_ids.add(candidate.chunk.chunk_id)
                seen_documents.add(document_id)

        for candidate in candidates[1:]:
            if len(selected) >= top_k:
                break
            if candidate.chunk.chunk_id not in selected_ids:
                selected.append(candidate)
                selected_ids.add(candidate.chunk.chunk_id)

        return tuple(replace(candidate, rank=rank) for rank, candidate in enumerate(selected, 1))
