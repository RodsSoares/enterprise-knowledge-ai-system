"""Knowledge service over the committed catalog, with a fake SDK; no API calls."""
from decimal import Decimal
import json
from types import SimpleNamespace

import pytest

from app.service.knowledge_service import (
    KnowledgeService, SessionBudgetExceeded, load_runtime_config,
)


class FakeSDK:
    """Answers with the first evidence item and approves it."""

    def __init__(self, answer=None):
        self.calls = []
        self.answer = answer

    def with_options(self, **kwargs):
        return self

    @property
    def embeddings(self):
        def create(**kw):
            self.calls.append("embeddings")
            texts = [kw["input"]] if isinstance(kw["input"], str) else kw["input"]
            data = [SimpleNamespace(index=i, embedding=[1.0] + [0.0] * 1535)
                    for i, _ in enumerate(texts)]
            return SimpleNamespace(data=data, usage=SimpleNamespace(prompt_tokens=10))
        return SimpleNamespace(create=create)

    @property
    def responses(self):
        def create(**kw):
            stage = kw["text"]["format"]["name"]
            self.calls.append(stage)
            if stage == "lean_answer":
                payload = self.answer or {
                    "evidence_use": [{"id": "E1", "relevance": "direct"}], "decision": "answer",
                    "claims": [{"text": "A regra consta do primeiro trecho.", "citation_ids": ["E1"]}],
                    "recovery_query": None, "message": ""}
            else:
                payload = {"decision": "PASS", "materially_complete": True, "reason": "Verificado.",
                           "claim_checks": [{"claim_index": 0, "entailed": True, "relevant": True,
                                             "conditions_preserved": True}]}
            return SimpleNamespace(status="completed", output_text=json.dumps(payload), output=(),
                                   id="r", model=kw["model"],
                                   usage=SimpleNamespace(input_tokens=1000, output_tokens=100))
        return SimpleNamespace(create=create)


@pytest.fixture(scope="module")
def config():
    return load_runtime_config()


def test_runtime_config_points_to_a_verified_catalog_of_the_whole_corpus(config):
    service = KnowledgeService(FakeSDK(), config)
    assert service.documents == 27 and len(service.units) > 200


def test_question_returns_cited_answer_with_source_text_and_cost(config):
    sdk = FakeSDK()
    service = KnowledgeService(sdk, config)
    answer = service.ask("Qual é a meta vigente de OTIF para operações nacionais?")
    assert answer.answered and answer.status == "answered_pending_human_review"
    assert answer.sources[0].alias == "E1" and answer.sources[0].text
    assert answer.sources[0].document_id.startswith("DOC-")
    assert sdk.calls == ["embeddings", "lean_answer", "lean_verify"]
    assert answer.calls == 3 and answer.cost_usd > 0
    assert service.session_cost == answer.cost_usd and service.questions == 1


def test_abstention_is_reported_without_sources(config):
    sdk = FakeSDK({"evidence_use": [], "decision": "abstain", "claims": [],
                   "recovery_query": None, "message": "Os documentos não tratam do assunto."})
    answer = KnowledgeService(sdk, config).ask("Qual é a política para material radioativo?")
    assert not answer.answered and answer.status == "abstained"
    assert answer.sources == () and "não tratam" in answer.message


def test_session_ceiling_blocks_further_questions(config):
    service = KnowledgeService(FakeSDK(), {**config, "max_cost_per_session_usd": "0.0001"})
    service.session_cost = Decimal("0.0001")
    with pytest.raises(SessionBudgetExceeded):
        service.ask("Quem aprova uma nova ferramenta de IA?")


def test_repeated_question_reuses_the_query_embedding(config):
    sdk = FakeSDK()
    service = KnowledgeService(sdk, config)
    service.ask("Quem aprova uma nova ferramenta de IA?")
    service.ask("Quem aprova uma nova ferramenta de IA?")
    assert sdk.calls.count("embeddings") == 1


def test_unknown_model_and_empty_question_are_rejected(config):
    service = KnowledgeService(FakeSDK(), config)
    with pytest.raises(ValueError):
        service.ask("Pergunta?", model="modelo-inexistente")
    with pytest.raises(ValueError):
        service.ask("   ")
