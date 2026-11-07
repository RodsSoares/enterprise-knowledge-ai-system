"""Compose existing retrieval/context with generation; no test-module imports."""
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Protocol

from app.generation.answer_contract import StructuredAnswer, parse_answer, request_id_for, validate_answer
from app.generation.openai_answer_provider import GenerationResult
from app.retrieval.candidate_fusion import ReciprocalRankFusion
from app.retrieval.document_diversifier import DocumentDiversifier
from app.retrieval.evidence_context import EvidenceContext, EvidenceContextBuilder, ShortDocumentContextBuilder
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.lexical_index import BM25LexicalIndex
from app.retrieval.lexical_query_filter import FilteredLexicalRetriever
from app.retrieval.lexical_retriever import LexicalRetriever
from app.retrieval.vector_index import NumPyVectorIndex
from app.retrieval.vector_indexer import VectorIndexer
from app.retrieval.vector_retriever import VectorRetriever


class AnswerProvider(Protocol):
    def generate(self, question: str, context: EvidenceContext) -> GenerationResult: ...


@dataclass(frozen=True)
class RagResult:
    question: str
    answer: StructuredAnswer
    context: EvidenceContext
    generation: GenerationResult | None
    elapsed_seconds: float

    def to_dict(self):
        return {"question": self.question, "answer": self.answer.to_dict(),
                "context": {"text": self.context.text, "citations": self.context.citations,
                    "passage_count": len(self.context.passages),
                    "character_count": self.context.character_count,
                    "passage_roles": {p.citation_id: p.role for p in self.context.passages},
                    "skipped": [asdict(p) for p in self.context.skipped]},
                "generation": None if self.generation is None else {
                    "model": self.generation.model, "response_id": self.generation.response_id,
                    "usage": self.generation.usage},
                "elapsed_seconds": self.elapsed_seconds,
                "validation": "structure_and_citation_ids_only; semantic_support_not_verified"}


class RagService:
    def __init__(self, retriever, provider: AnswerProvider, builder=None):
        # retriever must return the fused pool BEFORE document diversity.
        self.retriever, self.provider = retriever, provider
        self.builder = builder or EvidenceContextBuilder()

    def ask(self, question: str) -> RagResult:
        if not isinstance(question, str) or not question.strip() or len(question) > 4000:
            raise ValueError("Question must contain 1–4000 characters")
        started = perf_counter()
        pool = self.retriever.retrieve(question, top_k=20)
        selected = DocumentDiversifier().select(pool, top_k=5)
        context = self.builder.build(selected, pool)
        generation = None
        if not context.passages:
            answer = validate_answer({"request_id": request_id_for(question, context),
                "status": "abstained", "claims": [],
                "abstention_reason": "Nenhuma evidência foi recuperada para a pergunta."},
                question=question, context=context)
        else:
            generation = self.provider.generate(question, context)
            answer = parse_answer(generation.raw, question=question, context=context)
        return RagResult(question, answer, context, generation, perf_counter() - started)


def build_service(chunks, embedding_provider, answer_provider):
    """Index once per session. Explicit demo composition; no default promotion."""
    chunks = tuple(chunks)
    if not chunks or len({c.chunk_id for c in chunks}) != len(chunks):
        raise ValueError("Nonempty corpus with unique chunk IDs required")
    vector = NumPyVectorIndex()
    VectorIndexer(embedding_provider, vector).index(chunks)
    lexical = BM25LexicalIndex()
    lexical.add([c.chunk_id for c in chunks], [c.text for c in chunks])
    retriever = HybridRetriever(VectorRetriever(embedding_provider, vector, chunks),
        FilteredLexicalRetriever(LexicalRetriever(lexical, chunks)),
        ReciprocalRankFusion(), candidate_depth=20)  # No diversity here: retain pool.
    return RagService(retriever, answer_provider, ShortDocumentContextBuilder(chunks))
