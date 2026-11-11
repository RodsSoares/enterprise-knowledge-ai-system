"""V3 planning is an isolated experimental contract; not production validation."""
import json
from types import SimpleNamespace
import pytest

from app.orchestration.v3_planning_contract import (
    PLAN_V3_SCHEMA, PLAN_V3_INSTRUCTIONS, validate_v3_plan, V3PlanningContractError,
)

Q = "Quais cuidados exigem antes de compartilhar dados?"
U = SimpleNamespace(unit_id="DOC-005::u1", reading_text="External sharing needs an approved channel.",
                    status="ready", structural_role="text")


def item(status="supported", relevance="in_scope", **overrides):
    data = dict(need="Approved channel", relevance=relevance,
                condition=None, question_quote="compartilhar dados",
                evidence_status=status, supports=[dict(unit_id=U.unit_id, quote="approved channel")],
                missing_aspects=[])
    if status == "partial": data["missing_aspects"] = ["Formal approval"]
    if status == "missing":
        data["supports"] = []
        data["missing_aspects"] = ["Approved channel requirement not retrieved"]
    if relevance == "out_of_scope":
        data.update(evidence_status="excluded", supports=[], missing_aspects=[])
    data.update(overrides)
    return data


def evaluate(items=None, action=None, **kwargs):
    data = dict(items=items if items is not None else [item()],
                action=action or {"kind": "complete"})
    return validate_v3_plan(json.dumps(data), question=Q, candidates=(U,), **kwargs)


def test_supported_plan_can_complete():
    a = evaluate()
    assert a.may_complete and a.items[0]["supports"][0]["span"]["text"] == "approved channel"


def test_missing_requirement_is_allowed_without_fake_quote():
    a = evaluate([item(status="missing")], {"kind": "search", "query": "approval", "gap": "channel"})
    assert a.has_known_gap and not a.items[0]["supports"]


def test_cannot_complete_when_gap_is_known():
    with pytest.raises(V3PlanningContractError, match="Cannot declare complete"):
        evaluate([item(status="missing")])


def test_partial_requires_named_gap():
    with pytest.raises(V3PlanningContractError, match="Partial"):
        evaluate([item(status="partial", missing_aspects=[])], {"kind": "search", "query": "approval", "gap": "gap"})


def test_category_requires_explicit_condition():
    with pytest.raises(V3PlanningContractError, match="Category"):
        evaluate([item(relevance="category")])


def test_out_of_scope_item_is_not_required_coverage():
    a = evaluate([item(), item(relevance="out_of_scope", need="AI procurement")])
    assert not a.has_known_gap


def test_dangling_or_unready_source_rejected():
    with pytest.raises(V3PlanningContractError, match="authorized"):
        evaluate([item(supports=[dict(unit_id="forged", quote="approved channel")])])


def test_second_recovery_rejected():
    with pytest.raises(V3PlanningContractError, match="unused recovery"):
        evaluate([item(status="missing")], {"kind":"search", "query":"approval", "gap":"approval"}, recovery_used=True)


def test_fabricated_quote_rejected():
    with pytest.raises(V3PlanningContractError, match="Quote"):
        evaluate([item(supports=[dict(unit_id=U.unit_id, quote="newly invented rule")])])


def test_schema_does_not_require_generated_hashes():
    assert "items" in PLAN_V3_SCHEMA["properties"]
    assert "hash" not in str(PLAN_V3_SCHEMA)
    assert "Do not silently drop" in PLAN_V3_INSTRUCTIONS
