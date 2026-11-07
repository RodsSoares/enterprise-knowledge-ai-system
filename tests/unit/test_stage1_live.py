"""Live adapters exercised with a fake SDK. No network, OCR or paid calls."""
from dataclasses import replace
import json
from pathlib import Path
import shutil
from types import SimpleNamespace as NS

import pytest

from app.chunking.schemas import RetrievalChunk
from app.generation.answer_contract import request_id_for
from app.orchestration.contracts import AssessmentRequest
from app.orchestration.coordinator import BudgetExceeded, Stage1Coordinator
from app.orchestration.live_provider import BudgetedClient, RunBudget, LiveAssessor, LiveGenerator, LiveRetriever
from app.orchestration.snapshot import CorpusSnapshot, prepare_snapshot
from app.scripts.compare_stage1_orchestration import compare_case, load_config, main
from tests.unit.test_stage1_orchestration import assessment


class FakeSDK:
    def __init__(self, response=None):
        self.options=[]
        self.calls=[]
        self.response=response
        self.responses=NS(create=self.create_response)
        self.embeddings=NS(create=self.create_embedding)

    def with_options(self,**kw):
        self.options.append(kw)
        return self

    def create_response(self,**kw):
        self.calls.append(('responses',kw))
        if self.response:
            return self.response()
        data=json.loads(kw['input'][0]['content'])
        if kw['text']['format']['name']=='evidence_assessment':
            payload=assessment(AssessmentRequest(json.dumps(data)))
            for item in payload['passage_decisions']:
                item['supporting_spans']=[dict(text=s['text']) for s in item['supporting_spans']]
            raw=json.dumps(payload)
        else:
            raw=json.dumps(dict(request_id=data['request_id'],status='answered',claims=[dict(
                text='Use approved secure transfer.',citation_ids=['E1'])],abstention_reason=None))
        return NS(status='completed',output=[],output_text=raw,model=kw['model'],id='fake',
            usage=NS(input_tokens=100,output_tokens=50,total_tokens=150))

    def create_embedding(self,**kw):
        self.calls.append(('embeddings',kw))
        count=len(kw['input']) if isinstance(kw['input'],list) else 1
        return NS(data=[NS(index=i,embedding=[1.,0.1]) for i in range(count)],
            usage=NS(prompt_tokens=100),model=kw['model'])


def config():
    # Fake rates for testing only, not real provider prices.
    return dict(models=dict(assessment='fake',generation='fake',embedding='fake-embedding'),
        prices={m:dict(input_per_million='1',output_per_million='2') for m in ('fake','fake-embedding')},
        budget=dict(max_input_tokens=200000,max_output_tokens=20000,max_calls=7,
            deadline_seconds=120,max_cost_usd='10'),assessment_output_tokens=4000,
        generation_output_tokens=2000,as_of='2026-11-07')


@pytest.fixture
def snapshot(tmp_path,monkeypatch):
    registry=Path('data/ground_truth/document_registry.yaml').read_bytes()
    monkeypatch.chdir(tmp_path)
    Path('registry.yaml').write_bytes(registry)
    p=Path('DOC-005_policy.pdf')
    p.write_bytes(b'physical corpus fixture')
    chunk=RetrievalChunk('DOC-005::0','DOC-005',0,'Use approved secure transfer.',
        ('b1',),p,('Controls',),content_types=('text',))
    return prepare_snapshot([p],Path('registry.yaml'),lambda paths:[chunk])


def test_manifest_roundtrip_and_registry_metadata(snapshot):
    restored=CorpusSnapshot(snapshot.serialized).verify()
    assert restored.snapshot_id==snapshot.snapshot_id
    assert restored.metadata['DOC-005']['version']
    assert restored.chunks==snapshot.chunks


def test_manifest_rejects_physical_change(snapshot):
    snapshot.chunks[0].source_path.write_bytes(b'changed')
    with pytest.raises(ValueError,match='changed'):
        snapshot.verify()


def test_manifest_rejects_changed_catalog(snapshot):
    with pytest.raises(ValueError,match='Catalog'):
        snapshot.verify([replace(snapshot.chunks[0],text='changed')])


def test_manifest_detects_change_during_parsing(snapshot):
    def loader(paths):
        paths[0].write_bytes(b'changed during parse')
        return snapshot.chunks
    with pytest.raises(ValueError,match='changed'):
        prepare_snapshot([snapshot.chunks[0].source_path],Path('registry.yaml'),loader)


