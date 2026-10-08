from app.chunking.schemas import RetrievalChunk


SECTION_SEPARATOR = " > "


def build_search_text(chunk: RetrievalChunk) -> str:
    """Build a deterministic retrieval representation without mutating evidence."""
    if not chunk.section_path:
        return chunk.text

    section_context = SECTION_SEPARATOR.join(chunk.section_path)
    return f"Section: {section_context}\n\n{chunk.text}"
