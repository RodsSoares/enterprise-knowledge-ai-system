import pytest

from app.retrieval.vector_index import NumPyVectorIndex


def test_vector_index_returns_candidates_by_cosine_similarity() -> None:
    index = NumPyVectorIndex()
    index.add(
        chunk_ids=("chunk-a", "chunk-b", "chunk-c"),
        embeddings=((1.0, 0.0), (0.0, 1.0), (0.8, 0.2)),
    )

    hits = index.search((1.0, 0.0), top_k=3)

    assert tuple(hit.chunk_id for hit in hits) == ("chunk-a", "chunk-c", "chunk-b")
    assert tuple(hit.rank for hit in hits) == (1, 2, 3)
    assert hits[0].score == pytest.approx(1.0)


def test_vector_index_uses_cosine_similarity_not_vector_magnitude() -> None:
    index = NumPyVectorIndex()
    index.add(
        chunk_ids=("same-direction-large", "different-direction"),
        embeddings=((100.0, 0.0), (1.0, 1.0)),
    )

    hits = index.search((1.0, 0.0), top_k=2)

    assert hits[0].chunk_id == "same-direction-large"
    assert hits[0].score == pytest.approx(1.0)


def test_vector_index_limits_results_to_top_k() -> None:
    index = NumPyVectorIndex()
    index.add(
        chunk_ids=("chunk-a", "chunk-b", "chunk-c"),
        embeddings=((1.0, 0.0), (0.8, 0.2), (0.0, 1.0)),
    )

    hits = index.search((1.0, 0.0), top_k=2)

    assert len(hits) == 2
    assert tuple(hit.rank for hit in hits) == (1, 2)


def test_vector_index_returns_all_available_results_when_top_k_is_larger() -> None:
    index = NumPyVectorIndex()
    index.add(
        chunk_ids=("chunk-a", "chunk-b"),
        embeddings=((1.0, 0.0), (0.0, 1.0)),
    )

    assert len(index.search((1.0, 0.0), top_k=10)) == 2


def test_vector_index_breaks_equal_score_ties_by_insertion_order() -> None:
    index = NumPyVectorIndex()
    index.add(
        chunk_ids=("chunk-first", "chunk-second"),
        embeddings=((1.0, 0.0), (1.0, 0.0)),
    )

    hits = index.search((1.0, 0.0), top_k=2)

    assert tuple(hit.chunk_id for hit in hits) == ("chunk-first", "chunk-second")


@pytest.mark.parametrize(
    ("chunk_ids", "embeddings", "message"),
    [
        ((), (), "chunk_ids"),
        (("chunk-a",), (), "same number"),
        (("chunk-a", "chunk-a"), ((1.0, 0.0), (0.0, 1.0)), "duplicates"),
        (("chunk-a", "chunk-b"), ((1.0, 0.0), (1.0,)), "consistent dimensions"),
        (("chunk-a",), ((0.0, 0.0),), "zero vectors"),
    ],
)
def test_vector_index_rejects_invalid_index_data(
    chunk_ids,
    embeddings,
    message: str,
) -> None:
    index = NumPyVectorIndex()

    with pytest.raises(ValueError, match=message):
        index.add(chunk_ids=chunk_ids, embeddings=embeddings)


def test_vector_index_rejects_search_before_indexing() -> None:
    with pytest.raises(ValueError, match="empty"):
        NumPyVectorIndex().search((1.0, 0.0), top_k=1)


def test_vector_index_rejects_invalid_top_k() -> None:
    index = NumPyVectorIndex()
    index.add(chunk_ids=("chunk-a",), embeddings=((1.0, 0.0),))

    with pytest.raises(ValueError, match="top_k"):
        index.search((1.0, 0.0), top_k=0)


def test_vector_index_rejects_query_with_wrong_dimension() -> None:
    index = NumPyVectorIndex()
    index.add(chunk_ids=("chunk-a",), embeddings=((1.0, 0.0),))

    with pytest.raises(ValueError, match="dimension"):
        index.search((1.0, 0.0, 0.0), top_k=1)


def test_vector_index_rejects_zero_query_vector() -> None:
    index = NumPyVectorIndex()
    index.add(chunk_ids=("chunk-a",), embeddings=((1.0, 0.0),))

    with pytest.raises(ValueError, match="zero vector"):
        index.search((0.0, 0.0), top_k=1)
