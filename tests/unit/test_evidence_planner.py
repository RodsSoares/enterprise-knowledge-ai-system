"""Scope isolation, supported coverage, bounded recovery and output binding."""
from dataclasses import replace
import json

import pytest

from app.chunking.evidence_units import EvidenceUnitBuilder, digest
from app.ingestion.schemas import NormalizedContent, TextBlock, SourceLocation, TableBlock
from app.orchestration.evidence_planner import (
    EvidencePlanner, PlannerLimits, PlanningContractError, validate_scope, validate_plan, PLAN_SCHEMA,
)


def units():
    return EvidenceUnitBuilder().build(NormalizedContent((
        TextBlock("a", 0, "paragraph", "Confidential data requires a secure channel.",
                  SourceLocation(section_path=("Sharing",))),
        TextBlock("b", 1, "paragraph", "AI tools require approved use cases.",
                  SourceLocation(section_path=("AI",))),)),
        document_id="DOC-005", title="Sharing", source_revision="a"*64)


def scope(**overrides):
    return dict(request_kind="general", focus="External sharing", known_conditions=[],
                exclusions=[], unknown_conditions=[], decision="proceed", clarification=None, **overrides)


def plan(unit, action=None, question_quote="compartilhar"):
    return dict(items=[dict(need="Secure channel", use="category", condition="Confidential data",
        scope_link=dict(question_quote=question_quote, explanation="Controle da ação de compartilhamento solicitada."),
        supports=[dict(unit_id=unit.unit_id, quote=unit.reading_text)])],
        action=action or dict(kind="complete"))


class Retriever:
    def __init__(self, results):
        self.results, self.calls = results, []
    def search(self, query, docs, top_k):
        self.calls.append((query, docs, top_k))
        return self.results[min(len(self.calls)-1, len(self.results)-1)], {}


class Provider:
    def __init__(self, outputs):
        self.outputs, self.calls = list(outputs), []
    def invoke(self, stage, payload):
        self.calls.append((stage, json.loads(json.dumps(payload))))
        return json.dumps(self.outputs.pop(0))


def test_scope_sees_only_question_and_bundle_is_bound_to_plan_and_sources():
    items = units()
    provider = Provider([scope(), plan(items[0])])
    retriever = Retriever([items])
    outcome = EvidencePlanner(snapshot_id="snapshot", units=items, retriever=retriever,
                               provider=provider).plan("Como compartilhar dados?")
    assert provider.calls[0] == ("scope", {"question": "Como compartilhar dados?"})
    assert outcome["status"] == "planned_pending_review"
    bundle = outcome["bundle"]
    assert "AI tools" not in bundle["text"] and len(bundle["evidence"]) == 1
    assert bundle["coverage"][0]["coverage_id"] == "C1"
    assert bundle["bundle_hash"] == digest({k:v for k,v in bundle.items() if k!="bundle_hash"})
    assert outcome["semantic_review"] == "not_performed"


def test_document_reference_is_application_owned_and_filters_search():
    items = units()
    retriever = Retriever([items])
    outcome = EvidencePlanner(snapshot_id="s", units=items, retriever=retriever,
        provider=Provider([scope(), plan(items[0])])).plan("Segundo a doc-005, como compartilhar?")
    assert retriever.calls[0][1] == ("DOC-005",)
    assert outcome["scope"]["document_ids"] == ["DOC-005"]


def test_unknown_explicit_document_never_falls_back_to_generic_search():
    retriever = Retriever([units()])
    result = EvidencePlanner(snapshot_id="s", units=units(), retriever=retriever,
        provider=Provider([scope()])).plan("Segundo a DOC-999?")
    assert result["status"] == "abstained" and not retriever.calls


def test_exact_question_quotes_are_required_for_known_conditions():
    raw = scope()
    raw["known_conditions"] = [dict(text="confidential", quote="confidential")]
    with pytest.raises(PlanningContractError, match="exactly once"):
        validate_scope(json.dumps(raw), "Como compartilhar dados?")


def test_category_schema_and_validator_both_reject_null_condition():
    variants = PLAN_SCHEMA["properties"]["items"]["items"]["anyOf"]
    category = next(v for v in variants if v["properties"]["use"]["enum"] == ["category"])
    assert category["properties"]["condition"] == {"type": "string"}
    value = plan(units()[0])
    value["items"][0]["condition"] = None
    with pytest.raises(PlanningContractError, match=r"items\[0\].condition"):
        validate_plan(json.dumps(value), units(), set(), question="Como compartilhar?")


