"""Prepare once; compare baseline/candidate explicitly, with shared API budget."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path

from app.generation.openai_answer_provider import INSTRUCTIONS
from app.generation.rag_service import RagService, build_service
from app.orchestration.contracts import digest
from app.orchestration.coordinator import Stage1Coordinator, Stage1Limits
from app.orchestration.live_provider import (ASSESSMENT_INSTRUCTIONS, ASSESSMENT_SCHEMA,
    BudgetedClient, LiveAssessor, LiveGenerator, LiveRetriever, RunBudget)
from app.orchestration.snapshot import CorpusSnapshot, file_hash, prepare_snapshot
from app.retrieval.openai_embeddings import OpenAIEmbeddingProvider
from app.scripts.ask_knowledge import discover_sources, load_chunks


def load_config(path):
    p=json.loads(path.read_text(encoding='utf-8'))
    if set(p)!={'models','prices','budget','assessment_output_tokens','generation_output_tokens','as_of'}:
        raise ValueError('Config requires models/prices/budget/output caps/as_of')
    from datetime import date
    date.fromisoformat(p['as_of'])
    if set(p['models'])!={'assessment','generation','embedding'}:
        raise ValueError('Three explicit model roles required')
    for m in p['models'].values():
        if not isinstance(m,str) or not m.strip() or m not in p['prices']:
            raise ValueError('Model and price required')
    for k in ('assessment_output_tokens','generation_output_tokens'):
        if type(p[k]) is not int or p[k]<1:
            raise ValueError('Explicit positive output caps required')
    budget=RunBudget(**p['budget'])
    BudgetedClient(None,budget,p['prices'])  # Validate prices without SDK/API.
    return p,budget


def compare_case(snapshot, case, config, budget, sdk_client, checkpoint=None, *, raise_errors=False):
    snapshot.verify()
    shared=BudgetedClient(sdk_client,budget,config['prices'],checkpoint=checkpoint)
    result=dict(question=case['question'],case_id=case['id'],snapshot_id=snapshot.snapshot_id,
        baseline=None,candidate=None,semantic_verdict='pending_human_review')
    generator=LiveGenerator(shared,model=config['models']['generation'],
        max_output_tokens=config['generation_output_tokens'])
    stage='indexing'
    try:
        baseline=build_service(snapshot.chunks,OpenAIEmbeddingProvider(shared,model=config['models']['embedding']),generator)
        # Identical initial candidate pool in both arms, with no second query embedding.
        retriever=LiveRetriever(baseline.retriever,shared)
        baseline.retriever=retriever
        stage='baseline'
        result['baseline']=baseline.ask(case['question']).to_dict()
        stage='candidate_initialization'
        candidate=Stage1Coordinator(chunks=snapshot.chunks,retriever=retriever,
            assessor=LiveAssessor(shared,config['models']['assessment'],config['assessment_output_tokens']),
            generator=generator,snapshot=snapshot,allow_live=True,as_of=config['as_of'],
            limits=Stage1Limits(deadline_seconds=budget.deadline_seconds))
        stage='candidate_execution'
        result['candidate']=candidate.ask(case['question']).to_dict()
    except Exception as exc:
        result['error_type']=type(exc).__name__
        result['error_stage']=stage
        if raise_errors:
            raise
    finally:
        result['usage']=shared.report()
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    prep=sub.add_parser('prepare')
    prep.add_argument('--corpus',type=Path,default=Path('data/source/corporate_repository'))
    prep.add_argument('--registry',type=Path,default=Path('data/ground_truth/document_registry.yaml'))
    prep.add_argument('--output',type=Path,required=True)
    run=sub.add_parser('run')
    run.add_argument('--source',type=Path,required=True)
    run.add_argument('--suite',type=Path,default=Path('data/ground_truth/orchestration_stage1_cases.json'))
    run.add_argument('--case',required=True)
    run.add_argument('--config',type=Path,required=True)
    run.add_argument('--output',type=Path,required=True)
    run.add_argument('--execute',action='store_true',help='Explicitly enable paid API calls')
    args=parser.parse_args(argv)
    if args.output.exists():
        parser.error('Choose a new output filename')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    # Reserve destination before processing/API work; never overwrite user results.
    with args.output.open('x',encoding='utf-8') as target:
        report=dict(status='started',command=args.command)
        def save():
            target.seek(0)
            json.dump(report,target,ensure_ascii=False,indent=2)
            target.truncate()
            target.flush()
        save()
        try:
            if args.command=='prepare':
                snapshot=prepare_snapshot(discover_sources(args.corpus),args.registry,load_chunks)
                report.update(status='prepared',snapshot_id=snapshot.snapshot_id,snapshot=snapshot.payload)
            else:
                saved=json.loads(args.source.read_text(encoding='utf-8'))
                snapshot=CorpusSnapshot(json.dumps(saved['snapshot'],ensure_ascii=False)).verify()
                if snapshot.snapshot_id!=saved['snapshot_id']:
                    raise ValueError('Snapshot digest mismatch')
                suite=json.loads(args.suite.read_text(encoding='utf-8'))
                selected=[c for c in suite['cases'] if c['id']==args.case]
                if len(selected)!=1:
                    raise ValueError('Exactly one matching case required')
                case=selected[0]
                if not set(case['reference_document_ids'])<=set(snapshot.metadata):
                    raise ValueError('Reference document absent from physical snapshot')
                config,budget=load_config(args.config)
                report.update(status='dry_run',snapshot_id=snapshot.snapshot_id,
                    suite_hash=file_hash(args.suite),config=config,case_id=case['id'],split=case['split'],
                    question=case['question'],prompts=dict(assessment=ASSESSMENT_INSTRUCTIONS,generation=INSTRUCTIONS),
                    assessment_schema_hash=digest(ASSESSMENT_SCHEMA),
                    scope='One paired comparison; budget includes indexing and both arms',
                    estimate='At most 7 paid calls: document embeddings, initial query, baseline generation, two assessments, optional search embedding, candidate generation',
                    runtime_code_hashes={p.as_posix():file_hash(p) for p in sorted(Path('app').rglob('*.py'))})
                save()
                if args.execute:
                    import os
                    if not os.getenv('OPENAI_API_KEY','').strip():
                        raise ValueError('Set OPENAI_API_KEY locally')
                    from openai import OpenAI
                    def checkpoint(usage):
                        report.update(status='running',usage_checkpoint=usage)
                        save()
                    with OpenAI(timeout=60,max_retries=0) as client:
                        report['result']=compare_case(snapshot,case,config,budget,client,checkpoint)
                    report['status']='executed_pending_review'
                    if ('error_type' in report['result'] or
                            (report['result'].get('candidate') or {}).get('status') in ('error','budget_exceeded')):
                        report['status']='execution_failed'
            save()
        except Exception as exc:
            report.update(status='error',error_type=type(exc).__name__)
            save()
            raise
    print(f"{report['status']}: {args.output}")
    return 1 if report['status']=='execution_failed' else 0


if __name__=='__main__':
    raise SystemExit(main())
