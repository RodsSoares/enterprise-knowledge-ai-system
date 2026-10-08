from dataclasses import dataclass
from typing import Literal

from app.chunking.schemas import RetrievalChunk


RetrievalMethod = Literal["vector", "lexical"]


@dataclass(frozen=True, slots=True)
class RetrievalCandidate:
    """A canonical chunk returned by one retrieval mechanism for one query."""

    chunk: RetrievalChunk
    retrieval_method: RetrievalMethod
    score: float
    rank: int

    def __post_init__(self) -> None:
        if self.retrieval_method not in {"vector", "lexical"}:
            raise ValueError(
                "retrieval_method must be either 'vector' or 'lexical'."
            )

        if self.rank < 1:
            raise ValueError("rank must be greater than or equal to 1.")
