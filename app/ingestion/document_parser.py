"""Document-level ingestion orchestrator.

This module selects format-specific ingestion components and composes their
application-controlled canonical output. It does not parse source formats
itself.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from app.ingestion.schemas import ContentBlock, NormalizedContent


class DocumentParser:
    """Route source documents to specialized parsers and compose enrichments."""

    _DOCLING_SUFFIXES = {".pdf", ".docx", ".md"}

    def __init__(
        self,
        *,
        docling_parser: Any,
        xlsx_parser: Any,
        pptx_native_enricher: Any,
    ) -> None:
        self._docling_parser = docling_parser
        self._xlsx_parser = xlsx_parser
        self._pptx_native_enricher = pptx_native_enricher

    def parse(self, path: Path) -> NormalizedContent:
        """Parse one physical source into normalized canonical content."""
        if not isinstance(path, Path):
            raise TypeError("path must be a pathlib.Path.")

        suffix = path.suffix.lower()

        if suffix in self._DOCLING_SUFFIXES:
            return self._docling_parser.parse(path)

        if suffix == ".xlsx":
            return self._xlsx_parser.parse(path)

        if suffix == ".pptx":
            return self._parse_pptx(path)

        raise ValueError(f"Unsupported document format: {suffix or '<none>'}")

    def _parse_pptx(self, path: Path) -> NormalizedContent:
        base_content = self._docling_parser.parse(path)
        charts = self._pptx_native_enricher.extract_charts(path)

        if not charts:
            return base_content

        combined = (*base_content.blocks, *charts)
        ordered = sorted(combined, key=self._pptx_sort_key)

        reindexed = tuple(
            replace(block, order=order)
            for order, block in enumerate(ordered)
        )
        return NormalizedContent(blocks=reindexed)

    @staticmethod
    def _pptx_sort_key(block: ContentBlock) -> tuple[int, int, int]:
        """Order PPTX blocks by slide, then base content before enrichment.

        The original block order remains the final deterministic tie-breaker
        inside each source kind.
        """
        slide_number = block.location.slide_number
        slide_key = slide_number if slide_number is not None else 0

        # Native chart enrichment follows Docling content on the same slide.
        source_kind = 1 if type(block).__name__ == "ChartBlock" else 0

        return (slide_key, source_kind, block.order)
