"""Unit tests for the document-level ingestion orchestrator.

These tests define the composition contract before implementation:
- format dispatch belongs to DocumentParser;
- specialized parsers remain independent;
- PPTX composes Docling content with native chart enrichment;
- composition produces one valid NormalizedContent with unique deterministic order;
- unsupported formats fail explicitly.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from app.ingestion.document_parser import DocumentParser
from app.ingestion.schemas import (
    ChartBlock,
    ChartSeries,
    NormalizedContent,
    SourceLocation,
    SpreadsheetBlock,
    SpreadsheetCell,
    TextBlock,
)


def _text_content() -> NormalizedContent:
    return NormalizedContent(
        blocks=(
            TextBlock(
                block_id="docling-text-001",
                order=0,
                kind="paragraph",
                text="Normalized source text.",
                location=SourceLocation(page_number=1),
            ),
        )
    )


def _pptx_text_content() -> NormalizedContent:
    return NormalizedContent(
        blocks=(
            TextBlock(
                block_id="docling-text-001",
                order=0,
                kind="paragraph",
                text="Slide text.",
                location=SourceLocation(slide_number=1),
            ),
            TextBlock(
                block_id="docling-text-002",
                order=1,
                kind="paragraph",
                text="Second slide.",
                location=SourceLocation(slide_number=2),
            ),
        )
    )


def _chart_blocks() -> tuple[ChartBlock, ...]:
    return (
        ChartBlock(
            block_id="pptx-chart-s001-001",
            order=0,
            chart_type="COLUMN_CLUSTERED",
            series=(ChartSeries(name="Actual", values=(10, 20)),),
            location=SourceLocation(slide_number=1),
            title="Performance",
            categories=("P1", "P2"),
        ),
        ChartBlock(
            block_id="pptx-chart-s002-001",
            order=1,
            chart_type="LINE",
            series=(ChartSeries(name="Forecast", values=(12, 22)),),
            location=SourceLocation(slide_number=2),
            title="Trend",
            categories=("P1", "P2"),
        ),
    )


def _xlsx_content() -> NormalizedContent:
    return NormalizedContent(
        blocks=(
            SpreadsheetBlock(
                block_id="xlsx-sheet-1",
                order=0,
                sheet_name="Data",
                cells=(
                    SpreadsheetCell(
                        coordinate="A1",
                        value="Metric",
                        data_type="s",
                    ),
                ),
                cell_range="A1:A1",
            ),
        )
    )


@pytest.mark.parametrize("suffix", [".pdf", ".docx", ".md"])
def test_document_parser_routes_docling_formats_to_docling_only(suffix: str) -> None:
    docling = Mock()
    xlsx = Mock()
    pptx_enricher = Mock()
    expected = _text_content()
    docling.parse.return_value = expected

    parser = DocumentParser(
        docling_parser=docling,
        xlsx_parser=xlsx,
        pptx_native_enricher=pptx_enricher,
    )
    source = Path(f"document{suffix}")

    result = parser.parse(source)

    assert result is expected
    docling.parse.assert_called_once_with(source)
    xlsx.parse.assert_not_called()
    pptx_enricher.extract_charts.assert_not_called()


def test_document_parser_routes_xlsx_to_specialized_parser_only() -> None:
    docling = Mock()
    xlsx = Mock()
    pptx_enricher = Mock()
    expected = _xlsx_content()
    xlsx.parse.return_value = expected

    parser = DocumentParser(
        docling_parser=docling,
        xlsx_parser=xlsx,
        pptx_native_enricher=pptx_enricher,
    )
    source = Path("workbook.xlsx")

    result = parser.parse(source)

    assert result is expected
    xlsx.parse.assert_called_once_with(source)
    docling.parse.assert_not_called()
    pptx_enricher.extract_charts.assert_not_called()


def test_document_parser_composes_pptx_docling_content_and_native_charts() -> None:
    docling = Mock()
    xlsx = Mock()
    pptx_enricher = Mock()
    docling.parse.return_value = _pptx_text_content()
    pptx_enricher.extract_charts.return_value = _chart_blocks()

    parser = DocumentParser(
        docling_parser=docling,
        xlsx_parser=xlsx,
        pptx_native_enricher=pptx_enricher,
    )
    source = Path("presentation.pptx")

    result = parser.parse(source)

    docling.parse.assert_called_once_with(source)
    pptx_enricher.extract_charts.assert_called_once_with(source)
    xlsx.parse.assert_not_called()

    assert isinstance(result, NormalizedContent)
    assert len(result.blocks) == 4
    assert [block.order for block in result.ordered_blocks] == [0, 1, 2, 3]
    assert len({block.block_id for block in result.blocks}) == 4
    assert sum(isinstance(block, TextBlock) for block in result.blocks) == 2
    assert sum(isinstance(block, ChartBlock) for block in result.blocks) == 2


def test_pptx_composition_orders_blocks_by_slide_then_source_kind() -> None:
    docling = Mock()
    xlsx = Mock()
    pptx_enricher = Mock()
    docling.parse.return_value = _pptx_text_content()
    pptx_enricher.extract_charts.return_value = _chart_blocks()

    parser = DocumentParser(
        docling_parser=docling,
        xlsx_parser=xlsx,
        pptx_native_enricher=pptx_enricher,
    )

    result = parser.parse(Path("presentation.pptx"))

    assert [
        (type(block).__name__, block.location.slide_number)
        for block in result.ordered_blocks
    ] == [
        ("TextBlock", 1),
        ("ChartBlock", 1),
        ("TextBlock", 2),
        ("ChartBlock", 2),
    ]


def test_pptx_composition_preserves_text_projection_without_flattening_charts() -> None:
    docling = Mock()
    xlsx = Mock()
    pptx_enricher = Mock()
    docling.parse.return_value = _pptx_text_content()
    pptx_enricher.extract_charts.return_value = _chart_blocks()

    parser = DocumentParser(
        docling_parser=docling,
        xlsx_parser=xlsx,
        pptx_native_enricher=pptx_enricher,
    )

    result = parser.parse(Path("presentation.pptx"))

    assert result.text_projection == "Slide text.\nSecond slide."
    assert "Performance" not in result.text_projection
    assert "Trend" not in result.text_projection


def test_pptx_without_native_charts_returns_docling_content_unchanged() -> None:
    docling = Mock()
    xlsx = Mock()
    pptx_enricher = Mock()
    expected = _pptx_text_content()
    docling.parse.return_value = expected
    pptx_enricher.extract_charts.return_value = ()

    parser = DocumentParser(
        docling_parser=docling,
        xlsx_parser=xlsx,
        pptx_native_enricher=pptx_enricher,
    )

    result = parser.parse(Path("presentation.pptx"))

    assert result is expected


def test_document_parser_rejects_non_path_input() -> None:
    parser = DocumentParser(
        docling_parser=Mock(),
        xlsx_parser=Mock(),
        pptx_native_enricher=Mock(),
    )

    with pytest.raises(TypeError, match="path must be a pathlib.Path"):
        parser.parse("document.pdf")  # type: ignore[arg-type]


@pytest.mark.parametrize("filename", ["document.txt", "document.csv", "document"])
def test_document_parser_rejects_formats_without_an_ingestion_strategy(
    filename: str,
) -> None:
    parser = DocumentParser(
        docling_parser=Mock(),
        xlsx_parser=Mock(),
        pptx_native_enricher=Mock(),
    )

    with pytest.raises(ValueError, match="Unsupported document format"):
        parser.parse(Path(filename))