def test_shared_budget_reservation_and_actual_usage():
    cfg=config(); sdk=FakeSDK(lambda:NS(usage=NS(input_tokens=100,output_tokens=50),id="fake",output_text="{}"))
    c=BudgetedClient(sdk,RunBudget(**cfg['budget']),cfg['prices'])
    c.responses.create(model='fake',input='x',max_output_tokens=100)
    assert c.input_tokens==100 and c.output_tokens==50
    assert c.cost==__import__('decimal').Decimal('0.0002')
    assert sdk.options[0]['max_retries']==0
    assert c.report()['events'][0]['status']=='completed'


@pytest.mark.parametrize('change',[
    dict(max_input_tokens=1),dict(max_output_tokens=1),dict(max_cost_usd='0.000001')])
def test_budget_blocks_before_sdk(change):
    cfg=config(); cfg['budget'].update(change); sdk=FakeSDK()
    c=BudgetedClient(sdk,RunBudget(**cfg['budget']),cfg['prices'])
    with pytest.raises(BudgetExceeded):
        c.responses.create(model='fake',input='x',max_output_tokens=100)
    assert sdk.calls==[]


def test_call_limit_counts_embeddings_and_generation():
    cfg=config();cfg['budget']['max_calls']=1;sdk=FakeSDK()
    c=BudgetedClient(sdk,RunBudget(**cfg['budget']),cfg['prices'])
    c.embeddings.create(model='fake-embedding',input='x')
    with pytest.raises(BudgetExceeded):
        c.responses.create(model='fake',input='x',max_output_tokens=100)
    assert len(sdk.calls)==1


def test_missing_usage_retains_reservation_and_stops():
    sdk=FakeSDK(lambda:NS(usage=None))
    cfg=config();c=BudgetedClient(sdk,RunBudget(**cfg['budget']),cfg['prices'])
    with pytest.raises(Exception):
        c.responses.create(model='fake',input='x',max_output_tokens=100)
    assert c.failed and c.input_tokens>0 and c.output_tokens==100
    with pytest.raises(BudgetExceeded):
        c.responses.create(model='fake',input='x',max_output_tokens=100)
    assert len(sdk.calls)==1


def test_deadline_blocks_before_sdk():
    now=[0];cfg=config();sdk=FakeSDK()
    c=BudgetedClient(sdk,RunBudget(**cfg['budget']),cfg['prices'],clock=lambda:now[0])
    now[0]=121
    with pytest.raises(BudgetExceeded):
        c.responses.create(model='fake',input='x',max_output_tokens=100)
    assert not sdk.calls


def test_usage_above_reservation_stops_next_call():
    cfg=config(); sdk=FakeSDK(lambda:NS(usage=NS(input_tokens=1000000,output_tokens=1),id='x',output_text='{}'))
    c=BudgetedClient(sdk,RunBudget(**cfg['budget']),cfg['prices'])
    with pytest.raises(BudgetExceeded):
        c.responses.create(model='fake',input='x',max_output_tokens=100)
    assert c.failed and c.input_tokens==1000000


def test_compare_pair_reuses_initial_pool_and_records_metadata(snapshot):
    cfg=config(); sdk=FakeSDK()
    result=compare_case(snapshot,dict(id='ORC-001',question='Como compartilhar?'),cfg,RunBudget(**cfg['budget']),sdk,raise_errors=True)
    assert result['baseline']['answer']['status']=='answered'
    assert result['candidate']['status']=='answered'
    trace=result['candidate']['trace']
    request=next(e['request'] for e in trace['events'] if e['stage']=='assessment')
    assert request['passages'][0]['metadata']==snapshot.metadata['DOC-005']
    assert request['passages'][0]['as_of']=='2026-11-07'
    assert trace['snapshot_scope']=='physical_sources_registry_chunks_configuration'
    assert [k for k,kw in sdk.calls].count('embeddings')==2
    assert result['usage']['calls']==5
    assert result['semantic_verdict']=='pending_human_review'
    # Ground-truth fields never reach any API request.
    assert 'forbidden_behaviors' not in json.dumps(sdk.calls)
    assert 'expected_outcome' not in json.dumps(sdk.calls)


def test_compare_failure_still_records_cost(snapshot):
    cfg=config();cfg['budget']['max_calls']=2;sdk=FakeSDK()
    r=compare_case(snapshot,dict(id='x',question='Controles?'),cfg,RunBudget(**cfg['budget']),sdk)
    assert r['error_type']=='BudgetExceeded'
    assert r['usage']['calls']==2


