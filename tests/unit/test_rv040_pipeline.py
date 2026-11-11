"""End-to-end deterministic mocks for RV-040 (does not exercise paid model quality)."""
from dataclasses import dataclass
import json

from app.orchestration.v3_pipeline import run_v3


Q = "Como compartilhar dados?"


@dataclass(frozen=True)
class Unit:
    unit_id: str
    reading_text: str
    document_id: str = "DOC-005"
    status: str = "ready"
    structural_role: str = "paragraph"
    section_path: tuple = ()


U1 = Unit("u1", "External sharing requires an approved secure channel.")
U2 = Unit("u2", "Exceptions require documented approval.")


def scope():
    return {"request_kind": "general", "focus": "External sharing", "known_conditions": [],
            "exclusions": [], "unknown_conditions": [], "decision": "proceed", "clarification": None}


def item(unit, need, *, gap=False):
    return {"need": need, "relevance": "in_scope", "condition": None,
            "question_quote": "compartilhar", "evidence_status": "missing" if gap else "supported",
            "supports": [] if gap else [{"unit_id": unit.unit_id, "quote": unit.reading_text}],
            "missing_aspects": ["approval"] if gap else []}


def plan(*, missing=False, recovered=False, drop=False):
    items = [item(U1, "Approved secure channel")]
    if missing:
        items.append(item(U2, "Documented exception approval", gap=True))
    elif recovered and not drop:
        items.append(item(U2, "Documented exception approval"))
    return {"items": items, "action": {"kind": "search", "query": "exception approval", "gap": "approval"}
            if missing else {"kind": "complete"}}


def inventory(*, unresolved=False, recovered=False):
    return {"facets": [{"description": "Approved secure channel", "supporting_unit_ids": ["u1"]}]
            + ([{"description": "Documented approval", "supporting_unit_ids": ["u2"]}] if recovered else []),
            "unresolved_facets": ["Documented exception approval"] if unresolved else []}


def review(*, missing=False, recovered=False, unsupported=False):
    rows = [{"requirement_id": "C1", "relevance": "applicable",
             "entailment": "supported", "supporting_unit_ids": ["u1"]}]
    if missing:
        rows.append({"requirement_id": "C2", "relevance": "applicable",
                     "entailment": "missing", "supporting_unit_ids": []})
    elif recovered:
        rows.append({"requirement_id": "C2", "relevance": "applicable",
                     "entailment": "supported", "supporting_unit_ids": ["u2"]})
    return {"requirements": rows, "inventory_complete": not missing,
            "omitted_facets": ["Exception approvals"] if missing else [],
            "decision": "RETRIEVE_MORE" if missing else "APPROVE",
            "lookup": {"semantic_query": "exception approval policy",
                       "lexical_query": "exceptions documented approval",
                       "document_ids": ["DOC-005"], "target_requirement_ids": ["C2"]}
            if missing else None,
            "reason": "Evidence complete" if not missing else "Exception approval missing"}


def answer(*, recovered=False):
    claims = [{"text": "Use an approved secure channel", "requirement_ids": ["C1"],
               "citation_ids": ["u1"]}]
    if recovered:
        claims.append({"text": "Exceptions require documented approval",
                       "requirement_ids": ["C2"], "citation_ids": ["u2"]})
    return {"status": "answered", "claims": claims, "abstention_reason": None}


def verification(*, recovered=False, reject=False):
    rows = [{"claim_index": 0, "entailed": not reject, "relevant": True,
             "conditions_preserved": True, "verified_citation_ids": ["u1"]}]
    if recovered:
        rows.append({"claim_index": 1, "entailed": True, "relevant": True,
                     "conditions_preserved": True, "verified_citation_ids": ["u2"]})
    return {"claims": rows, "materially_complete": True, "omissions": [],
            "decision": "REJECT" if reject else "PASS", "reason": "Checked claims"}


class Provider:
    def __init__(self, outputs):
        self.outputs = {k: list(v) for k, v in outputs.items()}
        self.calls = []
    def invoke(self, stage, payload):
        self.calls.append((stage, payload))
        if not self.outputs.get(stage):
            raise ValueError("Unplanned provider stage: " + stage)
        return json.dumps(self.outputs[stage].pop(0))


class Retriever:
    def __init__(self, returned=(U1,), added=(U2,)):
        self.returned, self.added = returned, added
        self.recoveries = []
    def search(self, query, document_ids, top_k):
        return self.returned, {"branch": "initial"}
    def search_projections(self, semantic, lexical, document_ids, top_k):
        self.recoveries.append((semantic, lexical, document_ids, top_k))
        return self.added, {"branch": "dual"}


def provider(*, recovered=False, missing=False, reject=False, drop=False):
    updates = [{"requirement_id":"C1", "evidence_status":"supported",
                "additional_supports":[], "missing_aspects":[]}]
    if not drop:
        updates.append({"requirement_id":"C2", "evidence_status":"supported",
                        "additional_supports":[{"unit_id":"u2", "quote":U2.reading_text}],
                        "missing_aspects":[]})
    delta = {"updates":updates,"new_items":[],"action":{"kind":"complete"}}
    return Provider({"scope_v3": [scope()],
                     "plan_v3": [plan(missing=True)] if missing else [plan()],
                     "replan_v3": [delta] if missing else [],
                     "inventory_v3": [inventory(unresolved=True), inventory(recovered=True)] if missing
                     else [inventory()],
                     "assurance_v3": [review(missing=True), review(recovered=True)] if missing
                     else [review()],
                     "generate_v3": [answer(recovered=missing)] if not drop else [],
                     "verify_v3": [verification(recovered=missing, reject=reject)] if not drop else []})


