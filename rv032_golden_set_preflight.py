"""RV032: deterministic, zero-API-cost Golden Set A corpus preflight.

Run at the project root:
    python rv032_golden_set_preflight.py

The tool reads the project's canonical Golden Set loader and configured smoke
corpus, without parsing files, creating embeddings or invoking any LLM.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from app.evaluation.golden_set_loader import GoldenSetLoader
from tests.smoke.smoke_golden_set_vector_retrieval import (
    SOURCE_PATHS,
    document_id_from_path,
)

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs" / "validation"


def main() -> None:
    golden = GoldenSetLoader(ROOT / "data" / "ground_truth" / "golden_questions.yaml").load()
    declared_sources = [ROOT / source for source in SOURCE_PATHS]
    present_paths = [path for path in declared_sources if path.is_file()]
    missing_paths = [path for path in declared_sources if not path.is_file()]
    present_ids = {document_id_from_path(path) for path in present_paths}
    rows = []
    for entry in golden.classify_for_corpus(present_ids):
        q = entry.question
        if not entry.evaluable:
            classification = "BLOCKED_MISSING_EXPECTED_DOCUMENTS"
        elif not q.expected_evidence:
            classification = "ELIGIBLE_NO_POSITIVE_EVIDENCE"
        else:
            classification = "ELIGIBLE_POSITIVE"
        rows.append({
            "question_id": q.question_id,
            "question": q.question,
            "question_class": q.question_class,
            "retrieval_challenge": q.retrieval_challenge,
            "expected_behavior": q.expected_behavior,
            "expected_evidence": list(q.expected_evidence),
            "distractors": list(q.distractors),
            "missing_expected_documents": list(entry.missing_expected_documents),
            "classification": classification,
            "retrieval_execution_status": "NOT_RUN_PREFLIGHT_ONLY",
            "generation_execution_status": "NOT_RUN_PREFLIGHT_ONLY",
            "semantic_verdict": "NOT_REVIEWED",
        })
    counts = dict(sorted(Counter(row["classification"] for row in rows).items()))
    report = {
        "experiment": "RV032_FULL_GOLDEN_SET_PREFLIGHT",
        "phase": "offline_preflight",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_calls": 0,
        "estimated_api_cost_usd": 0,
        "corpus_source": "tests.smoke.smoke_golden_set_vector_retrieval.SOURCE_PATHS",
        "total_golden_questions": len(rows),
        "declared_source_documents": len(declared_sources),
        "present_source_documents": len(present_paths),
        "present_document_ids": sorted(present_ids),
        "missing_configured_paths": [str(path.relative_to(ROOT)) for path in missing_paths],
        "classification_counts": counts,
        "questions": rows,
        "interpretation": (
            "Eligibility is determined by expected-document presence only; "
            "it does not establish retrieval quality or answer correctness. "
            "This preflight does not run retrieval or generation."
        ),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    stem = "RV032_GOLDEN_SET_PREFLIGHT_local"
    json_path = OUT / f"{stem}.json"
    csv_path = OUT / f"{stem}.csv"
    if json_path.exists() or csv_path.exists():
        raise FileExistsError("RV032 preflight artifacts already exist; no overwrite performed")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "question_id", "classification", "expected_behavior", "expected_evidence",
            "missing_expected_documents", "retrieval_challenge", "question",
        ])
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ",".join(v) if isinstance(v, list) else v for k, v in row.items() if k in writer.fieldnames})
    print("RV032 | Golden Set questions:", len(rows))
    print("Corpus files present:", len(present_paths), "/", len(declared_sources))
    for label, count in counts.items():
        print(f"{label}: {count}")
    for row in rows:
        print(f"{row['question_id']}: {row['classification']}" +
              (f" | missing={','.join(row['missing_expected_documents'])}" if row['missing_expected_documents'] else ""))
    print("JSON:", json_path)
    print("CSV:", csv_path)
    print("API calls: 0 (retrieval and generation NOT executed)")


if __name__ == "__main__":
    main()
