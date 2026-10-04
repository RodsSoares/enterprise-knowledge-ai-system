"""Integration tests for Docling parsing of the physical DOCX corpus."""

from pathlib import Path

import pytest

from app.ingestion.docling_parser import DoclingParser
from app.ingestion.schemas import TextBlock


DOC_010 = Path(
    "data/source/corporate_repository/sops/"
    "DOC-010_Security_Incident_SOP.docx"
)


@pytest.fixture(scope="module")
def doc_010_content():
    """Parse DOC-010 once for the integration-test module."""
    if not DOC_010.is_file():
        pytest.fail(f"Expected corpus document not found: {DOC_010}")

    return DoclingParser().parse(DOC_010)


def _text_blocks(content) -> list[TextBlock]:
    return [
        block
        for block in content.ordered_blocks
        if isinstance(block, TextBlock)
    ]


def test_doc_010_is_parsed_from_physical_corpus(doc_010_content) -> None:
    assert doc_010_content.blocks


def test_doc_010_preserves_document_title_text(doc_010_content) -> None:
    blocks = _text_blocks(doc_010_content)

    assert any(
        block.text == "SECURITY INCIDENT SOP"
        for block in blocks
    )


@pytest.mark.parametrize(
    "heading",
    [
        "1. Purpose",
        "2. Trigger",
        "3. Immediate actions",
        "4. Supplier disclosure",
        "5. Closure",
        "6. Related documents",
    ],
)
def test_doc_010_preserves_expected_sections(
    doc_010_content,
    heading: str,
) -> None:
    headings = {
        block.text
        for block in _text_blocks(doc_010_content)
        if block.kind == "heading"
    }

    assert heading in headings


def test_doc_010_preserves_all_immediate_action_steps(doc_010_content) -> None:
    blocks = _text_blocks(doc_010_content)

    list_items = [
        block
        for block in blocks
        if block.kind == "list_item"
        and block.location.section_path
        and block.location.section_path[-1] == "3. Immediate actions"
    ]

    assert len(list_items) == 6

    projection = "\n".join(block.text for block in list_items)

    assert "Stop further disclosure" in projection
    assert "Notify the Information Security incident channel immediately" in projection
    assert "Preserve relevant messages, logs, files, and screenshots" in projection
    assert "Follow containment, notification, and remediation instructions" in projection


def test_doc_010_immediate_actions_keep_section_provenance(
    doc_010_content,
) -> None:
    block = next(
        block
        for block in _text_blocks(doc_010_content)
        if "Preserve relevant messages" in block.text
    )

    assert block.location.section_path
    assert block.location.section_path[-1] == "3. Immediate actions"


def test_doc_010_preserves_supplier_disclosure_rule(doc_010_content) -> None:
    projection = doc_010_content.text_projection

    assert "accidentally sent to a supplier or carrier" in projection
    assert "must report the incident immediately" in projection
    assert "Information Security coordinates containment" in projection


def test_doc_010_preserves_evidence_protection_instruction(
    doc_010_content,
) -> None:
    projection = doc_010_content.text_projection

    assert "without destroying evidence" in projection
    assert "Do not instruct the external recipient to delete evidence" in projection


def test_doc_010_preserves_closure_requirements(doc_010_content) -> None:
    projection = doc_010_content.text_projection

    assert "incident is closed only after" in projection
    assert "impact assessment" in projection
    assert "required notifications" in projection
    assert "follow-up actions" in projection


def test_doc_010_preserves_related_document_references(
    doc_010_content,
) -> None:
    projection = doc_010_content.text_projection

    assert "Information Security Policy" in projection
    assert "Data Sharing Policy" in projection
    assert "applicable supplier agreement" in projection
