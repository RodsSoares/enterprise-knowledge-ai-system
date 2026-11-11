"""Frozen-case and blind human-review protocol for RV-041.

This module is independent of LLM providers and source-dependent model code.
A deterministic result is NOT a semantic quality grade. Human source review is
required; expected answers must never enter the runtime prompts.
"""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path
import re

PROTOCOL = "rv041/qualification-1"
RUBRIC = (
    "material_facet_coverage", "claim_grounding", "citation_accuracy",
    "scope_discipline", "condition_fidelity", "outcome_appropriateness",
)
REVIEW_FIELDS = (
    "case_id", "cohort", "blind_arm", "outcome", "answer_for_review",
    "cited_evidence_for_review", *RUBRIC, "critical_error", "reviewer_notes",
)


class ProtocolError(ValueError):
    pass


def load_cases(path):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or set(raw) != {"protocol", "cases"} or raw["protocol"] != PROTOCOL:
        raise ProtocolError("Invalid frozen-case contract")
    cases = raw["cases"]
    if not isinstance(cases, list) or not 1 <= len(cases) <= 40:
        raise ProtocolError("Expected 1..40 frozen cases")
    names = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {"case_id", "cohort", "question"}:
            raise ProtocolError("Unexpected frozen-case fields")
        case_id, cohort, question = case["case_id"], case["cohort"], case["question"]
        if (not isinstance(case_id, str) or not re.fullmatch(r"[A-Z][A-Z0-9-]{2,30}", case_id)
                or case_id in names or cohort not in ("development", "safety")
                or not isinstance(question, str) or not question.strip() or len(question) > 4000):
            raise ProtocolError("Invalid or repeated case identity")
        names.add(case_id)
    return cases


def select_cases(cases, cohort):
    if cohort not in ("development", "safety", "all"):
        raise ProtocolError("Invalid cohort")
    chosen = [case for case in cases if cohort == "all" or case["cohort"] == cohort]
    if not chosen:
        raise ProtocolError("No cases in selected cohort")
    return chosen


def blinded_labels(snapshot_id, case_id):
    # Deterministic pseudo-blinding; mapping saved separately. Not guaranteed balanced.
    checksum = sha256(f"{snapshot_id}|{case_id}|rv041".encode("utf-8")).digest()[0]
    return {"baseline": "A", "v3": "B"} if checksum % 2 == 0 else {"baseline": "B", "v3": "A"}


def _csv_safe(s):
    if not isinstance(s, str):
        s = str(s)
    return "'" + s if s.lstrip().startswith(("=", "+", "-", "@")) else s


def _answer_and_sources(arm, result, catalog):
    if not isinstance(result, dict):
        return "", ""
    answer = result.get("answer")
    if not isinstance(answer, dict) or answer.get("status") != "answered":
        return "", ""
    raw_claims = answer.get("claims", [])
    if not isinstance(raw_claims, list):
        raise ProtocolError("Malformed claims")
    evidence_by_cite = {}
    if arm == "baseline":
        bundle = (result.get("generation_request") or {}).get("bundle") or {}
        for e in bundle.get("evidence", []):
            unit = catalog.get(e["unit_id"])
            if unit is None or unit.reading_text != e["reading_text"]:
                raise ProtocolError("Baseline evidence differs from canonical snapshot")
            evidence_by_cite[e["citation_id"]] = (e["unit_id"], e["reading_text"])
    else:
        for unit_id, unit in catalog.items():
            evidence_by_cite[unit_id] = (unit_id, unit.reading_text)
    # Both arms receive anonymous, consistent citation labels in reviewer material.
    labels, rendered = {}, []
    for claim in raw_claims:
        refs = claim.get("citation_ids", [])
        if not isinstance(refs, list) or not refs:
            raise ProtocolError("Malformed claim citations")
        aliases = []
        for ref in refs:
            if ref not in evidence_by_cite:
                raise ProtocolError("Cannot resolve cited source in reviewer packet")
            if ref not in labels:
                labels[ref] = "S" + str(len(labels) + 1)
            aliases.append(labels[ref])
        rendered.append(f"{claim['text']} [{', '.join(aliases)}]")
    excerpts = []
    for ref, label in labels.items():
        source_id, source_text = evidence_by_cite[ref]
        # Do NOT include unit IDs or source type hints that reveal the arm.
        excerpts.append(f"[{label}] {source_text}")
    return "\n".join(rendered), "\n\n".join(excerpts)


def build_review_rows(report, cases, catalog):
    if report.get("status") not in ("completed", "completed_with_failures"):
        raise ProtocolError("Run must be executed before preparing reviews")
    rows, mappings = [], []
    for case in cases:
        case_id = case["case_id"]
        results = report.get("runs", {}).get(case_id)
        if not isinstance(results, dict) or set(results) != {"baseline", "v3"}:
            raise ProtocolError("Paired baseline/v3 runs required")
        labels = blinded_labels(report["snapshot_id"], case_id)
        for arm in ("baseline", "v3"):
            run = results[arm]
            result = run.get("result")
            answer, sources = _answer_and_sources(arm, result, catalog)
            status = run.get("status", "missing")
            normalized = ("answered" if status in ("answered_pending_review", "answered_pending_human_review")
                          else "abstained" if status == "abstained"
                          else "no_answer_or_rejected")
            row = {"case_id": case_id, "cohort": case["cohort"],
                   "blind_arm": labels[arm], "outcome": normalized,
                   "answer_for_review": _csv_safe(answer),
                   "cited_evidence_for_review": _csv_safe(sources),
                   "critical_error": "", "reviewer_notes": ""}
            row.update({field: "" for field in RUBRIC})
            rows.append(row)
            mappings.append({"case_id": case_id, "blind_arm": labels[arm], "runtime_arm": arm})
    rows.sort(key=lambda row: (row["case_id"], row["blind_arm"]))
    mappings.sort(key=lambda row: (row["case_id"], row["blind_arm"]))
    return rows, mappings


