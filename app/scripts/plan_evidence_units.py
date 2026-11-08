"""Dry-run by default; explicit paid scope/selection experiment, without generation."""
import argparse
from dataclasses import asdict, replace
import json
import os
from pathlib import Path

from app.chunking.evidence_snapshot import file_hash, verify_snapshot
from app.orchestration.evidence_planner import (
    EvidencePlanner, LivePlanningProvider, PlannerLimits, SCOPE_INSTRUCTIONS, PLAN_INSTRUCTIONS,
    PLAN_CONTRACT_VERSION, PlanningContractError, planning_payload, validate_scope,
    validate_plan, make_bundle,
)
from app.chunking.evidence_units import digest
from app.orchestration.live_provider import BudgetedClient
from app.retrieval.evidence_unit_retriever import EvidenceUnitRetriever, make_cache, read_cache
from app.retrieval.openai_embeddings import OpenAIEmbeddingProvider
from app.scripts.compare_stage1_orchestration import load_config


def prepare_replay(saved, snapshot, units, config):
    """Reconstruct the exact initial request from canonical units before any payment."""
    result = saved.get("result")
    if (not isinstance(result, dict) or saved["snapshot_id"] != snapshot["snapshot_id"]
            or result["snapshot_id"] != snapshot["snapshot_id"]):
        raise ValueError("Replay requires a result from this snapshot")
    if (config["models"]["assessment"] != saved["config"]["models"]["assessment"]
            or config["as_of"] != saved["config"]["as_of"]
            or config["assessment_output_tokens"] != saved["config"]["assessment_output_tokens"]):
        raise ValueError("Replay holds assessment model, as_of and output cap fixed")
    question = saved["question"]
    if question != result["question"]:
        raise ValueError("Replay question mismatch")
    requests = [e["payload"] for e in result["trace"] if e["stage"] == "plan_request"]
    if not requests or requests[0]["complement_used"]:
        raise ValueError("Replay requires the initial planning request")
    payload = requests[0]
    scope = json.loads(json.dumps(result["scope"]))
    scope.pop("document_ids")
    for field in ("known_conditions", "exclusions"):
        for fact in scope[field]:
            fact["quote"] = fact.pop("source_span")["text"]
    canonical_scope = validate_scope(json.dumps(scope), question)
    if digest(canonical_scope) != digest(result["scope"]) or canonical_scope["decision"] != "proceed":
        raise ValueError("Saved scope differs from its validated question binding")
    catalog = {u.unit_id: u for u in units}
    ids = [u["unit_id"] for u in payload["candidates"]]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Replay candidates must be nonempty and unique")
    candidates = tuple(catalog[uid] for uid in ids)
    docs = canonical_scope["document_ids"]
    if docs and any(u.document_id not in docs for u in candidates):
        raise ValueError("Replay evidence violates explicit document restriction")
    metadata = {d["document_id"]: {**d["metadata"], "as_of": config["as_of"]}
                for d in snapshot["snapshot"]["documents"]}
    expected = planning_payload(question, canonical_scope, candidates, units, metadata)
    if digest(expected) != digest(payload):
        raise ValueError("Saved request differs from canonical evidence/scope/metadata")
    limits = PlannerLimits(**saved["limits"])
    if len(candidates) > limits.max_units or len(json.dumps(payload, ensure_ascii=False)) > limits.max_request_chars:
        raise ValueError("Replay exceeds original structural limits")
    return payload, candidates, limits


