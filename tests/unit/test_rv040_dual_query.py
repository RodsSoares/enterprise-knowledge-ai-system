"""Dual-query recovery uses separate embeddings/BM25 projections and document scope."""
from dataclasses import dataclass
import pytest

from app.retrieval.v3_dual_query_retriever import DualQueryEvidenceRetriever


@dataclass(frozen=True)
class Unit:
    unit_id: str
    document_id: str
    search_text: str
    searchable: bool = True


U1 = Unit("u1", "DOC-005", "External sharing needs business approval")
U2 = Unit("u2", "DOC-005", "Exceptions require documented exception approval")
U3 = Unit("u3", "DOC-006", "Exception approval for a different corporate process")


class Embeddings:
    def __init__(self):
        self.queries = []
    def embed_query(self, query):
        self.queries.append(query)
        return (0.0, 1.0) if "exception" in query else (1.0, 0.0)


def retriever():
    em = Embeddings()
    result = DualQueryEvidenceRetriever((U1,U2,U3), ((1.0,0.0),(0.0,1.0),(0.5,0.5)), em)
    return result, em


def test_explicit_recovery_projection_keeps_vector_query_separate():
    r, em = retriever()
    result, trace = r.search_projections("exception controls", "documented exception approval", ("DOC-005",), 2)
    assert result[0].unit_id == "u2"
    assert em.queries == ["exception controls"]
    assert trace["lexical_query"] == "documented exception approval"
    assert all(u.document_id == "DOC-005" for u in result)
    assert trace["version"] == "dual-query/1"


def test_scope_restriction_prevents_other_document_even_when_relevant():
    r, _ = retriever()
    result, _ = r.search_projections("exception controls", "exception approval", ("DOC-006",), 2)
    assert [u.document_id for u in result] == ["DOC-006"]


def test_empty_lexical_votes_preserve_vector_ranking():
    r, _ = retriever()
    result, trace = r.search_projections("exception controls", "zzunknownterm", ("DOC-005",), 2)
    assert [u.unit_id for u in result] == ["u2", "u1"]
    assert trace["lexical"] == []


@pytest.mark.parametrize("query,lexical,docs,k", [
    ("", "valid", (), 2), ("valid", "", (), 2),
    ("valid", "valid", (), 0), ("valid", "valid", (), 41),
    ("valid", "valid", ("",), 2),
])
def test_invalid_recovery_requests_fail_closed(query, lexical, docs, k):
    r, _ = retriever()
    with pytest.raises(ValueError):
        r.search_projections(query, lexical, docs, k)
