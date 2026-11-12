# RV-045 — Clean corpus and MVP interface

**Status:** functional MVP, measured on the cleaned corpus with the reduced
request shape: 45 of 46 cases pass deterministic scoring with `gpt-6.1-sol`
(one run per case). Not a semantic certification.

## Corpus

`app/scripts/rv045_clean_corpus.py` removed the evaluation-harness text found in
RV-044 from 26 documents. Business facts were not changed.

| Check | Before | After |
|---|---:|---:|
| Searchable passages with harness text (`audit_corpus_content`) | 67 of 244 | 0 of 219 |
| Documents affected | 26 of 27 | 0 of 27 |

- PDFs were regenerated with ReportLab from the structure parsed in RV-044. All 15
  were re-parsed with Docling and keep the same headings, paragraphs and tables.
- DOCX, PPTX, XLSX, Markdown and text files were edited in place.
- DOC-011 no longer states that it conflicts with DOC-006, and DOC-025 / DOC-027 no
  longer describe themselves as distractors. Authority and lifecycle now have to be
  resolved from document status, DOC-006 and DOC-007.
- The three carrier contracts no longer describe each other, so Q12 needs all three.
- DOC-013 lost its "Canonical status" column; metadata rows about the test were
  removed from DOC-012, DOC-013 and DOC-021.
- The script is a one-time migration. Its PDF output is byte-reproducible; Office
  files are not, so do not re-run it over the cleaned corpus. The pre-cleaning
  catalog is in commit `32022ce`.

The catalog (`EVIDENCE_UNITS_SNAPSHOT_27DOC.json`, 236 units, 219 searchable) and
its embeddings were rebuilt from the cleaned files. RV-035/036 retrieval figures
and RV-044 answer figures were measured on the previous text.

## Evaluation on the cleaned corpus

`gpt-6.1-sol`, 46 cases, one run each, top-k 20, three documents sent in full.
Final answers and scores: `docs/validation/RV045_LEAN_EVALUATION_RESULTS.json`.

| Result | Cases |
|---|---:|
| Pass | 45 |
| Fail | 1 (Q20) |
| Answered, verified | 38 |
| Answered with a reservation | 3 (Q01, Q16, Q35) |
| Clarification requested | 3 |
| Abstained | 2 |
| Execution failures, wrong-language answers | 0 |

- **Q20** ("which internal policies apply to sharing data with carriers") cites the
  Data Sharing Policy and not the Information Security Policy. The same miss
  occurred in RV-044.
- **ORC-003** first scored as a failure because a forbidden pattern matched the
  negated sentence "approval does not automatically authorize". The pattern was
  replaced by a `human_check`; the answer was correct.
- The three reservations are the verifier pointing to a rule from a neighbouring
  section; the answers pass the criteria.
- Mean usage per question: 5,628 input and 1,322 output tokens, about USD 0.028.
  The batch cost USD 1.29 in total.
- A first attempt used a USD 0.10 ceiling per question. The budget reserves the
  worst case before each call, and with this model's prices the answer call did
  not fit, so 17 runs stopped after the embedding call. The default ceiling per
  question is now USD 0.30; the amount actually spent is unchanged.
- One run per case does not measure stability. RV-044 showed this model stable on
  the cases it was run on; `gpt-4.1-mini` was not.

## Interface

```powershell
pip install -r requirements.txt
$env:OPENAI_API_KEY = "..."
streamlit run app/frontend/main.py
```

- `app/service/knowledge_service.py` loads the verified catalog once and answers
  through the lean pipeline. It is the single entry point for any future API.
- `config/lean_runtime.json` holds catalog paths, models, prices and cost ceilings
  (USD 0.30 reserved per question, USD 0.50 per session). Prices must be checked against
  current billing.
- The interface shows the status, each claim with its citations, the cited
  passages with their lifecycle (current, superseded, historical), reservations,
  and tokens and cost per question and per session.
- Colors and layout follow the images in the project READMEs: the AI Supply Chain
  Copilot interface and the Enterprise Knowledge artwork (navy panels, white-to-cyan
  title, green for grounded answers, amber for insufficient evidence, purple for
  questions that need the user). Theme: `.streamlit/config.toml`.

Measured in the interface with `gpt-4.1-mini`: an answered question used 6,614
input and 825 output tokens in 3 calls (USD 0.004); an abstention used 4,088 and
389 in 2 calls (USD 0.002).

![MVP interface](../images/mvp-interface.png)

The screenshot is a layout preview rendered with canned answers.

## Still open

1. Q20: make multi-policy questions name every applicable policy.
2. Human review of a sample of answers against `human_check`.
3. Slide-level evidence units for PPTX.
4. Authentication, persistence and deployment.
