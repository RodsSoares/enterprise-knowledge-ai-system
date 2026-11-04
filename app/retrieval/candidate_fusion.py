"""Deterministic reciprocal rank fusion for canonical retrieval candidates."""

from dataclasses import dataclass
from collections.abc import Sequence
import math

from app.chunking.schemas import RetrievalChunk
from app.retrieval.schemas import RetrievalCandidate


@dataclass(frozen=True, slots=True)
class FusedCandidate:
    """Candidate ranked across retrieval methods; score is an RRF score."""

    chunk: RetrievalChunk
    score: float
    rank: int
    retrieval_methods: tuple[str, ...]


class ReciprocalRankFusion:
    def __init__(self, k: int = 60) -> None:
        if isinstance(k, bool) or not isinstance(k, int) or k < 1:
            raise ValueError("k must be a positive integer.")
        self.k = k

    def fuse(
        self,
        rankings: Sequence[Sequence[RetrievalCandidate]],
        top_k: int = 5,
    ) -> tuple[FusedCandidate, ...]:
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be a positive integer.")

        scores: dict[str, float] = {}
        chunks: dict[str, RetrievalChunk] = {}
        methods: dict[str, set[str]] = {}
        first_seen: dict[str, int] = {}
        seen_count = 0
        used_methods: set[str] = set()

        for ranking in rankings:
            if not ranking:
                continue
            method = ranking[0].retrieval_method
            if method in used_methods:
                raise ValueError(f"duplicate retrieval method ranking: {method}")
            used_methods.add(method)
            seen_in_ranking: set[str] = set()
            ranks: set[int] = set()
            for candidate in ranking:
                if candidate.retrieval_method != method:
                    raise ValueError("each ranking must contain a single retrieval method.")
                if candidate.rank in ranks:
                    raise ValueError("ranks must be unique within a ranking.")
                ranks.add(candidate.rank)
                chunk_id = candidate.chunk.chunk_id
                if chunk_id in seen_in_ranking:
                    raise ValueError("chunk_ids must be unique within a ranking.")
                seen_in_ranking.add(chunk_id)
                if chunk_id in chunks and chunks[chunk_id] != candidate.chunk:
                    raise ValueError(f"conflicting chunk provenance for {chunk_id}")
                if chunk_id not in first_seen:
                    first_seen[chunk_id] = seen_count
                    seen_count += 1
                chunks[chunk_id] = candidate.chunk
                scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (self.k + candidate.rank)
                methods.setdefault(chunk_id, set()).add(method)

        ordered = sorted(scores, key=lambda chunk_id: (-scores[chunk_id], first_seen[chunk_id]))
        return tuple(
            FusedCandidate(
                chunk=chunks[chunk_id],
                score=math.fsum([scores[chunk_id]]),
                rank=rank,
                retrieval_methods=tuple(sorted(methods[chunk_id])),
            )
            for rank, chunk_id in enumerate(ordered[:top_k], start=1)
        )
