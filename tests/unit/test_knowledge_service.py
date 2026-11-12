"""Knowledge service over the committed catalog, with a fake SDK; no API calls."""
from decimal import Decimal
import json
from types import SimpleNamespace

import pytest

from app.service.knowledge_service import (
    DailyBudget, DailyBudgetExceeded, KnowledgeService, ModelLocked, SessionBudgetExceeded,
    load_runtime_config,
)
from app.service.upload_reader import UploadError


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


NOTE = "Reembolsos de viagem exigem recibo e aprovação do gestor em até 30 dias.".encode("utf-8")


def fresh(config, sdk=None, **overrides):
    return KnowledgeService(sdk or FakeSDK(), {**config, **overrides}, daily_budget=DailyBudget())


def test_protected_model_needs_an_explicit_unlock(config):
    service = fresh(config)
    assert service.is_protected("gpt-6.1-sol") and not service.is_protected(config["default_model"])
    with pytest.raises(ModelLocked):
        service.ask("Quem aprova uma nova ferramenta de IA?", model="gpt-6.1-sol")
    answer = service.ask("Quem aprova uma nova ferramenta de IA?", model="gpt-6.1-sol", unlocked=True)
    assert answer.model == "gpt-6.1-sol" and answer.answered


def test_default_model_cannot_be_protected(config, tmp_path):
    import json
    bad = tmp_path / "c.json"
    bad.write_text(json.dumps({**config, "protected_models": [config["default_model"]]}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_runtime_config(bad)


def test_cited_corpus_source_can_be_opened_and_unknown_paths_are_refused(config):
    service = fresh(config)
    answer = service.ask("Qual é a meta vigente de OTIF para operações nacionais?")
    path = answer.sources[0].source_path
    assert path.startswith("data/source/corporate_repository/")
    assert len(service.source_file(path)) > 100
    with pytest.raises(ValueError):
        service.source_file("config/lean_runtime.json")
    with pytest.raises(ValueError):
        service.source_file("../etc/passwd")


def test_uploaded_document_is_indexed_and_answered_from_in_its_own_scope(config):
    sdk = FakeSDK()
    service = fresh(config, sdk)
    upload = service.add_upload("viagens.txt", NOTE)
    assert upload.document_id == "UP-01" and len(upload.units) == len(upload.vectors) == 1
    assert service.session_cost > 0
    answer = service.ask("Qual é o prazo de reembolso?", scope="uploads")
    assert answer.answered and answer.scope == "uploads"
    source = answer.sources[0]
    assert source.document_id == "UP-01" and source.title == "viagens.txt"
    assert source.status == "uploaded" and source.source_path == ""
    evidence = [call for call in sdk.calls if call == "lean_answer"]
    assert len(evidence) == 1


def test_combined_scope_searches_corpus_and_uploads_and_corpus_scope_ignores_uploads(config):
    service = fresh(config)
    service.add_upload("viagens.txt", NOTE)
    units, vectors, metadata = service._collection("all")
    assert len(units) == len(service.units) + 1 and "UP-01" in metadata and "DOC-001" in metadata
    assert len(vectors) == len(service.vectors) + 1
    assert "UP-01" not in service._collection("corpus")[2]
    assert set(service._collection("uploads")[2]) == {"UP-01"}


def test_upload_scope_without_uploads_is_rejected(config):
    with pytest.raises(ValueError):
        fresh(config).ask("Qual é o prazo?", scope="uploads")


def test_upload_limits_and_duplicates_are_enforced(config):
    service = fresh(config, max_upload_files=2)
    service.add_upload("a.txt", NOTE)
    with pytest.raises(UploadError, match="já foi enviado"):
        service.add_upload("copia.txt", NOTE)
    service.add_upload("b.txt", NOTE + b" Outra regra.")
    with pytest.raises(UploadError, match="Limite de 2"):
        service.add_upload("c.txt", NOTE + b" Terceira.")
    too_big = fresh(config, max_upload_mb=1)
    with pytest.raises(UploadError, match="maior que 1 MB"):
        too_big.add_upload("grande.txt", b"x" * (1024 * 1024 + 1))
    too_long = fresh(config, max_upload_units=1)
    with pytest.raises(UploadError, match="grande demais"):
        too_long.add_upload("longo.txt", ("palavra " * 1000).encode("utf-8"))


def test_removed_upload_is_no_longer_searched(config):
    service = fresh(config)
    service.add_upload("viagens.txt", NOTE)
    service.remove_upload("UP-01")
    assert service._collection("all")[0] == service.units


def test_daily_ceiling_is_shared_by_sessions_and_blocks_new_calls(config):
    daily = DailyBudget()
    first = KnowledgeService(FakeSDK(), config, daily_budget=daily)
    second = KnowledgeService(FakeSDK(), config, daily_budget=daily)
    answer = first.ask("Quem aprova uma nova ferramenta de IA?")
    ceiling = Decimal(config["max_cost_per_day_usd"])
    assert daily.remaining(ceiling) == ceiling - answer.cost_usd and second.session_cost == 0
    daily.add(daily.remaining(ceiling))  # other sessions used the rest of the day
    with pytest.raises(DailyBudgetExceeded):
        second.ask("Quem aprova uma nova ferramenta de IA?")
    with pytest.raises(DailyBudgetExceeded):
        second.add_upload("viagens.txt", NOTE)
    assert second.uploads == {}
