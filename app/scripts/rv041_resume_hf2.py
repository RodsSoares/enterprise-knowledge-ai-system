"""RV-041 HF2: resume a halted HF1 qualification without repeating ORC-001 prefix.

Replays only recorded, contract-validated provider outputs and canonical unit IDs
from an immutable, hash-bound source file. Live calls start at replan_v3.
Does not skip source verification. Dry-run by default. Never overwrites output.
"""
import argparse
from copy import deepcopy
from dataclasses import asdict
from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path
from time import perf_counter

from app.orchestration.live_provider import BudgetedClient
from app.orchestration.v3_live_provider import LiveV3Provider
from app.orchestration.v3_pipeline import run_v3
from app.qualification.rv041_protocol import cost_and_calls
from app.retrieval.openai_embeddings import OpenAIEmbeddingProvider
from app.retrieval.v3_dual_query_retriever import DualQueryEvidenceRetriever
from app.orchestration.evidence_pipeline import validate_inputs
from app.scripts.rv041_qualification import setup, make_budget, _hashes, _run_arm
from app.chunking.evidence_snapshot import file_hash

PREFIX_STAGES = ("scope_v3", "plan_v3", "inventory_v3", "assurance_v3")


def validate_hf2_source(source, *, args, cases, config, snapshot):
    if source.get("protocol") != "rv041/qualification-resumed-v3-HF1" or source.get("status") != "halted_after_failure":
        raise ValueError("Expected halted HF1 resume checkpoint")
    if (source.get("cohort") != "development" or source.get("model") != args.model
            or source.get("embedding_model") != config["models"]["embedding"]
            or source.get("snapshot_id") != snapshot["snapshot_id"]):
        raise ValueError("Source run does not match model/cohort/corpus")
    if source.get("case_ids") != [c["case_id"] for c in cases] or source.get("questions") != {
            c["case_id"]: c["question"] for c in cases}:
        raise ValueError("Frozen questions differ")
    if source.get("input_hashes") != {
            "snapshot": file_hash(args.snapshot), "cache": file_hash(args.embedding_cache),
            "config": file_hash(args.config), "cases": file_hash(args.cases)}:
        raise ValueError("Input bytes changed; checkpoint replay forbidden")
    current = _hashes()
    for arm, stages in (("baseline", current["baseline"]),
                         ("v3", {key: current["v3"][key] for key in PREFIX_STAGES})):
        old = source.get("prompt_and_schema_hashes",{}).get(arm,{})
        if any(old.get(stage) != digest for stage,digest in stages.items()):
            raise ValueError("Historical prompt/schema mismatch: " + arm)
    runs = source["runs"]
    if any(runs[c["case_id"]]["baseline"]["status"] != "answered_pending_review" for c in cases):
        raise ValueError("Missing reusable baseline")
    if runs["ORC-001"]["v3"]["status"] != "execution_failed":
        raise ValueError("ORC-001 is not a failed resume candidate")
    if any(runs[c["case_id"]]["v3"]["status"] != "not_rerun_yet" for c in cases[1:]):
        raise ValueError("Other v3 arms have already been rerun")
    r=runs["ORC-001"]["v3"]["result"]
    if (r.get("question") != cases[0]["question"] or r.get("snapshot_id") != snapshot["snapshot_id"]
            or r.get("error_type") != "V3SemanticError" or r.get("stage") != "error"
            or not r.get("recovery_used") or r.get("assurance",{}).get("decision") != "RETRIEVE_MORE"):
        raise ValueError("Unexpected ORC-001 checkpoint stage")
    if source.get("new_run_api_calls") != 7:
        raise ValueError("Expected verified seven-call halted checkpoint")
    return r


def extract_prefix(result, arm_usage, *, units, question):
    """Prepare a source-bound, immutable first-attempt replay, NOT a new guess."""
    events=arm_usage.get("events")
    if not isinstance(events,list) or len(events)!=7:
        raise ValueError("Expected exactly seven recorded calls in stopped ORC-001")
    response_events=[e for e in events if e.get("kind")=="responses"]
    embed_events=[e for e in events if e.get("kind")=="embeddings"]
    if len(response_events)!=5 or len(embed_events)!=2 or any(
            e.get("status")!="completed" for e in events):
        raise ValueError("Unexpected incomplete provider call in replay")
    raw=[]
    for e in response_events[:4]:
        content=e.get("raw_output")
        if not isinstance(content,str) or not content:
            raise ValueError("Missing recorded model output")
        json.loads(content)
        raw.append(content)
    assessment=json.loads(raw[3])
    if assessment != result["assurance"] or assessment.get("decision") != "RETRIEVE_MORE":
        raise ValueError("Recorded assessment does not match checkpoint")
    records={e["stage"]:e for e in result.get("trace",[]) if e.get("stage") in ("initial_retrieval","recovery")}
    if set(records)!={"initial_retrieval","recovery"}:
        raise ValueError("Recorded retrieval stages missing")
    initial=records["initial_retrieval"].get("selected_ids")
    added=records["recovery"].get("recovered_ids")
    catalog={u.unit_id:u for u in units}
    if not isinstance(initial,list) or not isinstance(added,list) or not initial or not added:
        raise ValueError("Recorded canonical IDs missing")
    if (len(set(initial))!=len(initial) or len(set(added))!=len(added)
            or set(initial)&set(added) or not (set(initial)|set(added))<=set(catalog)):
        raise ValueError("Foreign/duplicate retrieval identity")
    lookup=result["assurance"]["lookup"]
    if not lookup or json.loads(raw[3])["lookup"]!=lookup:
        raise ValueError("Recovery lookup differs")
    return list(zip(PREFIX_STAGES,raw)), tuple(catalog[i] for i in initial), tuple(catalog[i] for i in added), lookup