def test_scope_link_requires_an_exact_question_anchor():
    value = plan(units()[0], question_quote="usar uma ferramenta de IA")
    with pytest.raises(PlanningContractError, match="exactly once"):
        validate_plan(json.dumps(value), units(), set(), question="Como compartilhar?")


def test_scope_link_is_traceability_not_a_semantic_guarantee():
    value = plan(units()[1])  # AI evidence remains a semantic error for this question.
    validated = validate_plan(json.dumps(value), units(), set(), question="Como compartilhar?")
    assert validated["items"][0]["scope_link"]["question_span"]["text"] == "compartilhar"
    # Exact anchors alone cannot decide whether a source regulates the requested action.
    assert "semantic_pass" not in validated


@pytest.mark.parametrize("mutation", ["foreign", "quote", "condition", "action_fields", "empty"])
def test_plan_rejects_invalid_supports_and_action_protocol(mutation):
    items = units()
    value = plan(items[0])
    if mutation == "foreign": value["items"][0]["supports"][0]["unit_id"] = "unknown"
    if mutation == "quote": value["items"][0]["supports"][0]["quote"] = "Invented approval"
    if mutation == "condition": value["items"][0]["condition"] = None
    if mutation == "action_fields": value["action"]["query"] = "Extra"
    if mutation == "empty": value["items"] = []
    with pytest.raises(PlanningContractError):
        validate_plan(json.dumps(value), items, set(), question="Como compartilhar?")


def test_only_one_complement_and_scope_remains_identical():
    items = units()
    request = dict(items=[], action=dict(kind="search", query="secure channel", gap="channel"))
    provider = Provider([scope(), request, request])
    retriever = Retriever([(items[1],), items])
    result = EvidencePlanner(snapshot_id="s", units=items, retriever=retriever,
        provider=provider).plan("Como compartilhar?")
    assert result["status"] == "abstained" and len(retriever.calls) == 2
    assert provider.calls[1][1]["scope"] == provider.calls[2][1]["scope"]
    assert provider.calls[2][1]["complement_used"]


def test_clarification_stops_before_retrieval():
    value = scope()
    value.update(decision="clarify", clarification="Qual ação deseja realizar?")
    retriever = Retriever([units()])
    result = EvidencePlanner(snapshot_id="s", units=units(), retriever=retriever,
        provider=Provider([value])).plan("Posso fazer isso?")
    assert result["status"] == "clarification_required" and not retriever.calls


def test_bundle_over_limit_is_not_silently_truncated_or_approved():
    items = units()
    result = EvidencePlanner(snapshot_id="s", units=items, retriever=Retriever([items]),
        provider=Provider([scope(), plan(items[0])]),
        limits=PlannerLimits(max_bundle_chars=5)).plan("Como compartilhar?")
    assert result["status"] == "error" and result["bundle"] is None


def test_foreign_retriever_evidence_is_rejected():
    items = units()
    result = EvidencePlanner(snapshot_id="s", units=items,
        retriever=Retriever([(replace(items[0], reading_text="Changed"),)]),
        provider=Provider([scope()])).plan("Como compartilhar?")
    assert result["status"] == "error"


def test_structural_expansion_adds_content_without_another_search():
    loc = SourceLocation(section_path=("Controls",))
    items = EvidenceUnitBuilder().build(NormalizedContent((
        TextBlock("h", 0, "heading", "Controls", loc),
        TableBlock("t", 1, (("Public", "Approved use"),), loc, ("Class", "Rule")))),
        document_id="DOC-005", title="Sharing", source_revision="a"*64)
    parent, child = items
    provider = Provider([scope(), dict(items=[], action=dict(kind="expand",
        parent_id=parent.unit_id, gap="classification")), plan(child, question_quote="controles")])
    retriever = Retriever([(parent,)])
    result = EvidencePlanner(snapshot_id="s", units=items, retriever=retriever,
        provider=provider).plan("Quais controles?")
    assert result["status"] == "planned_pending_review" and len(retriever.calls) == 1
    assert len(provider.calls[2][1]["candidates"]) == 2
