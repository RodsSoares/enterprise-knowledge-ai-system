"""Offline security and structural checks for the RV-042 relevance decision.

These tests do not assert that a model's materiality labels are true.
"""
import json
from copy import deepcopy

import pytest

from app.orchestration.v3_planning_contract import ValidatedV3Plan
from app.orchestration.v42_relevance_contract import apply_relevance, V42RelevanceError


def plan():
    def item(i, status="supported", relevance="category"):
        return {"requirement_id": f"C{i}", "need": f"Need {i}",
                "relevance": relevance, "condition": "If needed" if relevance == "category" else None,
                "evidence_status": status, "supports": ([{"unit_id": f"u{i}", "span": {"text": "x", "start": 0, "end": 1}}]
                                                       if status == "supported" else []),
                "question_span": {"start": 0, "end": 2, "text": "Do"},
                "missing_aspects": [] if status == "supported" else ["Unknown"]}
    return ValidatedV3Plan((item(1), item(2, relevance="in_scope"),
                            item(3, relevance="out_of_scope", status="excluded")),
                           {"kind": "complete"}, False)


def inv():
    return {"facets": [{"description": "One", "supporting_unit_ids": ["u1"]},
                       {"description": "Optional", "supporting_unit_ids": ["u2"]}],
            "unresolved_facets": ["Optional policy detail", "Required control"]}


def gate():
    return {"requirements": [
                {"requirement_id": "C1", "classification": "conditional", "reason": "General conditional rule"},
                {"requirement_id": "C2", "classification": "adjacent", "reason": "Not asked"}],
            "facets": [{"index": 0, "classification": "material", "reason": "Asked"},
                       {"index": 1, "classification": "adjacent", "reason": "Related"}],
            "unresolved": [{"index": 0, "classification": "adjacent", "reason": "Unasked detail"},
                           {"index": 1, "classification": "adjacent", "reason": "Not needed for general answer"}],
            "blocking_questions": [], "rationale": "Answer general rules with conditions"}


def call(data=None, **kwargs):
    return apply_relevance(json.dumps(data if data is not None else gate()),
                           plan=kwargs.pop("plan", plan()), inventory=kwargs.pop("inventory", inv()), **kwargs)


def test_adjacent_does_not_block_a_supported_conditional_answer():
    result = call()
    assert result.plan.may_complete
    assert result.plan.action == {"kind": "complete"}
    assert [r["requirement_id"] for r in result.plan.items] == ["C1"]
    assert result.inventory["unresolved_facets"] == []
    assert result.audit["adjacent_requirements"] == ["C2"]
    assert result.audit["semantic_claim"] == "model_label_only_requires_independent_review"


def test_unresolved_material_is_never_silently_suppressed():
    g = gate(); g["unresolved"][1]["classification"] = "material"
    result = call(g)
    assert result.material_missing
    assert "Required control" in result.missing_reasons
    assert not result.audit["sufficient_on_current_evidence"]


def test_known_material_gap_never_becomes_structurally_complete():
    p = plan(); rows = list(p.items)
    rows[0] = {**rows[0], "evidence_status": "missing", "supports": [], "missing_aspects": ["Missing"]}
    p = ValidatedV3Plan(tuple(rows), {"kind": "search", "query": "x", "gap": "Missing"}, True)
    result = call(plan=p)
    assert result.plan.has_known_gap
    assert result.plan.action["kind"] == "search"
    after = call(plan=p, recovery_used=True)
    assert after.plan.action["kind"] == "abstain"


def test_can_classify_both_material_and_conditional_without_losing_requirements():
    g = gate(); g["requirements"][1]["classification"] = "material"
    result = call(g)
    assert len(result.plan.items) == 2
    assert result.audit["material_requirements"] == ["C1", "C2"]


@pytest.mark.parametrize("mutation", [
    lambda g: g["requirements"].pop(),
    lambda g: g["requirements"].append(deepcopy(g["requirements"][0])),
    lambda g: g["requirements"][0].update(requirement_id="C88"),
    lambda g: g["requirements"].append({"requirement_id":"C3","classification":"adjacent","reason":"x"}),
    lambda g: g["requirements"][0].update(classification="unknown"),
    lambda g: g["requirements"][0].update(reason=""),
    lambda g: g["facets"].pop(),
    lambda g: g["facets"][1].update(index=0),
    lambda g: g["facets"][0].update(index=True),
    lambda g: g["unresolved"].pop(),
    lambda g: g["unresolved"][0].update(index=50),
    lambda g: g["blocking_questions"].append(""),
    lambda g: g.update(rationale=" "),
    lambda g: g.update(extra=42),
])
def test_invalid_or_incomplete_judgments_fail_closed(mutation):
    g = gate(); mutation(g)
    with pytest.raises((V42RelevanceError, ValueError)):
        call(g)


def test_frozen_classifications_cannot_be_demoted_after_recovery():
    first = call()
    g = gate(); g["requirements"][0]["classification"] = "adjacent"
    with pytest.raises(V42RelevanceError, match="frozen"):
        call(g, frozen=first.frozen, recovery_used=True)


def test_recovery_can_classify_new_items_but_not_change_existing_ones():
    first = call()
    p = plan(); new = {"requirement_id":"C4","need":"New",
                        "evidence_status":"supported","supports":[{"unit_id":"u4"}],
                        "missing_aspects":[],"relevance":"category","condition":"If applies"}
    p = ValidatedV3Plan(p.items+(new,), {"kind":"complete"},False)
    g=gate();g["requirements"].append({"requirement_id":"C4","classification":"adjacent","reason":"Unasked workflow"})
    second=call(g, plan=p, frozen=first.frozen, recovery_used=True)
    assert second.frozen["C1"] == "conditional"
    assert "C4" in second.audit["adjacent_requirements"]


def test_false_boolean_index_not_accepted():
    g=gate();g["facets"][0]["index"]=False
    with pytest.raises(V42RelevanceError):call(g)


def test_all_adjacent_cannot_approve():
    g=gate();g["requirements"][0]["classification"]="adjacent"
    with pytest.raises(V42RelevanceError, match="No material"):
        call(g)


def test_duplicate_json_key_rejected():
    raw = json.dumps(gate()).replace('"rationale":', '"rationale": "duplicate", "rationale":')
    with pytest.raises(ValueError, match="Duplicate"):
        apply_relevance(raw, plan=plan(), inventory=inv())


def test_question_is_immutable_and_unmodified():
    p=plan(); first_need=p.items[0]["need"]
    call()
    assert p.items[0]["need"]==first_need
