"""RV-043 lean RAG path. Preflight only by default; explicit paid execution.

Reuses existing canonical snapshot, hybrid retriever, embedding cache and
BudgetedClient. No interactive prompts, no file overwrites, no hidden model retry.
"""
import argparse
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path

from app.chunking.evidence_snapshot import file_hash, verify_snapshot
from app.orchestration.evidence_pipeline import validate_inputs
from app.orchestration.lean_live_provider import LeanLiveProvider, STAGES
from app.orchestration.lean_pipeline import VERSION, run_lean
from app.orchestration.live_provider import BudgetedClient, RunBudget
from app.retrieval.adaptive_evidence_retriever import AdaptiveEvidenceUnitRetriever
from app.retrieval.openai_embeddings import OpenAIEmbeddingProvider
from app.scripts.compare_stage1_orchestration import load_config
from app.chunking.evidence_units import digest


def _price(s):
    d = Decimal(str(s))
    if not d.is_finite() or d < 0:
        raise ValueError("Finite nonnegative model price required")
    return str(d)


def _question(args):
    if bool(args.question) == bool(args.case_id):
        raise ValueError("Provide exactly one of --question or --case-id")
    if args.question:
        return args.question
    data = json.loads(args.cases.read_text(encoding="utf-8"))
    matching = [case for case in data["cases"] if case["case_id"] == args.case_id]
    if len(matching) != 1:
        raise ValueError("Unknown or duplicated frozen case ID")
    return matching[0]["question"]


