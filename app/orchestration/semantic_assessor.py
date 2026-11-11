"""RV-038C1: offline semantic-assessment input boundary.

The provider proposes a decision; the existing assurance contract
validates it. No network, Golden Set, or production integration here.
"""
import json

from app.orchestration.assurance_adapter import (
    AssuranceIntegrationError, evaluate_planned_bundle,
)
from app.orchestration.contracts import digest


class SemanticBoundaryError(ValueError):
    pass


class SemanticAssessor:
    def __init__(self, *, planning_result, provider, max_chars=24000):
        if type(max_chars) is not int or max_chars < 1:
            raise SemanticBoundaryError("Invalid context budget")
        if not hasattr(provider, "invoke"):
            raise SemanticBoundaryError("Provider must expose invoke")
        self.planning_result = planning_result
        self.provider = provider
        self.max_chars = max_chars

    def __call__(self, request):
        planning = self.planning_result
        bundle = planning.get("bundle")
        if not isinstance(bundle, dict):
            raise SemanticBoundaryError("Missing evidence bundle")

        expected_hash = digest({
            k: v for k, v in bundle.items()
            if k != "bundle_hash"
        })
        if bundle.get("bundle_hash") != expected_hash:
            raise SemanticBoundaryError("Bundle integrity failure")

        r = request.payload
        if (
            planning.get("snapshot_id") != r["snapshot_id"]
            or digest(planning.get("question")) != r["question_hash"]
        ):
            raise SemanticBoundaryError("Question/snapshot mismatch")

        evidence = bundle.get("evidence", [])
        coverage = bundle.get("coverage", [])

        evidence_ids = [e.get("unit_id") for e in evidence]
        requirement_ids = [
            c.get("coverage_id") for c in coverage
        ]

        if (
            evidence_ids != r["candidate_chunk_ids"]
            or requirement_ids != r["requirement_ids"]
        ):
            raise SemanticBoundaryError("Stale evidence requirements")

        materials = []
        for item in evidence:
            text = item.get("reading_text")
            if not isinstance(text, str) or not text.strip():
                raise SemanticBoundaryError("Missing canonical evidence text")

            if item.get("status") != "ready":
                raise SemanticBoundaryError("Evidence unit not ready")

            materials.append({
                "unit_id": item["unit_id"],
                "document_id": item["document_id"],
                "reading_text": text,
                "section_path": item.get("section_path", []),
            })

        needs = []
        for item in coverage:
            supports = [
                s["unit_id"] for s in item["supports"]
            ]
            if not set(supports) <= set(evidence_ids):
                raise SemanticBoundaryError("Foreign coverage support")
            needs.append({
                "requirement_id": item["coverage_id"],
                "description": item["need"],
                "candidate_support_ids": supports,
            })

        payload = {
            "schema_version": "rv038c1/1",
            "question": planning["question"],
            "assurance_request": r,
            "requirements": needs,
            "canonical_evidence": materials,
            "instruction": (
                "Assess whether each requirement is semantically "
                "supported by the evidence text. Do not treat source "
                "presence alone as proof of support. Do not invent "
                "facts, use Golden Set labels, or execute tools. "
                "Return only the strict assurance decision JSON."
            ),
        }

        serialized = json.dumps(
            payload, ensure_ascii=False, allow_nan=False
        )
        if len(serialized) > self.max_chars:
            raise SemanticBoundaryError("Semantic context budget exceeded")

        raw = self.provider.invoke(
            "assurance", json.loads(serialized)
        )
        if not isinstance(raw, str):
            raise SemanticBoundaryError("Provider must return JSON text")
        return raw


def assess_planned_bundle(
    *, question, planning_result, provider,
    search=None, allowed_units=None,
    recovery_used=False, max_extra=20,
    max_context_chars=24000,
):
    assessor = SemanticAssessor(
        planning_result=planning_result,
        provider=provider,
        max_chars=max_context_chars,
    )
    return evaluate_planned_bundle(
        question=question,
        planning_result=planning_result,
        assess=assessor,
        search=search,
        allowed_units=allowed_units,
        recovery_used=recovery_used,
        max_extra=max_extra,
    )