def execute_replay(payload, candidates, units, snapshot_id, provider, limits, checkpoint):
    result = dict(status="started", contract_version=PLAN_CONTRACT_VERSION, snapshot_id=snapshot_id,
        question=payload["question"], scope=payload["scope"], bundle=None,
        trace=[dict(stage="plan_request", payload=payload)], semantic_review="not_performed")
    checkpoint(result)
    try:
        plan = validate_plan(provider.invoke("plan", payload), candidates,
            {e["parent_id"] for e in payload["expansion_targets"]}, question=payload["question"])
        result["trace"].append(dict(stage="plan", result=plan))
        kind = plan["action"]["kind"]
        if kind == "complete":
            result["bundle"] = make_bundle(snapshot_id, payload["question"], payload["scope"],
                                            plan, units, max_chars=limits.max_bundle_chars)
            result["status"] = "planned_pending_review"
        elif kind == "clarify":
            result.update(status="clarification_required", clarification=plan["action"]["question"])
        elif kind == "abstain":
            result.update(status="abstained", reason=plan["action"]["reason"])
        else:
            result.update(status="replay_requires_lookup", requested_action=plan["action"])
    except Exception as exc:
        from app.orchestration.coordinator import BudgetExceeded
        result.update(status="budget_exceeded" if isinstance(exc, BudgetExceeded) else "error",
                      error_type=type(exc).__name__)
        result["trace"].append(dict(stage="error", error_type=type(exc).__name__,
            detail=str(exc) if isinstance(exc, PlanningContractError) else None))
    checkpoint(result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True, help="Existing Stage1 run configuration")
    parser.add_argument("--question")
    parser.add_argument("--embedding-cache", type=Path)
    parser.add_argument("--replay-source", type=Path, help="Repeat only the saved initial planning call")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.replay_source and (args.question is not None or args.embedding_cache is not None):
        parser.error("Replay uses the saved question; omit --question and --embedding-cache")
    if not args.replay_source and (args.question is None or args.embedding_cache is None):
        parser.error("Normal execution requires --question and --embedding-cache")
    if args.question is not None and (not args.question.strip() or len(args.question) > 4000):
        parser.error("Question must contain 1–4000 characters")
    if args.output.exists():
        parser.error("Use a new output filename")
    paths = [p for p in (args.snapshot, args.config, args.embedding_cache, args.output, args.replay_source) if p]
    if len({p.resolve() for p in paths}) != len(paths):
        parser.error("Snapshot, config, cache and output must have distinct paths")
    try:
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
        units = verify_snapshot(snapshot, root=Path.cwd())
        config, budget = load_config(args.config)
        vectors, replay = None, None
        if args.replay_source:
            saved = json.loads(args.replay_source.read_text(encoding="utf-8"))
            replay = prepare_replay(saved, snapshot, units, config)
            args.question = replay[0]["question"]
        elif args.embedding_cache.exists():
            vectors = read_cache(json.loads(args.embedding_cache.read_text(encoding="utf-8")),
                                 units, config["models"]["embedding"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(f"Preflight failed: {type(exc).__name__}: {exc}")
    limits = replay[2] if replay else PlannerLimits()
    if replay:
        budget = replace(budget, max_calls=1)
    metadata = {d["document_id"]: d["metadata"] for d in snapshot["snapshot"]["documents"]}
    metadata = {doc: {**value, "as_of": config["as_of"]} for doc, value in metadata.items()}
    report = dict(status="dry_run", contract_version=PLAN_CONTRACT_VERSION,
        experiment="saved_planning_replay" if replay else "scope_and_selection_only",
        snapshot_id=snapshot["snapshot_id"], question=args.question, config=config,
        execution_budget=asdict(budget),
        limits=asdict(limits), embedding_cache="reused" if vectors is not None else "will_create",
        expected_calls=dict(normal=3 if vectors is not None else 4,
                            maximum=5 if vectors is not None else 6),
        prompts=dict(scope=SCOPE_INSTRUCTIONS, plan=PLAN_INSTRUCTIONS),
        code_hashes={p: file_hash(p) for p in (
            "app/orchestration/evidence_planner.py", "app/retrieval/evidence_unit_retriever.py",
            "app/scripts/plan_evidence_units.py", "app/chunking/evidence_units.py",
            "app/chunking/evidence_snapshot.py", "app/orchestration/live_provider.py")},
        result=None, usage=None, semantic_review="not_performed")
    if replay:
        report.update(embedding_cache="not_used", expected_calls=dict(normal=1, maximum=1),
            replay_source_hash=file_hash(args.replay_source), replay_request_hash=digest(replay[0]),
            fixed_inputs="question, scope, candidates, order, metadata, model, output cap; no retrieval")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        def save():
            output.seek(0)
            json.dump(report, output, ensure_ascii=False, indent=2, allow_nan=False)
            output.truncate()
            output.flush()
        save()
        if args.execute:
            try:
                if not os.getenv("OPENAI_API_KEY", "").strip():
                    raise ValueError("Set OPENAI_API_KEY locally")
                from openai import OpenAI
                def ledger(value):
                    report["usage"] = value
                    save()
                def checkpoint(value):
                    report["result"] = value
                    save()
                report["status"] = "running"
                save()
                with OpenAI(timeout=60, max_retries=0) as sdk:
                    shared = BudgetedClient(sdk, budget, config["prices"], checkpoint=ledger)
                    if replay:
                        report["result"] = execute_replay(replay[0], replay[1], units, snapshot["snapshot_id"],
                            LivePlanningProvider(shared, config["models"]["assessment"],
                                                 config["assessment_output_tokens"]), limits, checkpoint)
                        report["usage"] = shared.report()
                        report["status"] = report["result"]["status"]
                        save()
                        print(f"{report['status']}: {args.output}")
                        return 1 if report["status"] in ("error", "budget_exceeded") else 0
                    embedding = OpenAIEmbeddingProvider(shared, model=config["models"]["embedding"])
                    if vectors is None:
                        vectors = embedding.embed_documents(tuple(u.search_text for u in units if u.searchable))
                        cached = make_cache(units, config["models"]["embedding"], vectors)
                        args.embedding_cache.parent.mkdir(parents=True, exist_ok=True)
                        # Exclusive creation protects an existing cache; invalid caches are never overwritten.
                        with args.embedding_cache.open("x", encoding="utf-8") as cache_file:
                            json.dump(cached, cache_file, ensure_ascii=False, allow_nan=False)
                    planner = EvidencePlanner(snapshot_id=snapshot["snapshot_id"], units=units,
                        retriever=EvidenceUnitRetriever(units, vectors, embedding),
                        provider=LivePlanningProvider(shared, config["models"]["assessment"],
                                                      config["assessment_output_tokens"]),
                        metadata=metadata, limits=limits)
                    report["result"] = planner.plan(args.question, checkpoint)
                    report["usage"] = shared.report()
                    report["status"] = report["result"]["status"]
            except Exception as exc:
                from app.orchestration.coordinator import BudgetExceeded
                report.update(status="budget_exceeded" if isinstance(exc, BudgetExceeded) else "execution_failed",
                              error_type=type(exc).__name__)
            save()
    print(f"{report['status']}: {args.output}")
    if report["result"] and report["result"].get("bundle"):
        bundle = report["result"]["bundle"]
        print(f"Coverage: {len(bundle['coverage'])}; evidence: {len(bundle['evidence'])}; chars: {len(bundle['text'])}")
    return 1 if report["status"] in ("error", "execution_failed", "budget_exceeded") else 0


if __name__ == "__main__":
    raise SystemExit(main())
