"""Focused integration checks with real retrieval and a fake provider boundary."""
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest

from app.chunking.schemas import RetrievalChunk
from app.generation.answer_contract import AnswerContractError, request_id_for
from app.generation.openai_answer_provider import GenerationError, OpenAIAnswerProvider, GenerationResult
from app.generation.rag_service import RagService, build_service
from app.retrieval.candidate_fusion import FusedCandidate
from app.retrieval.evidence_context import EvidenceContextBuilder, ContextBudgetError
from app.scripts.ask_knowledge import discover_sources, main, print_result


def chunks():
    return tuple(RetrievalChunk(chunk_id=f"DOC-{i:03}::chunk-{n}", document_id=f"DOC-{i:03}",
        order=n, text=f"Regra {i}: compartilhar dados exige aprovação. Trecho {n}.",
        source_block_ids=(f"b{i}-{n}",), source_path=Path(f"DOC-{i:03}_policy.md"),
        content_types=("text",)) for i, n in [(1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (1, 1)])


def reply(question, context, status="answered"):
    return json.dumps({"request_id": request_id_for(question, context), "status": status,
        "claims": [{"text": "Compartilhar dados exige aprovação.", "citation_ids": ["E1"]}]
                  if status == "answered" else [],
        "abstention_reason": None if status == "answered" else "Faltam informações."})


def provider():
    p = Mock()
    p.generate.side_effect = lambda q, c: GenerationResult(reply(q, c), "fake", "r1", {})
    return p


def service(p=None, builder=None):
    pool = tuple(FusedCandidate(c, 1/(60+i), i, ("vector",)) for i, c in enumerate(chunks(), 1))
    retriever = Mock()
    retriever.retrieve.return_value = pool
    return RagService(retriever, p or provider(), builder)


def test_real_hybrid_context_generation_pipeline_and_repeated_questions(capsys):
    embeddings = Mock()
    embeddings.embed_documents.return_value = tuple((1.0, i / 10) for i in range(6))
    embeddings.embed_query.return_value = (1.0, 0.1)
    p = provider()
    rag = build_service(chunks(), embeddings, p)
    result = rag.ask("Como compartilhar dados?")
    assert result.answer.status == "answered"
    assert len(result.context.passages) == 6  # supplementary passage survived pool selection
    assert result.to_dict()["generation"]["model"] == "fake"
    print_result(result)
    output = capsys.readouterr().out
    assert "Fontes:" in output and "Compartilhar dados exige aprovação" in output
    second = rag.ask("Quem aprova compartilhar dados?")
    assert result.answer.request_id != second.answer.request_id
    assert embeddings.embed_documents.call_count == 1
    assert embeddings.embed_query.call_count == 2
    assert p.generate.call_count == 2


def test_empty_retrieval_abstains_without_llm():
    rag = service()
    rag.retriever.retrieve.return_value = ()
    result = rag.ask("Pergunta")
    assert result.answer.status == "abstained" and result.generation is None
    rag.provider.generate.assert_not_called()


def test_nonempty_context_can_abstain():
    p = provider()
    p.generate.side_effect = lambda q, c: GenerationResult(reply(q, c, "abstained"), "fake", None, {})
    assert service(p).ask("Pergunta").answer.status == "abstained"


def test_unknown_reference_blocks_displayable_result():
    p = provider()
    p.generate.side_effect = lambda q, c: GenerationResult(reply(q, c).replace('"E1"', '"E99"'), "fake", None, {})
    with pytest.raises(AnswerContractError): service(p).ask("Pergunta")


def test_provider_failure_propagates_without_retry_or_abstention():
    p = provider()
    p.generate.side_effect = TimeoutError("timeout")
    with pytest.raises(TimeoutError): service(p).ask("Pergunta")
    assert p.generate.call_count == 1


def test_budget_failure_does_not_call_provider():
    p = provider()
    with pytest.raises(ContextBudgetError):
        service(p, EvidenceContextBuilder(max_characters=1)).ask("Pergunta")
    p.generate.assert_not_called()


def test_invalid_question_stops_before_retrieval():
    rag = service()
    for question in ("  ", "x" * 4001):
        with pytest.raises(ValueError): rag.ask(question)
    rag.retriever.retrieve.assert_not_called()


def test_adapter_uses_structured_output_and_separates_data_from_instructions():
    result = service().ask("Pergunta")
    client = Mock()
    client.responses.create.return_value = NS(status="completed", output=[],
        output_text=reply(result.question, result.context), model="test-model", id="r1",
        usage=NS(input_tokens=100, output_tokens=50, total_tokens=150))
    generated = OpenAIAnswerProvider(client, model="test-model").generate(result.question, result.context)
    call = client.responses.create.call_args.kwargs
    assert call["store"] is False and call["max_output_tokens"] == 2000
    assert call["text"]["format"]["strict"] is True
    assert call["text"]["format"]["schema"]["additionalProperties"] is False
    assert "evidence" in json.loads(call["input"][0]["content"])
    assert generated.usage["total_tokens"] == 150


@pytest.mark.parametrize("kind", ["incomplete", "refusal", "empty"])
def test_adapter_rejects_incomplete_refused_or_empty_responses(kind):
    result = service().ask("Pergunta")
    client = Mock()
    client.responses.create.return_value = NS(status="incomplete" if kind == "incomplete" else "completed",
        output=[NS(content=[NS(type="refusal")])] if kind == "refusal" else [],
        output_text="" if kind == "empty" else "{}")
    with pytest.raises(GenerationError):
        OpenAIAnswerProvider(client).generate(result.question, result.context)


def test_source_discovery_excludes_generated_files_and_rejects_duplicate_ids(tmp_path):
    (tmp_path / 'DOC-001_Policy.md').write_text('Policy')
    (tmp_path / '.DOC-001_Policy.docling-normalized.md').write_text('Generated')
    assert len(discover_sources(tmp_path)) == 1
    (tmp_path / 'DOC-001_Copy.pdf').touch()
    with pytest.raises(ValueError): discover_sources(tmp_path)


def test_cli_rejects_existing_output_before_api_or_parsing(tmp_path):
    target = tmp_path / 'existing.json'
    target.write_text('original')
    with pytest.raises(SystemExit): main(['--question', 'Pergunta', '--output', str(target)])
    assert target.read_text() == 'original'


def test_cli_interactive_session_indexes_once_and_handles_two_questions(monkeypatch, tmp_path, capsys):
    import openai
    import app.scripts.ask_knowledge as cli
    (tmp_path / 'DOC-001_Test.md').write_text('source')
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(openai, 'OpenAI', Mock(return_value=client))
    monkeypatch.setenv('OPENAI_API_KEY', 'fake-test-only')
    monkeypatch.setattr(cli, 'load_chunks', Mock(return_value=chunks()))
    rag = service()
    build = Mock(return_value=rag)
    monkeypatch.setattr(cli, 'build_service', build)
    inputs = iter(['Pergunta um', 'Pergunta dois', '/sair'])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))
    assert main(['--corpus', str(tmp_path)]) == 0
    assert build.call_count == 1 and rag.provider.generate.call_count == 2
    assert capsys.readouterr().out.count('Resposta:') == 2


