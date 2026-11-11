"""RV-043 opt-in lean evidence pipeline: retrieve -> answer -> verify.

Optional single bounded retrieval when the answer model declares a missing fact.
Canonical source IDs are checked in Python; semantic verdicts are model judgments,
not mathematical proof of correctness. Existing pipelines remain unchanged.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from time import perf_counter

VERSION = "rv043/lean-pipeline-1"
DEFAULT_TOP_K = 16
DOC_PATTERN = re.compile(r"\bDOC-\d{3,}\b", re.IGNORECASE)


class LeanContractError(ValueError):
    pass


def _hash(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _object(raw, fields):
    if not isinstance(raw, str) or len(raw) > 100_000:
        raise LeanContractError("Invalid JSON response length")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise LeanContractError("Duplicate JSON key")
            result[key] = value
        return result
    try:
        data = json.loads(raw, object_pairs_hook=unique,
                          parse_constant=lambda value: (_ for _ in ()).throw(LeanContractError("Nonfinite JSON constant")))
    except LeanContractError:
        raise
    except (ValueError, TypeError, RecursionError) as exc:
        raise LeanContractError("Invalid JSON response") from exc
    if not isinstance(data, dict) or set(data) != set(fields):
        raise LeanContractError("Unexpected response fields")
    return data


def _text(value, *, limit=1800, allow_empty=False):
    if not isinstance(value, str) or len(value) > limit or (not allow_empty and not value.strip()):
        raise LeanContractError("Invalid text")
    return value


def _source(unit, metadata):
    return {"unit_id": unit.unit_id, "document_id": unit.document_id,
            "reading_text": unit.reading_text,
            "section_path": list(unit.section_path),
            "document_metadata": metadata.get(unit.document_id, {})}


def validate_decision(raw, candidates, *, can_retrieve):
    value = _object(raw, ("decision", "claims", "recovery_query", "message"))
    decision = value["decision"]
    if decision not in ("answer", "retrieve", "clarify", "abstain"):
        raise LeanContractError("Invalid decision")
    if not isinstance(value["claims"], list) or len(value["claims"]) > 16:
        raise LeanContractError("Invalid claims")
    known = {u.unit_id for u in candidates if u.status == "ready"}
    if decision == "answer":
        if not value["claims"] or value["recovery_query"] is not None:
            raise LeanContractError("Invalid answered structure")
        for row in value["claims"]:
            if not isinstance(row, dict) or set(row) != {"text", "citation_ids"}:
                raise LeanContractError("Invalid claim fields")
            _text(row["text"])
            ids = row["citation_ids"]
            if (not isinstance(ids, list) or not 1 <= len(ids) <= 12
                    or len(set(map(str, ids))) != len(ids)
                    or any(not isinstance(uid, str) or uid not in known for uid in ids)):
                raise LeanContractError("Claim cites foreign, duplicate or missing canonical unit")
    elif value["claims"]:
        raise LeanContractError("Only answer may contain claims")
    if decision == "retrieve":
        if not can_retrieve:
            raise LeanContractError("Repeated recovery forbidden")
        _text(value["recovery_query"], limit=600)
    elif value["recovery_query"] is not None:
        raise LeanContractError("Unexpected recovery query")
    _text(value["message"], limit=1200, allow_empty=(decision == "answer"))
    return value


def validate_review(raw, answer):
    value = _object(raw, ("decision", "claim_checks", "materially_complete", "reason"))
    if value["decision"] not in ("PASS", "REJECT"):
        raise LeanContractError("Unknown verification verdict")
    if type(value["materially_complete"]) is not bool:
        raise LeanContractError("Invalid completeness")
    _text(value["reason"], limit=1200)
    checks = value["claim_checks"]
    if not isinstance(checks, list) or len(checks) != len(answer["claims"]):
        raise LeanContractError("Verifier must check every claim")
    seen = set()
    all_valid = True
    for check in checks:
        if not isinstance(check, dict) or set(check) != {
            "claim_index", "entailed", "relevant", "conditions_preserved", "verified_citation_ids"
        }:
            raise LeanContractError("Unexpected claim check")
        idx = check["claim_index"]
        if type(idx) is not int or not 0 <= idx < len(checks) or idx in seen:
            raise LeanContractError("Invalid claim index")
        seen.add(idx)
        for key in ("entailed", "relevant", "conditions_preserved"):
            if type(check[key]) is not bool:
                raise LeanContractError("Invalid verifier boolean")
        ids = check["verified_citation_ids"]
        allowed = answer["claims"][idx]["citation_ids"]
        if (not isinstance(ids, list) or not ids or len(ids) != len(set(map(str, ids)))
                or any(not isinstance(uid, str) or uid not in allowed for uid in ids)
                or set(ids) != set(allowed)):
            raise LeanContractError("Verifier did not corroborate cited source IDs")
        if not all(check[k] for k in ("entailed", "relevant", "conditions_preserved")):
            all_valid = False
    if value["decision"] == "PASS" and (not all_valid or not value["materially_complete"]):
        raise LeanContractError("Unjustified verification PASS")
    if value["decision"] == "REJECT" and all_valid and value["materially_complete"]:
        raise LeanContractError("Contradictory verification REJECT")
    return value


def run_lean(question, *, snapshot_id, units, retriever, provider,
             document_metadata=None, top_k=DEFAULT_TOP_K, max_units=24, max_request_chars=65000,
             checkpoint=None):
    """Protocol-based dependency injection enables deterministic offline testing.

    retriever.search(question, document_ids, top_k) -> (canonical units, trace)
    provider.invoke(stage, payload) -> strict JSON string, stages 'answer'/'verify'.
    All live API calls must share a single BudgetedClient (enforced by CLI).
    """
    if (not isinstance(question, str) or not question.strip() or len(question) > 4000
            or not isinstance(snapshot_id, str) or not snapshot_id
            or type(top_k) is not int or not 1 <= top_k <= 30
            or type(max_units) is not int or not top_k <= max_units <= 40
            or type(max_request_chars) is not int or not 1000 <= max_request_chars <= 128000):
        raise ValueError("Invalid lean pipeline inputs")
    if not callable(getattr(retriever, "search", None)) or not callable(getattr(provider, "invoke", None)):
        raise ValueError("Explicit retriever and provider required")
    catalog_units = tuple(units)
    catalog = {u.unit_id: u for u in catalog_units}
    if not catalog_units or len(catalog) != len(catalog_units):
        raise ValueError("Canonical catalog must have unique evidence unit IDs")
    docs = {u.document_id for u in catalog_units}
    metadata = document_metadata or {}
    if not isinstance(metadata, dict) or set(metadata) - docs:
        raise ValueError("Unknown document metadata keys")
    required_docs = tuple(sorted(set(m.upper() for m in DOC_PATTERN.findall(question))))
    started = perf_counter()
    report = {"version": VERSION, "status": "running", "question": question,
              "snapshot_id": snapshot_id, "document_scope": list(required_docs),
              "answer": None, "review": None, "rendered_answer": None,
              "recovery_used": False, "trace": [], "elapsed_seconds": None,
              "semantic_quality": "not_independently_established"}
    def event(name, **details):
        report["trace"].append({"stage": name, **details})
        report["elapsed_seconds"] = round(perf_counter() - started, 4)
        if checkpoint is not None:
            checkpoint(report)
    def invoke(stage, payload):
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        if len(encoded) > max_request_chars:
            raise LeanContractError("Request exceeds bounded context")
        event("request_" + stage, payload_hash=_hash(payload), chars=len(encoded))
        raw = provider.invoke(stage, payload)
        if not isinstance(raw, str):
            raise LeanContractError("Provider must return strict JSON text")
        return raw
    def canonical_candidates(found, scope):
        if not isinstance(found, (tuple, list)) or len(found) > top_k:
            raise LeanContractError("Retriever exceeded candidate budget")
        ids = [u.unit_id for u in found]
        if len(ids) != len(set(ids)):
            raise LeanContractError("Duplicate retrieved units")
        for u in found:
            if (u.unit_id not in catalog or catalog[u.unit_id] != u
                    or not u.searchable or u.status != "ready"
                    or (scope and u.document_id not in scope)):
                raise LeanContractError("Foreign, unready or unauthorized source")
        return tuple(found)
    try:
        if set(required_docs) - docs:
            report.update(status="abstained", reason="Documento solicitado ausente do corpus canônico.")
            event("missing_requested_document", document_ids=list(required_docs))
            return report
        found, retrieval_trace = retriever.search(question, required_docs, top_k)
        candidates = canonical_candidates(found, required_docs)
        event("retrieval", selected_ids=[u.unit_id for u in candidates], retrieval=retrieval_trace)
        if not candidates:
            report.update(status="abstained", reason="Nenhuma evidência autorizada recuperada.")
            return report
        for attempt in range(2):
            payload = {"question": question, "document_scope": list(required_docs),
                       "snapshot_id": snapshot_id, "recovery_used": bool(attempt),
                       "evidence": [_source(u, metadata) for u in candidates]}
            answer = validate_decision(invoke("answer", payload), candidates, can_retrieve=not attempt)
            event("answer_decision", attempt=attempt, decision=answer["decision"])
            if answer["decision"] == "retrieve":
                query = answer["recovery_query"]
                # The recovery query can change ranking, but never document permissions.
                additional, trace = retriever.search(query, required_docs, top_k)
                additional = canonical_candidates(additional, required_docs)
                existing = {u.unit_id for u in candidates}
                new = tuple(u for u in additional if u.unit_id not in existing)
                event("recovery", added_ids=[u.unit_id for u in new], retrieval=trace)
                report["recovery_used"] = True
                if not new:
                    report.update(status="abstained", reason="Recuperação não encontrou evidência adicional.")
                    return report
                if len(candidates) + len(new) > max_units:
                    report.update(status="abstained", reason="Limite de evidências recuperadas atingido.")
                    return report
                candidates += new
                continue
            if answer["decision"] in ("clarify", "abstain"):
                report.update(status="clarification_required" if answer["decision"] == "clarify"
                              else "abstained", reason=answer["message"])
                return report
            # A model does not get to approve itself: verify in a separate call.
            report["answer"] = answer
            review_payload = {"question": question, "document_scope": list(required_docs),
                              "snapshot_id": snapshot_id, "answer": answer,
                              "evidence": [_source(u, metadata) for u in candidates]}
            review = validate_review(invoke("verify", review_payload), answer)
            report["review"] = review
            event("verification", verdict=review["decision"])
            if review["decision"] != "PASS":
                report.update(status="review_rejected", answer=None,
                              reason=review["reason"])
                return report
            rendered = "\n".join("- " + c["text"] + " [" + ", ".join(c["citation_ids"]) + "]"
                                 for c in answer["claims"])
            report.update(status="answered_pending_human_review", rendered_answer=rendered)
            return report
        report.update(status="abstained", reason="Limite de recuperação atingido.")
        return report
    except Exception as exc:
        report.update(status=("budget_exceeded" if type(exc).__name__ == "BudgetExceeded"
                              else "execution_failed"), error_type=type(exc).__name__,
                      error_message=str(exc)[:500], answer=None, rendered_answer=None)
        event("error", error_type=type(exc).__name__)
        return report
    finally:
        report["elapsed_seconds"] = round(perf_counter() - started, 4)
        if checkpoint is not None:
            checkpoint(report)
