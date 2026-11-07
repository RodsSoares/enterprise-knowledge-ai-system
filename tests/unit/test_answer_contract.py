"""RV-015: structural contract boundaries, not answer quality benchmarks."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest

from app.chunking.schemas import RetrievalChunk
from app.retrieval.candidate_fusion import FusedCandidate
from app.retrieval.evidence_context import EvidenceContextBuilder
from app.generation.answer_contract import (
    AnswerContractError, parse_answer, request_id_for, validate_answer,
)


@pytest.fixture
def context():
    chunk = RetrievalChunk(chunk_id="DOC-X::chunk-1", document_id="DOC-X", order=0,
        text="O prazo de entrega é de cinco dias.", source_block_ids=("b1",),
        source_path=Path("policy.md"), content_types=("text",), page_numbers=(2,))
    candidate = FusedCandidate(chunk, score=0.1, rank=1, retrieval_methods=("vector",))
    return EvidenceContextBuilder().build([candidate], [candidate])


def payload(context, question="Qual o prazo?"):
    return {"request_id": request_id_for(question, context), "status": "answered",
            "claims": [{"text": "O prazo é de cinco dias.", "citation_ids": ["E1"]}],
            "abstention_reason": None}


def test_roundtrip_preserves_claims_and_source_lookup(context):
    value = payload(context)
    before = deepcopy(value)
    result = parse_answer(json.dumps(value), question="Qual o prazo?", context=context)
    assert result.to_dict() == value == before
    assert context.citations[result.claims[0].citation_ids[0]]["page_numbers"] == [2]


@pytest.mark.parametrize("mutation", [
    "missing_field", "extra_field", "wrong_status", "boolean_status", "array_status",
    "claims_string", "empty_claims", "answer_with_reason", "missing_refs", "unknown_ref",
    "duplicate_ref", "numeric_ref", "refs_string", "blank_text", "numeric_text",
    "extra_claim_field", "missing_claim_field", "claim_string", "wrong_request",
])
def test_invalid_response_is_rejected(context, mutation):
    v = payload(context)
    c = v["claims"][0]
    if mutation == "missing_field": del v["status"]
    elif mutation == "extra_field": v["answer"] = "Uncited text"
    elif mutation == "wrong_status": v["status"] = "partial"
    elif mutation == "boolean_status": v["status"] = True
    elif mutation == "array_status": v["status"] = []
    elif mutation == "claims_string": v["claims"] = "claim"
    elif mutation == "empty_claims": v["claims"] = []
    elif mutation == "answer_with_reason": v["abstention_reason"] = "reason"
    elif mutation == "missing_refs": c["citation_ids"] = []
    elif mutation == "unknown_ref": c["citation_ids"] = ["E2"]
    elif mutation == "duplicate_ref": c["citation_ids"] = ["E1", "E1"]
    elif mutation == "numeric_ref": c["citation_ids"] = [1]
    elif mutation == "refs_string": c["citation_ids"] = "E1"
    elif mutation == "blank_text": c["text"] = "  "
    elif mutation == "numeric_text": c["text"] = 5
    elif mutation == "extra_claim_field": c["confidence"] = 1
    elif mutation == "missing_claim_field": del c["text"]
    elif mutation == "claim_string": v["claims"] = ["claim"]
    elif mutation == "wrong_request": v["request_id"] = "other"
    with pytest.raises(AnswerContractError):
        validate_answer(v, question="Qual o prazo?", context=context)


@pytest.mark.parametrize("empty", [False, True])
def test_abstention_allowed_even_with_nonempty_context(context, empty):
    if empty: context = EvidenceContextBuilder().build([], [])
    v = payload(context)
    v.update(status="abstained", claims=[], abstention_reason="Evidência insuficiente.")
    assert validate_answer(v, question="Qual o prazo?", context=context).status == "abstained"


@pytest.mark.parametrize("reason", [None, "", "  ", 1, False])
def test_abstention_requires_reason(context, reason):
    v = payload(context)
    v.update(status="abstained", claims=[], abstention_reason=reason)
    with pytest.raises(AnswerContractError):
        validate_answer(v, question="Qual o prazo?", context=context)


def test_abstention_with_claims_rejected(context):
    v = payload(context)
    v.update(status="abstained", abstention_reason="Insuficiente")
    with pytest.raises(AnswerContractError):
        validate_answer(v, question="Qual o prazo?", context=context)


def test_empty_context_cannot_answer():
    context = EvidenceContextBuilder().build([], [])
    with pytest.raises(AnswerContractError, match="Empty context"):
        validate_answer(payload(context), question="Qual o prazo?", context=context)


@pytest.mark.parametrize("raw", ['{} trailing', '```json\n{}\n```', '[]', 'null',
    '{"status": "answered", "status": "abstained"}', '{"value": NaN}',
    '{"value": Infinity}', '{"claims":[{"text":"a","text":"b"}]}'])
def test_nonconforming_json_rejected(context, raw):
    with pytest.raises(AnswerContractError):
        parse_answer(raw, question="Qual o prazo?", context=context)


def test_other_question_cannot_reuse_response(context):
    with pytest.raises(AnswerContractError):
        validate_answer(payload(context), question="Quem aprova?", context=context)


def test_same_citation_id_in_other_context_is_not_interchangeable(context):
    passage = context.passages[0]
    changed = replace(passage.source, chunk=replace(passage.chunk, text="Prazo de dez dias."))
    other = EvidenceContextBuilder().build([changed], [changed])
    assert set(context.citations) == set(other.citations)
    with pytest.raises(AnswerContractError):
        validate_answer(payload(context), question="Qual o prazo?", context=other)


@pytest.mark.parametrize("change", ["text", "duplicate_id", "invalid_id", "duplicate_chunk"])
def test_inconsistent_context_rejected(context, change):
    passage = context.passages[0]
    if change == "text": bad = replace(context, text="changed")
    elif change == "duplicate_id": bad = replace(context, passages=(passage, passage))
    elif change == "invalid_id": bad = replace(context, passages=(replace(passage, citation_id="X"),))
    else: bad = replace(context, passages=(passage, replace(passage, citation_id="E2")))
    with pytest.raises(AnswerContractError):
        request_id_for("Qual o prazo?", bad)


def test_structural_success_does_not_prove_claim_support(context):
    v = payload(context)
    v["claims"][0]["text"] = "O prazo é de noventa dias."
    # Intentionally passes: semantic contradiction detection is a later layer.
    result = validate_answer(v, question="Qual o prazo?", context=context)
    assert result.claims[0].text == "O prazo é de noventa dias."
