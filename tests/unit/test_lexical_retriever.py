from pathlib import Path

import pytest

from app.chunking.schemas import RetrievalChunk
from app.retrieval.lexical_index import BM25LexicalIndex
from app.retrieval.lexical_retriever import LexicalRetriever


def make_chunk(identifier, text):
    return RetrievalChunk(
        chunk_id=identifier, document_id=identifier.split("::")[0],
        order=0, text=text, source_block_ids=("block-1",),
        source_path=Path("sample.pdf"), content_types=("text",),
    )


def test_returns_canonical_candidates_with_provenance():
    chunks = (make_chunk("DOC-005::chunk-1", "confidential data sharing"),
              make_chunk("DOC-006::chunk-1", "security policy"))
    index = BM25LexicalIndex()
    index.add(tuple(c.chunk_id for c in chunks), tuple(c.text for c in chunks))
    result = LexicalRetriever(index, chunks).retrieve("confidential")
    assert len(result) == 1
    assert result[0].retrieval_method == "lexical"
    assert result[0].chunk.document_id == "DOC-005"
    assert result[0].rank == 1
    assert result[0].score > 0


def test_duplicate_chunk_ids_rejected():
    chunk = make_chunk("DOC-005::chunk-1", "text")
    with pytest.raises(ValueError):
        LexicalRetriever(BM25LexicalIndex(), (chunk, chunk))


def test_unknown_index_hit_rejected():
    index = BM25LexicalIndex()
    index.add(("other",), ("confidential",))
    retriever = LexicalRetriever(index, (make_chunk("DOC-005::chunk-1", "confidential"),))
    with pytest.raises(ValueError, match="unknown chunk_id"):
        retriever.retrieve("confidential")
