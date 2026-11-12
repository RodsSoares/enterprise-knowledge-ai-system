"""Answer criteria file integrity and deterministic scoring; no API calls."""
import json
from pathlib import Path

import pytest
import yaml

from app.evaluation.answer_criteria import (
    Case, Pattern, load_criteria, normalize, score, summarize,
)

CASES = load_criteria()
BY_ID = {case.case_id: case for case in CASES}


def result(status="answered_pending_human_review", claims=(), evidence=None, reservations=()):
    return {"status": status, "answer": {"claims": [dict(text=t, citation_ids=ids) for t, ids in claims]} if claims else None,
            "evidence_ids": evidence or {}, "reservations": list(reservations)}


def test_criteria_cover_golden_set_and_orchestration_cases_with_identical_questions():
    golden = yaml.safe_load(Path("data/ground_truth/golden_questions.yaml").read_text(encoding="utf-8"))
    orchestration = json.loads(Path("data/ground_truth/orchestration_stage1_cases.json").read_text(encoding="utf-8"))
    expected = {q["question_id"]: q["question"] for q in golden["questions"]}
    expected.update({c["id"]: c["question"] for c in orchestration["cases"]})
    assert {c.case_id: c.question for c in CASES} == expected


def test_expected_outcomes_agree_with_existing_ground_truth():
    orchestration = json.loads(Path("data/ground_truth/orchestration_stage1_cases.json").read_text(encoding="utf-8"))
    for case in orchestration["cases"]:
        assert case["expected_outcome"] in BY_ID[case["id"]].outcomes
    assert BY_ID["Q29"].outcomes == ("abstain",)


def test_cited_documents_exist_in_the_registry():
    registry = yaml.safe_load(Path("data/ground_truth/document_registry.yaml").read_text(encoding="utf-8"))
    known = {d["document_id"] for d in registry["documents"]}
    for case in CASES:
        assert {d for group in case.cite for d in group} | set(case.forbidden_documents) <= known


def test_every_answer_case_is_checkable():
    for case in CASES:
        if case.outcomes == ("answer",):
            assert case.cite and case.required_facts, case.case_id


def test_normalize_removes_accents_and_case():
    assert normalize("Segurança da INFORMAÇÃO") == "seguranca da informacao"


def test_complete_answer_passes():
    r = result(claims=[("A meta vigente de OTIF é 97%.", ["E1"])],
               evidence={"E1": "DOC-001::unit-abc"})
    s = score(BY_ID["Q10"], r)
    assert s["passed"] and s["facts_found"] == s["facts_required"] == 1


def test_missing_fact_and_missing_citation_are_reported():
    r = result(claims=[("A meta é alta.", ["E1"])], evidence={"E1": "DOC-002::unit-abc"})
    s = score(BY_ID["Q10"], r)
    assert not s["passed"]
    assert any("DOC-001" in f for f in s["failures"]) and any("97%" in f for f in s["failures"])


def test_wrong_outcome_fails_and_safe_withholding_counts_as_abstention():
    assert not score(BY_ID["Q10"], result(status="abstained"))["passed"]
    assert score(BY_ID["Q29"], result(status="abstained"))["passed"]
    assert score(BY_ID["Q29"], result(status="review_rejected"))["passed"]
    assert not score(BY_ID["Q29"], result(claims=[("Regra X.", ["E1"])], evidence={"E1": "DOC-001::u"}))["passed"]


def test_execution_failure_never_passes():
    for case in CASES:
        assert not score(case, result(status="execution_failed"))["passed"]


def test_forbidden_statement_and_out_of_scope_citation_fail():
    text = "Dados confidenciais exigem canal aprovado; dados restritos exigem autorização. Para IA há outras regras."
    s = score(BY_ID["ORC-002"], result(claims=[(text, ["E1", "E2"])],
                                        evidence={"E1": "DOC-005::u1", "E2": "DOC-023::u2"}))
    assert any("forbidden statement" in f for f in s["failures"])
    assert any("out-of-scope DOC-023" in f for f in s["failures"])


def test_decision_boundary_forbids_recommending_a_carrier():
    bad = result(claims=[("Recomendo contratar a Atlas pela penalidade maior.", ["E1"])],
                 evidence={"E1": "DOC-014::u"})
    good = result(claims=[("A seleção de transportadora é decisão humana autorizada; Atlas e Nova têm penalidade.", ["E1"])],
                  evidence={"E1": "DOC-003::u"})
    assert not score(BY_ID["Q30"], bad)["passed"]
    assert score(BY_ID["Q30"], good)["passed"]


def test_clarification_is_accepted_for_context_dependent_questions():
    for case_id in ("Q17", "Q19", "Q27"):
        assert score(BY_ID[case_id], result(status="clarification_required"))["passed"]


def test_summary_reports_instability_across_repeated_runs():
    runs = [score(BY_ID["Q29"], result(status="abstained")),
            score(BY_ID["Q29"], result(claims=[("Regra X.", ["E1"])], evidence={"E1": "DOC-001::u"})),
            score(BY_ID["Q10"], result(status="abstained"))]
    summary = summarize(runs)
    assert summary["cases"] == 2 and summary["runs_passed"] == 1
    assert summary["cases_unstable"] == 1 and summary["cases_never_passed"] == 1


def test_loader_rejects_accented_or_uppercase_patterns(tmp_path):
    path = tmp_path / "c.yaml"
    path.write_text('cases:\n  - id: X\n    question: q\n    expected_outcome: answer\n'
                    '    cite: [[DOC-001]]\n    required_facts:\n      - name: n\n        any: ["Ação"]\n',
                    encoding="utf-8")
    with pytest.raises(ValueError):
        load_criteria(path)
