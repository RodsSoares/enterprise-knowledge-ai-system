import pytest

from app.retrieval.lexical_index import BM25LexicalIndex, tokenize


def test_tokenization_preserves_identifiers():
    assert tokenize("DOC-005, AI_Governance! Árvore") == ("doc-005", "ai_governance", "árvore")


def test_ranking_and_positive_matches_only():
    index = BM25LexicalIndex()
    index.add(("a", "b", "c"), ("supplier contract", "supplier supplier contract", "warehouse stock"))
    hits = index.search("supplier", top_k=5)
    assert [hit.chunk_id for hit in hits] == ["b", "a"]
    assert [hit.rank for hit in hits] == [1, 2]
    assert index.search("nonexistent") == ()


def test_ties_are_stable():
    index = BM25LexicalIndex()
    index.add(("a", "b"), ("same text", "same text"))
    assert [hit.chunk_id for hit in index.search("same")] == ["a", "b"]


@pytest.mark.parametrize("ids,texts", [([], []), (["a"], []), (["a", "a"], ["x", "y"]), (["a"], [" "])])
def test_invalid_corpus(ids, texts):
    with pytest.raises(ValueError):
        BM25LexicalIndex().add(ids, texts)


def test_invalid_search():
    index = BM25LexicalIndex()
    with pytest.raises(ValueError):
        index.search("anything")
    index.add(("a",), ("text",))
    with pytest.raises(ValueError):
        index.search("text", top_k=0)
    with pytest.raises(ValueError):
        index.search("!!!")


def test_reindex_replaces_corpus():
    index = BM25LexicalIndex()
    index.add(("a",), ("old",))
    index.add(("b",), ("new",))
    assert index.search("old") == ()
    assert index.search("new")[0].chunk_id == "b"
