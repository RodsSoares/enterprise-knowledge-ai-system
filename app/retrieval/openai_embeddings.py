from typing import Any

from app.retrieval.embeddings import Embedding


DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


class OpenAIEmbeddingProvider:
    """OpenAI adapter implementing the project's provider-agnostic embedding contract."""

    def __init__(
        self,
        client: Any,
        model: str = DEFAULT_EMBEDDING_MODEL,
    ) -> None:
        if not model.strip():
            raise ValueError("model must not be empty.")

        self._client = client
        self._model = model

    @classmethod
    def from_environment(
        cls,
        model: str = DEFAULT_EMBEDDING_MODEL,
    ) -> "OpenAIEmbeddingProvider":
        """Create the real OpenAI client using OPENAI_API_KEY from the environment."""
        from openai import OpenAI

        return cls(
            client=OpenAI(),
            model=model,
        )

    def embed_documents(self, texts: tuple[str, ...]) -> tuple[Embedding, ...]:
        if not texts:
            return ()

        if any(not text.strip() for text in texts):
            raise ValueError("document texts must not contain empty values.")

        response = self._client.embeddings.create(
            input=list(texts),
            model=self._model,
            encoding_format="float",
        )

        ordered_data = sorted(response.data, key=lambda item: item.index)

        if len(ordered_data) != len(texts):
            raise ValueError(
                "OpenAI returned a different number of embeddings than requested."
            )

        return tuple(
            tuple(float(value) for value in item.embedding)
            for item in ordered_data
        )

    def embed_query(self, text: str) -> Embedding:
        if not text.strip():
            raise ValueError("query text must not be empty.")

        response = self._client.embeddings.create(
            input=text,
            model=self._model,
            encoding_format="float",
        )

        if len(response.data) != 1:
            raise ValueError("OpenAI must return exactly one embedding for a query.")

        return tuple(float(value) for value in response.data[0].embedding)
