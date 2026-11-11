"""RV-038 experimental assurance boundary.

This module validates *declared* evidence assessments; it does not prove
semantic entailment. It never executes retrieval, accesses golden answers,
or changes the production RAG path.
"""
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any


class AssuranceContractError(ValueError):
    """Invalid evidence-assurance request or assessment."""


def _digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _object(value: Any, fields: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise AssuranceContractError(f"Invalid {label} fields")
    return value


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise AssuranceContractError(f"Invalid {label}")
    return value


def _unique_ids(values: Any, label: str) -> list[str]:
    if not isinstance(values, list):
        raise AssuranceContractError(f"Invalid {label} list")
    result = [_id(x, label) for x in values]
    if len(result) != len(set(result)):
        raise AssuranceContractError(f"Duplicate {label}")
    return result


def _strict_json(raw: str) -> dict:
    if not isinstance(raw, str) or len(raw) > 100_000:
        raise AssuranceContractError("Invalid JSON response size")

    def pairs(seq):
        out = {}
        for k, v in seq:
            if k in out:
                raise AssuranceContractError("Duplicate JSON key")
            out[k] = v
        return out

    def constant(_):
        raise AssuranceContractError("Nonstandard JSON constant")

    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, RecursionError) as exc:
        raise AssuranceContractError("Invalid JSON") from exc
    if not isinstance(value, dict):
        raise AssuranceContractError("Expected JSON object")
    return value


@dataclass(frozen=True)
class AssuranceRequest:
    """Immutable boundary: declared requirements + authorized candidate IDs.

    Requirements must come from a query planner or independently supplied
    specification, NOT golden-set labels used by the runtime system.
    """
    serialized: str

    @property
    def payload(self) -> dict:
        return json.loads(self.serialized)

    @classmethod
    def create(cls, *, question: str, snapshot_id: str,
               requirement_ids: list[str], candidate_chunk_ids: list[str],
               recovery_used: bool = False) -> "AssuranceRequest":
        _id(question, "question")
        _id(snapshot_id, "snapshot_id")
        reqs = _unique_ids(requirement_ids, "requirement_id")
        candidates = _unique_ids(candidate_chunk_ids, "chunk_id")
        if not reqs:
            raise AssuranceContractError("At least one requirement is needed")
        if type(recovery_used) is not bool:
            raise AssuranceContractError("recovery_used must be boolean")
        payload = {
            "schema_version": "0.1",
            "question_hash": _digest(question),
            "snapshot_id": snapshot_id,
            "requirement_ids": reqs,
            "candidate_chunk_ids": candidates,
            "evidence_set_hash": _digest(candidates),
            "recovery_used": recovery_used,
        }
        return cls(json.dumps(payload, ensure_ascii=False, sort_keys=True))


@dataclass(frozen=True)
class AssuranceResult:
    serialized: str

    @property
    def payload(self) -> dict:
        return json.loads(self.serialized)


def validate_assurance(raw: str, request: AssuranceRequest) -> AssuranceResult:
    """Validate a proposed outcome; fail closed on invalid or missing coverage.

    Passing this gate means structural consistency only. Semantic sufficiency,
    source authority, and factual correctness require separate evaluation.
    """
    p = _strict_json(raw)
    _object(p, {"schema_version", "question_hash", "snapshot_id",
                "evidence_set_hash", "requirements", "decision", "lookup",
                "reason_codes"}, "assessment")
    r = request.payload
    for key in ("schema_version", "question_hash", "snapshot_id", "evidence_set_hash"):
        if p[key] != r[key]:
            raise AssuranceContractError(f"Stale or mismatched {key}")
    reason_codes = _unique_ids(p["reason_codes"], "reason_code")
    if not reason_codes:
        raise AssuranceContractError("Reason codes required")
    if not isinstance(p["requirements"], list):
        raise AssuranceContractError("Requirements must be a list")

    seen = set()
    statuses = {}
    permitted_chunks = set(r["candidate_chunk_ids"])
    for item in p["requirements"]:
        _object(item, {"requirement_id", "status", "supporting_chunk_ids"}, "requirement")
        rid = _id(item["requirement_id"], "requirement_id")
        if rid in seen or rid not in r["requirement_ids"]:
            raise AssuranceContractError("Unknown or repeated requirement")
        seen.add(rid)
        status = item["status"]
        if status not in {"supported", "partial", "missing", "conflicted", "not_applicable"}:
            raise AssuranceContractError("Invalid requirement status")
        supports = _unique_ids(item["supporting_chunk_ids"], "supporting_chunk_id")
        if not set(supports) <= permitted_chunks:
            raise AssuranceContractError("Evidence not in authorized snapshot candidates")
        if status == "supported" and not supports:
            raise AssuranceContractError("Supported requirement needs cited candidates")
        if status in {"missing", "not_applicable"} and supports:
            raise AssuranceContractError("Missing or inapplicable requirement cannot claim support")
        statuses[rid] = status

    if seen != set(r["requirement_ids"]):
        raise AssuranceContractError("Assessment must account for all requirements")

    decision = p["decision"]
    if decision not in {"APPROVE", "RETRIEVE_MORE", "CLARIFY", "ABSTAIN"}:
        raise AssuranceContractError("Invalid decision")
    all_supported = all(v == "supported" for v in statuses.values())
    if decision == "APPROVE":
        if not all_supported or p["lookup"] is not None:
            raise AssuranceContractError("Cannot approve incomplete or conflicted evidence")
    elif decision == "RETRIEVE_MORE":
        if all_supported or r["recovery_used"]:
            raise AssuranceContractError("Lookup disallowed or unnecessary")
        lookup = _object(p["lookup"], {"kind", "query", "target_requirement_ids"}, "lookup")
        if lookup["kind"] != "search":
            raise AssuranceContractError("RV-038 pilot supports search requests only")
        query = lookup["query"]
        if (
            not isinstance(query, str)
            or not query.strip()
            or len(query) > 1024
        ):
            raise AssuranceContractError("Invalid lookup query")
        targets = _unique_ids(lookup["target_requirement_ids"], "target_requirement_id")
        if not targets or any(statuses.get(t) not in {"partial", "missing", "conflicted"} for t in targets):
            raise AssuranceContractError("Lookup must target declared gaps")
    else:
        if p["lookup"] is not None:
            raise AssuranceContractError("Unexpected lookup")
        if decision == "ABSTAIN" and all_supported:
            raise AssuranceContractError("Cannot abstain when every requirement is declared supported")

    return AssuranceResult(json.dumps(p, ensure_ascii=False, sort_keys=True))
