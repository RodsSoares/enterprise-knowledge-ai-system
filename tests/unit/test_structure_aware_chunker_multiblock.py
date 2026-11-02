from pathlib import Path

from app.chunking.structure_aware_chunker import StructureAwareChunker
from app.ingestion.schemas import (
    NormalizedContent,
    SourceLocation,
    SpreadsheetBlock,
    SpreadsheetCell,
    TextBlock,
)


def test_chunker_serializes_spreadsheet_blocks_into_retrieval_chunks():
    content = NormalizedContent(
        blocks=(
            SpreadsheetBlock(
                block_id="sheet-1",
                order=0,
                sheet_name="Approval Matrix",
                cell_range="A1:B2",
                cells=(
                    SpreadsheetCell(coordinate="A1", value="Role"),
                    SpreadsheetCell(coordinate="B1", value="Approval limit"),
                    SpreadsheetCell(coordinate="A2", value="Manager"),
                    SpreadsheetCell(coordinate="B2", value=10000),
                ),
            ),
        )
    )

    chunks = StructureAwareChunker(target_chars=1200, max_chars=1800).chunk(
        content, Path("DOC-012.xlsx"), "DOC-012"
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_id == "DOC-012::chunk-00001"
    assert chunks[0].document_id == "DOC-012"
    assert chunks[0].content_types == ("spreadsheet",)
    assert chunks[0].sheet_names == ("Approval Matrix",)
    assert "A2 = Manager" in chunks[0].text
    assert "B2 = 10000" in chunks[0].text


def test_chunker_preserves_text_behavior_and_global_identity():
    content = NormalizedContent(
        blocks=(
            TextBlock(
                block_id="text-1",
                order=0,
                kind="paragraph",
                text="Enterprise policy evidence.",
                location=SourceLocation(section_path=("Policy",)),
            ),
        )
    )

    chunk = StructureAwareChunker(target_chars=1200, max_chars=1800).chunk(
        content, Path("DOC-005.pdf"), "DOC-005"
    )[0]

    assert chunk.chunk_id == "DOC-005::chunk-00001"
    assert chunk.content_types == ("text",)
    assert chunk.section_path == ("Policy",)


def test_oversized_spreadsheet_serialization_respects_max_chars():
    long_value = "X" * 300
    content = NormalizedContent(
        blocks=(
            SpreadsheetBlock(
                block_id="sheet-large",
                order=0,
                sheet_name="Large",
                cells=(SpreadsheetCell(coordinate="A1", value=long_value),),
            ),
        )
    )

    chunks = StructureAwareChunker(target_chars=80, max_chars=100).chunk(
        content, Path("DOC-012.xlsx"), "DOC-012"
    )

    assert len(chunks) > 1
    assert all(len(chunk.text) <= 100 for chunk in chunks)
    assert all(chunk.content_types == ("spreadsheet",) for chunk in chunks)
    assert all(chunk.sheet_names == ("Large",) for chunk in chunks)