def test_short_document_expansion_recovers_table_outside_retrieval_pool():
    from app.retrieval.evidence_context import ShortDocumentContextBuilder
    header = replace(chunks()[0], text="Policy heading")
    table = replace(header, chunk_id="DOC-001::table", order=10,
                    text="Restricted | Explicit approval required", content_types=("table",))
    pool = (FusedCandidate(header, 0.1, 1, ("vector",)),)
    context = ShortDocumentContextBuilder([header, table]).build(pool, pool)
    assert context.passages[0].chunk == header
    assert context.passages[1].chunk == table
    assert context.passages[1].source == table  # no fabricated retrieval score
    assert context.passages[1].role == "parent_document"
    assert request_id_for("Question", context)


def test_parent_document_budget_is_atomic_and_preserves_anchors():
    from app.retrieval.evidence_context import ShortDocumentContextBuilder
    corpus = chunks()
    pool = (FusedCandidate(corpus[0], 0.1, 1, ("vector",)),)
    baseline = EvidenceContextBuilder(max_additional_per_document=0).build(pool, pool)
    context = ShortDocumentContextBuilder(corpus,
        max_characters=baseline.character_count).build(pool, pool)
    assert context.text == baseline.text
    assert context.skipped[0].reason == "complete_document_budget"
    assert len(context.passages) == 1
    # Unselected documents must never leak into context.
    assert context.selected_document_ids == ("DOC-001",)


def test_long_document_uses_ranked_supplement_instead_of_full_expansion():
    from app.retrieval.evidence_context import ShortDocumentContextBuilder
    corpus = chunks()
    pool = tuple(FusedCandidate(c, 0.1, i, ("vector",))
                 for i, c in enumerate([corpus[0], corpus[-1]], 1))
    context = ShortDocumentContextBuilder(corpus, max_document_characters=1).build(pool[:1], pool)
    assert [p.role for p in context.passages] == ["anchor", "supplement"]
    assert context.skipped == ()


def test_parent_expansion_rejects_stale_corpus_text():
    from app.retrieval.evidence_context import ShortDocumentContextBuilder
    corpus = chunks()
    stale = replace(corpus[0], text="changed")
    pool = (FusedCandidate(stale, 0.1, 1, ("vector",)),)
    with pytest.raises(ValueError, match="differs"):
        ShortDocumentContextBuilder(corpus).build(pool, pool)


def test_parent_expansion_is_independent_of_corpus_insertion_order():
    from app.retrieval.evidence_context import ShortDocumentContextBuilder
    corpus = chunks()
    pool = (FusedCandidate(corpus[0], 0.1, 1, ("vector",)),)
    first = ShortDocumentContextBuilder(corpus).build(pool, pool)
    second = ShortDocumentContextBuilder(tuple(reversed(corpus))).build(pool, pool)
    assert first == second
