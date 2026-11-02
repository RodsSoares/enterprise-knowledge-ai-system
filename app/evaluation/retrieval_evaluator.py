"""Evaluation of ranked document retrieval against Golden Set evidence."""

from dataclasses import dataclass
from typing import Mapping, Sequence

from app.evaluation.golden_set_loader import GoldenSet
from app.evaluation.retrieval_metrics import hit_at_k, recall_at_k, reciprocal_rank


@dataclass(frozen=True)
class QuestionRetrievalResult:
    question_id: str
    expected_document_ids: tuple[str, ...]
    retrieved_document_ids: tuple[str, ...]
    hit_at_1: float
    hit_at_3: float
    hit_at_5: float
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    reciprocal_rank: float


@dataclass(frozen=True)
class RetrievalEvaluationReport:
    evaluated_questions: int
    skipped_questions: int
    mean_hit_at_1: float
    mean_hit_at_3: float
    mean_hit_at_5: float
    mean_recall_at_1: float
    mean_recall_at_3: float
    mean_recall_at_5: float
    mean_reciprocal_rank: float
    results: tuple[QuestionRetrievalResult, ...]


class RetrievalEvaluator:
    """Score document-level ranked retrieval for corpus-eligible questions."""

    def __init__(self, ks: tuple[int, ...] = (1, 3, 5)) -> None:
        if ks != (1, 3, 5):
            raise ValueError("RetrievalEvaluator v0.1 supports ks=(1, 3, 5).")
        self.ks = ks

    def evaluate(
        self,
        golden_set: GoldenSet,
        available_document_ids: set[str],
        ranked_results_by_question: Mapping[str, Sequence[str]],
    ) -> RetrievalEvaluationReport:
        eligibility = golden_set.classify_for_corpus(available_document_ids)
        scored: list[QuestionRetrievalResult] = []
        skipped = 0

        for item in eligibility:
            question = item.question
            if not item.evaluable:
                skipped += 1
                continue

            # Retrieval metrics require positive expected evidence. Abstention
            # questions are evaluated later by the abstention/answer layer.
            if not question.expected_evidence:
                skipped += 1
                continue

            if question.question_id not in ranked_results_by_question:
                raise ValueError(
                    f"Missing ranked retrieval results for {question.question_id}."
                )

            retrieved = tuple(ranked_results_by_question[question.question_id])
            expected = question.expected_evidence

            scored.append(
                QuestionRetrievalResult(
                    question_id=question.question_id,
                    expected_document_ids=expected,
                    retrieved_document_ids=retrieved,
                    hit_at_1=hit_at_k(expected, retrieved, 1),
                    hit_at_3=hit_at_k(expected, retrieved, 3),
                    hit_at_5=hit_at_k(expected, retrieved, 5),
                    recall_at_1=recall_at_k(expected, retrieved, 1),
                    recall_at_3=recall_at_k(expected, retrieved, 3),
                    recall_at_5=recall_at_k(expected, retrieved, 5),
                    reciprocal_rank=reciprocal_rank(expected, retrieved),
                )
            )

        count = len(scored)
        if count == 0:
            return RetrievalEvaluationReport(
                evaluated_questions=0,
                skipped_questions=skipped,
                mean_hit_at_1=0.0,
                mean_hit_at_3=0.0,
                mean_hit_at_5=0.0,
                mean_recall_at_1=0.0,
                mean_recall_at_3=0.0,
                mean_recall_at_5=0.0,
                mean_reciprocal_rank=0.0,
                results=(),
            )

        def mean(attribute: str) -> float:
            return sum(getattr(result, attribute) for result in scored) / count

        return RetrievalEvaluationReport(
            evaluated_questions=count,
            skipped_questions=skipped,
            mean_hit_at_1=mean("hit_at_1"),
            mean_hit_at_3=mean("hit_at_3"),
            mean_hit_at_5=mean("hit_at_5"),
            mean_recall_at_1=mean("recall_at_1"),
            mean_recall_at_3=mean("recall_at_3"),
            mean_recall_at_5=mean("recall_at_5"),
            mean_reciprocal_rank=mean("reciprocal_rank"),
            results=tuple(scored),
        )
