"""Diagnostic generation-only comparison. No retrieval, parsing or embeddings."""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
from time import perf_counter

from app.generation.answer_contract import parse_answer, validate_answer
from app.generation.openai_answer_provider import INSTRUCTIONS, SCHEMA, OpenAIAnswerProvider
from app.orchestration.contracts import digest
from app.orchestration.live_provider import BudgetedClient
from app.orchestration.snapshot import CorpusSnapshot, file_hash
from app.retrieval.evidence_context import EvidenceContext, EvidencePassage, render_context
from app.scripts.compare_stage1_orchestration import load_config

# Human-designed development controls, NEVER production selection rules.
MINIMUM = {
    'ORC-001': ('DOC-005::chunk-00005', 'DOC-005::chunk-00007'),
    'ORC-002': ('DOC-005::chunk-00005', 'DOC-005::chunk-00007'),
    'ORC-003': ('DOC-023::chunk-00005', 'DOC-012::chunk-00001'),
    'ORC-004': ('DOC-010::chunk-00004', 'DOC-010::chunk-00005'),
}


def make_context(chunks):
    passages=tuple(EvidencePassage(f'E{i}',c,'diagnostic_control') for i,c in enumerate(chunks,1))
    return EvidenceContext(passages,tuple(dict.fromkeys(c.document_id for c in chunks)),(),render_context(passages))


def prepare_cases(snapshot, saved, suite):
    """Canonical subset comparison; broad arm is a controlled distractor bank."""
    if saved['snapshot_id'] != snapshot.snapshot_id:
        raise ValueError('Comparison and snapshot differ')
    catalog={c.chunk_id:c for c in snapshot.chunks}
    baseline=saved['result']['baseline']
    evidence=json.loads(baseline['context']['text'])['evidence']
    broad_ids=[e['chunk_id'] for e in evidence]
    if len(set(broad_ids))!=len(broad_ids) or not broad_ids:
        raise ValueError('Saved context must be nonempty with unique chunks')
    for e in evidence:
        chunk=catalog.get(e['chunk_id'])
        if chunk is None or e['text']!=chunk.text or e['document_id']!=chunk.document_id:
            raise ValueError('Saved evidence differs from canonical snapshot')
        original=EvidencePassage(e['citation_id'],chunk,'source').citation_metadata()
        if {k:e[k] for k in original}!=original:
            raise ValueError('Saved provenance differs from snapshot')
    if render_context(tuple(EvidencePassage(e['citation_id'],catalog[e['chunk_id']],'source') for e in evidence))!=baseline['context']['text']:
        raise ValueError('Noncanonical saved rendering')
    original_context=make_context([catalog[i] for i in broad_ids])
    validate_answer(baseline['answer'],question=saved['question'],context=original_context)
    cases=[]
    for case_id, minimum in MINIMUM.items():
        matches=[c for c in suite['cases'] if c['id']==case_id]
        if len(matches)!=1 or matches[0]['split']!='development':
            raise ValueError('Only the four development cases are eligible')
        if any(cid not in catalog for cid in minimum):
            raise ValueError('Missing required control evidence')
        # Add evidence missing from the distractor bank, so narrow is a subset.
        ids=broad_ids+[cid for cid in minimum if cid not in broad_ids]
        narrow_ids=[cid for cid in ids if cid in minimum]
        narrow=make_context([catalog[cid] for cid in narrow_ids])
        broad=make_context([catalog[cid] for cid in ids])
        cases.append(dict(case_id=case_id,question=matches[0]['question'],
            contexts={'minimal':narrow,'broad':broad}))
    return cases


def context_record(context):
    return dict(text=context.text,hash=digest(context.text),citations=context.citations,
        passage_count=len(context.passages),character_count=len(context.text))


def execute_cases(cases, generator, checkpoint):
    rows=[]
    for i,case in enumerate(cases):
        # Alternate order; this does not establish statistical significance.
        order=('minimal','broad') if i%2==0 else ('broad','minimal')
        for arm in order:
            context=case['contexts'][arm]
            row=dict(case_id=case['case_id'],arm=arm,status='started',
                question=case['question'],context_hash=digest(context.text))
            rows.append(row);checkpoint(rows)
            start=perf_counter()
            try:
                generation=generator.generate(case['question'],context)
                answer=parse_answer(generation.raw,question=case['question'],context=context)
                row.update(status='contract_valid',answer=answer.to_dict(),
                    generation=asdict(generation),semantic_verdict='pending_human_review')
            except Exception as exc:
                row.update(status='error',error_type=type(exc).__name__)
                raise
            finally:
                row['elapsed_seconds']=perf_counter()-start
                checkpoint(rows)
    return rows


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,required=True)
    parser.add_argument('--comparison',type=Path,required=True)
    parser.add_argument('--suite',type=Path,default=Path('data/ground_truth/orchestration_stage1_cases.json'))
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args(argv)
    if args.output.exists():parser.error('Use a new output filename')
    source=json.loads(args.snapshot.read_text(encoding='utf-8'))
    snapshot=CorpusSnapshot(json.dumps(source['snapshot'],ensure_ascii=False)).verify()
    if snapshot.snapshot_id!=source['snapshot_id']:raise ValueError('Snapshot hash mismatch')
    saved=json.loads(args.comparison.read_text(encoding='utf-8'))
    suite=json.loads(args.suite.read_text(encoding='utf-8'))
    cases=prepare_cases(snapshot,saved,suite)
    config,budget=load_config(args.config)
    if budget.max_calls<8:raise ValueError('A complete comparison needs eight generation calls')
    report=dict(status='dry_run',snapshot_id=snapshot.snapshot_id,
        source_comparison_hash=file_hash(args.comparison),suite_hash=file_hash(args.suite),
        config=config,prompt=INSTRUCTIONS,schema_hash=digest(SCHEMA),
        experiment='Human-selected minimal subset vs controlled broad distractor bank; not a retrieval benchmark',
        sampling='One sample per arm; four development cases; alternate arm order; provider defaults unchanged',
        contexts=[dict(case_id=c['case_id'],question=c['question'],
            arms={a:context_record(x) for a,x in c['contexts'].items()}) for c in cases],
        runtime_code_hashes={p.as_posix():file_hash(p) for p in sorted(Path('app').rglob('*.py'))},
        results=[])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as out:
        def save():
            out.seek(0);json.dump(report,out,ensure_ascii=False,indent=2);out.truncate();out.flush()
        save()
        if args.execute:
            try:
                if not os.getenv('OPENAI_API_KEY','').strip():raise ValueError('Set OPENAI_API_KEY locally')
                def ledger(usage):
                    report['usage']=usage;save()
                def checkpoint(rows):
                    report['results']=rows;save()
                from openai import OpenAI
                with OpenAI(timeout=60,max_retries=0) as client:
                    shared=BudgetedClient(client,budget,config['prices'],checkpoint=ledger)
                    generator=OpenAIAnswerProvider(shared,model=config['models']['generation'],
                        max_output_tokens=config['generation_output_tokens'])
                    report['status']='running';save()
                    execute_cases(cases,generator,checkpoint)
                    report['usage']=shared.report()
                report['status']='executed_pending_review'
            except Exception as exc:
                report.update(status='execution_failed',error_type=type(exc).__name__)
            save()
    print(f"{report['status']}: {args.output}")
    for c in cases:
        print(c['case_id'], ' | '.join(f'{a}: {len(x.passages)} passages, {len(x.text)} chars' for a,x in c['contexts'].items()))
    return 1 if report['status']=='execution_failed' else 0


if __name__=='__main__':
    raise SystemExit(main())
