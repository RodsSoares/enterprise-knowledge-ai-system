"""RV-042 opt-in pipeline regression: all model replies are deterministic stubs."""
from dataclasses import dataclass
import json

from app.orchestration.v3_pipeline import run_v42, run_v3


QUESTION = "Como compartilhar dados?"


@dataclass(frozen=True)
class Unit:
    unit_id: str
    reading_text: str
    document_id: str = "DOC-005"
    status: str = "ready"
    structural_role: str = "paragraph"
    section_path: tuple = ()


CORE = Unit("u1", "Use an approved secure channel.")
ADJACENT = Unit("u2", "AI-specific approval is needed when using a new AI tool.")


def scope():
    return {"request_kind":"general","focus":"Sharing rules","known_conditions":[],
            "exclusions":[],"unknown_conditions":[],"decision":"proceed","clarification":None}


def item(unit, need, *, status="supported"):
    return {"need": need,"relevance":"category","condition":"When applicable",
            "question_quote":"compartilhar","evidence_status":status,
            "supports":[{"unit_id":unit.unit_id,"quote":unit.reading_text}]
                       if status == "supported" else [],
            "missing_aspects":[] if status == "supported" else ["Unknown approval"]}


def plan(*, gap=False, action=None):
    items = [item(CORE,"Secure channel",status="missing" if gap else "supported"),
             item(ADJACENT,"AI approval")]
    return {"items":items,"action":action or ({"kind":"search", "query":"secure", "gap":"approval"}
                                              if gap else {"kind":"complete"})}


def inventory(*, missing=False):
    return {"facets":[{"description":"Approved transfer","supporting_unit_ids":["u2"]}],
            "unresolved_facets":["Missing required approval"] if missing else
                                ["AI tools procedure not requested"]}


def gate(*, missing=False, new=False, demote=False):
    out = {"requirements":[
        {"requirement_id":"C1", "classification":"adjacent" if demote else "conditional", "reason":"Sharing safeguard"},
        {"requirement_id":"C2", "classification":"adjacent", "reason":"No AI request"}],
        "facets":[{"index":0,"classification":"adjacent", "reason":"Nearby AI text only"}],
        "unresolved":[{"index":0,"classification":"material" if missing else "adjacent",
                       "reason":"Required" if missing else "Not requested"}],
        "blocking_questions":[],"rationale":"Scoped to general sharing"}
    return out


def assurance(*, recover=False):
    return {"requirements":[{"requirement_id":"C1","relevance":"applicable",
                             "entailment":"missing" if recover else "supported",
                             "supporting_unit_ids":[] if recover else ["u1"]}],
            "inventory_complete":not recover,
            "omitted_facets":["Missing approval"] if recover else [],
            "decision":"RETRIEVE_MORE" if recover else "APPROVE",
            "lookup":{"semantic_query":"secure channel", "lexical_query":"secure sharing",
                      "document_ids":["DOC-005"], "target_requirement_ids":["C1"]}
                     if recover else None,
            "reason":"Recovery" if recover else "Cited requirements supported"}


def answer():
    return {"status":"answered", "claims":[{"text":"Use approved secure transfer",
                                              "requirement_ids":["C1"],"citation_ids":["u1"]}],
            "abstention_reason":None}


def verification(*, reject=False, scope_error=False):
    return {"suppressed_requirements":[{"requirement_id":"C2","materially_needed":scope_error,
                                         "reason":"Unasked AI workflow" if not scope_error else "Required"}],
            "excluded_unresolved":[{"index":0,"materially_needed":False,
                                    "reason":"Not requested"}],
            "claims":[{"claim_index":0,"entailed":not reject,"relevant":True,
                       "conditions_preserved":True,"verified_citation_ids":["u1"]}],
            "materially_complete":True,"omissions":[],
            "decision":"REJECT" if reject else "PASS","reason":"Audited"}


class Provider:
    def __init__(self, outputs):
        self.outputs={k:list(v) for k,v in outputs.items()}; self.calls=[]
    def invoke(self,stage,payload):
        self.calls.append((stage,payload))
        if not self.outputs.get(stage):
            raise ValueError("Unexpected stage: "+stage)
        return json.dumps(self.outputs[stage].pop(0))


class Retriever:
    def __init__(self, *, initial=(CORE, ADJACENT), recovered=(CORE,)):
        self.initial=initial; self.recovered=recovered; self.recoveries=[]
    def search(self,query,document_ids,top_k):
        return self.initial, {"path":"first"}
    def search_projections(self,s,l,document_ids,top_k):
        self.recoveries.append((s,l,document_ids,top_k))
        return self.recovered, {"path":"recovery"}


def provider(*, gap=False, premature_clarification=False, reject=False, scope_error=False):
    action={"kind":"clarify","question":"What AI tool?"} if premature_clarification else None
    return Provider({
        "scope_v3":[scope()],
        "plan_v3":[plan(gap=gap,action=action)],
        "inventory_v3":[inventory(missing=gap),inventory(missing=False)] if gap else [inventory()],
        "relevance_v42":[gate(missing=True),gate()] if gap else [gate()],
        "assurance_v3":[assurance(recover=True),assurance()] if gap else [assurance()],
        "replan_v3":[{"updates":[
            {"requirement_id":"C1", "evidence_status":"supported",
             "additional_supports":[{"unit_id":"u1","quote":CORE.reading_text}], "missing_aspects":[]},
            {"requirement_id":"C2","evidence_status":"supported",
             "additional_supports":[],"missing_aspects":[]}],
            "new_items":[],"action":{"kind":"complete"}}] if gap else [],
        "generate_v3":[answer()], "verify_v3":[verification(reject=reject or scope_error,
                                                        scope_error=scope_error)],
    })


