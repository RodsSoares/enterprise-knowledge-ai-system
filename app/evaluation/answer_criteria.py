"""Deterministic answer criteria for the lean pipeline.

Each case states the expected outcome, the documents an answer must cite, the
facts it must contain and the statements it must not make. Scoring uses only
string matching on the final answer, so a pass is reproducible and costs
nothing. It is a lower bound on quality: it proves that required facts and
sources are present, not that every sentence is correct. Human review of a
sample remains necessary.

Patterns are regular expressions matched against the answer after lowercasing
and removing accents, so write them lowercase and without accents.
"""
from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata

import yaml

DEFAULT_CRITERIA_PATH = Path("data/ground_truth/answer_criteria.yaml")
OUTCOMES = ("answer", "clarify", "abstain")
# Lean pipeline status -> outcome. A withheld answer is a safe non-answer.
STATUS_OUTCOME = {
    "answered_pending_human_review": "answer",
    "answered_with_reservations": "answer",
    "clarification_required": "clarify",
    "abstained": "abstain",
    "review_rejected": "abstain",
}
DOC_ID = re.compile(r"^DOC-\d{3,}$")


def normalize(text):
    """Lowercase and strip accents so patterns survive spelling variation."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


@dataclass(frozen=True)
class Pattern:
    name: str
    any_of: tuple[str, ...]

    def found(self, normalized_text):
        return any(re.search(expression, normalized_text) for expression in self.any_of)


@dataclass(frozen=True)
class Case:
    case_id: str
    question: str
    outcomes: tuple[str, ...]
    cite: tuple[tuple[str, ...], ...]
    forbidden_documents: tuple[str, ...]
    required_facts: tuple[Pattern, ...]
    forbidden: tuple[Pattern, ...]
    human_check: str
    note: str


def _patterns(rows, label):
    result = []
    for row in rows or ():
        if not isinstance(row, dict) or set(row) != {"name", "any"}:
            raise ValueError(f"{label}: each entry needs exactly name and any")
        expressions = tuple(row["any"]) if isinstance(row["any"], list) else ()
        if not isinstance(row["name"], str) or not row["name"].strip() or not expressions:
            raise ValueError(f"{label}: name and at least one pattern required")
        for expression in expressions:
            if not isinstance(expression, str) or expression != normalize(expression):
                raise ValueError(f"{label}: pattern must be lowercase without accents: {expression!r}")
            re.compile(expression)
        result.append(Pattern(row["name"], expressions))
    return tuple(result)


def load_criteria(path=DEFAULT_CRITERIA_PATH):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        raise ValueError("Criteria file needs a cases list")
    allowed = {"id", "question", "expected_outcome", "cite", "forbidden_documents",
               "required_facts", "forbidden", "human_check", "note"}
    cases = []
    for row in data["cases"]:
        if not isinstance(row, dict) or set(row) - allowed or not {"id", "question", "expected_outcome"} <= set(row):
            raise ValueError(f"Unexpected criteria fields: {row!r:.80}")
        label = row["id"]
        outcomes = row["expected_outcome"]
        outcomes = tuple(outcomes) if isinstance(outcomes, list) else (outcomes,)
        if not outcomes or any(o not in OUTCOMES for o in outcomes):
            raise ValueError(f"{label}: unknown expected outcome")
        cite = tuple(tuple(group) if isinstance(group, list) else (group,) for group in row.get("cite") or ())
        documents = [d for group in cite for d in group] + list(row.get("forbidden_documents") or ())
        if any(not isinstance(d, str) or not DOC_ID.match(d) for d in documents):
            raise ValueError(f"{label}: invalid document id")
        facts = _patterns(row.get("required_facts"), label)
        if "answer" not in outcomes and (cite or facts):
            raise ValueError(f"{label}: citations and facts require an answer outcome")
        cases.append(Case(label, row["question"], outcomes, cite,
                          tuple(row.get("forbidden_documents") or ()), facts,
                          _patterns(row.get("forbidden"), label),
                          row.get("human_check", ""), row.get("note", "")))
    ids = [c.case_id for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate case ids")
    return tuple(cases)


def cited_documents(result):
    """Document ids cited by the final claims of a lean pipeline result."""
    answer = result.get("answer") or {}
    aliases = result.get("evidence_ids") or {}
    cited = set()
    for claim in answer.get("claims", ()):
        for alias in claim["citation_ids"]:
            cited.add(aliases.get(alias, alias).split("::", 1)[0])
    return cited


def score(case, result):
    """Score one lean pipeline result against one case."""
    status = result.get("status")
    outcome = STATUS_OUTCOME.get(status, "error")
    failures = []
    if outcome not in case.outcomes:
        failures.append(f"outcome {outcome} ({status}); expected {' or '.join(case.outcomes)}")
    facts_found = []
    if outcome == "answer":
        cited = cited_documents(result)
        text = normalize(" ".join(claim["text"] for claim in result["answer"]["claims"]))
        for group in case.cite:
            if not cited & set(group):
                failures.append("no citation of " + " or ".join(group))
        for document in sorted(cited & set(case.forbidden_documents)):
            failures.append("cites out-of-scope " + document)
        for fact in case.required_facts:
            present = fact.found(text)
            facts_found.append(present)
            if not present:
                failures.append("missing fact: " + fact.name)
        for pattern in case.forbidden:
            if pattern.found(text):
                failures.append("forbidden statement: " + pattern.name)
    return {"case_id": case.case_id, "passed": not failures, "outcome": outcome,
            "status": status, "failures": failures,
            "facts_found": sum(facts_found), "facts_required": len(case.required_facts),
            "reservations": len(result.get("reservations") or ()),
            "human_check": case.human_check}


def summarize(scores):
    """Pass rate per case over repeated runs, and overall."""
    by_case = {}
    for item in scores:
        by_case.setdefault(item["case_id"], []).append(item)
    rows = []
    for case_id, runs in by_case.items():
        passed = sum(run["passed"] for run in runs)
        rows.append({"case_id": case_id, "runs": len(runs), "passed": passed,
                     "stable": passed in (0, len(runs)),
                     "outcomes": sorted({run["outcome"] for run in runs}),
                     "failures": sorted({f for run in runs for f in run["failures"]})})
    total = len(scores)
    return {"cases": len(rows), "runs": total,
            "runs_passed": sum(s["passed"] for s in scores),
            "cases_always_passed": sum(r["passed"] == r["runs"] for r in rows),
            "cases_never_passed": sum(r["passed"] == 0 for r in rows),
            "cases_unstable": sum(not r["stable"] for r in rows),
            "by_case": rows}
