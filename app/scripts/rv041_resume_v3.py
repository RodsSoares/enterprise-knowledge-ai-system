"""RV-041 HF1: complete only failed V3 arms, reusing frozen paid baselines.

Dry-run is the default; two explicit CLI flags are required for paid calls.
Do not redo already paid baseline calls.
"""
import argparse
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
from time import perf_counter

from app.chunking.evidence_snapshot import file_hash
from app.qualification.rv041_protocol import cost_and_calls
from app.scripts.rv041_qualification import setup, make_budget, _hashes, _run_arm


def _validate_resume(source, cases, config, snapshot, args):
    if (source.get("status") != "completed_with_failures"
            or source.get("cohort") != args.cohort
            or source.get("model") != args.model
            or source.get("embedding_model") != config["models"]["embedding"]
            or source.get("snapshot_id") != snapshot["snapshot_id"]):
        raise ValueError("Source paired report does not match requested experiment")
    if source.get("case_ids") != [case["case_id"] for case in cases]:
        raise ValueError("Frozen case IDs changed")
    if source.get("questions") != {c["case_id"]: c["question"] for c in cases}:
        raise ValueError("Frozen case questions changed")
    if source.get("input_hashes") != {
        "snapshot": file_hash(args.snapshot),
        "cache": file_hash(args.embedding_cache),
        "config": file_hash(args.config),
        "cases": file_hash(args.cases),
    }:
        raise ValueError("Snapshot/embedding/config/case bytes differ from original run")
    if source.get("prompt_and_schema_hashes",{}).get("baseline") != _hashes()["baseline"]:
        raise ValueError("Baseline prompts or schemas changed; cannot reuse baseline")
    for case in cases:
        r = source.get("runs",{}).get(case["case_id"], {})
        if r.get("baseline",{}).get("status") != "answered_pending_review":
            raise ValueError("No successful reusable baseline for " + case["case_id"])
        if r.get("v3",{}).get("status") != "execution_failed":
            raise ValueError("V3 arm is not an eligible failed arm: " + case["case_id"])
    return True


