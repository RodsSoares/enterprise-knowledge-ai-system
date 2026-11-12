"""Single entry point for asking the knowledge base a question.

Loads the verified evidence catalog and its embedding cache once, then answers
questions through the lean pipeline. Every question has its own cost ceiling
and the service keeps a session total that it refuses to exceed. Prices come
from the runtime configuration and must be checked against current billing.
"""
from dataclasses import dataclass
from decimal import Decimal
import json
from pathlib import Path

from app.chunking.evidence_snapshot import verify_snapshot
from app.orchestration.lean_live_provider import LeanLiveProvider
from app.orchestration.lean_pipeline import run_lean
from app.orchestration.live_provider import BudgetedClient, RunBudget
from app.retrieval.adaptive_evidence_retriever import AdaptiveEvidenceUnitRetriever
from app.retrieval.evidence_unit_retriever import read_cache
from app.retrieval.openai_embeddings import OpenAIEmbeddingProvider

DEFAULT_RUNTIME_CONFIG = Path("config/lean_runtime.json")
REQUIRED = {"snapshot", "embedding_cache", "embedding_model", "default_model", "models",
            "embedding_price_per_million", "as_of", "top_k", "expand_documents",
            "max_cost_per_question_usd", "max_cost_per_session_usd",
            "max_output_tokens_per_call", "deadline_seconds"}
ANSWERED = ("answered_pending_human_review", "answered_with_reservations")


class SessionBudgetExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class Source:
    alias: str
    document_id: str
    title: str
    version: str
    status: str
    section: str
    text: str


@dataclass(frozen=True)
class Answer:
    status: str
    answered: bool
    text: str
    claims: tuple
    sources: tuple
    reservations: tuple
    message: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal
    calls: int
    elapsed_seconds: float
    report: dict


def load_runtime_config(path=DEFAULT_RUNTIME_CONFIG):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    if set(config) != REQUIRED:
        raise ValueError("Runtime config fields differ from the expected set")
    if config["default_model"] not in config["models"]:
        raise ValueError("Default model must be one of the configured models")
    for name, model in config["models"].items():
        if not {"label", "input_per_million", "output_per_million"} <= set(model):
            raise ValueError("Model needs label and prices: " + name)
    for key in ("max_cost_per_question_usd", "max_cost_per_session_usd"):
        if not Decimal(str(config[key])) > 0:
            raise ValueError("Positive cost ceilings required")
    return config


class KnowledgeService:
    def __init__(self, sdk, config=None, *, root=None):
        """sdk: an OpenAI client (or a test double with the same interface)."""
        self.sdk = sdk
        self.config = config or load_runtime_config()
        root = Path(root) if root is not None else Path.cwd()
        snapshot = json.loads((root / self.config["snapshot"]).read_text(encoding="utf-8"))
        self.units = verify_snapshot(snapshot, root=root)
        cache = json.loads((root / self.config["embedding_cache"]).read_text(encoding="utf-8"))
        self.vectors = read_cache(cache, self.units, self.config["embedding_model"])
        self.snapshot_id = snapshot["snapshot_id"]
        self.catalog = {unit.unit_id: unit for unit in self.units}
        self.metadata = {d["document_id"]: {**d["metadata"], "as_of": self.config["as_of"]}
                         for d in snapshot["snapshot"]["documents"]}
        self.query_cache = {}
        self.session_cost = Decimal(0)
        self.questions = 0

    @property
    def documents(self):
        return len(self.metadata)

    @property
    def session_remaining(self):
        return Decimal(str(self.config["max_cost_per_session_usd"])) - self.session_cost

    def prices(self, model):
        chosen = self.config["models"][model]
        return {model: {"input_per_million": chosen["input_per_million"],
                        "output_per_million": chosen["output_per_million"]},
                self.config["embedding_model"]: {
                    "input_per_million": self.config["embedding_price_per_million"],
                    "output_per_million": "0"}}

    def ask(self, question, *, model=None):
        model = model or self.config["default_model"]
        if model not in self.config["models"]:
            raise ValueError("Unknown model: " + str(model))
        if not isinstance(question, str) or not question.strip() or len(question) > 4000:
            raise ValueError("Question must contain 1-4000 characters")
        ceiling = min(Decimal(str(self.config["max_cost_per_question_usd"])), self.session_remaining)
        if ceiling <= 0:
            raise SessionBudgetExceeded("Session cost ceiling reached")
        budget = RunBudget(120000, 20000, 6, self.config["deadline_seconds"], str(ceiling))
        client = BudgetedClient(self.sdk, budget, self.prices(model), transport_retries=2)
        retriever = AdaptiveEvidenceUnitRetriever(
            self.units, self.vectors,
            OpenAIEmbeddingProvider(client, model=self.config["embedding_model"]))
        retriever.query_cache = self.query_cache
        report = run_lean(question.strip(), snapshot_id=self.snapshot_id, units=self.units,
                          retriever=retriever,
                          provider=LeanLiveProvider(client, model, self.config["max_output_tokens_per_call"]),
                          document_metadata=self.metadata, top_k=self.config["top_k"],
                          expand_documents=self.config["expand_documents"])
        usage = client.report()
        cost = Decimal(usage["estimated_cost_usd"])
        self.session_cost += cost
        self.questions += 1
        return self._answer(report, model, usage, cost)

    def _answer(self, report, model, usage, cost):
        answered = report["status"] in ANSWERED
        claims = tuple(report["answer"]["claims"]) if answered else ()
        sources = []
        for alias in dict.fromkeys(uid for claim in claims for uid in claim["citation_ids"]):
            unit = self.catalog[report["evidence_ids"][alias]]
            document = self.metadata.get(unit.document_id, {})
            sources.append(Source(alias, unit.document_id, str(document.get("title", "")),
                                  str(document.get("version", "")), str(document.get("status", "")),
                                  " › ".join(unit.section_path), unit.reading_text))
        text = "\n".join("- " + c["text"] + " [" + ", ".join(c["citation_ids"]) + "]" for c in claims)
        return Answer(
            status=report["status"], answered=answered, text=text, claims=claims,
            sources=tuple(sources), reservations=tuple(report.get("reservations") or ()),
            message=report.get("reason") or report.get("error_message") or "", model=model,
            input_tokens=usage["input_tokens"], output_tokens=usage["output_tokens"],
            cost_usd=cost, calls=usage["calls"], elapsed_seconds=report["elapsed_seconds"],
            report=report)
