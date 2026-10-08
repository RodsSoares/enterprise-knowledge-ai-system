from math import isfinite

from app.retrieval.openai_embeddings import (
    DEFAULT_EMBEDDING_MODEL,
    OpenAIEmbeddingProvider,
)


SMOKE_TEXT = "enterprise knowledge retrieval"


def main() -> None:
    provider = OpenAIEmbeddingProvider.from_environment()
    embedding = provider.embed_query(SMOKE_TEXT)

    if not embedding:
        raise RuntimeError("OpenAI returned an empty embedding.")

    if not all(isfinite(value) for value in embedding):
        raise RuntimeError("OpenAI returned a non-finite embedding value.")

    if not any(value != 0.0 for value in embedding):
        raise RuntimeError("OpenAI returned a zero embedding vector.")

    print("OpenAI embedding smoke test: PASS")
    print(f"Model: {DEFAULT_EMBEDDING_MODEL}")
    print(f"Input: {SMOKE_TEXT!r}")
    print(f"Dimensions: {len(embedding)}")
    print(f"First 5 values: {embedding[:5]}")


if __name__ == "__main__":
    main()
