"""Offline checks for the prospective live experiment; no embeddings or weights."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from app.chunking.schemas import RetrievalChunk
from tests.smoke import smoke_prefix_reranking_live as live


def test_challenge_b_is_frozen_and_covers_12_new_cases_and_ten_documents():
    path = Path(__file__).resolve().parents[2] / "data/ground_truth/reranking_challenge_b.json"
    challenge = json.loads(path.read_text(encoding="utf-8-sig"))
    assert live.canonical_sha256(challenge) == live.CHALLENGE_SHA256
    assert len(challenge["questions"]) == 12
    assert len({q["question_id"] for q in challenge["questions"]}) == 12
    assert len({d for q in challenge["questions"] for d in q["expected_document_ids"]}) == 10
    for q in challenge["questions"]:
        assert q["query"].strip()
        assert q["reference_passage_groups"]
        refs = {r["chunk_id"] for r in q["source_evidence"]}
        assert all(set(g["any_of_chunk_ids"]).issubset(refs) for g in q["reference_passage_groups"])


def input_files(tmp_path, monkeypatch):
    source = {"questions": [{"question_id": f"Q{i:02d}", "query": f"old {i}",
               "expected_document_ids": ["DOC-1"]} for i in range(13)]}
    challenge = {"source_artifact": {"canonical_sha256": live.canonical_sha256(source)},
                 "questions": [{"question_id": f"B{i:02d}", "query": f"new {i}",
                     "expected_document_ids": ["DOC-1"]} for i in range(12)]}
    monkeypatch.setattr(live, "CHALLENGE_SHA256", live.canonical_sha256(challenge))
    monkeypatch.setattr(live, "replay", lambda supplied: {"validated_source": supplied})
    paths = tmp_path / "source.json", tmp_path / "challenge.json"
    for path, value in zip(paths, (source, challenge)):
        path.write_bytes(b"\xef\xbb\xbf" + json.dumps(value, indent=2).replace("\n", "\r\n").encode())
    return paths


def test_loading_frozen_json_accepts_windows_line_endings_and_utf8_bom(tmp_path, monkeypatch):
    paths = input_files(tmp_path, monkeypatch)
    source, _, cached, cases_a, cases_b = live.load_inputs(*paths)
    assert cached["validated_source"] == source
    assert len(cases_a) == 13 and len(cases_b) == 12


def test_changed_question_definition_is_rejected_before_scoring(tmp_path, monkeypatch):
    paths = input_files(tmp_path, monkeypatch)
    value = json.loads(paths[1].read_text(encoding="utf-8-sig"))
    value["questions"][0]["query"] = "edited after seeing scores"
    paths[1].write_text(json.dumps(value))
    with pytest.raises(ValueError, match="changed after definition"):
        live.load_inputs(*paths)


def test_source_snapshot_mismatch_is_rejected(tmp_path, monkeypatch):
    paths = input_files(tmp_path, monkeypatch)
    value = json.loads(paths[0].read_text(encoding="utf-8-sig"))
    value["questions"][0]["query"] = "different source"
    paths[0].write_text(json.dumps(value))
    with pytest.raises(ValueError, match="same snapshot"):
        live.load_inputs(*paths)


def test_reference_passages_are_checked_against_actual_chunk_content():
    chunk = RetrievalChunk(chunk_id="DOC-A::chunk-00001", document_id="DOC-A", order=1,
        text="Source evidence", source_block_ids=("b1",), source_path=Path("doc.pdf"), content_types=("text",))
    challenge = {"questions": [{"question_id": "B01", "expected_document_ids": ["DOC-A"],
        "reference_passage_groups": [{"any_of_chunk_ids": [chunk.chunk_id]}],
        "source_evidence": [{"chunk_id": chunk.chunk_id, "document_id": chunk.document_id,
                            "text_sha256": hashlib.sha256(chunk.text.encode()).hexdigest()}]}]}
    live.validate_reference_passages(challenge, [chunk])
    with pytest.raises(ValueError, match="content changed"):
        live.validate_reference_passages(challenge, [replace(chunk, text="changed")])
    with pytest.raises(ValueError, match="identity changed"):
        live.validate_reference_passages(challenge, [])


def test_frozen_data_guard_checks_exact_known_files(tmp_path):
    path = tmp_path / "policy.md"
    path.write_text("original")
    source = {"input_fingerprints": {path.as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()}}
    live.verify_frozen_data(source, [path])
    path.write_text("changed")
    with pytest.raises(ValueError, match="changed since"):
        live.verify_frozen_data(source, [path])


def test_b_regression_cannot_be_hidden_by_a_improvement():
    groups = {"A": {"comparisons": {"prefix_preserved": {"decision": "IMPROVEMENT"}}},
              "B": {"comparisons": {"prefix_preserved": {"decision": "REGRESSION"}}}}
    assert live.decide_run(groups, True, True, True) == "REGRESSION"
    groups["B"]["comparisons"]["prefix_preserved"]["decision"] = "NO_FIRST_RANK_GAIN"
    assert live.decide_run(groups, True, True, True) == "READY_FOR_REVIEW"
    assert live.decide_run(groups, False, True, True) == "BASELINE_DRIFT"
    assert live.decide_run(groups, True, False, True) == "BASELINE_DRIFT"
    assert live.decide_run(groups, True, True, False) == "INPUT_CHANGED_DURING_RUN"


def test_comparison_preserves_the_existing_no_regression_gate():
    baseline = {name: 0.5 for name in live.METRIC_NAMES}
    candidate = dict(baseline, **{"Hit@1": 0.8, "Recall@3": 0.4})
    result = live.compare_metrics(baseline, candidate)
    assert result["decision"] == "REGRESSION"
    assert result["regressed_metrics"] == ["Recall@3"]
    assert result["automatically_promoted"] is False
