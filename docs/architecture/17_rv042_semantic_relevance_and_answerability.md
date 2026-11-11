# RV-042 — Semantic Relevance & Answerability (opt-in, experimental)

**Base checkpoint:** `7ea3e86eaa3bb960ede857f95a43ae94f89a082e` (RV-041 HF1/HF2/HF3).
**Status:** offline contract validation; NOT a demonstrated quality gain, NOT production-ready.
**Backward compatibility:** `run_v3()` remains the old path by default; the new flow is invoked only with `run_v42()` or `python -m app.scripts.ask_evidence_v42`.

## Observed failure motivating this design

RV-041 baseline generated four answers, whereas v3 initially failed at the semantic-assurance contract. After HF1/2/3, replay of ORC-001 showed nine initial active requirements, then a post-recovery plan with AI-tool requirements and `clarify`, even though the general question asked for the safeguards for sharing data with an external supplier. HF3 canonically validated the *structure* of the recorded replan and identified a potential scope expansion; it did not certify the correct answer.

The failure was not fixed by making a powerful model perform more unbounded searches. **The operational question must constrain materiality before a missing detail can become an obligatory recovery target.** The original planner and independent inventory retain their complete, unmodified record for audit.

## Runtime architecture

```text
question -> scope_v3 -> adaptive retrieval -> plan_v3
                                             |
                                    inventory_v3 (no plan)
                                             |
                            relevance_v42 [new: semantic materiality]
                               | material / conditional / adjacent
                               | retain all original classifications in audit
                               | freeze classifications across recovery
                                             |
                                 assurance_v3 [on material subset]
                             /                  |
                         approve          retrieve once       abstain/clarify
                            |                   |
                            |           frozen replan_v3 -> inventory
                            |                   |                |
                            |             relevance_v42 -> assurance
                            +-------------------+
                                             |
                                     generate_v3
                                             |
                verify_v3 + independent suppressed-requirements review [new]
                                             |
                            PASS (human review pending) / REJECT
```

The additional gate is intentionally **not a truth oracle**. It classifies each validated requirement and each independent facet using the exact frozen question/scope. Python enforces complete classification, provenance of input requirements, no forged IDs, and immutable old classifications on recovery. Semantic judgments may still be mistaken.

## Materiality and sufficiency rules

- `material`: explicitly requested or needed for the question's answer.
- `conditional`: a relevant category or exception that must be explained conditionally, not presumed true.
- `adjacent`: related background or another business workflow that does not answer the actual question. All suppressed IDs, reasons and original evidence remain auditable.
- Only `material` and `conditional` can be required for the current answer. A model **cannot** transform a source-supported rule into an unsupported one, invent canonical evidence, widen explicit DOC-ID restrictions, or silently rename a frozen requirement.
- An answer is structurally sufficient only when every retained requirement has `evidence_status=supported`, **and** no material unresolved facet remains. This is a **necessary**, not sufficient, condition: `assurance_v3` must independently approve and `verify_v3` must independently PASS.
- Missing *adjacent* details do not force a lookup or clarification. Missing *material* details remain blocking and can cause one authorized recovery, abstenção or pedido de esclarecimento.
- If the material set is empty, fail closed. The model cannot mark everything irrelevant to manufacture an approval.
- Initial planner `clarify`/`abstain` action can be reevaluated in RV-042 only when supported material requirements remain and the independent assurance + final verifier still approve. The original planner decision is logged.

## Final anti-suppression verification

The **final verifier**, in addition to checking every cited claim and required conditions, receives *all suppressed planner/relevance requirements*, their source context, original planner action, and every excluded unresolved facet. It must independently assess each omission and explicitly veto `PASS` if a suppressed requirement would materially change the answer. Python validates one review per suppression ID/index and disallows a positive verdict alongside any declared material omission.

This mitigates but **does not eliminate** correlated error: `relevance_v42`, `assurance_v3` and the final verifier may all use the same LLM. Independent human-reviewed Golden Set and holdout testing remain mandatory.

## What is preserved

The canonical source catalog, hashes, query+document authorization, frozen user scope, bounded dual-query recovery, immutable replan IDs/quotes, strict source/citation constraints, answer-claim coverage, failure-closed behaviour, token/cost budget, baseline v3 and human-review status.

No external document or guessed policy is promoted into authority. No new API tool call or extra retrieval is needed by the relevance classifier; it receives only previously referenced candidate evidence, not the entire retrieved corpus.

## Offline evidence at this checkpoint

- `rv042_offline_scope_audit` replays the **recorded RV-041 ORC-001 plan/inventory only**, frozen by snapshot and input hashes. A **human-review hypothesis** treats initial `C8` (AI-tool workflow) and two unresolved background dependencies as adjacent to a general sharing-safeguards question. It retains `C1–C7` and `C9`. Under that hypothesis, the retained plan items are source-supported.
- This is **not** a generated answer, not a real `relevance_v42` call, and not an independent correctness verdict. ORC-002/003/004 are listed for comparison metadata but were **not** semantically requalified by the offline hypothesis.
- Unit tests use deterministic mock providers, including material-gap recovery, citation veto, frozen relevance, protected document scope, true conditional relevance and original v3 backward-compatibility.

## Cost, quality and next gate

Normal maximum: **7 LLM stage calls + 1 embedding = 8 API calls** (vs v3 7). One-recovery maximum: **11 LLM stage calls + 2 embeddings = 13 API calls** (vs v3 11). Budget and actual cost remain operator-configured. This may increase expense and latency; relevance improvement must exceed that overhead to justify promotion.

1. Confirm offline replay, canonical corpus preflight and complete regression on the real Windows checkout. No API calls during install.
2. Review the recorded ORC-001 hypothesis, especially whether AI is material to a *general* supplier-sharing question and whether the unknown authority details are required for a *general* policy summary.
3. In a separate, explicitly authorized bounded live evaluation, run paired development questions, holdout questions and Q29 abstention. Human-evaluate completeness, missing obligations, unsupported claims, over-clarification, cost and latency. Do **not** mark success solely because model verification says PASS.
4. Promote or roll back based on paired evidence. Keep `run_v3` as experimental control until a promotion decision is documented.

## Commands (PowerShell, repo root)

```powershell
python -m pytest tests -q

python -m app.scripts.rv042_offline_scope_audit `
  --initial docs/validation/RV041_DEV_LIVE_local.json `
  --hf2 docs/validation/RV041_DEV_V3_HF2_LIVE_local.json `
  --output docs/validation/RV042_SCOPE_COUNTERFACTUAL_local.json

python -m app.scripts.ask_evidence_v42 `
  --snapshot docs/validation/EVIDENCE_UNITS_SNAPSHOT_local.json `
  --embedding-cache docs/validation/EVIDENCE_UNIT_EMBEDDINGS_local.json `
  --config docs/validation/STAGE1_RUN_CONFIG_local.json `
  --question "Quais cuidados a política exige antes de compartilhar dados com um fornecedor externo?" `
  --output docs/validation/RV042_PREFLIGHT_local.json
```

**Do not execute with `--execute` until the offline qualification and pricing controls have been reviewed.** Dry run invokes no model or embedding endpoint.