def save_review_packet(report, cases, catalog, *, template_path, mapping_path):
    template_path, mapping_path = Path(template_path), Path(mapping_path)
    if template_path.resolve() == mapping_path.resolve():
        raise ProtocolError("Distinct reviewer and mapping files required")
    if template_path.exists() or mapping_path.exists():
        raise ProtocolError("Review output exists: use new filenames")
    rows, mapping = build_review_rows(report, cases, catalog)
    template_path.parent.mkdir(parents=True, exist_ok=True)
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    with template_path.open("x", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    mapping_path.write_text(json.dumps({"protocol": PROTOCOL, "mapping": mapping},
                                       ensure_ascii=False, indent=2), encoding="utf-8")
    return len(rows)


def score_review_packet(reviewed_csv, mapping_path):
    mapping = json.loads(Path(mapping_path).read_text(encoding="utf-8"))
    if set(mapping) != {"protocol", "mapping"} or mapping["protocol"] != PROTOCOL:
        raise ProtocolError("Invalid mapping")
    identity = {(r["case_id"], r["blind_arm"]): r["runtime_arm"] for r in mapping["mapping"]}
    if len(identity) != len(mapping["mapping"]):
        raise ProtocolError("Duplicate mapping identity")
    with Path(reviewed_csv).open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not set(REVIEW_FIELDS).issubset(reader.fieldnames or ()):
            raise ProtocolError("Missing reviewer columns")
        rows = list(reader)
    seen, reviewed, missing = set(), [], []
    for row in rows:
        key = (row["case_id"], row["blind_arm"])
        if key in seen or key not in identity:
            raise ProtocolError("Unknown/duplicate review row")
        seen.add(key)
        scores = {}
        ready = True
        for name in RUBRIC:
            val = row[name].strip()
            if val not in ("0", "1", "2"):
                ready = False
            else:
                scores[name] = int(val)
        critical = row["critical_error"].strip().lower()
        if critical not in ("yes", "no"):
            ready = False
        if ready:
            reviewed.append({"case_id": key[0], "arm": identity[key],
                             "points": sum(scores.values()), "scores": scores,
                             "critical_error": critical == "yes"})
        else:
            missing.append({"case_id": key[0], "blind_arm": key[1]})
    if seen != set(identity):
        raise ProtocolError("Review file is missing paired rows")
    summary = {"protocol": PROTOCOL, "status": "complete" if not missing else "review_incomplete",
               "expected_rows": len(identity), "reviewed_rows": len(reviewed),
               "unreviewed": missing, "arms": {}, "paired_case_comparison": []}
    for arm in ("baseline", "v3"):
        selected = [r for r in reviewed if r["arm"] == arm]
        summary["arms"][arm] = {
            "reviewed": len(selected), "mean_score_out_of_12":
                round(sum(r["points"] for r in selected) / len(selected), 3) if selected else None,
            "critical_errors": sum(r["critical_error"] for r in selected),
        }
    paired = {}
    for item in reviewed:
        paired.setdefault(item["case_id"], {})[item["arm"]] = item
    for case_id, data in sorted(paired.items()):
        if set(data) == {"baseline", "v3"}:
            summary["paired_case_comparison"].append({
                "case_id": case_id,
                "v3_minus_baseline_points": data["v3"]["points"] - data["baseline"]["points"],
                "v3_critical_error": data["v3"]["critical_error"],
                "baseline_critical_error": data["baseline"]["critical_error"],
            })
    return summary


def cost_and_calls(report):
    total, calls = Decimal(0), 0
    per_arm = {"baseline": {"calls": 0, "cost_usd": Decimal(0)},
               "v3": {"calls": 0, "cost_usd": Decimal(0)}}
    for case in report.get("runs", {}).values():
        for arm, run in case.items():
            usage = run.get("usage")
            if not usage:
                continue
            try:
                cost = Decimal(str(usage["estimated_cost_usd"]))
                if not cost.is_finite() or cost < 0:
                    raise ProtocolError("Invalid usage cost")
            except (InvalidOperation, KeyError, TypeError) as exc:
                raise ProtocolError("Invalid usage report") from exc
            count = usage["calls"]
            if type(count) is not int or count < 0:
                raise ProtocolError("Invalid usage calls")
            total += cost
            calls += count
            per_arm[arm]["calls"] += count
            per_arm[arm]["cost_usd"] += cost
    return {"estimated_total_cost_usd": str(total), "total_api_calls": calls,
            "by_arm": {arm: {"calls": val["calls"], "estimated_cost_usd": str(val["cost_usd"])}
                       for arm, val in per_arm.items()}}
