from dataclasses import dataclass

import numpy as np

from app.retrieval.embeddings import Embedding


@dataclass(frozen=True, slots=True)
class VectorHit:
    """One ranked result returned by the vector index."""

    chunk_id: str
    score: float
    rank: int


class NumPyVectorIndex:
    """Small exact vector index using cosine similarity."""

    def __init__(self) -> None:
        self._chunk_ids: tuple[str, ...] = ()
        self._vectors: np.ndarray | None = None

    def add(
        self,
        chunk_ids: tuple[str, ...],
        embeddings: tuple[Embedding, ...],
    ) -> None:
        if not chunk_ids:
            raise ValueError("chunk_ids must not be empty.")
        if len(chunk_ids) != len(embeddings):
            raise ValueError("chunk_ids and embeddings must contain the same number of items.")
        if len(set(chunk_ids)) != len(chunk_ids):
            raise ValueError("chunk_ids must not contain duplicates.")

        matrix = self._as_matrix(embeddings)
        self._chunk_ids = chunk_ids
        self._vectors = self._normalize_rows(matrix)

    def search(self, query_embedding: Embedding, top_k: int) -> tuple[VectorHit, ...]:
        if self._vectors is None:
            raise ValueError("vector index is empty.")
        if top_k < 1:
            raise ValueError("top_k must be greater than or equal to 1.")

        query = np.asarray(query_embedding, dtype=np.float64)
        if query.ndim != 1 or query.size == 0:
            raise ValueError("query_embedding must be a non-empty one-dimensional vector.")
        if query.shape[0] != self._vectors.shape[1]:
            raise ValueError("query_embedding dimension must match indexed embedding dimension.")

        query_norm = np.linalg.norm(query)
        if query_norm == 0:
            raise ValueError("query_embedding must not be a zero vector.")

        scores = self._vectors @ (query / query_norm)
        limit = min(top_k, len(self._chunk_ids))
        ranked_indices = sorted(
            range(len(self._chunk_ids)),
            key=lambda index: (-float(scores[index]), index),
        )[:limit]

        return tuple(
            VectorHit(
                chunk_id=self._chunk_ids[index],
                score=float(scores[index]),
                rank=rank,
            )
            for rank, index in enumerate(ranked_indices, start=1)
        )

    @staticmethod
    def _as_matrix(embeddings: tuple[Embedding, ...]) -> np.ndarray:
        if not embeddings:
            raise ValueError("embeddings must not be empty.")

        dimensions = {len(embedding) for embedding in embeddings}
        if len(dimensions) != 1 or 0 in dimensions:
            raise ValueError("embeddings must be non-empty vectors with consistent dimensions.")

        matrix = np.asarray(embeddings, dtype=np.float64)
        if matrix.ndim != 2:
            raise ValueError("embeddings must form a two-dimensional matrix.")
        return matrix

    @staticmethod
    def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(matrix, axis=1)
        if np.any(norms == 0):
            raise ValueError("embeddings must not contain zero vectors.")
        return matrix / norms[:, np.newaxis]
