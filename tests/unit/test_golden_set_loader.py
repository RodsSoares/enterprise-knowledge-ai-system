from pathlib import Path

import pytest

from app.evaluation.golden_set_loader import GoldenSet, GoldenSetLoader
from app.evaluation.schemas import GoldenQuestion


def make_question(expected=("DOC-005",)):
    return GoldenQuestion(
        question_id="Q20",
        question="What policies apply?",
        question_class="knowledge",
        retrieval_challenge="multi_document",
        expected_behavior="answer_with_citations",
        expected_evidence=expected,
        distractors=(),
    )


def test_loader_reads_real_golden_set():
    golden_set = GoldenSetLoader().load()
    assert len(golden_set.questions) == 36
    assert golden_set.questions[0].question_id == "Q01"
    assert golden_set.questions[-1].question_id == "Q36"


def test_rejects_duplicate_question_ids():
    question = make_question()
    with pytest.raises(ValueError, match="duplicate question IDs"):
        GoldenSet((question, question))


def test_materialized_question_is_evaluable():
    golden_set = GoldenSet((make_question(("DOC-005", "DOC-006")),))
    result = golden_set.classify_for_corpus({"DOC-005", "DOC-006"})[0]
    assert result.evaluable is True
    assert result.missing_expected_documents == ()


def test_missing_evidence_blocks_question():
    golden_set = GoldenSet((make_question(("DOC-023", "DOC-005", "DOC-012")),))
    result = golden_set.classify_for_corpus({"DOC-023", "DOC-005"})[0]
    assert result.evaluable is False
    assert result.missing_expected_documents == ("DOC-012",)


def test_abstention_without_evidence_is_evaluable():
    question = GoldenQuestion(
        question_id="Q29",
        question="What is the radioactive material policy?",
        question_class="abstention",
        retrieval_challenge="intentional_unknown",
        expected_behavior="abstain_insufficient_evidence",
        expected_evidence=(),
        distractors=("DOC-001",),
    )
    result = GoldenSet((question,)).classify_for_corpus(set())[0]
    assert result.evaluable is True
