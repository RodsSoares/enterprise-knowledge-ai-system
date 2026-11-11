# Architecture v3 — RV-039 / RV-040 / RV-041

Status: **proposed and partially prototyped, NOT promoted to production**.
Baseline: GitHub `main` at commit `822c943` (2026-11-11). The 871 passed / 4 warnings checkpoint reflects the last reported complete suite before this candidate, not the outcome of this package.

## Problem statement

Do not equate a powerful foundation model, correctly shaped JSON, and valid citations with a correct enterprise answer. Evidence can be (1) absent from the pool, (2) present but unselected, (3) selected but semantically irrelevant or incomplete, or (4) used incorrectly in generation.

Observed facts to preserve:
- RV-037 vector-only document FullEvidence@5 0.8286; default hybrid 0.7714; protected-vector-document-prefix-3 0.8571 across 35 positive questions. Q29 abstention was not part of these retrieval metrics. These are **document-level metrics**, not sufficient-span coverage or answer correctness.
- RV-038D2A: target DOC-005 exception **unit was verified** against original canonical snapshot, but BM25 recovered zero units on the model's Portuguese follow-up query. This is a lexical-only diagnostic, not a failure of the vector channel.
- Existing experimental `EvidenceAssurance` validates an assessor's *declared* evidence coverage and disallows unknown IDs; it **does not** independently establish global requirement completeness.
- `evidence_pipeline.py` currently calls planning then generation; `assurance_recovery.py` is an offline experiment, not in that path.
- `AssuranceRequest.create` limits `question` to 256 chars through `_id`; the planner/pipeline allow 4000. This mismatch must be fixed before integration.

## Work policy: three major, cohesive deliveries (no micro-patches)

### RV-039 — Retrieval & planning intelligence

1. Add an **optional** adaptive retriever with the same `search(query, document_ids, top_k)` interface. Preserve existing canonical units/snapshot and vector query. Permit a **separate lexical projection**, with a versioned controlled PT/EN glossary. Protect a bounded prefix of **vector units** before RRF; note this is NOT the RV-036 policy protecting distinct documents. Log source-channel ranks and selected IDs.
2. Perform an offline benchmark reusing *saved* RV-036 vector/lexical candidate traces; compare historical results with experimental unit-prefix policies. Evaluate the previously saved RV-038D2A lexical query against the verified DOC-005 unit. No LLM/embedding calls in this first pass.
3. Implement a **separate experimental v3 planning contract** with versioned instructions and explicit gaps; freeze the question-scope design. New planning must represent **unsupported requirements as gaps**, rather than requiring an invented support before an item can be declared.
4. Do not silently change production `EvidencePlanner`, `EvidenceUnitRetriever`, `evidence_pipeline.py`, or answer prompts. Only promote the candidate if the controlled comparison passes predetermined criteria.

Exit: versioned experimental retrieval code, deterministic tests, one offline report, retrieval regressions identified. In the next batch, run a fixed real embedding replay if the saved traces are insufficient for candidate-pool coverage measurement.

### RV-040 — Semantic assurance, recovery, generation

Single integrated **experimental** end-to-end pipeline with `baseline`/`v3` selection; baseline remains available.

- Scope: separate from evidence, question-only, immutable across recovery.
- Evidence plan: requirements + gap statuses + exact support quotes, no omission of identified mandatory facets to make a plan look complete.
- Assessment A: relevance/applicability of each requirement to the *question*.
- Assessment B: semantic entailment of each requirement by cited units.
- Assessment C: independent completeness of the requirement inventory relative to question and presented normative source (not only existing requirement IDs).
- `APPROVE` only after all three checks pass; JSON structural validation is a separate condition, not semantic confidence.
- Single authorized recovery with two explicit query projections: `semantic_query` for vectors and `lexical_query` for BM25, plus bounded document scope. Search/replan cannot mix synthetic and canonical snapshots, forge sources or change question scope. Enforce old and new evidence text identity, IDs, and requirements conservation.
- Generation: traceable claims can reference **several** coverage IDs when a relation legitimately needs both; all cited sources must entail each claim; preserve actors, temporal conditions, conjunctions and exclusions. Do not treat every conditional as a universal obligation.
- Final verifier: validate claim entailment, missing material requirements, unsupported conditionality and citations. Fail closed on an operational error without misreporting it as abstention.
- Consolidated budget across scope, planning, assessment, one recovery, generation and verification; hard cap for API calls, tokens and cost; no unbounded retries.

