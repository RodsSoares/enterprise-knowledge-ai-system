# RV-041 HF1 — Real-run contract failure and deterministic recovery

**Status:** experimental hotfix, not production promotion or answer-quality certification.
**Baseline:** first RV-041 paid run, `RV041_DEV_LIVE_local.json`, using `gpt-6.1-sol` and frozen ORC-001..004.

## Findings from recorded responses

- Four baseline executions reached `answered_pending_review`.
- Four V3 executions stopped during `assurance_v3` validation with `V3SemanticError`, after the API returned completed outputs.
- All four raw assessor responses included IDs for `out_of_scope` planner items. The previous validator considered only in-scope IDs and rejected those extra rows.
- The ORC-003 excluded onboarding item cited an ID outside the presented candidates. This must not become accepted evidence. New requests present only in-scope requirements to the assessor, with exclusion descriptions separately for scope delimitation. The validator still rejects all foreign candidate IDs appearing in an active assessment.
- ORC-001 and ORC-002 proposed recovery targeting requirements already supported as written, because the independent inventory detected unresolved external dependencies. The prior validator rejected that combination. The hotfix permits an in-scope target only when the independent inventory reports omissions or unresolved facets.
- ORC-004 produced `CLARIFY`, even though its own explanation acknowledged that general incident-response steps could be answered. This is a semantic over-conservatism candidate, not resolved by HF1.

## Exactly what changed

1. `v3_pipeline.py`: `assurance_v3` input contains only in-scope requirements; excluded requirement descriptions remain in a separate field.
2. `v3_live_provider.py`: versioned assurance prompt explicitly forbids assessment rows for excluded IDs; prompt hash is derived from the actual instruction string.
3. `v3_semantic_contracts.py`: retrieval targeting handles separately identified inventory omissions. Unauthorized documents, unknown requirement targets, repeated recovery and foreign active citations remain forbidden.
4. `rv041_assurance_replay.py`: uses the stored completed assessor outputs and removes only rows that the revised request will not ask the model to produce. Revalidates remaining decisions against the original canonical snapshot. This is a **counterfactual structural projection**, not evidence that a future model response or the end-to-end pipeline will pass.
5. `rv041_resume_v3.py`: reuses the four already paid baseline runs and executes only V3 arms. Defaults to zero-API dry-run. Live execution requires both `--execute` and `--confirm-paid`, uses a fresh output filename and stops the batch on the first integration failure. The new cost cap applies only to **new paid V3 calls**; previously incurred charges remain visible as historical baseline usage.

## Guardrails

- No automatic API calls in installation or offline replay.
- No automatic promotion of V3 or semantic PASS claim.
- No edits to baseline pipeline, physical sources or frozen questions.
- Preserve original RV-041 report untouched.
- Never commit the original paid raw-output report without an explicit privacy review.
- A new V3 response may still reach `RETRIEVE_MORE`, `CLARIFY`, `ABSTAIN` or an error. Offline projection does not guarantee it will generate an answer.

## Operator sequence

1. Install the HF1 bundle and run its single consolidated validation (targeted tests, full regression, offline projection and resume dry-run).
2. Review `docs/validation/RV041_HF1_ASSURANCE_REPLAY_local.json`.
3. Only after that, explicitly authorize V3-only paid resume (no baseline rerun).
4. Compare answer content and citations; qualify semantic quality independently from the model's own assessor and verifier.
