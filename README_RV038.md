# RV-038 — Evidence Assurance structural boundary (experimental)

This is an additive, offline first increment for the existing `app/orchestration/` package. It provides an immutable request with question/snapshot/evidence fingerprints and a fail-closed validator for proposed requirement-level decisions.

## Scope

- **Implemented:** deterministic contract validation; request/assessment identity; authorized candidate IDs; requirement coverage accounting; one-search recovery budget; explicit `APPROVE`, `RETRIEVE_MORE`, `CLARIFY`, `ABSTAIN` decisions; tests.
- **Not implemented:** semantic requirement inference, LLM assessor, actual retrieval execution, source authority evaluation, citation entailment, final answer verification, CLI integration, runtime access control.
- Validating an `APPROVE` assessment **does not prove** the model was correct to mark a requirement supported. This is a structural boundary, not a semantic certification.
- Do not make golden expected document IDs, canonical facts or question IDs runtime inputs. They are reserved for independent evaluation.

## Install and test

Copy `app/orchestration/evidence_assurance.py` and `tests/unit/test_evidence_assurance.py` to matching project directories, preserving existing files. From the project root:

```powershell
python -m pytest tests/unit/test_evidence_assurance.py -q
python -m pytest -q
```

No API key needed, no external calls, no existing production flow changed. After passing tests, build an adapter to the existing evidence planner and evaluator as a separate increment. A search action must be executed only by the authorized deterministic coordinator, never by this validator.
