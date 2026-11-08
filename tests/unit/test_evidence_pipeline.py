"""Integrated flow and one shared ledger using deterministic fake SDK responses."""
from copy import deepcopy
from dataclasses import asdict, replace
import json
from types import SimpleNamespace as NS

import pytest

from app.chunking.evidence_snapshot import document_record, make_snapshot, verify_snapshot
from app.ingestion.schemas import NormalizedContent, TextBlock, SourceLocation
from app.retrieval.evidence_unit_retriever import make_cache
from app.orchestration.live_provider import RunBudget
from app.orchestration.evidence_pipeline import run_pipeline


@pytest.fixture
def inputs():
    content=NormalizedContent((TextBlock('a',0,'paragraph','Use a secure channel.',
        SourceLocation(section_path=('Sharing',))),TextBlock('b',1,'paragraph','Document exceptions.',
        SourceLocation(section_path=('Exceptions',)))))
    snapshot=make_snapshot([document_record(content,document_id='DOC-005',title='Sharing',
        source_path='policy.md',source_revision='a'*64)])
    units=verify_snapshot(snapshot)
    cache=make_cache(units,'embed',[[1.,0.] for u in units if u.searchable])
    budget=RunBudget(400000,1000,6,240,'1')
    config=dict(models=dict(assessment='fake',generation='fake',embedding='embed'),
        prices={m:dict(input_per_million='2',output_per_million='10') for m in ('fake','embed')},
        budget=asdict(budget),assessment_output_tokens=100,generation_output_tokens=100,as_of='2026-11-06')
    return snapshot,cache,config,budget


class SDK:
    def __init__(self,mode='answer',**kwargs):
        self.mode=mode; self.calls=[]; self.plans=0
        self.responses=NS(create=self.response); self.embeddings=NS(create=self.embedding)
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def with_options(self,**kwargs):
        assert kwargs['max_retries']==0
        return self
    def embedding(self,**kwargs):
        self.calls.append(('embedding',kwargs['input']))
        # Only query embeddings; document cache is never regenerated.
        assert isinstance(kwargs['input'],str)
        return NS(data=[NS(index=0,embedding=[1.,0.])],usage=NS(prompt_tokens=10),id='emb',model='embed')
    def response(self,**kwargs):
        stage=kwargs['text']['format']['name']; self.calls.append((stage,kwargs))
        payload=json.loads(kwargs['input'][0]['content'])
        if stage=='evidence_scope':
            assert set(payload)=={'question'}
            answer=dict(request_kind='general',focus='sharing',known_conditions=[],exclusions=[],
                unknown_conditions=[],decision='clarify' if self.mode=='clarify' else 'proceed',
                clarification='Qual operação?' if self.mode=='clarify' else None)
        elif stage=='evidence_plan':
            self.plans+=1
            action={'kind':'complete'}
            if self.mode=='plan_abstain': action={'kind':'abstain','reason':'Evidence is insufficient.'}
            if self.mode in ('search','search_again') and (self.plans==1 or self.mode=='search_again'):
                action={'kind':'search','query':'Additional sharing rules','gap':'Need more evidence'}
            answer=dict(items=[dict(need=u['reading_text'],use='category',condition='Dados confidenciais',
                scope_link=dict(question_quote=payload['question'],explanation='Sharing condition'),
                supports=[dict(unit_id=u['unit_id'],quote=u['reading_text'])]) for u in payload['candidates']],
                action=action)
        else:
            assert stage=='evidence_answer'
            if self.mode=='generation_error': raise RuntimeError('Provider error')
            claims=[dict(text='Controle da fonte.',coverage_id=i['coverage_id'],
                citation_ids=[e['citation_id'] for e in payload['bundle']['evidence']
                              if e['unit_id']==i['supports'][0]['unit_id']]) for i in payload['bundle']['coverage']]
            answer=dict(request_id=payload['request_id'],status='answered',claims=claims,abstention_reason=None)
            if self.mode=='generation_abstain':
                answer.update(status='abstained',claims=[],abstention_reason='Insufficient evidence.')
            if self.mode=='bad_citation': answer['claims'][0]['citation_ids']=['E999']
        return NS(status='completed',output_text=json.dumps(answer),output=[],id='response',
                  model='fake',usage=NS(input_tokens=100,output_tokens=100))


