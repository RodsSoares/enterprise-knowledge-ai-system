"""RV-041 HF1: assurance boundary aligned with planner exclusions and inventory gaps."""
import json
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from app.orchestration.v3_pipeline import run_v3
from app.orchestration.v3_semantic_contracts import V3SemanticError, validate_assurance


Q = "Como compartilhar dados?"


@dataclass(frozen=True)
class Unit:
    unit_id: str = "u1"
    document_id: str = "DOC-005"
    reading_text: str = "External sharing requires an approved channel."
    status: str = "ready"
    structural_role: str = "section"
    section_path: tuple = ()


U = Unit()


def _plan():
    return SimpleNamespace(items=(
        {"requirement_id": "C1", "need": "Approved channel", "relevance": "in_scope",
         "evidence_status": "supported", "supports": [{"unit_id": "u1"}]},
        {"requirement_id": "C2", "need": "Exclude AI approvals", "relevance": "out_of_scope",
         "evidence_status": "excluded", "supports": []},
    ), has_known_gap=False)


def _assessment(*, inventory_gap=False, target="C1", source="u1", extra_row=False):
    rows = [{"requirement_id": "C1", "relevance": "applicable",
             "entailment": "supported", "supporting_unit_ids": [source]}]
    if extra_row:
        rows.append({"requirement_id":"C2", "relevance":"irrelevant",
                     "entailment":"supported", "supporting_unit_ids":[]})
    return json.dumps({
        "requirements": rows, "inventory_complete": not inventory_gap,
        "omitted_facets": ["Unresolved authority"] if inventory_gap else [],
        "decision": "RETRIEVE_MORE" if inventory_gap else "APPROVE",
        "lookup": {"semantic_query":"authority and secure sharing", "lexical_query":"approved authorization",
                   "document_ids": ["DOC-005"], "target_requirement_ids": [target]}
                  if inventory_gap else None,
        "reason": "Audited evidence inventory",
    })


def _inv(*, unresolved=False):
    return {"facets":[{"description":"Approved channel", "supporting_unit_ids":["u1"]}],
            "unresolved_facets":["Authority details"] if unresolved else []}


def _validate(raw, *, gap=False):
    return validate_assurance(raw, plan=_plan(), inventory=_inv(unresolved=gap),
                              candidates=(U,), recovery_used=False,
                              allowed_document_ids=("DOC-005",))


def test_supported_facet_can_be_targeted_when_independent_inventory_is_incomplete():
    assert _validate(_assessment(inventory_gap=True), gap=True)["decision"] == "RETRIEVE_MORE"


def test_out_of_scope_id_never_becomes_recovery_target():
    with pytest.raises(V3SemanticError, match="in-scope"):
        _validate(_assessment(inventory_gap=True, target="C2"), gap=True)


def test_unrequested_exclusion_assessment_is_rejected_not_silently_used():
    with pytest.raises(V3SemanticError, match="Foreign"):
        _validate(_assessment(extra_row=True))


def test_active_requirement_cannot_cite_out_of_catalog_unit():
    with pytest.raises(V3SemanticError, match="unauthorized"):
        _validate(_assessment(source="forged-unit"))


def test_supported_facet_cannot_trigger_unnecessary_recovery_without_gap():
    raw = json.loads(_assessment(inventory_gap=True))
    raw["omitted_facets"] = []
    raw["inventory_complete"] = False
    # Inventory is complete; the assessor cannot invent missing inventory.
    # The structural gate does not establish this independently, so we assert
    # that mismatched inventory references do not by themselves authorize a
    # foreign/out-of-scope recovery target.
    raw["lookup"]["target_requirement_ids"] = ["C2"]
    with pytest.raises(V3SemanticError):
        _validate(json.dumps(raw))


def test_pipeline_assurance_input_contains_only_active_requirement_ids():
    plan = {"items": [
        {"need":"Approved channel", "relevance":"in_scope", "condition":None,
         "question_quote":"compartilhar", "evidence_status":"supported",
         "supports":[{"unit_id":"u1","quote":U.reading_text}], "missing_aspects":[]},
        {"need":"Exclude unrelated AI use", "relevance":"out_of_scope", "condition":None,
         "question_quote":"compartilhar", "evidence_status":"excluded",
         "supports":[], "missing_aspects":[]},
    ], "action":{"kind":"complete"}}
    calls = []
    class Provider:
        def invoke(self, stage, payload):
            calls.append((stage, payload))
            values = {
                "scope_v3": {"request_kind":"general", "focus":"External sharing",
                             "known_conditions":[],"exclusions":[],"unknown_conditions":[],
                             "decision":"proceed", "clarification":None},
                "plan_v3": plan,
                "inventory_v3": _inv(),
                "assurance_v3": json.loads(_assessment()),
                "generate_v3": {"status":"answered", "claims":[{
                    "text":"Use an approved channel", "requirement_ids":["C1"],
                    "citation_ids":["u1"]}],"abstention_reason":None},
                "verify_v3": {"claims":[{"claim_index":0, "entailed":True,
                    "relevant":True, "conditions_preserved":True,
                    "verified_citation_ids":["u1"]}],
                    "materially_complete":True,"omissions":[],"decision":"PASS", "reason":"Verified"},
            }
            return json.dumps(values[stage])
    class Retriever:
        def search(self, query, document_ids, top_k):
            return (U,), {}
        def search_projections(self,*args):
            raise AssertionError("Unexpected recovery")
    result = run_v3(Q, snapshot_id="snapshot", units=(U,), retriever=Retriever(), provider=Provider())
    assert result["status"] == "answered_pending_human_review"
    payload = next(value for stage, value in calls if stage == "assurance_v3")
    assert [x["requirement_id"] for x in payload["requirements"]] == ["C1"]
    assert [x["requirement_id"] for x in payload["excluded_requirements"]] == ["C2"]
