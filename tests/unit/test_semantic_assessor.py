"""RV-038C1 offline boundary tests."""
import json
from copy import deepcopy

import pytest

from app.orchestration.contracts import digest
from app.orchestration.semantic_assessor import (
    SemanticBoundaryError,
    assess_planned_bundle,
)


def planned():
    bundle = {
        "snapshot_id": "snapshot-c1",
        "coverage": [{
            "coverage_id": "C1",
            "need": "Current policy rule",
            "supports": [{"unit_id": "unit-1"}],
        }],
        "evidence": [{
            "unit_id": "unit-1",
            "document_id": "DOC-001",
            "reading_text": "Current policy permits approved carriers.",
            "section_path": ["Rules"],
            "status": "ready",
        }],
    }
    bundle["bundle_hash"] = digest(bundle)
    return {
        "status": "planned_pending_review",
        "snapshot_id": "snapshot-c1",
        "question": "What is the current policy rule?",
        "bundle": bundle,
        "trace": [],
    }


class FakeProvider:
    def __init__(self, status="supported"):
        self.status = status
        self.calls = []

    def invoke(self, stage, payload):
        self.calls.append((stage, payload))
        r = payload["assurance_request"]
        supported = self.status == "supported"
        return json.dumps({
            "schema_version": r["schema_version"],
            "question_hash": r["question_hash"],
            "snapshot_id": r["snapshot_id"],
            "evidence_set_hash": r["evidence_set_hash"],
            "requirements": [{
                "requirement_id": "C1",
                "status": self.status,
                "supporting_chunk_ids": (
                    ["unit-1"] if supported else []
                ),
            }],
            "decision": "APPROVE" if supported else "ABSTAIN",
            "lookup": None,
            "reason_codes": ["OFFLINE_FIXTURE"],
        })


def test_canonical_text_reaches_provider():
    provider = FakeProvider()
    result = assess_planned_bundle(
        question=planned()["question"],
        planning_result=planned(),
        provider=provider,
    )
    assert result.status == "approved_structurally"
    stage, payload = provider.calls[0]
    assert stage == "assurance"
    assert "approved carriers" in (
        payload["canonical_evidence"][0]["reading_text"]
    )


def test_missing_support_abstains():
    provider = FakeProvider("missing")
    result = assess_planned_bundle(
        question=planned()["question"],
        planning_result=planned(),
        provider=provider,
    )
    assert result.status == "abstained"


def test_tampering_rejected_before_provider():
    p = planned()
    p["bundle"]["evidence"][0]["reading_text"] = "tampered"
    provider = FakeProvider()
    with pytest.raises(Exception, match="hash"):
        assess_planned_bundle(
            question=p["question"],
            planning_result=p,
            provider=provider,
        )
    assert not provider.calls


def test_missing_text_rejected():
    p = planned()
    del p["bundle"]["evidence"][0]["reading_text"]
    p["bundle"]["bundle_hash"] = digest({
        k: v for k, v in p["bundle"].items()
        if k != "bundle_hash"
    })
    provider = FakeProvider()
    with pytest.raises(SemanticBoundaryError, match="text"):
        assess_planned_bundle(
            question=p["question"],
            planning_result=p,
            provider=provider,
        )
    assert not provider.calls


def test_context_budget_blocks_provider():
    provider = FakeProvider()
    with pytest.raises(SemanticBoundaryError, match="budget"):
        assess_planned_bundle(
            question=planned()["question"],
            planning_result=planned(),
            provider=provider,
            max_context_chars=10,
        )
    assert not provider.calls


def test_golden_labels_not_in_payload():
    provider = FakeProvider()
    p = planned()
    assess_planned_bundle(
        question=p["question"],
        planning_result=p,
        provider=provider,
    )
    payload = provider.calls[0][1]
    assert "expected_evidence" not in payload
    assert "golden_questions" not in payload


def test_unready_evidence_rejected():
    p = planned()
    p["bundle"]["evidence"][0]["status"] = "unresolved_structure"
    p["bundle"]["bundle_hash"] = digest({
        k: v for k, v in p["bundle"].items()
        if k != "bundle_hash"
    })
    provider = FakeProvider()
    with pytest.raises(SemanticBoundaryError, match="not ready"):
        assess_planned_bundle(
            question=p["question"],
            planning_result=p,
            provider=provider,
        )
    assert not provider.calls
