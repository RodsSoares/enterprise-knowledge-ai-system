from typing import Protocol, runtime_checkable


Embedding = tuple[float, ...]


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Provider-agnostic contract for document and query embeddings."""

    def embed_documents(self, texts: tuple[str, ...]) -> tuple[Embedding, ...]:
        """Return one embedding for each document text, preserving input order."""
        ...

    def embed_query(self, text: str) -> Embedding:
        """Return the embedding representation for a single retrieval query."""
        ...
