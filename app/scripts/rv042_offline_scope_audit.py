"""Zero-API RV-042 counterfactual relevance experiment from recorded RV-041 data.

Only ORC-001 has a proposed human-review classification. This report does
NOT claim a real RV-042 run, complete source coverage, or factual correctness.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from app.orchestration.v3_planning_contract import ValidatedV3Plan
from app.orchestration.v42_relevance_contract import apply_relevance

QUESTION = "Quais cuidados a política exige antes de compartilhar dados com um fornecedor externo?"
SNAPSHOT = "8ac5dc558483180a93dc9013e1ee4bc8169bcc57938ee32dcfaa533ebb390d70"

# Deliberate hypothesis, NOT labels learned from an evaluator or a proof.
# C8 refers to an additional AI-tool workflow not asked by this general question.
HYPOTHESIS_REQUIREMENTS = {
    "C1": "material", "C2": "material", "C3": "conditional",
    "C4": "conditional", "C5": "conditional", "C6": "conditional",
    "C7": "conditional", "C8": "adjacent", "C9": "conditional",
}
HYPOTHESIS_FACETS = {0: "material", 1: "material", 2: "conditional",
                     3: "conditional", 4: "conditional", 5: "conditional",
                     6: "material", 7: "conditional", 8: "adjacent",
                     9: "adjacent", 10: "adjacent", 11: "conditional"}
HYPOTHESIS_UNRESOLVED = {0: "adjacent", 1: "adjacent"}


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def evaluate(initial, hf2):
    if initial.get("snapshot_id") != SNAPSHOT or hf2.get("snapshot_id") != SNAPSHOT:
        raise ValueError("Unexpected source snapshot. Do not extrapolate frozen hypothesis")
    if initial["input_hashes"] != hf2["input_hashes"]:
        raise ValueError("Input hashes changed between qualification and resumed run")
    if set(initial["runs"]) != {"ORC-001","ORC-002","ORC-003","ORC-004"}:
        raise ValueError("Unexpected original development cohort")
    if hf2["questions"].get("ORC-001") != QUESTION:
        raise ValueError("Frozen question mismatch")
    old = hf2["runs"]["ORC-001"]["v3"]["result"]
    raw_plan = old["plan"]
    inventory = old["inventory"]
    if not raw_plan or not inventory:
        raise ValueError("Historical plan/inventory missing")
    p = ValidatedV3Plan(tuple(raw_plan["items"]), raw_plan["action"], raw_plan["has_known_gap"])
    active_ids = {x["requirement_id"] for x in p.items if x["relevance"] != "out_of_scope"}
    if active_ids != set(HYPOTHESIS_REQUIREMENTS):
        raise ValueError("Frozen ORC-001 plan changed; classification invalid")
    if len(inventory["facets"]) != len(HYPOTHESIS_FACETS) or len(inventory["unresolved_facets"]) != len(HYPOTHESIS_UNRESOLVED):
        raise ValueError("Frozen inventory changed; classification invalid")
    hypothesis = {
        "requirements": [{"requirement_id": rid, "classification": cls,
                          "reason": "Human-review hypothesis: answer the general sharing question without requiring an unasked AI-tool approval workflow"}
                         for rid,cls in HYPOTHESIS_REQUIREMENTS.items()],
        "facets": [{"index": i, "classification": cls,
                    "reason": "Human-review scope hypothesis against the frozen user question"}
                   for i,cls in HYPOTHESIS_FACETS.items()],
        "unresolved": [{"index": i, "classification": cls,
                         "reason": "The general question requests policy safeguards, not detailed external-approval procedures"}
                       for i,cls in HYPOTHESIS_UNRESOLVED.items()],
        "blocking_questions": [],
        "rationale": "Counterfactual scope hypothesis for a general policy-safeguards question, not a factual verdict",
    }
    scoped = apply_relevance(json.dumps(hypothesis,ensure_ascii=False),plan=p,inventory=inventory)
    sample = {}
    for cid,pair in initial["runs"].items():
        sample[cid] = {"baseline_status":pair["baseline"]["status"],
                       "historical_v3_status":pair["v3"]["status"],
                       "hypothesis_assessed": cid=="ORC-001"}
    return {
        "experiment":"RV-042", "status":"offline_counterfactual_only",
        "no_api_calls":True,"source_snapshot_id":SNAPSHOT,
        "semantic_review":"human_review_required_not_ground_truth",
        "cases":sample,
        "ORC-001_hypothesis":{
            "original_in_scope_count":len(active_ids),
            "material_ids":scoped.audit["material_requirements"],
            "adjacent_ids":scoped.audit["adjacent_requirements"],
            "excluded_unresolved": [x["index"] for x in scoped.audit["unresolved_classifications"]
                                    if x["classification"]=="adjacent"],
            "all_retained_plan_requirements_have_validated_source_status":not scoped.plan.has_known_gap,
            "suggested_answerable_by_source_status_only":scoped.audit["sufficient_on_current_evidence"],
            "actual_RV042_generation_or_assurance_performed":False,
            "warning":"Scope labels are a hypothesis. Real RV-042 relevance, assurance, generation and final suppression review were NOT run.",
        },
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial",type=Path,default=Path("docs/validation/RV041_DEV_LIVE_local.json"))
    parser.add_argument("--hf2",type=Path,default=Path("docs/validation/RV041_DEV_V3_HF2_LIVE_local.json"))
    parser.add_argument("--output",type=Path,default=Path("docs/validation/RV042_SCOPE_COUNTERFACTUAL_local.json"))
    args=parser.parse_args(argv)
    if args.output.exists() or args.output.resolve() in {args.initial.resolve(),args.hf2.resolve()}:
        parser.error("Output must be a fresh path distinct from inputs")
    initial=json.loads(args.initial.read_text(encoding="utf-8"))
    hf2=json.loads(args.hf2.read_text(encoding="utf-8"))
    report=evaluate(initial,hf2)
    report["source_hashes"]={"initial":file_hash(args.initial),"hf2":file_hash(args.hf2)}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False)
    print("RV-042 offline counterfactual: material=%s adjacent=%s, API calls=0" % (
        len(report["ORC-001_hypothesis"]["material_ids"]),
        len(report["ORC-001_hypothesis"]["adjacent_ids"])))
    print("This is NOT proof of semantic correctness or a live RV-042 result")
    print("Saved:",args.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
