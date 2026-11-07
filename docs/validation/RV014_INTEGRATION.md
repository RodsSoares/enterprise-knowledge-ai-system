# RV-014 integration — 2026-11-06

Base: `055b0a8` on `main` (retrieval experiments through RV-013).
Integrated the previously prepared EvidenceContextBuilder, its two unit-test
modules, offline replay and decision guide. Regenerated the result from the
committed RV-008/010/011/013 inputs and frozen challenge B.

## Validation

- Targeted tests: **50 passed**.
- Available regression suite: **487 passed** on Python 3.12.14/Linux.
- Full suite attempted: collection blocked in eight Docling-dependent modules
  because Docling is not installed. Those modules alone were excluded from the
  regression run; no application stubs or test changes were used.
- This is not a reproduction of the Windows/Python 3.14 pinned environment.
  Test dependencies here include pytest 9.2.0, NumPy 2.5.4, PyYAML 6.0.3,
  openpyxl 3.1.5, python-pptx 1.0.2 and OpenAI 3.46.0.
- Replay: 25 cases, all anchor orders preserved, zero new model/API calls.
- B reference groups: 13/15 to 15/15; macro coverage 0.8750 to 1.0000.
- Context character volume increases 62%; coverage does not establish answer
  correctness. A/B are development cases, not independent validation.
- RV-013 remains MIXED_RESULTS_REVIEW_REQUIRED; its original recorded scores
  and latencies were audited without rerunning inference.

## Reproduce in the project environment

```powershell
python -m pytest tests/unit/test_evidence_context.py tests/unit/test_evidence_context_replay.py -q
python -m tests.smoke.smoke_evidence_context_replay --output docs/validation/RV014_CONTEXT_REPLAY_RESULTS_local.json
python -m pytest -q
```

The historical auto-generated project audit is retained as a historical
snapshot; it is not manually rewritten to claim a new full-suite result.

## Remaining boundary

This adds a reusable bounded-context component and an offline experiment.
It does not alter the default HybridRetriever, promote the lexical filter or
reranker, or implement generated answers. Next integration must preserve the
fusion pool before diversity selection and provide model-specific token
budgeting, structured answers, citation validation and abstention evaluation.
API/frontend and permission enforcement remain outstanding.
