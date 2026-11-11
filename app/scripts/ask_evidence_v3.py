"""RV-040 opt-in full experimental pipeline. DRY-RUN by default.

Baseline remains: python -m app.scripts.ask_evidence
V3 candidate: python -m app.scripts.ask_evidence_v3
No live calls without --execute and explicit model prices.
"""
import argparse
from decimal import InvalidOperation
from dataclasses import asdict
import json
import os
from pathlib import Path

from app.chunking.evidence_snapshot import verify_snapshot, file_hash
from app.chunking.evidence_units import digest
from app.orchestration.evidence_pipeline import validate_inputs
from app.orchestration.live_provider import RunBudget, BudgetedClient
from app.orchestration.v3_live_provider import STAGES, LiveV3Provider
from app.orchestration.v3_pipeline import PIPELINE_V3, run_v3
from app.retrieval.v3_dual_query_retriever import DualQueryEvidenceRetriever
from app.retrieval.openai_embeddings import OpenAIEmbeddingProvider
from app.scripts.compare_stage1_orchestration import load_config


def main(argv=None, *, sdk_factory=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--embedding-cache", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--model", default="gpt-6.1-sol")
    parser.add_argument("--input-price", help="Explicit USD/million for live model input")
    parser.add_argument("--output-price", help="Explicit USD/million for live model output")
    parser.add_argument("--max-cost-usd", default="1.50")
    parser.add_argument("--max-calls", type=int, default=12)
    parser.add_argument("--max-input-tokens", type=int, default=350000)
    parser.add_argument("--max-output-tokens", type=int, default=55000)
    parser.add_argument("--max-per-call-output-tokens", type=int, default=4500)
    parser.add_argument("--deadline-seconds", type=int, default=360)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.output.exists() or len({p.resolve() for p in
        (args.snapshot, args.embedding_cache, args.config, args.output)}) != 4:
        parser.error("Output must be a new, distinct file")
    try:
        if args.execute and (args.input_price is None or args.output_price is None):
            raise ValueError("Live execution requires explicit input/output token prices")
        if not args.model.strip() or not 1 <= args.max_per_call_output_tokens <= 8192:
            raise ValueError("Invalid model or output token cap")
        config, _ = load_config(args.config)
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
        # Full canonical integrity, including physical sources, before any paid call.
        units = verify_snapshot(snapshot, root=Path.cwd())
        cache = json.loads(args.embedding_cache.read_text(encoding="utf-8"))
        prices = dict(config["prices"])
        if args.model == config["models"]["embedding"]:
            raise ValueError("Generation model cannot equal embedding model")
        prices[args.model] = dict(
            input_per_million=args.input_price if args.input_price is not None else "0",
            output_per_million=args.output_price if args.output_price is not None else "0",
        )
        config = {**config, "prices": prices}
        units, vectors = validate_inputs(snapshot, cache, config, args.question)
        budget = RunBudget(args.max_input_tokens, args.max_output_tokens,
                           args.max_calls, args.deadline_seconds, args.max_cost_usd)
        BudgetedClient(None, budget, prices)
    except (OSError, ValueError, KeyError, TypeError, InvalidOperation) as exc:
        parser.error("Preflight failed: " + type(exc).__name__ + ": " + str(exc))

    report = {
        "experiment": "RV-040", "status": "dry_run", "contract_version": PIPELINE_V3,
        "question": args.question, "snapshot_id": snapshot["snapshot_id"],
        "snapshot_file_hash": file_hash(args.snapshot),
        "embedding_cache_hash": file_hash(args.embedding_cache),
        "config_file_hash": file_hash(args.config),
        "models": {"embedding": config["models"]["embedding"], "llm": args.model},
        "prompts_and_schemas": {stage: {"schema_hash": digest(schema),
                            "instructions_hash": digest(instructions)}
             for stage, (schema, instructions) in STAGES.items()},
        "limits": asdict(budget), "per_call_output_tokens": args.max_per_call_output_tokens,
        "normal_max_api_calls": 7, "recovery_max_api_calls": 11,
        "searchable_units": sum(u.searchable for u in units),
        "dry_run": not args.execute, "results": None, "usage": None,
        "semantic_review": "not_performed",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        def save():
            output.seek(0)
            json.dump(report, output, ensure_ascii=False, indent=2, allow_nan=False)
            output.truncate()
            output.flush()
        save()
        if args.execute:
            report["status"] = "running"
            save()
            client = None
            try:
                if sdk_factory is None:
                    if not os.getenv("OPENAI_API_KEY", "").strip():
                        raise ValueError("OPENAI_API_KEY not configured")
                    from openai import OpenAI
                    sdk_factory = OpenAI
                with sdk_factory(timeout=60, max_retries=0) as sdk:
                    def usage_checkpoint(value):
                        report["usage"] = value
                        save()
                    client = BudgetedClient(sdk, budget, prices, checkpoint=usage_checkpoint)
                    embeddings = OpenAIEmbeddingProvider(client, model=config["models"]["embedding"])
                    retriever = DualQueryEvidenceRetriever(units, vectors, embeddings)
                    provider = LiveV3Provider(client, args.model, args.max_per_call_output_tokens)
                    def run_checkpoint(value):
                        report["results"] = value
                        report["status"] = value["status"]
                        save()
                    result = run_v3(args.question, snapshot_id=snapshot["snapshot_id"],
                                    units=units, retriever=retriever, provider=provider,
                                    checkpoint=run_checkpoint)
                    report["results"] = result
                    report["status"] = result["status"]
            except Exception as exc:
                report.update(status="execution_failed", error_type=type(exc).__name__)
            finally:
                if client is not None:
                    report["usage"] = client.report()
                save()
    print(f"{report['status']}: {args.output}")
    if report["results"] and report["results"].get("rendered_answer"):
        print(report["results"]["rendered_answer"])
    if report["usage"]:
        print("Calls:", report["usage"]["calls"],
              "Estimated USD:", report["usage"]["estimated_cost_usd"])
    else:
        print("Canonical catalog + warm embeddings verified. API calls: 0")
    return 1 if report["status"] in ("execution_failed", "budget_exceeded") else 0


if __name__ == "__main__":
    raise SystemExit(main())
