"""RV-041 HF2: replan delta freezes original meaning and source identity."""
from dataclasses import dataclass
import json
import pytest

from app.orchestration.v3_planning_contract import validate_v3_plan, V3PlanningContractError
from app.orchestration.v3_replanning_contract import validate_v3_replan, REPLAN_SCHEMA
from app.orchestration.v3_pipeline import run_v3

Q = "Como compartilhar dados?"

@dataclass(frozen=True)
class Unit:
    unit_id: str
    reading_text: str
    document_id: str = "DOC-005"
    status: str = "ready"
    structural_role: str = "paragraph"
    section_path: tuple = ()

U1 = Unit("u1", "External sharing requires an approved secure channel.")
U2 = Unit("u2", "Exceptions require documented approval.")

def item(need="Approved secure channel", *, unit=None, gap=False):
    return dict(need=need, relevance="in_scope", condition=None,
        question_quote="compartilhar", evidence_status="missing" if gap else "supported",
        supports=[] if gap else [{"unit_id": (unit or U1).unit_id, "quote": (unit or U1).reading_text}],
        missing_aspects=["exception approval"] if gap else [])

def prior():
    return validate_v3_plan(json.dumps({"items": [item(), item("Exception approval", gap=True)],
        "action": {"kind": "search", "query": "exception", "gap": "approval"}}),
        question=Q, candidates=(U1,), recovery_used=False)

def delta():
    return {"updates": [
        {"requirement_id":"C1", "evidence_status":"supported", "additional_supports":[], "missing_aspects":[]},
        {"requirement_id":"C2", "evidence_status":"supported", "additional_supports":[{"unit_id":"u2", "quote":U2.reading_text}], "missing_aspects":[]},
        ], "new_items":[], "action":{"kind":"complete"}}

def test_replan_preserves_identity_and_upgrades_gap_without_repeating_source():
    result=validate_v3_replan(json.dumps(delta()), previous_plan=prior(), question=Q, candidates=(U1,U2))
    assert [x["requirement_id"] for x in result.items] == ["C1","C2"]
    assert [x["need"] for x in result.items] == ["Approved secure channel", "Exception approval"]
    assert all(x["evidence_status"]=="supported" for x in result.items)
    assert result.items[0]["supports"][0]["unit_id"]=="u1"
    assert result.items[1]["supports"][0]["unit_id"]=="u2"
    assert result.action=={"kind":"complete"}

def test_missing_update_rejected_not_silently_dropped():
    d=delta(); d['updates'].pop()
    with pytest.raises(V3PlanningContractError, match="every existing"):
        validate_v3_replan(json.dumps(d), previous_plan=prior(), question=Q, candidates=(U1,U2))

def test_extra_unknown_id_rejected():
    d=delta(); d['updates'][1]['requirement_id']='C900'
    with pytest.raises(V3PlanningContractError, match="drop, repeat or forge"):
        validate_v3_replan(json.dumps(d), previous_plan=prior(), question=Q, candidates=(U1,U2))

def test_forged_source_is_rejected():
    d=delta(); d['updates'][1]['additional_supports'][0]['unit_id']='forged'
    with pytest.raises(V3PlanningContractError, match="authorized"):
        validate_v3_replan(json.dumps(d), previous_plan=prior(), question=Q, candidates=(U1,U2))

def test_new_material_requirement_can_be_appended_without_mutating_frozen_ids():
    d=delta();d['new_items']=[item("New material approval step",unit=U2)]
    result=validate_v3_replan(json.dumps(d),previous_plan=prior(),question=Q,candidates=(U1,U2))
    assert [x['requirement_id'] for x in result.items]==['C1','C2','C3']
    assert result.items[2]['need']=='New material approval step'

def test_repeated_authorized_source_is_idempotent_and_frozen():
    d=delta(); d['updates'][0]['additional_supports']=[{'unit_id':'u1','quote':U1.reading_text}]
    result=validate_v3_replan(json.dumps(d),previous_plan=prior(),question=Q,candidates=(U1,U2))
    assert [s['unit_id'] for s in result.items[0]['supports']] == ['u1']

def test_second_lookup_disallowed_even_with_new_gap():
    d=delta(); d['action']={'kind':'search','query':'again','gap':'something'}
    d['updates'][1]['evidence_status']='missing';d['updates'][1]['additional_supports']=[];d['updates'][1]['missing_aspects']=['approval']
    with pytest.raises(V3PlanningContractError):
        validate_v3_replan(json.dumps(d),previous_plan=prior(),question=Q,candidates=(U1,U2))

