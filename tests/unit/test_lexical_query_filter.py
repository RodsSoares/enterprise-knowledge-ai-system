"""Behavior of the opt-in lexical filter inside the existing hybrid pipeline."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from app.chunking.schemas import RetrievalChunk
from app.retrieval.candidate_fusion import ReciprocalRankFusion
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.lexical_index import BM25LexicalIndex
from app.retrieval.lexical_query_filter import FilteredLexicalRetriever, filter_lexical_query
from app.retrieval.lexical_retriever import LexicalRetriever
from app.retrieval.schemas import RetrievalCandidate


def chunk(doc, text):
    return RetrievalChunk(chunk_id=f"{doc}::chunk-00001", document_id=doc, order=1,
        text=text, source_block_ids=("b1",), source_path=Path(f"{doc}.md"), content_types=("text",))


def test_grammatical_collision_no_longer_outvotes_semantic_leader_and_vector_query_is_unchanged():
    chunks = (chunk("TARGET", "Supplier emergency authority."), chunk("NOISE", "A consumer tool."))
    index = BM25LexicalIndex()
    index.add([c.chunk_id for c in chunks], [c.text for c in chunks])
    raw = LexicalRetriever(index, chunks)
    vector = Mock()
    vector.retrieve.return_value = tuple(RetrievalCandidate(c, "vector", 1 / rank, rank)
                                         for rank, c in enumerate(chunks, 1))
    query = "A fornecedor?"
    baseline = HybridRetriever(vector, raw, ReciprocalRankFusion()).retrieve(query, top_k=1)
    candidate = HybridRetriever(vector, FilteredLexicalRetriever(raw), ReciprocalRankFusion()).retrieve(query, top_k=1)
    assert baseline[0].chunk.document_id == "NOISE"
    assert candidate[0].chunk.document_id == "TARGET"
    assert all(call.args[0] == query for call in vector.retrieve.call_args_list)
    assert raw.retrieve(query)[0].chunk.document_id == "NOISE"  # existing default remains unchanged


def test_content_terms_identifiers_numbers_and_negations_survive():
    result = filter_lexical_query("The SOP DOC-012 ISO-27001 350000: não not no sem without aprovação?")
    tokens = set(result.split())
    assert {"sop", "doc-012", "iso-27001", "350000", "não", "not", "no", "sem", "without", "aprovação"} <= tokens
    assert "the" not in tokens


def test_empty_filtered_query_abstains_only_from_the_lexical_branch():
    delegate = Mock()
    assert FilteredLexicalRetriever(delegate).retrieve("a do the e", top_k=20) == ()
    delegate.retrieve.assert_not_called()


def test_remaining_terms_are_sent_for_rescoring_before_topk_is_applied():
    delegate = Mock()
    delegate.retrieve.return_value = ("opaque result",)
    result = FilteredLexicalRetriever(delegate).retrieve("A revisão do SOP", top_k=12)
    delegate.retrieve.assert_called_once_with("revisão sop", top_k=12)
    assert result == delegate.retrieve.return_value


def test_delegate_failure_is_not_silently_converted_to_an_empty_ranking():
    delegate = Mock()
    delegate.retrieve.side_effect = RuntimeError("index unavailable")
    with pytest.raises(RuntimeError, match="index unavailable"):
        FilteredLexicalRetriever(delegate).retrieve("Restricted information")


@pytest.mark.parametrize("query", [None, 42, "", "   "])
def test_invalid_query_is_rejected(query):
    with pytest.raises(ValueError, match="query"):
        FilteredLexicalRetriever(Mock()).retrieve(query)


@pytest.mark.parametrize("top_k", [0, -1, True, 1.5])
def test_invalid_depth_is_rejected_even_when_all_terms_would_be_removed(top_k):
    with pytest.raises(ValueError, match="top_k"):
        FilteredLexicalRetriever(Mock()).retrieve("a do", top_k=top_k)
