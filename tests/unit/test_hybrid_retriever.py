"""Unit tests for hybrid retrieval orchestration."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from app.chunking.schemas import RetrievalChunk
from app.retrieval.candidate_fusion import ReciprocalRankFusion
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.schemas import RetrievalCandidate


def chunk(identifier: str) -> RetrievalChunk:
    return RetrievalChunk(
        chunk_id=f"DOC-001::{identifier}", document_id="DOC-001", order=0,
        text=f"Text for {identifier}", source_block_ids=("block-1",),
        source_path=Path("document.pdf"), content_types=("text",),
    )


def candidate(item: RetrievalChunk, method: str, rank: int) -> RetrievalCandidate:
    return RetrievalCandidate(chunk=item, retrieval_method=method, score=0.5, rank=rank)


def make_retriever(vector_results=(), lexical_results=(), candidate_depth=20):
    vector = Mock()
    lexical = Mock()
    vector.retrieve.return_value = tuple(vector_results)
    lexical.retrieve.return_value = tuple(lexical_results)
    return HybridRetriever(vector, lexical, ReciprocalRankFusion(), candidate_depth), vector, lexical


def test_combines_overlapping_candidates_and_preserves_methods():
    shared, vector_only, lexical_only = chunk("a"), chunk("b"), chunk("c")
    retriever, _, _ = make_retriever(
        (candidate(shared, "vector", 1), candidate(vector_only, "vector", 2)),
        (candidate(shared, "lexical", 1), candidate(lexical_only, "lexical", 2)),
    )
    result = retriever.retrieve("query")
    assert [item.chunk.chunk_id for item in result] == [shared.chunk_id, vector_only.chunk_id, lexical_only.chunk_id]
    assert result[0].retrieval_methods == ("lexical", "vector")
    assert [item.rank for item in result] == [1, 2, 3]


def test_passes_candidate_depth_to_both_retrievers():
    retriever, vector, lexical = make_retriever(candidate_depth=17)
    retriever.retrieve("query", top_k=5)
    vector.retrieve.assert_called_once_with("query", top_k=17)
    lexical.retrieve.assert_called_once_with("query", top_k=17)


def test_top_k_larger_than_candidate_depth_expands_search():
    retriever, vector, lexical = make_retriever(candidate_depth=3)
    retriever.retrieve("query", top_k=8)
    vector.retrieve.assert_called_once_with("query", top_k=8)
    lexical.retrieve.assert_called_once_with("query", top_k=8)


def test_top_k_limits_fused_results():
    a, b = chunk("a"), chunk("b")
    retriever, _, _ = make_retriever((candidate(a, "vector", 1), candidate(b, "vector", 2)))
    assert len(retriever.retrieve("query", top_k=1)) == 1


def test_empty_retrievals_return_empty_tuple():
    retriever, _, _ = make_retriever()
    assert retriever.retrieve("query") == ()


def test_single_retrieval_method_is_supported():
    a = chunk("a")
    retriever, _, _ = make_retriever(lexical_results=(candidate(a, "lexical", 1),))
    result = retriever.retrieve("query")
    assert len(result) == 1
    assert result[0].retrieval_methods == ("lexical",)


@pytest.mark.parametrize("query", ["", "  ", "\n"])
def test_rejects_blank_query(query):
    retriever, vector, lexical = make_retriever()
    with pytest.raises(ValueError, match="query"):
        retriever.retrieve(query)
    vector.retrieve.assert_not_called()
    lexical.retrieve.assert_not_called()


@pytest.mark.parametrize("top_k", [0, -1, 1.5, True])
def test_rejects_invalid_top_k(top_k):
    retriever, _, _ = make_retriever()
    with pytest.raises(ValueError, match="top_k"):
        retriever.retrieve("query", top_k=top_k)


@pytest.mark.parametrize("depth", [0, -1, 1.5, True])
def test_rejects_invalid_candidate_depth(depth):
    with pytest.raises(ValueError, match="candidate_depth"):
        make_retriever(candidate_depth=depth)


def test_propagates_vector_failure_without_running_lexical():
    retriever, vector, lexical = make_retriever()
    vector.retrieve.side_effect = RuntimeError("vector unavailable")
    with pytest.raises(RuntimeError, match="vector unavailable"):
        retriever.retrieve("query")
    lexical.retrieve.assert_not_called()


def test_propagates_lexical_failure():
    retriever, _, lexical = make_retriever()
    lexical.retrieve.side_effect = RuntimeError("lexical unavailable")
    with pytest.raises(RuntimeError, match="lexical unavailable"):
        retriever.retrieve("query")
