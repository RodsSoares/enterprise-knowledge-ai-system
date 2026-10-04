"""Integration tests for Docling parsing of the physical PPTX corpus."""

from pathlib import Path

import pytest

from app.ingestion.docling_parser import DoclingParser
from app.ingestion.schemas import TextBlock


DOC_026 = Path(
    "data/source/corporate_repository/guidelines/"
    "DOC-026_AI_Workforce_Enablement_Guide.pptx"
)


@pytest.fixture(scope="module")
def doc_026_content():
    if not DOC_026.is_file():
        pytest.fail(f"Expected corpus document not found: {DOC_026}")
    return DoclingParser().parse(DOC_026)


def _text_blocks(content) -> list[TextBlock]:
    return [
        block for block in content.ordered_blocks if isinstance(block, TextBlock)
    ]


def test_doc_026_is_parsed_from_physical_corpus(doc_026_content) -> None:
    assert doc_026_content.blocks


def test_doc_026_preserves_guide_title_text(doc_026_content) -> None:
    blocks = _text_blocks(doc_026_content)
    assert blocks[0].text == "AI Workforce Enablement Guide"


def test_doc_026_does_not_invent_title_semantics(doc_026_content) -> None:
    title = _text_blocks(doc_026_content)[0]
    assert title.kind == "paragraph"


def test_doc_026_maps_docling_page_ordinals_to_slides(doc_026_content) -> None:
    blocks = _text_blocks(doc_026_content)

    assert {block.location.slide_number for block in blocks} == {1, 2, 3, 4}
    assert all(block.location.page_number is None for block in blocks)


@pytest.mark.parametrize(
    ("text", "slide_number"),
    [
        ("AI Workforce Enablement Guide", 1),
        ("Mandatory baseline training", 2),
        ("Role-specific learning", 3),
        ("What training does not do", 4),
    ],
)
def test_doc_026_preserves_slide_specific_content(
    doc_026_content,
    text: str,
    slide_number: int,
) -> None:
    block = next(
        block
        for block in _text_blocks(doc_026_content)
        if block.text == text
    )
    assert block.location.slide_number == slide_number


def test_doc_026_preserves_mandatory_baseline_training(doc_026_content) -> None:
    projection = doc_026_content.text_projection

    assert "AI Fundamentals and Responsible Use" in projection
    assert "Information Classification and Safe Prompting" in projection
    assert "Human Accountability and Verification" in projection
    assert "Annual refresher" in projection


def test_doc_026_preserves_role_specific_learning(doc_026_content) -> None:
    projection = doc_026_content.text_projection

    assert "Users handling confidential data" in projection
    assert "Managers approving AI-assisted workflows" in projection
    assert "Procurement and vendor-management roles" in projection
    assert "Technical builders" in projection


def test_doc_026_preserves_training_governance_boundary(doc_026_content) -> None:
    projection = doc_026_content.text_projection

    assert "Training does not approve a tool or use case." in projection
    assert "Training does not override Information Security requirements." in projection
    assert "Training does not authorize confidential data" in projection
    assert "AI Governance Policy" in projection
