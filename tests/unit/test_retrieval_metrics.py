import pytest

from app.evaluation.retrieval_metrics import hit_at_k, recall_at_k, reciprocal_rank


def test_hit_at_k_detects_expected_document():
    assert hit_at_k(("DOC-005",), ("DOC-006", "DOC-005"), 2) == 1.0
    assert hit_at_k(("DOC-005",), ("DOC-006",), 1) == 0.0


def test_recall_at_k_measures_multi_document_coverage():
    expected = ("DOC-023", "DOC-024", "DOC-006")
    retrieved = ("DOC-024", "DOC-025", "DOC-006", "DOC-005", "DOC-023")

    assert recall_at_k(expected, retrieved, 1) == pytest.approx(1 / 3)
    assert recall_at_k(expected, retrieved, 3) == pytest.approx(2 / 3)
    assert recall_at_k(expected, retrieved, 5) == 1.0


def test_reciprocal_rank_uses_first_expected_document():
    assert reciprocal_rank(("DOC-005",), ("DOC-006", "DOC-007", "DOC-005")) == pytest.approx(1 / 3)


def test_metrics_do_not_double_count_multiple_chunks_from_same_document():
    retrieved = ("DOC-006", "DOC-006", "DOC-005")
    assert recall_at_k(("DOC-005", "DOC-006"), retrieved, 2) == 1.0
    assert reciprocal_rank(("DOC-005",), retrieved) == pytest.approx(1 / 2)


def test_empty_expected_evidence_scores_zero():
    assert hit_at_k((), ("DOC-001",), 1) == 0.0
    assert recall_at_k((), ("DOC-001",), 1) == 0.0
    assert reciprocal_rank((), ("DOC-001",)) == 0.0


@pytest.mark.parametrize("metric", [hit_at_k, recall_at_k])
def test_k_must_be_positive(metric):
    with pytest.raises(ValueError, match="k must be >= 1"):
        metric(("DOC-001",), ("DOC-001",), 0)