def main(argv=None, *, sdk_factory=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--snapshot", type=Path, default=Path("docs/validation/EVIDENCE_UNITS_SNAPSHOT_local.json"))
    p.add_argument("--embedding-cache", type=Path, default=Path("docs/validation/EVIDENCE_UNIT_EMBEDDINGS_local.json"))
    p.add_argument("--config", type=Path, default=Path("docs/validation/STAGE1_RUN_CONFIG_local.json"))
    p.add_argument("--cases", type=Path, default=Path("docs/validation/RV041_CASES_FROZEN.json"))
    p.add_argument("--question")
    p.add_argument("--case-id", help="Existing frozen ORC-001 etc; never changes the case")
    p.add_argument("--model", help="Defaults to generation model in existing config")
    p.add_argument("--input-price", help="Override price USD / million input tokens for chosen model")
    p.add_argument("--output-price", help="Override price USD / million output tokens")
    p.add_argument("--max-cost-usd", default="0.75")
    p.add_argument("--max-input-tokens", type=int, default=160000)
    p.add_argument("--max-output-tokens", type=int, default=20000)
    p.add_argument("--max-per-call-output-tokens", type=int, default=4500)
    p.add_argument("--deadline-seconds", type=int, default=300)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--execute", action="store_true")
    p.add_argument("--confirm-paid", action="store_true")
    a = p.parse_args(argv)
    if a.output.exists():
        p.error("Output exists; choose a new path to preserve prior evidence")
    protected = {x.resolve() for x in (a.snapshot, a.embedding_cache, a.config, a.cases)}
    if a.output.resolve() in protected:
        p.error("Output must differ from canonical inputs")
    try:
        if a.execute != a.confirm_paid:
            raise ValueError("Paid run requires BOTH --execute and --confirm-paid")
        if (a.input_price is None) != (a.output_price is None):
            raise ValueError("Provide both model price overrides or neither")
        if type(a.max_per_call_output_tokens) is not int or not 1 <= a.max_per_call_output_tokens <= 8192:
            raise ValueError("Invalid per-call output cap")
        question = _question(a)
        config, _ = load_config(a.config)
        snapshot = json.loads(a.snapshot.read_text(encoding="utf-8"))
        units = verify_snapshot(snapshot, root=Path.cwd())
        cache = json.loads(a.embedding_cache.read_text(encoding="utf-8"))
        model = a.model or config["models"]["generation"]
        if model == config["models"]["embedding"]:
            raise ValueError("LLM and embedding model cannot match")
        prices = dict(config["prices"])
        if a.input_price is not None:
            prices[model] = {"input_per_million": _price(a.input_price),
                             "output_per_million": _price(a.output_price)}
        if model not in prices:
            raise ValueError("Model pricing missing; pass both price overrides")
        vectors = validate_inputs(snapshot, cache, config, question)[1]
        # Required only for the selected model; explicit pricing for cached embedding.
        budget = RunBudget(a.max_input_tokens, a.max_output_tokens, 5,
                           a.deadline_seconds, a.max_cost_usd)
        BudgetedClient(None, budget, prices)
        metadata = {d["document_id"]: {**d["metadata"], "as_of": config["as_of"]}
                    for d in snapshot["snapshot"]["documents"]}
        if a.execute and sdk_factory is None and not os.getenv("OPENAI_API_KEY", "").strip():
            raise ValueError("OPENAI_API_KEY environment variable is required")
    except (ValueError, KeyError, TypeError, OSError, InvalidOperation) as exc:
        p.error("Preflight failed: " + type(exc).__name__ + ": " + str(exc))

    report = {
        "experiment": "RV043-LEAN", "status": "dry_run", "version": VERSION,
        "question": question, "case_id": a.case_id, "snapshot_id": snapshot["snapshot_id"],
        "models": {"embedding": config["models"]["embedding"], "generation": model},
        "input_hashes": {"snapshot": file_hash(a.snapshot), "embedding_cache": file_hash(a.embedding_cache),
                         "config": file_hash(a.config)},
        "prompts": {s: {"schema_hash": digest(schema), "instructions_hash": digest(instructions)}
                    for s, (schema, instructions) in STAGES.items()},
        "budget": asdict(budget), "max_output_tokens_per_call": a.max_per_call_output_tokens,
        "max_calls_normal": 3, "max_calls_recovery": 5,
        "status_note": "Model review is not independent ground truth; human evaluation required.",
        "result": None, "usage": None,
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("x", encoding="utf-8") as out:
        def save():
            out.seek(0)
            json.dump(report, out, ensure_ascii=False, indent=2, allow_nan=False)
            out.truncate()
            out.flush()
        save()
        if a.execute:
            client = None
            report["status"] = "running"
            save()
            try:
                if sdk_factory is None:
                    from openai import OpenAI
                    sdk_factory = OpenAI
                with sdk_factory(timeout=60, max_retries=0) as sdk:
                    client = BudgetedClient(sdk, budget, prices,
                                            checkpoint=lambda value: (report.update(usage=value), save()))
                    embed = OpenAIEmbeddingProvider(client, model=config["models"]["embedding"])
                    retriever = AdaptiveEvidenceUnitRetriever(units, vectors, embed)
                    provider = LeanLiveProvider(client, model, a.max_per_call_output_tokens)
                    def record(result):
                        report["result"] = result
                        report["status"] = result["status"]
                        save()
                    answer = run_lean(question, snapshot_id=snapshot["snapshot_id"], units=units,
                                      retriever=retriever, provider=provider,
                                      document_metadata=metadata, checkpoint=record)
                    report["result"] = answer
                    report["status"] = answer["status"]
            except Exception as exc:
                report.update(status="execution_failed", error_type=type(exc).__name__,
                              error_message=str(exc)[:500])
            finally:
                if client is not None:
                    report["usage"] = client.report()
                save()
    print("RV043:", report["status"], "| file:", a.output)
    if report["result"] and report["result"].get("rendered_answer"):
        print(report["result"]["rendered_answer"])
    if report["usage"]:
        print("Calls:", report["usage"]["calls"],
              "| estimated USD:", report["usage"]["estimated_cost_usd"])
    else:
        print("Preflight only. No paid calls.")
    return 1 if report["status"] in ("execution_failed", "budget_exceeded") else 0


if __name__ == "__main__":
    raise SystemExit(main())
