"""RV-041 paired baseline/v3 quality qualification. DRY RUN by default.

Only --execute --confirm-paid with explicit prices can access an API.
Same snapshot, model, questions and per-call limits; independent per-arm
budgets together cap the total reservation. Does not judge truth automatically.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
from time import perf_counter

from app.chunking.evidence_snapshot import file_hash, verify_snapshot
from app.chunking.evidence_units import digest
from app.qualification.rv041_protocol import (
    PROTOCOL, load_cases, select_cases, cost_and_calls,
)
from app.orchestration.evidence_pipeline import run_pipeline, validate_inputs
from app.orchestration.evidence_planner import (
    PLAN_INSTRUCTIONS, SCOPE_INSTRUCTIONS, PLAN_SCHEMA, SCOPE_SCHEMA,
)
from app.generation.evidence_answer import INSTRUCTIONS as BASELINE_GENERATION_INSTRUCTIONS
from app.generation.evidence_answer import SCHEMA as BASELINE_GENERATION_SCHEMA
from app.orchestration.live_provider import RunBudget, BudgetedClient
from app.orchestration.v3_live_provider import LiveV3Provider, STAGES
from app.orchestration.v3_pipeline import run_v3
from app.retrieval.v3_dual_query_retriever import DualQueryEvidenceRetriever
from app.retrieval.openai_embeddings import OpenAIEmbeddingProvider
from app.scripts.compare_stage1_orchestration import load_config


def positive_decimal(s, field):
    try:
        value = Decimal(str(s))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Invalid " + field) from exc
    if not value.is_finite() or value <= 0:
        raise ValueError("Positive finite " + field + " required")
    return value


def nonnegative_decimal(s, field):
    try:
        value = Decimal(str(s))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Invalid " + field) from exc
    if not value.is_finite() or value < 0:
        raise ValueError("Nonnegative finite " + field + " required")
    return value


def make_budget(args, num_arms):
    total_cap = positive_decimal(args.max_total_cost_usd, "total budget")
    return RunBudget(
        args.max_input_tokens_per_arm,
        args.max_output_tokens_per_arm,
        args.max_calls_per_arm,
        args.deadline_seconds_per_arm,
        str(total_cap / Decimal(num_arms)),
    )


def setup(args):
    if args.execute != args.confirm_paid:
        raise ValueError("Live run requires BOTH --execute and --confirm-paid")
    if not args.model or not args.model.strip():
        raise ValueError("Nonempty model required")
    if type(args.per_call_output_tokens) is not int or not 1 <= args.per_call_output_tokens <= 8192:
        raise ValueError("Invalid output cap")
    case_file = Path(args.cases)
    cases = select_cases(load_cases(case_file), args.cohort)
    config, _ = load_config(Path(args.config))
    config = deepcopy(config)
    snapshot_path, cache_path = Path(args.snapshot), Path(args.embedding_cache)
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    # Validate physical synthetic corpus sources, not only declared hashes.
    units = verify_snapshot(snapshot, root=Path.cwd())
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    if args.model == config["models"]["embedding"]:
        raise ValueError("LLM model must differ from embedding model")
    prices = dict(config["prices"])
    if args.execute:
        if args.input_price is None or args.output_price is None:
            raise ValueError("Live model prices must be explicitly provided")
        positive_decimal(args.input_price, "LLM input price")
        positive_decimal(args.output_price, "LLM output price")
    # Avoid presenting 0-price preflight as a billing estimate.
    elif args.input_price is not None or args.output_price is not None:
        if args.input_price is None or args.output_price is None:
            raise ValueError("Provide both prices or neither")
        positive_decimal(args.input_price, "LLM input price")
        positive_decimal(args.output_price, "LLM output price")
    prices[args.model] = dict(
        input_per_million=args.input_price or "0",
        output_per_million=args.output_price or "0",
    )
    for p in prices.values():
        nonnegative_decimal(p["input_per_million"], "input price")
        nonnegative_decimal(p["output_per_million"], "output price")
    config["models"].update(assessment=args.model, generation=args.model)
    config["prices"] = prices
    config["assessment_output_tokens"] = args.per_call_output_tokens
    config["generation_output_tokens"] = args.per_call_output_tokens
    for case in cases:
        validate_inputs(snapshot, cache, config, case["question"])
    budget = make_budget(args, len(cases) * 2)
    BudgetedClient(None, budget, prices)
    return cases, config, snapshot, cache, units, budget


def _hashes():
    baseline = {
        "scope": dict(instructions=digest(SCOPE_INSTRUCTIONS), schema=digest(SCOPE_SCHEMA)),
        "plan": dict(instructions=digest(PLAN_INSTRUCTIONS), schema=digest(PLAN_SCHEMA)),
        "generate": dict(instructions=digest(BASELINE_GENERATION_INSTRUCTIONS),
                         schema=digest(BASELINE_GENERATION_SCHEMA)),
    }
    v3 = {name: dict(instructions=digest(instructions), schema=digest(schema))
          for name, (schema, instructions) in STAGES.items()}
    return dict(baseline=baseline, v3=v3)


def _run_arm(arm, *, case, snapshot, cache, units, config, budget, sdk,
             per_call_output_tokens, on_result):
    start = perf_counter()
    if arm == "baseline":
        result = run_pipeline(snapshot, cache, case["question"], config, budget, sdk,
                              checkpoint=on_result)
        return dict(status=result.get("status", "execution_failed"), result=result,
                    usage=result.get("usage"), elapsed_seconds=round(perf_counter() - start, 4))
    client = BudgetedClient(sdk, budget, config["prices"])
    embedding = OpenAIEmbeddingProvider(client, model=config["models"]["embedding"])
    retriever = DualQueryEvidenceRetriever(
        units, validate_inputs(snapshot, cache, config, case["question"])[1], embedding
    )
    provider = LiveV3Provider(client, config["models"]["generation"], per_call_output_tokens)
    try:
        result = run_v3(case["question"], snapshot_id=snapshot["snapshot_id"],
                        units=units, retriever=retriever, provider=provider,
                        checkpoint=on_result)
        status = result.get("status", "execution_failed")
    except Exception as exc:
        # Preserve operational errors separately from grounded abstentions.
        result = {"status": "execution_failed", "error_type": type(exc).__name__}
        status = "execution_failed"
    return dict(status=status, result=result, usage=client.report(),
                elapsed_seconds=round(perf_counter() - start, 4))


def main(argv=None, *, sdk_factory=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", default="docs/validation/EVIDENCE_UNITS_SNAPSHOT_local.json")
    parser.add_argument("--embedding-cache", default="docs/validation/EVIDENCE_UNIT_EMBEDDINGS_local.json")
    parser.add_argument("--config", default="docs/validation/STAGE1_RUN_CONFIG_local.json")
    parser.add_argument("--cases", default="docs/validation/RV041_CASES_FROZEN.json")
    parser.add_argument("--cohort", choices=("development", "safety", "all"), default="development")
    parser.add_argument("--model", default="gpt-6.1-sol")
    parser.add_argument("--input-price", help="Explicit USD per million LLM input tokens")
    parser.add_argument("--output-price", help="Explicit USD per million LLM output tokens")
    parser.add_argument("--max-total-cost-usd", default="2.00")
    parser.add_argument("--max-calls-per-arm", type=int, default=12)
    parser.add_argument("--max-input-tokens-per-arm", type=int, default=350000)
    parser.add_argument("--max-output-tokens-per-arm", type=int, default=55000)
    parser.add_argument("--per-call-output-tokens", type=int, default=4500)
    parser.add_argument("--deadline-seconds-per-arm", type=int, default=360)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm-paid", action="store_true")
    args = parser.parse_args(argv)
    protected_inputs = (args.snapshot, args.embedding_cache, args.config, args.cases)
    if args.output.exists() or args.output.resolve() in {Path(p).resolve() for p in protected_inputs}:
        parser.error("Use a fresh output path distinct from inputs")
    try:
        cases, config, snapshot, cache, units, budget = setup(args)
        if args.execute and sdk_factory is None and not os.getenv("OPENAI_API_KEY", "").strip():
            raise ValueError("OPENAI_API_KEY required only for --execute")
    except (ValueError, KeyError, TypeError, OSError, InvalidOperation) as exc:
        parser.error("Preflight failed: " + type(exc).__name__ + ": " + str(exc))
    report = {
        "protocol": PROTOCOL, "status": "dry_run", "cohort": args.cohort,
        "model": args.model, "embedding_model": config["models"]["embedding"],
        "snapshot_id": snapshot["snapshot_id"],
        "input_hashes": {
            "snapshot": file_hash(args.snapshot), "cache": file_hash(args.embedding_cache),
            "config": file_hash(args.config), "cases": file_hash(args.cases)},
        "prompt_and_schema_hashes": _hashes(),
        "case_ids": [c["case_id"] for c in cases],
        "questions": {c["case_id"]: c["question"] for c in cases},
        "budgets": {"global_cap_usd": str(positive_decimal(args.max_total_cost_usd, "global budget")),
                    "per_arm": asdict(budget), "num_arms": len(cases) * 2},
        "caps_and_controls": {"same_llm_model": True, "same_embedding_model": True,
                              "same_question_and_snapshot": True, "same_per_call_token_cap": True,
                              "max_output_tokens_per_call": args.per_call_output_tokens,
                              "no_auto_retries": True},
        "searchable_units": sum(u.searchable for u in units),
        "runtime_expected_calls": {"baseline": "up to 6", "v3": "up to 11"},
        "runs": {}, "usage_summary": None,
        "semantic_quality_status": "requires_independent_human_review",
        "note": "Runtime truth labels, canonical facts and Golden Set are never provided to either model.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as file:
        def save():
            file.seek(0)
            json.dump(report, file, ensure_ascii=False, indent=2, allow_nan=False)
            file.truncate()
            file.flush()
        save()
        if not args.execute:
            print("RV-041 preflight: verified source snapshot, cached embeddings and frozen cases")
            print("Zero API calls. Comparative runtime NOT executed.")
            print("Frozen development cases:", ", ".join(report["case_ids"]))
            print("Saved:", args.output)
            return 0
        report["status"] = "running"
        save()
        if sdk_factory is None:
            from openai import OpenAI
            sdk_factory = OpenAI
        try:
            with sdk_factory(timeout=60, max_retries=0) as sdk:
                for case in cases:
                    case_id = case["case_id"]
                    report["runs"][case_id] = {}
                    for arm in ("baseline", "v3"):
                        report["runs"][case_id][arm] = {"status": "running", "result": None, "usage": None}
                        save()
                        def checkpoint(value, *, current_case=case_id, current_arm=arm):
                            report["runs"][current_case][current_arm]["result"] = value
                            save()
                        try:
                            run = _run_arm(arm, case=case, snapshot=snapshot, cache=cache,
                                           units=units, config=config, budget=budget,
                                           sdk=sdk, per_call_output_tokens=args.per_call_output_tokens,
                                           on_result=checkpoint)
                        except Exception as exc:
                            run = {"status": "execution_failed", "error_type": type(exc).__name__,
                                   "result": report["runs"][case_id][arm].get("result"),
                                   "usage": None}
                        report["runs"][case_id][arm] = run
                        report["usage_summary"] = cost_and_calls(report)
                        save()
                        print(f"{case_id} / {arm}: {run['status']}", flush=True)
        except Exception as exc:
            report["status"] = "execution_failed"
            report["error_type"] = type(exc).__name__
            save()
            print("RV-041: execution_failed", type(exc).__name__)
            return 1
        failure = any(run["status"] in ("execution_failed", "budget_exceeded")
                      for pair in report["runs"].values() for run in pair.values())
        report["status"] = "completed_with_failures" if failure else "completed"
        report["usage_summary"] = cost_and_calls(report)
        save()
    print("RV-041 status:", report["status"], "| calls:", report["usage_summary"]["total_api_calls"],
          "| estimated USD:", report["usage_summary"]["estimated_total_cost_usd"])
    print("Saved:", args.output)
    return 1 if report["status"] != "completed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