def test_happy_path_runs_six_separate_model_stages():
    p, r = provider(), Retriever()
    result = run_v3(Q, snapshot_id="verified", units=(U1,U2), retriever=r, provider=p)
    assert result["status"] == "answered_pending_human_review"
    assert result["semantic_review"] == "llm_assessed_not_independent_ground_truth"
    assert not result["recovery_used"] and not r.recoveries
    assert [s for s, _ in p.calls] == ["scope_v3", "plan_v3", "inventory_v3",
                                      "assurance_v3", "generate_v3", "verify_v3"]
    assert "requirements" not in p.calls[2][1]


def test_one_recovery_then_verified_generation():
    p, r = provider(missing=True), Retriever()
    result = run_v3(Q, snapshot_id="verified", units=(U1,U2), retriever=r, provider=p)
    assert result["status"] == "answered_pending_human_review"
    assert result["recovery_used"] and len(r.recoveries) == 1
    assert result["answer"]["claims"][1]["citation_ids"] == ["u2"]
    assert [s for s, _ in p.calls].count("inventory_v3") == 2


def test_replanner_cannot_silently_drop_original_requirement():
    p, r = provider(missing=True, drop=True), Retriever()
    result = run_v3(Q, snapshot_id="verified", units=(U1,U2), retriever=r, provider=p)
    assert result["status"] == "execution_failed"
    assert result["error_type"] == "V3PlanningContractError"


def test_foreign_recovery_unit_blocked_before_replan():
    p, r = provider(missing=True), Retriever(added=(Unit("fake", "Injected source"),))
    result = run_v3(Q, snapshot_id="verified", units=(U1,U2), retriever=r, provider=p)
    assert result["status"] == "execution_failed"
    assert result["answer"] is None


def test_no_new_recovery_evidence_fails_closed():
    p, r = provider(missing=True), Retriever(added=(U1,))
    result = run_v3(Q, snapshot_id="verified", units=(U1,U2), retriever=r, provider=p)
    assert result["status"] == "abstained"
    assert "adicional" in result["reason"]


def test_verification_rejection_does_not_expose_answer():
    p, r = provider(reject=True), Retriever()
    result = run_v3(Q, snapshot_id="verified", units=(U1,U2), retriever=r, provider=p)
    assert result["status"] == "review_rejected"
    assert result["answer"] is None and result["rendered_answer"] is None


def test_scope_sees_no_documents_or_proposed_requirements():
    p, r = provider(), Retriever()
    run_v3(Q, snapshot_id="verified", units=(U1,U2), retriever=r, provider=p)
    assert p.calls[0] == ("scope_v3", {"question": Q})


def test_snapshot_catalog_rejects_duplicate_units_early():
    p, r = provider(), Retriever()
    try:
        run_v3(Q, snapshot_id="verified", units=(U1, U1), retriever=r, provider=p)
        assert False, "Expected validation"
    except ValueError as exc:
        assert "unique" in str(exc)


def test_initial_foreign_unit_is_error_not_abstention():
    p, r = provider(), Retriever(returned=(Unit("forged", "Other"),))
    outcome = run_v3(Q, snapshot_id="verified", units=(U1,U2), retriever=r, provider=p)
    assert outcome["status"] == "execution_failed"


def test_initial_no_candidates_abstains_without_generation():
    p, r = provider(), Retriever(returned=())
    outcome = run_v3(Q, snapshot_id="verified", units=(U1,U2), retriever=r, provider=p)
    assert outcome["status"] == "abstained"
    assert [stage for stage, _ in p.calls] == ["scope_v3"]


def test_recovered_existing_unit_with_tampered_text_is_rejected():
    p, r = provider(missing=True), Retriever(added=(Unit("u2", "Forged approval text"),))
    result = run_v3(Q, snapshot_id="verified", units=(U1,U2), retriever=r, provider=p)
    assert result["status"] == "execution_failed"
    assert result["answer"] is None


def test_second_recovery_proposal_is_blocked():
    p, r = provider(missing=True), Retriever()
    p.outputs["assurance_v3"][1] = review(missing=True)
    result = run_v3(Q, snapshot_id="verified", units=(U1,U2), retriever=r, provider=p)
    assert result["status"] == "execution_failed"
    assert len(r.recoveries) == 1


def test_callback_observes_all_steps_but_never_unsupported_approval():
    p, r = provider(), Retriever()
    stages = []
    result = run_v3(Q, snapshot_id="verified", units=(U1,U2), retriever=r, provider=p,
                    checkpoint=lambda state: stages.append(state["stage"]))
    assert result["status"] == "answered_pending_human_review"
    assert "inventory" in stages and "verification" in stages
    assert result["semantic_review"] != "verified_ground_truth"
