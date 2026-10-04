"""Integration tests for the physical DOC-012 XLSX corpus document."""

from pathlib import Path

from app.ingestion.schemas import SpreadsheetBlock
from app.ingestion.xlsx_parser import XlsxParser


DOC_012 = Path(
    "data/source/corporate_repository/governance/"
    "DOC-012_Approval_Authority_Matrix.xlsx"
)


def _parse_doc_012():
    return XlsxParser().parse(DOC_012)


def _cells_by_coordinate(block: SpreadsheetBlock):
    return {cell.coordinate: cell for cell in block.cells}


def test_doc_012_is_parsed_from_physical_corpus() -> None:
    assert DOC_012.is_file()

    content = _parse_doc_012()

    assert len(content.blocks) == 2


def test_doc_012_preserves_worksheet_names() -> None:
    content = _parse_doc_012()

    assert [block.sheet_name for block in content.blocks] == [
        "Approval Matrix",
        "Document Control",
    ]


def test_doc_012_preserves_worksheet_ranges() -> None:
    content = _parse_doc_012()

    assert content.blocks[0].cell_range == "A1:E9"
    assert content.blocks[1].cell_range == "A1:B9"


def test_doc_012_approval_matrix_preserves_headers() -> None:
    block = _parse_doc_012().blocks[0]
    cells = _cells_by_coordinate(block)

    assert cells["A1"].value == "Decision Type"
    assert cells["B1"].value == "Value / Condition"
    assert cells["C1"].value == "Required Approval"
    assert cells["D1"].value == "Additional Review"
    assert cells["E1"].value == "Notes"


def test_doc_012_preserves_new_ai_tool_approval_rule() -> None:
    block = _parse_doc_012().blocks[0]
    cells = _cells_by_coordinate(block)

    assert cells["A8"].value == "New AI tool approval"
    assert (
        cells["B8"].value
        == "Any value when enterprise or supplier data is processed"
    )
    assert cells["C8"].value == "AI Governance Owner"
    assert cells["D8"].value == "Information Security + Procurement"


def test_doc_012_preserves_confidential_supplier_data_rule() -> None:
    block = _parse_doc_012().blocks[0]
    cells = _cells_by_coordinate(block)

    assert cells["A9"].value == "AI use with confidential supplier data"
    assert (
        cells["C9"].value
        == "Information Security Owner + AI Governance Owner"
    )
    assert cells["D9"].value == "Data Owner"


def test_doc_012_document_control_preserves_identity() -> None:
    block = _parse_doc_012().blocks[1]
    cells = _cells_by_coordinate(block)

    assert cells["A2"].value == "Document ID"
    assert cells["B2"].value == "DOC-012"
    assert cells["A3"].value == "Title"
    assert cells["B3"].value == "Approval Authority Matrix"


def test_doc_012_document_control_preserves_governance_metadata() -> None:
    block = _parse_doc_012().blocks[1]
    cells = _cells_by_coordinate(block)

    assert cells["B4"].value == "2026"
    assert cells["B5"].value == "2026-01-01"
    assert cells["B6"].value == "ACTIVE"
    assert cells["B7"].value == "Governance"


def test_doc_012_cells_are_preserved_as_native_spreadsheet_cells() -> None:
    content = _parse_doc_012()

    assert all(isinstance(block, SpreadsheetBlock) for block in content.blocks)
    assert len(content.blocks[0].cells) == 45
    assert len(content.blocks[1].cells) == 18
    assert all(
        cell.data_type == "s"
        for block in content.blocks
        for cell in block.cells
    )
