"""Docling-backed parsing adapter for narrative enterprise documents."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from docling.document_converter import DocumentConverter
from docling_core.types.doc import (
    DocItemLabel,
    PictureItem,
    SectionHeaderItem,
    TableItem,
    TextItem,
)

from app.ingestion.schemas import (
    ImageBlock,
    NormalizedContent,
    SourceLocation,
    TableBlock,
    TextBlock,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


_INLINE_MARKDOWN_RE = re.compile(r"(\*\*|__)(.+?)\1|(?<!\*)\*([^*\n]+?)\*(?!\*)|(?<!_)_([^_\n]+?)_(?!_)")
_SUPPORTED_SUFFIXES = {".md", ".docx", ".pdf", ".pptx"}


def _normalize_markdown_inline(source: str) -> str:
    """Remove lightweight inline emphasis markers without changing block structure."""

    def replacement(match: re.Match[str]) -> str:
        return next(group for group in match.groups()[1:] if group is not None)

    return _INLINE_MARKDOWN_RE.sub(replacement, source)


def _text_kind(label: DocItemLabel) -> str:
    mapping = {
        DocItemLabel.TITLE: "title",
        DocItemLabel.SECTION_HEADER: "heading",
        DocItemLabel.LIST_ITEM: "list_item",
        DocItemLabel.CAPTION: "caption",
        DocItemLabel.PARAGRAPH: "paragraph",
        DocItemLabel.TEXT: "paragraph",
    }
    return mapping.get(label, "other")


def _provenance_number(item: object) -> int | None:
    provenance = getattr(item, "prov", None)
    if not provenance:
        return None
    page_no = getattr(provenance[0], "page_no", None)
    return int(page_no) if page_no is not None else None


def _source_location(
    item: object,
    source_path: Path,
    section_path: Sequence[str] = (),
) -> SourceLocation:
    ordinal = _provenance_number(item)
    suffix = source_path.suffix.lower()

    return SourceLocation(
        page_number=ordinal if suffix != ".pptx" else None,
        slide_number=ordinal if suffix == ".pptx" else None,
        section_path=tuple(section_path),
    )


def _table_rows(item: TableItem) -> tuple[tuple[str | None, ...], ...]:
    grid = item.data.grid
    return tuple(
        tuple(cell.text if cell.text != "" else None for cell in row)
        for row in grid
    )


def _section_path(
    headings_by_level: dict[int, str],
    level: int,
    heading: str,
) -> tuple[str, ...]:
    """Update heading state and return the active semantic section path.

    Docling heading levels are identifiers of hierarchy depth, not zero-based
    indexes into a stack. Siblings at the same level replace one another,
    deeper headings inherit active shallower headings, and skipped levels do
    not create synthetic ancestors.
    """
    for existing_level in tuple(headings_by_level):
        if existing_level >= level:
            del headings_by_level[existing_level]

    headings_by_level[level] = heading

    return tuple(
        headings_by_level[existing_level]
        for existing_level in sorted(headings_by_level)
    )


class DoclingParser:
    """Parse narrative source files into the application canonical model."""

    def __init__(self, converter: DocumentConverter | None = None) -> None:
        self._converter = converter or DocumentConverter()

    def parse(self, source_path: Path) -> NormalizedContent:
        if not isinstance(source_path, Path):
            raise TypeError("source_path must be a pathlib.Path")
        if not source_path.exists():
            raise FileNotFoundError(source_path)
        if source_path.suffix.lower() not in _SUPPORTED_SUFFIXES:
            raise ValueError(
                f"Unsupported Docling source format: {source_path.suffix.lower()}"
            )

        parse_path = source_path
        normalized_markdown_path: Path | None = None

        if source_path.suffix.lower() == ".md":
            normalized_source = _normalize_markdown_inline(
                source_path.read_text(encoding="utf-8")
            )
            normalized_markdown_path = source_path.with_name(
                f".{source_path.stem}.docling-normalized.md"
            )
            normalized_markdown_path.write_text(normalized_source, encoding="utf-8")
            parse_path = normalized_markdown_path

        try:
            result = self._converter.convert(parse_path)
        finally:
            if normalized_markdown_path is not None:
                normalized_markdown_path.unlink(missing_ok=True)

        document = result.document
        blocks: list[TextBlock | TableBlock | ImageBlock] = []
        headings_by_level: dict[int, str] = {}
        section_path: tuple[str, ...] = ()

        for item, _tree_level in document.iterate_items():
            if isinstance(item, SectionHeaderItem):
                heading = item.text.strip()
                if heading:
                    section_path = _section_path(
                        headings_by_level,
                        int(item.level),
                        heading,
                    )

            if isinstance(item, TextItem):
                text = item.text.strip()
                if not text:
                    continue

                blocks.append(
                    TextBlock(
                        block_id=f"text-{len(blocks):05d}",
                        order=len(blocks),
                        kind=_text_kind(item.label),
                        text=text,
                        location=_source_location(item, source_path, section_path),
                    )
                )
                continue

            if isinstance(item, TableItem):
                rows = _table_rows(item)
                if not rows:
                    continue

                blocks.append(
                    TableBlock(
                        block_id=f"table-{len(blocks):05d}",
                        order=len(blocks),
                        rows=rows,
                        location=_source_location(item, source_path, section_path),
                    )
                )

                continue

            if isinstance(item, PictureItem):
                caption = item.caption_text(document).strip() or None
                blocks.append(
                    ImageBlock(
                        block_id=f"image-{len(blocks):05d}",
                        order=len(blocks),
                        location=_source_location(item, source_path, section_path),
                        caption=caption,
                    )
                )

        if not blocks:
            raise ValueError(f"No canonical content extracted from {source_path}")

        return NormalizedContent(blocks=tuple(blocks))
