from pathlib import Path

import pytest

from app.chunking.schemas import RetrievalChunk
from app.retrieval.schemas import RetrievalCandidate


def _chunk() -> RetrievalChunk:
    return RetrievalChunk(
        chunk_id="chunk-00001",
        order=0,
        text="External AI vendors require security assessment.",
        source_block_ids=("text-00001",),
        source_path=Path("data/source/policies/ai-governance.pdf"),
        section_path=("Third-Party AI",),
        page_numbers=(4,),
        content_types=("text",),
    )


def test_retrieval_candidate_preserves_chunk_and_search_result_metadata() -> None:
    chunk = _chunk()

    candidate = RetrievalCandidate(
        chunk=chunk,
        retrieval_method="vector",
        score=0.873,
        rank=1,
    )

    assert candidate.chunk is chunk
    assert candidate.retrieval_method == "vector"
    assert candidate.score == pytest.approx(0.873)
    assert candidate.rank == 1


@pytest.mark.parametrize("retrieval_method", ["vector", "lexical"])
def test_retrieval_candidate_accepts_supported_methods(
    retrieval_method: str,
) -> None:
    candidate = RetrievalCandidate(
        chunk=_chunk(),
        retrieval_method=retrieval_method,  # type: ignore[arg-type]
        score=1.0,
        rank=1,
    )

    assert candidate.retrieval_method == retrieval_method


@pytest.mark.parametrize("retrieval_method", ["", "semantic", "bm25", "VECTOR"])
def test_retrieval_candidate_rejects_unsupported_methods(
    retrieval_method: str,
) -> None:
    with pytest.raises(ValueError, match="retrieval_method"):
        RetrievalCandidate(
            chunk=_chunk(),
            retrieval_method=retrieval_method,  # type: ignore[arg-type]
            score=1.0,
            rank=1,
        )


@pytest.mark.parametrize("rank", [0, -1, -10])
def test_retrieval_candidate_requires_one_based_positive_rank(rank: int) -> None:
    with pytest.raises(ValueError, match="rank"):
        RetrievalCandidate(
            chunk=_chunk(),
            retrieval_method="vector",
            score=0.5,
            rank=rank,
        )


def test_retrieval_candidate_is_immutable() -> None:
    candidate = RetrievalCandidate(
        chunk=_chunk(),
        retrieval_method="vector",
        score=0.5,
        rank=1,
    )

    with pytest.raises(AttributeError):
        candidate.rank = 2  # type: ignore[misc]
