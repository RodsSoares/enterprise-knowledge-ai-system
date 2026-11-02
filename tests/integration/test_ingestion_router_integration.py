"""Integration tests for the public format-agnostic ingestion facade."""

from pathlib import Path

import pytest

from app.ingestion.ingestion_router import IngestionRouter
from app.ingestion.schemas import NormalizedContent, SpreadsheetBlock


XLSX_SOURCE = Path(
    "data/source/corporate_repository/governance/"
    "DOC-012_Approval_Authority_Matrix.xlsx"
)


@pytest.mark.skipif(
    not XLSX_SOURCE.is_file(),
    reason="Controlled XLSX corpus file unavailable.",
)
def test_ingestion_router_routes_xlsx_without_exposing_parser_choice():
    """Caller supplies only the path; routing to XlsxParser is internal."""
    router = IngestionRouter()

    content = router.parse(XLSX_SOURCE)

    assert isinstance(content, NormalizedContent)
    assert content.blocks
    assert all(isinstance(block, SpreadsheetBlock) for block in content.blocks)
