# RV-041 HF3 — Canonical replay and answerability audit

**Status:** structural boundary hotfix, NOT a semantic-quality promotion.
**Evaluation:** ORC-001, with all work done offline against the immutable HF2 paid report and verified canonical source snapshot.
**API policy:** this release performs **zero** new paid calls; do not schedule a v3 rerun as its next step.

## Evidence of failure

The `RV041_DEV_V3_HF2_LIVE_local.json` report shows a completed `replan_v3` call whose response was rejected by `V3PlanningContractError`. The exact repeated unit is a previously authorized `DOC-005` source within update `C2`. This is an idempotent citation rather than an attempted mutation; rejecting the ID solely because it is present in the frozen plan is stricter than intended. The previous response remains available in `usage.events[0].raw_output` and can be replayed with no API usage.

## HF3 structural change

* Retain frozen requirement IDs, text, conditions, question anchor and all prior supports.
* For `additional_supports`, validate the source against the canonical eligible catalog and validate each quote as an exact unique substring, even when the unit was already cited.
* An already-retained unit ID is a **no-op** after validation. A previously unseen eligible unit ID is added once.
* Reject duplicate IDs within the new proposal, forged IDs, quarantined/navigation sources and nonmatching or ambiguous quotes.
* Revalidate the composed plan with the original strict `validate_v3_plan` checks, including missing facets, no second search and authorized source provenance.

## What the replay reveals about semantics

Applying the idempotent citation rule to the real paid replan output produces a structurally valid delta with 14 active requirements. Its declared action is `clarify`, requesting additional policy/authority documents rather than answering a generic question. The model also introduces three AI-related requirements not present in the user's explicit question. The initial plan already contained a conditional AI-related requirement, and the initial independent inventory included AI dependencies despite the question's direction: sharing data **with an external supplier**, not processing supplier data **inside an AI tool**.

The baseline already answered ORC-001 with applicable classification categories, secure-channel requirements, exceptions and exact citations. Its factual quality still requires independent evaluation; however, this shows the v3 clarification should not be considered an improvement or a successful end-to-end answer.

The offline reporter flags potential scope expansion using a *keyword heuristic only*. It does **not** automatically remove questionable requirements or claim proof of semantic irrelevance; adjudication and future policy for material relevance are separate work.

## Mandatory design correction before any further paid qualification

Consolidate into the next architecture revision rather than another stream of protocol hotfixes:

1. Freeze question intent as a structured **action direction** (from whom, to whom, doing what), not solely a textual scope focus. Distinguish summarizing general requirements from granting case-specific approval.
2. Evaluate **material relevance** before treating inventory observations as missing required obligations. A nearby unrelated conditional workflow must not force a recovery.
3. Permit complete **general conditional explanations** when a policy names an authority or security control but does not specify its full operational details. Do not invent those details. Require clarification only when a *specific requested decision* depends on them.
4. The reviewer must recognize omitted relevant requirements, but must not endlessly expand into neighboring topics. Track unaddressed material information separately from irrelevant source content.
5. Keep raw canonical provenance validation, bounded calls, independently reviewable claims, and the original production-neutral baseline as rollback.
6. Compare baseline and v3 against frozen sources with human semantic review, not `APPROVE`/test-count proxy metrics. Track false refusals/clarifications, unsupported claims, omissions, scope drift and cost.

**Next action:** inspect and approve the RV-042 design before enabling new paid calls. The HF3 replay is an offline diagnostic, not authorization to resume the full experimental cohort.
