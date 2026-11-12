"""Corpus content audit patterns; no API calls."""
from app.scripts.audit_corpus_content import audit_text, audit_snapshot


def test_clean_policy_text_has_no_findings():
    assert audit_text("Confidential information shared externally must use an approved secure channel.") == {}
    assert audit_text("Report quarterly results for Q3 and review the SLA.") == {}


def test_question_ids_and_benchmark_notes_are_leakage():
    found = audit_text("Benchmark coverage: Q02, Q06, Q10; distractor for Q10.")
    assert set(found) == {"leakage"} and "Q02" in found["leakage"]


def test_harness_disclaimers_and_reader_instructions_are_reported():
    assert "disclaimer" in audit_text("RV032 synthetic draft; details require review before benchmark freeze.")
    assert "instruction" in audit_text("It must not be used to answer current-policy questions.")


def test_only_searchable_units_are_audited():
    snapshot = {"snapshot": {"documents": [{"document_id": "DOC-001", "units": [
        {"searchable": False, "section_path": [], "reading_text": "Golden Set: Q01"},
        {"searchable": True, "section_path": ["1. Purpose"], "reading_text": "Golden Set: Q01"},
        {"searchable": True, "section_path": [], "reading_text": "Normal rule."}]}]}}
    findings = audit_snapshot(snapshot)
    assert len(findings) == 1 and findings[0]["section"] == "1. Purpose"
