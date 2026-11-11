"""RV-040: deterministic validity gates, not a claim of semantic model accuracy."""
from dataclasses import dataclass
import json

import pytest

from app.orchestration.v3_planning_contract import validate_v3_plan
from app.orchestration.v3_semantic_contracts import (
    V3SemanticError, validate_inventory, validate_assurance,
)
from app.generation.v3_answer_contract import validate_answer, validate_verification


@dataclass(frozen=True)
class Unit:
    unit_id: str
    reading_text: str
    document_id: str = "DOC-005"
    status: str = "ready"
    structural_role: str = "paragraph"


QUESTION = "Como compartilhar dados?"
U1 = Unit("u1", "Sharing requires a secure channel.")
U2 = Unit("u2", "Exception requires documented approval.")


def plan(*, gap=False):
    entries = [dict(need="Secure channel", relevance="in_scope", condition=None,
                    question_quote="compartilhar", evidence_status="supported",
                    supports=[{"unit_id": "u1", "quote": U1.reading_text}], missing_aspects=[])]
    if gap:
        entries.append(dict(need="Exception approval", relevance="category",
                            condition="When exception applies", question_quote="compartilhar",
                            evidence_status="missing", supports=[], missing_aspects=["approval"]))
    return validate_v3_plan(json.dumps({"items": entries,
        "action": {"kind": "search", "query": "exceptions", "gap": "approval"} if gap else {"kind": "complete"}}),
        question=QUESTION, candidates=(U1,U2))


def inv():
    return {"facets": [{"description": "Secure channel", "supporting_unit_ids": ["u1"]}],
            "unresolved_facets": []}


def review(*, decision="APPROVE", missing=False, lookup=None):
    return json.dumps({
        "requirements": [{"requirement_id": "C1", "relevance": "applicable",
                          "entailment": "missing" if missing else "supported",
                          "supporting_unit_ids": [] if missing else ["u1"]}],
        "inventory_complete": not missing,
        "omitted_facets": ["Secure channel"] if missing else [],
        "decision": decision, "lookup": lookup, "reason": "Assessed with canonical evidence",
    })


def test_inventory_rejects_foreign_evidence():
    raw = json.dumps({"facets": [{"description": "Rule", "supporting_unit_ids": ["u999"]}], "unresolved_facets": []})
    with pytest.raises(V3SemanticError, match="unauthorized"):
        validate_inventory(raw, (U1,))


def test_inventory_rejects_duplicate_keys():
    with pytest.raises(V3SemanticError, match="Duplicate JSON"):
        validate_inventory('{"facets":[],"facets":[],"unresolved_facets":[]}', (U1,))


def test_assurance_valid_approval_and_no_new_lookups():
    r = validate_assurance(review(), plan=plan(), inventory=inv(), candidates=(U1,U2),
                           recovery_used=False, allowed_document_ids=("DOC-005",))
    assert r["decision"] == "APPROVE"


def test_assurance_refuses_approve_known_gap():
    with pytest.raises(V3SemanticError):
        validate_assurance(review(), plan=plan(gap=True), inventory=inv(), candidates=(U1,U2),
                           recovery_used=False, allowed_document_ids=("DOC-005",))


def test_assurance_cannot_retrieve_twice():
    lookup = {"semantic_query": "approved exception", "lexical_query": "exception approval",
              "document_ids": ["DOC-005"], "target_requirement_ids": ["C1"]}
    with pytest.raises(V3SemanticError, match="repeated"):
        validate_assurance(review(decision="RETRIEVE_MORE", missing=True, lookup=lookup),
                           plan=plan(), inventory=inv(), candidates=(U1,U2),
                           recovery_used=True, allowed_document_ids=("DOC-005",))


def test_assurance_rejects_unauthorized_document():
    lookup = {"semantic_query": "approved exception", "lexical_query": "exception approval",
              "document_ids": ["DOC-666"], "target_requirement_ids": ["C1"]}
    with pytest.raises(V3SemanticError, match="unauthorized"):
        validate_assurance(review(decision="RETRIEVE_MORE", missing=True, lookup=lookup),
                           plan=plan(), inventory=inv(), candidates=(U1,U2),
                           recovery_used=False, allowed_document_ids=("DOC-005",))


