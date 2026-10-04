"""Unit tests for the Docling parsing adapter."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.ingestion.docling_parser import (
    DoclingParser,
    _normalize_markdown_inline,
    _source_location,
)
from app.ingestion.schemas import TableBlock, TextBlock


@pytest.fixture
def markdown_file(tmp_path: Path) -> Path:
    source = tmp_path / "sample.md"
    source.write_text(
        """# AI Procurement Guidelines

## Approved Use

AI tools may support supplier analysis.

- Use approved tools.
- Protect confidential data.

## Escalation

Escalate exceptions to the responsible authority.
""",
        encoding="utf-8",
    )
    return source


def test_markdown_inline_normalization_preserves_semantic_spacing() -> None:
    source = (
        "These guidelines do **not** authorize a tool. "
        "Products or **services** remain controlled."
    )
    assert _normalize_markdown_inline(source) == (
        "These guidelines do not authorize a tool. "
        "Products or services remain controlled."
    )


def test_markdown_inline_normalization_preserves_block_structure() -> None:
    source = "# Title\n\n## Section\n\n- Use **approved** tools.\n"
    assert _normalize_markdown_inline(source) == (
        "# Title\n\n## Section\n\n- Use approved tools.\n"
    )


def test_source_location_maps_pdf_ordinal_to_page_number() -> None:
    item = SimpleNamespace(prov=[SimpleNamespace(page_no=3)])
    location = _source_location(item, Path("policy.pdf"), ("Section",))

    assert location.page_number == 3
    assert location.slide_number is None
    assert location.section_path == ("Section",)


def test_source_location_maps_pptx_ordinal_to_slide_number() -> None:
    item = SimpleNamespace(prov=[SimpleNamespace(page_no=4)])
    location = _source_location(item, Path("guide.pptx"))

    assert location.page_number is None
    assert location.slide_number == 4


def test_source_location_preserves_missing_provenance() -> None:
    item = SimpleNamespace(prov=[])
    location = _source_location(item, Path("guide.pptx"))

    assert location.page_number is None
    assert location.slide_number is None


def test_docling_parser_normalizes_markdown_structure(markdown_file: Path) -> None:
    content = DoclingParser().parse(markdown_file)
    text_blocks = [
        block for block in content.ordered_blocks if isinstance(block, TextBlock)
    ]
    assert text_blocks
    assert any(
        block.kind == "title" and block.text == "AI Procurement Guidelines"
        for block in text_blocks
    )
    assert any(
        block.kind == "heading" and block.text == "Approved Use"
        for block in text_blocks
    )
    assert any(
        block.kind == "list_item" and block.text == "Use approved tools."
        for block in text_blocks
    )


def test_docling_parser_preserves_section_path(markdown_file: Path) -> None:
    content = DoclingParser().parse(markdown_file)
    target = next(
        block
        for block in content.ordered_blocks
        if isinstance(block, TextBlock)
        and block.text == "AI tools may support supplier analysis."
    )
    assert target.location.section_path[-1] == "Approved Use"


def test_docling_parser_returns_deterministic_block_order(markdown_file: Path) -> None:
    content = DoclingParser().parse(markdown_file)
    orders = [block.order for block in content.ordered_blocks]
    assert orders == list(range(len(orders)))


def test_docling_parser_text_projection_contains_source_content(markdown_file: Path) -> None:
    content = DoclingParser().parse(markdown_file)
    assert "AI Procurement Guidelines" in content.text_projection
    assert "Protect confidential data." in content.text_projection
    assert "Escalation" in content.text_projection


def test_docling_parser_rejects_missing_source(tmp_path: Path) -> None:
    missing = tmp_path / "missing.md"
    with pytest.raises(FileNotFoundError):
        DoclingParser().parse(missing)


def test_docling_parser_rejects_non_path_input() -> None:
    with pytest.raises(TypeError, match="pathlib.Path"):
        DoclingParser().parse("sample.md")  # type: ignore[arg-type]


def test_markdown_baseline_does_not_create_spreadsheet_blocks(markdown_file: Path) -> None:
    content = DoclingParser().parse(markdown_file)
    assert all(not isinstance(block, TableBlock) for block in content.blocks)
