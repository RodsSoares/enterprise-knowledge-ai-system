"""Integration tests for Docling parsing against the physical corpus."""

from pathlib import Path

import pytest

from app.ingestion.docling_parser import DoclingParser
from app.ingestion.schemas import TextBlock


DOC_025 = Path(
    "data/source/corporate_repository/guidelines/"
    "DOC-025_AI_Procurement_Guidelines.md"
)


@pytest.fixture(scope="module")
def doc_025_content():
    """Parse DOC-025 once for the integration-test module."""
    if not DOC_025.is_file():
        pytest.fail(f"Expected corpus document not found: {DOC_025}")

    return DoclingParser().parse(DOC_025)


def test_doc_025_is_parsed_from_physical_corpus(doc_025_content) -> None:
    assert doc_025_content.blocks


def test_doc_025_preserves_document_title(doc_025_content) -> None:
    text_blocks = [
        block
        for block in doc_025_content.ordered_blocks
        if isinstance(block, TextBlock)
    ]

    assert any(
        block.kind == "title" and block.text == "AI Procurement Guidelines"
        for block in text_blocks
    )


@pytest.mark.parametrize(
    "heading",
    [
        "1. Purpose",
        "2. Procurement considerations",
        "3. AI supplier due diligence",
        "4. Approval boundary",
        "5. Supplier data",
        "6. Evaluation role",
    ],
)
def test_doc_025_preserves_expected_sections(
    doc_025_content,
    heading: str,
) -> None:
    headings = {
        block.text
        for block in doc_025_content.ordered_blocks
        if isinstance(block, TextBlock) and block.kind == "heading"
    }

    assert heading in headings


def test_doc_025_preserves_authority_boundary_statement(
    doc_025_content,
) -> None:
    projection = doc_025_content.text_projection

    assert "do not authorize a new AI tool" in projection
    assert "AI Governance Policy" in projection
    assert "Approval Authority Matrix" in projection


def test_doc_025_preserves_inline_spacing(doc_025_content) -> None:
    projection = doc_025_content.text_projection

    assert "products or services" in projection
    assert "products orservices" not in projection


def test_doc_025_preserves_supplier_data_boundary(doc_025_content) -> None:
    projection = doc_025_content.text_projection

    assert "confidential supplier or customer data" in projection
    assert "Data classification" in projection


def test_doc_025_section_content_keeps_structural_provenance(
    doc_025_content,
) -> None:
    paragraph = next(
        block
        for block in doc_025_content.ordered_blocks
        if isinstance(block, TextBlock)
        and "Formal approval is governed by" in block.text
    )

    assert paragraph.location.section_path
    assert paragraph.location.section_path[-1] == "4. Approval boundary"


def test_doc_025_remains_guidance_not_decision_authority(
    doc_025_content,
) -> None:
    projection = doc_025_content.text_projection

    assert "They are guidance" in projection
    assert "do not replace corporate policy" in projection
