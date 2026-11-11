"""RV-038C2B tests: offline only, no SDK/API."""
import json

import pytest

from app.orchestration.contracts import digest
from app.scripts.rv038c2b_semantic_pilot import (
    extract_planning, prepare, assess_once, main,
)


def planned():
    bundle = {
        "snapshot_id": "snapshot-pilot",
        "coverage": [{
            "coverage_id": "C1",
            "need": "What is required",
            "supports": [{"unit_id": "unit-1"}],
        }],
        "evidence": [{
            "unit_id": "unit-1",
            "document_id": "DOC-001",
            "reading_text": "Approved carriers are required.",
            "section_path": ["Rules"],
            "status": "ready",
        }],
    }
    bundle["bundle_hash"] = digest(bundle)
    return {
        "status": "planned_pending_review",
        "snapshot_id": "snapshot-pilot",
        "question": "What is required?",
        "bundle": bundle,
        "trace": [],
    }


class FakeProvider:
    def __init__(self, decision="APPROVE"):
        self.decision = decision
        self.calls = 0

    def invoke(self, stage, payload):
        self.calls += 1
        r = payload["assurance_request"]
        complete = self.decision == "APPROVE"
        return json.dumps({
            "schema_version": r["schema_version"],
            "question_hash": r["question_hash"],
            "snapshot_id": r["snapshot_id"],
            "evidence_set_hash": r["evidence_set_hash"],
            "requirements": [{
                "requirement_id": "C1",
                "status": "supported" if complete else "missing",
                "supporting_chunk_ids": (
                    ["unit-1"] if complete else []
                ),
            }],
            "decision": self.decision,
            "lookup": {
                "kind": "search",
                "query": "missing approval evidence",
                "target_requirement_ids": ["C1"],
            } if self.decision == "RETRIEVE_MORE" else None,
            "reason_codes": ["PILOT_FIXTURE"],
        })


def test_direct_and_enveloped_input():
    p = planned()
    assert extract_planning(p) is p
    assert extract_planning({"result": {"planning": p}}) is p


def test_prepare_contains_canonical_text():
    request, context = prepare(planned())
    assert request.payload["requirement_ids"] == ["C1"]
    assert "Approved carriers" in (
        context["canonical_evidence"][0]["reading_text"]
    )


def test_approve_single_call():
    provider = FakeProvider()
    result = assess_once(planned(), provider)
    assert result["decision"] == "APPROVE"
    assert provider.calls == 1


def test_retrieve_is_recorded_not_executed():
    provider = FakeProvider("RETRIEVE_MORE")
    result = assess_once(planned(), provider)
    assert result["decision"] == "RETRIEVE_MORE"
    assert provider.calls == 1


def test_recovery_budget_blocks_second_lookup():
    from app.orchestration.evidence_assurance import (
        AssuranceContractError,
    )
    with pytest.raises(AssuranceContractError):
        assess_once(
            planned(), FakeProvider("RETRIEVE_MORE"),
            recovery_used=True,
        )


def test_tampered_evidence_fails_preflight():
    p = planned()
    p["bundle"]["evidence"][0]["reading_text"] = "Tampered"
    with pytest.raises(ValueError, match="integrity"):
        prepare(p)


def test_cli_dry_run_no_api(tmp_path):
    p = tmp_path / "planning.json"
    out = tmp_path / "report.json"
    p.write_text(json.dumps(planned()), encoding="utf-8")
    assert main([
        "--input", str(p),
        "--output", str(out),
    ]) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["status"] == "dry_run"
    assert report["decision"] is None
    assert report["usage"] is None


def test_extract_planning_prefers_nested_result_over_outer_status():
    """Real planner reports repeat the planning status at the root."""
    p = planned()
    report = {
        "status": "planned_pending_review",
        "experiment": "evidence_planner",
        "result": p,
        "usage": {"calls": 2},
    }
    assert extract_planning(report) is p

    pipeline_report = {
        "status": "answered_pending_review",
        "result": {"planning": p},
    }
    assert extract_planning(pipeline_report) is p
