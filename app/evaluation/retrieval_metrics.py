"""Deterministic document-level retrieval metrics."""

from collections.abc import Sequence


def _unique_ranked_documents(retrieved_document_ids: Sequence[str]) -> tuple[str, ...]:
    """Preserve ranking while counting each document only once."""
    seen: set[str] = set()
    unique: list[str] = []
    for document_id in retrieved_document_ids:
        normalized = document_id.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return tuple(unique)


def hit_at_k(
    expected_document_ids: Sequence[str],
    retrieved_document_ids: Sequence[str],
    k: int,
) -> float:
    """Return 1.0 when at least one expected document occurs in the top-k."""
    if k < 1:
        raise ValueError("k must be >= 1.")
    expected = {document_id.strip() for document_id in expected_document_ids if document_id.strip()}
    if not expected:
        return 0.0
    retrieved = _unique_ranked_documents(retrieved_document_ids)[:k]
    return float(any(document_id in expected for document_id in retrieved))


def recall_at_k(
    expected_document_ids: Sequence[str],
    retrieved_document_ids: Sequence[str],
    k: int,
) -> float:
    """Return the fraction of expected documents found in the top-k."""
    if k < 1:
        raise ValueError("k must be >= 1.")
    expected = {document_id.strip() for document_id in expected_document_ids if document_id.strip()}
    if not expected:
        return 0.0
    retrieved = set(_unique_ranked_documents(retrieved_document_ids)[:k])
    return len(expected & retrieved) / len(expected)


def reciprocal_rank(
    expected_document_ids: Sequence[str],
    retrieved_document_ids: Sequence[str],
) -> float:
    """Return reciprocal rank of the first expected document, or 0.0."""
    expected = {document_id.strip() for document_id in expected_document_ids if document_id.strip()}
    if not expected:
        return 0.0
    for rank, document_id in enumerate(
        _unique_ranked_documents(retrieved_document_ids), start=1
    ):
        if document_id in expected:
            return 1.0 / rank
    return 0.0
