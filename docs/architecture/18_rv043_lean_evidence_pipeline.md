# RV-043 — Lean Evidence Pipeline (comparison candidate)

**Status:** opt-in experimental candidate. Not certified as more accurate, complete or cost-effective. No existing pipeline is changed or deleted.

## Motivation and scope

The RV-040/RV-042 branch split question interpretation, planning, independent inventory, relevance labeling, assurance, frozen replanning, generation and verification across many model calls and incompatible intermediate semantic contracts. In RV-041, a large structural regression suite did not prevent runtime contract failures or scope expansion. This is a **new, smaller comparison candidate**, not an additional gate in that old chain.

The older version remains available for audit/rollback. Deleting it before a controlled comparison would hide possible regressions and erase experimentally useful evidence.

## New runtime (only two semantic model tasks)

1. **Retrieval:** reuse the verified physical source snapshot, warm document-embedding cache, and the existing RV-039 adaptive hybrid retriever. Programmatic `DOC-NNN` restrictions from the question are retained, including during recovery.
2. **Answer:** one structured model call decides among `answer`, `retrieve`, `clarify`, `abstain`. For a general question, category-specific rules may be explained conditionally without guessing the user's circumstances. Neighboring unrelated processes should not become mandatory requirements.
3. **Optional retrieval:** at most one additional query in the same document scope; append only canonical new units and request a final structured answer. No second recovery.
4. **Verify:** one independent review call checks every cited claim for entailment, relevance, conditional integrity and material completeness. The verifier cannot add citation IDs. REJECT withholds the answer. Even a PASS is marked `answered_pending_human_review`, not proven truth.

**API call upper bounds:** normal: 1 embedding + 1 answer model + 1 verification model = **3**; single recovery: 2 embedding + 2 answer model + 1 verification model = **5**. These maxima assume cache misses for each distinct query and a completed answer; early exits take fewer calls.

## Code and responsibility map

| File | Responsibility |
|---|---|
| `app/orchestration/lean_pipeline.py` | Single state machine; bounded retrieval; strict JSON validation; citation scope, one recovery, review gating |
| `app/orchestration/lean_live_provider.py` | Only two prompts, JSON Schemas and shared `BudgetedClient` adapter |
| `app/scripts/ask_evidence_lean.py` | Canonical preflight; existing config; optional paid run; checkpointed JSON result |
| `tests/unit/test_lean_pipeline.py` | Deterministic runtime contract regression checks; no API calls |

Existing ingestion, chunking, embedding, retrieval, physical source hashing, API budgeting and replay datasets are deliberately reused, **not rewritten**.

## Nonnegotiable boundaries

- Canonical source membership and exact unit equality validated before any model call.
- Model citations must refer to retrieved, ready, searchable, authorized unit IDs.
- Explicit document references remain in scope; missing named documents fail safely.
- At most one recovery; maximum candidate and payload bounds; one shared API budget.
- The model's assessment is *not* corpus-level evidence completeness proof.
- Strict JSON with duplicate-key rejection; no model tool execution; no retries.
- Absent evidence, unsupported reference, missing review or review rejection never produces a user-visible answer.
- Physical-source integrity and cached embeddings verified in CLI preflight before execution.
- Configured operator rates; `--execute --confirm-paid` required for paid execution; dry-run by default; output files never overwritten.
- Authority and document lifecycle are **not fully solved** by this release. Metadata is provided to the model and must be independently evaluated in a holdout; no production ACL guarantee.

## Qualification gate before considering retirement of old paths

Re-run the **existing frozen ORC-001..ORC-004 cases** and separate Q29 abstention against the same snapshot and model. Compare to previously saved baseline responses without repaying for them. Human scoring must judge:

1. Claims actually entailed by each cited passage.
2. Scope adherence (especially the ORC-001 generic-sharing vs adjacent AI requirements).
3. Conditions/negations/exceptions preserved; completeness without invented policy.
4. Correct abstention for Q29; no material false permission.
5. API calls, estimated USD and elapsed seconds **per successfully useful answer**, not per completed JSON.

Only if the lean branch succeeds on the frozen cohort and then a reserved holdout should we refactor the active entrypoint, archive superseded scripts and remove dead code. Don't turn this into another 4+ hotfix series: any failed integration should first become a single offline regression diagnosis.

## Dry-run (zero API)

```powershell
python -m app.scripts.ask_evidence_lean `
  --case-id ORC-001 `
  --output docs/validation/RV043_PREFLIGHT_local.json
```

## Paid, single-case smoke ONLY AFTER REVIEWING PREFLIGHT AND COST

The project config currently defaults to `gpt-4.1-mini-2025-04-14`. To compare on the historical `gpt-6.1-sol`, prices must be explicitly supplied by the operator and checked against current billing; this example is not a recommendation to execute immediately:

```powershell
python -m app.scripts.ask_evidence_lean `
  --case-id ORC-001 `
  --model 'gpt-6.1-sol' `
  --input-price 'YOUR_INPUT_RATE' --output-price 'YOUR_OUTPUT_RATE' `
  --max-cost-usd '0.40' `
  --output docs/validation/RV043_ORC001_LIVE_local.json `
  --execute --confirm-paid
```

This does NOT automatically run all four tests, doesn't overwrite old experiments and doesn't publish source material or logs. Never commit raw model usage reports or API keys.
