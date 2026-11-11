"""RV-043 lean behavioral contracts; intentionally no paid API calls."""
from dataclasses import dataclass
import json
import pytest

from app.orchestration.lean_pipeline import (
    run_lean, validate_decision, validate_review, LeanContractError,
)


@dataclass(frozen=True)
class U:
    unit_id: str
    reading_text: str
    document_id: str = "DOC-005"
    status: str = "ready"
    searchable: bool = True
    section_path: tuple = ()


U1 = U("u1", "Public information may be shared on an approved business channel.")
U2 = U("u2", "Confidential requires secure channel; corporate email is insufficient.")
U3 = U("u3", "Documented exceptions must be approved by security.")
OUTSIDE = U("out", "AI tools need separate approval.", "DOC-023")


def answer(*rows):
    return {"decision": "answer", "claims": [dict(text=text, citation_ids=ids) for text, ids in rows],
            "recovery_query": None, "message": ""}


def retrieve(query="exceptions approved channel"):
    return {"decision": "retrieve", "claims": [], "recovery_query": query,
            "message": "Missing necessary exception detail"}


def clarify():
    return {"decision": "clarify", "claims": [], "recovery_query": None,
            "message": "Which document version is requested?"}


def abstain():
    return {"decision": "abstain", "claims": [], "recovery_query": None,
            "message": "No relevant evidence"}


def verify(n=1, verdict="PASS", bad=None):
    checks = []
    ids = ["u1", "u2", "u3"]
    for i in range(n):
        checks.append({"claim_index": i, "entailed": not (bad == i), "relevant": True,
                       "conditions_preserved": True, "verified_citation_ids": [ids[i]]})
    return {"decision": verdict, "claim_checks": checks,
            "materially_complete": verdict == "PASS", "reason": "Reviewed evidence"}


class P:
    def __init__(self, *responses):
        self.responses = [json.dumps(x) if not isinstance(x, str) else x for x in responses]
        self.calls = []
    def invoke(self, stage, payload):
        self.calls.append((stage, payload))
        return self.responses.pop(0)


class R:
    def __init__(self, initial=(U1,), recovery=(U2,)):
        self.initial, self.recovery = initial, recovery
        self.calls = []
    def search(self, query, document_ids, top_k):
        self.calls.append((query, tuple(document_ids), top_k))
        return (self.initial if len(self.calls) == 1 else self.recovery), {"step": len(self.calls)}


def run(prov, ret=None, units=(U1, U2, U3, OUTSIDE), question="Quais regras de compartilhamento?"):
    ret = ret or R()
    return run_lean(question, snapshot_id="signed-catalog", units=units,
                    retriever=ret, provider=prov)


def test_happy_path_one_answer_and_one_review():
    p = P(answer(("Public must use approved business channel", ["u1"])), verify())
    r = run(p)
    assert r["status"] == "answered_pending_human_review"
    assert "u1" in r["rendered_answer"]
    assert [x[0] for x in p.calls] == ["answer", "verify"]
    assert r["semantic_quality"] == "not_independently_established"


def test_retrieve_once_then_answer_and_review():
    p = P(retrieve(), answer(("Public rule", ["u1"]), ("Confidential rule", ["u2"])), verify(2))
    r = run(p)
    assert r["status"] == "answered_pending_human_review"
    assert r["recovery_used"]
    assert [x[0] for x in p.calls] == ["answer", "answer", "verify"]
    assert "u2" in r["rendered_answer"]


def test_retrieval_does_not_widen_explicit_document_scope():
    p = P(retrieve(), answer(("Public rule", ["u1"]), ("Confidential rule", ["u2"])), verify(2))
    retriever = R(initial=(U1,), recovery=(U2,))
    r = run(p, ret=retriever, question="Segundo DOC-005, qual regra?")
    assert r["status"] == "answered_pending_human_review"
    assert all(docs == ("DOC-005",) for _, docs, _ in retriever.calls)
    assert all(x[1]["document_scope"] == ["DOC-005"] for x in p.calls)


def test_unknown_named_document_abstains_before_api():
    p, retriever = P(), R()
    r = run(p, ret=retriever, question="Segundo DOC-999, qual regra?")
    assert r["status"] == "abstained"
    assert retriever.calls == p.calls == []


def test_initial_no_evidence_abstains():
    p = P()
    r = run(p, ret=R(initial=()))
    assert r["status"] == "abstained" and not p.calls


def test_clarification_is_not_failure():
    r = run(P(clarify()))
    assert r["status"] == "clarification_required"


def test_abstention_is_not_failure():
    r = run(P(abstain()))
    assert r["status"] == "abstained"


