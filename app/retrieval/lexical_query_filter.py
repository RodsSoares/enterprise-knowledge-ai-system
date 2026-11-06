"""Opt-in PT/EN function-word filtering for the lexical branch only."""

from typing import Protocol

from app.retrieval.lexical_index import tokenize
from app.retrieval.schemas import RetrievalCandidate


# Project-owned initial policy: grammatical words, not corpus/document names.
# Negation terms, numbers, technical acronyms and hyphenated IDs are retained.
# This filters query terms before BM25 scoring; it does not translate queries,
# remove hits after ranking, or change document lengths/IDF in the index.
FILTER_VERSION = "pt_en_function_words_v1"
FUNCTION_WORDS = frozenset("""
a an and are as at be been being but by can could did do does for from had has
have how i if in into is it its may of on or our should than that the their them
there these they this those to was were what when where which who will with
would you your
à às ao aos com da das de dos e ela elas ele eles em era eram essa essas esse
esses esta estas este estes eu foi foram isso isto já lhe lhes mais mas me meu
meus minha minhas muita muitas muito muitos na nas nos o os ou para pela pelas
pelo pelos por qual quais quando que quem se seu seus sua suas são ser sou tem
têm um uma umas uns é você vocês
""".split())


class LexicalRetrieverProtocol(Protocol):
    def retrieve(self, query: str, top_k: int = 5) -> tuple[RetrievalCandidate, ...]: ...


def filter_lexical_query(query: str) -> str:
    """Retain searchable content tokens; an empty result means no lexical vote."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string.")
    return " ".join(token for token in tokenize(query) if token not in FUNCTION_WORDS)


class FilteredLexicalRetriever:
    """Wrap the existing lexical adapter without changing HybridRetriever defaults.

    HybridRetriever can receive this wrapper as its lexical_retriever. The
    vector retriever continues receiving the original, unmodified question.
    All-empty filtered queries return no lexical candidates, allowing the
    existing fusion to use the vector branch alone.
    """

    def __init__(self, retriever: LexicalRetrieverProtocol) -> None:
        self._retriever = retriever

    def retrieve(self, query: str, top_k: int = 5) -> tuple[RetrievalCandidate, ...]:
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be a positive integer.")
        filtered = filter_lexical_query(query)
        if not filtered:
            return ()
        return self._retriever.retrieve(filtered, top_k=top_k)
