"""RV-041: deterministic, provider-free qualification/reviewer contract tests."""
from dataclasses import dataclass
import csv
import json

import pytest

from app.qualification.rv041_protocol import (
    PROTOCOL, RUBRIC, REVIEW_FIELDS, ProtocolError,
    blinded_labels, build_review_rows, cost_and_calls, load_cases,
    save_review_packet, score_review_packet, select_cases,
)


@dataclass(frozen=True)
class Unit:
    unit_id: str
    reading_text: str


CASES = [
    {"case_id": "ORC-001", "cohort": "development", "question": "Pergunta de teste?"},
    {"case_id": "Q29-ABSTENTION", "cohort": "safety", "question": "Politica ausente?"},
]


def cases_file(tmp_path, cases=None):
    target = tmp_path / "cases.json"
    target.write_text(json.dumps({"protocol": PROTOCOL, "cases": CASES if cases is None else cases}),
                      encoding="utf-8")
    return target


def report(status="completed"):
    source = {"unit_id": "u1", "reading_text": "External sharing requires approved channel.",
              "citation_id": "E1"}
    baseline = {"answer": {"status": "answered", "claims": [
        {"text": "Use an approved channel", "citation_ids": ["E1"]}]},
        "generation_request": {"bundle": {"evidence": [source]}}}
    v3 = {"answer": {"status": "answered", "claims": [
        {"text": "Use an approved channel", "citation_ids": ["u1"]}]}}
    return {"status": status, "snapshot_id": "snap123",
            "runs": {"ORC-001": {
                "baseline": {"status": "answered_pending_review", "result": baseline,
                             "usage": {"calls": 3, "estimated_cost_usd": "0.010"}},
                "v3": {"status": "answered_pending_human_review", "result": v3,
                       "usage": {"calls": 7, "estimated_cost_usd": "0.020"}},
            }}}


def test_load_and_select(tmp_path):
    cases = load_cases(cases_file(tmp_path))
    assert len(select_cases(cases, "development")) == 1
    assert len(select_cases(cases, "safety")) == 1
    assert len(select_cases(cases, "all")) == 2


@pytest.mark.parametrize("mutation", [
    {"case_id": "ORC-001", "cohort": "development", "question": ""},
    {"case_id": "orc001", "cohort": "development", "question": "question"},
    {"case_id": "ORC-001", "cohort": "reserved", "question": "question"},
    {"case_id": "ORC-001", "cohort": "development", "question": "test", "answer": "leak"},
])
def test_reject_bad_cases(tmp_path, mutation):
    with pytest.raises(ProtocolError):
        load_cases(cases_file(tmp_path, [mutation]))


def test_duplicate_case_rejected(tmp_path):
    with pytest.raises(ProtocolError):
        load_cases(cases_file(tmp_path, [CASES[0], CASES[0]]))


def test_invalid_protocol_rejected(tmp_path):
    p = tmp_path / "cases.json"
    p.write_text(json.dumps({"protocol": "old", "cases": CASES}), encoding="utf-8")
    with pytest.raises(ProtocolError):
        load_cases(p)


def test_unknown_cohort_rejected():
    with pytest.raises(ProtocolError):
        select_cases(CASES, "reservado")


def test_blinding_repeatable_and_pairs():
    assert blinded_labels("snap123", "ORC-001") == blinded_labels("snap123", "ORC-001")
    assert set(blinded_labels("snap123", "ORC-001").values()) == {"A", "B"}


def test_anonymous_evidence_links_equal_between_arms():
    rows, mapping = build_review_rows(report(), CASES[:1], {"u1": Unit("u1", "External sharing requires approved channel.")})
    assert len(rows) == len(mapping) == 2
    assert {x["blind_arm"] for x in rows} == {"A", "B"}
    for row in rows:
        assert "[S1]" in row["answer_for_review"]
        assert "External sharing requires approved channel." in row["cited_evidence_for_review"]
        assert "u1" not in row["cited_evidence_for_review"]
        assert "E1" not in row["answer_for_review"]
        assert "v3" not in row["answer_for_review"]


def test_missing_source_rejected():
    r = report()
    r["runs"]["ORC-001"]["v3"]["result"]["answer"]["claims"][0]["citation_ids"] = ["fake"]
    with pytest.raises(ProtocolError):
        build_review_rows(r, CASES[:1], {"u1": Unit("u1", "External sharing requires approved channel.")})


def test_no_premature_review_on_dry_run():
    with pytest.raises(ProtocolError):
        build_review_rows(report("dry_run"), CASES[:1], {"u1": Unit("u1", "External sharing requires approved channel.")})


def test_hides_rejected_output():
    r = report()
    r["runs"]["ORC-001"]["v3"] = {"status": "review_rejected", "result": {"answer": None}}
    rows, _ = build_review_rows(r, CASES[:1], {"u1": Unit("u1", "External sharing requires approved channel.")})
    assert any(row["outcome"] == "no_answer_or_rejected" and not row["answer_for_review"] for row in rows)


def test_usage_summary():
    summary = cost_and_calls(report())
    assert summary["total_api_calls"] == 10
    assert summary["estimated_total_cost_usd"] == "0.030"
    assert summary["by_arm"]["baseline"]["calls"] == 3


def test_save_review_packet_no_overwrite(tmp_path):
    out, mapping = tmp_path / "review.csv", tmp_path / "private.json"
    n = save_review_packet(report(), CASES[:1], {"u1": Unit("u1", "External sharing requires approved channel.")},
                           template_path=out, mapping_path=mapping)
    assert n == 2 and out.exists() and mapping.exists()
    with pytest.raises(ProtocolError):
        save_review_packet(report(), CASES[:1], {"u1": Unit("u1", "External sharing requires approved channel.")},
                           template_path=out, mapping_path=mapping)


def test_scoring_requires_human_review(tmp_path):
    out, mapping = tmp_path / "review.csv", tmp_path / "private.json"
    save_review_packet(report(), CASES[:1], {"u1": Unit("u1", "External sharing requires approved channel.")},
                       template_path=out, mapping_path=mapping)
    summary = score_review_packet(out, mapping)
    assert summary["status"] == "review_incomplete"
    assert summary["arms"]["baseline"]["mean_score_out_of_12"] is None


def test_scoring_completed_review(tmp_path):
    out, mapping = tmp_path / "review.csv", tmp_path / "private.json"
    save_review_packet(report(), CASES[:1], {"u1": Unit("u1", "External sharing requires approved channel.")},
                       template_path=out, mapping_path=mapping)
    with out.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for idx, row in enumerate(rows):
        for rubric in RUBRIC:
            row[rubric] = "2" if idx == 0 else "1"
        row["critical_error"] = "no"
    with out.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=REVIEW_FIELDS)
        writer.writeheader(); writer.writerows(rows)
    summary = score_review_packet(out, mapping)
    assert summary["status"] == "complete"
    assert len(summary["paired_case_comparison"]) == 1
    assert {summary["arms"][arm]["mean_score_out_of_12"] for arm in ("baseline", "v3")} == {6.0, 12.0}


def test_scoring_rejects_missing_row(tmp_path):
    out, mapping = tmp_path / "review.csv", tmp_path / "private.json"
    save_review_packet(report(), CASES[:1], {"u1": Unit("u1", "External sharing requires approved channel.")},
                       template_path=out, mapping_path=mapping)
    with out.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    with out.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=REVIEW_FIELDS)
        writer.writeheader(); writer.writerow(rows[0])
    with pytest.raises(ProtocolError):
        score_review_packet(out, mapping)
