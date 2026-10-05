"""Integration tests for document-level PPTX ingestion composition."""

from pathlib import Path

import pytest

from app.ingestion.docling_parser import DoclingParser
from app.ingestion.document_parser import DocumentParser
from app.ingestion.pptx_native_enricher import PptxNativeEnricher
from app.ingestion.schemas import ChartBlock, NormalizedContent, TextBlock
from app.ingestion.xlsx_parser import XlsxParser


DOC_026 = Path(
    "data/source/corporate_repository/guidelines/"
    "DOC-026_AI_Workforce_Enablement_Guide.pptx"
)


@pytest.fixture(scope="module")
def doc_026_content() -> NormalizedContent:
    if not DOC_026.is_file():
        pytest.fail(f"Expected corpus document not found: {DOC_026}")

    parser = DocumentParser(
        docling_parser=DoclingParser(),
        xlsx_parser=XlsxParser(),
        pptx_native_enricher=PptxNativeEnricher(),
    )
    return parser.parse(DOC_026)


def _text_blocks(content: NormalizedContent) -> list[TextBlock]:
    return [
        block
        for block in content.ordered_blocks
        if isinstance(block, TextBlock)
    ]


def test_doc_026_is_parsed_through_document_parser(
    doc_026_content: NormalizedContent,
) -> None:
    assert isinstance(doc_026_content, NormalizedContent)
    assert doc_026_content.blocks


def test_doc_026_preserves_all_four_slide_locations(
    doc_026_content: NormalizedContent,
) -> None:
    blocks = _text_blocks(doc_026_content)

    assert {block.location.slide_number for block in blocks} == {1, 2, 3, 4}
    assert all(block.location.page_number is None for block in blocks)


def test_doc_026_preserves_known_text_after_composition(
    doc_026_content: NormalizedContent,
) -> None:
    projection = doc_026_content.text_projection

    assert "AI Workforce Enablement Guide" in projection
    assert "Mandatory baseline training" in projection
    assert "Role-specific learning" in projection
    assert "What training does not do" in projection
    assert "AI Governance Policy" in projection


def test_doc_026_has_no_native_chart_blocks(
    doc_026_content: NormalizedContent,
) -> None:
    assert not any(
        isinstance(block, ChartBlock)
        for block in doc_026_content.blocks
    )


def test_doc_026_preserves_docling_order_when_no_charts_exist(
    doc_026_content: NormalizedContent,
) -> None:
    orders = [block.order for block in doc_026_content.ordered_blocks]

    assert orders == list(range(len(orders)))


def test_doc_026_preserves_existing_pptx_semantics(
    doc_026_content: NormalizedContent,
) -> None:
    blocks = _text_blocks(doc_026_content)

    assert blocks[0].text == "AI Workforce Enablement Guide"
    assert blocks[0].kind == "paragraph"
