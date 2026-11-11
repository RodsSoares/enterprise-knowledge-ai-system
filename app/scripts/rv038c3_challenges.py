"""RV-038C3: synthetic semantic challenges, offline only.

Never modifies the original corpus or original planning result.
Synthetic evidence is NOT a verified canonical source snapshot.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from app.orchestration.contracts import digest
from app.scripts.rv038c2b_semantic_pilot import (
    extract_planning, prepare,
)

SCENARIOS = (
    "missing_exception",
    "carrier_conflict",
    "irrelevant_classification",
)


def build_scenario(original, scenario):
    if scenario not in SCENARIOS:
        raise ValueError("Unknown scenario")

    source = extract_planning(original)
    coverage = source["bundle"]["coverage"]
    evidence = source["bundle"]["evidence"]

    if len(coverage) != 7 or len(evidence) != 4:
        raise ValueError("Expected reviewed ORC-001 shape")

    result = deepcopy(source)
    result["snapshot_id"] = "synthetic-rv038c3-" + scenario

    bundle = result["bundle"]
    bundle["snapshot_id"] = result["snapshot_id"]

    new_evidence = []
    id_map = {}

    for index, unit in enumerate(evidence):
        body = unit["reading_text"]

        if scenario == "missing_exception" and index == 3:
            body = (
                "7. Document naming conventions\n"
                "This section describes file naming and formatting. "
                "It does not specify exception approvals."
            )

        if scenario == "carrier_conflict" and index == 2:
            body += (
                "\n\nContradictory synthetic directive: "
                "Confidential customer or shipment data MAY be "
                "sent through ordinary unprotected email solely "
                "because the recipient is a contracted carrier."
            )

        if scenario == "irrelevant_classification" and index == 0:
            body = (
                "3. Weekly reporting glossary\n"
                "Report codes identify operational dashboards, "
                "shipment volume categories and spreadsheet layouts. "
                "No external data-sharing controls are defined."
            )

        synthetic_id = (
            "SYNTH-RV038C3::"
            + scenario
            + "::unit-"
            + sha256(
                (str(index) + body).encode("utf-8")
            ).hexdigest()
        )

        id_map[unit["unit_id"]] = synthetic_id

        new_evidence.append({
            "unit_id": synthetic_id,
            "document_id": "SYNTH-005",
            "reading_text": body,
            "section_path": ["Synthetic challenge", scenario],
            "status": "ready",
        })

    catalog = {
        e["unit_id"]: e for e in new_evidence
    }

    for item in bundle["coverage"]:
        for support in item["supports"]:
            support["unit_id"] = id_map[support["unit_id"]]
            text = catalog[support["unit_id"]]["reading_text"]
            # The synthetic plan deliberately points to an
            # existing excerpt, even if it does NOT entail
            # the requirement. This tests false approval.
            quote = text[:min(80, len(text))]
            support["source_span"] = {
                "text": quote,
                "start": 0,
                "end": len(quote),
            }

    bundle["evidence"] = new_evidence
    bundle["text"] = "\n\n".join(
        e["reading_text"] for e in new_evidence
    )
    bundle["plan_hash"] = digest({
        "synthetic_scenario": scenario,
        "coverage": bundle["coverage"],
    })
    bundle.pop("bundle_hash", None)
    bundle["bundle_hash"] = digest(bundle)

    # Local integrity preflight; no LLM calls.
    prepare(result)

    return {
        "experiment": "RV-038C3",
        "synthetic": True,
        "scenario": scenario,
        "source": "ORC-001 counterfactual fixture",
        "status": "planned_pending_review",
        "result": result,
    }


def write_scenarios(source_path, destination):
    source = json.loads(
        Path(source_path).read_text(encoding="utf-8")
    )
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)

    paths = []

    for scenario in SCENARIOS:
        output = destination / (
            "RV038C3_" + scenario.upper()
            + "_INPUT_local.json"
        )

        payload = build_scenario(source, scenario)

        with output.open("x", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        paths.append(output)

    return paths
