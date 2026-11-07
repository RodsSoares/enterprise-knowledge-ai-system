"""Stage-one assessment boundary. Structural validity is not semantic truth."""
from dataclasses import dataclass
import hashlib
import json


class AssessmentContractError(ValueError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def keys(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected.split()):
        raise AssessmentContractError(f"Expected fields: {expected}")


def text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 4000:
        raise AssessmentContractError("Expected nonempty text up to 4000 characters")
    return value


def strings(value, *, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        raise AssessmentContractError("Expected array")
    for item in value:
        text(item)
    if len(value) != len(set(value)):
        raise AssessmentContractError("Duplicate entries")
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AssessmentContractError("Duplicate JSON field")
        result[key] = value
    return result


def reject_constant(value):
    raise AssessmentContractError("Nonstandard JSON constant")


@dataclass(frozen=True)
class AssessmentRequest:
    # Immutable serialized boundary: provider cannot mutate trusted evidence.
    serialized: str

    @property
    def payload(self):
        return json.loads(self.serialized)

    @classmethod
    def create(cls, *, run_id, question, snapshot_id, passages, sections):
        payload = dict(schema_version="1.0", run_id=run_id, question=question,
            question_hash=digest(question), snapshot_id=snapshot_id,
            passages=passages, section_catalog=sections)
        payload["evidence_set_hash"] = digest(dict(passages=passages, sections=sections))
        return cls(json.dumps(payload, ensure_ascii=False, allow_nan=False))


@dataclass(frozen=True)
class AssessmentResult:
    serialized: str

    @property
    def payload(self):
        return json.loads(self.serialized)


def parse_assessment(raw: str, request: AssessmentRequest) -> AssessmentResult:
    if not isinstance(raw, str) or len(raw) > 100000:
        raise AssessmentContractError("Invalid or oversized response")
    try:
        p = json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)
    except (ValueError, RecursionError) as exc:
        raise AssessmentContractError("Invalid assessment JSON") from exc
    keys(p, "schema_version run_id question_hash snapshot_id evidence_set_hash scope requirements passage_decisions gaps decision lookup clarification reason")
    r = request.payload
    for field in ("schema_version", "run_id", "question_hash", "snapshot_id", "evidence_set_hash"):
        if p[field] != r[field]:
            raise AssessmentContractError(f"Mismatched {field}")
    scope = p["scope"]
    keys(scope, "action sender recipient subject known_conditions unknown_conditions")
    for field in ("action", "sender", "recipient", "subject"):
        if scope[field] is not None:
            text(scope[field])
    strings(scope["unknown_conditions"])
    passages = {c["chunk_id"]: c for c in r["passages"]}
    if not isinstance(scope["known_conditions"], list):
        raise AssessmentContractError("Conditions must be an array")
    for condition in scope["known_conditions"]:
        keys(condition, "text source")
        text(condition["text"])
        if condition["source"] != "question" and condition["source"] not in passages:
            raise AssessmentContractError("Unknown condition origin")
    requirements = strings(p["requirements"], nonempty=True)
    gaps = strings(p["gaps"])
    if not isinstance(p["passage_decisions"], list):
        raise AssessmentContractError("Expected passage decisions")
    seen, covered, selected = set(), set(), 0
    for item in p["passage_decisions"]:
        keys(item, "chunk_id applicability requirement_ids supporting_spans condition reason")
        cid = text(item["chunk_id"])
        if cid not in passages or cid in seen:
            raise AssessmentContractError("Unknown or repeated chunk")
        seen.add(cid)
        mode = item["applicability"]
        if mode not in ("direct", "conditional", "background", "irrelevant"):
            raise AssessmentContractError("Unknown applicability")
        refs = strings(item["requirement_ids"])
        if not set(refs) <= set(requirements):
            raise AssessmentContractError("Unknown requirement")
        text(item["reason"])
        if mode == "conditional":
            text(item["condition"])
        elif item["condition"] is not None:
            raise AssessmentContractError("Condition belongs only to conditional evidence")
        spans = item["supporting_spans"]
        if not isinstance(spans, list):
            raise AssessmentContractError("Expected spans")
        for span in spans:
            keys(span, "start end text")
            a, b = span["start"], span["end"]
            original = passages[cid]["text"]
            if (type(a) is not int or type(b) is not int or not 0 <= a < b <= len(original)
                    or span["text"] != original[a:b]):
                raise AssessmentContractError("Invalid canonical span")
        if mode in ("direct", "conditional"):
            if not spans or not refs:
                raise AssessmentContractError("Applicable evidence requires support and requirements")
            covered.update(refs)
            selected += 1
    if seen != set(passages):
        raise AssessmentContractError("Every presented chunk needs a decision")
    decision = p["decision"]
    if decision not in ("sufficient", "retrieve", "clarify", "abstain"):
        raise AssessmentContractError("Unknown decision")
    text(p["reason"])
    if decision == "sufficient" and (gaps or not selected or covered != set(requirements)):
        raise AssessmentContractError("Sufficiency requires declared complete coverage")
    if decision == "clarify":
        text(p["clarification"])
    elif p["clarification"] is not None:
        raise AssessmentContractError("Unexpected clarification")
    if decision == "retrieve":
        lookup = p["lookup"]
        keys(lookup, "kind query document_id section_ids gap_ids")
        requested_gaps = strings(lookup["gap_ids"], nonempty=True)
        if not set(requested_gaps) <= set(gaps):
            raise AssessmentContractError("Lookup must address declared gaps")
        if lookup["kind"] == "search":
            text(lookup["query"])
            if lookup["document_id"] is not None or lookup["section_ids"] != []:
                raise AssessmentContractError("Search cannot request sections")
        elif lookup["kind"] == "expand_document_section":
            doc = text(lookup["document_id"])
            ids = strings(lookup["section_ids"], nonempty=True)
            allowed = {(s["document_id"], s["section_id"]) for s in r["section_catalog"]}
            if lookup["query"] is not None or any((doc, sid) not in allowed for sid in ids):
                raise AssessmentContractError("Invalid section expansion")
        else:
            raise AssessmentContractError("Unsupported lookup")
    elif p["lookup"] is not None:
        raise AssessmentContractError("Unexpected lookup")
    return AssessmentResult(json.dumps(p, ensure_ascii=False, allow_nan=False))


def resolve_assessment_quotes(raw: str, request: AssessmentRequest) -> str:
    """Provider sends exact quotes; code computes offsets, without fuzzy matching.

    Only span coordinates are derived. IDs, relevance, coverage and sufficiency
    remain untouched and must pass parse_assessment. Repeated quotes are rejected.
    """
    if not isinstance(raw, str) or len(raw) > 100000:
        raise AssessmentContractError("Invalid or oversized response")
    try:
        payload = json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)
    except (ValueError, RecursionError) as exc:
        raise AssessmentContractError("Invalid assessment JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("passage_decisions"), list):
        raise AssessmentContractError("Expected passage decisions")
    passages = {p["chunk_id"]: p["text"] for p in request.payload["passages"]}
    for item in payload["passage_decisions"]:
        if not isinstance(item, dict) or not isinstance(item.get("chunk_id"), str):
            raise AssessmentContractError("Invalid passage decision")
        original = passages.get(item["chunk_id"])
        if original is None:
            raise AssessmentContractError("Unknown quoted chunk")
        if not isinstance(item.get("supporting_spans"), list):
            raise AssessmentContractError("Expected quoted spans")
        for span in item["supporting_spans"]:
            keys(span, "text")
            quote = span["text"]
            if not isinstance(quote, str) or not quote:
                raise AssessmentContractError("Expected nonempty exact quote")
            start = original.find(quote)
            if start < 0 or original.find(quote, start + 1) >= 0:
                raise AssessmentContractError("Quote absent or ambiguous in canonical chunk")
            span.update(start=start, end=start+len(quote))
    return json.dumps(payload, ensure_ascii=False, allow_nan=False)
