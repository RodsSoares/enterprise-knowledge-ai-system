from dataclasses import dataclass
from pathlib import Path

from app.chunking.schemas import RetrievalChunk
from app.ingestion.schemas import NormalizedContent, TextBlock


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
            raise ValueError(
                "target_chars must be less than or equal to max_chars."
            )

    def chunk(
        self,
        content: NormalizedContent,
        source_path: Path,
    ) -> tuple[RetrievalChunk, ...]:
        text_blocks = tuple(
            block
            for block in content.ordered_blocks
            if isinstance(block, TextBlock)
        )

        if not text_blocks:
            return ()

        grouped_blocks: list[list[TextBlock]] = []
        current_group: list[TextBlock] = []

        for block in text_blocks:
            if len(block.text) > self.max_chars:
                if current_group:
                    grouped_blocks.append(current_group)
                    current_group = []

                grouped_blocks.extend(
                    [fragment]
                    for fragment in self._split_oversized_block(block)
                )
                continue

            if not current_group:
                current_group.append(block)
                continue

            same_section = (
                block.location.section_path
                == current_group[0].location.section_path
            )

            if not same_section:
                grouped_blocks.append(current_group)
                current_group = [block]
                continue

            current_text = self._join_text(tuple(current_group))

            if len(current_text) >= self.target_chars:
                grouped_blocks.append(current_group)
                current_group = [block]
                continue

            candidate_blocks = (*current_group, block)
            candidate_text = self._join_text(candidate_blocks)

            if len(candidate_text) <= self.max_chars:
                current_group.append(block)
                continue

            grouped_blocks.append(current_group)
            current_group = [block]

        if current_group:
            grouped_blocks.append(current_group)

        return tuple(
            self._build_chunk(
                blocks=tuple(blocks),
                chunk_order=chunk_order,
                source_path=source_path,
            )
            for chunk_order, blocks in enumerate(grouped_blocks)
        )

    @staticmethod
    def _join_text(blocks: tuple[TextBlock, ...]) -> str:
        return "\n\n".join(block.text for block in blocks)

    def _split_oversized_block(
        self,
        block: TextBlock,
    ) -> tuple[TextBlock, ...]:
        fragments: list[TextBlock] = []

        for start in range(0, len(block.text), self.max_chars):
            fragment_text = block.text[start : start + self.max_chars]

            fragments.append(
                TextBlock(
                    block_id=block.block_id,
                    order=block.order,
                    kind=block.kind,
                    text=fragment_text,
                    location=block.location,
                    parent_id=block.parent_id,
                )
            )

        return tuple(fragments)

    def _build_chunk(
        self,
        blocks: tuple[TextBlock, ...],
        chunk_order: int,
        source_path: Path,
    ) -> RetrievalChunk:
        page_numbers = tuple(
            dict.fromkeys(
                block.location.page_number
                for block in blocks
                if block.location.page_number is not None
            )
        )

        slide_numbers = tuple(
            dict.fromkeys(
                block.location.slide_number
                for block in blocks
                if block.location.slide_number is not None
            )
        )

        sheet_names = tuple(
            dict.fromkeys(
                block.location.sheet_name
                for block in blocks
                if block.location.sheet_name is not None
            )
        )

        return RetrievalChunk(
            chunk_id=f"chunk-{chunk_order + 1:05d}",
            order=chunk_order,
            text=self._join_text(blocks),
            source_block_ids=tuple(
                dict.fromkeys(block.block_id for block in blocks)
            ),
            source_path=source_path,
            section_path=blocks[0].location.section_path,
            page_numbers=page_numbers,
            slide_numbers=slide_numbers,
            sheet_names=sheet_names,
            content_types=("text",),
        )
