from pathlib import Path

import pytest

from app.chunking.schemas import RetrievalChunk


def test_retrieval_chunk_preserves_content_and_source_traceability() -> None:
    chunk = RetrievalChunk(
        chunk_id="chunk-00001",
        order=0,
        text="Evidence before generation.",
        source_block_ids=("text-00001", "text-00002"),
        source_path=Path("data/source/policy.pdf"),
        section_path=("Core Principles",),
        page_numbers=(2,),
        content_types=("text",),
    )

    assert chunk.chunk_id == "chunk-00001"
    assert chunk.order == 0
    assert chunk.text == "Evidence before generation."
    assert chunk.source_block_ids == ("text-00001", "text-00002")
    assert chunk.source_path == Path("data/source/policy.pdf")
    assert chunk.section_path == ("Core Principles",)
    assert chunk.page_numbers == (2,)
    assert chunk.slide_numbers == ()
    assert chunk.sheet_names == ()
    assert chunk.content_types == ("text",)


def test_retrieval_chunk_supports_multi_block_and_multi_page_provenance() -> None:
    chunk = RetrievalChunk(
        chunk_id="chunk-00002",
        order=1,
        text="Evidence spanning two pages.",
        source_block_ids=("text-00010", "image-00011", "text-00012"),
        source_path=Path("data/source/report.pdf"),
        section_path=("Incident Analysis",),
        page_numbers=(10, 11),
        content_types=("text", "image"),
    )

    assert chunk.source_block_ids == (
        "text-00010",
        "image-00011",
        "text-00012",
    )
    assert chunk.page_numbers == (10, 11)
    assert chunk.content_types == ("text", "image")


def test_retrieval_chunk_supports_slide_provenance() -> None:
    chunk = RetrievalChunk(
        chunk_id="chunk-00003",
        order=2,
        text="Quarterly demand analysis.",
        source_block_ids=("text-00020", "pptx-chart-s010-001"),
        source_path=Path("data/source/presentation.pptx"),
        section_path=("Demand Analysis",),
        slide_numbers=(10,),
        content_types=("text", "chart"),
    )

    assert chunk.slide_numbers == (10,)
    assert chunk.page_numbers == ()
    assert chunk.sheet_names == ()


def test_retrieval_chunk_supports_worksheet_provenance() -> None:
    chunk = RetrievalChunk(
        chunk_id="chunk-00004",
        order=3,
        text="Transportation rate card.",
        source_block_ids=("xlsx-sheet-1",),
        source_path=Path("data/source/rate-card.xlsx"),
        sheet_names=("Rate Card",),
        content_types=("spreadsheet",),
    )

    assert chunk.sheet_names == ("Rate Card",)
    assert chunk.page_numbers == ()
    assert chunk.slide_numbers == ()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("chunk_id", ""),
        ("chunk_id", "   "),
        ("text", ""),
        ("text", "   "),
    ],
)
def test_retrieval_chunk_rejects_empty_required_text_fields(
    field: str,
    value: str,
) -> None:
    kwargs = {
        "chunk_id": "chunk-00001",
        "order": 0,
        "text": "Valid evidence.",
        "source_block_ids": ("text-00001",),
        "source_path": Path("data/source/policy.pdf"),
        "content_types": ("text",),
    }
    kwargs[field] = value

    with pytest.raises(ValueError):
        RetrievalChunk(**kwargs)


def test_retrieval_chunk_rejects_negative_order() -> None:
    with pytest.raises(ValueError):
        RetrievalChunk(
            chunk_id="chunk-00001",
            order=-1,
            text="Valid evidence.",
            source_block_ids=("text-00001",),
            source_path=Path("data/source/policy.pdf"),
            content_types=("text",),
        )


def test_retrieval_chunk_requires_source_blocks() -> None:
    with pytest.raises(ValueError):
        RetrievalChunk(
            chunk_id="chunk-00001",
            order=0,
            text="Valid evidence.",
            source_block_ids=(),
            source_path=Path("data/source/policy.pdf"),
            content_types=("text",),
        )


def test_retrieval_chunk_requires_content_types() -> None:
    with pytest.raises(ValueError):
        RetrievalChunk(
            chunk_id="chunk-00001",
            order=0,
            text="Valid evidence.",
            source_block_ids=("text-00001",),
            source_path=Path("data/source/policy.pdf"),
            content_types=(),
        )


def test_retrieval_chunk_rejects_duplicate_provenance_values() -> None:
    with pytest.raises(ValueError):
        RetrievalChunk(
            chunk_id="chunk-00001",
            order=0,
            text="Valid evidence.",
            source_block_ids=("text-00001", "text-00001"),
            source_path=Path("data/source/policy.pdf"),
            content_types=("text",),
        )


def test_retrieval_chunk_rejects_invalid_page_number() -> None:
    with pytest.raises(ValueError):
        RetrievalChunk(
            chunk_id="chunk-00001",
            order=0,
            text="Valid evidence.",
            source_block_ids=("text-00001",),
            source_path=Path("data/source/policy.pdf"),
            page_numbers=(0,),
            content_types=("text",),
        )
