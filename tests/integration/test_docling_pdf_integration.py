"""Integration tests for Docling parsing of the physical PDF corpus."""

from pathlib import Path

import pytest

from app.ingestion.docling_parser import DoclingParser
from app.ingestion.schemas import TableBlock, TextBlock


DOC_005 = Path(
    "data/source/corporate_repository/policies/"
    "DOC-005_Data_Sharing_Policy.pdf"
)


@pytest.fixture(scope="module")
def doc_005_content():
    """Parse DOC-005 once for the integration-test module."""
    if not DOC_005.is_file():
        pytest.fail(f"Expected corpus document not found: {DOC_005}")

    return DoclingParser().parse(DOC_005)


def _text_blocks(content) -> list[TextBlock]:
    return [
        block
        for block in content.ordered_blocks
        if isinstance(block, TextBlock)
    ]


def _table_blocks(content) -> list[TableBlock]:
    return [
        block
        for block in content.ordered_blocks
        if isinstance(block, TableBlock)
    ]


def test_doc_005_is_parsed_from_physical_corpus(doc_005_content) -> None:
    assert doc_005_content.blocks


def test_doc_005_preserves_policy_title_text(doc_005_content) -> None:
    assert any(
        block.text == "DATA SHARING POLICY"
        for block in _text_blocks(doc_005_content)
    )


@pytest.mark.parametrize(
    "heading",
    [
        "1. Purpose",
        "2. Scope",
        "3. Information classification and minimum controls",
        "4. Sharing with transportation carriers",
        "5. Approved channels",
        "6. Supplier and AI-related use",
        "7. Exceptions",
    ],
)
def test_doc_005_preserves_expected_sections(
    doc_005_content,
    heading: str,
) -> None:
    headings = {
        block.text
        for block in _text_blocks(doc_005_content)
        if block.kind == "heading"
    }

    assert heading in headings


def test_doc_005_preserves_page_provenance(doc_005_content) -> None:
    """All provenance-bearing content in this one-page PDF should point to page 1."""
    blocks_with_page = [
        block
        for block in doc_005_content.ordered_blocks
        if block.location.page_number is not None
    ]

    assert blocks_with_page
    assert {block.location.page_number for block in blocks_with_page} == {1}


def test_doc_005_extracts_classification_table(doc_005_content) -> None:
    tables = _table_blocks(doc_005_content)

    assert tables

    projection = "\n".join(
        " | ".join("" if value is None else value for value in row)
        for table in tables
        for row in table.rows
    )

    assert "Classification" in projection
    assert "External sharing rule" in projection
    assert "Minimum channel/control" in projection
    assert "Confidential" in projection
    assert "Restricted" in projection


def test_doc_005_table_preserves_page_provenance(doc_005_content) -> None:
    tables = _table_blocks(doc_005_content)

    assert tables
    assert all(table.location.page_number == 1 for table in tables)


def test_doc_005_preserves_confidential_sharing_rule(doc_005_content) -> None:
    projection = doc_005_content.text_projection

    assert "authorized recipient" in projection
    assert "approved business purpose" in projection
    assert "Approved secure transfer or controlled platform" in projection


def test_doc_005_preserves_carrier_restriction(doc_005_content) -> None:
    projection = doc_005_content.text_projection

    assert "contracted logistics service" in projection
    assert "ordinary unprotected email" in projection
    assert "contracted carrier" in projection


def test_doc_005_preserves_approved_channel_rule(doc_005_content) -> None:
    projection = doc_005_content.text_projection

    assert "approved secure channel" in projection
    assert "Corporate email alone" in projection
    assert "approved secure transfer" in projection


def test_doc_005_preserves_ai_cross_policy_reference(doc_005_content) -> None:
    projection = doc_005_content.text_projection

    assert "AI Governance Policy" in projection
    assert "Information Security Policy" in projection


def test_doc_005_preserves_exception_boundary(doc_005_content) -> None:
    projection = doc_005_content.text_projection

    assert "documented business justification" in projection
    assert "An operational SOP cannot independently create an exception" in projection
