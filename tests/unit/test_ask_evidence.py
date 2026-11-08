"""CLI preflight, in-memory config overrides and durable result persistence."""
import json
import pytest
from tests.unit.test_evidence_pipeline import inputs, SDK
from app.scripts import ask_evidence as runner


@pytest.fixture
def setup(inputs,tmp_path,monkeypatch):
    snapshot,cache,config,_=inputs
    for name,value in [('snapshot',snapshot),('cache',cache),('config',config)]:
        (tmp_path/f'{name}.json').write_text(json.dumps(value),encoding='utf-8')
    # Physical-source verification belongs to snapshot integration tests. Keep
    # canonical verification active in the pipeline and CLI input validation.
    monkeypatch.setattr(runner,'verify_snapshot',lambda *args,**kwargs:None)
    args=['--snapshot',str(tmp_path/'snapshot.json'),'--embedding-cache',str(tmp_path/'cache.json'),
          '--config',str(tmp_path/'config.json'),'--question','Como compartilhar?',
          '--model','fake','--input-price','2','--output-price','10']
    return args,tmp_path


def test_dry_run_does_not_create_sdk_or_change_inputs(setup):
    args,path=setup;before={p:p.read_bytes() for p in path.glob('*.json')}
    def forbidden(**kwargs):raise AssertionError('No SDK in dry-run')
    assert runner.main([*args,'--output',str(path/'plan.json')],sdk_factory=forbidden)==0
    p=json.loads((path/'plan.json').read_text())
    assert p['status']=='dry_run' and p['expected_calls']=={'normal':4,'maximum':6}
    assert p['config']['budget']['max_calls']==6 and p['config']['generation_output_tokens']==8000
    assert all(p.read_bytes()==data for p,data in before.items())


def test_execute_saves_all_stages_and_usage(setup):
    args,path=setup
    assert runner.main([*args,'--output',str(path/'result.json'),'--execute'],sdk_factory=SDK)==0
    p=json.loads((path/'result.json').read_text())
    assert p['status']=='answered_pending_review' and p['usage']['calls']==4
    assert p['result']['planning']['bundle'] and p['result']['answer']


def test_missing_cache_fails_before_sdk_or_output(setup):
    args,path=setup;(path/'cache.json').unlink()
    with pytest.raises(SystemExit):runner.main([*args,'--output',str(path/'result.json'),'--execute'],sdk_factory=SDK)
    assert not (path/'result.json').exists()


def test_existing_output_is_preserved(setup):
    args,path=setup;p=path/'result.json';p.write_text('keep')
    with pytest.raises(SystemExit):runner.main([*args,'--output',str(p)],sdk_factory=SDK)
    assert p.read_text()=='keep'


def test_budget_failure_persists_plan_and_usage(setup):
    args,path=setup
    assert runner.main([*args,'--output',str(path/'result.json'),'--max-calls','3','--execute'],sdk_factory=SDK)==1
    p=json.loads((path/'result.json').read_text())
    assert p['status']=='budget_exceeded' and p['usage']['calls']==3
    assert p['result']['planning']['bundle'] and p['result']['answer'] is None
