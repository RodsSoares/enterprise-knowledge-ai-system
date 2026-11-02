from dataclasses import dataclass
from pathlib import Path

from app.chunking.block_serializer import BlockSerializer
from app.chunking.schemas import RetrievalChunk
from app.ingestion.schemas import ContentBlock, NormalizedContent, SpreadsheetBlock


@dataclass(frozen=True, slots=True)
class _ChunkBlock:
    """Retrieval-ready projection of one canonical content block."""

    block: ContentBlock
    text: str
    content_type: str


@dataclass(frozen=True, slots=True)
class StructureAwareChunker:
    """Deterministic chunker that prioritizes canonical source structure."""

    target_chars: int
    max_chars: int

    def __post_init__(self) -> None:
        if self.target_chars < 1:
            raise ValueError("target_chars must be greater than or equal to 1.")
        if self.max_chars < 1:
            raise ValueError("max_chars must be greater than or equal to 1.")
        if self.target_chars > self.max_chars:
            raise ValueError("target_chars must be less than or equal to max_chars.")

    def chunk(
        self,
        content: NormalizedContent,
        source_path: Path,
        document_id: str,
    ) -> tuple[RetrievalChunk, ...]:
        if not document_id.strip():
            raise ValueError("document_id must not be empty.")

        serializer = BlockSerializer()
        projected_blocks: list[_ChunkBlock] = []

        for block in content.ordered_blocks:
            serialized = serializer.serialize(block)
            if serialized is None or not serialized.strip():
                continue

            projected_blocks.append(
                _ChunkBlock(
                    block=block,
                    text=serialized,
                    content_type=self._content_type(block),
                )
            )

        if not projected_blocks:
            return ()

        grouped_blocks: list[list[_ChunkBlock]] = []
        current_group: list[_ChunkBlock] = []

        for projected in projected_blocks:
            if len(projected.text) > self.max_chars:
                if current_group:
                    grouped_blocks.append(current_group)
                    current_group = []

                grouped_blocks.extend(
                    [fragment] for fragment in self._split_oversized_block(projected)
                )
                continue

            if not current_group:
                current_group.append(projected)
                continue

            if not self._same_structure(projected, current_group[0]):
                grouped_blocks.append(current_group)
                current_group = [projected]
                continue

            current_text = self._join_text(tuple(current_group))
            if len(current_text) >= self.target_chars:
                grouped_blocks.append(current_group)
                current_group = [projected]
                continue

            candidate_blocks = (*current_group, projected)
            if len(self._join_text(candidate_blocks)) <= self.max_chars:
                current_group.append(projected)
                continue

            grouped_blocks.append(current_group)
            current_group = [projected]

        if current_group:
            grouped_blocks.append(current_group)

        return tuple(
            self._build_chunk(
                blocks=tuple(blocks),
                chunk_order=chunk_order,
                source_path=source_path,
                document_id=document_id,
            )
            for chunk_order, blocks in enumerate(grouped_blocks)
        )

    @staticmethod
    def _content_type(block: ContentBlock) -> str:
        mapping = {
            "TextBlock": "text",
            "TableBlock": "table",
            "SpreadsheetBlock": "spreadsheet",
            "ChartBlock": "chart",
            "ImageBlock": "image",
        }
        name = type(block).__name__
        return mapping.get(name, name.removesuffix("Block").lower())

    @classmethod
    def _same_structure(cls, left: _ChunkBlock, right: _ChunkBlock) -> bool:
        # Preserve the original text-chunking behavior: page/slide boundaries are
        # provenance, not grouping boundaries. Section remains the semantic boundary.
        # Spreadsheet blocks use sheet identity as their structural boundary.
        if left.content_type != right.content_type:
            return False

        if left.content_type == "spreadsheet":
            return cls._sheet_name(left.block) == cls._sheet_name(right.block)

        return cls._section_path(left.block) == cls._section_path(right.block)

    @staticmethod
    def _location(block: ContentBlock):
        return getattr(block, "location", None)

    @classmethod
    def _section_path(cls, block: ContentBlock) -> tuple[str, ...]:
        location = cls._location(block)
        return () if location is None else location.section_path

    @classmethod
    def _page_number(cls, block: ContentBlock) -> int | None:
        location = cls._location(block)
        return None if location is None else location.page_number

    @classmethod
    def _slide_number(cls, block: ContentBlock) -> int | None:
        location = cls._location(block)
        return None if location is None else location.slide_number

    @classmethod
    def _sheet_name(cls, block: ContentBlock) -> str | None:
        if isinstance(block, SpreadsheetBlock):
            return block.sheet_name
        location = cls._location(block)
        return None if location is None else location.sheet_name

    @staticmethod
    def _join_text(blocks: tuple[_ChunkBlock, ...]) -> str:
        return "\n\n".join(block.text for block in blocks)

    def _split_oversized_block(
        self,
        block: _ChunkBlock,
    ) -> tuple[_ChunkBlock, ...]:
        return tuple(
            _ChunkBlock(
                block=block.block,
                text=block.text[start : start + self.max_chars],
                content_type=block.content_type,
            )
            for start in range(0, len(block.text), self.max_chars)
        )

    def _build_chunk(
        self,
        blocks: tuple[_ChunkBlock, ...],
        chunk_order: int,
        source_path: Path,
        document_id: str,
    ) -> RetrievalChunk:
        canonical_blocks = tuple(item.block for item in blocks)

        page_numbers = tuple(
            dict.fromkeys(
                page_number
                for block in canonical_blocks
                if (page_number := self._page_number(block)) is not None
            )
        )
        slide_numbers = tuple(
            dict.fromkeys(
                slide_number
                for block in canonical_blocks
                if (slide_number := self._slide_number(block)) is not None
            )
        )
        sheet_names = tuple(
            dict.fromkeys(
                sheet_name
                for block in canonical_blocks
                if (sheet_name := self._sheet_name(block)) is not None
            )
        )

        return RetrievalChunk(
            chunk_id=f"{document_id}::chunk-{chunk_order + 1:05d}",
            document_id=document_id,
            order=chunk_order,
            text=self._join_text(blocks),
            source_block_ids=tuple(
                dict.fromkeys(block.block_id for block in canonical_blocks)
            ),
            source_path=source_path,
            section_path=self._section_path(canonical_blocks[0]),
            page_numbers=page_numbers,
            slide_numbers=slide_numbers,
            sheet_names=sheet_names,
            content_types=tuple(dict.fromkeys(item.content_type for item in blocks)),
        )