def main(argv=None, *, sdk_factory=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("docs/validation/RV041_DEV_LIVE_local.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--snapshot", default="docs/validation/EVIDENCE_UNITS_SNAPSHOT_local.json")
    parser.add_argument("--embedding-cache", default="docs/validation/EVIDENCE_UNIT_EMBEDDINGS_local.json")
    parser.add_argument("--config", default="docs/validation/STAGE1_RUN_CONFIG_local.json")
    parser.add_argument("--cases", default="docs/validation/RV041_CASES_FROZEN.json")
    parser.add_argument("--cohort", choices=("development",), default="development")
    parser.add_argument("--model", default="gpt-6.1-sol")
    parser.add_argument("--input-price", required=True)
    parser.add_argument("--output-price", required=True)
    parser.add_argument("--max-new-cost-usd", default="1.00")
    parser.add_argument("--max-calls-per-arm", type=int, default=12)
    parser.add_argument("--max-input-tokens-per-arm", type=int, default=350000)
    parser.add_argument("--max-output-tokens-per-arm", type=int, default=55000)
    parser.add_argument("--per-call-output-tokens", type=int, default=4500)
    parser.add_argument("--deadline-seconds-per-arm", type=int, default=360)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm-paid", action="store_true")
    args = parser.parse_args(argv)
    if args.output.exists() or args.output.resolve() == args.source.resolve():
        parser.error("Use a new output path distinct from source")
    if args.execute != args.confirm_paid:
        parser.error("Paid calls require BOTH --execute and --confirm-paid")
    if args.execute and sdk_factory is None and not os.getenv("OPENAI_API_KEY", "").strip():
        parser.error("OPENAI_API_KEY required for live run")
    args.max_total_cost_usd = args.max_new_cost_usd
    try:
        source_bytes = args.source.read_bytes()
        source = json.loads(source_bytes)
        cases, config, snapshot, cache, units, _unused_budget = setup(args)
        _validate_resume(source, cases, config, snapshot, args)
        new_budget = make_budget(args, len(cases))
    except (ValueError, TypeError, KeyError, OSError) as exc:
        parser.error(f"Preflight failed: {type(exc).__name__}: {exc}")
    report = deepcopy(source)
    report["protocol"] = "rv041/qualification-resumed-v3-HF1"
    report["source_paired_report_sha256"] = sha256(source_bytes).hexdigest()
    report["source_paired_report_status"] = source["status"]
    report["source_baseline_costs_are_historical"] = True
    report["hotfix"] = "rv041-hf1/assurance-eligibility-and-inventory-gap"
    report["prompt_and_schema_hashes"] = _hashes()
    report["new_run_budget"] = {"max_new_cost_usd": args.max_new_cost_usd,
                                "per_v3_arm": asdict(new_budget),
                                "v3_arms": len(cases)}
    report["new_run_api_calls"] = 0
    report["new_run_estimated_cost_usd"] = "0"
    report["status"] = "dry_run" if not args.execute else "running"
    for case in cases:
        cid = case["case_id"]
        report["runs"][cid]["v3"] = {"status":"not_rerun_yet", "result":None, "usage":None}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as out:
        def save():
            out.seek(0)
            json.dump(report, out, ensure_ascii=False, indent=2, allow_nan=False)
            out.truncate()
            out.flush()
        save()
        if not args.execute:
            print("V3-only resume preflight passed; 4 historical baselines reused. API calls: 0")
            print("Saved:", args.output)
            return 0
        if sdk_factory is None:
            from openai import OpenAI
            sdk_factory = OpenAI
        halted = False
        try:
            with sdk_factory(timeout=60, max_retries=0) as sdk:
                for case in cases:
                    cid = case["case_id"]
                    report["runs"][cid]["v3"] = {"status":"running", "result":None, "usage":None}
                    save()
                    def checkpoint(value, current=cid):
                        report["runs"][current]["v3"]["result"] = value
                        save()
                    t0 = perf_counter()
                    try:
                        arm = _run_arm("v3", case=case, snapshot=snapshot, cache=cache,
                                       units=units, config=config, budget=new_budget,
                                       sdk=sdk, per_call_output_tokens=args.per_call_output_tokens,
                                       on_result=checkpoint)
                    except Exception as exc:
                        arm = {"status":"execution_failed","error_type":type(exc).__name__,
                               "result":report["runs"][cid]["v3"].get("result"),
                               "usage":None,"elapsed_seconds":round(perf_counter()-t0,4)}
                    report["runs"][cid]["v3"] = arm
                    usage = arm.get("usage") or {}
                    report["new_run_api_calls"] += usage.get("calls",0)
                    from decimal import Decimal
                    report["new_run_estimated_cost_usd"] = str(
                        Decimal(report["new_run_estimated_cost_usd"]) +
                        Decimal(str(usage.get("estimated_cost_usd", "0")))
                    )
                    report["usage_summary"] = cost_and_calls(report)
                    save()
                    print(f"{cid} / v3-only: {arm['status']}", flush=True)
                    if arm["status"] in ("execution_failed", "budget_exceeded"):
                        # Fail fast: do not spend on three more cases after a
                        # newly discovered integration failure in the first.
                        halted = True
                        report["status"] = "halted_after_failure"
                        save()
                        break
        except Exception as exc:
            report.update(status="execution_failed", error_type=type(exc).__name__)
            save()
            print("RV041-HF1 runner error:", type(exc).__name__)
            return 1
        failure = any(report["runs"][c["case_id"]]["v3"]["status"] in
                      ("execution_failed", "budget_exceeded") for c in cases)
        report["status"] = "halted_after_failure" if halted else ("completed_with_failures" if failure else "completed")
        report["usage_summary"] = cost_and_calls(report)
        save()
    print("RV041-HF1:", report["status"], "| NEW calls:", report["new_run_api_calls"],
          "| NEW estimated USD:", report["new_run_estimated_cost_usd"])
    print("Saved:", args.output)
    return 1 if report["status"] != "completed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
