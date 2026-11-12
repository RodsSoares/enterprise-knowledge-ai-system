"""Lean evidence pipeline: retrieve -> answer -> verify.

One optional bounded retrieval when the answer model declares a missing fact.
Canonical source IDs are checked in Python. Semantic verdicts are model
judgments, not proof of correctness. Earlier pipelines remain unchanged.

Version 2 changes, each motivated by a recorded failure:

* The models see short evidence aliases (E1, E2, ...) instead of 80-character
  unit hashes. Python maps them back to canonical unit IDs.
* The verification verdict is derived in Python from the per-claim checks.
  An inconsistent model verdict no longer aborts the run.
* A claim that fails verification is removed; the remaining verified claims
  are kept. The whole answer is withheld only when no claim survives.
* An answer the verifier considers incomplete is returned with an explicit
  reservation instead of being hidden (configurable).
* Document authority is presented as a labelled rank, because the registry
  scale (4 = highest) is the inverse of the scale written in the corpus
  (1 = highest).
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from time import perf_counter

VERSION = "rv044/lean-pipeline-2"
DEFAULT_TOP_K = 20
DOC_PATTERN = re.compile(r"\bDOC-\d{3,}\b", re.IGNORECASE)
ALIAS_PATTERN = re.compile(r"^E[1-9]\d{0,2}$")
CLAIM_CHECKS = ("entailed", "relevant", "conditions_preserved")
# Registry authority_level -> label shown to the models (1 is the highest rank).
AUTHORITY_LABELS = {
    4: "rank 1 of 4 (highest): corporate policy",
    3: "rank 2 of 4: standard",
    2: "rank 3 of 4: SOP or governance record",
    1: "rank 4 of 4 (lowest): guideline, reference or operational record",
}
INCOMPLETE_MODES = ("flag", "withhold")
RELEVANCE = ("direct", "conditional", "background", "irrelevant")
LANGUAGE_NAMES = {"pt": "português do Brasil", "en": "English", "es": "español"}
USABLE = ("direct", "conditional")
_WORDS = re.compile(r"[a-zà-ÿ]+")
# Words that separate the three languages; words shared by two of them
# ("que", "para", "de", "una") are deliberately left out.
_STOPWORDS = {
    "pt": frozenset("não com dos das pelo pela pelos pelas são é ou em ao aos os as do da na nos "
                    "nas e à às só também mas quais qual quem posso podemos houve existe existem "
                    "alguma algum foi ainda sobre quero deve devem pode podem uma um".split()),
    "en": frozenset("the and of to is are for with must may be only when which what who how "
                    "not or if in by an".split()),
    "es": frozenset("el los las del y con es son en al lo también pero sólo solo según cuáles "
                    "cuál quién puedo hay debe deben puede pueden está están un".split()),
}
_MARKS = {"pt": frozenset("ãõçêôâ"), "es": frozenset("ñ¿¡")}


class LeanContractError(ValueError):
    pass


def _hash(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _object(raw, fields):
    if not isinstance(raw, str) or len(raw) > 100_000:
        raise LeanContractError("Invalid JSON response length")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise LeanContractError("Duplicate JSON key")
            result[key] = value
        return result

    def nonfinite(_value):
        raise LeanContractError("Nonfinite JSON constant")

    try:
        data = json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)
    except LeanContractError:
        raise
    except (ValueError, TypeError, RecursionError) as exc:
        raise LeanContractError("Invalid JSON response") from exc
    if not isinstance(data, dict) or set(data) != set(fields):
        raise LeanContractError("Unexpected response fields")
    return data


def _text(value, *, limit=1800, allow_empty=False):
    if not isinstance(value, str) or len(value) > limit or (not allow_empty and not value.strip()):
        raise LeanContractError("Invalid text")
    return value


def detect_language(text, *, minimum=3):
    """'pt', 'en', 'es' or None when the text is too short or mixed to tell.

    Counts function words and language-specific letters. `minimum` is the
    evidence required: 3 for an answer, 1 for a short question.
    """
    lowered = text.lower()
    tokens = _WORDS.findall(lowered)
    counts = sorted(((sum(token in words for token in tokens)
                      + sum(lowered.count(mark) for mark in _MARKS.get(code, ())), code)
                     for code, words in _STOPWORDS.items()), reverse=True)
    (best, code), (second, _) = counts[0], counts[1]
    if best < minimum or best < 1.5 * second:
        return None
    return code


def assemble_evidence(found, catalog_units, *, expand_documents, max_units):
    """Order retrieved units by document and complete the best documents.

    Retrieval works on small units, so a decisive section of the right document
    can rank just below the cut-off. For the `expand_documents` best-ranked
    documents every searchable ready unit is included, plus title units, which
    are not indexed but give list items their context (a slide title above its
    bullets). Other documents keep only their retrieved units. Units are
    grouped by document, best document first, in source order. Deterministic;
    no model call.
    """
    order = {unit.unit_id: index for index, unit in enumerate(catalog_units)}
    scores, first = {}, {}
    for rank, unit in enumerate(found, 1):
        scores[unit.document_id] = scores.get(unit.document_id, 0.0) + 1.0 / (60 + rank)
        first.setdefault(unit.document_id, rank)
    documents = sorted(scores, key=lambda doc: (-scores[doc], first[doc]))
    complete = set(documents[:expand_documents])
    retrieved = {unit.unit_id for unit in found}
    selected = []
    for document in documents:
        units = [u for u in catalog_units if u.document_id == document
                 and (u.unit_id in retrieved
                      or (document in complete and u.status == "ready"
                          and (u.searchable or getattr(u, "structural_role", None) == "title")))]
        selected.extend(sorted(units, key=lambda u: order[u.unit_id]))
    return tuple(selected[:max_units])


def describe_document(metadata):
    """Compact, unambiguous document header for the models."""
    if not metadata:
        return {}
    described = {key: metadata[key] for key in (
        "title", "document_type", "version", "effective_date", "status",
        "supersedes", "superseded_by", "as_of") if metadata.get(key) is not None}
    level = metadata.get("authority_level")
    if level in AUTHORITY_LABELS:
        described["authority"] = AUTHORITY_LABELS[level]
    return described


def evidence_aliases(candidates):
    """Stable alias for every candidate, in retrieval order."""
    return {"E" + str(index): unit for index, unit in enumerate(candidates, 1)}


def _evidence(aliases, metadata, only=None):
    """Evidence items and the header of each document, stated once.

    Repeating the document header inside every passage was about a third of
    the request. `only` restricts the items to a set of aliases.
    """
    items = [{"id": alias, "document_id": unit.document_id,
              "section": " › ".join(unit.section_path), "text": unit.reading_text}
             for alias, unit in aliases.items() if only is None or alias in only]
    documents = {doc: describe_document(metadata.get(doc))
                 for doc in dict.fromkeys(item["document_id"] for item in items)}
    return items, documents


def review_scope(answer):
    """Aliases the verifier needs: what the answer cites, plus every passage
    the answer model itself judged direct or conditional. Passages it judged
    background or irrelevant are left out to keep the second call small."""
    cited = {uid for claim in answer["claims"] for uid in claim["citation_ids"]}
    return cited | {alias for alias, label in answer["evidence_use"].items() if label in USABLE}


def validate_decision(raw, aliases, *, can_retrieve):
    """Validate the answer stage. Citations must be aliases of presented evidence.

    Harmless inconsistencies are normalized instead of aborting the run: an
    answer without claims becomes an abstention, and claims or a recovery
    query attached to a decision that cannot use them are dropped.
    """
    value = _object(raw, ("evidence_use", "decision", "claims", "recovery_query", "message"))
    decision = value["decision"]
    if decision not in ("answer", "retrieve", "clarify", "abstain"):
        raise LeanContractError("Invalid decision")
    if not isinstance(value["claims"], list) or len(value["claims"]) > 24:
        raise LeanContractError("Invalid claims")
    if not isinstance(value["evidence_use"], list):
        raise LeanContractError("Invalid evidence use")
    use = {}
    for row in value["evidence_use"]:
        if (not isinstance(row, dict) or set(row) != {"id", "relevance"}
                or row["relevance"] not in RELEVANCE):
            raise LeanContractError("Invalid evidence use entry")
        if row["id"] in aliases:
            use.setdefault(row["id"], row["relevance"])
    value["evidence_use"] = use
    value["uncited_claims_removed"] = 0
    if not isinstance(value["message"], str):
        raise LeanContractError("Invalid text")
    if decision == "answer" and not value["claims"]:
        decision = value["decision"] = "abstain"
        value["message"] = value["message"].strip() or "O modelo não produziu afirmações sustentadas pelas evidências."
    if decision == "answer":
        for row in value["claims"]:
            if not isinstance(row, dict) or set(row) != {"text", "citation_ids"}:
                raise LeanContractError("Invalid claim fields")
            _text(row["text"])
            ids = row["citation_ids"]
            if not isinstance(ids, list) or any(not isinstance(uid, str) for uid in ids):
                raise LeanContractError("Invalid citation list")
            # Unknown or repeated ids are removed; they can never become sources.
            row["citation_ids"] = list(dict.fromkeys(uid for uid in ids if uid in aliases))[:12]
        uncited = sum(not row["citation_ids"] for row in value["claims"])
        value["claims"] = [row for row in value["claims"] if row["citation_ids"]]
        value["uncited_claims_removed"] = uncited
        if not value["claims"]:
            raise LeanContractError("No claim cites presented evidence")
    else:
        value["claims"] = []
    if decision == "retrieve":
        if not can_retrieve:
            raise LeanContractError("Repeated recovery forbidden")
        _text(value["recovery_query"], limit=600)
    else:
        value["recovery_query"] = None
    _text(value["message"], limit=1200, allow_empty=(decision == "answer"))
    return value


def validate_review(raw, answer):
    """Validate the verification stage and derive the verdict in Python.

    Returns the model's checks plus `passed_claims` (indexes of claims that
    passed every check) and `verdict`. The model's own `decision` is kept for
    audit only: PASS requires every claim to pass and material completeness.
    A claim the verifier did not check, or checked twice, is treated as not
    verified; a miscounted list does not abort the run.
    """
    value = _object(raw, ("decision", "claim_checks", "materially_complete", "reason"))
    if value["decision"] not in ("PASS", "REJECT"):
        raise LeanContractError("Unknown verification verdict")
    if type(value["materially_complete"]) is not bool:
        raise LeanContractError("Invalid completeness")
    _text(value["reason"], limit=1200)
    checks = value["claim_checks"]
    total = len(answer["claims"])
    if not isinstance(checks, list):
        raise LeanContractError("Invalid claim checks")
    verdicts = {}
    for check in checks:
        if not isinstance(check, dict) or set(check) != {"claim_index", *CLAIM_CHECKS}:
            raise LeanContractError("Unexpected claim check")
        if any(type(check[key]) is not bool for key in CLAIM_CHECKS):
            raise LeanContractError("Invalid verifier boolean")
        index = check["claim_index"]
        if type(index) is not int or not 0 <= index < total:
            continue
        # A duplicated index passes only if every copy passes.
        verdicts[index] = verdicts.get(index, True) and all(check[key] for key in CLAIM_CHECKS)
    passed = sorted(index for index, ok in verdicts.items() if ok)
    unchecked = total - len(verdicts)
    verdict = "PASS" if len(passed) == total and value["materially_complete"] else "REJECT"
    return {**value, "passed_claims": passed, "unchecked_claims": unchecked, "verdict": verdict,
            "model_verdict_consistent": value["decision"] == verdict}


def render_answer(claims, aliases, metadata):
    """Verified claims followed by the sources they cite."""
    lines = ["- " + claim["text"] + " [" + ", ".join(claim["citation_ids"]) + "]"
             for claim in claims]
    cited = list(dict.fromkeys(uid for claim in claims for uid in claim["citation_ids"]))
    lines.append("")
    lines.append("Fontes:")
    for alias in cited:
        unit = aliases[alias]
        document = metadata.get(unit.document_id, {})
        label = unit.document_id
        if document.get("title"):
            label += " — " + str(document["title"])
        if document.get("version"):
            label += " v" + str(document["version"])
        if document.get("status"):
            label += " (" + str(document["status"]) + ")"
        if unit.section_path:
            label += " › " + " › ".join(unit.section_path)
        lines.append("[" + alias + "] " + label)
    return "\n".join(lines)


def run_lean(question, *, snapshot_id, units, retriever, provider,
             document_metadata=None, top_k=DEFAULT_TOP_K, max_units=60, max_request_chars=65000,
             on_incomplete="flag", expand_documents=3, checkpoint=None):
    """Protocol-based dependency injection enables deterministic offline testing.

    retriever.search(question, document_ids, top_k) -> (canonical units, trace)
    provider.invoke(stage, payload) -> strict JSON string, stages 'answer'/'verify'.
    All live API calls must share a single BudgetedClient (enforced by CLI).

    on_incomplete: 'flag' returns verified claims with an explicit reservation
    when the verifier reports a material omission; 'withhold' hides the answer.
    expand_documents: number of best-ranked documents sent in full (0 disables).
    """
    if (not isinstance(question, str) or not question.strip() or len(question) > 4000
            or not isinstance(snapshot_id, str) or not snapshot_id
            or type(top_k) is not int or not 1 <= top_k <= 30
            or type(max_units) is not int or not top_k <= max_units <= 80
            or type(expand_documents) is not int or not 0 <= expand_documents <= 6
            or type(max_request_chars) is not int or not 1000 <= max_request_chars <= 128000
            or on_incomplete not in INCOMPLETE_MODES):
        raise ValueError("Invalid lean pipeline inputs")
    if not callable(getattr(retriever, "search", None)) or not callable(getattr(provider, "invoke", None)):
        raise ValueError("Explicit retriever and provider required")
    catalog_units = tuple(units)
    catalog = {u.unit_id: u for u in catalog_units}
    if not catalog_units or len(catalog) != len(catalog_units):
        raise ValueError("Canonical catalog must have unique evidence unit IDs")
    docs = {u.document_id for u in catalog_units}
    metadata = document_metadata or {}
    if not isinstance(metadata, dict) or set(metadata) - docs:
        raise ValueError("Unknown document metadata keys")
    required_docs = tuple(sorted(set(m.upper() for m in DOC_PATTERN.findall(question))))
    question_language = detect_language(question, minimum=1)
    answer_language = LANGUAGE_NAMES.get(question_language, "the language of the question")
    started = perf_counter()
    report = {"version": VERSION, "status": "running", "question": question,
              "snapshot_id": snapshot_id, "document_scope": list(required_docs),
              "answer": None, "review": None, "rendered_answer": None,
              "reservations": [], "diagnostics": [], "evidence_ids": {},
              "recovery_used": False, "language_repair_used": False,
              "trace": [], "elapsed_seconds": None,
              "semantic_quality": "not_independently_established"}

    def event(name, **details):
        report["trace"].append({"stage": name, **details})
        report["elapsed_seconds"] = round(perf_counter() - started, 4)
        if checkpoint is not None:
            checkpoint(report)

    def invoke(stage, payload):
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        if len(encoded) > max_request_chars:
            raise LeanContractError("Request exceeds bounded context")
        event("request_" + stage, payload_hash=_hash(payload), chars=len(encoded))
        raw = provider.invoke(stage, payload)
        if not isinstance(raw, str):
            raise LeanContractError("Provider must return strict JSON text")
        return raw

    def canonical_candidates(found, scope):
        if not isinstance(found, (tuple, list)) or len(found) > top_k:
            raise LeanContractError("Retriever exceeded candidate budget")
        ids = [u.unit_id for u in found]
        if len(ids) != len(set(ids)):
            raise LeanContractError("Duplicate retrieved units")
        for u in found:
            if (u.unit_id not in catalog or catalog[u.unit_id] != u
                    or not u.searchable or u.status != "ready"
                    or (scope and u.document_id not in scope)):
                raise LeanContractError("Foreign, unready or unauthorized source")
        return tuple(found)

    try:
        if set(required_docs) - docs:
            report.update(status="abstained", reason="Documento solicitado ausente do corpus canônico.")
            event("missing_requested_document", document_ids=list(required_docs))
            return report
        found, retrieval_trace = retriever.search(question, required_docs, top_k)
        retrieved = canonical_candidates(found, required_docs)
        candidates = assemble_evidence(retrieved, catalog_units,
                                       expand_documents=expand_documents, max_units=max_units)
        event("retrieval", retrieved_ids=[u.unit_id for u in retrieved],
              selected_ids=[u.unit_id for u in candidates], retrieval=retrieval_trace)
        if not candidates:
            report.update(status="abstained", reason="Nenhuma evidência autorizada recuperada.")
            return report
        for attempt in range(2):
            aliases = evidence_aliases(candidates)
            report["evidence_ids"] = {alias: unit.unit_id for alias, unit in aliases.items()}
            evidence, documents = _evidence(aliases, metadata)
            payload = {"question": question, "answer_language": answer_language,
                       "document_scope": list(required_docs),
                       "recovery_used": bool(attempt), "documents": documents,
                       "evidence": evidence}
            answer = validate_decision(invoke("answer", payload), aliases, can_retrieve=not attempt)
            event("answer_decision", attempt=attempt, decision=answer["decision"])
            written = detect_language(" ".join(
                [claim["text"] for claim in answer["claims"]] + [answer["message"]]))
            if (question_language and written and written != question_language
                    and answer["decision"] != "retrieve" and not report["language_repair_used"]):
                # One bounded repair: the same request, stating what went wrong.
                report["language_repair_used"] = True
                event("language_repair", written=written, expected=question_language)
                answer = validate_decision(invoke("answer", {
                    **payload, "previous_attempt_error":
                        "Your previous output was written in " + LANGUAGE_NAMES[written]
                        + ". Write every claim and the message in " + answer_language + "."}),
                    aliases, can_retrieve=False)
                event("answer_decision", attempt=attempt, decision=answer["decision"], repaired=True)
            if answer["decision"] == "retrieve":
                query = answer["recovery_query"]
                # The recovery query can change ranking, but never document permissions.
                additional, trace = retriever.search(query, required_docs, top_k)
                additional = canonical_candidates(additional, required_docs)
                existing = {u.unit_id for u in candidates}
                new = tuple(u for u in additional if u.unit_id not in existing)
                event("recovery", added_ids=[u.unit_id for u in new], retrieval=trace)
                report["recovery_used"] = True
                if not new:
                    report.update(status="abstained", reason="Recuperação não encontrou evidência adicional.")
                    return report
                # Existing aliases stay stable: new units are appended, never reordered.
                candidates += new[:max(0, max_units - len(candidates))]
                continue
            if answer["decision"] == "answer":
                # Deterministic gate on the model's own triage: an answer needs at
                # least one passage that directly addresses the question.
                use = answer["evidence_use"]
                if "direct" not in use.values():
                    event("no_direct_evidence", labels=sorted(set(use.values())))
                    report.update(status="abstained", reason=(
                        "Nenhuma evidência recuperada responde diretamente à pergunta. "
                        "Reformule a pergunta ou informe mais detalhes."))
                    return report
                if answer["uncited_claims_removed"]:
                    report["reservations"].append(
                        str(answer["uncited_claims_removed"]) + " afirmação(ões) removida(s) por não "
                        "citar nenhuma evidência apresentada.")
                grounded = [claim for claim in answer["claims"]
                            if any(use.get(uid) in USABLE for uid in claim["citation_ids"])]
                dropped = len(answer["claims"]) - len(grounded)
                if dropped:
                    report["reservations"].append(
                        str(dropped) + " afirmação(ões) removida(s) por citar apenas evidência "
                        "que o próprio modelo classificou como contexto.")
                    answer["claims"] = grounded
            if answer["decision"] in ("clarify", "abstain"):
                report.update(status="clarification_required" if answer["decision"] == "clarify"
                              else "abstained", reason=answer["message"])
                return report
            # A model does not get to approve itself: verify in a separate call.
            scoped, scoped_documents = _evidence(aliases, metadata, review_scope(answer))
            review = validate_review(invoke("verify", {
                "question": question, "document_scope": list(required_docs),
                "answer_language": answer_language,
                "answer": {"claims": answer["claims"]}, "documents": scoped_documents,
                "evidence": scoped}), answer)
            report["review"] = review
            event("verification", verdict=review["verdict"], passed_claims=review["passed_claims"],
                  model_verdict_consistent=review["model_verdict_consistent"])
            kept = [answer["claims"][index] for index in review["passed_claims"]]
            removed = len(answer["claims"]) - len(kept)
            if not kept:
                report.update(status="review_rejected", reason=review["reason"])
                return report
            if removed:
                report["reservations"].append(
                    str(removed) + " afirmação(ões) removida(s) por não passar na verificação.")
            if not review["materially_complete"]:
                if on_incomplete == "withhold":
                    report.update(status="review_rejected", reason=review["reason"])
                    return report
                report["reservations"].append("A verificação indicou possível omissão: " + review["reason"])
            # Deterministic signals, independent of the verifier's judgment.
            cited = {uid for claim in kept for uid in claim["citation_ids"]}
            unused = [alias for alias, label in answer["evidence_use"].items()
                      if label == "direct" and alias not in cited]
            if unused:
                # Audit signal only: models over-label passages as direct.
                report["diagnostics"].append(
                    "Evidência classificada como direta não usada na resposta: " + ", ".join(
                        alias + " (" + aliases[alias].document_id + ")" for alias in unused))
            written = detect_language(" ".join(claim["text"] for claim in kept))
            if question_language and written and written != question_language:
                report["reservations"].append("Resposta redigida em idioma diferente do da pergunta.")
            report["answer"] = {**answer, "claims": kept}
            report.update(
                status="answered_with_reservations" if report["reservations"]
                else "answered_pending_human_review",
                rendered_answer=render_answer(kept, aliases, metadata))
            return report
        report.update(status="abstained", reason="Limite de recuperação atingido.")
        return report
    except Exception as exc:
        report.update(status=("budget_exceeded" if type(exc).__name__ == "BudgetExceeded"
                              else "execution_failed"), error_type=type(exc).__name__,
                      error_message=str(exc)[:500], answer=None, rendered_answer=None)
        event("error", error_type=type(exc).__name__)
        return report
    finally:
        report["elapsed_seconds"] = round(perf_counter() - started, 4)
        if checkpoint is not None:
            checkpoint(report)
