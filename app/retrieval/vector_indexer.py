from collections.abc import Sequence

from app.chunking.schemas import RetrievalChunk
from app.retrieval.embeddings import EmbeddingProvider
from app.retrieval.search_text import build_search_text
from app.retrieval.vector_index import NumPyVectorIndex


class VectorIndexer:
    """Transforms canonical chunks into embeddings and loads the vector index."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_index: NumPyVectorIndex,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._vector_index = vector_index

    def index(self, chunks: Sequence[RetrievalChunk]) -> None:
        if not chunks:
            raise ValueError("chunks must not be empty.")

        chunk_ids = tuple(chunk.chunk_id for chunk in chunks)
        search_texts = tuple(build_search_text(chunk) for chunk in chunks)
        embeddings = self._embedding_provider.embed_documents(search_texts)

        if len(embeddings) != len(chunks):
            raise ValueError(
                "embedding provider must return one embedding for each chunk."
            )

        self._vector_index.add(
            chunk_ids=chunk_ids,
            embeddings=embeddings,
        )
