"""Generate from a saved verified plan. Dry-run default; one paid call with --execute."""
import argparse
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path

from app.chunking.evidence_snapshot import file_hash
from app.chunking.evidence_units import digest
from app.generation.evidence_answer import (
    ANSWER_VERSION, prepare_generation, generation_kwargs, generate_answer, render_answer,
)
from app.orchestration.live_provider import BudgetedClient, RunBudget
from app.orchestration.coordinator import BudgetExceeded


def main(argv=None, *, sdk_factory=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--input-price", required=True, help="USD per million input tokens")
    parser.add_argument("--output-price", required=True, help="USD per million output tokens")
    parser.add_argument("--max-cost-usd", default="0.25")
    parser.add_argument("--max-output-tokens", type=int, default=8000)
    parser.add_argument("--max-input-tokens", type=int, default=120000)
    parser.add_argument("--deadline-seconds", type=int, default=180)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("Use a new output filename")
    if len({p.resolve() for p in (args.snapshot, args.source, args.output)}) != 3:
        parser.error("Snapshot, source and output must have distinct paths")
    try:
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
        saved = json.loads(args.source.read_text(encoding="utf-8"))
        request = prepare_generation(saved, snapshot)
        kwargs = generation_kwargs(request, args.model, args.max_output_tokens)
        budget = RunBudget(args.max_input_tokens, args.max_output_tokens, 1,
                           args.deadline_seconds, args.max_cost_usd)
        prices = {args.model: dict(input_per_million=args.input_price,
                                  output_per_million=args.output_price)}
        BudgetedClient(None, budget, prices)
        reserved_input = len(json.dumps(kwargs, ensure_ascii=False).encode("utf-8")) + 8192
        reservation_cost = (reserved_input * Decimal(args.input_price)
            + args.max_output_tokens * Decimal(args.output_price)) / 1000000
        if reserved_input > budget.max_input_tokens or reservation_cost > Decimal(budget.max_cost_usd):
            raise ValueError("Budget cannot reserve generation; inspect caps and prices")
    except (OSError, ValueError, KeyError, TypeError, InvalidOperation) as exc:
        parser.error(f"Preflight failed: {type(exc).__name__}: {exc}")
    report = dict(status="dry_run", contract_version=ANSWER_VERSION,
        experiment="generation_from_saved_evidence_plan", source_hash=file_hash(args.source),
        snapshot_file_hash=file_hash(args.snapshot), snapshot_id=snapshot["snapshot_id"],
        request=request, api_request_hash=digest(kwargs), generation_settings=kwargs,
        prices=prices, budget=asdict(budget),
        reservation=dict(input_tokens=reserved_input, output_tokens=args.max_output_tokens,
                         estimated_cost_usd=str(reservation_cost)),
        expected_calls=1, answer=None, rendered_answer=None, usage=None,
        semantic_review="not_performed",
        code_hashes={p: file_hash(p) for p in (
            "app/generation/evidence_answer.py", "app/scripts/generate_evidence_answer.py",
            "app/orchestration/evidence_planner.py", "app/orchestration/live_provider.py",
            "app/chunking/evidence_snapshot.py", "app/chunking/evidence_units.py")})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        def save():
            output.seek(0)
            json.dump(report, output, ensure_ascii=False, indent=2, allow_nan=False)
            output.truncate()
            output.flush()
        save()
        if args.execute:
            shared = None
            try:
                if sdk_factory is None:
                    if not os.getenv("OPENAI_API_KEY", "").strip():
                        raise ValueError("Set OPENAI_API_KEY locally")
                    from openai import OpenAI
                    sdk_factory = OpenAI
                def ledger(value):
                    report["usage"] = value
                    save()
                report["status"] = "running"
                save()
                with sdk_factory(timeout=60, max_retries=0) as sdk:
                    shared = BudgetedClient(sdk, budget, prices, checkpoint=ledger)
                    answer = generate_answer(shared, request, args.model, args.max_output_tokens)
                    report.update(answer=answer, rendered_answer=render_answer(answer, request),
                        status="answered_pending_review" if answer["status"] == "answered" else "abstained")
            except Exception as exc:
                report.update(status="budget_exceeded" if isinstance(exc, BudgetExceeded) else "execution_failed",
                              error_type=type(exc).__name__)
            finally:
                if shared is not None:
                    report["usage"] = shared.report()
                save()
    print(f"{report['status']}: {args.output}")
    if report["rendered_answer"]:
        print(report["rendered_answer"])
    else:
        print(f"Generation only: {len(request['bundle']['evidence'])} units; maximum one call.")
    return 1 if report["status"] in ("execution_failed", "budget_exceeded") else 0


if __name__ == "__main__":
    raise SystemExit(main())
