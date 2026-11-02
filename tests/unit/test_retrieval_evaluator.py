import pytest

from app.evaluation.golden_set_loader import GoldenSet
from app.evaluation.retrieval_evaluator import RetrievalEvaluator
from app.evaluation.schemas import GoldenQuestion


def question(question_id, expected):
    return GoldenQuestion(
        question_id=question_id,
        question=f"Question {question_id}",
        question_class="knowledge",
        retrieval_challenge="multi_document",
        expected_behavior="answer_with_citations",
        expected_evidence=expected,
        distractors=(),
    )


def test_evaluator_scores_eligible_positive_evidence_questions():
    golden_set = GoldenSet(
        (
            question("Q20", ("DOC-005", "DOC-006")),
            question("Q31", ("DOC-023", "DOC-024")),
        )
    )
    ranked = {
        "Q20": ("DOC-006", "DOC-005", "DOC-023"),
        "Q31": ("DOC-025", "DOC-023", "DOC-024"),
    }

    report = RetrievalEvaluator().evaluate(
        golden_set,
        {"DOC-005", "DOC-006", "DOC-023", "DOC-024", "DOC-025"},
        ranked,
    )

    assert report.evaluated_questions == 2
    assert report.skipped_questions == 0
    assert report.mean_hit_at_1 == pytest.approx(0.5)
    assert report.mean_hit_at_3 == 1.0
    assert report.mean_recall_at_3 == 1.0
    assert report.mean_reciprocal_rank == pytest.approx(0.75)


def test_evaluator_skips_question_blocked_by_missing_corpus_document():
    golden_set = GoldenSet((question("Q32", ("DOC-023", "DOC-012")),))

    report = RetrievalEvaluator().evaluate(
        golden_set,
        {"DOC-023"},
        {},
    )

    assert report.evaluated_questions == 0
    assert report.skipped_questions == 1


def test_evaluator_defers_abstention_question_to_later_layer():
    abstention = GoldenQuestion(
        question_id="Q29",
        question="Unknown policy?",
        question_class="abstention",
        retrieval_challenge="intentional_unknown",
        expected_behavior="abstain_insufficient_evidence",
        expected_evidence=(),
        distractors=("DOC-005",),
    )

    report = RetrievalEvaluator().evaluate(GoldenSet((abstention,)), {"DOC-005"}, {})

    assert report.evaluated_questions == 0
    assert report.skipped_questions == 1


def test_evaluator_requires_results_for_each_scored_question():
    golden_set = GoldenSet((question("Q20", ("DOC-005",)),))

    with pytest.raises(ValueError, match="Missing ranked retrieval results for Q20"):
        RetrievalEvaluator().evaluate(golden_set, {"DOC-005"}, {})


def test_evaluator_rejects_unsupported_k_configuration():
    with pytest.raises(ValueError, match="supports ks"):
        RetrievalEvaluator(ks=(1, 5))
