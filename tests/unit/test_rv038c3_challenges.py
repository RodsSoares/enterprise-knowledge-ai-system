"""Offline semantic challenge fixture tests."""
from copy import deepcopy
from pathlib import Path
import json

import pytest

from app.scripts.rv038c3_challenges import (
    SCENARIOS, build_scenario, write_scenarios,
)
from app.scripts.rv038c2b_semantic_pilot import (
    extract_planning, prepare,
)

SOURCE = Path(
    "docs/validation/"
    "EVIDENCE_PLANNER_ORC001_GPT61SOL_RESULTS_local.json"
)


@pytest.fixture
def source():
    return json.loads(SOURCE.read_text(encoding="utf-8"))


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_synthetic_scenario_passes_preflight(source, scenario):
    fixture = build_scenario(source, scenario)
    planning = extract_planning(fixture)
    request, context = prepare(planning)

    assert fixture["synthetic"] is True
    assert request.payload["snapshot_id"].startswith(
        "synthetic-rv038c3-"
    )
    assert len(context["canonical_evidence"]) == 4
    assert len(context["requirements"]) == 7
    assert all(
        item["unit_id"].startswith("SYNTH-RV038C3::")
        for item in context["canonical_evidence"]
    )


def test_source_not_mutated(source):
    original = deepcopy(source)

    for scenario in SCENARIOS:
        build_scenario(source, scenario)

    assert source == original


def test_missing_exception_removes_rule(source):
    fixture = build_scenario(source, "missing_exception")
    evidence = fixture["result"]["bundle"]["evidence"]

    assert "business justification" not in (
        evidence[3]["reading_text"]
    )
    assert "naming conventions" in (
        evidence[3]["reading_text"]
    )


def test_conflict_is_explicit(source):
    fixture = build_scenario(source, "carrier_conflict")
    text = fixture["result"]["bundle"]["evidence"][2][
        "reading_text"
    ]

    assert "must not" in text.lower()
    assert "MAY be" in text


def test_irrelevant_classification(source):
    fixture = build_scenario(
        source, "irrelevant_classification"
    )
    text = fixture["result"]["bundle"]["evidence"][0][
        "reading_text"
    ]

    assert "No external data-sharing controls" in text


def test_write_files_once(source, tmp_path):
    input_path = tmp_path / "source.json"
    input_path.write_text(
        json.dumps(source), encoding="utf-8"
    )
    paths = write_scenarios(input_path, tmp_path / "cases")

    assert len(paths) == 3
    assert all(p.exists() for p in paths)

    with pytest.raises(FileExistsError):
        write_scenarios(input_path, tmp_path / "cases")
