"""Canonical ingestion schemas for the Enterprise Knowledge AI System.

This module defines the deterministic, application-controlled contracts produced
by the ingestion layer.

Format-specific parsers may use third-party representations internally, but
parser-native models must be adapted into the canonical schemas defined here
before downstream retrieval processing.

The document registry remains responsible for controlled identity and governance
metadata. Evaluation-only metadata such as ``canonical_fact_paths`` and
``evaluation_roles`` intentionally does not belong to this runtime contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal


DocumentFormat = Literal["pdf", "docx", "xlsx", "pptx", "md", "txt"]
LifecycleStatus = Literal["active", "superseded", "historical"]
TextBlockKind = Literal[
    "title",
    "heading",
    "paragraph",
    "list_item",
    "caption",
    "other",
]


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """Structural location of normalized content inside the physical source.

    Only reliable locators should be populated. A parser must not invent source
    locations that cannot be reconstructed from the original document.
    """

    page_number: int | None = None
    slide_number: int | None = None
    sheet_name: str | None = None
    cell_range: str | None = None
    section_path: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.page_number is not None and self.page_number < 1:
            raise ValueError("page_number must be greater than or equal to 1.")

        if self.slide_number is not None and self.slide_number < 1:
            raise ValueError("slide_number must be greater than or equal to 1.")

        if self.sheet_name is not None and not self.sheet_name.strip():
            raise ValueError("sheet_name must not be empty when provided.")

        if self.cell_range is not None and not self.cell_range.strip():
            raise ValueError("cell_range must not be empty when provided.")

        if any(not part.strip() for part in self.section_path):
            raise ValueError("section_path entries must not be empty.")


@dataclass(frozen=True, slots=True)
class TextBlock:
    """Ordered textual unit preserved from the source document."""

    block_id: str
    order: int
    kind: TextBlockKind
    text: str
    location: SourceLocation = SourceLocation()
    parent_id: str | None = None

    def __post_init__(self) -> None:
        if not self.block_id.strip():
            raise ValueError("block_id must not be empty.")

        if self.order < 0:
            raise ValueError("order must be greater than or equal to 0.")

        if not self.text.strip():
            raise ValueError("text must not be empty.")

        if self.parent_id == self.block_id:
            raise ValueError("A text block cannot be its own parent.")


@dataclass(frozen=True, slots=True)
class TableBlock:
    """Normalized table while preserving row/column relationships."""

    block_id: str
    order: int
    rows: tuple[tuple[str | None, ...], ...]
    location: SourceLocation = SourceLocation()
    headers: tuple[str, ...] = ()
    caption: str | None = None
    parent_id: str | None = None

    def __post_init__(self) -> None:
        if not self.block_id.strip():
            raise ValueError("block_id must not be empty.")

        if self.order < 0:
            raise ValueError("order must be greater than or equal to 0.")

        if not self.rows:
            raise ValueError("rows must not be empty.")

        row_widths = {len(row) for row in self.rows}
        if len(row_widths) != 1:
            raise ValueError("All table rows must have the same number of columns.")

        width = next(iter(row_widths))
        if width == 0:
            raise ValueError("Table rows must contain at least one column.")

        if self.headers and len(self.headers) != width:
            raise ValueError(
                "headers must contain the same number of columns as table rows."
            )

        if self.caption is not None and not self.caption.strip():
            raise ValueError("caption must not be empty when provided.")

        if self.parent_id == self.block_id:
            raise ValueError("A table block cannot be its own parent.")


@dataclass(frozen=True, slots=True)
class SpreadsheetCell:
    """Cell-level representation used when spreadsheet semantics require it."""

    coordinate: str
    value: str | int | float | bool | None
    formula: str | None = None
    data_type: str | None = None

    def __post_init__(self) -> None:
        if not self.coordinate.strip():
            raise ValueError("coordinate must not be empty.")

        if self.formula is not None and not self.formula.strip():
            raise ValueError("formula must not be empty when provided.")

        if self.data_type is not None and not self.data_type.strip():
            raise ValueError("data_type must not be empty when provided.")


@dataclass(frozen=True, slots=True)
class SpreadsheetBlock:
    """Workbook region requiring spreadsheet-specific structural preservation."""

    block_id: str
    order: int
    sheet_name: str
    cells: tuple[SpreadsheetCell, ...]
    cell_range: str | None = None
    table_name: str | None = None
    parent_id: str | None = None

    def __post_init__(self) -> None:
        if not self.block_id.strip():
            raise ValueError("block_id must not be empty.")

        if self.order < 0:
            raise ValueError("order must be greater than or equal to 0.")

        if not self.sheet_name.strip():
            raise ValueError("sheet_name must not be empty.")

        if not self.cells:
            raise ValueError("cells must not be empty.")

        coordinates = [cell.coordinate for cell in self.cells]
        if len(coordinates) != len(set(coordinates)):
            raise ValueError(
                "Spreadsheet cell coordinates must be unique within a block."
            )

        if self.cell_range is not None and not self.cell_range.strip():
            raise ValueError("cell_range must not be empty when provided.")

        if self.table_name is not None and not self.table_name.strip():
            raise ValueError("table_name must not be empty when provided.")

        if self.parent_id == self.block_id:
            raise ValueError("A spreadsheet block cannot be its own parent.")


ContentBlock = TextBlock | TableBlock | SpreadsheetBlock


@dataclass(frozen=True, slots=True)
class NormalizedContent:
    """Structure-preserving normalized content of an enterprise document.

    Blocks remain ordered and typed. ``text_projection`` is a convenience view
    for text-oriented downstream operations and is not the canonical source of
    truth.
    """

    blocks: tuple[ContentBlock, ...]

    def __post_init__(self) -> None:
        if not self.blocks:
            raise ValueError("blocks must not be empty.")

        block_ids = [block.block_id for block in self.blocks]
        if len(block_ids) != len(set(block_ids)):
            raise ValueError("block_id values must be unique within a document.")

        orders = [block.order for block in self.blocks]
        if len(orders) != len(set(orders)):
            raise ValueError("block order values must be unique within a document.")

        known_ids = set(block_ids)
        for block in self.blocks:
            if block.parent_id is not None and block.parent_id not in known_ids:
                raise ValueError(
                    f"Unknown parent_id {block.parent_id!r} for block "
                    f"{block.block_id!r}."
                )

    @property
    def ordered_blocks(self) -> tuple[ContentBlock, ...]:
        """Return content blocks in deterministic source order."""
        return tuple(sorted(self.blocks, key=lambda block: block.order))

    @property
    def text_projection(self) -> str:
        """Return a deterministic textual projection of normalized content.

        This representation exists for text-oriented operations such as lexical
        inspection or debugging. It must not replace the structured blocks as
        the canonical source of truth.
        """
        parts: list[str] = []

        for block in self.ordered_blocks:
            if isinstance(block, TextBlock):
                parts.append(block.text)
                continue

            if isinstance(block, TableBlock):
                if block.caption:
                    parts.append(block.caption)
                if block.headers:
                    parts.append(" | ".join(block.headers))
                parts.extend(
                    " | ".join("" if value is None else value for value in row)
                    for row in block.rows
                )
                continue

            if isinstance(block, SpreadsheetBlock):
                parts.extend(
                    f"{block.sheet_name}!{cell.coordinate}: "
                    f"{'' if cell.value is None else cell.value}"
                    for cell in block.cells
                )

        return "\n".join(parts)


@dataclass(frozen=True, slots=True)
class CanonicalDocument:
    """Canonical representation of an enterprise document after ingestion.

    Content comes from the physical source document and is normalized into
    application-controlled structural contracts.

    Identity and governance metadata come from the controlled document registry.
    """

    document_id: str
    key: str
    title: str

    source_path: Path
    format: DocumentFormat

    document_type: str
    domain: str
    version: str
    effective_date: date
    status: LifecycleStatus
    authority_level: int

    content: NormalizedContent

    supersedes: str | None = None
    superseded_by: str | None = None
    entity_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate invariants that belong to the canonical document contract."""
        if not self.document_id.strip():
            raise ValueError("document_id must not be empty.")

        if not self.key.strip():
            raise ValueError("key must not be empty.")

        if not self.title.strip():
            raise ValueError("title must not be empty.")

        if not self.document_type.strip():
            raise ValueError("document_type must not be empty.")

        if not self.domain.strip():
            raise ValueError("domain must not be empty.")

        if not self.version.strip():
            raise ValueError("version must not be empty.")

        if not isinstance(self.source_path, Path):
            raise TypeError("source_path must be a pathlib.Path.")

        if self.authority_level not in {1, 2, 3, 4}:
            raise ValueError("authority_level must be one of: 1, 2, 3, 4.")

        if not isinstance(self.content, NormalizedContent):
            raise TypeError("content must be a NormalizedContent instance.")

        if self.document_id in {self.supersedes, self.superseded_by}:
            raise ValueError("A document cannot supersede or be superseded by itself.")

    @property
    def extracted_text(self) -> str:
        """Backward-compatible textual projection of normalized content.

        New code should prefer ``content`` and consume typed structural blocks.
        """
        return self.content.text_projection