def test_v42_can_answer_supported_general_question_without_inventing_ai_duties():
    p=provider(); r=Retriever()
    out=run_v42(QUESTION,snapshot_id="fixture",units=(CORE,ADJACENT),retriever=r,provider=p)
    assert out["status"]=="answered_pending_human_review", out
    assert out["relevance_audits"][0]["adjacent_requirements"]==["C2"]
    assert [x["requirement_id"] for x in out["effective_plan"]["items"]]==["C1"]
    assert p.calls[-2][1]["requirements"][0]["requirement_id"]=="C1"
    assert all(x["requirement_id"]!="C2" for x in p.calls[-2][1]["requirements"])
    assert p.calls[0] == ("scope_v3", {"question":QUESTION})
    assert r.recoveries==[]
    assert out["semantic_review"]=="llm_assessed_not_independent_ground_truth"


def test_relevance_gate_can_override_premature_planner_clarification_with_sources():
    p=provider(premature_clarification=True)
    out=run_v42(QUESTION,snapshot_id="fixture",units=(CORE,ADJACENT),retriever=Retriever(),provider=p)
    assert out["status"]=="answered_pending_human_review",out
    assert out["relevance_audits"][0]["full_plan_action"]["kind"]=="clarify"


def test_old_v3_still_honors_original_clarification_without_relevance_stage():
    p=provider(premature_clarification=True)
    out=run_v3(QUESTION,snapshot_id="fixture",units=(CORE,ADJACENT),retriever=Retriever(),provider=p)
    assert out["status"]=="clarification_required"
    assert not any(stage=="relevance_v42" for stage,_ in p.calls)


def test_material_gap_only_one_recovery_preserving_old_requirements():
    p=provider(gap=True)
    r=Retriever(initial=(ADJACENT,),recovered=(CORE,))
    out=run_v42(QUESTION,snapshot_id="fixture",units=(CORE,ADJACENT),retriever=r,provider=p)
    assert out["status"]=="answered_pending_human_review",out
    assert out["recovery_used"] is True
    assert len(r.recoveries)==1
    assert out["relevance_audits"][0]["material_unresolved_count"]==1
    assert out["relevance_audits"][1]["material_unresolved_count"]==0
    assert p.calls[-2][1]["requirements"][0]["requirement_id"]=="C1"


def test_materiality_demotion_after_recovery_fails_closed():
    p=provider(gap=True);p.outputs["relevance_v42"][1]=gate(demote=True)
    out=run_v42(QUESTION,snapshot_id="fixture",units=(CORE,ADJACENT),
                retriever=Retriever(initial=(ADJACENT,),recovered=(CORE,)),provider=p)
    assert out["status"]=="execution_failed"
    assert out["error_type"]=="V42RelevanceError"
    assert out["answer"] is None


def test_all_adjacent_stops_before_assurance_or_generation():
    p=provider();p.outputs["relevance_v42"][0]=gate(demote=True)
    out=run_v42(QUESTION,snapshot_id="fixture",units=(CORE,ADJACENT),retriever=Retriever(),provider=p)
    assert out["status"]=="execution_failed"
    assert out["answer"] is None
    assert not any(x[0] in ("assurance_v3","generate_v3") for x in p.calls)


def test_verifier_reject_still_hides_answer():
    p=provider(reject=True)
    out=run_v42(QUESTION,snapshot_id="fixture",units=(CORE,ADJACENT),retriever=Retriever(),provider=p)
    assert out["status"]=="review_rejected"
    assert out["answer"] is None and out["rendered_answer"] is None


def test_untrusted_foreign_retrieval_still_fails_closed():
    p=provider()
    out=run_v42(QUESTION,snapshot_id="fixture",units=(CORE,ADJACENT),
                retriever=Retriever(initial=(Unit("foreign","forged"),)),provider=p)
    assert out["status"]=="execution_failed"
    assert out["answer"] is None


def test_gate_receives_bounded_cited_evidence_not_full_corpus():
    p=provider();irrelevant=Unit("u3","Unrelated policy")
    r=Retriever(initial=(CORE, ADJACENT, irrelevant))
    out=run_v42(QUESTION,snapshot_id="fixture",units=(CORE,ADJACENT,irrelevant),retriever=r,provider=p)
    assert out["status"]=="answered_pending_human_review"
    call=next(payload for stage,payload in p.calls if stage=="relevance_v42")
    assert "candidates" not in call
    assert {x["unit_id"] for x in call["cited_evidence"]}=={"u1","u2"}


def test_relevance_mode_does_not_override_explicit_restrictions():
    p=provider()
    # The real scope contract extracts explicit DOC IDs from question text.
    out=run_v42("Segundo DOC-999, "+QUESTION,snapshot_id="fixture",
                units=(CORE,ADJACENT),retriever=Retriever(),provider=p)
    assert out["status"]=="abstained"
    assert not any(stage=="relevance_v42" for stage,_ in p.calls)


def test_final_scope_verifier_can_reject_suppressed_material_requirement():
    p=provider(scope_error=True)
    out=run_v42(QUESTION,snapshot_id="fixture",units=(CORE,ADJACENT),retriever=Retriever(),provider=p)
    assert out["status"]=="review_rejected",out
    assert out["answer"] is None
    assert out["verification"]["suppressed_requirements"][0]["materially_needed"] is True


def test_verifier_omitting_suppression_review_fails_closed():
    p=provider()
    p.outputs["verify_v3"][0]["suppressed_requirements"]=[]
    out=run_v42(QUESTION,snapshot_id="fixture",units=(CORE,ADJACENT),retriever=Retriever(),provider=p)
    assert out["status"]=="execution_failed"
    assert out["answer"] is None
