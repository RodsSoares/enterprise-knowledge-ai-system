"""Docling-backed parsing adapter for enterprise source documents.

Docling is an external parsing dependency. Its native document model is kept
behind this module and converted into application-controlled ingestion schemas.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

from docling.document_converter import DocumentConverter
from docling_core.types.doc import (
    DocItemLabel,
    SectionHeaderItem,
    TableItem,
    TextItem,
)

from app.ingestion.schemas import (
    NormalizedContent,
    SourceLocation,
    TableBlock,
    TextBlock,
)


_TEXT_KIND_BY_LABEL = {
    DocItemLabel.TITLE: "title",
    DocItemLabel.SECTION_HEADER: "heading",
    DocItemLabel.LIST_ITEM: "list_item",
    DocItemLabel.CAPTION: "caption",
    DocItemLabel.PARAGRAPH: "paragraph",
    DocItemLabel.TEXT: "paragraph",
}

_MARKDOWN_INLINE_PATTERNS = (
    re.compile(r"(?<!\\)\*\*(?=\S)(.+?)(?<=\S)\*\*"),
    re.compile(r"(?<!\\)__(?=\S)(.+?)(?<=\S)__"),
    re.compile(r"(?<!\\)~~(?=\S)(.+?)(?<=\S)~~"),
    re.compile(r"(?<!\\)(?<!\*)\*(?=\S)(.+?)(?<=\S)\*(?!\*)"),
    re.compile(r"(?<!\\)(?<!_)_(?=\S)(.+?)(?<=\S)_(?!_)"),
)


def _normalize_markdown_inline(source: str) -> str:
    """Remove inline Markdown emphasis markers without changing text spacing."""
    normalized = source
    for pattern in _MARKDOWN_INLINE_PATTERNS:
        normalized = pattern.sub(r"\1", normalized)
    return normalized


def _provenance_number(item: TextItem | TableItem) -> int | None:
    """Return Docling's reliable one-based page/slide ordinal when available."""
    if not item.prov:
        return None

    page_no = item.prov[0].page_no
    return int(page_no) if page_no is not None else None


def _source_location(
    item: TextItem | TableItem,
    source_path: Path,
    section_path: tuple[str, ...] = (),
) -> SourceLocation:
    """Map Docling provenance to source-format-specific canonical provenance."""
    ordinal = _provenance_number(item)

    if source_path.suffix.lower() == ".pptx":
        return SourceLocation(
            slide_number=ordinal,
            section_path=section_path,
        )

    return SourceLocation(
        page_number=ordinal,
        section_path=section_path,
    )


def _table_rows(item: TableItem) -> tuple[tuple[str | None, ...], ...]:
    """Convert Docling table data into a rectangular canonical row matrix."""
    grid = item.data.grid
    if not grid:
        raise ValueError("Docling table contains no grid data.")

    return tuple(
        tuple(cell.text if cell.text != "" else None for cell in row)
        for row in grid
    )


class DoclingParser:
    """Parse supported files and adapt Docling output to canonical content."""

    def __init__(self, converter: DocumentConverter | None = None) -> None:
        self._converter = converter or DocumentConverter()

    def parse(self, source_path: Path) -> NormalizedContent:
        """Parse a physical source document into normalized canonical content."""
        if not isinstance(source_path, Path):
            raise TypeError("source_path must be a pathlib.Path.")

        if not source_path.is_file():
            raise FileNotFoundError(source_path)

        if source_path.suffix.lower() == ".md":
            document = self._convert_normalized_markdown(source_path)
        else:
            document = self._converter.convert(source_path).document

        blocks: list[TextBlock | TableBlock] = []
        section_stack: list[str] = []
        order = 0

        for item, _tree_level in document.iterate_items():
            if isinstance(item, SectionHeaderItem):
                level = int(item.level)
                section_stack = section_stack[: max(level - 1, 0)]
                section_stack.append(item.text.strip())

            if isinstance(item, TextItem):
                text = item.text.strip()
                if not text:
                    continue

                kind = _TEXT_KIND_BY_LABEL.get(item.label, "other")
                blocks.append(
                    TextBlock(
                        block_id=f"text-{order:05d}",
                        order=order,
                        kind=kind,
                        text=text,
                        location=_source_location(
                            item,
                            source_path,
                            tuple(section_stack),
                        ),
                    )
                )
                order += 1
                continue

            if isinstance(item, TableItem):
                rows = _table_rows(item)
                blocks.append(
                    TableBlock(
                        block_id=f"table-{order:05d}",
                        order=order,
                        rows=rows,
                        location=_source_location(
                            item,
                            source_path,
                            tuple(section_stack),
                        ),
                    )
                )
                order += 1

        if not blocks:
            raise ValueError(
                f"Docling produced no supported canonical content for {source_path}."
            )

        return NormalizedContent(blocks=tuple(blocks))

    def _convert_normalized_markdown(self, source_path: Path):
        """Normalize inline Markdown presentation before Docling conversion."""
        source = source_path.read_text(encoding="utf-8")
        normalized = _normalize_markdown_inline(source)

        if normalized == source:
            return self._converter.convert(source_path).document

        with tempfile.TemporaryDirectory(prefix="enterprise-rag-md-") as temp_dir:
            normalized_path = Path(temp_dir) / source_path.name
            normalized_path.write_text(normalized, encoding="utf-8")
            return self._converter.convert(normalized_path).document
