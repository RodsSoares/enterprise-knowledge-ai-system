"""RV-040: opt-in, end-to-end, bounded experimental evidence pipeline.

This file does not change app/orchestration/evidence_pipeline.py. It takes an
already verified canonical snapshot catalog, a retriever bound to that catalog,
and an explicit provider. LLM assessments are *declarations*, not proofs.
"""
from dataclasses import asdict
from time import perf_counter
import json

from app.chunking.evidence_units import digest
from app.orchestration.coordinator import BudgetExceeded
from app.orchestration.evidence_planner import validate_scope
from app.orchestration.v3_planning_contract import validate_v3_plan
from app.orchestration.v3_replanning_contract import validate_v3_replan
from app.orchestration.v3_semantic_contracts import (
    V3SemanticError, validate_inventory, validate_assurance, provenance_id,
)
from app.generation.v3_answer_contract import validate_answer, validate_verification
from app.orchestration.v42_relevance_contract import apply_relevance
from app.orchestration.v42_verification_contract import validate_v42_verification

PIPELINE_V3 = "rv040/pipeline-experimental-1"


def _source(unit):
    return {"unit_id": unit.unit_id, "document_id": unit.document_id,
            "reading_text": unit.reading_text, "section_path": list(unit.section_path),
            "structural_role": unit.structural_role, "status": unit.status}


def _join(baseline, additional):
    merged = {u.unit_id: u for u in baseline}
    for u in additional:
        merged.setdefault(u.unit_id, u)
    return tuple(merged.values())


