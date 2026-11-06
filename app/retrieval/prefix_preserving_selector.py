"""Optional ordering policy for an already selected, completely scored set."""

from collections.abc import Sequence
from dataclasses import replace

from app.retrieval.candidate_fusion import FusedCandidate
from app.retrieval.reranker import RerankedCandidate


class PrefixPreservingSelector:
    """Preserve the first N distinct documents and the full selected chunk set.

    Scores sort candidates within the protected document group and within the
    remaining group. Ties preserve baseline order. On the RV-009 five-distinct-
    document case with N=3, these are exactly positions 1-3 and 4-5.

    With repeated documents, the invariant applies to document ranks, matching
    the current evaluator, rather than to the first N physical chunk positions.
    The scorer is never called here. This policy does not add evidence or repair
    relevance/authority judgments. It is opt-in, not a default retriever change.
    """

    def __init__(self, protected_documents: int = 3) -> None:
        if (isinstance(protected_documents, bool)
                or not isinstance(protected_documents, int)
                or protected_documents < 1):
            raise ValueError("protected_documents must be a positive integer.")
        self.protected_documents = protected_documents

    def select(
        self,
        baseline: Sequence[FusedCandidate],
        reranked: Sequence[RerankedCandidate],
    ) -> tuple[RerankedCandidate, ...]:
        baseline = tuple(baseline)
        reranked = tuple(reranked)
        baseline_ids = [item.chunk.chunk_id for item in baseline]
        if len(set(baseline_ids)) != len(baseline_ids):
            raise ValueError("baseline contains duplicate chunk IDs.")
        by_id = {item.chunk.chunk_id: item for item in reranked}
        if len(by_id) != len(reranked):
            raise ValueError("reranked candidates contain duplicate chunk IDs.")
        if set(baseline_ids) != set(by_id):
            raise ValueError("reranked candidates must contain exactly the baseline selection.")
        for item in baseline:
            if by_id[item.chunk.chunk_id].source != item:
                raise ValueError(f"Changed source candidate or provenance: {item.chunk.chunk_id}")

        document_order = tuple(dict.fromkeys(item.chunk.document_id for item in baseline))
        protected = set(document_order[: self.protected_documents])
        groups = (
            [item.chunk.chunk_id for item in baseline if item.chunk.document_id in protected],
            [item.chunk.chunk_id for item in baseline if item.chunk.document_id not in protected],
        )
        ordered = [by_id[cid] for group in groups
                   for cid in sorted(group, key=lambda cid: -by_id[cid].score)]
        return tuple(replace(item, rank=rank) for rank, item in enumerate(ordered, 1))
