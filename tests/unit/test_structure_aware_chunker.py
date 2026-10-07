from pathlib import Path

import pytest

from app.chunking.structure_aware_chunker import StructureAwareChunker
from app.ingestion.schemas import NormalizedContent, SourceLocation, TextBlock


SOURCE_PATH = Path("data/source/policy.pdf")


def _text_block(
    block_id: str,
    order: int,
    text: str,
    section_path: tuple[str, ...],
    page_number: int = 1,
) -> TextBlock:
    return TextBlock(
        block_id=block_id,
        order=order,
        text=text,
        kind="paragraph",
        location=SourceLocation(
            page_number=page_number,
            section_path=section_path,
        ),
    )


def test_chunker_groups_text_blocks_from_same_section() -> None:
    content = NormalizedContent(
        blocks=(
            _text_block("text-00001", 0, "Evidence before generation.", ("Core Principles",)),
            _text_block("text-00002", 1, "Retrieval before fluency.", ("Core Principles",)),
        )
    )
    chunker = StructureAwareChunker(target_chars=200, max_chars=300)
    chunks = chunker.chunk(content, SOURCE_PATH)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.chunk_id == "chunk-00001"
    assert chunk.order == 0
    assert chunk.text == "Evidence before generation.\n\nRetrieval before fluency."
    assert chunk.source_block_ids == ("text-00001", "text-00002")
    assert chunk.source_path == SOURCE_PATH
    assert chunk.section_path == ("Core Principles",)
    assert chunk.page_numbers == (1,)
    assert chunk.content_types == ("text",)


def test_chunker_starts_new_chunk_when_section_changes() -> None:
    content = NormalizedContent(
        blocks=(
            _text_block("text-00001", 0, "First section evidence.", ("Section A",)),
            _text_block("text-00002", 1, "Second section evidence.", ("Section B",)),
        )
    )
    chunker = StructureAwareChunker(target_chars=200, max_chars=300)
    chunks = chunker.chunk(content, SOURCE_PATH)

    assert len(chunks) == 2
    assert chunks[0].text == "First section evidence."
    assert chunks[0].section_path == ("Section A",)
    assert chunks[0].source_block_ids == ("text-00001",)
    assert chunks[1].text == "Second section evidence."
    assert chunks[1].section_path == ("Section B",)
    assert chunks[1].source_block_ids == ("text-00002",)


def test_chunker_splits_same_section_before_exceeding_max_size() -> None:
    content = NormalizedContent(
        blocks=(
            _text_block("text-00001", 0, "A" * 60, ("Long Section",)),
            _text_block("text-00002", 1, "B" * 60, ("Long Section",)),
        )
    )
    chunker = StructureAwareChunker(target_chars=80, max_chars=100)
    chunks = chunker.chunk(content, SOURCE_PATH)

    assert len(chunks) == 2
    assert chunks[0].text == "A" * 60
    assert chunks[0].source_block_ids == ("text-00001",)
    assert chunks[1].text == "B" * 60
    assert chunks[1].source_block_ids == ("text-00002",)


def test_chunker_preserves_multi_page_provenance() -> None:
    content = NormalizedContent(
        blocks=(
            _text_block("text-00001", 0, "Evidence from page one.", ("Incident",), page_number=1),
            _text_block("text-00002", 1, "Evidence from page two.", ("Incident",), page_number=2),
        )
    )
    chunker = StructureAwareChunker(target_chars=200, max_chars=300)
    chunks = chunker.chunk(content, SOURCE_PATH)

    assert len(chunks) == 1
    assert chunks[0].page_numbers == (1, 2)


def test_chunker_preserves_source_order() -> None:
    content = NormalizedContent(
        blocks=(
            _text_block("text-00001", 0, "First.", ("Section A",)),
            _text_block("text-00002", 1, "Second.", ("Section B",)),
            _text_block("text-00003", 2, "Third.", ("Section C",)),
        )
    )
    chunker = StructureAwareChunker(target_chars=200, max_chars=300)
    chunks = chunker.chunk(content, SOURCE_PATH)

    assert [chunk.order for chunk in chunks] == [0, 1, 2]
    assert [chunk.chunk_id for chunk in chunks] == ["chunk-00001", "chunk-00002", "chunk-00003"]
    assert [chunk.text for chunk in chunks] == ["First.", "Second.", "Third."]


def test_chunker_splits_single_text_block_that_exceeds_max_size() -> None:
    content = NormalizedContent(
        blocks=(
            _text_block("text-00001", 0, "A" * 250, ("Long Section",)),
        )
    )
    chunker = StructureAwareChunker(target_chars=80, max_chars=100)
    chunks = chunker.chunk(content, SOURCE_PATH)

    assert len(chunks) == 3
    assert [len(chunk.text) for chunk in chunks] == [100, 100, 50]
    assert all(len(chunk.text) <= chunker.max_chars for chunk in chunks)
    assert all(chunk.source_block_ids == ("text-00001",) for chunk in chunks)
    assert all(chunk.section_path == ("Long Section",) for chunk in chunks)


def test_chunker_starts_new_chunk_after_reaching_target_size() -> None:
    content = NormalizedContent(
        blocks=(
            _text_block("text-00001", 0, "A" * 60, ("Section A",)),
            _text_block("text-00002", 1, "B" * 45, ("Section A",)),
            _text_block("text-00003", 2, "C" * 30, ("Section A",)),
        )
    )
    chunker = StructureAwareChunker(target_chars=100, max_chars=150)
    chunks = chunker.chunk(content, SOURCE_PATH)

    assert len(chunks) == 2
    assert chunks[0].source_block_ids == ("text-00001", "text-00002")
    assert chunks[1].source_block_ids == ("text-00003",)
    assert chunks[0].text == ("A" * 60) + "\n\n" + ("B" * 45)
    assert chunks[1].text == "C" * 30


def test_chunker_rejects_zero_target_chars() -> None:
    with pytest.raises(
        ValueError,
        match="target_chars must be greater than or equal to 1",
    ):
        StructureAwareChunker(target_chars=0, max_chars=100)


def test_chunker_rejects_zero_max_chars() -> None:
    with pytest.raises(
        ValueError,
        match="max_chars must be greater than or equal to 1",
    ):
        StructureAwareChunker(target_chars=50, max_chars=0)


def test_chunker_rejects_target_chars_greater_than_max_chars() -> None:
    with pytest.raises(
        ValueError,
        match="target_chars must be less than or equal to max_chars",
    ):
        StructureAwareChunker(target_chars=101, max_chars=100)
