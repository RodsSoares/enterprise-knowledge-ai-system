"""HF3 regression: duplicate source references remain authorized and idempotent.

Covers the exact class of model output observed in the paid HF2 replay, without
weakening document scope, quote matching or frozen requirement semantics.
"""
import json
import pytest
from app.orchestration.v3_replanning_contract import validate_v3_replan
from app.orchestration.v3_planning_contract import V3PlanningContractError
from test_rv041_hf2_replan import prior, delta, U1, U2, Q


def replay(d, candidates=(U1,U2)):
    return validate_v3_replan(json.dumps(d), previous_plan=prior(), question=Q, candidates=candidates)


def test_same_authorized_source_repeated_is_noop():
    d=delta()
    d['updates'][0]['additional_supports']=[{'unit_id':'u1','quote':U1.reading_text}]
    result=replay(d)
    assert [s['unit_id'] for s in result.items[0]['supports']] == ['u1']
    assert result.items[0]['need']=='Approved secure channel'


def test_repeated_authorized_source_cannot_inject_new_quote():
    d=delta()
    d['updates'][0]['additional_supports']=[{'unit_id':'u1','quote':'I am not in the document'}]
    with pytest.raises(V3PlanningContractError, match='Quote must match'):
        replay(d)


def test_new_source_still_authorized_and_recorded():
    d=delta()
    d['updates'][0]['additional_supports']=[{'unit_id':'u2','quote':U2.reading_text}]
    result=replay(d)
    assert {s['unit_id'] for s in result.items[0]['supports']}=={'u1','u2'}


def test_unknown_repeated_source_cannot_be_smuggled():
    d=delta()
    d['updates'][0]['additional_supports']=[{'unit_id':'foreign','quote':U1.reading_text}]
    with pytest.raises(V3PlanningContractError, match='authorized'):
        replay(d)


def test_duplicate_proposed_source_id_rejected():
    d=delta()
    d['updates'][0]['additional_supports']=[
        {'unit_id':'u1','quote':U1.reading_text},
        {'unit_id':'u1','quote':U1.reading_text},
    ]
    with pytest.raises(V3PlanningContractError, match='Repeated additional'):
        replay(d)


def test_status_and_original_supports_stay_frozen_on_dedup():
    d=delta()
    d['updates'][0]['additional_supports']=[{'unit_id':'u1','quote':U1.reading_text}]
    d['updates'][0]['evidence_status']='partial'
    d['updates'][0]['missing_aspects']=['Unresolved approval specifics']
    d['action']={'kind':'clarify','question':'What approval details apply?'}
    result=replay(d)
    assert result.has_known_gap
    assert result.items[0]['supports'][0]['unit_id']=='u1'
    assert result.items[0]['evidence_status']=='partial'


def test_no_completed_plan_when_material_gap_remains():
    d=delta()
    d['updates'][0]['additional_supports']=[{'unit_id':'u1','quote':U1.reading_text}]
    d['updates'][0]['evidence_status']='partial'
    d['updates'][0]['missing_aspects']=['Unresolved approval specifics']
    with pytest.raises(V3PlanningContractError, match='Cannot declare complete'):
        replay(d)


def test_repeated_unit_from_nonready_source_is_rejected():
    from dataclasses import replace
    d=delta()
    d['updates'][0]['additional_supports']=[{'unit_id':'u1','quote':U1.reading_text}]
    with pytest.raises(V3PlanningContractError, match='authorized ready'):
        replay(d,candidates=(replace(U1,status='quarantined'),U2))
