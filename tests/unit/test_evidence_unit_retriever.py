"""Unit retrieval and cache integrity without network calls."""
from dataclasses import replace
import json
import math

import pytest

from app.chunking.evidence_units import EvidenceUnitBuilder
from app.ingestion.schemas import NormalizedContent, TextBlock
from app.retrieval.evidence_unit_retriever import EvidenceUnitRetriever, make_cache, read_cache


def units():
    return tuple(EvidenceUnitBuilder().build(NormalizedContent((TextBlock("p", 0,
        "paragraph", text),)), document_id=doc, title="Policy", source_revision="a"*64)[0]
        for doc, text in (("DOC-005", "External sharing rules"), ("DOC-023", "AI tool rules")))


class Embedding:
    def __init__(self): self.calls = []
    def embed_query(self, query):
        self.calls.append(query)
        return (1., 0.)


def test_hybrid_trace_and_filter_apply_before_ranking():
    source = units()
    provider = Embedding()
    retriever = EvidenceUnitRetriever(source, [(1, 0), (0, 1)], provider)
    found, trace = retriever.search("AI", ("DOC-023",))
    assert [u.document_id for u in found] == ["DOC-023"]
    assert len(trace["vector"]) == len(trace["lexical"]) == 1
    retriever.search("AI", ("DOC-005",))
    assert provider.calls == ["AI"]


def test_cache_roundtrip_and_changed_search_text_invalidates():
    source = units()
    payload = json.loads(json.dumps(make_cache(source, "model", [(1, 0), (0, 1)])))
    assert read_cache(payload, source, "model") == [[1, 0], [0, 1]]
    changed = (replace(source[0], search_text="Changed"), source[1])
    with pytest.raises(ValueError, match="cache differs"):
        read_cache(payload, changed, "model")
    with pytest.raises(ValueError, match="cache differs"):
        read_cache(payload, source, "other-model")


def test_empty_filtered_lexical_query_has_no_vote():
    provider = Embedding()
    retriever = EvidenceUnitRetriever(units(), [(1, 0), (0, 1)], provider)
    found, trace = retriever.search("the and a")
    assert found and trace["lexical"] == [] and trace["lexical_query"] == ""
    assert provider.calls == ["the and a"]


@pytest.mark.parametrize("vectors", [[(math.nan, 1), (0, 1)], [(0, 0), (0, 1)], [(1,), (0, 1)]])
def test_invalid_embeddings_are_not_cached(vectors):
    with pytest.raises(ValueError): make_cache(units(), "model", vectors)
