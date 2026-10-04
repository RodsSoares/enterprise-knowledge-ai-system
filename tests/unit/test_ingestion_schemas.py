"""Unit tests for canonical ingestion schemas."""

from datetime import date
from pathlib import Path

import pytest

from app.ingestion.schemas import (
    CanonicalDocument,
    NormalizedContent,
    SourceLocation,
    SpreadsheetBlock,
    SpreadsheetCell,
    TableBlock,
    TextBlock,
)


def _text_block(
    *,
    block_id: str = "block-001",
    order: int = 0,
    text: str = "Controlled enterprise content.",
    parent_id: str | None = None,
    location: SourceLocation | None = None,
) -> TextBlock:
    return TextBlock(
        block_id=block_id,
        order=order,
        kind="paragraph",
        text=text,
        parent_id=parent_id,
        location=location or SourceLocation(),
    )


def _document(content: NormalizedContent | None = None) -> CanonicalDocument:
    return CanonicalDocument(
        document_id="DOC-001",
        key="transportation_policy_2026",
        title="Transportation Policy",
        source_path=Path("data/source/policies/transportation_policy_2026.pdf"),
        format="pdf",
        document_type="corporate_policy",
        domain="transportation",
        version="3.0",
        effective_date=date(2026, 1, 1),
        status="active",
        authority_level=4,
        content=content or NormalizedContent(blocks=(_text_block(),)),
        supersedes="DOC-002",
        entity_refs=("R001",),
    )


def test_source_location_accepts_supported_structural_locators() -> None:
    location = SourceLocation(
        page_number=3,
        slide_number=2,
        sheet_name="Approvals",
        cell_range="B4:D8",
        section_path=("Governance", "Emergency Contracting"),
    )

    assert location.page_number == 3
    assert location.slide_number == 2
    assert location.sheet_name == "Approvals"
    assert location.cell_range == "B4:D8"
    assert location.section_path == ("Governance", "Emergency Contracting")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("page_number", 0),
        ("slide_number", 0),
        ("sheet_name", "   "),
        ("cell_range", ""),
    ],
)
def test_source_location_rejects_invalid_locators(field: str, value: object) -> None:
    with pytest.raises(ValueError):
        SourceLocation(**{field: value})


def test_text_block_preserves_hierarchy_and_provenance() -> None:
    location = SourceLocation(
        page_number=2,
        section_path=("Data Sharing", "External Sharing"),
    )
    block = TextBlock(
        block_id="paragraph-001",
        order=1,
        kind="paragraph",
        text="Confidential data requires an approved secure channel.",
        location=location,
        parent_id="heading-001",
    )

    assert block.location.page_number == 2
    assert block.location.section_path[-1] == "External Sharing"
    assert block.parent_id == "heading-001"


def test_table_block_preserves_tabular_relationships() -> None:
    table = TableBlock(
        block_id="table-001",
        order=0,
        headers=("Role", "Limit"),
        rows=(
            ("Manager", "50000"),
            ("Director", "100000"),
        ),
        caption="Approval limits",
        location=SourceLocation(page_number=4),
    )

    assert table.headers == ("Role", "Limit")
    assert table.rows[1][0] == "Director"
    assert table.location.page_number == 4


def test_table_block_rejects_inconsistent_row_widths() -> None:
    with pytest.raises(ValueError, match="same number of columns"):
        TableBlock(
            block_id="table-001",
            order=0,
            rows=(
                ("A", "B"),
                ("C",),
            ),
        )


def test_table_block_rejects_header_width_mismatch() -> None:
    with pytest.raises(ValueError, match="same number of columns"):
        TableBlock(
            block_id="table-001",
            order=0,
            headers=("A",),
            rows=(("1", "2"),),
        )


def test_spreadsheet_block_preserves_cells_formulas_and_range() -> None:
    block = SpreadsheetBlock(
        block_id="sheet-001",
        order=0,
        sheet_name="Approval Matrix",
        cell_range="A1:C3",
        table_name="ApprovalAuthority",
        cells=(
            SpreadsheetCell(coordinate="A1", value="Role", data_type="s"),
            SpreadsheetCell(coordinate="B1", value="Limit", data_type="s"),
            SpreadsheetCell(
                coordinate="C3",
                value=150000,
                formula="=B3*1.5",
                data_type="n",
            ),
        ),
    )

    assert block.sheet_name == "Approval Matrix"
    assert block.cell_range == "A1:C3"
    assert block.cells[2].formula == "=B3*1.5"


def test_spreadsheet_block_rejects_duplicate_coordinates() -> None:
    with pytest.raises(ValueError, match="coordinates must be unique"):
        SpreadsheetBlock(
            block_id="sheet-001",
            order=0,
            sheet_name="Approvals",
            cells=(
                SpreadsheetCell(coordinate="A1", value="first"),
                SpreadsheetCell(coordinate="A1", value="duplicate"),
            ),
        )


