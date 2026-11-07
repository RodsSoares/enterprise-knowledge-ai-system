"""Experimental stage-one coordinator with optional shared-budget live adapters.

Full canonical passages reach generation, never assessor-authored substitutes.
Character/deadline limits here are local test controls, not API token budgets.
"""
from dataclasses import asdict, dataclass
import json
from time import monotonic
from uuid import uuid4

from app.generation.answer_contract import StructuredAnswer, parse_answer, request_id_for, validate_answer
from app.orchestration.contracts import AssessmentContractError, AssessmentRequest, digest, parse_assessment, text
from app.retrieval.evidence_context import EvidenceContext, EvidencePassage, render_context


class BudgetExceeded(ValueError):
    pass


@dataclass(frozen=True)
class Stage1Limits:
    max_passages: int = 40
    max_request_characters: int = 64000
    max_context_characters: int = 32000
    deadline_seconds: float = 30

    def __post_init__(self):
        for value in (self.max_passages, self.max_request_characters, self.max_context_characters):
            if type(value) is not int or value < 1:
                raise ValueError("Limits must be positive integers")
        if (isinstance(self.deadline_seconds, bool) or
                not isinstance(self.deadline_seconds, (int, float)) or
                not 0 < self.deadline_seconds < float("inf")):
            raise ValueError("Finite positive deadline required")


@dataclass(frozen=True)
class Stage1Outcome:
    status: str
    answer: StructuredAnswer | None
    clarification: str | None
    error: str | None
    context: EvidenceContext
    trace_json: str
    semantic_review: str = "not_performed"

    def to_dict(self):
        return dict(status=self.status, answer=self.answer.to_dict() if self.answer else None,
            clarification=self.clarification, error=self.error,
            context=dict(text=self.context.text, citations=self.context.citations),
            trace=json.loads(self.trace_json), semantic_review=self.semantic_review)


