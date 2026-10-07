from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RetrievalChunk:
    """Retrieval unit derived from canonical source blocks."""

    chunk_id: str
    order: int
    text: str
    source_block_ids: tuple[str, ...]
    source_path: Path
    section_path: tuple[str, ...] = ()
    page_numbers: tuple[int, ...] = ()
    slide_numbers: tuple[int, ...] = ()
    sheet_names: tuple[str, ...] = ()
    content_types: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.chunk_id.strip():
            raise ValueError("chunk_id must not be empty.")

        if self.order < 0:
            raise ValueError("order must be greater than or equal to 0.")

        if not self.text.strip():
            raise ValueError("text must not be empty.")

        if not self.source_block_ids:
            raise ValueError("source_block_ids must not be empty.")

        if not self.content_types:
            raise ValueError("content_types must not be empty.")

        if len(set(self.source_block_ids)) != len(self.source_block_ids):
            raise ValueError("source_block_ids must not contain duplicates.")

        if any(not block_id.strip() for block_id in self.source_block_ids):
            raise ValueError("source_block_ids entries must not be empty.")

        if any(not section.strip() for section in self.section_path):
            raise ValueError("section_path entries must not be empty.")

        if any(page_number < 1 for page_number in self.page_numbers):
            raise ValueError("page_numbers entries must be greater than or equal to 1.")

        if any(slide_number < 1 for slide_number in self.slide_numbers):
            raise ValueError("slide_numbers entries must be greater than or equal to 1.")

        if any(not sheet_name.strip() for sheet_name in self.sheet_names):
            raise ValueError("sheet_names entries must not be empty.")

        if any(not content_type.strip() for content_type in self.content_types):
            raise ValueError("content_types entries must not be empty.")
