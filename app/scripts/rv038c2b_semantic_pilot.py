"""RV-038C2B: one-question semantic assurance pilot.

Dry-run by default. A live run requires --execute and an explicit budget.
No retrieval, generation, or Golden Set access.
"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path

from app.orchestration.contracts import digest
from app.orchestration.evidence_assurance import (
    AssuranceRequest, validate_assurance,
)
from app.orchestration.semantic_assessor import SemanticAssessor
from app.orchestration.live_semantic_assessor import (
    LiveSemanticAssessor, ASSURANCE_SCHEMA,
    ASSURANCE_INSTRUCTIONS,
)
from app.orchestration.live_provider import (
    BudgetedClient, RunBudget,
)


def extract_planning(data):
    """Accept a planner result or a persisted pipeline envelope."""
    if not isinstance(data, dict):
        raise ValueError("Expected JSON object")
    if (
        data.get("status") == "planned_pending_review"
        and isinstance(data.get("bundle"), dict)
    ):
        return data

    if isinstance(data.get("planning"), dict):
        return extract_planning(data["planning"])

    result = data.get("result")
    if isinstance(result, dict):
        return extract_planning(result)

    raise ValueError("No completed EvidencePlanner result found")


def prepare(planning, *, recovery_used=False, max_chars=24000):
    if planning.get("status") != "planned_pending_review":
        raise ValueError("Planning is not pending review")
    question = planning.get("question")
    bundle = planning.get("bundle")
    if not isinstance(bundle, dict):
        raise ValueError("Missing bundle")
    if bundle.get("snapshot_id") != planning.get("snapshot_id"):
        raise ValueError("Snapshot mismatch")
    if bundle.get("bundle_hash") != digest({
        k: v for k, v in bundle.items() if k != "bundle_hash"
    }):
        raise ValueError("Bundle integrity failure")

    coverage = bundle.get("coverage")
    evidence = bundle.get("evidence")
    if not isinstance(coverage, list) or not coverage:
        raise ValueError("Missing coverage")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("Missing evidence")

    requirement_ids = [item["coverage_id"] for item in coverage]
    evidence_ids = [item["unit_id"] for item in evidence]

    if any(
        not item.get("supports")
        or any(
            s.get("unit_id") not in evidence_ids
            for s in item["supports"]
        )
        for item in coverage
    ):
        raise ValueError("Coverage contains invalid supports")

    request = AssuranceRequest.create(
        question=question,
        snapshot_id=bundle["snapshot_id"],
        requirement_ids=requirement_ids,
        candidate_chunk_ids=evidence_ids,
        recovery_used=recovery_used,
    )

    class Capture:
        payload = None

        def invoke(self, stage, payload):
            if stage != "assurance":
                raise ValueError("Unexpected provider stage")
            self.payload = payload
            return "{}"

    capture = Capture()
    assessor = SemanticAssessor(
        planning_result=planning,
        provider=capture,
        max_chars=max_chars,
    )
    assessor(request)

    return request, capture.payload


def assess_once(planning, provider, *, recovery_used=False,
                max_chars=24000):
    """One provider decision, then deterministic validation.

    RETRIEVE_MORE is recorded, never executed here.
    """
    request, _ = prepare(
        planning, recovery_used=recovery_used,
        max_chars=max_chars,
    )
    raw = SemanticAssessor(
        planning_result=planning,
        provider=provider,
        max_chars=max_chars,
    )(request)
    return validate_assurance(raw, request).payload


def main(argv=None, *, sdk_factory=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model")
    parser.add_argument("--input-price")
    parser.add_argument("--output-price")
    parser.add_argument("--max-cost-usd", default="0.10")
    parser.add_argument("--max-input-tokens", type=int, default=40000)
    parser.add_argument("--max-output-tokens", type=int, default=2500)
    parser.add_argument("--deadline-seconds", type=int, default=120)
    parser.add_argument("--max-context-chars", type=int, default=24000)
    parser.add_argument("--recovery-used", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    if args.input.resolve() == args.output.resolve():
        parser.error("Input and output must be different")
    if args.output.exists():
        parser.error("Output already exists; use a new filename")

    try:
        raw = args.input.read_bytes()
        planning = extract_planning(json.loads(raw.decode("utf-8")))
        request, context = prepare(
            planning,
            recovery_used=args.recovery_used,
            max_chars=args.max_context_chars,
        )
        if args.max_output_tokens < 1 or args.max_output_tokens > 8192:
            raise ValueError("Invalid output token cap")
        budget = None
        prices = None
        if args.execute:
            if not all((
                args.model, args.input_price, args.output_price
            )):
                raise ValueError("Live run requires model and prices")
            budget = RunBudget(
                args.max_input_tokens,
                args.max_output_tokens,
                1,
                args.deadline_seconds,
                args.max_cost_usd,
            )
            prices = {
                args.model: {
                    "input_per_million": args.input_price,
                    "output_per_million": args.output_price,
                }
            }
            BudgetedClient(None, budget, prices)

    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(
            f"Preflight failed: {type(exc).__name__}: {exc}"
        )

    report = {
        "experiment": "RV-038C2B",
        "status": "dry_run",
        "question": planning["question"],
        "snapshot_id": planning["snapshot_id"],
        "input_sha256": sha256(raw).hexdigest(),
        "bundle_hash": planning["bundle"]["bundle_hash"],
        "assurance_request": request.payload,
        "context_hash": digest(context),
        "schema_hash": digest(ASSURANCE_SCHEMA),
        "instructions_hash": digest(ASSURANCE_INSTRUCTIONS),
        "decision": None,
        "usage": None,
        "semantic_review": "unverified",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        def save():
            output.seek(0)
            json.dump(report, output, ensure_ascii=False,
                      indent=2, allow_nan=False)
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
                        raise ValueError("OPENAI_API_KEY not set")
                    from openai import OpenAI
                    sdk_factory = OpenAI

                with sdk_factory(
                    timeout=60, max_retries=0
                ) as sdk:
                    client = BudgetedClient(
                        sdk, budget, prices,
                        checkpoint=lambda usage: (
                            report.update(usage=usage),
                            save(),
                        ),
                    )
                    provider = LiveSemanticAssessor(
                        client, args.model,
                        args.max_output_tokens,
                    )
                    decision = assess_once(
                        planning, provider,
                        recovery_used=args.recovery_used,
                        max_chars=args.max_context_chars,
                    )
                    report["decision"] = decision
                    report["status"] = "assessment_recorded"
            except Exception as exc:
                report["status"] = "execution_failed"
                report["error_type"] = type(exc).__name__
            finally:
                if client is not None:
                    report["usage"] = client.report()
                save()

    print(f"{report['status']}: {args.output}")
    if report["decision"]:
        print("Decision:", report["decision"]["decision"])
        print("Requirements:",
              [(x["requirement_id"], x["status"])
               for x in report["decision"]["requirements"]])
    if report["usage"]:
        print("Calls:", report["usage"]["calls"])
        print("Estimated USD:",
              report["usage"]["estimated_cost_usd"])
    return 1 if report["status"] == "execution_failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
