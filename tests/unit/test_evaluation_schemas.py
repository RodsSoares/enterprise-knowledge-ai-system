import pytest

from app.evaluation.schemas import GoldenQuestion


def make_question(**overrides):
    values = dict(
        question_id="Q01",
        question="What evidence applies?",
        question_class="knowledge",
        retrieval_challenge="direct_retrieval",
        expected_behavior="answer_with_citations",
        expected_evidence=("DOC-001",),
        distractors=("DOC-002",),
    )
    values.update(overrides)
    return GoldenQuestion(**values)


def test_valid_question():
    assert make_question().expected_evidence == ("DOC-001",)


@pytest.mark.parametrize(
    "field",
    ["question_id", "question", "question_class",
     "retrieval_challenge", "expected_behavior"],
)
def test_rejects_empty_required_text(field):
    with pytest.raises(ValueError):
        make_question(**{field: " "})


def test_rejects_duplicate_evidence():
    with pytest.raises(ValueError, match="duplicates"):
        make_question(expected_evidence=("DOC-001", "DOC-001"))


def test_rejects_evidence_distractor_overlap():
    with pytest.raises(ValueError, match="both expected evidence"):
        make_question(expected_evidence=("DOC-001",), distractors=("DOC-001",))


def test_abstention_allows_empty_expected_evidence():
    question = make_question(
        question_class="abstention",
        expected_behavior="abstain_insufficient_evidence",
        expected_evidence=(),
    )
    assert question.expected_evidence == ()