def run_v3(question, *, snapshot_id, units, retriever, provider,
           max_candidates=20, max_units=40, max_context_chars=60000,
           checkpoint=lambda state: None, relevance_mode=False):
    """Scope→discovery→plan→independent inventory→assure→optional recovery
    →replan→reinventorize→reassure→generate→verify. No silent retries.

    provider.invoke(stage, payload) -> strict JSON string; all live calls must
    use ONE BudgetedClient shared with the embedding provider in retriever.
    """
    if type(relevance_mode) is not bool:
        raise ValueError("Invalid relevance mode")
    if (not isinstance(question, str) or not question.strip() or len(question) > 4000
            or not isinstance(snapshot_id, str) or not snapshot_id
            or type(max_candidates) is not int or not 1 <= max_candidates <= 40
            or type(max_units) is not int or not max_candidates <= max_units <= 80
            or type(max_context_chars) is not int or not 1000 <= max_context_chars <= 128000):
        raise ValueError("Invalid RV-040 inputs or limits")
    if not callable(getattr(provider, "invoke", None)):
        raise ValueError("Explicit bounded provider required")
    if not callable(getattr(retriever, "search", None)) or not callable(
        getattr(retriever, "search_projections", None)
    ):
        raise ValueError("Versioned retriever with dual-query support required")
    allowed = tuple(units)
    catalog = {u.unit_id: u for u in allowed}
    if not allowed or len(catalog) != len(allowed):
        raise ValueError("Canonical catalog must contain unique units")
    known_doc_ids = {u.document_id for u in allowed}
    started = perf_counter()
    result = {"contract_version": "rv042/pipeline-relevance-1" if relevance_mode else PIPELINE_V3, "status": "running",
              "question": question, "snapshot_id": snapshot_id, "stage": "scope",
              "scope": None, "plan": None, "inventory": None, "assurance": None,
              "answer": None, "verification": None, "rendered_answer": None,
              "recovery_used": False, "semantic_review": "not_performed",
              "trace": [], "elapsed_seconds": None}
    if relevance_mode:
        result["relevance_audits"] = []
        result["effective_plan"] = None

    def record(stage, **details):
        result["stage"] = stage
        result["trace"].append({"stage": stage, **details})
        result["elapsed_seconds"] = round(perf_counter() - started, 4)
        checkpoint(result)

    def invoke(stage, payload):
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        if len(body) > max_context_chars:
            raise V3SemanticError("LLM request exceeds context character budget")
        record("request_" + stage, payload_hash=digest(payload), chars=len(body))
        raw = provider.invoke(stage, payload)
        if not isinstance(raw, str):
            raise V3SemanticError("Provider did not return JSON string")
        return raw

    def validate_candidates(candidate_units, *, document_ids):
        if not isinstance(candidate_units, (tuple, list)) or len(candidate_units) > max_candidates:
            raise V3SemanticError("Search exceeded requested candidate budget")
        if len({u.unit_id for u in candidate_units}) != len(candidate_units):
            raise V3SemanticError("Repeated candidate")
        for unit in candidate_units:
            if catalog.get(unit.unit_id) != unit or (document_ids and unit.document_id not in document_ids):
                raise V3SemanticError("Foreign or unauthorized evidence")
        return tuple(candidate_units)

    try:
        scope = validate_scope(invoke("scope_v3", {"question": question}), question)
        result["scope"] = scope
        scope_hash = digest({"question": question, "scope": scope})
        record("scope", scope_hash=scope_hash)
        if scope["decision"] == "clarify":
            result.update(status="clarification_required", clarification=scope["clarification"])
            return result
        requested_docs = tuple(scope["document_ids"])
        if set(requested_docs) - known_doc_ids:
            result.update(status="abstained", reason="Documento explicitamente solicitado não disponível.")
            return result
        authorized_docs = requested_docs or tuple(sorted(known_doc_ids))
        found, trace = retriever.search(question, requested_docs, max_candidates)
        candidates = validate_candidates(found, document_ids=requested_docs)
        record("initial_retrieval", selected_ids=[u.unit_id for u in candidates], retrieval=trace)
        if not candidates:
            result.update(status="abstained", reason="Nenhuma evidência recuperada.")
            return result

        previous_plan = None
        previous_decision = None
        frozen_relevance = None
        for attempt in range(2):
            used = bool(attempt)
            result["recovery_used"] = used
            if len(candidates) > max_units:
                raise V3SemanticError("Merged candidate budget exceeded")
            planning_input = {"question": question, "scope": scope, "scope_hash": scope_hash,
                              "snapshot_id": snapshot_id, "recovery_used": used,
                              "candidates": [_source(u) for u in candidates]}
            if not used:
                plan = validate_v3_plan(
                    invoke("plan_v3", planning_input), question=question,
                    candidates=candidates, recovery_used=False,
                )
            else:
                # Preserve all previously declared requirement identities: no
                # free-form second planning pass, only validated evidence deltas.
                planning_input["previous_requirements"] = list(previous_plan.items)
                planning_input["previous_assurance"] = previous_decision
                plan = validate_v3_replan(
                    invoke("replan_v3", planning_input),
                    previous_plan=previous_plan, question=question, candidates=candidates,
                )
            result["plan"] = {"items": list(plan.items), "action": plan.action,
                              "has_known_gap": plan.has_known_gap}
            record("plan", attempt=attempt, plan_hash=digest(result["plan"]))
            if not relevance_mode and plan.action["kind"] == "clarify":
                result.update(status="clarification_required", clarification=plan.action["question"])
                return result
            if not relevance_mode and plan.action["kind"] == "abstain":
                result.update(status="abstained", reason=plan.action["reason"])
                return result

            # Critical anti-anchoring boundary: NO plan or suggested support IDs.
            inventory_input = {"question": question, "scope": scope, "snapshot_id": snapshot_id,
                               "candidates": [_source(u) for u in candidates]}
            inventory = validate_inventory(invoke("inventory_v3", inventory_input), candidates)
            result["inventory"] = inventory
            record("inventory", independent=True, facet_count=len(inventory["facets"]))
            effective_plan, effective_inventory = plan, inventory
            if relevance_mode:
                # Explicit, auditable *model* judgment; not semantic ground truth.
                # Restrict which already validated requirements can be mandatory,
                # never rewrite user scope, source quotes or the canonical catalog.
                gate_source_ids = {
                    link["unit_id"] for item in plan.items for link in item["supports"]
                } | {
                    uid for facet in inventory["facets"]
                    for uid in facet["supporting_unit_ids"]
                }
                gate_input = {
                    "question": question, "scope": scope, "scope_hash": scope_hash,
                    "snapshot_id": snapshot_id, "recovery_used": used,
                    "requirements": list(plan.items),
                    "independent_inventory": inventory,
                    # Source *subset* needed for relevance, not every retrieved hit.
                    # Provenance is inherited from the already validated plan/inventory.
                    "cited_evidence": [_source(u) for u in candidates
                                       if u.unit_id in gate_source_ids],
                    "frozen_classifications": frozen_relevance or {},
                }
                gate = apply_relevance(
                    invoke("relevance_v42", gate_input), plan=plan,
                    inventory=inventory, frozen=frozen_relevance, recovery_used=used,
                )
                frozen_relevance = gate.frozen
                effective_plan, effective_inventory = gate.plan, gate.inventory
                result["relevance_audits"].append(gate.audit)
                result["effective_plan"] = {
                    "items": list(effective_plan.items), "action": effective_plan.action,
                    "has_known_gap": effective_plan.has_known_gap,
                }
                record("relevance", attempt=attempt,
                       material_ids=gate.audit["material_requirements"],
                       adjacent_ids=gate.audit["adjacent_requirements"],
                       material_unresolved=gate.audit["material_unresolved_count"],
                       model_declared_sufficient=gate.audit["sufficient_on_current_evidence"])
            assurance_input = {
                "question": question, "scope": scope, "snapshot_id": snapshot_id,
                "scope_hash": scope_hash, "recovery_used": used,
                # Do not ask the semantic assessor to re-assess excluded items.
                # Their IDs belong to planner bookkeeping, not the approval set.
                "requirements": [x for x in effective_plan.items if x["relevance"] != "out_of_scope"],
                "excluded_requirements": [
                    {"requirement_id": x["requirement_id"], "need": x["need"]}
                    for x in plan.items if x["relevance"] == "out_of_scope" or (
                        relevance_mode and x["requirement_id"] not in {
                            i["requirement_id"] for i in effective_plan.items})
                ],
                "independent_inventory": effective_inventory,
                "candidates": [_source(u) for u in candidates],
                "provenance_id": provenance_id(question, snapshot_id, scope, candidates),
            }
            decision = validate_assurance(
                invoke("assurance_v3", assurance_input), plan=effective_plan,
                inventory=effective_inventory, candidates=candidates, recovery_used=used,
                allowed_document_ids=authorized_docs,
            )
            result["assurance"] = decision
            record("assurance", attempt=attempt, decision=decision["decision"])
            if decision["decision"] == "CLARIFY":
                result.update(status="clarification_required", clarification=decision["reason"])
                return result
            if decision["decision"] == "ABSTAIN":
                result.update(status="abstained", reason=decision["reason"])
                return result
            if decision["decision"] == "RETRIEVE_MORE":
                if used:
                    raise V3SemanticError("Second recovery forbidden")
                lookup = decision["lookup"]
                lookup_docs = tuple(lookup["document_ids"]) or requested_docs
                # An explicit user document restriction ALWAYS wins.
                if requested_docs and (not lookup_docs or not set(lookup_docs) <= set(requested_docs)):
                    raise V3SemanticError("Recovery widened document scope")
                result["recovery_used"] = True
                extra, retrieval_trace = retriever.search_projections(
                    lookup["semantic_query"], lookup["lexical_query"],
                    lookup_docs, max_candidates,
                )
                extra = validate_candidates(extra, document_ids=lookup_docs)
                additions = [u for u in extra if u.unit_id not in {x.unit_id for x in candidates}]
                record("recovery", recovered_ids=[u.unit_id for u in additions], retrieval=retrieval_trace)
                if not additions:
                    result.update(status="abstained", reason="Recuperação não encontrou evidência adicional.")
                    return result
                if len(candidates) + len(additions) > max_units:
                    # Bounded: do not silently discard original evidence.
                    result.update(status="abstained", reason="Limite de contexto para recuperação atingido.")
                    return result
                candidates = _join(candidates, additions)
                previous_plan = plan
                previous_decision = decision
                continue
            if decision["decision"] != "APPROVE" or effective_plan.action["kind"] != "complete":
                raise V3SemanticError("Inconsistent final approval and planning action")
            if digest({"question": question, "scope": scope}) != scope_hash:
                raise V3SemanticError("Frozen scope changed")
            # Generation sees source text only for units anchored by planned supports.
            supported_ids = {s["unit_id"] for row in effective_plan.items
                             if row["relevance"] != "out_of_scope" for s in row["supports"]}
            selected = tuple(u for u in candidates if u.unit_id in supported_ids)
            generation_input = {"question": question, "scope": scope, "snapshot_id": snapshot_id,
                                "requirements": list(effective_plan.items),
                                "independent_inventory": effective_inventory,
                                "evidence": [_source(u) for u in selected]}
            answer = validate_answer(invoke("generate_v3", generation_input), effective_plan, selected)
            result["answer"] = answer
            record("generation", status=answer["status"], claim_count=len(answer["claims"]))
            if answer["status"] == "abstained":
                result.update(status="abstained", reason=answer["abstention_reason"])
                return result
            verify_input = {"question": question, "scope": scope, "snapshot_id": snapshot_id,
                            "requirements": list(effective_plan.items), "independent_inventory": effective_inventory,
                            "evidence": [_source(u) for u in selected], "answer": answer}
            if relevance_mode:
                retained_ids = {x["requirement_id"] for x in effective_plan.items}
                suppressed = [x for x in plan.items if x["requirement_id"] not in retained_ids]
                excluded_unresolved = [
                    {"index": x["index"], "reason": x["reason"],
                     "text": inventory["unresolved_facets"][x["index"]]}
                    for x in gate.audit["unresolved_classifications"]
                    if x["classification"] == "adjacent"
                ]
                suppressed_source_ids = {
                    s["unit_id"] for x in suppressed for s in x["supports"]
                }
                verify_input["suppressed_requirements"] = suppressed
                verify_input["excluded_unresolved"] = excluded_unresolved
                verify_input["original_plan_action"] = plan.action
                verify_input["suppressed_evidence"] = [
                    _source(u) for u in candidates if u.unit_id in suppressed_source_ids]
            raw_verify = invoke("verify_v3", verify_input)
            if relevance_mode:
                verification = validate_v42_verification(
                    raw_verify, answer=answer, plan=effective_plan,
                    inventory=effective_inventory,
                    suppressed_ids=[x["requirement_id"] for x in suppressed],
                    excluded_unresolved_indices=[x["index"] for x in excluded_unresolved],
                )
            else:
                verification = validate_verification(
                    raw_verify, answer, effective_plan, effective_inventory)
            result["verification"] = verification
            record("verification", decision=verification["decision"])
            if verification["decision"] != "PASS":
                result.update(status="review_rejected", reason=verification["reason"], answer=None)
                return result
            result["rendered_answer"] = "\n".join(
                "- " + c["text"] + " [" + ", ".join(c["citation_ids"]) + "]"
                for c in answer["claims"])
            result.update(status="answered_pending_human_review",
                          semantic_review="llm_assessed_not_independent_ground_truth")
            return result
        result.update(status="abstained", reason="Recuperação esgotada.")
        return result
    except Exception as exc:
        result.update(status="budget_exceeded" if isinstance(exc, BudgetExceeded) else "execution_failed",
                      error_type=type(exc).__name__, answer=None, rendered_answer=None)
        record("error", error_type=type(exc).__name__)
        return result
    finally:
        result["elapsed_seconds"] = round(perf_counter() - started, 4)
        checkpoint(result)


def run_v42(question, **kwargs):
    """Opt-in RV-042; RV-040/RV-041 path remains run_v3() unchanged."""
    if "relevance_mode" in kwargs:
        raise ValueError("Do not override RV-042 relevance mode")
    return run_v3(question, relevance_mode=True, **kwargs)
