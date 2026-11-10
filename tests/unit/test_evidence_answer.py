"""Canonical binding and answer references; these tests do not measure LLM quality."""
from copy import deepcopy
from dataclasses import asdict
import json
from types import SimpleNamespace as NS

import pytest

from app.chunking.evidence_snapshot import document_record, make_snapshot, verify_snapshot
from app.ingestion.schemas import NormalizedContent, TextBlock, SourceLocation
from app.orchestration.evidence_planner import (
    PlannerLimits, PLAN_CONTRACT_VERSION, validate_scope, validate_plan, make_bundle, planning_payload,
)
from app.generation.evidence_answer import (
    prepare_generation, validate_answer, render_answer, generate_answer, generation_kwargs,
)
from app.generation.openai_answer_provider import GenerationError


@pytest.fixture
def inputs():
    content = NormalizedContent((
        TextBlock("a", 0, "paragraph", "Confidential data requires a secure channel.",
                  SourceLocation(section_path=("Channel",))),
        TextBlock("b", 1, "paragraph", "Exceptions require documented approval.",
                  SourceLocation(section_path=("Exceptions",))),))
    snapshot = make_snapshot([document_record(content, document_id="DOC-005", title="Sharing",
        source_path="policy.md", source_revision="a"*64)])
    units = verify_snapshot(snapshot)
    question = "Como compartilhar?"
    scope = validate_scope(json.dumps(dict(request_kind="general", focus="sharing",
        known_conditions=[], exclusions=[], unknown_conditions=[], decision="proceed",
        clarification=None)), question)
    raw = dict(items=[dict(need=u.reading_text, use="category", condition=condition,
        scope_link=dict(question_quote="compartilhar", explanation="Sharing control"),
        supports=[dict(unit_id=u.unit_id, quote=u.reading_text)])
        for u, condition in zip(units, ("Dados confidenciais", "Quando houver exceção"))],
        action=dict(kind="complete"))
    plan = validate_plan(json.dumps(raw), units, set(), question=question)
    bundle = make_bundle(snapshot['snapshot_id'], question, scope, plan, units, max_chars=16000)
    payload = planning_payload(question, scope, units, units, {"DOC-005": {"as_of":"2026-11-07"}})
    result = dict(status="planned_pending_review", contract_version=PLAN_CONTRACT_VERSION,
        snapshot_id=snapshot['snapshot_id'], question=question, scope=scope, bundle=bundle,
        trace=[dict(stage="plan_request", payload=payload), dict(stage="plan", result=plan)])
    saved = dict(status=result['status'], contract_version=PLAN_CONTRACT_VERSION,
        result=result, snapshot_id=snapshot['snapshot_id'], question=question,
        limits=asdict(PlannerLimits()), config={"as_of":"2026-11-07"})
    return saved, snapshot


def answer_for(request):
    return dict(request_id=request['request_id'], status="answered", abstention_reason=None,
        claims=[dict(text="Controle da fonte.", coverage_id=i['coverage_id'],
                     citation_ids=[e['citation_id'] for e in request['bundle']['evidence']
                        if e['unit_id'] == i['supports'][0]['unit_id']])
                for i in request['bundle']['coverage']])


def test_valid_source_binds_and_renders_conditions_and_sources(inputs):
    request = prepare_generation(*inputs)
    value = validate_answer(json.dumps(answer_for(request)), request)
    rendered = render_answer(value, request)
    assert "Condição: Dados confidenciais" in rendered
    assert "Condição: Quando houver exceção" in rendered
    assert "DOC-005" in rendered and "Exceptions require" in rendered


@pytest.mark.parametrize('target', ['question','scope','candidate','plan','bundle','status','snapshot'])
def test_tampered_sources_fail_before_generation(inputs, target):
    saved, snapshot = deepcopy(inputs)
    if target == 'question': saved['result']['question'] += ' outra'
    if target == 'scope': saved['result']['scope']['focus'] = 'AI'
    if target == 'candidate': saved['result']['trace'][0]['payload']['candidates'][0]['reading_text'] = 'invented'
    if target == 'plan': saved['result']['trace'][1]['result']['items'][0]['supports'][0]['source_span']['start'] += 1
    if target == 'bundle': saved['result']['bundle']['evidence'][0]['reading_text'] = 'invented'
    if target == 'status': saved['status'] = 'abstained'
    if target == 'snapshot': snapshot['snapshot']['documents'][0]['units'][0]['reading_text'] = 'invented'
    with pytest.raises(ValueError): prepare_generation(saved, snapshot)


