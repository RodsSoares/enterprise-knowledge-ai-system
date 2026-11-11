"""Offline root-cause diagnostic for saved HF1 stopped run. NO API calls."""
import argparse
import json
from pathlib import Path


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('docs/validation/RV041_DEV_V3_RESUME_local.json'))
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    if args.output.exists() or args.source.resolve()==args.output.resolve():
        p.error('New, distinct output required')
    source=json.loads(args.source.read_text(encoding='utf-8'))
    arm=source['runs']['ORC-001']['v3']
    if source['status']!='halted_after_failure' or arm['result']['error_type']!='V3SemanticError':
        raise ValueError('Expected original HF1 stopped report')
    events=arm['usage']['events']
    plans=[json.loads(e['raw_output']) for e in events
           if e['kind']=='responses' and isinstance(e.get('raw_output'),str) and
           set(json.loads(e['raw_output']))=={'items','action'}]
    if len(plans)!=2:
        raise ValueError('Expected two recorded planning outputs')
    original=[x['need'].casefold().strip() for x in plans[0]['items'] if x['relevance']!='out_of_scope']
    rerun=[x['need'].casefold().strip() for x in plans[1]['items'] if x['relevance']!='out_of_scope']
    same=set(original)&set(rerun)
    report={
        'experiment':'RV041-HF2', 'status':'offline_replan_diagnostic',
        'original_active_requirement_count':len(original),
        'replanned_active_requirement_count':len(rerun),
        'original_requirements_with_exact_matching_text':len(same),
        'original_requirements_with_changed_text':len(original)-len(same),
        'structural_problem':'freeform-replan-text-identity-drift',
        'semantic_equivalence_assessed':False,
        'solution':'frozen original identities + validated evidence-only delta',
        'api_calls':0,
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as out:
        json.dump(report,out,ensure_ascii=False,indent=2)
    print(f"HF2 diagnostic: {len(original)} prior active requirements, "
          f"{len(same)} exact-name matches and {len(original)-len(same)} changed descriptions")
    print('Saved:',args.output)
    print('No API calls. No semantic equivalence asserted.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