Exit: opt-in v3 execution path + integration tests + 4 recorded development cases in one reproducible report. Do not claim production readiness or global semantic guarantees.

### RV-041 — Qualification and release decision

- Freeze source snapshot and model settings. Run 35 positive development questions + Q29 negative for retrieval qualification; qualify generation on reviewed examples including Q18/Q19/Q28/Q34 plus adversarial cases.
- Ablations, changing one axis at a time: baseline vs protected fusion; before/after bilingual lexical query; old vs independent completeness; old vs relational generation.
- Required metrics: document recall and passage recall, material-facet coverage, out-of-scope obligations, claim-level entailment, citation accuracy, condition correctness, appropriate abstention/clarification, token count, cost, latency and failure counts.
- Set test acceptance *before* observing reserved-case outputs: no new critical false approvals, no source/scope forgery, full structural regressions green, measurable advantage without unreviewed severe regressions. If a candidate fails, roll back only that feature.
- Publish architecture ADR, prompt and experiment versions, comparison, risk register, and GitHub checkpoint. Human review required before promoting new default.

## Component boundary / invariants

| Layer | Owned responsibility | Forbidden shortcut |
|---|---|---|
| Query scope | User intent and conditions from question | Deriving question conditions from source distractors |
| Retrieval | Candidate ranking and canonical provenance | Treating top-ranked document as a complete rule |
| Planning | Applicable requirements, explicit gaps | Fabricated evidence or silently dropped obligations |
| Assurance | Relevance, entailment, **inventory completeness** | Approving only because 100% of planner's items were cited |
| Recovery | One allowlisted lookup; same authorized snapshot | Mixing synthetic and real units |
| Generation | Evidence-bound explanatory synthesis | Copying irrelevant plan requirements as obligations |
| Verification | Claim support and material omissions | Treating valid citation IDs as semantic proof |

## Prompt modifications policy

Do not paste new prose over old prompts in production. Version instructions together with their schema/contract, hash and evaluation set. Compare identical model/input/snapshot; do not tune on holdout. Proposed v3 prompt goals:

- **SCOPE-v3**: read question only; extract action, direction, object, explicit conditions, unknown material conditions, exclusions and document reference. Do not answer or infer user conditions.
- **PLAN-v3**: map relevant source requirements to question; separate `required_supported`, `required_missing`, `out_of_scope`, `conditional_category`. Quote exact source text for supported items; never require a fake quote to record a gap.
- **ASSURANCE-v3**: run *independent* relevance, entailment and completeness checks. Candidate links are suggestions, not proof. Report missing dimensions and precise next action only if authorized.
- **RECOVERY-v3**: state minimal missing facet, propose a semantic query (original meaning) and a target-language lexical query; do not introduce source IDs or case-specific rules not present in authorized scope.
- **ANSWER-v3**: concise business answer with relationally supported claims; preserve all source conditions, explicit exceptions, negations and chronology. If essential evidence is missing, abstain with a specific limitation.
- **VERIFY-v3**: independently check claim-level entailment, unsupported conditions and material omissions against source units. Do not rubber-stamp planner output.

## Risks and controls

1. Protected **unit** prefix can lose different **documents**; compare, do not infer RV-037 gains transfer unchanged.
2. PT/EN glossary expansion can attract irrelevant sources; lexical-only and vector-only traces remain distinct and reversible.
3. Existing scope/planner statements may omit relevant facets; separate independent completeness review and evaluate adversarial omissions.
4. Additional LLM calls increase costs and model-to-model correlated mistakes; test quality uplift under a fixed cumulative budget.
5. Context length and source metadata are not themselves source authority; authority and temporal conflicts require explicit rules.
6. New experiments are not production integrations; baseline cannot be silently overwritten.

## Operator rhythm

One install step + targeted/whole regression + a saved replay report for RV-039A. Subsequent releases follow the same pattern. Every release has one checkpoint review and one selective Git commit; no dozens of tiny terminal changes.
