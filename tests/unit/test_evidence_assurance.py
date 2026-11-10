"""RV-038 fail-closed contract tests; no network or LLM."""
import json
import pytest

from app.orchestration.evidence_assurance import (
    AssuranceContractError, AssuranceRequest, validate_assurance,
)


def req(recovery=False):
    return AssuranceRequest.create(
        question="What changed in the current policy?", snapshot_id="snapshot-1",
        requirement_ids=["old", "current", "rationale"],
        candidate_chunk_ids=["DOC-001::c1", "DOC-002::c1"],
        recovery_used=recovery,
    )


def proposal(request, decision="RETRIEVE_MORE"):
    r = request.payload
    return {
        "schema_version": r["schema_version"],
        "question_hash": r["question_hash"],
        "snapshot_id": r["snapshot_id"],
        "evidence_set_hash": r["evidence_set_hash"],
        "requirements": [
            {"requirement_id": "old", "status": "supported", "supporting_chunk_ids": ["DOC-002::c1"]},
            {"requirement_id": "current", "status": "supported", "supporting_chunk_ids": ["DOC-001::c1"]},
            {"requirement_id": "rationale", "status": "missing", "supporting_chunk_ids": []},
        ],
        "decision": decision,
        "lookup": {"kind": "search", "query": "historical approval rationale", "target_requirement_ids": ["rationale"]}
            if decision == "RETRIEVE_MORE" else None,
        "reason_codes": ["MISSING_RATIONALE"],
    }


def valid(p, request):
    return validate_assurance(json.dumps(p), request).payload


def test_bounded_retrieve_allowed():
    assert valid(proposal(req()), req())["decision"] == "RETRIEVE_MORE"


def test_missing_evidence_blocks_approval():
    p = proposal(req(), "APPROVE")
    with pytest.raises(AssuranceContractError):
        valid(p, req())


def test_exhausted_budget_blocks_more_retrieval():
    r = req(True)
    with pytest.raises(AssuranceContractError):
        valid(proposal(r), r)


def test_foreign_candidate_rejected():
    r = req()
    p = proposal(r)
    p["requirements"][0]["supporting_chunk_ids"] = ["foreign"]
    with pytest.raises(AssuranceContractError):
        valid(p, r)


def test_stale_evidence_set_rejected():
    r = req()
    p = proposal(r)
    p["evidence_set_hash"] = "old"
    with pytest.raises(AssuranceContractError):
        valid(p, r)


def test_missing_requirement_rejected():
    r = req()
    p = proposal(r)
    p["requirements"].pop()
    with pytest.raises(AssuranceContractError):
        valid(p, r)


def test_lookup_must_target_gap():
    r = req()
    p = proposal(r)
    p["lookup"]["target_requirement_ids"] = ["current"]
    with pytest.raises(AssuranceContractError):
        valid(p, r)


def test_approve_all_supported():
    r = req()
    p = proposal(r, "APPROVE")
    p["requirements"][2] = {"requirement_id": "rationale", "status": "supported", "supporting_chunk_ids": ["DOC-002::c1"]}
    assert valid(p, r)["decision"] == "APPROVE"


def test_abstain_on_gap_after_recovery():
    r = req(True)
    assert valid(proposal(r, "ABSTAIN"), r)["decision"] == "ABSTAIN"


def test_duplicate_json_keys_rejected():
    r = req()
    raw = json.dumps(proposal(r))
    raw = raw.replace('"decision": "RETRIEVE_MORE",', '"decision": "RETRIEVE_MORE", "decision": "APPROVE",')
    with pytest.raises(AssuranceContractError):
        validate_assurance(raw, r)


def test_extra_field_rejected():
    r = req()
    p = proposal(r)
    p["arbitrary_tool"] = "run anything"
    with pytest.raises(AssuranceContractError):
        valid(p, r)


def test_bad_request_rejected():
    with pytest.raises(AssuranceContractError):
        AssuranceRequest.create(question="q", snapshot_id="s", requirement_ids=["x", "x"], candidate_chunk_ids=[])
