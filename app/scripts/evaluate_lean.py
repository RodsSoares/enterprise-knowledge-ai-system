"""Run the lean pipeline over the answer criteria and score it deterministically.

Dry run by default: lists what would run and the cost ceiling, with no API
call. Paid execution needs --execute and --confirm-paid. --score-only rescores
a saved report with the current criteria at no cost. --retrieval-only measures
whether the documents an answer must cite reach the candidate list, using
embedding calls only.

Scoring is string matching against data/ground_truth/answer_criteria.yaml. It
is a reproducible lower bound, not a semantic certification.
"""
import argparse
from dataclasses import asdict
from decimal import Decimal
import json
import os
from pathlib import Path

from app.chunking.evidence_snapshot import verify_snapshot
from app.evaluation.answer_criteria import (
    DEFAULT_CRITERIA_PATH, load_criteria, score, summarize,
)
from app.orchestration.evidence_pipeline import validate_inputs
from app.orchestration.lean_live_provider import LeanLiveProvider
from app.orchestration.lean_pipeline import DEFAULT_TOP_K, VERSION, run_lean
from app.orchestration.live_provider import BudgetedClient, RunBudget
from app.retrieval.adaptive_evidence_retriever import AdaptiveEvidenceUnitRetriever
from app.retrieval.openai_embeddings import OpenAIEmbeddingProvider
from app.scripts.compare_stage1_orchestration import load_config


def select_cases(cases, wanted, available_documents):
    """Split cases into those the snapshot can answer and those it cannot."""
    if wanted:
        known = {c.case_id for c in cases}
        missing = [w for w in wanted if w not in known]
        if missing:
            raise ValueError("Unknown case ids: " + ", ".join(missing))
        cases = [c for c in cases if c.case_id in wanted]
    runnable, skipped = [], []
    for case in cases:
        absent = sorted({d for group in case.cite
                         if not set(group) & available_documents for d in group})
        if absent:
            skipped.append({"case_id": case.case_id,
                            "reason": "snapshot lacks " + ", ".join(absent)})
        else:
            runnable.append(case)
    return runnable, skipped


def retrieval_coverage(case, units):
    """Which citation groups of a case are present among retrieved units."""
    found = {u.document_id for u in units}
    groups = [bool(found & set(group)) for group in case.cite]
    return {"case_id": case.case_id, "groups": len(groups), "groups_found": sum(groups),
            "complete": all(groups), "retrieved_documents": sorted(found)}


def print_summary(summary, skipped):
    print(f"\nCasos: {summary['cases']} | execuções: {summary['runs']} | "
          f"aprovadas: {summary['runs_passed']}")
    print(f"Sempre aprovados: {summary['cases_always_passed']} | nunca: "
          f"{summary['cases_never_passed']} | instáveis: {summary['cases_unstable']}")
    for row in summary["by_case"]:
        mark = "OK  " if row["passed"] == row["runs"] else ("FAIL" if row["passed"] == 0 else "VAR ")
        print(f"  {mark} {row['case_id']:<8} {row['passed']}/{row['runs']} "
              f"{','.join(row['outcomes'])}" + (" | " + "; ".join(row["failures"]) if row["failures"] else ""))
    for item in skipped:
        print(f"  SKIP {item['case_id']:<8} {item['reason']}")


