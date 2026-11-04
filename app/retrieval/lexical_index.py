"""Deterministic, in-memory BM25 lexical index."""

from collections import Counter
from dataclasses import dataclass
import math
import re
from collections.abc import Sequence

_TOKEN_RE = re.compile(r"[^\W_]+(?:[-_][^\W_]+)*", re.UNICODE)


def tokenize(text: str) -> tuple[str, ...]:
    """Case-insensitive Unicode tokens, preserving hyphenated identifiers."""
    return tuple(_TOKEN_RE.findall(text.casefold()))


@dataclass(frozen=True, slots=True)
class LexicalHit:
    chunk_id: str
    score: float
    rank: int


class BM25LexicalIndex:
    """BM25 index with deterministic tie-breaking by insertion order."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        if not math.isfinite(k1) or k1 <= 0:
            raise ValueError("k1 must be a positive finite number.")
        if not math.isfinite(b) or not 0 <= b <= 1:
            raise ValueError("b must be a finite number between 0 and 1.")
        self.k1 = k1
        self.b = b
        self._chunk_ids: tuple[str, ...] = ()
        self._frequencies: tuple[Counter[str], ...] = ()
        self._lengths: tuple[int, ...] = ()
        self._document_frequencies: Counter[str] = Counter()
        self._average_length = 0.0

    def add(self, chunk_ids: Sequence[str], texts: Sequence[str]) -> None:
        if not chunk_ids or len(chunk_ids) != len(texts):
            raise ValueError("chunk_ids and texts must be non-empty and aligned.")
        if any(not chunk_id.strip() for chunk_id in chunk_ids):
            raise ValueError("chunk_ids must not contain empty identifiers.")
        if len(set(chunk_ids)) != len(chunk_ids):
            raise ValueError("chunk_ids must not contain duplicates.")
        if any(not text.strip() for text in texts):
            raise ValueError("texts must not contain empty documents.")
        frequencies = tuple(Counter(tokenize(text)) for text in texts)
        lengths = tuple(sum(freq.values()) for freq in frequencies)
        if not all(lengths):
            raise ValueError("each text must contain at least one searchable token.")
        document_frequencies: Counter[str] = Counter()
        for freq in frequencies:
            document_frequencies.update(freq.keys())
        self._chunk_ids = tuple(chunk_ids)
        self._frequencies = frequencies
        self._lengths = lengths
        self._document_frequencies = document_frequencies
        self._average_length = sum(lengths) / len(lengths)

    def search(self, query: str, top_k: int = 5) -> tuple[LexicalHit, ...]:
        if not self._chunk_ids:
            raise ValueError("lexical index is empty.")
        if top_k < 1:
            raise ValueError("top_k must be greater than or equal to 1.")
        terms = set(tokenize(query))
        if not terms:
            raise ValueError("query must contain searchable tokens.")
        count = len(self._chunk_ids)
        scores: list[tuple[int, float]] = []
        for index, (frequencies, length) in enumerate(zip(self._frequencies, self._lengths)):
            score = 0.0
            for term in terms:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                df = self._document_frequencies[term]
                idf = math.log1p((count - df + 0.5) / (df + 0.5))
                denominator = frequency + self.k1 * (1 - self.b + self.b * length / self._average_length)
                score += idf * frequency * (self.k1 + 1) / denominator
            if score > 0:
                scores.append((index, score))
        scores.sort(key=lambda item: (-item[1], item[0]))
        return tuple(
            LexicalHit(self._chunk_ids[index], score, rank)
            for rank, (index, score) in enumerate(scores[:top_k], start=1)
        )