class PrefixProvider:
    def __init__(self, recorded, live):
        self.recorded=list(recorded)
        self.position=0
        self.live=live
    def invoke(self, stage, payload):
        if self.position < len(self.recorded):
            expected,output=self.recorded[self.position]
            if stage!=expected:
                raise ValueError("Prefix replay stage diverged")
            self.position+=1
            return output
        if stage in PREFIX_STAGES and stage not in ("inventory_v3", "assurance_v3"):
            raise ValueError("Unexpected reuse of an initial-only stage")
        return self.live.invoke(stage,payload)


class PrefixRetriever:
    def __init__(self, question, initial, added, lookup):
        self.question,self.initial,self.added,self.lookup=question,initial,added,lookup
        self.initial_called=self.recovery_called=False
    def search(self,query,document_ids,top_k):
        if self.initial_called or query!=self.question or len(self.initial)>top_k:
            raise ValueError("Initial retrieval replay diverged")
        if document_ids and any(u.document_id not in document_ids for u in self.initial):
            raise ValueError("Initial source scope divergence")
        self.initial_called=True
        return self.initial,{"replay":"source-bound-initial", "api_calls":0}
    def search_projections(self,semantic,lexical,document_ids,top_k):
        if (self.recovery_called or not self.initial_called
                or semantic!=self.lookup["semantic_query"] or lexical!=self.lookup["lexical_query"]
                or tuple(document_ids)!=tuple(self.lookup["document_ids"])
                or len(self.added)>top_k):
            raise ValueError("Recovery retrieval replay diverged")
        if document_ids and any(u.document_id not in document_ids for u in self.added):
            raise ValueError("Recovery source scope divergence")
        self.recovery_called=True
        return self.added,{"replay":"source-bound-recovered", "api_calls":0}


