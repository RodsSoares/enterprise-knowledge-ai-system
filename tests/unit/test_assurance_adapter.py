import json
from dataclasses import dataclass
from copy import deepcopy
import pytest

from app.orchestration.contracts import digest
from app.orchestration.assurance_adapter import evaluate_planned_bundle, AssuranceIntegrationError

@dataclass(frozen=True)
class U:
    unit_id: str


def prepared():
    bundle = {"snapshot_id": "snapshot", "coverage": [
        {"coverage_id": "C1", "supports": [{"unit_id": "u1"}]},
        {"coverage_id": "C2", "supports": [{"unit_id": "u1"}]}],
        "evidence": [{"unit_id": "u1"}]}
    bundle["bundle_hash"] = digest(bundle)
    return {"status": "planned_pending_review", "question": "question", "snapshot_id": "snapshot", "bundle": bundle, "trace": []}


def assessor(decision="APPROVE"):
    def evaluate(request):
        p = request.payload
        missing = decision != "APPROVE"
        d = dict(schema_version=p["schema_version"], question_hash=p["question_hash"],
                 snapshot_id=p["snapshot_id"], evidence_set_hash=p["evidence_set_hash"],
                 requirements=[{"requirement_id": rid,
                                "status": "missing" if missing and rid == "C2" else "supported",
                                "supporting_chunk_ids": [] if missing and rid == "C2" else ["u1"]}
                               for rid in p["requirement_ids"]],
                 decision=decision, lookup={"kind": "search", "query": "find reason",
                                            "target_requirement_ids": ["C2"]} if decision == "RETRIEVE_MORE" else None,
                 reason_codes=["TEST"])
        return json.dumps(d)
    return evaluate


def test_approve():
    result = evaluate_planned_bundle(question="question", planning_result=prepared(), assess=assessor())
    assert result.status == "approved_structurally"
    assert result.to_dict()["semantic_review"] == "not_performed"


def test_recovery_requires_replan():
    result = evaluate_planned_bundle(question="question", planning_result=prepared(),
        assess=assessor("RETRIEVE_MORE"), search=lambda q, n: [U("u2")], allowed_units=[U("u1"), U("u2")])
    assert result.status == "replan_required"
    assert result.discovered_unit_ids == ("u2",)


def test_foreign_evidence_rejected():
    with pytest.raises(AssuranceIntegrationError, match="foreign"):
        evaluate_planned_bundle(question="question", planning_result=prepared(),
            assess=assessor("RETRIEVE_MORE"), search=lambda q,n: [U("evil")], allowed_units=[U("u1")])


def test_missing_search_rejected():
    with pytest.raises(AssuranceIntegrationError, match="Authorized search"):
        evaluate_planned_bundle(question="question", planning_result=prepared(), assess=assessor("RETRIEVE_MORE"))


def test_question_mismatch_rejected():
    with pytest.raises(AssuranceIntegrationError, match="Question mismatch"):
        evaluate_planned_bundle(question="different", planning_result=prepared(), assess=assessor())


def test_tampered_bundle_rejected():
    p = prepared(); p["bundle"]["evidence"].append({"unit_id":"u2"})
    with pytest.raises(AssuranceIntegrationError, match="hash"):
        evaluate_planned_bundle(question="question", planning_result=p, assess=assessor())


def test_missing_coverage_support_rejected():
    p = prepared(); p["bundle"]["coverage"][0]["supports"]=[{"unit_id":"absent"}];p["bundle"]["bundle_hash"]=digest({k:v for k,v in p["bundle"].items() if k!="bundle_hash"})
    with pytest.raises(AssuranceIntegrationError, match="unknown evidence"):
        evaluate_planned_bundle(question="question", planning_result=p, assess=assessor())


def test_recovery_limit_rejected():
    with pytest.raises(AssuranceIntegrationError, match="budget"):
        evaluate_planned_bundle(question="question", planning_result=prepared(),assess=assessor("RETRIEVE_MORE"),
            search=lambda q,n: [U("u2"), U("u3")], allowed_units=[U("u1"),U("u2"),U("u3")], max_extra=1)


def test_declared_previous_recovery_rejected_by_contract():
    from app.orchestration.evidence_assurance import AssuranceContractError
    with pytest.raises(AssuranceContractError):
        evaluate_planned_bundle(question="question", planning_result=prepared(),assess=assessor("RETRIEVE_MORE"), recovery_used=True)
