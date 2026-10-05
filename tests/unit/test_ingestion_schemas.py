"""Unit tests for canonical ingestion schemas."""

from datetime import date
from pathlib import Path

import pytest

from app.ingestion.schemas import (
    CanonicalDocument,
    ChartBlock,
    ChartSeries,
    ChartSourceReference,
    ImageBlock,
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



def test_chart_source_reference_preserves_resolved_lineage() -> None:
    reference = ChartSourceReference(
        resource="ppt/embeddings/Microsoft_Excel_Worksheet.xlsx",
        sheet_name="Planilha2",
        cell_range="$A$1:$A$5",
        status="resolved",
    )

    assert reference.resource == "ppt/embeddings/Microsoft_Excel_Worksheet.xlsx"
    assert reference.sheet_name == "Planilha2"
    assert reference.cell_range == "$A$1:$A$5"
    assert reference.status == "resolved"


def test_chart_source_reference_preserves_unresolved_lineage() -> None:
    reference = ChartSourceReference(
        resource="ppt/embeddings/Microsoft_Excel_Worksheet.xlsx",
        sheet_name="Planilha3",
        cell_range="$B$1:$B$3",
        status="unresolved",
    )

    assert reference.sheet_name == "Planilha3"
    assert reference.cell_range == "$B$1:$B$3"
    assert reference.status == "unresolved"


@pytest.mark.parametrize(
    ("sheet_name", "cell_range"),
    [
        (None, "$A$1:$A$5"),
        ("Planilha2", None),
    ],
)
def test_resolved_chart_source_requires_sheet_and_range(
    sheet_name: str | None,
    cell_range: str | None,
) -> None:
    with pytest.raises(ValueError, match="require sheet_name and cell_range"):
        ChartSourceReference(
            resource="ppt/embeddings/Microsoft_Excel_Worksheet.xlsx",
            sheet_name=sheet_name,
            cell_range=cell_range,
            status="resolved",
        )


def test_chart_source_reference_rejects_empty_resource() -> None:
    with pytest.raises(ValueError, match="resource must not be empty"):
        ChartSourceReference(resource="   ")


def test_chart_series_accepts_presented_values_without_source_reference() -> None:
    series = ChartSeries(
        name="Realizado",
        values=(-0.0714, -0.0006, 0.0381, 0.1246, None),
    )

    assert series.name == "Realizado"
    assert series.values[3] == 0.1246
    assert series.source_reference is None


def test_chart_series_accepts_source_reference_without_materialized_values() -> None:
    reference = ChartSourceReference(
        resource="ppt/embeddings/Microsoft_Excel_Worksheet.xlsx",
        sheet_name="Planilha3",
        cell_range="$B$1:$B$3",
        status="unresolved",
    )
    series = ChartSeries(name="Forecast", source_reference=reference)

    assert series.values == ()
    assert series.source_reference is reference
    assert series.source_reference.status == "unresolved"


def test_chart_series_rejects_missing_values_and_source_reference() -> None:
    with pytest.raises(ValueError, match="values or a source_reference"):
        ChartSeries(name="Forecast")


def test_chart_block_preserves_presented_chart_structure_and_slide_provenance() -> None:
    source = ChartSourceReference(
        resource="ppt/embeddings/Microsoft_Excel_Worksheet.xlsx",
        sheet_name="Planilha2",
        cell_range="$B$1:$B$5",
        status="resolved",
    )
    chart = ChartBlock(
        block_id="chart-001",
        order=3,
        chart_type="COLUMN_CLUSTERED",
        title="Variabilidade Realizado vs. FCT visão Semanal",
        categories=("w44", "w45", "w46", "w47", "Total"),
        series=(
            ChartSeries(
                name="Forecast",
                values=(-0.0714, -0.0006, 0.0381, 0.1246, None),
                source_reference=source,
            ),
        ),
        location=SourceLocation(slide_number=10),
    )

    assert chart.location.slide_number == 10
    assert chart.location.page_number is None
    assert chart.categories == ("w44", "w45", "w46", "w47", "Total")
    assert chart.series[0].source_reference is source


def test_chart_block_rejects_empty_series() -> None:
    with pytest.raises(ValueError, match="series must not be empty"):
        ChartBlock(
            block_id="chart-001",
            order=0,
            chart_type="LINE",
            series=(),
        )


@pytest.mark.parametrize(
    ("block_id", "order", "chart_type", "match"),
    [
        ("", 0, "LINE", "block_id must not be empty"),
        ("chart-001", -1, "LINE", "order must be greater than or equal to 0"),
        ("chart-001", 0, "   ", "chart_type must not be empty"),
    ],
)
def test_chart_block_rejects_invalid_required_fields(
    block_id: str,
    order: int,
    chart_type: str,
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        ChartBlock(
            block_id=block_id,
            order=order,
            chart_type=chart_type,
            series=(ChartSeries(values=(1,)),),
        )


def test_chart_block_rejects_self_parent() -> None:
    with pytest.raises(ValueError, match="cannot be its own parent"):
        ChartBlock(
            block_id="chart-001",
            order=0,
            chart_type="LINE",
            series=(ChartSeries(values=(1,)),),
            parent_id="chart-001",
        )


def test_normalized_content_accepts_chart_block_and_orders_it_deterministically() -> None:
    content = NormalizedContent(
        blocks=(
            ChartBlock(
                block_id="chart-second",
                order=2,
                chart_type="LINE",
                series=(ChartSeries(values=(2,)),),
                location=SourceLocation(slide_number=16),
            ),
            _text_block(block_id="first", order=1, text="Presented context"),
        )
    )

    assert tuple(block.block_id for block in content.ordered_blocks) == (
        "first",
        "chart-second",
    )
    chart = content.ordered_blocks[1]
    assert isinstance(chart, ChartBlock)
    assert chart.location.slide_number == 16


def test_text_projection_does_not_flatten_chart_data_implicitly() -> None:
    content = NormalizedContent(
        blocks=(
            _text_block(
                block_id="context",
                order=0,
                text="Variabilidade da Demanda",
            ),
            ChartBlock(
                block_id="chart-001",
                order=1,
                chart_type="LINE",
                title="Realizado vs. FCT",
                categories=("w44", "w45"),
                series=(ChartSeries(name="Forecast", values=(0.1, 0.2)),),
                location=SourceLocation(slide_number=10),
            ),
        )
    )

    assert content.text_projection == "Variabilidade da Demanda"
    assert "Forecast" not in content.text_projection
    assert "0.1" not in content.text_projection


def test_unresolved_chart_relationship_is_valid_canonical_evidence_state() -> None:
    unresolved = ChartSourceReference(
        resource="ppt/embeddings/Microsoft_Excel_Worksheet.xlsx",
        sheet_name="Planilha3",
        cell_range="$B$1:$B$3",
        status="unresolved",
    )
    content = NormalizedContent(
        blocks=(
            ChartBlock(
                block_id="chart-004",
                order=0,
                chart_type="COLUMN_CLUSTERED",
                series=(
                    ChartSeries(
                        name="Presented series",
                        source_reference=unresolved,
                    ),
                ),
                location=SourceLocation(slide_number=14),
            ),
        )
    )

    chart = content.blocks[0]
    assert isinstance(chart, ChartBlock)
    assert chart.series[0].source_reference is unresolved
    assert chart.series[0].source_reference.status == "unresolved"


def test_image_block_preserves_visual_evidence_and_provenance() -> None:
    block = ImageBlock(
        block_id="image-001",
        order=1,
        location=SourceLocation(
            page_number=18,
            section_path=("CAPÍTULO I",),
        ),
        caption="Alice follows the White Rabbit.",
        parent_id="heading-001",
    )

    assert block.location.page_number == 18
    assert block.location.section_path == ("CAPÍTULO I",)
    assert block.caption == "Alice follows the White Rabbit."
    assert block.parent_id == "heading-001"


@pytest.mark.parametrize(
    ("block_id", "order", "caption", "match"),
    [
        ("", 0, None, "block_id must not be empty"),
        ("image-001", -1, None, "order must be greater than or equal to 0"),
        ("image-001", 0, "   ", "caption must not be empty when provided"),
    ],
)
def test_image_block_rejects_invalid_fields(
    block_id: str,
    order: int,
    caption: str | None,
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        ImageBlock(
            block_id=block_id,
            order=order,
            caption=caption,
        )


def test_image_block_rejects_self_parent() -> None:
    with pytest.raises(ValueError, match="cannot be its own parent"):
        ImageBlock(
            block_id="image-001",
            order=0,
            parent_id="image-001",
        )


def test_normalized_content_accepts_image_without_flattening_it_to_text() -> None:
    content = NormalizedContent(
        blocks=(
            _text_block(
                block_id="context",
                order=0,
                text="Visual evidence follows.",
            ),
            ImageBlock(
                block_id="image-001",
                order=1,
                caption="Operational diagram",
                location=SourceLocation(page_number=3),
            ),
        )
    )

    assert isinstance(content.ordered_blocks[1], ImageBlock)
    assert content.ordered_blocks[1].location.page_number == 3
    assert content.text_projection == "Visual evidence follows."
    assert "Operational diagram" not in content.text_projection

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