def test_normalized_content_orders_blocks_deterministically() -> None:
    content = NormalizedContent(
        blocks=(
            _text_block(block_id="second", order=2, text="Second"),
            _text_block(block_id="first", order=1, text="First"),
        )
    )

    assert tuple(block.block_id for block in content.ordered_blocks) == (
        "first",
        "second",
    )


def test_normalized_content_rejects_duplicate_block_ids() -> None:
    with pytest.raises(ValueError, match="block_id values must be unique"):
        NormalizedContent(
            blocks=(
                _text_block(block_id="duplicate", order=0),
                _text_block(block_id="duplicate", order=1),
            )
        )


def test_normalized_content_rejects_duplicate_orders() -> None:
    with pytest.raises(ValueError, match="order values must be unique"):
        NormalizedContent(
            blocks=(
                _text_block(block_id="one", order=0),
                _text_block(block_id="two", order=0),
            )
        )


def test_normalized_content_rejects_unknown_parent() -> None:
    with pytest.raises(ValueError, match="Unknown parent_id"):
        NormalizedContent(
            blocks=(
                _text_block(
                    block_id="child",
                    order=0,
                    parent_id="missing-parent",
                ),
            )
        )


def test_text_projection_is_derived_from_typed_blocks() -> None:
    content = NormalizedContent(
        blocks=(
            TextBlock(
                block_id="heading",
                order=0,
                kind="heading",
                text="Approval Authority",
            ),
            TableBlock(
                block_id="table",
                order=1,
                headers=("Role", "Limit"),
                rows=(("Manager", "50000"),),
            ),
            SpreadsheetBlock(
                block_id="spreadsheet",
                order=2,
                sheet_name="Matrix",
                cells=(
                    SpreadsheetCell(coordinate="A1", value="Director"),
                    SpreadsheetCell(coordinate="B1", value=100000),
                ),
            ),
        )
    )

    assert content.text_projection == (
        "Approval Authority\n"
        "Role | Limit\n"
        "Manager | 50000\n"
        "Matrix!A1: Director\n"
        "Matrix!B1: 100000"
    )


def test_canonical_document_combines_registry_metadata_and_normalized_content() -> None:
    document = _document()

    assert document.document_id == "DOC-001"
    assert document.authority_level == 4
    assert document.content.blocks[0].text == "Controlled enterprise content."
    assert document.supersedes == "DOC-002"


def test_extracted_text_remains_backward_compatible_projection() -> None:
    content = NormalizedContent(
        blocks=(
            _text_block(
                block_id="paragraph",
                order=0,
                text="Normalized enterprise evidence.",
            ),
        )
    )
    document = _document(content)

    assert document.extracted_text == "Normalized enterprise evidence."


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("document_id", ""),
        ("key", " "),
        ("title", ""),
        ("document_type", ""),
        ("domain", ""),
        ("version", ""),
    ],
)
def test_canonical_document_rejects_empty_required_strings(
    field: str,
    value: str,
) -> None:
    kwargs = {
        "document_id": "DOC-001",
        "key": "transportation_policy_2026",
        "title": "Transportation Policy",
        "source_path": Path("policy.pdf"),
        "format": "pdf",
        "document_type": "corporate_policy",
        "domain": "transportation",
        "version": "3.0",
        "effective_date": date(2026, 1, 1),
        "status": "active",
        "authority_level": 4,
        "content": NormalizedContent(blocks=(_text_block(),)),
    }
    kwargs[field] = value

    with pytest.raises(ValueError):
        CanonicalDocument(**kwargs)


@pytest.mark.parametrize("authority_level", [0, 5, -1])
def test_canonical_document_rejects_invalid_authority_level(
    authority_level: int,
) -> None:
    with pytest.raises(ValueError, match="authority_level"):
        CanonicalDocument(
            document_id="DOC-001",
            key="transportation_policy_2026",
            title="Transportation Policy",
            source_path=Path("policy.pdf"),
            format="pdf",
            document_type="corporate_policy",
            domain="transportation",
            version="3.0",
            effective_date=date(2026, 1, 1),
            status="active",
            authority_level=authority_level,
            content=NormalizedContent(blocks=(_text_block(),)),
        )


def test_canonical_document_rejects_self_supersession() -> None:
    with pytest.raises(ValueError, match="cannot supersede"):
        CanonicalDocument(
            document_id="DOC-001",
            key="transportation_policy_2026",
            title="Transportation Policy",
            source_path=Path("policy.pdf"),
            format="pdf",
            document_type="corporate_policy",
            domain="transportation",
            version="3.0",
            effective_date=date(2026, 1, 1),
            status="active",
            authority_level=4,
            content=NormalizedContent(blocks=(_text_block(),)),
            supersedes="DOC-001",
        )