def main(argv=None, *, sdk_factory=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--snapshot", type=Path, default=Path("docs/validation/EVIDENCE_UNITS_SNAPSHOT_27DOC.json"))
    p.add_argument("--embedding-cache", type=Path, default=Path("docs/validation/EVIDENCE_UNIT_EMBEDDINGS_27DOC.json"))
    p.add_argument("--config", type=Path, default=Path("docs/validation/STAGE1_RUN_CONFIG_local.json"))
    p.add_argument("--criteria", type=Path, default=DEFAULT_CRITERIA_PATH)
    p.add_argument("--cases", help="Comma-separated case ids; default is every case")
    p.add_argument("--repeats", type=int, default=1, help="Runs per case, to measure stability")
    p.add_argument("--model", help="Defaults to the generation model in the config")
    p.add_argument("--input-price", help="USD per million input tokens for --model")
    p.add_argument("--output-price", help="USD per million output tokens for --model")
    p.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    p.add_argument("--on-incomplete", choices=("flag", "withhold"), default="flag")
    p.add_argument("--expand-documents", type=int, choices=range(0, 7), default=3)
    p.add_argument("--max-cost-per-run-usd", default="0.30")
    p.add_argument("--max-total-cost-usd", default="0.50",
                   help="Hard ceiling for the whole batch (default: 0.50)")
    p.add_argument("--max-per-call-output-tokens", type=int, default=4500)
    p.add_argument("--deadline-seconds", type=int, default=300)
    p.add_argument("--retrieval-only", action="store_true")
    p.add_argument("--score-only", type=Path, help="Rescore a saved report; no API call")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--execute", action="store_true")
    p.add_argument("--confirm-paid", action="store_true")
    a = p.parse_args(argv)
    if a.output.exists():
        p.error("Output exists; choose a new path to preserve prior evidence")
    try:
        cases = load_criteria(a.criteria)
        wanted = [c.strip() for c in a.cases.split(",") if c.strip()] if a.cases else []
        if a.score_only:
            saved = json.loads(a.score_only.read_text(encoding="utf-8"))
            by_id = {c.case_id: c for c in cases}
            scores = [score(by_id[run["case_id"]], run["result"]) for run in saved["runs"]
                      if run["case_id"] in by_id and (not wanted or run["case_id"] in wanted)]
            report = {"experiment": "LEAN-EVAL-RESCORE", "source": str(a.score_only),
                      "scores": scores, "summary": summarize(scores), "skipped": saved.get("skipped", [])}
            a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print_summary(report["summary"], report["skipped"])
            return 0
        if a.execute != a.confirm_paid:
            raise ValueError("Paid run requires BOTH --execute and --confirm-paid")
        if (a.input_price is None) != (a.output_price is None):
            raise ValueError("Provide both model price overrides or neither")
        if type(a.repeats) is not int or not 1 <= a.repeats <= 10:
            raise ValueError("Repeats must be between 1 and 10")
        config, _ = load_config(a.config)
        snapshot = json.loads(a.snapshot.read_text(encoding="utf-8"))
        units = verify_snapshot(snapshot, root=Path.cwd())
        cache = json.loads(a.embedding_cache.read_text(encoding="utf-8"))
        vectors = validate_inputs(snapshot, cache, config, "preflight")[1]
        model = a.model or config["models"]["generation"]
        prices = dict(config["prices"])
        if a.input_price is not None:
            prices[model] = {"input_per_million": str(Decimal(a.input_price)),
                             "output_per_million": str(Decimal(a.output_price))}
        if model not in prices:
            raise ValueError("Model pricing missing; pass both price overrides")
        runnable, skipped = select_cases(cases, wanted, {u.document_id for u in units})
        if not runnable:
            raise ValueError("No runnable case for this snapshot")
        metadata = {d["document_id"]: {**d["metadata"], "as_of": config["as_of"]}
                    for d in snapshot["snapshot"]["documents"]}
        total_cap = Decimal(str(a.max_total_cost_usd))
        if a.execute and sdk_factory is None and not os.getenv("OPENAI_API_KEY", "").strip():
            raise ValueError("OPENAI_API_KEY environment variable is required")
    except (ValueError, KeyError, TypeError, OSError, ArithmeticError) as exc:
        p.error("Preflight failed: " + type(exc).__name__ + ": " + str(exc))

    planned = len(runnable) * (1 if a.retrieval_only else a.repeats)
    report = {"experiment": "LEAN-RETRIEVAL" if a.retrieval_only else "LEAN-EVAL",
              "status": "dry_run", "version": VERSION, "snapshot_id": snapshot["snapshot_id"],
              "documents": len(snapshot["snapshot"]["documents"]),
              "models": {"embedding": config["models"]["embedding"], "generation": model},
              "top_k": a.top_k, "on_incomplete": a.on_incomplete,
              "expand_documents": a.expand_documents, "repeats": a.repeats,
              "planned_runs": planned, "max_total_cost_usd": str(total_cap),
              "skipped": skipped, "runs": [], "scores": [], "summary": None,
              "retrieval": [], "estimated_cost_usd": "0"}

    def save():
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False),
                            encoding="utf-8")

    if not a.execute:
        save()
        # Measured on RV-044 runs: about 6,000 input and 1,500 output tokens per run.
        rates = prices[model]
        estimate = planned * (Decimal(6000) * Decimal(str(rates["input_per_million"]))
                              + Decimal(1500) * Decimal(str(rates["output_per_million"]))) / 1000000
        print(f"Dry run: {len(runnable)} casos executáveis, {len(skipped)} fora do snapshot, "
              f"{planned} execuções, até {planned * 3} chamadas.")
        print(f"Estimativa: ~{planned * 6000:,} tokens de entrada, ~{planned * 1500:,} de saída, "
              f"~USD {estimate:.2f} com {model}. Teto configurado: USD {total_cap}. "
              "Nenhuma chamada paga.")
        for item in skipped:
            print(f"  SKIP {item['case_id']:<8} {item['reason']}")
        return 0

    if sdk_factory is None:
        from openai import OpenAI
        sdk_factory = OpenAI
    spent = Decimal(0)
    query_cache = {}
    report["status"] = "running"
    with sdk_factory(timeout=60, max_retries=0) as sdk:
        for case in runnable:
            for repeat in range(1 if a.retrieval_only else a.repeats):
                if spent >= total_cap:
                    report["status"] = "stopped_total_budget"
                    break
                budget = RunBudget(200000, 24000, 6, a.deadline_seconds,
                                   str(min(Decimal(str(a.max_cost_per_run_usd)), total_cap - spent)))
                client = BudgetedClient(sdk, budget, prices, transport_retries=2)
                retriever = AdaptiveEvidenceUnitRetriever(
                    units, vectors, OpenAIEmbeddingProvider(client, model=config["models"]["embedding"]))
                retriever.query_cache = query_cache
                try:
                    if a.retrieval_only:
                        found, _ = retriever.search(case.question, (), a.top_k)
                        report["retrieval"].append(retrieval_coverage(case, found))
                    else:
                        result = run_lean(
                            case.question, snapshot_id=snapshot["snapshot_id"], units=units,
                            retriever=retriever,
                            provider=LeanLiveProvider(client, model, a.max_per_call_output_tokens),
                            document_metadata=metadata, top_k=a.top_k,
                            on_incomplete=a.on_incomplete,
                            expand_documents=a.expand_documents)
                        usage = client.report()
                        for item in usage["events"]:
                            item.pop("raw_output", None)
                        report["runs"].append({"case_id": case.case_id, "repeat": repeat,
                                               "result": result, "usage": usage})
                        report["scores"].append(score(case, result))
                except Exception as exc:  # one failed run must not hide the others
                    failed = {"status": "execution_failed", "error_type": type(exc).__name__,
                              "error_message": str(exc)[:300]}
                    if a.retrieval_only:
                        report["retrieval"].append({"case_id": case.case_id, **failed})
                    else:
                        report["runs"].append({"case_id": case.case_id, "repeat": repeat,
                                               "result": failed, "usage": client.report()})
                        report["scores"].append(score(case, failed))
                spent += Decimal(client.report()["estimated_cost_usd"])
                report["estimated_cost_usd"] = str(spent)
                save()
            else:
                continue
            break
    if report["status"] == "running":
        report["status"] = "complete"
    if a.retrieval_only:
        done = [r for r in report["retrieval"] if "complete" in r]
        print(f"Recuperação top-{a.top_k}: {sum(r['complete'] for r in done)}/{len(done)} casos "
              "com todos os documentos exigidos entre os candidatos")
        for r in done:
            if not r["complete"]:
                print(f"  FALTA {r['case_id']:<8} {r['groups_found']}/{r['groups']} grupos | "
                      + ",".join(r["retrieved_documents"]))
    else:
        report["summary"] = summarize(report["scores"])
        print_summary(report["summary"], skipped)
    save()
    print(f"Custo estimado: USD {spent} | arquivo: {a.output}")
    return 0 if report["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
