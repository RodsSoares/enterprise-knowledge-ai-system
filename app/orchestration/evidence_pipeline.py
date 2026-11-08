"""Single-question evidence pipeline with one cumulative API budget, no retries."""
from dataclasses import asdict
from time import perf_counter

from app.chunking.evidence_snapshot import verify_snapshot
from app.chunking.evidence_units import digest
from app.generation.evidence_answer import (
    prepare_generation, generation_kwargs, generate_answer, render_answer,
)
from app.orchestration.evidence_planner import (
    EvidencePlanner, LivePlanningProvider, PlannerLimits, PLAN_CONTRACT_VERSION,
)
from app.orchestration.live_provider import BudgetedClient
from app.orchestration.coordinator import BudgetExceeded
from app.retrieval.evidence_unit_retriever import EvidenceUnitRetriever, read_cache
from app.retrieval.openai_embeddings import OpenAIEmbeddingProvider

PIPELINE_VERSION = "evidence-pipeline/1"


def validate_inputs(snapshot, cache, config, question):
    if not isinstance(question, str) or not question.strip() or len(question) > 4000:
        raise ValueError("Question must contain 1–4000 characters")
    units = verify_snapshot(snapshot)
    vectors = read_cache(cache, units, config['models']['embedding'])
    return units, vectors


def run_pipeline(snapshot, cache, question, config, budget, sdk, *, checkpoint=lambda value: None):
    """Reuse document vectors; scope/search/plan/generation share the SAME client.

    Normal path: four calls. At most one complementary search/expansion, giving
    six calls with a new search or five with expansion. Functional exits can
    end earlier. The budget is checked cumulatively before each provider call.
    """
    started = perf_counter()
    units, vectors = validate_inputs(snapshot, cache, config, question)
    limits = PlannerLimits()
    result = dict(contract_version=PIPELINE_VERSION, status='running', question=question,
        snapshot_id=snapshot['snapshot_id'], stage='planning', planning=None,
        generation_request=None, generation_settings=None, generation_request_hash=None,
        answer=None, rendered_answer=None, usage=None, elapsed_seconds=None,
        semantic_review='not_performed')

    def save():
        result['elapsed_seconds'] = round(perf_counter() - started, 4)
        checkpoint(result)

    def ledger(value):
        result['usage'] = value
        save()

    shared = BudgetedClient(sdk, budget, config['prices'], checkpoint=ledger)
    metadata = {d['document_id']: {**d['metadata'], 'as_of': config['as_of']}
                for d in snapshot['snapshot']['documents']}

    def planning_checkpoint(value):
        result['planning'] = value
        save()

    save()
    try:
        embedding = OpenAIEmbeddingProvider(shared, model=config['models']['embedding'])
        planner = EvidencePlanner(snapshot_id=snapshot['snapshot_id'], units=units,
            retriever=EvidenceUnitRetriever(units, vectors, embedding),
            provider=LivePlanningProvider(shared, config['models']['assessment'],
                                           config['assessment_output_tokens']),
            metadata=metadata, limits=limits)
        planning = planner.plan(question, checkpoint=planning_checkpoint)
        result['planning'] = planning
        if planning['status'] != 'planned_pending_review':
            status = planning['status']
            result['status'] = 'execution_failed' if status == 'error' else status
            for field in ('clarification', 'reason', 'error_type'):
                if field in planning:
                    result[field] = planning[field]
            return result
        result['stage'] = 'generation_preflight'
        save()
        envelope = dict(status=planning['status'], contract_version=PLAN_CONTRACT_VERSION,
            snapshot_id=snapshot['snapshot_id'], question=question, result=planning,
            config=config, limits=asdict(limits))
        request = prepare_generation(envelope, snapshot)
        settings = generation_kwargs(request, config['models']['generation'], config['generation_output_tokens'])
        result.update(generation_request=request, generation_settings=settings,
                      generation_request_hash=digest(settings), stage='generation')
        save()
        answer = generate_answer(shared, request, config['models']['generation'], config['generation_output_tokens'])
        result.update(answer=answer, rendered_answer=render_answer(answer, request),
            status='answered_pending_review' if answer['status'] == 'answered' else 'abstained',
            stage='completed')
        return result
    except Exception as exc:
        result.update(status='budget_exceeded' if isinstance(exc, BudgetExceeded) else 'execution_failed',
                      error_type=type(exc).__name__)
        return result
    finally:
        result['usage'] = shared.report()
        save()
