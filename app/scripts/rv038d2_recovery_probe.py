"""RV-038D2A: audited lexical recovery from a verified source snapshot.

No LLM, no embeddings call, no generated answer, no snapshot merging.
The synthetic challenge remains an external counterfactual fixture.
"""
import json
from pathlib import Path

from app.chunking.evidence_snapshot import verify_snapshot
from app.retrieval.lexical_index import BM25LexicalIndex
from app.retrieval.lexical_query_filter import filter_lexical_query


def inspect_recovery(snapshot, challenge, original, *, top_k=20):
    if type(top_k) is not int or not 1 <= top_k <= 40:
        raise ValueError("Invalid retrieval budget")

    if challenge.get("status") != "assessment_recorded":
        raise ValueError("Completed challenge assessment required")

    decision = challenge.get("decision") or {}
    if decision.get("decision") != "RETRIEVE_MORE":
        raise ValueError("Recovery was not requested")

    lookup = decision.get("lookup") or {}
    if lookup.get("kind") != "search":
        raise ValueError("Only search recovery supported")

    if "C7" not in lookup.get("target_requirement_ids", []):
        raise ValueError("Expected C7 recovery challenge")

    source_plan = original.get("result", original)
    if source_plan.get("status") != "planned_pending_review":
        raise ValueError("Original planner result required")

    if source_plan["snapshot_id"] != snapshot["snapshot_id"]:
        raise ValueError("Original planner/snapshot mismatch")

    if challenge["snapshot_id"] == snapshot["snapshot_id"]:
        raise ValueError("Synthetic and canonical snapshots must differ")

    if not challenge["snapshot_id"].startswith(
        "synthetic-rv038c3-"
    ):
        raise ValueError("Unrecognized synthetic provenance")

    units = verify_snapshot(snapshot)
    catalog = {u.unit_id: u for u in units}

    original_evidence = source_plan["bundle"]["evidence"]
    targets = [
        e["unit_id"] for e in original_evidence
        if "Exceptions require documented business justification"
        in e.get("reading_text", "")
    ]

    if len(targets) != 1:
        raise ValueError("Expected one original exception evidence unit")

    target = targets[0]
    if target not in catalog:
        raise ValueError("Original evidence absent from canonical catalog")

    original_unit = catalog[target]
    reference = next(
        e for e in original_evidence if e["unit_id"] == target
    )

    if (
        reference["reading_text"] != original_unit.reading_text
        or reference["document_id"] != original_unit.document_id
        or original_unit.status != "ready"
    ):
        raise ValueError("Original evidence differs from verified snapshot")

    candidates = tuple(
        u for u in units if u.searchable and u.status == "ready"
    )

    index = BM25LexicalIndex()
    index.add(
        [u.unit_id for u in candidates],
        [u.search_text for u in candidates],
    )

    query = lookup["query"]
    filtered = filter_lexical_query(query)

    hits = index.search(filtered, top_k=top_k) if filtered else ()
    ranked = [hit.chunk_id for hit in hits]
    rank = ranked.index(target) + 1 if target in ranked else None

    return {
        "experiment": "RV-038D2A",
        "status": "offline_recovery_probe_complete",
        "source_snapshot_id": snapshot["snapshot_id"],
        "synthetic_snapshot_id": challenge["snapshot_id"],
        "provenance_mode": "separate_snapshots_no_merge",
        "query": query,
        "lexical_query": filtered,
        "top_k": top_k,
        "target_requirement": "C7",
        "canonical_target_id": target,
        "canonical_document_id": original_unit.document_id,
        "canonical_target_verified": True,
        "searchable_units": len(candidates),
        "retrieved_ids": ranked,
        "target_rank": rank,
        "target_hit": rank is not None,
        "api_calls": 0,
        "limitation": (
            "Lexical-only diagnostic; not a full hybrid retrieval "
            "or successful replan/reassessment demonstration."
        ),
    }


def main():
    base = Path("docs/validation")
    snapshot = json.loads(
        (base / "EVIDENCE_UNITS_SNAPSHOT_local.json")
        .read_text(encoding="utf-8")
    )
    original = json.loads(
        (base / "EVIDENCE_PLANNER_ORC001_GPT61SOL_RESULTS_local.json")
        .read_text(encoding="utf-8")
    )
    challenge = json.loads(
        (base / "rv038c3_scenarios"
         / "RV038C3_MISSING_EXCEPTION_LIVE_local.json")
        .read_text(encoding="utf-8")
    )

    report = inspect_recovery(snapshot, challenge, original)
    output = base / "RV038D2A_RECOVERY_PROBE_local.json"

    with output.open("x", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)

    print("Status:", report["status"])
    print("Canonical target verified:", report["canonical_target_verified"])
    print("Lexical query:", report["lexical_query"])
    print("Target hit:", report["target_hit"])
    print("Target rank:", report["target_rank"])
    print("Retrieved count:", len(report["retrieved_ids"]))
    print("API calls:", report["api_calls"])
    print("Report:", output)


if __name__ == "__main__":
    main()
