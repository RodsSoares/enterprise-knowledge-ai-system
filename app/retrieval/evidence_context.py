"""Build a bounded, cited context without changing the selected documents."""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
import json
from math import isfinite
from numbers import Real

from app.chunking.schemas import RetrievalChunk
from app.retrieval.candidate_fusion import FusedCandidate


@dataclass(frozen=True, slots=True)
class EvidencePassage:
    citation_id: str
    source: FusedCandidate | RetrievalChunk
    role: str

    @property
    def chunk(self) -> RetrievalChunk:
        return self.source if isinstance(self.source, RetrievalChunk) else self.source.chunk

    def citation_metadata(self) -> dict:
        chunk = self.chunk
        return {"citation_id": self.citation_id, "document_id": chunk.document_id,
                "chunk_id": chunk.chunk_id, "source_path": chunk.source_path.as_posix(),
                "source_block_ids": list(chunk.source_block_ids),
                "section_path": list(chunk.section_path), "page_numbers": list(chunk.page_numbers),
                "slide_numbers": list(chunk.slide_numbers), "sheet_names": list(chunk.sheet_names)}


@dataclass(frozen=True, slots=True)
class SkippedPassage:
    chunk_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class EvidenceContext:
    passages: tuple[EvidencePassage, ...]
    selected_document_ids: tuple[str, ...]
    skipped: tuple[SkippedPassage, ...]
    text: str

    @property
    def character_count(self) -> int:
        return len(self.text)

    @property
    def citations(self) -> dict[str, dict]:
        """Lookup for a future answer/citation validator; includes source locations."""
        return {passage.citation_id: passage.citation_metadata() for passage in self.passages}


class ContextBudgetError(ValueError):
    """The selected anchors cannot fit without changing the retrieval result."""


def render_context(passages: Sequence[EvidencePassage]) -> str:
    """JSON preserves source text as data; retrieval scores stay outside LLM text."""
    if not passages:
        return ""
    evidence = [dict(passage.citation_metadata(), text=passage.chunk.text) for passage in passages]
    return json.dumps({"evidence": evidence}, ensure_ascii=False, indent=2, allow_nan=False)


class EvidenceContextBuilder:
    """Keep selected anchors, then append ranked passages from the same documents.

    There is no query, answer key, semantic threshold, or model call here.
    candidate_pool must be in increasing fusion-rank order. Additional passages
    follow that order and are accepted only if they fit all budgets. A skipped
    oversized extra does not prevent a later, shorter extra from fitting.

    max_characters counts the complete rendered JSON, including citation
    metadata; it is not a model-token budget. Anchors are never truncated or
    silently dropped. The per-document limit applies to additions only, so
    repeated documents already present among the anchors remain intact.
    """

    def __init__(self, *, max_chunks: int = 10, max_characters: int = 12000,
                 max_additional_per_document: int = 1) -> None:
        for name, value, minimum in (("max_chunks", max_chunks, 1),
                ("max_characters", max_characters, 1),
                ("max_additional_per_document", max_additional_per_document, 0)):
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise ValueError(f"{name} must be an integer >= {minimum}.")
        self.max_chunks = max_chunks
        self.max_characters = max_characters
        self.max_additional_per_document = max_additional_per_document

    def build(self, selected: Sequence[FusedCandidate],
              candidate_pool: Sequence[FusedCandidate]) -> EvidenceContext:
        selected, candidate_pool = tuple(selected), tuple(candidate_pool)
        pool = {candidate.chunk.chunk_id: candidate for candidate in candidate_pool}
        if len(pool) != len(candidate_pool):
            raise ValueError("candidate_pool contains duplicate chunk IDs.")
        ids = [candidate.chunk.chunk_id for candidate in selected]
        if len(set(ids)) != len(ids):
            raise ValueError("selected contains duplicate chunk IDs.")
        ranks = [candidate.rank for candidate in candidate_pool]
        if any(type(rank) is not int or rank < 1 for rank in ranks) or any(
                a >= b for a, b in zip(ranks, ranks[1:])):
            raise ValueError("candidate_pool must have increasing, unique fusion ranks.")
        if any(isinstance(c.score, bool) or not isinstance(c.score, Real)
               or not isfinite(c.score) for c in candidate_pool):
            raise ValueError("candidate_pool scores must be finite numbers.")
        for candidate in selected:
            original = pool.get(candidate.chunk.chunk_id)
            if (original is None or candidate.chunk != original.chunk or candidate.score != original.score
                    or candidate.retrieval_methods != original.retrieval_methods):
                raise ValueError(f"Selected evidence/provenance differs from pool: {candidate.chunk.chunk_id}")
        if len(selected) > self.max_chunks:
            raise ContextBudgetError("Selected anchors exceed the chunk budget.")
        if not selected:
            return EvidenceContext((), (), (), "")
        documents = tuple(dict.fromkeys(c.chunk.document_id for c in selected))
        selected_ids = set(ids)
        passages = [EvidencePassage(f"E{i}", pool[c.chunk.chunk_id], "anchor")
                    for i, c in enumerate(selected, 1)]
        text = render_context(passages)
        if len(text) > self.max_characters:
            raise ContextBudgetError(
                f"Selected anchors require {len(text)} characters; budget is {self.max_characters}.")
        additions = Counter()
        skipped = []
        for candidate in candidate_pool:
            cid, doc = candidate.chunk.chunk_id, candidate.chunk.document_id
            if cid in selected_ids:
                continue
            reason = None
            if doc not in documents:
                reason = "outside_selected_documents"
            elif additions[doc] >= self.max_additional_per_document:
                reason = "additional_document_limit"
            elif len(passages) >= self.max_chunks:
                reason = "chunk_budget"
            if reason:
                skipped.append(SkippedPassage(cid, reason))
                continue
            extra = EvidencePassage(f"E{len(passages) + 1}", candidate, "supplement")
            proposed = render_context((*passages, extra))
            if len(proposed) > self.max_characters:
                skipped.append(SkippedPassage(cid, "character_budget"))
                continue
            passages.append(extra)
            text = proposed
            additions[doc] += 1
        return EvidenceContext(tuple(passages), documents, tuple(skipped), text)