def test_out_of_scope_original_remains_out_of_scope():
    raw={'items':[item(),{'need':'Unrelated AI tool approval','relevance':'out_of_scope',
         'condition':None,'question_quote':'compartilhar','evidence_status':'excluded',
         'supports':[],'missing_aspects':[]}], 'action':{'kind':'complete'}}
    original=validate_v3_plan(json.dumps(raw),question=Q,candidates=(U1,),recovery_used=False)
    d={'updates':[{'requirement_id':'C1','evidence_status':'supported','additional_supports':[],'missing_aspects':[]}],
       'new_items':[],'action':{'kind':'complete'}}
    result=validate_v3_replan(json.dumps(d),previous_plan=original,question=Q,candidates=(U1,))
    assert result.items[1]==original.items[1]

def test_strict_schema_disallows_extra_model_fields():
    assert REPLAN_SCHEMA['additionalProperties'] is False
    assert REPLAN_SCHEMA['required']==['updates','new_items','action']

class Provider:
    def __init__(self, *, missing_update=False):
        self.calls=[];self.missing_update=missing_update
    def invoke(self,stage,payload):
        self.calls.append((stage,payload))
        if stage=='scope_v3':
            data={'request_kind':'general','focus':'External sharing','known_conditions':[],
                  'exclusions':[],'unknown_conditions':[],'decision':'proceed','clarification':None}
        elif stage=='plan_v3':
            data={'items':[item(),item('Exception approval',gap=True)],
                  'action':{'kind':'search','query':'exception','gap':'approval'}}
        elif stage=='replan_v3':
            data=delta()
            if self.missing_update:data['updates'].pop()
        elif stage=='inventory_v3':
            found='u2' in [u['unit_id'] for u in payload['candidates']]
            data={'facets':[{'description':'Secure channel','supporting_unit_ids':['u1']}]
                 + ([{'description':'Exception approval','supporting_unit_ids':['u2']}] if found else []),
                  'unresolved_facets':[] if found else ['Exception approval']}
        elif stage=='assurance_v3':
            found='u2' in [u['unit_id'] for u in payload['candidates']]
            data={'requirements':[
                  {'requirement_id':'C1','relevance':'applicable','entailment':'supported','supporting_unit_ids':['u1']},
                  {'requirement_id':'C2','relevance':'applicable','entailment':'supported' if found else 'missing',
                   'supporting_unit_ids':['u2'] if found else []}],
                  'inventory_complete':found, 'omitted_facets':[] if found else ['Exception approval'],
                  'decision':'APPROVE' if found else 'RETRIEVE_MORE',
                  'lookup':None if found else {'semantic_query':'exception approval',
                     'lexical_query':'exceptions documented approval','document_ids':['DOC-005'],
                     'target_requirement_ids':['C2']},
                  'reason':'Source checked'}
        elif stage=='generate_v3':
            data={'status':'answered','claims':[
               {'text':'Use an approved channel','requirement_ids':['C1'],'citation_ids':['u1']},
               {'text':'Exceptions require approval','requirement_ids':['C2'],'citation_ids':['u2']}],
               'abstention_reason':None}
        elif stage=='verify_v3':
            data={'claims':[{'claim_index':i,'entailed':True,'relevant':True,
                 'conditions_preserved':True,'verified_citation_ids':[f'u{i+1}']} for i in range(2)],
                 'materially_complete':True,'omissions':[],'decision':'PASS','reason':'Verified'}
        else:raise ValueError(stage)
        return json.dumps(data)

class Retriever:
    def search(self,*args):return (U1,),{}
    def search_projections(self,*args):return (U2,),{}

def test_v3_pipeline_uses_delta_stage_instead_of_second_freeform_plan():
    provider=Provider()
    result=run_v3(Q,snapshot_id='snapshot',units=(U1,U2),retriever=Retriever(),provider=provider)
    assert result['status']=='answered_pending_human_review'
    assert [stage for stage,_ in provider.calls].count('plan_v3') == 1
    assert [stage for stage,_ in provider.calls].count('replan_v3') == 1
    frozen=next(payload for stage,payload in provider.calls if stage=='replan_v3')['previous_requirements']
    assert frozen[0]['need']=='Approved secure channel'
    assert frozen[1]['need']=='Exception approval'

def test_v3_pipeline_rejects_missing_requirement_delta():
    provider=Provider(missing_update=True)
    result=run_v3(Q,snapshot_id='snapshot',units=(U1,U2),retriever=Retriever(),provider=provider)
    assert result['status']=='execution_failed'
    assert result['error_type']=='V3PlanningContractError'