def test_source_cannot_be_forged_by_retriever():
    foreign = U("u1", "Modified citation text")
    r = run(P(), ret=R(initial=(foreign,)))
    assert r["status"] == "execution_failed"
    assert r["error_type"] == "LeanContractError"


def test_explicit_scope_blocks_unrelated_document():
    r = run(P(), ret=R(initial=(OUTSIDE,)), question="Segundo DOC-005, qual regra?")
    assert r["status"] == "execution_failed"


def test_unready_source_blocked():
    invalid = U("bad", "Not ready", status="quarantined")
    r = run(P(), ret=R(initial=(invalid,)), units=(invalid,))
    assert r["status"] == "execution_failed"


def test_recovery_no_new_evidence_abstains():
    r = run(P(retrieve()), ret=R(initial=(U1,), recovery=(U1,)))
    assert r["status"] == "abstained"


def test_repeated_recovery_fails_closed():
    r = run(P(retrieve(), retrieve()))
    assert r["status"] == "execution_failed"
    assert r["rendered_answer"] is None


def test_verification_reject_hides_answer():
    r = run(P(answer(("Public", ["u1"])), verify(verdict="REJECT", bad=0)))
    assert r["status"] == "review_rejected" and r["rendered_answer"] is None
    assert r["answer"] is None


def test_unsupported_pass_fails_closed():
    bad = verify(bad=0)
    r = run(P(answer(("Public", ["u1"])), bad))
    assert r["status"] == "execution_failed"


def test_duplicate_claim_citations_rejected():
    with pytest.raises(LeanContractError):
        validate_decision(json.dumps(answer(("A", ["u1", "u1"]))), (U1,), can_retrieve=True)


def test_unknown_claim_citations_rejected():
    with pytest.raises(LeanContractError):
        validate_decision(json.dumps(answer(("A", ["foreign"]))), (U1,), can_retrieve=True)


def test_duplicate_json_keys_rejected():
    with pytest.raises(LeanContractError):
        validate_decision('{"decision":"answer","decision":"answer","claims":[],"recovery_query":null,"message":""}', (U1,), can_retrieve=True)


def test_no_unexpected_field_in_response():
    raw = answer(("A", ["u1"]))
    raw["extra"] = "untrusted"
    with pytest.raises(LeanContractError):
        validate_decision(json.dumps(raw), (U1,), can_retrieve=True)


def test_recovery_response_requires_real_query():
    with pytest.raises(LeanContractError):
        validate_decision(json.dumps(retrieve("")), (U1,), can_retrieve=True)


def test_verifier_cannot_add_citation():
    bad = verify()
    bad["claim_checks"][0]["verified_citation_ids"] = ["out"]
    with pytest.raises(LeanContractError):
        validate_review(json.dumps(bad), answer(("Public", ["u1"])))


def test_verifier_must_cover_every_claim():
    with pytest.raises(LeanContractError):
        validate_review(json.dumps(verify()), answer(("Public", ["u1"]), ("Secure", ["u2"])))


def test_prompt_does_not_include_planner_or_assurance_stage():
    p = P(answer(("Public", ["u1"])), verify())
    run(p)
    assert [stage for stage, _ in p.calls] == ["answer", "verify"]
    for _, payload in p.calls:
        assert "requirements" not in payload and "plan" not in payload


def test_report_has_trace_but_not_full_source_dump():
    p = P(answer(("Public", ["u1"])), verify())
    result = run(p)
    assert all("reading_text" not in json.dumps(t) for t in result["trace"])


def test_catalog_requires_unique_ids():
    with pytest.raises(ValueError):
        run(P(), units=(U1, U1))


def test_no_unknown_metadata_key():
    with pytest.raises(ValueError):
        run_lean("Question", snapshot_id="x", units=(U1,), retriever=R(),
                 provider=P(), document_metadata={"DOC-999": {}})


def test_budgeted_request_context_limit_stops_before_answer_call():
    big = U("big", "x" * 3000)
    r = run_lean("Q?", snapshot_id="x", units=(big,), retriever=R(initial=(big,)),
                 provider=P(), max_request_chars=1000)
    assert r["status"] == "execution_failed"


def test_verifier_must_check_all_presented_citations():
    candidate = answer(("Combined rule", ["u1", "u2"]))
    review = verify()
    # Partial verification would let an irrelevant source pass unchecked.
    with pytest.raises(LeanContractError):
        validate_review(json.dumps(review), candidate)


def test_provider_budget_exception_is_distinct_from_contract_failure():
    class BudgetExceeded(RuntimeError):
        pass
    class FaultyProvider:
        def invoke(self, stage, payload):
            raise BudgetExceeded("Stop at budget")
    r = run(FaultyProvider())
    assert r["status"] == "budget_exceeded"
