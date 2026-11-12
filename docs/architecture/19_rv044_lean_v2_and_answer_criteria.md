# RV-044 — Lean pipeline v2, answer criteria and first measured results

**Status:** MVP candidate. Measured on the full 27-document corpus with deterministic
scoring. Not a semantic certification: a pass means required facts and sources are
present, not that every sentence was reviewed.

## What was wrong (root causes, in order of impact)

1. **Answer criteria did not exist.** All 36 golden questions had
   `expected_answer_specification: "To be finalized"`. Only four development cases
   (ORC-001..004) had prose checks, and they were reused across dozens of experiments.
   There was no objective target to tune against.
2. **The lean pipeline ran on 10 of the 27 documents.** The snapshot was built on
   8 November, before the 17 RV-032 documents were added. 20 of the 46 evaluation
   cases could not be answered at all. `.txt` sources were also excluded by the
   snapshot builder, and two spreadsheets lacked header declarations.
3. **Preflight only worked on a Windows checkout.** Input hashes were taken over
   CRLF files; the same files check out with LF elsewhere.
4. **Fail-closed validators turned harmless model slips into failed runs**: an
   inconsistent verdict, a miscounted check list, an unknown citation id, an answer
   with no claims. RV-041 HF1..HF3 were all contract failures, not answer failures.
5. **A binary verifier gate.** One doubtful claim, or a subjective "incomplete",
   hid the whole answer. The verifier asked for neighbouring-topic rules (AI
   approvals) on a general data-sharing question, the same scope disagreement seen
   in RV-041.
6. **Chunk-level retrieval misses hidden by document-level metrics.** For Q23 the
   decisive section (DOC-010 §3, immediate actions) was not in the top 20 units
   although DOC-010 was. Slide bullets are indexed without their slide title.
7. **Corpus content.** 67 of 244 searchable passages, in 26 of 27 documents,
   contain text about the test itself (see below).
8. **Model capability.** `gpt-4.1-mini` answered in English or Spanish in 4 of 89
   runs and was unstable on completeness and on clarify/abstain decisions.

## What changed

| Area | Change |
|---|---|
| Criteria | `data/ground_truth/answer_criteria.yaml`: outcome, required citations, required facts and forbidden statements for Q01-Q36 and ORC-001..010, written from the corpus text |
| Scoring | `app/evaluation/answer_criteria.py`: deterministic, free, reproducible |
| Runner | `app/scripts/evaluate_lean.py`: dry run with cost estimate, hard cost ceiling, repeats, `--score-only`, `--retrieval-only` |
| Snapshot | 27 documents, 261 units, 244 searchable (`EVIDENCE_UNITS_SNAPSHOT_27DOC.json`); `.txt` included; DOC-013 and DOC-021 headers declared |
| Portability | Input hashes accept LF and CRLF |
| Evidence | Best 3 documents are sent in full, grouped by document in source order, with slide titles |
| Citations | Models cite `E1..En`; Python maps to canonical unit ids |
| Triage | The answer model labels every passage direct / conditional / background / irrelevant before writing |
| Gates | No direct passage -> abstain. Claims citing only background passages are removed |
| Verifier | Verdict derived in Python; failed claims are removed, the rest kept; "incomplete" becomes a reservation (`--on-incomplete withhold` restores the old behaviour) |
| Language | Answer language detected and enforced, with one bounded repair call |
| Authority | Registry level shown as a labelled rank (the registry scale is the inverse of DOC-007's) |
| Resilience | Up to 2 SDK retries for connection errors and 5xx |
| Request size | Document header sent once; verifier receives only cited and usable passages |
| Corpus gate | `app/scripts/audit_corpus_content.py` |

## Results (27 documents, 46 cases, top-k 20, expand 3)

| Model | Runs | Passed | Notes |
|---|---:|---:|---|
| gpt-4.1-mini | 92 (2 per case) | 72 (78%) | 30 cases always pass, 12 unstable, 4 never; 3 failures were transient network errors |
| gpt-6.1-sol | 36 (1 per case) | 35 (97%) | 10 cases not run (batch interrupted); only miss is Q20 (cites DOC-005 but not DOC-006) |

Document-level retrieval: all 46 cases have every required document among the
top 20 candidates (45 of 46 at top 12).

These runs used the request shape before the size reduction below. The reduced
shape carries the same information to the answer model and less to the verifier;
**it has not been re-measured**.

Sending 5 documents in full instead of 3 was worse with `gpt-4.1-mini` (more
context made it answer Q29 and ORC-006). Keep 3.

## Cost

About 12,000 input and 1,450 output tokens per question in these runs. After the
size reduction the two requests are about half as large (46,170 -> 23,625
characters per question, measured offline on the saved runs). The whole RV-044
investigation used about 3.0M input and 0.24M output tokens over 756 calls,
most of it in repeated full-batch runs. `evaluate_lean.py` now defaults to a
USD 0.50 ceiling and prints a token and cost estimate before any paid call.

## Corpus content

`python -m app.scripts.audit_corpus_content --show` lists every passage. Three
kinds of harness text reach the model as evidence:

- **Leakage**: "Benchmark coverage: Q02, Q06, Q10", "Expected use: Q11 and Q28;
  distractor for Q10", "Golden Set: Q06, Q07", `evaluation_questions | Q08, Q09`.
- **Disclaimers**: "RV032 synthetic draft", "proposed synthetic definitions ...
  require acceptance before benchmark freeze", "not fixed in canonical_facts.yaml".
- **Instructions to the reader**: "must not be used to answer current-policy
  questions", "Do not recommend following its obsolete sharing instruction",
  "the system must not invent a final recommendation".

Observed effect: answers repeat the disclaimers ("o documento ressalva que os
responsáveis e os status são fatos sintéticos propostos, não fixados em
canonical_facts.yaml"), and section titles such as "controlled synthetic detail"
appear in the source list. The conflict and distractor tests are also weakened:
DOC-011 states that it conflicts with DOC-006 and must not be followed, and
DOC-025 and DOC-027 describe themselves as distractors, so the system is not
required to resolve authority by itself.

Other content findings:

- Q11 asks why the OTIF target changed; the corpus records the approval, not a reason.
- Q17, Q19 and Q27 depend on a previous turn or are ambiguous (two 2024 documents).
- Q05 "diretoria" is ambiguous between Procurement Director and Executive Director.
- DOC-005 §6 links data sharing to AI rules, so a conditional AI remark in
  ORC-001 is supported by the corpus.

## Open items before calling it an MVP

1. Clean the 26 documents and regenerate snapshot and embeddings.
2. Run the 10 cases not yet measured on the chosen model, then one full pass with
   the reduced request shape.
3. Human review of a sample of passed answers against `human_check`.
4. Slide-level evidence units for PPTX in `EvidenceUnitBuilder`.
5. A minimal API or UI over `run_lean`.

## Commands

```powershell
python -m pytest tests -q
python -m app.scripts.audit_corpus_content --show
python -m app.scripts.evaluate_lean --output docs/validation/RV044_DRY_local.json
python -m app.scripts.ask_evidence_lean --question "Quem aprova uma nova ferramenta de IA?" --output docs/validation/RV044_ASK_local.json
```

Paid execution adds `--execute --confirm-paid`. Rebuilding the catalog:
`prepare_evidence_units --output NEW_FILE`, then `embed_evidence_units`.
