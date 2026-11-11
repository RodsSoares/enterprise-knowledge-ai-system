"""RV-041 HF3: zero-API canonical replay of the paid ORC-001 replan response.

Proves structural validity after idempotent source citation handling; explicitly
DOES NOT certify the relevance/semantics of newly proposed requirements.
"""
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import re

from app.chunking.evidence_snapshot import file_hash, verify_snapshot
from app.chunking.evidence_units import digest
from app.orchestration.v3_pipeline import _source
from app.orchestration.v3_planning_contract import ValidatedV3Plan
from app.orchestration.v3_replanning_contract import validate_v3_replan


def examine(report, *, units, snapshot, snapshot_file_hash):
    if (report.get('protocol') != 'rv041/qualification-resumed-v3-HF2'
            or report.get('status') != 'halted_after_failure'
            or report.get('snapshot_id') != snapshot.get('snapshot_id')
            or report.get('input_hashes', {}).get('snapshot') != snapshot_file_hash):
        raise ValueError('HF2 report/snapshot binding mismatch')
    cid = 'ORC-001'
    arm = report['runs'][cid]['v3']
    failed = arm['result']
    if (arm['status'] != 'execution_failed' or failed['error_type'] != 'V3PlanningContractError'
            or failed['stage'] != 'error' or not failed['recovery_used']):
        raise ValueError('Unexpected failed execution boundary')
    events = arm['usage']['events']
    if (len(events) != 1 or events[0]['kind'] != 'responses'
            or events[0]['model'] != report['model'] or events[0]['status'] != 'completed'
            or not isinstance(events[0].get('raw_output'), str)):
        raise ValueError('Expected exactly one completed paid replan response')
    trace = failed['trace']
    stages = [item['stage'] for item in trace]
    if stages[-2:] != ['request_replan_v3', 'error'] or stages.count('recovery') != 1:
        raise ValueError('HF2 trace is not a replan failure')
    first = next((x for x in trace if x['stage'] == 'initial_retrieval'), None)
    second = next((x for x in trace if x['stage'] == 'recovery'), None)
    if not first or not second:
        raise ValueError('Missing canonical retrieval identities')
    ids = first['selected_ids'] + second['recovered_ids']
    if len(ids) != len(set(ids)):
        raise ValueError('Repeated canonical source identity')
    catalog = {u.unit_id: u for u in units}
    if len(catalog) != len(units) or any(uid not in catalog for uid in ids):
        raise ValueError('Foreign canonical source identity')
    candidates = tuple(catalog[uid] for uid in ids)
    previous = failed['plan']
    prior = ValidatedV3Plan(tuple(previous['items']), previous['action'], previous['has_known_gap'])
    scope = failed['scope']
    question = report['questions'][cid]
    request = {
        'question': question, 'scope': scope,
        'scope_hash': digest({'question': question, 'scope': scope}),
        'snapshot_id': snapshot['snapshot_id'], 'recovery_used': True,
        'candidates': [_source(u) for u in candidates],
        'previous_requirements': list(prior.items),
        'previous_assurance': failed['assurance'],
    }
    request_trace = trace[-2]
    if (request_trace['payload_hash'] != digest(request) or
            request_trace['chars'] != len(json.dumps(request, ensure_ascii=False, allow_nan=False))):
        raise ValueError('Frozen replan request hash mismatch')
    raw = events[0]['raw_output']
    delta = json.loads(raw)
    if not isinstance(delta.get('new_items'), list) or not isinstance(delta.get('updates'), list):
        raise ValueError('Replan response is not a delta')
    before = {s['unit_id'] for row in prior.items for s in row['supports']}
    duplicates = [s['unit_id'] for row in delta['updates'] for s in row.get('additional_supports', [])
                  if s.get('unit_id') in before]
    result = validate_v3_replan(raw, previous_plan=prior, question=question, candidates=candidates)
    if len(result.items) < len(prior.items):
        raise ValueError('Replan lost an original requirement')
    # Surface a potential directional scope drift for *human inspection* only.
    ai_terms = re.compile(r'\b(?:IA|AI)\b|intelig[eê]ncia artificial', re.I)
    newly_ai_related = [item['need'] for item in delta['new_items'] if ai_terms.search(item['need'])]
    return {
        'experiment': 'RV041-HF3',
        'status': 'structural_replay_valid', 'api_calls': 0,
        'qualification': 'STRUCTURAL_ONLY_NOT_SEMANTIC_PROOF',
        'source_snapshot_id': snapshot['snapshot_id'],
        'question': question, 'reused_model_output_hash': sha256(raw.encode('utf-8')).hexdigest(),
        'previous_active_requirements': sum(x['relevance'] != 'out_of_scope' for x in prior.items),
        'final_active_requirements': sum(x['relevance'] != 'out_of_scope' for x in result.items),
        'new_requirements': len(delta['new_items']),
        'validated_redundant_source_refs': duplicates,
        'replayed_decision': result.action['kind'],
        'replayed_action': result.action,
        'potential_scope_expansion': {
            'flag': bool(newly_ai_related) and not bool(ai_terms.search(question)),
            'new_ai_related_requirements': len(newly_ai_related),
            'review_required': True,
            'note': 'Keyword alert only; relevance is NOT deterministically certified.',
        },
        'next_step': 'Do not rerun paid v3 before assessing materiality and answerability.',
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=Path('docs/validation/RV041_DEV_V3_HF2_LIVE_local.json'))
    p.add_argument('--snapshot', type=Path, default=Path('docs/validation/EVIDENCE_UNITS_SNAPSHOT_local.json'))
    p.add_argument('--output', type=Path, default=Path('docs/validation/RV041_HF3_CANONICAL_REPLAY_local.json'))
    args = p.parse_args(argv)
    if args.output.exists() or args.output.resolve() in (args.source.resolve(), args.snapshot.resolve()):
        p.error('Output must be new and distinct from inputs')
    raw = args.source.read_bytes()
    report = json.loads(raw)
    snapshot = json.loads(args.snapshot.read_text(encoding='utf-8'))
    units = verify_snapshot(snapshot, root=Path.cwd())
    result = examine(report, units=units, snapshot=snapshot,
                     snapshot_file_hash=file_hash(args.snapshot))
    result['source_report_sha256'] = sha256(raw).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
    print('RV041-HF3: exact paid output replayed, canonical sources verified, API calls: 0')
    print('Plan requirements:', result['previous_active_requirements'], '->', result['final_active_requirements'])
    print('Structural result:', result['status'], '| decision:', result['replayed_decision'])
    print('Potential scope expansion:', result['potential_scope_expansion']['new_ai_related_requirements'],
          'AI-related new requirements (human review required)')
    print('Saved:', args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