def main(argv=None, *, sdk_factory=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('docs/validation/RV041_DEV_V3_RESUME_local.json'))
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--snapshot',default='docs/validation/EVIDENCE_UNITS_SNAPSHOT_local.json')
    p.add_argument('--embedding-cache',default='docs/validation/EVIDENCE_UNIT_EMBEDDINGS_local.json')
    p.add_argument('--config',default='docs/validation/STAGE1_RUN_CONFIG_local.json')
    p.add_argument('--cases',default='docs/validation/RV041_CASES_FROZEN.json')
    p.add_argument('--cohort',choices=('development',),default='development')
    p.add_argument('--model',default='gpt-6.1-sol')
    p.add_argument('--input-price',required=True)
    p.add_argument('--output-price',required=True)
    p.add_argument('--max-new-cost-usd',default='1.00')
    p.add_argument('--max-calls-per-arm',type=int,default=12)
    p.add_argument('--max-input-tokens-per-arm',type=int,default=350000)
    p.add_argument('--max-output-tokens-per-arm',type=int,default=55000)
    p.add_argument('--per-call-output-tokens',type=int,default=4500)
    p.add_argument('--deadline-seconds-per-arm',type=int,default=360)
    p.add_argument('--execute',action='store_true')
    p.add_argument('--confirm-paid',action='store_true')
    args=p.parse_args(argv)
    if args.output.exists() or args.output.resolve() in {args.source.resolve(),Path(args.snapshot).resolve(),Path(args.embedding_cache).resolve()}:
        p.error('Use a fresh output path distinct from inputs')
    if args.execute!=args.confirm_paid:
        p.error('Both --execute and --confirm-paid required for live calls')
    if args.execute and sdk_factory is None and not os.getenv('OPENAI_API_KEY','').strip():
        p.error('OPENAI_API_KEY required for live run')
    args.max_total_cost_usd=args.max_new_cost_usd
    try:
        raw=args.source.read_bytes()
        source=json.loads(raw)
        cases,config,snapshot,cache,units,_=setup(args)
        prior=validate_hf2_source(source,args=args,cases=cases,config=config,snapshot=snapshot)
        stage_replay,initial,added,lookup=extract_prefix(prior,source['runs']['ORC-001']['v3']['usage'],
                                                        units=units,question=cases[0]['question'])
        budget=make_budget(args,len(cases))
    except (ValueError,TypeError,KeyError,OSError) as exc:
        p.error(f'Preflight failed: {type(exc).__name__}: {exc}')
    report=deepcopy(source)
    report.update(protocol='rv041/qualification-resumed-v3-HF2',status='dry_run' if not args.execute else 'running',
        source_hf1_sha256=sha256(raw).hexdigest(),
        historical_failed_v3_calls=source['new_run_api_calls'],
        historical_failed_v3_estimated_usd=source['new_run_estimated_cost_usd'],
        source_baseline_costs_are_historical=True,
        prompt_and_schema_hashes=_hashes(),
        hf2={'replay_source':'seven-call-hf1-checkpoint','replayed_model_calls':4,
             'replayed_embedding_calls':2,'replayed_freeform_replan_response':False,
             'requirement_identity':'frozen-with-evidence-delta',
             'budget_for_new_calls':asdict(budget)},
        new_run_api_calls=0,new_run_estimated_cost_usd='0')
    for case in cases:
        report['runs'][case['case_id']]['v3']={'status':'not_rerun_yet','result':None,'usage':None}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream:
        def save():
            stream.seek(0)
            json.dump(report,stream,indent=2,ensure_ascii=False,allow_nan=False)
            stream.truncate();stream.flush()
        save()
        if not args.execute:
            print('HF2 preflight: frozen canonical replay verified; new API calls: 0')
            print('Saved:',args.output)
            return 0
        if sdk_factory is None:
            from openai import OpenAI
            sdk_factory=OpenAI
        try:
            with sdk_factory(timeout=60,max_retries=0) as sdk:
                for case in cases:
                    cid=case['case_id']
                    report['runs'][cid]['v3']={'status':'running','result':None,'usage':None}
                    save()
                    def checkpoint(value,current=cid):
                        report['runs'][current]['v3']['result']=value
                        save()
                    t0=perf_counter()
                    if cid=='ORC-001':
                        shared=BudgetedClient(sdk,budget,config['prices'])
                        provider=PrefixProvider(stage_replay,LiveV3Provider(shared,args.model,args.per_call_output_tokens))
                        retriever=PrefixRetriever(case['question'],initial,added,lookup)
                        try:
                            outcome=run_v3(case['question'],snapshot_id=snapshot['snapshot_id'],
                                units=units,retriever=retriever,provider=provider,checkpoint=checkpoint)
                            status=outcome['status']
                            if provider.position != 4 or not retriever.recovery_called:
                                raise ValueError('Historical replay was not fully consumed')
                        except Exception as exc:
                            outcome={'status':'execution_failed','error_type':type(exc).__name__}
                            status='execution_failed'
                        arm={'status':status,'result':outcome,'usage':shared.report(),
                             'elapsed_seconds':round(perf_counter()-t0,4),
                             'replayed_historical_calls':6}
                    else:
                        try:
                            arm=_run_arm('v3',case=case,snapshot=snapshot,cache=cache,units=units,
                                config=config,budget=budget,sdk=sdk,
                                per_call_output_tokens=args.per_call_output_tokens,on_result=checkpoint)
                        except Exception as exc:
                            arm={'status':'execution_failed','error_type':type(exc).__name__,
                                 'result':report['runs'][cid]['v3'].get('result'),'usage':None}
                    report['runs'][cid]['v3']=arm
                    usage=arm.get('usage') or {}
                    report['new_run_api_calls']+=usage.get('calls',0)
                    report['new_run_estimated_cost_usd']=str(Decimal(report['new_run_estimated_cost_usd'])+
                                                        Decimal(str(usage.get('estimated_cost_usd','0'))))
                    report['usage_summary']=cost_and_calls(report)
                    save()
                    print(cid,'/ v3-HF2:',arm['status'],flush=True)
                    if arm['status'] in ('execution_failed','budget_exceeded'):
                        report['status']='halted_after_failure'
                        save()
                        break
                else:
                    report['status']='completed'
                    save()
        except Exception as exc:
            report.update(status='execution_failed',error_type=type(exc).__name__)
            save()
            print('HF2 runner error:',type(exc).__name__)
            return 1
        report['usage_summary']=cost_and_calls(report)
        save()
    print('RV041-HF2:',report['status'],'| NEW calls:',report['new_run_api_calls'],
          '| NEW estimated USD:',report['new_run_estimated_cost_usd'])
    print('Saved:',args.output)
    return 1 if report['status']!='completed' else 0

if __name__=='__main__':
    raise SystemExit(main())
