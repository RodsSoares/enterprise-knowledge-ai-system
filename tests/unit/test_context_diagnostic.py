"""Validate the paired experiment, without testing LLM quality or calling APIs."""
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from app.chunking.schemas import RetrievalChunk
from app.generation.answer_contract import request_id_for
from app.scripts.compare_evidence_contexts import MINIMUM,make_context,prepare_cases,execute_cases


def inputs():
    ids=list(dict.fromkeys(cid for pair in MINIMUM.values() for cid in pair))
    chunks=tuple(RetrievalChunk(cid,cid.split('::')[0],i,'Evidence '+cid,('block',),
        Path('source.md'),content_types=('text',)) for i,cid in enumerate(ids))
    snapshot=NS(chunks=chunks,snapshot_id='snapshot')
    context=make_context([c for c in chunks if c.document_id!='DOC-012'])
    answer=dict(request_id=request_id_for('Question',context),status='abstained',claims=[],abstention_reason='fixture')
    saved=dict(snapshot_id='snapshot',question='Question',result=dict(baseline=dict(
        context=dict(text=context.text),answer=answer)))
    suite=dict(cases=[dict(id=cid,split='development',question='Question '+cid,
        expected_outcome='DO NOT SEND') for cid in MINIMUM])
    return snapshot,saved,suite


def test_all_pairs_have_minimal_subset_and_identical_shared_text():
    cases=prepare_cases(*inputs())
    assert len(cases)==4
    for c in cases:
        a,b=c['contexts']['minimal'],c['contexts']['broad']
        assert len(a.passages)==2
        assert set(p.chunk for p in a.passages)<=set(p.chunk for p in b.passages)
    assert any(p.chunk.document_id=='DOC-012' for p in cases[2]['contexts']['broad'].passages)


@pytest.mark.parametrize('mutation', ['snapshot','text','reserved'])
def test_invalid_evidence_or_reserved_case_rejected(mutation):
    snapshot,saved,suite=inputs()
    if mutation=='snapshot':saved['snapshot_id']='different'
    if mutation=='text':
        p=json.loads(saved['result']['baseline']['context']['text']);p['evidence'][0]['text']='tampered'
        saved['result']['baseline']['context']['text']=json.dumps(p)
    if mutation=='reserved':suite['cases'][0]['split']='reserved'
    with pytest.raises(ValueError):prepare_cases(snapshot,saved,suite)


def test_eight_calls_share_provider_and_never_receive_reference_answers():
    calls=[]; checkpoints=[]
    class Generator:
        def generate(self,q,c):
            calls.append((q,c))
            from app.generation.openai_answer_provider import GenerationResult
            return GenerationResult(json.dumps(dict(request_id=request_id_for(q,c),status='answered',
                claims=[dict(text='supported fixture',citation_ids=['E1'])],abstention_reason=None)),
                'fake',None,{})
    result=execute_cases(prepare_cases(*inputs()),Generator(),lambda rows:checkpoints.append(len(rows)))
    assert len(calls)==len(result)==8
    assert [r['arm'] for r in result]==['minimal','broad','broad','minimal','minimal','broad','broad','minimal']
    assert all(r['semantic_verdict']=='pending_human_review' for r in result)
    assert all('DO NOT SEND' not in q+c.text for q,c in calls)


def test_failure_stops_and_preserves_partial_results():
    saved=[]
    class Broken:
        def generate(self,q,c):raise TimeoutError('not exported')
    with pytest.raises(TimeoutError):
        execute_cases(prepare_cases(*inputs()),Broken(),lambda rows:saved.append(json.loads(json.dumps(rows))))
    assert len(saved[-1])==1 and saved[-1][0]['error_type']=='TimeoutError'