class ShortDocumentContextBuilder:
    """Keep retrieval anchors; append complete short selected documents.

    Completeness here means all canonical chunks supplied for that document,
    not a guarantee of perfect parsing. Parent passages carry their canonical
    chunk directly, with no invented retrieval score or rank. Selection uses
    no query, expected answers, document IDs or reference labels.

    A document's missing chunks are accepted together or skipped together.
    Large documents retain anchors plus the original ranked supplement policy.
    """

    def __init__(self, chunks: Sequence[RetrievalChunk], *, max_chunks=60,
                 max_characters=32000, max_document_characters=6000):
        for name, value in (("max_chunks", max_chunks), ("max_characters", max_characters),
                            ("max_document_characters", max_document_characters)):
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        self.max_chunks = max_chunks
        self.max_characters = max_characters
        self.max_document_characters = max_document_characters
        self._catalog = {c.chunk_id: c for c in chunks}
        if len(self._catalog) != len(chunks):
            raise ValueError("Duplicate corpus chunk IDs")
        self._documents = {}
        for chunk in chunks:
            self._documents.setdefault(chunk.document_id, []).append(chunk)
        for document in self._documents.values():
            if len({c.order for c in document}) != len(document):
                raise ValueError("Duplicate order within a document")
            if len({c.source_path for c in document}) != 1:
                raise ValueError("A document must have one source path")
            document.sort(key=lambda c: c.order)

    def build(self, selected, candidate_pool):
        selected, candidate_pool = tuple(selected), tuple(candidate_pool)
        # Preserve the original identity/rank/score validation for retrieval.
        baseline = EvidenceContextBuilder(max_chunks=self.max_chunks,
            max_characters=self.max_characters, max_additional_per_document=0).build(
                selected, candidate_pool)
        for candidate in candidate_pool:
            if self._catalog.get(candidate.chunk.chunk_id) != candidate.chunk:
                raise ValueError("Retrieval chunk differs from the indexed corpus")
        passages = list(baseline.passages)
        present = {p.chunk.chunk_id for p in passages}
        skipped = []
        long_documents = set()
        for doc in baseline.selected_document_ids:
            document = self._documents[doc]
            missing = [c for c in document if c.chunk_id not in present]
            if sum(len(c.text) for c in document) > self.max_document_characters:
                long_documents.add(doc)
                skipped.extend(SkippedPassage(c.chunk_id, "document_too_large") for c in missing)
                continue
            extras = [EvidencePassage(f"E{len(passages) + i}", c, "parent_document")
                      for i, c in enumerate(missing, 1)]
            if (len(passages) + len(extras) > self.max_chunks
                    or len(render_context((*passages, *extras))) > self.max_characters):
                skipped.extend(SkippedPassage(c.chunk_id, "complete_document_budget") for c in missing)
                continue
            passages.extend(extras)
            present.update(c.chunk_id for c in missing)
        # For long documents only, retain at most one ranked extra per document.
        supplemented = set()
        for candidate in candidate_pool:
            chunk = candidate.chunk
            if (chunk.document_id not in long_documents or chunk.chunk_id in present
                    or chunk.document_id in supplemented):
                continue
            extra = EvidencePassage(f"E{len(passages) + 1}", candidate, "supplement")
            if len(passages) < self.max_chunks and len(render_context((*passages, extra))) <= self.max_characters:
                passages.append(extra)
                present.add(chunk.chunk_id)
                supplemented.add(chunk.document_id)
        skipped = tuple(p for p in skipped if p.chunk_id not in present)
        return EvidenceContext(tuple(passages), baseline.selected_document_ids,
                               skipped, render_context(passages))