def test_last_completed_plan_after_complement_is_used(inputs):
    saved, snapshot = deepcopy(inputs)
    trace = saved['result']['trace']
    initial = deepcopy(trace)
    initial[1]['result']['action'] = {'kind':'search', 'query':'exception', 'gap':'missing'}
    trace[0]['payload']['complement_used'] = True
    saved['result']['trace'] = initial + trace
    assert prepare_generation(saved, snapshot)['bundle'] == inputs[0]['result']['bundle']


@pytest.mark.parametrize('change', ['wrong_request','wrong_coverage','wrong_source','missing_item','duplicate_ref','empty','extra_field'])
def test_invalid_claim_bindings_rejected(inputs, change):
    request = prepare_generation(*inputs); answer = answer_for(request)
    if change == 'wrong_request': answer['request_id'] = 'other'
    if change == 'wrong_coverage': answer['claims'][0]['coverage_id'] = 'C99'
    if change == 'wrong_source': answer['claims'][0]['citation_ids'] = answer['claims'][1]['citation_ids']
    if change == 'missing_item': answer['claims'].pop()
    if change == 'duplicate_ref': answer['claims'][0]['citation_ids'] *= 2
    if change == 'empty': answer['claims'][0]['text'] = ' '
    if change == 'extra_field': answer['claims'][0]['condition'] = None
    with pytest.raises(ValueError): validate_answer(json.dumps(answer), request)


def test_abstention_does_not_require_forced_coverage(inputs):
    request = prepare_generation(*inputs)
    answer = dict(request_id=request['request_id'], status='abstained', claims=[],
                  abstention_reason='O plano contradiz a fonte.')
    assert render_answer(answer, request).startswith('Abstenção:')
    answer['claims'] = answer_for(request)['claims']
    with pytest.raises(ValueError): validate_answer(json.dumps(answer), request)


def test_contract_does_not_claim_semantic_entailment(inputs):
    request = prepare_generation(*inputs); answer = answer_for(request)
    answer['claims'][0]['text'] = 'Pode enviar sem nenhum controle.'
    # Valid links cannot prove the claim true; it must remain pending semantic review.
    assert validate_answer(json.dumps(answer), request) == answer


def test_modified_prepared_request_is_rejected(inputs):
    request = prepare_generation(*inputs); request['question'] += '?'
    with pytest.raises(ValueError, match='binding'): generation_kwargs(request, 'fake', 100)


@pytest.mark.parametrize('state', ['incomplete','refusal','empty'])
def test_provider_failure_is_not_abstention(inputs, state):
    request = prepare_generation(*inputs)
    response = NS(status='incomplete' if state=='incomplete' else 'completed',
        output_text='' if state=='empty' else json.dumps(answer_for(request)),
        output=[NS(content=[NS(type='refusal')])] if state=='refusal' else [])
    client = NS(responses=NS(create=lambda **kw: response))
    with pytest.raises(GenerationError): generate_answer(client, request, 'fake', 100)


def test_duplicate_json_keys_rejected(inputs):
    request = prepare_generation(*inputs)
    with pytest.raises(ValueError): validate_answer('{"status":"answered","status":"abstained"}', request)


def test_compact_terminal_comparison_uses_saved_request_metadata(inputs):
    saved, snapshot = inputs
    compact = {k:saved[k] for k in ('status','snapshot_id','result')}
    compact['experiment'] = 'terminal_model_comparison'
    assert prepare_generation(compact, snapshot) == prepare_generation(saved, snapshot)
    compact['result']['trace'][0]['payload']['candidates'][0]['metadata']['as_of']='invalid'
    with pytest.raises(ValueError): prepare_generation(compact, snapshot)


def test_generation_instructions_preserve_coverage_boundaries(inputs):
    from app.generation.evidence_answer import INSTRUCTIONS

    request = prepare_generation(*inputs)
    kwargs = generation_kwargs(request, "fake", 100)

    assert kwargs["instructions"] == INSTRUCTIONS
    assert "Each claim must contain only statements" in INSTRUCTIONS
    assert "Do not cite evidence assigned exclusively" in INSTRUCTIONS
    assert "Preserve all material requirements" in INSTRUCTIONS

    answer = answer_for(request)
    assert validate_answer(json.dumps(answer), request) == answer

    answer["claims"][0]["citation_ids"] = (
        answer["claims"][1]["citation_ids"]
    )
    with pytest.raises(
        ValueError, match="Citations must support"
    ):
        validate_answer(json.dumps(answer), request)
