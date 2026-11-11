"""RV-041: deterministic replay of previously paid V3 assurance decisions.

No API calls; projects only planner-excluded rows out of the old response,
reflecting the new model request boundary. Not an accuracy benchmark.
"""
import argparse
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path

from app.chunking.evidence_snapshot import verify_snapshot, file_hash
from app.orchestration.v3_semantic_contracts import validate_assurance


@dataclass(frozen=True)
class SavedPlan:
    items: tuple
    has_known_gap: bool


def replay(saved, snapshot, units):
    if saved.get("input_hashes", {}).get("snapshot") != file_hash(snapshot):
        raise ValueError("RV-041 report and snapshot file do not match")
    if saved.get("snapshot_id") != units["snapshot_id"]:
        raise ValueError("RV-041 report snapshot identity mismatch")
    canonical = {u.unit_id: u for u in units["units"]}
    doc_ids = tuple(sorted({u.document_id for u in units["units"]}))
    results = {}
    for case, pair in saved["runs"].items():
        arm = pair["v3"]
        state = arm["result"]
        if arm["status"] != "execution_failed" or state.get("error_type") != "V3SemanticError":
            raise ValueError("Replay expects the recorded assurance failure for " + case)
        trace = state["trace"]
        if not any(t.get("stage") == "request_assurance_v3" for t in trace):
            raise ValueError("No completed assurance request for " + case)
        if trace[-1]["stage"] != "error":
            raise ValueError("Failure stage changed for " + case)
        selected = next(t for t in trace if t.get("stage") == "initial_retrieval")["selected_ids"]
        candidates = tuple(canonical[i] for i in selected)
        plan = SavedPlan(tuple(state["plan"]["items"]), state["plan"]["has_known_gap"])
        exclude = {x["requirement_id"] for x in plan.items if x["relevance"] == "out_of_scope"}
        active = {x["requirement_id"] for x in plan.items if x["relevance"] != "out_of_scope"}
        events = arm["usage"]["events"]
        raw = next((e["raw_output"] for e in reversed(events)
                    if e.get("kind") == "responses" and e.get("status") == "completed"
                    and e.get("raw_output")), None)
        if not raw:
            raise ValueError("Saved assurance response missing for " + case)
        decision = json.loads(raw)
        existing = {x["requirement_id"] for x in decision["requirements"]}
        if existing != (exclude | active):
            raise ValueError("Unexpected original requirement IDs for " + case)
        # Counterfactual projection: discard ONLY the rows that the revised
        # assurance stage no longer requests. Retain every active model verdict,
        # lookup, citation, omission and final decision completely unchanged.
        decision = deepcopy(decision)
        decision["requirements"] = [row for row in decision["requirements"]
                                    if row["requirement_id"] not in exclude]
        requested_docs = tuple(state["scope"].get("document_ids", []))
        outcome = validate_assurance(json.dumps(decision, ensure_ascii=False),
                                     plan=plan, inventory=state["inventory"],
                                     candidates=candidates, recovery_used=False,
                                     allowed_document_ids=requested_docs or doc_ids)
        results[case] = dict(structural_replay="pass", decision=outcome["decision"],
                             removed_exclusion_rows=sorted(exclude),
                             active_requirement_count=len(active),
                             unresolved_facets=len(state["inventory"]["unresolved_facets"]),
                             legacy_failure_type=state["error_type"])
    return dict(experiment="RV-041-HF1", status="offline_assurance_projection_complete",
                original_status=saved["status"], model=saved["model"],
                source_snapshot_id=saved["snapshot_id"],
                paid_calls=0,
                qualification="STRUCTURAL_ONLY_NOT_END_TO_END_NOT_SEMANTIC_PROOF",
                results=results)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=Path("docs/validation/RV041_DEV_LIVE_local.json"))
    ap.add_argument("--snapshot", type=Path, default=Path("docs/validation/EVIDENCE_UNITS_SNAPSHOT_local.json"))
    ap.add_argument("--output", type=Path, default=Path("docs/validation/RV041_HF1_ASSURANCE_REPLAY_local.json"))
    args = ap.parse_args(argv)
    if args.output.exists() or args.output.resolve() in {args.input.resolve(), args.snapshot.resolve()}:
        ap.error("Use a new distinct output path")
    source = json.loads(args.input.read_text(encoding="utf-8"))
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    units = verify_snapshot(snapshot, root=Path.cwd())
    result = replay(source, args.snapshot, {"snapshot_id":snapshot["snapshot_id"], "units": units})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as out:
        json.dump(result,out,ensure_ascii=False,indent=2)
    for case, summary in result["results"].items():
        print(f"{case}: {summary['decision']} | projected valid | excluded rows={len(summary['removed_exclusion_rows'])}")
    print("No API calls. Saved:", args.output)


if __name__ == "__main__":
    main()
