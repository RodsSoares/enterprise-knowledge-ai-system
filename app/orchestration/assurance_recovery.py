"""RV-038D1: bounded offline recovery and reassessment.

This is an experimental coordinator, not a production pipeline.
Assessors and replanner are explicitly supplied callables.
No LLM, SDK, embedding, or automatic answer generation.
"""
from dataclasses import dataclass

from app.orchestration.assurance_adapter import (
    AssuranceIntegrationError,
    evaluate_planned_bundle,
)


@dataclass(frozen=True)
class RecoveryOutcome:
    status: str
    first_decision: dict
    final_decision: dict | None
    recovered_ids: tuple[str, ...]
    trace: tuple[dict, ...]

    def to_dict(self):
        return {
            "status": self.status,
            "first_decision": self.first_decision,
            "final_decision": self.final_decision,
            "recovered_ids": list(self.recovered_ids),
            "trace": list(self.trace),
            "semantic_review": "unverified",
        }


def run_bounded_recovery(
    *,
    question,
    initial_planning,
    first_assessor,
    final_assessor,
    search,
    replan,
    allowed_units,
    max_extra=20,
):
    """One assurance, up to one lookup, one replan, one final assurance.

    assess(request) -> raw JSON
    search(query, top_k) -> authorized catalog units
    replan(question, original, recovered_ids, lookup) -> new planner result

    The replan callback must construct and validate a new plan.
    This coordinator does not synthesize a planner decision.
    """
    if not callable(replan):
        raise AssuranceIntegrationError("Replanner callable required")
    if not callable(first_assessor) or not callable(final_assessor):
        raise AssuranceIntegrationError("Assessor callables required")

    catalog = {u.unit_id: u for u in allowed_units}
    if len(catalog) != len(allowed_units):
        raise AssuranceIntegrationError("Duplicate catalog IDs")

    first = evaluate_planned_bundle(
        question=question,
        planning_result=initial_planning,
        assess=first_assessor,
        search=search,
        allowed_units=allowed_units,
        recovery_used=False,
        max_extra=max_extra,
    )

    trace = list(first.trace)

    if first.status != "replan_required":
        return RecoveryOutcome(
            status=first.status,
            first_decision=first.assessment,
            final_decision=None,
            recovered_ids=(),
            trace=tuple(trace),
        )

    recovered = first.discovered_unit_ids

    if not recovered:
        trace.append({
            "stage": "recovery",
            "status": "no_new_evidence",
        })
        return RecoveryOutcome(
            status="abstained_no_new_evidence",
            first_decision=first.assessment,
            final_decision=None,
            recovered_ids=(),
            trace=tuple(trace),
        )

    lookup = first.assessment["lookup"]
    revised = replan(
        question,
        initial_planning,
        recovered,
        lookup,
    )

    if not isinstance(revised, dict):
        raise AssuranceIntegrationError("Replanner returned invalid result")

    if revised.get("status") != "planned_pending_review":
        raise AssuranceIntegrationError("Replanner did not complete")

    if (
        revised.get("question") != question
        or revised.get("snapshot_id")
            != initial_planning.get("snapshot_id")
    ):
        raise AssuranceIntegrationError("Replanned identity mismatch")

    old_bundle = initial_planning["bundle"]
    new_bundle = revised.get("bundle")

    if not isinstance(new_bundle, dict):
        raise AssuranceIntegrationError("Replanned bundle missing")

    old_ids = {
        x["unit_id"] for x in old_bundle["evidence"]
    }
    revised_evidence = new_bundle.get("evidence")

    if not isinstance(revised_evidence, list):
        raise AssuranceIntegrationError("Invalid replanned evidence")

    revised_ids = {
        x["unit_id"] for x in revised_evidence
    }

    if not revised_ids <= old_ids | set(recovered):
        raise AssuranceIntegrationError(
            "Replanned evidence includes unauthorized IDs"
        )

    if not revised_ids.intersection(recovered):
        raise AssuranceIntegrationError(
            "Replanning must incorporate recovered evidence"
        )

    for item in revised_evidence:
        uid = item["unit_id"]
        if uid in recovered:
            unit = catalog[uid]
            if (
                item.get("reading_text") != unit.reading_text
                or item.get("document_id") != unit.document_id
                or item.get("status") != "ready"
            ):
                raise AssuranceIntegrationError(
                    "Recovered evidence differs from authorized unit"
                )

    trace.append({
        "stage": "replanning",
        "recovered_ids": list(recovered),
        "selected_ids": sorted(revised_ids),
    })

    final = evaluate_planned_bundle(
        question=question,
        planning_result=revised,
        assess=final_assessor,
        recovery_used=True,
        max_extra=max_extra,
    )

    trace.extend(final.trace)

    return RecoveryOutcome(
        status=final.status,
        first_decision=first.assessment,
        final_decision=final.assessment,
        recovered_ids=recovered,
        trace=tuple(trace),
    )