def test_runner_dry_run_and_output_not_overwritten(snapshot):
    Path('snapshot.json').write_text(json.dumps(dict(snapshot_id=snapshot.snapshot_id,snapshot=snapshot.payload)))
    Path('cases.json').write_text(json.dumps(dict(cases=[dict(id='x',question='Controles?',split='development',reference_document_ids=['DOC-005'])])))
    Path('config.json').write_text(json.dumps(config()))
    argv=['run','--source','snapshot.json','--suite','cases.json','--case','x',
        '--config','config.json','--output','result.json']
    assert main(argv)==0
    report=json.loads(Path('result.json').read_text())
    assert report['status']=='dry_run' and 'result' not in report
    before=Path('result.json').read_bytes()
    with pytest.raises(SystemExit):main(argv)
    assert Path('result.json').read_bytes()==before


def test_missing_config_rejected(tmp_path):
    p=tmp_path/'config.json';p.write_text('{}')
    with pytest.raises(ValueError):load_config(p)


def test_reserved_case_fields_not_in_assessment_request(snapshot):
    cfg=config();sdk=FakeSDK()
    result=compare_case(snapshot,dict(id='reserved',question='Pergunta',expected_outcome='secret'),cfg,RunBudget(**cfg['budget']),sdk)
    assert 'secret' not in json.dumps(sdk.calls)


def test_constructor_failure_preserves_original_exception(snapshot,monkeypatch):
    import app.scripts.compare_stage1_orchestration as runner
    def old_constructor(**kwargs):
        raise TypeError("unexpected keyword argument 'snapshot'")
    monkeypatch.setattr(runner,'Stage1Coordinator',old_constructor)
    cfg=config()
    result=compare_case(snapshot,dict(id='x',question='Controles?'),cfg,RunBudget(**cfg['budget']),FakeSDK())
    assert result['baseline']['answer']['status']=='answered'
    assert result['candidate'] is None
    assert result['error_type']=='TypeError'
    assert result['error_stage']=='candidate_initialization'
    with pytest.raises(TypeError,match='snapshot'):
        compare_case(snapshot,dict(id='x',question='Controles?'),cfg,RunBudget(**cfg['budget']),FakeSDK(),raise_errors=True)


def test_quote_offsets_are_computed_without_changing_decisions():
    from app.orchestration.contracts import resolve_assessment_quotes, parse_assessment
    r=AssessmentRequest.create(run_id='r',question='Q',snapshot_id='s',
        passages=[dict(chunk_id='c',text='Ação: café ☕. Controles.')],sections=[])
    p=assessment(r)
    p['passage_decisions'][0]['supporting_spans']=[dict(text='café ☕')]
    normalized=resolve_assessment_quotes(json.dumps(p),r)
    accepted=parse_assessment(normalized,r).payload
    assert accepted['passage_decisions'][0]['supporting_spans']==[dict(text='café ☕',start=6,end=12)]
    assert accepted['decision']==p['decision']


@pytest.mark.parametrize('source,quote',[('abc','fabricated'),('abc abc','abc'),('abc','')])
def test_quotes_must_be_exact_nonempty_and_unique(source,quote):
    from app.orchestration.contracts import resolve_assessment_quotes, AssessmentContractError
    r=AssessmentRequest.create(run_id='r',question='Q',snapshot_id='s',
        passages=[dict(chunk_id='c',text=source)],sections=[])
    p=assessment(r);p['passage_decisions'][0]['supporting_spans']=[dict(text=quote)]
    with pytest.raises(AssessmentContractError):resolve_assessment_quotes(json.dumps(p),r)


def test_quote_resolution_does_not_repair_requirement_mismatch_or_false_sufficiency():
    from app.orchestration.contracts import resolve_assessment_quotes, parse_assessment, AssessmentContractError
    r=AssessmentRequest.create(run_id='r',question='Q',snapshot_id='s',
        passages=[dict(chunk_id='c',text='abc')],sections=[])
    p=assessment(r);p['passage_decisions'][0]['supporting_spans']=[dict(text='abc')]
    p['requirements']=['controls: description']
    normalized=resolve_assessment_quotes(json.dumps(p),r)
    with pytest.raises(AssessmentContractError,match='Unknown requirement'):parse_assessment(normalized,r)
    p['requirements']=['controls'];p['gaps']=['unresolved']
    normalized=resolve_assessment_quotes(json.dumps(p),r)
    with pytest.raises(AssessmentContractError,match='Sufficiency'):parse_assessment(normalized,r)
