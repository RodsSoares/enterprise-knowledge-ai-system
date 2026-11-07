"""Strict answer contracts; reference integrity is not semantic groundedness.

No model calls, retrieval changes, or automatic sufficiency decisions. Only
empty context forces abstention. Nonempty context may still be insufficient.
"""

from dataclasses import dataclass
import hashlib
import json
import re

from app.retrieval.evidence_context import EvidenceContext, render_context


class AnswerContractError(ValueError):
    """The response cannot be accepted by the structural/reference contract."""


@dataclass(frozen=True, slots=True)
class AnswerClaim:
    text: str
    citation_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StructuredAnswer:
    request_id: str
    status: str
    claims: tuple[AnswerClaim, ...]
    abstention_reason: str | None

    def to_dict(self) -> dict:
        return {"request_id": self.request_id, "status": self.status,
                "claims": [{"text": c.text, "citation_ids": list(c.citation_ids)}
                           for c in self.claims],
                "abstention_reason": self.abstention_reason}


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise AnswerContractError(f"{name} must be a nonempty string.")
    return value


def _keys(value, expected, name):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise AnswerContractError(f"{name} must contain exactly {sorted(expected)}.")


def request_id_for(question: str, context: EvidenceContext) -> str:
    """Bind local E IDs to exact question and canonical evidence contents.

    This digest detects accidental mismatches; it is not authentication and
    does not prevent a provider from echoing it with an unsupported claim.
    """
    _text(question, "question")
    if not isinstance(context, EvidenceContext):
        raise AnswerContractError("context must be EvidenceContext.")
    ids = [p.citation_id for p in context.passages]
    if any(not isinstance(cid, str) or not re.fullmatch(r"E[1-9][0-9]*", cid)
           for cid in ids) or len(ids) != len(set(ids)):
        raise AnswerContractError("Context citation IDs must be unique E identifiers.")
    chunks = [p.chunk.chunk_id for p in context.passages]
    if len(chunks) != len(set(chunks)):
        raise AnswerContractError("Context contains duplicate chunks.")
    if context.text != render_context(context.passages):
        raise AnswerContractError("Context text differs from its source passages.")
    payload = json.dumps({"question": question, "context": context.text},
                         ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_answer(payload: dict, *, question: str,
                    context: EvidenceContext) -> StructuredAnswer:
    """Accept only validated output, not direct dataclass construction.

    Each claim requires unique existing references. This checks reference
    membership, not entailment, completeness, authority, or factual correctness.
    Do not label this result 'grounded' or expose it without later semantic
    evaluation in a production answer pipeline.
    """
    expected_id = request_id_for(question, context)
    _keys(payload, {"request_id", "status", "claims", "abstention_reason"}, "answer")
    if payload["request_id"] != expected_id:
        raise AnswerContractError("Response belongs to a different question/context.")
    status = payload["status"]
    if not isinstance(status, str) or status not in ("answered", "abstained"):
        raise AnswerContractError("status must be answered or abstained.")
    claims = payload["claims"]
    if not isinstance(claims, list):
        raise AnswerContractError("claims must be a JSON array.")
    reason = payload["abstention_reason"]
    if status == "abstained":
        if claims:
            raise AnswerContractError("Abstention cannot contain answer claims.")
        _text(reason, "abstention_reason")
        return StructuredAnswer(expected_id, status, (), reason)
    if not context.passages:
        raise AnswerContractError("Empty context requires abstention.")
    if reason is not None or not claims:
        raise AnswerContractError("An answer requires claims and a null abstention_reason.")
    allowed = context.citations
    validated = []
    for claim in claims:
        _keys(claim, {"text", "citation_ids"}, "claim")
        text = _text(claim["text"], "claim.text")
        refs = claim["citation_ids"]
        if (not isinstance(refs, list) or not refs
                or any(not isinstance(ref, str) or ref not in allowed for ref in refs)):
            raise AnswerContractError("Every claim requires existing citation IDs.")
        if len(refs) != len(set(refs)):
            raise AnswerContractError("A claim cannot repeat a citation ID.")
        validated.append(AnswerClaim(text, tuple(refs)))
    return StructuredAnswer(expected_id, status, tuple(validated), None)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AnswerContractError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value):
    raise AnswerContractError(f"Nonstandard JSON constant: {value}")


def parse_answer(raw: str, *, question: str,
                 context: EvidenceContext) -> StructuredAnswer:
    """Parse exact JSON; reject fences, duplicate keys, NaN and extra prose."""
    _text(raw, "raw response")
    try:
        payload = json.loads(raw, object_pairs_hook=_unique_object,
                             parse_constant=_reject_constant)
    except json.JSONDecodeError as exc:
        raise AnswerContractError("Response must be a single JSON object.") from exc
    return validate_answer(payload, question=question, context=context)
