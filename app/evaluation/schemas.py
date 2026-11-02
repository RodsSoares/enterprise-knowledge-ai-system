"""Application-controlled schemas for retrieval evaluation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GoldenQuestion:
    question_id: str
    question: str
    question_class: str
    retrieval_challenge: str
    expected_behavior: str
    expected_evidence: tuple[str, ...]
    distractors: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "question_id", "question", "question_class",
            "retrieval_challenge", "expected_behavior",
        ):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must not be empty.")

        evidence = tuple(item.strip() for item in self.expected_evidence)
        distractors = tuple(item.strip() for item in self.distractors)

        if any(not item for item in evidence):
            raise ValueError("expected_evidence must not contain empty document IDs.")
        if any(not item for item in distractors):
            raise ValueError("distractors must not contain empty document IDs.")
        if len(set(evidence)) != len(evidence):
            raise ValueError("expected_evidence must not contain duplicates.")
        if len(set(distractors)) != len(distractors):
            raise ValueError("distractors must not contain duplicates.")
        if set(evidence) & set(distractors):
            raise ValueError("A document cannot be both expected evidence and a distractor.")

        object.__setattr__(self, "expected_evidence", evidence)
        object.__setattr__(self, "distractors", distractors)
