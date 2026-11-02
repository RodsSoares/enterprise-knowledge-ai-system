"""Loader and corpus-eligibility logic for Golden Set A."""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml

from app.evaluation.schemas import GoldenQuestion


DEFAULT_GOLDEN_SET_PATH = Path("data/ground_truth/golden_questions.yaml")


@dataclass(frozen=True)
class QuestionEligibility:
    question: GoldenQuestion
    evaluable: bool
    missing_expected_documents: tuple[str, ...]


@dataclass(frozen=True)
class GoldenSet:
    questions: tuple[GoldenQuestion, ...]

    def __post_init__(self) -> None:
        ids = [question.question_id for question in self.questions]
        if len(set(ids)) != len(ids):
            raise ValueError("Golden Set contains duplicate question IDs.")

    def classify_for_corpus(
        self, available_document_ids: Iterable[str]
    ) -> tuple[QuestionEligibility, ...]:
        available = {
            document_id.strip()
            for document_id in available_document_ids
            if document_id.strip()
        }
        results = []
        for question in self.questions:
            missing = tuple(
                document_id
                for document_id in question.expected_evidence
                if document_id not in available
            )
            results.append(
                QuestionEligibility(
                    question=question,
                    evaluable=not missing,
                    missing_expected_documents=missing,
                )
            )
        return tuple(results)


class GoldenSetLoader:
    def __init__(self, path: Path = DEFAULT_GOLDEN_SET_PATH) -> None:
        self.path = path

    def load(self) -> GoldenSet:
        if not self.path.is_file():
            raise FileNotFoundError(f"Golden Set not found: {self.path}")

        with self.path.open("r", encoding="utf-8") as stream:
            payload = yaml.safe_load(stream)

        if not isinstance(payload, dict):
            raise ValueError("Golden Set root must be a mapping.")

        raw_questions = payload.get("questions")
        if not isinstance(raw_questions, list):
            raise ValueError("Golden Set 'questions' must be a list.")

        questions = tuple(self._parse_question(item) for item in raw_questions)

        declared_count = payload.get("evaluation_contract", {}).get("question_count")
        if declared_count is not None and declared_count != len(questions):
            raise ValueError(
                "Golden Set question_count does not match loaded questions: "
                f"declared={declared_count}, loaded={len(questions)}."
            )
        return GoldenSet(questions=questions)

    @staticmethod
    def _parse_question(item: object) -> GoldenQuestion:
        if not isinstance(item, dict):
            raise ValueError("Each Golden Set question must be a mapping.")

        required = (
            "question_id", "question", "class", "retrieval_challenge",
            "expected_behavior", "expected_evidence", "distractors",
        )
        missing = [field for field in required if field not in item]
        if missing:
            raise ValueError(
                "Golden Set question is missing required fields: "
                + ", ".join(missing)
            )

        if not isinstance(item["expected_evidence"], list):
            raise ValueError("expected_evidence must be a list.")
        if not isinstance(item["distractors"], list):
            raise ValueError("distractors must be a list.")

        return GoldenQuestion(
            question_id=str(item["question_id"]),
            question=str(item["question"]),
            question_class=str(item["class"]),
            retrieval_challenge=str(item["retrieval_challenge"]),
            expected_behavior=str(item["expected_behavior"]),
            expected_evidence=tuple(str(x) for x in item["expected_evidence"]),
            distractors=tuple(str(x) for x in item["distractors"]),
        )
