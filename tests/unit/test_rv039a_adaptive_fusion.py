"""RV-039A unit tests: deterministic fusion, safe query expansion, scope invariants."""
from types import SimpleNamespace
import pytest

from app.retrieval.adaptive_fusion import (
    FusionPolicy, controlled_bilingual_query, fuse_ranked,
)
from app.scripts.rv039a_replay import unique_documents, score_docs, replay_saved_queries


def hits(*values):
    return [SimpleNamespace(chunk_id=v, rank=i) for i, v in enumerate(values, 1)]


def test_zero_lexical_fallback_is_exact_vector_order():
    ids, trace = fuse_ranked(hits("A", "B", "C"), [], top_k=2)
    assert ids == ("A", "B") and trace["lexical_used"] is False


def test_vector_prefix_protected_against_strong_lexical_noise():
    ids, trace = fuse_ranked(hits("A", "B", "C", "D", "E"),
                             hits("E", "D", "Z", "Y", "X"), top_k=4)
    assert ids[:3] == ("A", "B", "C")
    assert trace["protected"] == ["A", "B", "C"]


def test_no_unauthorized_or_fabricated_unit():
    ids, _ = fuse_ranked(hits("A", "B"), hits("X", "Y"), top_k=3)
    assert set(ids) <= {"A", "B", "X", "Y"}
    assert len(ids) == len(set(ids))


def test_zero_lexical_weight_falls_back_to_vector():
    ids, trace = fuse_ranked(hits("A", "B", "C"), hits("X"),
                              top_k=3, policy=FusionPolicy(lexical_weight=0))
    assert ids == ("A", "B", "C") and not trace["lexical_used"]


def test_bilingual_retains_original_and_adds_generic_aliases():
    q = "Quais exceções exigem justificativa documentada antes de compartilhar dados?"
    out = controlled_bilingual_query(q)
    assert out.startswith(q)
    assert "exceptions" in out and "justification" in out and "data" in out


def test_glossary_does_not_change_unmapped_or_negated_query():
    q = "não pode autorizar X-991"
    assert controlled_bilingual_query(q) == q


@pytest.mark.parametrize("policy", [
    {"protected_vector_units": -1}, {"rrf_k": 0},
    {"lexical_weight": float("nan")}, {"lexical_weight": -1},
    {"protected_vector_units": True},
])
def test_invalid_policies_fail(policy):
    with pytest.raises(ValueError):
        FusionPolicy(**policy)


@pytest.mark.parametrize("invalid", [0, True, -2])
def test_invalid_k_fail(invalid):
    with pytest.raises(ValueError):
        fuse_ranked(hits("A"), [], top_k=invalid)


def test_duplicate_ranked_candidates_fail():
    with pytest.raises(ValueError, match="Duplicated"):
        fuse_ranked(hits("A", "A"), [], top_k=3)


def test_unique_document_projection_does_not_fabricate_evidence():
    docs = unique_documents(["a1", "a2", "b1", "unknown"],
                             {"a1": "DOC-A", "a2": "DOC-A", "b1": "DOC-B"})
    assert docs == ["DOC-A", "DOC-B"]
    assert score_docs(docs, ["DOC-A", "DOC-B"])["full"]


def test_replay_uses_only_saved_traces():
    fake = {"questions": [{"question_id": "TEST-1", "expected_evidence": ["DOC-A"],
        "candidate_traces": {"vector": [{"chunk_id": "a1", "document_id": "DOC-A", "rank": 1}],
                             "lexical_bilingual": []},
        "arms": {"vector": {"document_ids": ["DOC-A"]}}}]}
    result = replay_saved_queries(fake)
    assert result["sample_size"] == 1
    assert result["summary"]["protected_units_3"]["full_document_evidence_5"] == 1


def test_abstention_question_excluded_from_positive_recall():
    fake = {"questions": [
        {"question_id": "Q29", "expected_evidence": [], "expected_behavior": "abstain"},
        {"question_id": "Q01", "expected_evidence": ["DOC-A"],
         "candidate_traces": {"vector": [{"chunk_id": "a1", "document_id": "DOC-A", "rank": 1}],
                              "lexical_bilingual": []},
         "arms": {"vector": {"document_ids": ["DOC-A"]}}}]}
    result = replay_saved_queries(fake)
    assert result["sample_size"] == 1
    assert result["excluded_abstention_cases"][0]["question_id"] == "Q29"
