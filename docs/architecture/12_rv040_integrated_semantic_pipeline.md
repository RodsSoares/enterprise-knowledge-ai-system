# RV-040 — Integrated semantic evidence pipeline (experimental)

**Status:** opt-in experimental integration. Not production-ready, not a validated accuracy improvement.
**Source checkpoint:** `e6bb855` on `main` (2026-11-11).
**Baseline retained:** `app/orchestration/evidence_pipeline.py` and `app/scripts/ask_evidence.py` are unchanged.

## Intent

Deliver one cohesive implementation, not an accumulating chain of small LLM prompt patches.
Prevent a powerful model from being limited by bad information routing, repeated guesses
and circular self-approval. Retain deterministic source integrity and a single execution budget.

## Runtime stages

1. **scope_v3** — question only, using the prior frozen scope contract. It receives no sources or planned answers.
2. **Adaptive discovery** — opt-in RV-039 adaptive search: vector plus controlled PT/EN BM25. Returns a candidate pool bound to one canonical catalog.
3. **plan_v3** — RV-039A plan contract: supported/partial/missing/excluded facets with exact quote spans, no fabricated support for gaps.
4. **inventory_v3** — independent source inventory, **without the proposed plan**. Critical anti-anchoring experiment; semantic independence remains limited because the same model may run both stages.
5. **assurance_v3** — separate relevance, entailment and inventory completeness verdicts. `APPROVE` needs all material requirements supported, no declared omissions or unresolved audited facets, and a structurally complete plan.
6. **Recovery (optional)** — exactly one semantic embedding query and separately specified English (or source-language) BM25 query; explicit authorized document scope. Retains all original candidates, validates canonical unit equality, then replans and re-inventories. Conservation check prohibits silently dropping original in-scope requirement texts.
7. **generate_v3** — relational claims may use multiple requirement IDs only if authorized source IDs support each relationship. All relevant requirements must be covered.
8. **verify_v3** — independent critical review of each claim's support, relevance and conditions; also material completeness. A `REJECT` hides the generated answer and returns `review_rejected`.

Normal path: **6 model calls + 1 query embedding call = 7 API calls**.
Single-recovery path: **9 model calls + 2 query embeddings = 11 API calls**.
Actual calls may be fewer because of clarifications, retrieval misses, refusals and abstentions. Cost estimates require explicit operator-provided model pricing; the live CLI uses one existing `BudgetedClient` for model and query-embedding calls.

## Components

- `app/orchestration/v3_semantic_contracts.py`: response schemas, strict JSON parsing, inventory and decision checks.
- `app/orchestration/v3_pipeline.py`: deterministic transitions, snapshot scope, single recovery and safe exits.
- `app/orchestration/v3_live_provider.py`: versioned prompts and strict OpenAI Responses schemas, shared budget.
- `app/retrieval/v3_dual_query_retriever.py`: distinct query projections, explicit document scope, RV-039 fusion policy.
- `app/generation/v3_answer_contract.py`: relational claims and final verifier.
- `app/scripts/ask_evidence_v3.py`: dry-run by default, `--execute` only with explicit model pricing and API key.

## Demonstrated versus not yet demonstrated

**Validated offline by deterministic tests:** schema rejection, source provenance,
replanning conservation, one retrieval maximum, scope-only interpretation,
independent inventory input (no proposed plan), full claim coverage,
per-claim citation checks and `REJECT` withholding final answers.

**Not demonstrated:** greater factual correctness; better performance on untouched enterprise questions;
absence of correlated assessment errors; complete corpus-level rule inventory; policy authority or
version precedence; ACL/multi-tenant production safety; live comparative costs/latency;
meaningful lexical translation for all PT/EN vocabulary; or successful live end-to-end behavior.

The upstream v3 plan can omit a facet, and the inventory auditor only sees retrieved candidates.
If a material rule is absent from **all** candidates, both planner and inventory can miss it.
The independent inventory is model-proposed, not proven exhaustive. Keep `semantic_review = llm_assessed_not_independent_ground_truth` even after `PASS`.

## Risk policy and future qualification (RV-041)

- Freeze question, snapshot, model, pricing and prompt/schema hashes before comparative runs.
- Run baseline and v3 with the same setup on four existing development cases ORC-001..004; record **answer-level** evidence and latency, not only JSON validity.
- Compare retrieval vector-only, hybrid and RV-039 adaptive; collect lexical/vector traces per case.
- Run original 35 positive queries plus Q29 abstention to evaluate retrieval/decision separately.
- Then evaluate reserved or newly frozen questions; do not tune prompts using a reserved set.
- Require no new critical false approvals and no source/scope forgery. Track every unsupported rule, omitted material condition and cited but semantically irrelevant excerpt.
- Only promote features that show measurable improvement without severe regressions. Keep baseline path available indefinitely until a documented rollback policy exists.

## Working commands (PowerShell, repository root)

Full regression after installation:

```powershell
python -m pytest tests -q
```

Dry-run, zero API calls (use your project configuration and warm embeddings cache):

```powershell
python -m app.scripts.ask_evidence_v3 `
  --snapshot docs/validation/EVIDENCE_UNITS_SNAPSHOT_local.json `
  --embedding-cache docs/validation/EVIDENCE_UNIT_EMBEDDINGS_local.json `
  --config docs/validation/STAGE1_RUN_CONFIG_local.json `
  --question "Quais cuidados a política exige antes de compartilhar dados com um fornecedor externo?" `
  --output docs/validation/RV040_PREFLIGHT_local.json
```

Live execution requires an explicit, separate output filename, `--execute`,
`--input-price` and `--output-price`, a local `OPENAI_API_KEY`, and a budget.
Do not reuse stale pricing guesses for actual billing. Never publish keys or raw
enterprise documents. Existing synthetic demonstration data should not be confused
with source-policy authority or production quality certification.
