"""Optional reranking after RRF, with original evidence and scores preserved."""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from math import isfinite
from numbers import Real
from typing import Protocol

from app.chunking.schemas import RetrievalChunk
from app.retrieval.candidate_fusion import FusedCandidate
from app.retrieval.document_diversifier import DocumentDiversifier
from app.retrieval.search_text import build_search_text


class PairScorer(Protocol):
    """Return one finite score per passage, in input order; higher is better."""

    def score_pairs(self, query: str, passages: Sequence[str]) -> Sequence[float]:
        ...


def _positive_integer(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer.")


def _score(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise ValueError("reranker scores must be finite real numbers.")
    return float(value)


@dataclass(frozen=True, slots=True)
class RerankedCandidate:
    """A reranker score is distinct from source.score (RRF), not a probability.

    source retains the original fusion rank and score. rerank_rank records the
    order before optional diversity selection; rank is the final output order.
    """

    source: FusedCandidate
    score: float
    rank: int
    rerank_rank: int

    def __post_init__(self) -> None:
        _score(self.score)
        _positive_integer(self.rank, "rank")
        _positive_integer(self.rerank_rank, "rerank_rank")

    @property
    def chunk(self) -> RetrievalChunk:
        return self.source.chunk

    @property
    def retrieval_methods(self) -> tuple[str, ...]:
        return self.source.retrieval_methods


class CandidateReranker:
    """Score a candidate pool and sort it, resolving ties in input order.

    Supply the wider, non-diversified RRF pool (for example Top-20), before
    selecting the final Top-5. No model is chosen by this provider-independent
    component. Scorer failures propagate; there is no silent baseline fallback.
    """

    def __init__(self, scorer: PairScorer) -> None:
        self._scorer = scorer

    def rerank(
        self,
        query: str,
        candidates: Sequence[FusedCandidate],
        top_k: int = 5,
    ) -> tuple[RerankedCandidate, ...]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string.")
        _positive_integer(top_k, "top_k")
        pool = tuple(candidates)
        ids = [candidate.chunk.chunk_id for candidate in pool]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate pool contains duplicate chunk_ids.")
        if not pool:
            return ()

        passages = tuple(build_search_text(candidate.chunk) for candidate in pool)
        raw_scores = tuple(self._scorer.score_pairs(query, passages))
        if len(raw_scores) != len(pool):
            raise ValueError("reranker must return exactly one score per candidate.")
        scores = tuple(_score(value) for value in raw_scores)
        order = sorted(range(len(pool)), key=lambda index: -scores[index])
        return tuple(
            RerankedCandidate(pool[index], scores[index], rank, rank)
            for rank, index in enumerate(order[:top_k], start=1)
        )


def select_reranked_candidates(
    candidates: Sequence[RerankedCandidate],
    top_k: int = 5,
    document_diversifier: DocumentDiversifier | None = None,
) -> tuple[RerankedCandidate, ...]:
    """Select from an already reranked pool without a second model call.

    Adapt the original FusedCandidates to the existing diversity selector;
    never relabel a reranker score as an RRF score or mutate source provenance.
    """
    _positive_integer(top_k, "top_k")
    pool = tuple(candidates)
    by_id = {candidate.chunk.chunk_id: candidate for candidate in pool}
    if len(by_id) != len(pool):
        raise ValueError("reranked pool contains duplicate chunk_ids.")
    if document_diversifier is None:
        selected = pool[:top_k]
    else:
        ordered_sources = tuple(
            replace(candidate.source, rank=rank)
            for rank, candidate in enumerate(pool, start=1)
        )
        selected = tuple(
            by_id[candidate.chunk.chunk_id]
            for candidate in document_diversifier.select(ordered_sources, top_k=top_k)
        )
    return tuple(replace(candidate, rank=rank) for rank, candidate in enumerate(selected, 1))