def run(inputs,sdk,question='Como compartilhar?',budget=None,checkpoint=lambda x:None):
    snapshot,cache,config,original=inputs
    return run_pipeline(snapshot,cache,question,config,budget or original,sdk,checkpoint=checkpoint)


def test_end_to_end_shares_four_call_ledger_and_preserves_binding(inputs):
    sdk=SDK(); checkpoints=[]
    result=run(inputs,sdk,checkpoint=lambda x:checkpoints.append(deepcopy(x)))
    assert result['status']=='answered_pending_review'
    assert [c[0] for c in sdk.calls]==['evidence_scope','embedding','evidence_plan','evidence_answer']
    assert result['usage']['calls']==4 and result['usage']['input_tokens']==310
    assert result['usage']['output_tokens']==300
    assert result['generation_request']['bundle']==result['planning']['bundle']
    assert result['semantic_review']=='not_performed' and 'Condição:' in result['rendered_answer']
    assert checkpoints[-1]['status']==result['status']
    assert any(c['planning'] and c['generation_request'] is None for c in checkpoints)


@pytest.mark.parametrize('mode,status,calls',[
    ('clarify','clarification_required',1),('plan_abstain','abstained',3),
    ('generation_abstain','abstained',4),('generation_error','execution_failed',4),
    ('bad_citation','execution_failed',4)])
def test_exit_paths_do_not_retry_or_force_answers(inputs,mode,status,calls):
    sdk=SDK(mode);r=run(inputs,sdk)
    assert r['status']==status and len(sdk.calls)==r['usage']['calls']==calls
    if mode in ('clarify','plan_abstain'):
        assert r['generation_request'] is None and r['answer'] is None
    if mode in ('generation_error','bad_citation'):
        assert r['answer'] is None and r['planning']['bundle']


def test_unknown_document_ends_after_scope(inputs):
    sdk=SDK();r=run(inputs,sdk,question='Segundo DOC-999?')
    assert r['status']=='abstained' and len(sdk.calls)==1


@pytest.mark.parametrize('field,value',[('max_calls',3),('max_output_tokens',250),('max_cost_usd','0.032')])
def test_cumulative_budget_blocks_generation_without_reset(inputs,field,value):
    inputs=deepcopy(inputs)
    if field=='max_cost_usd': inputs[2]['generation_output_tokens']=300
    sdk=SDK();budget=replace(inputs[3],**{field:value});r=run(inputs,sdk,budget=budget)
    assert r['status']=='budget_exceeded'
    assert not any(c[0]=='evidence_answer' for c in sdk.calls)
    assert r['usage']['calls']==len(sdk.calls)==3


def test_single_complement_includes_generation_in_same_budget(inputs):
    sdk=SDK('search');r=run(inputs,sdk)
    assert r['status']=='answered_pending_review' and r['usage']['calls']==6
    assert sdk.plans==2
    assert r['planning']['trace'][-2]['stage']=='plan'


def test_second_lookup_is_not_executed(inputs):
    sdk=SDK('search_again');r=run(inputs,sdk)
    assert r['status']=='abstained' and r['usage']['calls']==5
    assert r['generation_request'] is None


def test_invalid_cache_never_calls_sdk(inputs):
    snapshot,cache,config,budget=deepcopy(inputs);cache['cache']['vectors'][0][0]=2
    sdk=SDK()
    with pytest.raises(ValueError):run_pipeline(snapshot,cache,'Como compartilhar?',config,budget,sdk)
    assert not sdk.calls
