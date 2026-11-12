"""Single entry point for asking the knowledge base a question.

Loads the verified evidence catalog and its embedding cache once, then answers
questions through the lean pipeline. A session can add its own documents,
which are read, embedded and searched in memory only.

Three cost ceilings apply to every paid call: per question, per session and per
day for the whole server process. Models listed as protected need an explicit
unlock. Prices come from the runtime configuration and must be checked against
current billing.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
from threading import Lock

from app.chunking.evidence_snapshot import verify_snapshot
from app.orchestration.lean_live_provider import LeanLiveProvider
from app.orchestration.lean_pipeline import run_lean
from app.orchestration.live_provider import BudgetedClient, RunBudget
from app.retrieval.adaptive_evidence_retriever import AdaptiveEvidenceUnitRetriever
from app.retrieval.evidence_unit_retriever import read_cache
from app.retrieval.openai_embeddings import OpenAIEmbeddingProvider
from app.service.upload_reader import UploadError, build_units

DEFAULT_RUNTIME_CONFIG = Path("config/lean_runtime.json")
REQUIRED = {"snapshot", "embedding_cache", "embedding_model", "default_model", "models",
            "embedding_price_per_million", "as_of", "top_k", "expand_documents",
            "max_cost_per_question_usd", "max_cost_per_session_usd", "max_cost_per_day_usd",
            "protected_models", "max_upload_files", "max_upload_mb", "max_upload_units",
            "repository_blob_url", "max_output_tokens_per_call", "deadline_seconds"}
ANSWERED = ("answered_pending_human_review", "answered_with_reservations")
SCOPES = ("corpus", "uploads", "all")
EMBED_BATCH = 64


class SessionBudgetExceeded(RuntimeError):
    pass


class DailyBudgetExceeded(RuntimeError):
    pass


class ModelLocked(PermissionError):
    pass


class DailyBudget:
    """Spending of the whole server process for the current day.

    Kept in memory: it resets when the process restarts, so it limits abuse of
    a public demo but is not an account-wide billing cap.
    """

    def __init__(self):
        self._lock = Lock()
        self._day = date.today()
        self._spent = Decimal(0)

    def remaining(self, ceiling):
        with self._lock:
            if date.today() != self._day:
                self._day, self._spent = date.today(), Decimal(0)
            return Decimal(str(ceiling)) - self._spent

    def add(self, cost):
        with self._lock:
            if date.today() != self._day:
                self._day, self._spent = date.today(), Decimal(0)
            self._spent += cost


DAILY_BUDGET = DailyBudget()


@dataclass(frozen=True)
class Source:
    alias: str
    document_id: str
    title: str
    version: str
    status: str
    section: str
    text: str
    source_path: str  # repository path of a corpus document; empty for an upload


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
    scope: str
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal
    calls: int
    elapsed_seconds: float
    report: dict


@dataclass(frozen=True)
class Upload:
    document_id: str
    name: str
    units: tuple
    vectors: tuple
    revision: str


def load_runtime_config(path=DEFAULT_RUNTIME_CONFIG):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    if set(config) != REQUIRED:
        raise ValueError("Runtime config fields differ from the expected set")
    if config["default_model"] not in config["models"]:
        raise ValueError("Default model must be one of the configured models")
    if config["default_model"] in config["protected_models"]:
        raise ValueError("The default model cannot be a protected model")
    if set(config["protected_models"]) - set(config["models"]):
        raise ValueError("Protected models must be configured models")
    for name, model in config["models"].items():
        if not {"label", "input_per_million", "output_per_million"} <= set(model):
            raise ValueError("Model needs label and prices: " + name)
    for key in ("max_cost_per_question_usd", "max_cost_per_session_usd", "max_cost_per_day_usd"):
        if not Decimal(str(config[key])) > 0:
            raise ValueError("Positive cost ceilings required")
    for key in ("max_upload_files", "max_upload_mb", "max_upload_units"):
        if type(config[key]) is not int or config[key] < 1:
            raise ValueError("Positive upload limits required")
    return config


class KnowledgeService:
    def __init__(self, sdk, config=None, *, root=None, daily_budget=None):
        """sdk: an OpenAI client (or a test double with the same interface)."""
        self.sdk = sdk
        self.config = config or load_runtime_config()
        self.daily = daily_budget or DAILY_BUDGET
        self.root = Path(root) if root is not None else Path.cwd()
        snapshot = json.loads((self.root / self.config["snapshot"]).read_text(encoding="utf-8"))
        self.units = verify_snapshot(snapshot, root=self.root)
        cache = json.loads((self.root / self.config["embedding_cache"]).read_text(encoding="utf-8"))
        self.vectors = read_cache(cache, self.units, self.config["embedding_model"])
        self.snapshot_id = snapshot["snapshot_id"]
        self.metadata = {d["document_id"]: {**d["metadata"], "as_of": self.config["as_of"]}
                         for d in snapshot["snapshot"]["documents"]}
        self.source_paths = {d["document_id"]: d["source_path"]
                             for d in snapshot["snapshot"]["documents"]}
        self.uploads = {}
        self.upload_counter = 0
        self.query_cache = {}
        self.session_cost = Decimal(0)
        self.questions = 0

    @property
    def documents(self):
        return len(self.metadata)

    @property
    def session_remaining(self):
        return Decimal(str(self.config["max_cost_per_session_usd"])) - self.session_cost

    def is_protected(self, model):
        return model in self.config["protected_models"]

    def prices(self, model=None):
        prices = {self.config["embedding_model"]: {
            "input_per_million": self.config["embedding_price_per_million"],
            "output_per_million": "0"}}
        if model is not None:
            chosen = self.config["models"][model]
            prices[model] = {"input_per_million": chosen["input_per_million"],
                             "output_per_million": chosen["output_per_million"]}
        return prices

    def _ceiling(self):
        """Smallest of the question, session and daily allowances still available."""
        if self.session_remaining <= 0:
            raise SessionBudgetExceeded("Session cost ceiling reached")
        daily = self.daily.remaining(self.config["max_cost_per_day_usd"])
        if daily <= 0:
            raise DailyBudgetExceeded("Daily cost ceiling of the demo reached")
        return min(Decimal(str(self.config["max_cost_per_question_usd"])), self.session_remaining, daily)

    def _charge(self, client):
        cost = Decimal(client.report()["estimated_cost_usd"])
        self.session_cost += cost
        self.daily.add(cost)
        return cost

    def add_upload(self, name, data):
        """Read, embed and keep one user document for this session only."""
        if len(self.uploads) >= self.config["max_upload_files"]:
            raise UploadError(f"Limite de {self.config['max_upload_files']} documentos por sessão.")
        if len(data) > self.config["max_upload_mb"] * 1024 * 1024:
            raise UploadError(f"Arquivo maior que {self.config['max_upload_mb']} MB.")
        self.upload_counter += 1
        document_id = f"UP-{self.upload_counter:02d}"
        units = build_units(document_id, name, data)
        if any(upload.revision == units[0].source_revision for upload in self.uploads.values()):
            raise UploadError("Este arquivo já foi enviado nesta sessão.")
        total = sum(len(upload.units) for upload in self.uploads.values()) + len(units)
        if total > self.config["max_upload_units"]:
            raise UploadError("Documento grande demais para esta demonstração "
                              f"(limite de {self.config['max_upload_units']} trechos por sessão).")
        calls = -(-len(units) // EMBED_BATCH)
        client = BudgetedClient(self.sdk, RunBudget(2_000_000, 1, calls,
                                                    self.config["deadline_seconds"], str(self._ceiling())),
                                self.prices(), transport_retries=2)
        provider = OpenAIEmbeddingProvider(client, model=self.config["embedding_model"])
        vectors = []
        try:
            for start in range(0, len(units), EMBED_BATCH):
                vectors.extend(provider.embed_documents(
                    tuple(unit.search_text for unit in units[start:start + EMBED_BATCH])))
        finally:
            self._charge(client)
        upload = Upload(document_id, name, units, tuple(vectors), units[0].source_revision)
        self.uploads[document_id] = upload
        return upload

    def remove_upload(self, document_id):
        self.uploads.pop(document_id, None)

    def _collection(self, scope):
        """Units, their vectors and document metadata for a search scope."""
        units, vectors, metadata = [], [], {}
        if scope in ("corpus", "all"):
            units += list(self.units)
            vectors += list(self.vectors)
            metadata.update(self.metadata)
        if scope in ("uploads", "all"):
            for upload in self.uploads.values():
                units += list(upload.units)
                vectors += list(upload.vectors)
                metadata[upload.document_id] = {"title": upload.name, "status": "uploaded",
                                                "document_type": "user_upload"}
        return tuple(units), vectors, metadata

    def ask(self, question, *, model=None, scope="corpus", unlocked=False):
        model = model or self.config["default_model"]
        if model not in self.config["models"]:
            raise ValueError("Unknown model: " + str(model))
        if self.is_protected(model) and unlocked is not True:
            raise ModelLocked("Model requires the access password: " + model)
        if scope not in SCOPES:
            raise ValueError("Unknown scope: " + str(scope))
        if not isinstance(question, str) or not question.strip() or len(question) > 4000:
            raise ValueError("Question must contain 1-4000 characters")
        units, vectors, metadata = self._collection(scope)
        if not units:
            raise ValueError("Nenhum documento disponível para a fonte selecionada.")
        budget = RunBudget(120000, 20000, 6, self.config["deadline_seconds"], str(self._ceiling()))
        client = BudgetedClient(self.sdk, budget, self.prices(model), transport_retries=2)
        retriever = AdaptiveEvidenceUnitRetriever(
            units, vectors, OpenAIEmbeddingProvider(client, model=self.config["embedding_model"]))
        retriever.query_cache = self.query_cache
        try:
            report = run_lean(
                question.strip(), snapshot_id=self.snapshot_id, units=units, retriever=retriever,
                provider=LeanLiveProvider(client, model, self.config["max_output_tokens_per_call"]),
                document_metadata=metadata, top_k=self.config["top_k"],
                expand_documents=self.config["expand_documents"])
        finally:
            cost = self._charge(client)
        self.questions += 1
        return self._answer(report, model, scope, client.report(), cost,
                            {unit.unit_id: unit for unit in units}, metadata)

    def _answer(self, report, model, scope, usage, cost, catalog, metadata):
        answered = report["status"] in ANSWERED
        claims = tuple(report["answer"]["claims"]) if answered else ()
        sources = []
        for alias in dict.fromkeys(uid for claim in claims for uid in claim["citation_ids"]):
            unit = catalog[report["evidence_ids"][alias]]
            document = metadata.get(unit.document_id, {})
            sources.append(Source(alias, unit.document_id, str(document.get("title", "")),
                                  str(document.get("version", "")), str(document.get("status", "")),
                                  " › ".join(unit.section_path), unit.reading_text,
                                  self.source_paths.get(unit.document_id, "")))
        text = "\n".join("- " + c["text"] + " [" + ", ".join(c["citation_ids"]) + "]" for c in claims)
        return Answer(
            status=report["status"], answered=answered, text=text, claims=claims,
            sources=tuple(sources), reservations=tuple(report.get("reservations") or ()),
            message=report.get("reason") or report.get("error_message") or "", model=model,
            scope=scope, input_tokens=usage["input_tokens"], output_tokens=usage["output_tokens"],
            cost_usd=cost, calls=usage["calls"], elapsed_seconds=report["elapsed_seconds"],
            report=report)

    def source_file(self, source_path):
        """Bytes of a corpus document cited by an answer; only catalog paths are served."""
        if source_path not in self.source_paths.values():
            raise ValueError("Unknown source document")
        return (self.root / source_path).read_bytes()
