"""Integrated experimental evidence pipeline. Warm cache required; dry-run default."""
import argparse
from copy import deepcopy
from dataclasses import asdict
from decimal import InvalidOperation
import json
import os
from pathlib import Path

from app.chunking.evidence_snapshot import verify_snapshot, file_hash
from app.generation.evidence_answer import INSTRUCTIONS, SCHEMA
from app.chunking.evidence_units import digest
from app.orchestration.evidence_planner import PLAN_INSTRUCTIONS, SCOPE_INSTRUCTIONS, PLAN_SCHEMA, SCOPE_SCHEMA
from app.orchestration.evidence_pipeline import run_pipeline, validate_inputs, PIPELINE_VERSION
from app.orchestration.live_provider import RunBudget, BudgetedClient
from app.scripts.compare_stage1_orchestration import load_config


def main(argv=None, *, sdk_factory=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--embedding-cache', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--question', required=True)
    parser.add_argument('--model', required=True, help='Model for both scope/planning and generation')
    parser.add_argument('--input-price', required=True, help='USD per million input tokens for --model')
    parser.add_argument('--output-price', required=True, help='USD per million output tokens for --model')
    parser.add_argument('--max-cost-usd', default='0.75')
    parser.add_argument('--max-calls', type=int, default=6)
    parser.add_argument('--max-input-tokens', type=int, default=400000)
    parser.add_argument('--max-output-tokens', type=int, default=32000, help='Cumulative output token budget')
    parser.add_argument('--assessment-output-tokens', type=int, default=8000)
    parser.add_argument('--generation-output-tokens', type=int, default=8000)
    parser.add_argument('--deadline-seconds', type=int, default=240)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error('Use a new output filename')
    paths = (args.snapshot, args.embedding_cache, args.config, args.output)
    if len({p.resolve() for p in paths}) != len(paths):
        parser.error('Inputs and output must have distinct paths')
    try:
        config, _ = load_config(args.config)
        config = deepcopy(config)
        if not args.model.strip() or min(args.assessment_output_tokens,args.generation_output_tokens) < 1:
            raise ValueError('Nonempty model and positive per-call output caps required')
        if args.model == config['models']['embedding']:
            raise ValueError('Generation model must differ from embedding model')
        config['models'].update(assessment=args.model, generation=args.model)
        config['prices'][args.model] = dict(input_per_million=args.input_price, output_per_million=args.output_price)
        config.update(assessment_output_tokens=args.assessment_output_tokens,
                      generation_output_tokens=args.generation_output_tokens)
        budget = RunBudget(args.max_input_tokens,args.max_output_tokens,args.max_calls,
                           args.deadline_seconds,args.max_cost_usd)
        config['budget'] = asdict(budget)
        BudgetedClient(None,budget,config['prices'])
        snapshot = json.loads(args.snapshot.read_text(encoding='utf-8'))
        verify_snapshot(snapshot, root=Path.cwd())
        cache = json.loads(args.embedding_cache.read_text(encoding='utf-8'))
        units, _ = validate_inputs(snapshot,cache,config,args.question)
    except (OSError,ValueError,KeyError,TypeError,InvalidOperation) as exc:
        parser.error(f'Preflight failed: {type(exc).__name__}: {exc}')
    report = dict(status='dry_run', contract_version=PIPELINE_VERSION,
        experiment='integrated_scope_retrieval_planning_generation',question=args.question,
        snapshot_id=snapshot['snapshot_id'], snapshot_file_hash=file_hash(args.snapshot),
        embedding_cache_hash=file_hash(args.embedding_cache), source_config_hash=file_hash(args.config),
        config=config, expected_calls=dict(normal=4, maximum=6), document_embeddings='reused',
        searchable_units=sum(u.searchable for u in units), result=None, usage=None,
        semantic_review='not_performed',
        prompts=dict(scope=SCOPE_INSTRUCTIONS,plan=PLAN_INSTRUCTIONS,generation=INSTRUCTIONS),
        schema_hashes=dict(scope=digest(SCOPE_SCHEMA),plan=digest(PLAN_SCHEMA),generation=digest(SCHEMA)),
        code_hashes={p:file_hash(p) for p in (
            'app/orchestration/evidence_pipeline.py','app/scripts/ask_evidence.py',
            'app/orchestration/evidence_planner.py','app/generation/evidence_answer.py',
            'app/orchestration/live_provider.py','app/retrieval/evidence_unit_retriever.py',
            'app/chunking/evidence_snapshot.py','app/chunking/evidence_units.py')})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as output:
        def save():
            output.seek(0)
            json.dump(report,output,ensure_ascii=False,indent=2,allow_nan=False)
            output.truncate(); output.flush()
        save()
        if args.execute:
            try:
                if sdk_factory is None:
                    if not os.getenv('OPENAI_API_KEY','').strip():
                        raise ValueError('Set OPENAI_API_KEY locally')
                    from openai import OpenAI
                    sdk_factory = OpenAI
                def checkpoint(value):
                    report.update(result=value,usage=value['usage'],status=value['status'])
                    save()
                report['status']='running'; save()
                with sdk_factory(timeout=60,max_retries=0) as sdk:
                    result = run_pipeline(snapshot,cache,args.question,config,budget,sdk,checkpoint=checkpoint)
                    report.update(result=result,status=result['status'],usage=result['usage'])
            except Exception as exc:
                report.update(status='execution_failed',error_type=type(exc).__name__)
            save()
    print(f"{report['status']}: {args.output}")
    result=report.get('result') or {}
    if result.get('rendered_answer'):
        print(result['rendered_answer'])
    elif result.get('clarification'):
        print('Esclarecimento: '+result['clarification'])
    elif result.get('reason'):
        print('Abstenção: '+result['reason'])
    if report['usage']:
        print(f"Calls: {report['usage']['calls']} | Estimated USD: {report['usage']['estimated_cost_usd']}")
    else:
        print('Warm cache verified. Normal path: 4 calls; maximum: 6. No API call in dry-run.')
    return 1 if report['status'] in ('execution_failed','budget_exceeded') else 0


if __name__=='__main__':
    raise SystemExit(main())
