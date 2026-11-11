"""RV-038D1 offline recovery tests."""
import json
from dataclasses import dataclass

import pytest

from app.orchestration.contracts import digest
from app.orchestration.assurance_adapter import AssuranceIntegrationError
from app.orchestration.evidence_assurance import AssuranceContractError
from app.orchestration.assurance_recovery import run_bounded_recovery


@dataclass(frozen=True)
class Unit:
    unit_id: str
    document_id: str
    reading_text: str
    status: str = "ready"


U1 = Unit("u1", "DOC-001", "Existing rule")
U2 = Unit("u2", "DOC-001", "Recovered exception approval")


def planning(*, recovered=False):
    coverage = [
        {"coverage_id": "C1", "supports": [{"unit_id": "u1"}]},
        {"coverage_id": "C2", "supports": [
            {"unit_id": "u2" if recovered else "u1"}
        ]},
    ]

    evidence = [{
        "unit_id": U1.unit_id,
        "document_id": U1.document_id,
        "reading_text": U1.reading_text,
        "status": "ready",
    }]

    if recovered:
        evidence.append({
            "unit_id": U2.unit_id,
            "document_id": U2.document_id,
            "reading_text": U2.reading_text,
            "status": "ready",
        })

    bundle = {
        "snapshot_id": "snapshot",
        "coverage": coverage,
        "evidence": evidence,
    }
    bundle["bundle_hash"] = digest(bundle)

    return {
        "status": "planned_pending_review",
        "question": "What are the required controls?",
        "snapshot_id": "snapshot",
        "bundle": bundle,
        "trace": [],
    }


def assessor(decision, support_c2=False):
    def assess(request):
        r = request.payload
        complete = decision == "APPROVE"
        return json.dumps({
            "schema_version": r["schema_version"],
            "question_hash": r["question_hash"],
            "snapshot_id": r["snapshot_id"],
            "evidence_set_hash": r["evidence_set_hash"],
            "requirements": [
                {
                    "requirement_id": "C1",
                    "status": "supported",
                    "supporting_chunk_ids": ["u1"],
                },
                {
                    "requirement_id": "C2",
                    "status": "supported" if complete else "missing",
                    "supporting_chunk_ids": (
                        ["u2"] if complete else []
                    ),
                },
            ],
            "decision": decision,
            "lookup": {
                "kind": "search",
                "query": "find exception rule",
                "target_requirement_ids": ["C2"],
            } if decision == "RETRIEVE_MORE" else None,
            "reason_codes": ["OFFLINE_TEST"],
        })
    return assess


def run(*, search=None, replan=None, final=None):
    return run_bounded_recovery(
        question="What are the required controls?",
        initial_planning=planning(),
        first_assessor=assessor("RETRIEVE_MORE"),
        final_assessor=final or assessor("APPROVE"),
        search=search or (lambda q, n: [U2]),
        replan=replan or (
            lambda q, original, ids, lookup: planning(recovered=True)
        ),
        allowed_units=(U1, U2),
    )


def test_successful_recovery_and_final_approval():
    searches = []
    replans = []

    def search(q, limit):
        searches.append((q, limit))
        return [U2]

    def replan(q, original, ids, lookup):
        replans.append((ids, lookup["query"]))
        return planning(recovered=True)

    outcome = run(search=search, replan=replan)

    assert outcome.status == "approved_structurally"
    assert outcome.recovered_ids == ("u2",)
    assert outcome.final_decision["decision"] == "APPROVE"
    assert len(searches) == 1
    assert len(replans) == 1


def test_no_new_evidence_abstains_without_replan():
    def forbidden(*args):
        raise AssertionError("Replanning must not run")

    outcome = run(
        search=lambda q, n: [U1],
        replan=forbidden,
    )
    assert outcome.status == "abstained_no_new_evidence"
    assert outcome.final_decision is None


def test_foreign_retrieval_rejected():
    foreign = Unit("foreign", "DOC-999", "Unexpected")
    with pytest.raises(AssuranceIntegrationError, match="foreign"):
        run(search=lambda q, n: [foreign])


def test_wrong_snapshot_rejected():
    def wrong(q, original, ids, lookup):
        p = planning(recovered=True)
        p["snapshot_id"] = "other"
        return p

    with pytest.raises(AssuranceIntegrationError, match="identity"):
        run(replan=wrong)


def test_replan_must_include_recovered_evidence():
    with pytest.raises(AssuranceIntegrationError, match="incorporate"):
        run(
            replan=lambda q, original, ids, lookup: planning()
        )


def test_second_retrieval_disallowed():
    with pytest.raises(AssuranceContractError):
        run(final=assessor("RETRIEVE_MORE"))


def test_remaining_gap_can_abstain():
    outcome = run(final=assessor("ABSTAIN"))
    assert outcome.status == "abstained"
    assert outcome.final_decision["decision"] == "ABSTAIN"


def test_recovered_text_tampering_rejected():
    def corrupted(q, original, ids, lookup):
        p = planning(recovered=True)
        p["bundle"]["evidence"][1]["reading_text"] = "Altered"
        p["bundle"]["bundle_hash"] = digest({
            k: v for k, v in p["bundle"].items()
            if k != "bundle_hash"
        })
        return p

    with pytest.raises(AssuranceIntegrationError, match="differs"):
        run(replan=corrupted)


def test_initial_approval_skips_recovery():
    outcome = run_bounded_recovery(
        question="What are the required controls?",
        initial_planning=planning(recovered=True),
        first_assessor=assessor("APPROVE"),
        final_assessor=lambda req: (
            _ for _ in ()
        ).throw(AssertionError("Unexpected final assessment")),
        search=lambda q, n: (
            _ for _ in ()
        ).throw(AssertionError("Unexpected search")),
        replan=lambda *args: (
            _ for _ in ()
        ).throw(AssertionError("Unexpected replan")),
        allowed_units=(U1, U2),
    )
    assert outcome.status == "approved_structurally"
    assert outcome.final_decision is None