def test_relational_claim_needs_support_for_each_facet():
    p = plan()
    answer = json.dumps({"status": "answered", "claims": [
        {"text": "A sharing control applies", "requirement_ids": ["C1"], "citation_ids": ["u2"]}],
        "abstention_reason": None})
    with pytest.raises(V3SemanticError, match="lacks evidence"):
        validate_answer(answer, p, (U1,U2))


def test_relational_claim_valid_and_final_verification():
    p = plan()
    ans = validate_answer(json.dumps({"status": "answered", "claims": [
        {"text": "Use a secure channel", "requirement_ids": ["C1"], "citation_ids": ["u1"]}],
        "abstention_reason": None}), p, (U1,))
    verification = json.dumps({"claims": [
        {"claim_index": 0, "entailed": True, "relevant": True,
         "conditions_preserved": True, "verified_citation_ids": ["u1"]}],
        "materially_complete": True, "omissions": [], "decision": "PASS", "reason": "All claims verified"})
    assert validate_verification(verification, ans, p, inv())["decision"] == "PASS"


def test_final_verifier_rejects_rubber_stamp():
    p = plan()
    ans = validate_answer(json.dumps({"status": "answered", "claims": [
        {"text": "Use a secure channel", "requirement_ids": ["C1"], "citation_ids": ["u1"]}],
        "abstention_reason": None}), p, (U1,))
    verification = json.dumps({"claims": [
        {"claim_index": 0, "entailed": False, "relevant": True,
         "conditions_preserved": True, "verified_citation_ids": ["u1"]}],
        "materially_complete": True, "omissions": [], "decision": "PASS", "reason": "All claims verified"})
    with pytest.raises(V3SemanticError, match="Invalid PASS"):
        validate_verification(verification, ans, p, inv())


def test_final_verifier_rejects_unlisted_citations():
    p = plan()
    ans = validate_answer(json.dumps({"status": "answered", "claims": [
        {"text": "Use a secure channel", "requirement_ids": ["C1"], "citation_ids": ["u1"]}],
        "abstention_reason": None}), p, (U1,))
    verification = json.dumps({"claims": [
        {"claim_index": 0, "entailed": True, "relevant": True,
         "conditions_preserved": True, "verified_citation_ids": ["u2"]}],
        "materially_complete": True, "omissions": [], "decision": "PASS", "reason": "All claims verified"})
    with pytest.raises(V3SemanticError, match="unpresented"):
        validate_verification(verification, ans, p, inv())


def test_relational_multi_requirement_claim_checks_each_source():
    question = QUESTION
    entries = [
        {"need": "Secure channel", "relevance": "in_scope", "condition": None,
         "question_quote": "compartilhar", "evidence_status": "supported",
         "supports": [{"unit_id": "u1", "quote": U1.reading_text}], "missing_aspects": []},
        {"need": "Documented approval", "relevance": "category", "condition": "When exception applies",
         "question_quote": "compartilhar", "evidence_status": "supported",
         "supports": [{"unit_id": "u2", "quote": U2.reading_text}], "missing_aspects": []},
    ]
    p = validate_v3_plan(json.dumps({"items": entries, "action": {"kind": "complete"}}),
                         question=question, candidates=(U1,U2))
    raw = json.dumps({"status": "answered", "claims": [{
        "text": "Share through an approved channel; exceptions need approval",
        "requirement_ids": ["C1", "C2"], "citation_ids": ["u1", "u2"]}],
        "abstention_reason": None})
    assert len(validate_answer(raw, p, (U1,U2))["claims"]) == 1
    bad = json.loads(raw)
    bad["claims"][0]["citation_ids"] = ["u1"]
    with pytest.raises(V3SemanticError, match="lacks evidence"):
        validate_answer(json.dumps(bad), p, (U1,U2))
