"""One-call execution, budget, dry-run and durable failure ledger with a fake SDK."""
import json
from types import SimpleNamespace as NS
import pytest

from tests.unit.test_evidence_answer import inputs, answer_for
from app.scripts import generate_evidence_answer as runner


@pytest.fixture
def setup(inputs, tmp_path):
    saved, snapshot = inputs
    for name, value in [('source',saved), ('snapshot',snapshot)]:
        (tmp_path/f'{name}.json').write_text(json.dumps(value), encoding='utf-8')
    args = ['--source',str(tmp_path/'source.json'),'--snapshot',str(tmp_path/'snapshot.json'),
        '--model','fake','--input-price','2','--output-price','10']
    calls=[]
    class SDK:
        fail = False
        malformed = False
        def __init__(self, **kwargs): self.responses=NS(create=self.response)
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def with_options(self,**kwargs):
            assert kwargs['max_retries']==0
            return self
        def response(self, **kwargs):
            calls.append(kwargs)
            if self.fail: raise RuntimeError('network error')
            request=json.loads(kwargs['input'][0]['content'])
            return NS(status='completed',output_text='{}' if self.malformed else json.dumps(answer_for(request)),
                output=[],id='test',model='fake',usage=NS(input_tokens=100,output_tokens=100))
    return args,tmp_path,SDK,calls


def test_dry_run_never_creates_sdk(setup):
    args,path,_,calls=setup
    def forbidden(**kwargs): raise AssertionError('SDK must not be created')
    assert runner.main([*args,'--output',str(path/'plan.json')],sdk_factory=forbidden)==0
    report=json.loads((path/'plan.json').read_text())
    assert report['status']=='dry_run' and report['expected_calls']==1 and not calls


def test_execute_one_generation_and_preserve_inputs(setup):
    args,path,sdk,calls=setup
    before=(path/'source.json').read_bytes()
    assert runner.main([*args,'--output',str(path/'result.json'),'--execute'],sdk_factory=sdk)==0
    report=json.loads((path/'result.json').read_text())
    assert report['status']=='answered_pending_review' and report['semantic_review']=='not_performed'
    assert report['usage']['calls']==1 and len(calls)==1
    assert report['answer'] and report['rendered_answer']
    assert (path/'source.json').read_bytes()==before


@pytest.mark.parametrize('mode',['fail','malformed'])
def test_failure_preserves_ledger_without_retry(setup, mode):
    args,path,sdk,calls=setup
    setattr(sdk,mode,True)
    assert runner.main([*args,'--output',str(path/'result.json'),'--execute'],sdk_factory=sdk)==1
    report=json.loads((path/'result.json').read_text())
    assert report['status']=='execution_failed' and report['answer'] is None
    assert report['usage']['calls']==1 and len(calls)==1


def test_budget_rejected_in_dry_run_before_call(setup):
    args,path,sdk,calls=setup
    with pytest.raises(SystemExit):
        runner.main([*args,'--output',str(path/'result.json'),'--max-cost-usd','0.00001'],sdk_factory=sdk)
    assert not calls and not (path/'result.json').exists()


def test_existing_output_not_overwritten(setup):
    args,path,sdk,calls=setup
    output=path/'result.json';output.write_text('preserve')
    with pytest.raises(SystemExit):
        runner.main([*args,'--output',str(output),'--execute'],sdk_factory=sdk)
    assert output.read_text()=='preserve' and not calls
