from app.chunking.block_serializer import BlockSerializer
from app.ingestion.schemas import TextBlock
from app.ingestion.schemas import SpreadsheetBlock, SpreadsheetCell

from app.ingestion.schemas import (
    ChartBlock,
    ChartSeries,
    ChartSourceReference,
)


from app.ingestion.schemas import ImageBlock


def test_serializer_preserves_text_block_content() -> None:
    block = TextBlock(
        block_id="text-00001",
        order=0,
        kind="paragraph",
        text="Evidence before generation.",
    )

    serializer = BlockSerializer()

    result = serializer.serialize(block)

    assert result == "Evidence before generation."

from app.ingestion.schemas import TableBlock


def test_serializer_serializes_table_structure_deterministically() -> None:
    block = TableBlock(
        block_id="table-00001",
        order=0,
        caption="Carrier Performance",
        headers=("Carrier", "SLA", "Cost"),
        rows=(
            ("Atlas", "95%", "1200"),
            ("Nova", "91%", "1100"),
        ),
    )

    serializer = BlockSerializer()

    result = serializer.serialize(block)

    assert result == (
        "Caption: Carrier Performance\n"
        "Carrier | SLA | Cost\n"
        "Atlas | 95% | 1200\n"
        "Nova | 91% | 1100"
    )


def test_serializer_serializes_spreadsheet_structure_deterministically() -> None:
    block = SpreadsheetBlock(
        block_id="xlsx-sheet-1",
        order=0,
        sheet_name="Logistics KPI",
        cell_range="A1:C2",
        table_name="Carrier Performance",
        cells=(
            SpreadsheetCell(
                coordinate="A1",
                value="Carrier",
                data_type="s",
            ),
            SpreadsheetCell(
                coordinate="B1",
                value="SLA",
                data_type="s",
            ),
            SpreadsheetCell(
                coordinate="C1",
                value="Cost",
                data_type="s",
            ),
            SpreadsheetCell(
                coordinate="A2",
                value="Atlas",
                data_type="s",
            ),
            SpreadsheetCell(
                coordinate="B2",
                value=0.95,
                data_type="n",
            ),
            SpreadsheetCell(
                coordinate="C2",
                value=None,
                formula="=SUM(C3:C6)",
                data_type="f",
            ),
        ),
    )

    serializer = BlockSerializer()

    result = serializer.serialize(block)

    assert result == (
        "Sheet: Logistics KPI\n"
        "Range: A1:C2\n"
        "Table: Carrier Performance\n"
        "A1 = Carrier\n"
        "B1 = SLA\n"
        "C1 = Cost\n"
        "A2 = Atlas\n"
        "B2 = 0.95\n"
        "C2 [formula: =SUM(C3:C6)]"
    )


def test_serializer_serializes_chart_structure_deterministically() -> None:
    block = ChartBlock(
        block_id="chart-00001",
        order=0,
        chart_type="line",
        title="Demand Variability",
        categories=("Jan", "Feb", "Mar"),
        category_source_reference=ChartSourceReference(
            resource="external-workbook",
            sheet_name="Demand",
            cell_range="A2:A4",
            status="unresolved",
        ),
        series=(
            ChartSeries(
                name="Forecast",
                values=(100, 120, 140),
                source_reference=ChartSourceReference(
                    resource="external-workbook",
                    sheet_name="Demand",
                    cell_range="B2:B4",
                    status="unresolved",
                ),
            ),
        ),
    )

    serializer = BlockSerializer()

    result = serializer.serialize(block)

    assert result == (
        "Chart: Demand Variability\n"
        "Type: line\n"
        "Categories: Jan | Feb | Mar\n"
        "Category source: external-workbook | Demand | A2:A4 | unresolved\n"
        "Series: Forecast\n"
        "Values: 100 | 120 | 140\n"
        "Source: external-workbook | Demand | B2:B4 | unresolved"
    )


def test_serializer_uses_image_caption_when_available() -> None:
    block = ImageBlock(
        block_id="image-00001",
        order=0,
        caption="Transportation network architecture.",
    )

    serializer = BlockSerializer()

    result = serializer.serialize(block)

    assert result == "Transportation network architecture."


def test_serializer_returns_none_for_image_without_caption() -> None:
    block = ImageBlock(
        block_id="image-00001",
        order=0,
        caption=None,
    )

    serializer = BlockSerializer()

    result = serializer.serialize(block)

    assert result is None