class Stage1Coordinator:
    def __init__(self, *, chunks, retriever, assessor, generator, limits=None, clock=monotonic,
                 snapshot=None, allow_live=False, as_of=None):
        modes={getattr(c,"execution_mode",None) for c in (retriever,assessor,generator)}
        self.execution_mode="offline"
        if modes != {"offline"}:
            from app.orchestration.live_provider import BudgetedClient
            clients=[getattr(c,"budget_client",None) for c in (retriever,assessor,generator)]
            if (not allow_live or modes != {"budgeted_live"} or snapshot is None or as_of is None
                    or not isinstance(clients[0],BudgetedClient)
                    or any(c is not clients[0] for c in clients)):
                raise ValueError("Use offline providers or explicit shared-budget live adapters and snapshot")
            self.execution_mode="budgeted_live"
        self.as_of=as_of
        if as_of is not None:
            from datetime import date
            date.fromisoformat(as_of)
        self.metadata={}
        self.snapshot_scope="canonical_chunks_only"
        self.chunks = tuple(chunks)
        self.catalog = {c.chunk_id: c for c in self.chunks}
        if not self.chunks or len(self.catalog) != len(self.chunks):
            raise ValueError("Nonempty unique canonical catalog required")
        self.retriever, self.assessor, self.generator = retriever, assessor, generator
        self.limits, self.clock = limits or Stage1Limits(), clock
        # Honest scope: canonical catalog fingerprint, not full physical corpus manifest.
        self.snapshot_id = digest([dict(asdict(c), source_path=c.source_path.as_posix())
            for c in sorted(self.chunks, key=lambda c: c.chunk_id)])
        if snapshot is not None:
            snapshot.verify(self.chunks)
            self.snapshot_id=snapshot.snapshot_id
            self.metadata=snapshot.metadata
            self.snapshot_scope="physical_sources_registry_chunks_configuration"
        self.sections = {}
        for c in self.chunks:
            if c.section_path:
                sid = digest([c.document_id, c.section_path])
                self.sections.setdefault((c.document_id, sid), []).append(c)

    def _search(self, question):
        found, seen = [], set()
        for candidate in self.retriever.retrieve(question, top_k=20):
            chunk = candidate.chunk
            if self.catalog.get(chunk.chunk_id) != chunk:
                raise ValueError("Retriever returned noncanonical evidence")
            if chunk.chunk_id not in seen:
                found.append(chunk)
                seen.add(chunk.chunk_id)
        if len(found) > 20:
            raise ValueError("Retriever exceeded requested depth")
        return found

    def _request(self, run_id, question, chunks):
        if len(chunks) > self.limits.max_passages:
            raise BudgetExceeded("Assessment passage budget exceeded")
        documents = {c.document_id for c in chunks}
        sections = [dict(document_id=doc, section_id=sid, section_path=list(items[0].section_path))
            for (doc, sid), items in sorted(self.sections.items()) if doc in documents]
        passages = [dict(chunk_id=c.chunk_id, document_id=c.document_id,
            text=c.text, section_path=list(c.section_path),
            metadata=self.metadata.get(c.document_id), as_of=self.as_of) for c in chunks]
        request = AssessmentRequest.create(run_id=run_id, question=question,
            snapshot_id=self.snapshot_id, passages=passages, sections=sections)
        if len(request.serialized) > self.limits.max_request_characters:
            raise BudgetExceeded("Assessment character budget exceeded")
        return request

    def ask(self, question):
        text(question)
        started, trace = self.clock(), []
        run_id = uuid4().hex
        context = EvidenceContext((), (), (), "")

        def check_time():
            if self.clock() - started >= self.limits.deadline_seconds:
                raise BudgetExceeded("Deadline exceeded")

        def outcome(status, answer=None, clarification=None, error=None):
            envelope = dict(run_id=run_id, snapshot_id=self.snapshot_id,
                snapshot_scope=self.snapshot_scope, execution_mode=self.execution_mode,
                elapsed_seconds=self.clock()-started, events=trace)
            return Stage1Outcome(status, answer, clarification, error, context,
                json.dumps(envelope, ensure_ascii=False))

        def abstain(reason):
            answer = validate_answer(dict(request_id=request_id_for(question, context),
                status="abstained", claims=[], abstention_reason=reason),
                question=question, context=context)
            return outcome("abstained", answer=answer)

        try:
            check_time()
            chunks = self._search(question)
            trace.append(dict(stage="initial_search", chunk_ids=[c.chunk_id for c in chunks]))
            for attempt in range(2):
                check_time()
                request = self._request(run_id, question, chunks)
                trace.append(dict(stage="assessment_request", request=request.payload))
                raw = self.assessor.assess(request)
                check_time()
                assessment = parse_assessment(raw, request).payload
                trace.append(dict(stage="assessment", request=request.payload, result=assessment))
                decision = assessment["decision"]
                if decision == "clarify":
                    return outcome("clarification_required", clarification=assessment["clarification"])
                if decision == "abstain":
                    return abstain(assessment["reason"])
                if decision == "sufficient":
                    ids = {p["chunk_id"] for p in assessment["passage_decisions"]
                        if p["applicability"] in ("direct", "conditional")}
                    selected = [c for c in chunks if c.chunk_id in ids]
                    passages = tuple(EvidencePassage(f"E{i}", c, "assessed")
                        for i, c in enumerate(selected, 1))
                    context = EvidenceContext(passages, tuple(dict.fromkeys(c.document_id for c in selected)),
                        (), render_context(passages))
                    if len(context.text) > self.limits.max_context_characters:
                        raise BudgetExceeded("Generation context budget exceeded")
                    # Full source passages preserve conditional clauses; no summaries substituted.
                    check_time()
                    result = self.generator.generate(question, context)
                    check_time()
                    answer = parse_answer(result.raw, question=question, context=context)
                    trace.append(dict(stage="generation", model=result.model,
                        response_id=result.response_id, usage=result.usage,
                        request_id=answer.request_id))
                    return outcome(answer.status, answer=answer)
                if attempt == 1:
                    return abstain("Evidências insuficientes após a recuperação complementar permitida.")
                lookup = assessment["lookup"]
                check_time()
                if lookup["kind"] == "search":
                    extra = self._search(lookup["query"])
                else:
                    extra = []
                    for sid in lookup["section_ids"]:
                        extra.extend(sorted(self.sections[(lookup["document_id"], sid)], key=lambda c: c.order))
                # Atomic addition: no silently truncated section/table.
                by_id = {c.chunk_id: c for c in chunks}
                by_id.update((c.chunk_id, c) for c in extra)
                chunks = list(by_id.values())
                trace.append(dict(stage="complementary_lookup", lookup=lookup,
                    returned_chunk_ids=[c.chunk_id for c in extra]))
            raise RuntimeError("Unreachable transition")
        except BudgetExceeded as exc:
            return outcome("budget_exceeded", error=str(exc))
        except Exception as exc:
            # Avoid leaking provider exception text/secrets through user-facing output.
            trace.append(dict(stage="error", error_type=type(exc).__name__,
                contract_detail=str(exc) if isinstance(exc, AssessmentContractError) else None))
            return outcome("error", error=type(exc).__name__)
