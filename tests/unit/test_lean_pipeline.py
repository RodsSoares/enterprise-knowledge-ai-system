"""Lean pipeline behavioral contracts (v2); intentionally no paid API calls.

Models cite evidence by alias (E1, E2, ... in retrieval order); the pipeline
maps aliases to canonical unit IDs and derives the verification verdict.
"""
from dataclasses import dataclass
import json
import pytest

from app.orchestration.lean_pipeline import (
    run_lean, validate_decision, validate_review, evidence_aliases, describe_document,
    detect_language, assemble_evidence, LeanContractError,
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
    cited = list(dict.fromkeys(uid for _, ids in rows for uid in ids))
    return {"evidence_use": [{"id": uid, "relevance": "direct"} for uid in cited],
            "decision": "answer",
            "claims": [dict(text=text, citation_ids=ids) for text, ids in rows],
            "recovery_query": None, "message": ""}


def retrieve(query="exceptions approved channel"):
    return {"evidence_use": [], "decision": "retrieve", "claims": [], "recovery_query": query,
            "message": "Missing necessary exception detail"}


def clarify():
    return {"evidence_use": [], "decision": "clarify", "claims": [], "recovery_query": None,
            "message": "Which document version is requested?"}


def abstain():
    return {"evidence_use": [], "decision": "abstain", "claims": [], "recovery_query": None,
            "message": "No relevant evidence"}


def verify(n=1, verdict="PASS", bad=None, complete=None):
    checks = [{"claim_index": i, "entailed": not (bad == i), "relevant": True,
               "conditions_preserved": True} for i in range(n)]
    return {"decision": verdict, "claim_checks": checks,
            "materially_complete": (verdict == "PASS") if complete is None else complete,
            "reason": "Reviewed evidence"}


A1 = evidence_aliases((U1,))


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


def run(prov, ret=None, units=(U1, U2, U3, OUTSIDE), question="Quais regras de compartilhamento?",
        expand=0):
    ret = ret or R()
    return run_lean(question, snapshot_id="signed-catalog", units=units,
                    retriever=ret, provider=prov, expand_documents=expand)


def test_happy_path_one_answer_and_one_review():
    p = P(answer(("Public must use approved business channel", ["E1"])), verify())
    r = run(p)
    assert r["status"] == "answered_pending_human_review"
    assert "[E1]" in r["rendered_answer"]
    assert r["evidence_ids"] == {"E1": "u1"}
    assert [x[0] for x in p.calls] == ["answer", "verify"]
    assert r["semantic_quality"] == "not_independently_established"


def test_retrieve_once_then_answer_and_review():
    p = P(retrieve(), answer(("Public rule", ["E1"]), ("Confidential rule", ["E2"])), verify(2))
    r = run(p)
    assert r["status"] == "answered_pending_human_review"
    assert r["recovery_used"]
    assert [x[0] for x in p.calls] == ["answer", "answer", "verify"]
    assert "[E2]" in r["rendered_answer"]
    assert r["evidence_ids"] == {"E1": "u1", "E2": "u2"}


def test_retrieval_does_not_widen_explicit_document_scope():
    p = P(retrieve(), answer(("Public rule", ["E1"]), ("Confidential rule", ["E2"])), verify(2))
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
    r = run(P(answer(("Public", ["E1"])), verify(verdict="REJECT", bad=0)))
    assert r["status"] == "review_rejected" and r["rendered_answer"] is None
    assert r["answer"] is None


def test_inconsistent_model_pass_is_overruled_not_fatal():
    # The model says PASS while failing its only claim: Python derives REJECT.
    r = run(P(answer(("Public", ["E1"])), verify(bad=0)))
    assert r["status"] == "review_rejected" and r["rendered_answer"] is None
    assert r["review"]["verdict"] == "REJECT"
    assert r["review"]["model_verdict_consistent"] is False


def test_failed_claim_is_removed_and_verified_claims_are_kept():
    p = P(retrieve(), answer(("Public rule", ["E1"]), ("Invented rule", ["E2"])),
          verify(2, verdict="REJECT", bad=1, complete=True))
    r = run(p)
    assert r["status"] == "answered_with_reservations"
    assert [c["text"] for c in r["answer"]["claims"]] == ["Public rule"]
    assert "Invented rule" not in r["rendered_answer"]
    assert "não passar na verificação" in r["reservations"][0]


def test_incomplete_answer_is_flagged_by_default():
    r = run(P(answer(("Public", ["E1"])), verify(verdict="REJECT", complete=False)))
    assert r["status"] == "answered_with_reservations"
    assert "Public" in r["rendered_answer"] and r["reservations"]


def test_incomplete_answer_can_be_withheld():
    r = run_lean("Quais regras?", snapshot_id="s", units=(U1,), retriever=R(),
                 provider=P(answer(("Public", ["E1"])), verify(verdict="REJECT", complete=False)),
                 on_incomplete="withhold")
    assert r["status"] == "review_rejected" and r["rendered_answer"] is None


def test_unit_ids_are_not_accepted_as_citations():
    with pytest.raises(LeanContractError):
        validate_decision(json.dumps(answer(("A", ["u1"]))), A1, can_retrieve=True)


def test_completed_document_includes_unindexed_title_units():
    @dataclass(frozen=True)
    class T(U):
        structural_role: str = "list_item"
    title = T("t", "R003 incident - decisions", searchable=False, structural_role="title")
    table = T("dup", "Duplicate table", searchable=False, structural_role="table")
    bullet = T("b", "Approve dispatch checklist")
    selected = assemble_evidence((bullet,), (title, table, bullet), expand_documents=1, max_units=10)
    assert [u.unit_id for u in selected] == ["t", "b"]


def test_models_receive_aliases_and_labelled_authority():
    p = P(answer(("Public", ["E1"])), verify())
    run_lean("Quais regras?", snapshot_id="s", units=(U1,), retriever=R(), provider=p,
             document_metadata={"DOC-005": {"title": "Data Sharing Policy", "status": "active",
                                            "authority_level": 4, "version": "2.2"}})
    for _, payload in p.calls:
        item = payload["evidence"][0]
        assert item["id"] == "E1" and "u1" not in json.dumps(payload)
        header = payload["documents"]["DOC-005"]
        assert header["authority"].startswith("rank 1 of 4 (highest)")
        assert "authority_level" not in header and "document" not in item


def test_authority_label_inverts_registry_scale():
    assert describe_document({"authority_level": 1})["authority"].startswith("rank 4 of 4 (lowest)")
    assert describe_document({}) == {}


def test_duplicate_claim_citations_are_deduplicated():
    value = validate_decision(json.dumps(answer(("A", ["E1", "E1"]))), A1, can_retrieve=True)
    assert value["claims"][0]["citation_ids"] == ["E1"]


def test_unknown_citations_are_removed_and_uncited_claims_dropped():
    raw = answer(("Kept", ["E1", "E77"]), ("Dropped", ["foreign"]))
    value = validate_decision(json.dumps(raw), A1, can_retrieve=True)
    assert [c["text"] for c in value["claims"]] == ["Kept"]
    assert value["claims"][0]["citation_ids"] == ["E1"] and value["uncited_claims_removed"] == 1


def test_answer_whose_claims_cite_nothing_valid_fails_closed():
    with pytest.raises(LeanContractError):
        validate_decision(json.dumps(answer(("A", ["foreign"]))), A1, can_retrieve=True)


def test_duplicate_json_keys_rejected():
    with pytest.raises(LeanContractError):
        validate_decision('{"evidence_use":[],"decision":"answer","decision":"answer","claims":[],"recovery_query":null,"message":""}', A1, can_retrieve=True)


def test_no_unexpected_field_in_response():
    raw = answer(("A", ["E1"]))
    raw["extra"] = "untrusted"
    with pytest.raises(LeanContractError):
        validate_decision(json.dumps(raw), A1, can_retrieve=True)


def test_recovery_response_requires_real_query():
    with pytest.raises(LeanContractError):
        validate_decision(json.dumps(retrieve("")), A1, can_retrieve=True)


def test_verifier_cannot_add_fields():
    bad = verify()
    bad["claim_checks"][0]["verified_citation_ids"] = ["out"]
    with pytest.raises(LeanContractError):
        validate_review(json.dumps(bad), answer(("Public", ["E1"])))


def test_unchecked_claim_is_treated_as_unverified_not_as_a_crash():
    review = validate_review(json.dumps(verify()), answer(("Public", ["E1"]), ("Secure", ["E2"])))
    assert review["passed_claims"] == [0] and review["unchecked_claims"] == 1
    assert review["verdict"] == "REJECT"


def test_prompt_does_not_include_planner_or_assurance_stage():
    p = P(answer(("Public", ["E1"])), verify())
    run(p)
    assert [stage for stage, _ in p.calls] == ["answer", "verify"]
    for _, payload in p.calls:
        assert "requirements" not in payload and "plan" not in payload


def test_report_has_trace_but_not_full_source_dump():
    p = P(answer(("Public", ["E1"])), verify())
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


def test_duplicate_or_out_of_range_claim_checks_cannot_approve_a_claim():
    review = verify(2)
    review["claim_checks"][1]["claim_index"] = 0
    review["claim_checks"][1]["entailed"] = False
    review["claim_checks"].append({"claim_index": 7, "entailed": True, "relevant": True,
                                   "conditions_preserved": True})
    result = validate_review(json.dumps(review), answer(("A", ["E1"]), ("B", ["E1"])))
    assert result["passed_claims"] == [] and result["unchecked_claims"] == 1


def test_provider_budget_exception_is_distinct_from_contract_failure():
    class BudgetExceeded(RuntimeError):
        pass
    class FaultyProvider:
        def invoke(self, stage, payload):
            raise BudgetExceeded("Stop at budget")
    r = run(FaultyProvider())
    assert r["status"] == "budget_exceeded"


def test_answer_without_claims_becomes_abstention_instead_of_crashing():
    r = run(P(answer()))
    assert r["status"] == "abstained" and r["reason"]


def test_stray_recovery_query_and_claims_are_dropped():
    stray = clarify()
    stray["recovery_query"] = "unused"
    stray["claims"] = [dict(text="x", citation_ids=["E1"])]
    value = validate_decision(json.dumps(stray), A1, can_retrieve=True)
    assert value["recovery_query"] is None and value["claims"] == []


def test_direct_evidence_left_unused_is_a_diagnostic_not_a_reservation():
    candidate = answer(("Public rule", ["E1"]))
    candidate["evidence_use"] = [{"id": "E1", "relevance": "direct"},
                                 {"id": "E2", "relevance": "direct"},
                                 {"id": "E9", "relevance": "direct"}]
    r = run(P(candidate, verify()), ret=R(initial=(U1, U2)))
    assert r["status"] == "answered_pending_human_review"
    assert "E2 (DOC-005)" in r["diagnostics"][0] and "E9" not in r["diagnostics"][0]


ENGLISH = "The policy requires that the data must be shared only with the approved channel."
PT_QUESTION = "Quais cuidados a política exige para que os dados sejam compartilhados?"


def test_answer_in_another_language_is_repaired_once():
    p = P(answer((ENGLISH, ["E1"])), answer(("A política exige que os dados sejam compartilhados com o canal aprovado.", ["E1"])), verify())
    r = run(p, question=PT_QUESTION)
    assert r["status"] == "answered_pending_human_review" and r["language_repair_used"]
    assert [stage for stage, _ in p.calls] == ["answer", "answer", "verify"]
    assert "previous_attempt_error" in p.calls[1][1] and "previous_attempt_error" not in p.calls[0][1]


def test_answer_still_in_another_language_after_repair_is_flagged():
    r = run(P(answer((ENGLISH, ["E1"])), answer((ENGLISH, ["E1"])), verify()), question=PT_QUESTION)
    assert r["status"] == "answered_with_reservations"
    assert any("idioma" in note for note in r["reservations"])


def test_language_detection_is_conservative():
    assert detect_language("Quais são as regras que se aplicam para os dados?") == "pt"
    assert detect_language("Which rules apply to the data and when must it be shared?") == "en"
    assert detect_language("Puedes usar IA para analizar los contratos que son de la empresa y del proveedor") == "es"
    assert detect_language("DOC-005 SLA OTIF") is None


def test_models_are_told_the_answer_language():
    p = P(answer(("Regra pública", ["E1"])), verify())
    run(p, question="Quais são as regras que se aplicam para os dados?")
    assert all(payload["answer_language"] == "português do Brasil" for _, payload in p.calls)


def test_answer_without_direct_evidence_is_refused_before_verification():
    candidate = answer(("Regra vizinha", ["E1"]))
    candidate["evidence_use"] = [{"id": "E1", "relevance": "conditional"}]
    p = P(candidate)
    r = run(p)
    assert r["status"] == "abstained" and r["rendered_answer"] is None
    assert [stage for stage, _ in p.calls] == ["answer"]


def test_claim_citing_only_background_evidence_is_dropped():
    candidate = answer(("Regra direta", ["E1"]), ("Contexto", ["E2"]))
    candidate["evidence_use"] = [{"id": "E1", "relevance": "direct"},
                                 {"id": "E2", "relevance": "background"}]
    r = run(P(candidate, verify()), ret=R(initial=(U1, U2)))
    assert [c["text"] for c in r["answer"]["claims"]] == ["Regra direta"]
    assert r["status"] == "answered_with_reservations"


def test_best_documents_are_completed_and_grouped_in_source_order():
    other = U("o1", "Other document section", "DOC-006")
    catalog = (U1, U2, U3, other, OUTSIDE)
    hidden = U("h", "Not searchable duplicate", searchable=False)
    selected = assemble_evidence((other, U3), catalog + (hidden,), expand_documents=1, max_units=10)
    # DOC-006 ranks first and is completed; DOC-005 keeps only its retrieved unit.
    assert [u.unit_id for u in selected] == ["o1", "u3"]
    selected = assemble_evidence((U3, other), catalog + (hidden,), expand_documents=1, max_units=10)
    assert [u.unit_id for u in selected] == ["u1", "u2", "u3", "o1"]
    assert [u.unit_id for u in assemble_evidence((U3, other), catalog, expand_documents=0, max_units=10)] == ["u3", "o1"]
    assert len(assemble_evidence((U3, other), catalog, expand_documents=2, max_units=2)) == 2


def test_pipeline_sends_completed_document_to_the_model():
    p = P(answer(("Regra", ["E1"])), verify())
    r = run(p, ret=R(initial=(U2,)), expand=1)
    assert [e["text"] for e in p.calls[0][1]["evidence"]] == [U1.reading_text, U2.reading_text, U3.reading_text]
    assert r["evidence_ids"] == {"E1": "u1", "E2": "u2", "E3": "u3"}


def test_every_evaluation_question_has_a_detectable_language():
    from app.evaluation.answer_criteria import load_criteria
    for case in load_criteria():
        assert detect_language(case.question, minimum=1) == "pt", case.case_id


def test_verifier_receives_only_cited_and_usable_evidence():
    candidate = answer(("Regra", ["E1"]))
    candidate["evidence_use"] = [{"id": "E1", "relevance": "direct"},
                                 {"id": "E2", "relevance": "conditional"},
                                 {"id": "E3", "relevance": "background"}]
    p = P(candidate, verify())
    run(p, ret=R(initial=(U1, U2, U3)))
    assert [e["id"] for e in p.calls[0][1]["evidence"]] == ["E1", "E2", "E3"]
    assert [e["id"] for e in p.calls[1][1]["evidence"]] == ["E1", "E2"]


def test_document_header_is_sent_once_per_document():
    p = P(answer(("Regra", ["E1"])), verify())
    run_lean("Quais regras?", snapshot_id="s", units=(U1, U2), retriever=R(initial=(U1, U2)),
             provider=p, document_metadata={"DOC-005": {"title": "Data Sharing Policy"}})
    assert json.dumps(p.calls[0][1]).count("Data Sharing Policy") == 1
