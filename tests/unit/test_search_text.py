from pathlib import Path

from app.chunking.schemas import RetrievalChunk
from app.retrieval.search_text import build_search_text


def _chunk(
    *,
    text: str = "External AI vendors require security assessment.",
    section_path: tuple[str, ...] = (),
) -> RetrievalChunk:
    return RetrievalChunk(
        chunk_id="chunk-00001",
        order=0,
        text=text,
        source_block_ids=("text-00001",),
        source_path=Path("data/source/policies/ai-governance.pdf"),
        section_path=section_path,
        page_numbers=(4,),
        content_types=("text",),
    )


def test_build_search_text_returns_original_text_without_section_context() -> None:
    chunk = _chunk()
    assert build_search_text(chunk) == chunk.text


def test_build_search_text_adds_single_section_context() -> None:
    chunk = _chunk(section_path=("Third-Party AI",))
    assert build_search_text(chunk) == (
        "Section: Third-Party AI\n\n"
        "External AI vendors require security assessment."
    )


def test_build_search_text_preserves_section_hierarchy() -> None:
    chunk = _chunk(
        section_path=("AI Governance", "Third-Party AI", "Security Assessment")
    )
    assert build_search_text(chunk) == (
        "Section: AI Governance > Third-Party AI > Security Assessment\n\n"
        "External AI vendors require security assessment."
    )


def test_build_search_text_does_not_mutate_canonical_chunk_text() -> None:
    original_text = "Canonical evidence must remain unchanged."
    chunk = _chunk(text=original_text, section_path=("Governance",))
    search_text = build_search_text(chunk)

    assert search_text != chunk.text
    assert chunk.text == original_text
