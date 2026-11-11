# RV-041 HF2 — Frozen requirement identities and cost-aware checkpoint resume

**Status:** experimental correction, not independently validated for answer quality.
**Input evidence:** RV041_DEV_V3_RESUME_local.json (HF1) and its original frozen snapshot.
**No production promotion.** Baseline and frozen development questions remain unchanged.

## Confirmed root cause

HF1 successfully passed scope, adaptive retrieval, initial v3 planning, independent inventory,
semantic assurance (`RETRIEVE_MORE`), one dual-query complementary retrieval and a second
LLM planning call for ORC-001. The Python conservation gate compared the *free-form*
`need` text from first and second plans, not immutable identity. The model emitted nine
in-scope items again, but changed eight descriptions. The code therefore reported
`V3SemanticError` before the second inventory or generation.

This observation **does not independently prove semantic equivalence** of the old and
new descriptions. It establishes that the mechanism is fragile and does not provide
stable requirement identities across replan. The updated contract removes this
failure mode without relying on guessed semantic matching.

## Correction

1. Initial `plan_v3` remains intact and defines frozen `C1...Cn` IDs, original
   descriptions, conditions, relevance, question spans and already verified quotes.
2. After exactly one authorized recovery, `replan_v3` receives `previous_requirements`
   and the prior assurance decision. Its response is a **delta**, not another free-form
   plan: one `updates[]` record for each original in-scope ID, with new evidence status,
   newly found quote-backed source supports and explicitly remaining gaps.
3. Excluded requirements persist unchanged. New facets can only be appended through
   `new_items[]`. The application, not the model, allocates their IDs.
4. A deterministic composer rehydrates the original frozen requirements and validates
   the entire resulting plan using the existing `validate_v3_plan` gate. It rejects
   missing/unknown/duplicate IDs, altered source texts, forged sources and further
   retrieval attempts. Previously authorized supports cannot be silently removed.
5. This does not establish global completeness or relevance. Independent inventory,
   assurance and final claim verification remain required and uncertain.

## Resume policy

`rv041_resume_hf2.py` can consume the failed HF1 resume file and **replay** the first
four model outputs and the two retrieval stages from their frozen, canonical source
identities. It does not reuse the fifth historical free-form replan response; it
starts new paid model calls with `replan_v3`, then live inventory, assurance, generation
and verification as required. Model and input/prompt hashes are verified before
replay. Only one failed ORC-001 arm is eligible for prefix replay; ORC-002..004 run
normally as v3-only arms. Replayed outputs are fed through current deterministic
validators; no previously saved answer is promoted without its checks.

**Cost accounting:** original paired experiment and failed HF1 resume are historical
spend. The HF2 report separates historical calls from *new* API calls. Its
`usage_summary` is a convenience for baseline plus newly evaluated v3 arms and is
**not** a sum of all past aborted attempts. An explicit estimated new-cost cap is
allocated per pending arm. No exact billing guarantee is claimed.

## Evaluation and release conditions

- Offline proof: 9 initial in-scope requirements, 9 rephrased requirements, 8 text
  differences, 0 new API calls. This is a **lexical identity diagnostic**, not proof
  that no meaning changed.
- Contract proof: mock tests for frozen identities, source links, authorizations,
  missing IDs, duplicate updates and one-recovery limit.
- Source integrity: exact snapshot/cache/config/cases hashes and past stage prompt
  hashes must match. Any mismatch fails the dry-run before API calls.
- Operational proof still needed: live ORC-001 reaches a meaningful final state and
  ORC-002..004 do not introduce new structural errors.
- Semantic proof still needed: independent human evaluation of actual answers,
  omitted requirements, conditions and citation-to-claim entailment. An LLM PASS
  alone does not validate semantic correctness.
- Do **not** publish raw paid-run logs or enterprise corpus files by default.

## Commands

The installer performs targeted/full tests, offline root cause diagnostic and an
HF2 resume preflight with zero API calls. A *separate* explicit invocation of
`rv041_resume_hf2.py --execute --confirm-paid` is required for live continuation.
