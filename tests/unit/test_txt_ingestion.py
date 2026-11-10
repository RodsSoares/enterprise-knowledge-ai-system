"""Regression tests for native TXT ingestion."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from app.ingestion.document_parser import DocumentParser
from app.ingestion.schemas import NormalizedContent, TextBlock
from app.scripts.ask_knowledge import discover_sources


def make_parser():
    return DocumentParser(
        docling_parser=Mock(),
        xlsx_parser=Mock(),
        pptx_native_enricher=Mock(),
    )


def test_txt_produces_canonical_content(tmp_path):
    path = tmp_path / "DOC-027_guidelines.txt"
    path.write_text("TITLE\nContent", encoding="utf-8")

    result = make_parser().parse(path)

    assert isinstance(result, NormalizedContent)
    assert len(result.blocks) == 2
    assert all(isinstance(b, TextBlock) for b in result.blocks)


def test_txt_preserves_source_order(tmp_path):
    path = tmp_path / "DOC-027_guidelines.txt"
    path.write_text("FIRST\nSECOND\nTHIRD", encoding="utf-8")

    result = make_parser().parse(path)

    assert [b.text for b in result.ordered_blocks] == [
        "FIRST", "SECOND", "THIRD"
    ]
    assert [b.order for b in result.blocks] == [0, 1, 2]


def test_txt_supports_utf8_bom(tmp_path):
    path = tmp_path / "DOC-027_guidelines.txt"
    path.write_text("AI SUPPLY CHAIN", encoding="utf-8-sig")

    result = make_parser().parse(path)

    assert result.text_projection == "AI SUPPLY CHAIN"


def test_txt_rejects_empty_content(tmp_path):
    path = tmp_path / "DOC-027_guidelines.txt"
    path.write_text("  \n  \n", encoding="utf-8")

    with pytest.raises(ValueError, match="No canonical content"):
        make_parser().parse(path)


def test_discovery_finds_nested_txt(tmp_path):
    folder = tmp_path / "guidelines"
    folder.mkdir()

    source = folder / "DOC-027_guidelines.txt"
    source.write_text("Example text", encoding="utf-8")

    discovered = discover_sources(tmp_path)

    assert discovered == [source]
