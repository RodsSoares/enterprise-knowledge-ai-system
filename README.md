# Enterprise Knowledge AI System

🚀 **Current Release:** Functional Lean Enterprise RAG MVP — RV-045  
🌐 **Live Application:** [Launch Enterprise Knowledge AI System](https://enterprise-knowledge-ai-system.onrender.com/)  
🧪 **Validation Baseline:** 27 documents · 236 evidence units · 45/46 deterministic checks passed with `gpt-6.1-sol`  
🛡️ **Engineering Focus:** Source provenance · hybrid retrieval · cited claims · verification · bounded execution

The **Enterprise Knowledge AI System** is a modular, evidence-first Enterprise Retrieval-Augmented Generation (RAG) platform that transforms fragmented organizational documents into searchable, traceable knowledge and answers grounded in identifiable sources.

The implemented MVP combines multi-format document ingestion, canonical content representation, evidence units, version-aware metadata, hybrid retrieval, structured AI generation, deterministic guardrails, and independent model-mediated claim verification. The project also contains broader orchestration and evaluation research, **clearly separated from the live MVP path**.

> **Evidence before generation. Retrieval quality before answer fluency.**

## Engineering Overview

The system separates **offline knowledge preparation** from **online question answering**. Offline, it creates and verifies a citable evidence catalog and its embeddings. Online, it retrieves relevant material, assembles bounded context, generates source-backed claims, validates their references, and performs a separate verification pass.

| Layer | Implemented in the Lean MVP |
|---|---|
| Enterprise Sources | Controlled synthetic corporate corpus with 27 documents and source registry |
| Ingestion & Parsing | IngestionRouter, Docling, native XLSX adapter, PDF/DOCX/XLSX/PPTX/MD/TXT |
| Canonical Representation | `NormalizedContent`, structured blocks, source locations and metadata |
| Evidence Units | Structure-sensitive text/table records; 236 units, of which 219 are searchable |
| Verified Catalog | Versioned evidence snapshot, source hashing, identity checks and cached embeddings |
| Hybrid Retrieval | OpenAI embeddings, cosine similarity, BM25, PT/EN expansion and adaptive fusion |
| Evidence Assembly | Bounded document expansion, canonical citation aliases and source ordering |
| Answer Generation | Structured evidence assessment and cited claims; at most one recovery search |
| Independent Verification | Separate LLM assessment of claim entailment, relevance, conditions and completeness |
| Deterministic Controls | Citation mapping, document scope, answer schema, abstention conditions and budgets |
| Experience | Streamlit chat, model selection, uploads, cited passages, source links and usage display |
| Validation & Delivery | pytest, offline GitHub Actions, RV-045 evaluation, Render deployment |

<p align="center">
  <img src="docs/images/Arquitetura%20MVP%20de%20IA%20Empresarial%20com%20RAG.png"
       alt="Enterprise Knowledge AI System — current implemented Lean RAG MVP architecture"
       width="1150">
</p>

*Current implemented architecture. See the [technical specification](docs/architecture/21_current_lean_mvp_architecture.md) for executable contracts and limits. The previous [navy/cyan technical diagram](docs/images/architecture-overview-7039382.svg) remains versioned. Historical Stage-1, v3, v4.2, and Evidence Assurance investigations are **not** part of the default online request path.*

## Trustworthy Enterprise RAG Principle

The system is built around a separation of responsibilities:

~~~text
Enterprise Documents
       ↓
Canonical Content + Source Metadata
       ↓
Verified Evidence Units + Search Index
       ↓
Hybrid Retrieval + Bounded Context
       ↓
LLM Interpretation + Cited Claims
       ↓
Python Citation / Scope Validation
       ↓
Independent Claim Review
       ↓
Grounded Answer · Reservations · Clarification · Abstention
~~~

**The LLM interprets evidence. Python governs references, contracts, limits and outcome rules.** The language model is not an enterprise system of record, and a citation identifier alone is not proof that a claim is true.

## The Core Idea

> **Enterprise RAG is not primarily a text-generation problem. It is an evidence-selection, provenance and answerability problem.**

A fluent answer is not enough if the system retrieves a superseded policy, loses the structure of a spreadsheet, confuses source authority, omits another applicable policy, or attaches a citation that does not support the stated claim.

The project therefore treats document identity, source structure, retrieval quality, evidence scope, citation integrity and systematic evaluation as architectural capabilities—not accessories around a prompt.

## System Overview

The product-level view complements the engineering pipeline: heterogeneous corporate knowledge is transformed into a controlled intelligence layer for human consumption and decision support.

<p align="center">
  <img src="docs/images/art-system-overview.png"
       alt="Enterprise Knowledge AI System — product-level system overview and knowledge intelligence concept"
       width="1100">
</p>

**Product proposition:** turn disconnected corporate documents into an accessible knowledge experience while preserving the source and context required to evaluate each answer.

## Product Experience

The Lean MVP is a functioning Streamlit application connected to the catalog and the answer/verification pipeline, not merely a proposed architecture.

### MVP Interface

Users can submit questions, select supported models, choose between the synthetic corpus and session-uploaded files, and inspect returned citations, excerpts, document status, tokens and estimated cost.

<p align="center">
  <img src="docs/images/mvp-interface.png"
       alt="Enterprise Knowledge AI System — Streamlit MVP interface preview"
       width="1050">
</p>

*Interface layout preview. For a recorded interaction with the deployed application, see the animation below.*

### System in Action

The demonstration follows an enterprise knowledge question through the application and shows a source-backed answer, its citations, document inspection and a follow-up query.

<p align="center">
  <img src="docs/images/enterprise-knowledge-demo.gif"
       alt="Enterprise Knowledge AI System — interactive RAG MVP demonstration"
       width="900">
</p>

**[Open the live application](https://enterprise-knowledge-ai-system.onrender.com/)**

The live demonstration uses a **synthetic, non-confidential 27-document corpus**. The default model is `gpt-4.1-mini`; access to the protected `gpt-6.1-sol` option requires a sidebar password. A free Render instance may take time to wake when idle.

### Capabilities Available in the MVP

- **Evidence-grounded questions:** ask about policies, contracts, operating procedures, approval matrices, KPIs and other indexed documents.
- **Version and status visibility:** inspect current, historical and superseded sources where metadata is available.
- **Inspectable answers:** view the cited passages and available document references rather than relying only on the generated text.
- **Multi-format session uploads:** PDF, DOCX, XLSX, PPTX, Markdown and TXT may be analyzed in-memory alongside or instead of the example corpus.
- **Controlled outcomes:** receive an answer, an answer with reservations, a clarification request, abstention or a controlled failure.
- **Usage transparency:** inspect per-question/per-session usage and cost estimates.

**Upload boundary:** runtime uploads use lightweight parsers and do **not** follow the complete offline Docling ingestion pipeline. Scanned image-only PDFs are not supported by the upload reader. Uploaded text is sent to the OpenAI API; **do not upload confidential documents**.

See [MVP delivery notes](docs/architecture/20_rv045_clean_corpus_and_mvp_interface.md) and [Render operating instructions](docs/validation/RENDER_MVP_DEPLOYMENT.md).

## Table of Contents

- [Engineering Overview](#engineering-overview)
- [Trustworthy Enterprise RAG Principle](#trustworthy-enterprise-rag-principle)
- [The Core Idea](#the-core-idea)
- [System Overview](#system-overview)
- [Product Experience](#product-experience)
- [Overview](#overview)
- [Current Status](#current-status)
- [Enterprise Knowledge Sources](#enterprise-knowledge-sources)
- [Canonical Document Model & Evidence Units](#canonical-document-model--evidence-units)
- [Solution Architecture](#solution-architecture)
- [Retrieval & Evidence Assembly](#retrieval--evidence-assembly)
- [Answer Generation & Verification](#answer-generation--verification)
- [Ground Truth & Evaluation](#ground-truth--evaluation)
- [Governance, Traceability & Runtime Controls](#governance-traceability--runtime-controls)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Getting Started — Local Development](#getting-started--local-development)
- [Automated Tests & CI](#automated-tests--ci)
- [Engineering Practices](#engineering-practices)
- [Roadmap & Current Development Stage](#roadmap--current-development-stage)
- [Documentation & Engineering History](#documentation--engineering-history)
- [Why This Project?](#why-this-project)
- [License](#license)

## Overview

Organizations keep operational knowledge across policies, procedures, supplier contracts, spreadsheets, guidelines, reports and presentations. Traditional search can return a file containing a keyword without establishing **which version applies, which section answers the question, or whether several documents must be considered together**.

This project explores a software-engineering response to that problem. Its objectives are to:

1. Parse diverse source formats into an application-owned representation.
2. Preserve structural context, identity, version and provenance.
3. Build an inspectable catalog of evidence rather than an opaque text blob.
4. Retrieve and assemble the smallest useful bounded source context.
5. Generate answers that cite specific source passages.
6. Reject unsupported citations and expose uncertainty or gaps.
7. Evaluate retrieval, grounding and answer quality independently.

The corporate corpus is deliberately **synthetic**. Its policies, service levels, approval thresholds and authority relationships emulate realistic business knowledge without exposing employer data.

### Example Business Questions

The controlled corpus enables scenarios such as:

- Which delivery SLA applies to a given service category?
- What is the currently effective OTIF target, and how does it differ from the earlier target?
- Which approvals are required for an emergency procurement?
- Which contractual penalties apply to different carriers?
- Which internal policies govern data sharing with logistics providers?

The OTIF scenario illustrates the intended behavior: **97%** is the current target in the synthetic scenario, while **95%** belongs to an earlier version. The system must distinguish those periods from the documents, not from model memory.

## Current Status

**Status: functional, deployed Lean RAG MVP (RV-045).** The live application runs through:

~~~text
Streamlit UI
    ↓
KnowledgeService
    ↓
AdaptiveEvidenceUnitRetriever
    ↓
Lean Pipeline: retrieve → answer → verify
    ↓
Checked source-backed response or controlled alternative
~~~

The canonical implementation path is `app/frontend/main.py` → `app/service/knowledge_service.py` → `app/orchestration/lean_pipeline.py`.

| Capability | Status | Important boundary |
|---|---|---|
| 27-document controlled corpus | Implemented | Synthetic, not connected to live corporate systems |
| PDF/DOCX/XLSX/PPTX/MD/TXT ingestion | Implemented | Parser-specific fidelity still requires review |
| Canonical blocks and source locations | Implemented | Parsed structure is not automatically semantic correctness |
| Verified snapshot + cached embeddings | Implemented | Source changes require a controlled rebuild |
| Vector + lexical retrieval and fusion | Implemented | Ranking does not guarantee evidence completeness |
| Document-aware evidence expansion | Implemented | Limited to bounded context and selected sources |
| Structured generation and one recovery | Implemented | Model may still misunderstand a condition |
| Separate claim verification | Implemented | Verification is another model judgment |
| Streamlit demo, uploads, usage controls | Implemented | Demo-level access, not enterprise authentication |
| Offline regression and archived evaluation | Implemented | CI does not replay paid LLM evaluations |
| Stage-1/v3/v4.2 orchestration research | Experimental | Not in the active Streamlit path |
| Cross-encoder/reranking alternatives | Experimental | Not the production-default retriever |
| Enterprise ACL, SSO, persistent multi-user storage | Not implemented | Required before enterprise deployment |

The milestone represents a working system with testable technical behavior, **not** production certification, universal correctness or a claim of enterprise security readiness.

## Enterprise Knowledge Sources

### Controlled Document Universe

The RV-045 source set has **27 physical documents** in six supported formats: PDF, DOCX, XLSX, PPTX, Markdown and plain text. Documents model an interconnected business universe: policies, standards, operational procedures, approvals, contractual obligations, KPIs and supporting records.

Source metadata supports information such as:

| Metadata | Engineering role |
|---|---|
| Document ID | Stable source identity and document-scoped retrieval |
| Document type | Policy, standard, SOP, contract, guideline or reference context |
| Version / effective date | Source lifecycle and time applicability |
| Status / supersession | Current, historical and replaced-document context |
| Authority level | Explicit relative source ranking supplied to the model |
| Section / page / sheet | Traceability of a selected passage to its origin |

These attributes help the model distinguish competing documents; they are **not yet a deterministic enterprise policy engine**. Tenant permissions and document-level authorization are outside the current MVP.

### Corpus Integrity

The source files are transformed offline into a frozen evidence snapshot. A verified snapshot and matching embedding cache are loaded by `KnowledgeService`. Hash and identity validation guards against accidental source/catalog mismatches.

The cleaned RV-045 corpus deliberately removes evaluation-harness information from searchable content. Expected answers and scoring criteria belong to the **evaluation layer**, not to the knowledge base presented to the answer model.

[Corpus and interface checkpoint — RV-045](docs/architecture/20_rv045_clean_corpus_and_mvp_interface.md).

## Canonical Document Model & Evidence Units

### Canonical Representation

The ingestion router dispatches files to the appropriate parser, including Docling and the specialized XLSX adapter. Parser-specific output is normalized into application-owned data structures so retrieval and answer logic are not tied to a single vendor document representation.

The canonical model distinguishes meaningful content categories such as text, tables, lists and images, retaining source and structural information where available. For spreadsheets, the native parser preserves sheet-oriented and row-oriented relationships needed to interpret table records.

### Structure-Aware Evidence

Rather than indiscriminately splitting every document into equal text windows, the project materializes **citable evidence units**, including sections and table records with source identity.

The current cleaned snapshot contains:

| Corpus checkpoint | Recorded amount |
|---|---:|
| Physical documents | **27** |
| Total evidence units | **236** |
| Searchable evidence units | **219** |
| Non-searchable or structural units | **17** |

A unit's existence in the catalog does not ensure that the retriever will select it for every relevant question; ranking and completeness are evaluated separately. Titles and other structural context may remain available during context expansion even when they are not separately indexed.

This distinction was informed by earlier chunking and multi-document retrieval experiments. Their detailed replays remain in the [retrieval validation history](docs/validation/RETRIEVAL_VALIDATION.md).

## Solution Architecture

### Offline Pipeline — Knowledge Preparation

~~~text
Synthetic Enterprise Sources + Document Registry
                    │
                    ▼
         IngestionRouter / Parsers
                    │
                    ▼
      Canonical NormalizedContent
                    │
                    ▼
     Structure-Aware Evidence Units
                    │
          ┌─────────┴──────────┐
          ▼                    ▼
 Verified Evidence       Embedding Cache
 Snapshot + Hashes       text-embedding-3-small
          └─────────┬──────────┘
                    ▼
    KnowledgeService Startup Validation
~~~

The offline pipeline establishes the source-of-truth catalog used by the deployed demo. Document vectors are **precomputed**; they are not regenerated on every user question. A corpus revision requires rebuilding and validating both the catalog and the corresponding cache.

### Online Pipeline — Answering a Question

~~~text
User Question / Selected Model / Source Scope
                    │
                    ▼
              Streamlit UI
                    │
                    ▼
            KnowledgeService
         verified catalog + budgets
                    │
                    ▼
          Adaptive Hybrid Search
           vectors + BM25 + fusion
                    │
                    ▼
          Bounded Evidence Assembly
           documents / E1...En
                    │
                    ▼
           Structured Answer Model
       answer / retrieve / clarify / abstain
                    │
                    ├──── optional one recovery retrieval
                    │
                    ▼
       Deterministic Python Validation
         schema / citation / scope
                    │
                    ▼
             Independent Verifier
       entailment / relevance / conditions
                    │
                    ▼
          Python-Derived Final Outcome
                    │
                    ▼
       Cited Answer / Reservations / Abstain
~~~

The goal is a **bounded, observable application workflow**, not unrestricted agent autonomy. The current execution path uses a lean pipeline; independent experimental orchestration code in the repository must not be mistaken for active runtime behavior.

The [current architecture specification](docs/architecture/21_current_lean_mvp_architecture.md) describes the exact sequence, contracts and outcome state machine.

## Retrieval & Evidence Assembly

### Hybrid Search

The online retriever combines complementary signals:

- **Semantic relevance:** the user query is embedded using OpenAI `text-embedding-3-small` and compared with cached unit vectors by cosine similarity.
- **Lexical relevance:** BM25 detects exact terminology and other signals that embeddings can underweight.
- **Bilingual assistance:** controlled Portuguese/English query expansion improves matching against terminology across languages.
- **Fusion:** an adaptive scoring/fusion strategy combines rankings while protecting important vector candidates.
- **Explicit document scope:** a named `DOC-NNN` document ID limits admissible retrieval candidates.

The current configuration uses **top-k = 20** retrieved units. These are ranking candidates, not guaranteed answers.

### Evidence Assembly

The lean pipeline expands the **three strongest documents** in source order, subject to a **60-unit** cap. It then presents a bounded context with short aliases (`E1`, `E2`, …) that Python maps back to canonical evidence unit IDs.

This design addresses a common retrieval failure: a top-ranked passage may identify the relevant document but leave out an adjacent exception, condition or related clause. Expansion improves context availability, but **does not prove completeness**.

### Key Retrieval Trade-offs

A larger context can help recall while also increasing token cost, distracting the answer model or admitting conflicting evidence. A high similarity score should therefore never be interpreted as the probability that a statement is factually true.

Earlier RV-035/RV-036 bilingual and retrieval measurements were recorded on a **different corpus snapshot**. They remain useful experiments, but their metrics must not be silently attributed to the cleaned RV-045 production demo.

## Answer Generation & Verification

### Structured Answer Decisions

The answer model receives the question, source context, document metadata and the evidence aliases. It classifies relevant passages and chooses a bounded action:

| Decision | Intended behavior |
|---|---|
| `answer` | Produce structured claims with citations |
| `retrieve` | Request one additional search when required evidence may be recoverable |
| `clarify` | Ask for a missing condition or user detail |
| `abstain` | Decline unsupported or out-of-scope conclusions |

The recovery path is allowed **at most once**. Generated claims must refer to aliases that actually appeared in the selected evidence, and Python removes or rejects unsupported citation structures.

### Independent Claim Review

A second model call checks submitted claims against the relevant supplied source context. The verification contract examines:

1. **Entailment:** does the cited material support the claim?
2. **Relevance:** does the claim answer the user's question?
3. **Preserved conditions:** are qualifiers, exceptions and negations respected?
4. **Material completeness:** is the answer missing a significant applicable requirement?

Python—not the model's free-form verdict—derives the final accepted claim set from those checks. Failed claims may be removed, and an answer judged incomplete can carry an explicit reservation.

**Verification limitation:** model-mediated claim review is valuable but not mathematical proof, independent ground truth or a substitute for human inspection.

### Response Outcomes

The UI may communicate an answer pending human review, an answer with reservations, clarification required, abstention, a rejected review, a budget limit or an execution failure.

The term *verified* in the UI refers to the implemented verification procedure and **does not constitute a certification of factual accuracy**.

## Ground Truth & Evaluation

Evaluation is part of the design, not a finishing task. The project maintains synthetic canonical facts, document identities, expected source relationships and question criteria separately from indexed enterprise content.

### RV-045 — Current MVP Validation

The clean-corpus checkpoint evaluated **46 cases** with `gpt-6.1-sol`, one execution per case.

| Measure | Recorded RV-045 result | Boundary |
|---|---:|---|
| Deterministic answer criteria | **45/46 passed (97.8%)** | Checks expected facts/patterns and source conditions |
| Strict semantic review | **40/46 approved (87.0%)** | Editorial review of saved outputs; not independent external certification |
| Cases with cited, reviewed answers | **38** | Includes model-mediated verification |
| Answers with reservations | **3** | Partial/supplementary conditions surfaced |
| Clarifications requested | **3** | Required context not supplied |
| Abstentions | **2** | No unsupported final answer |
| Execution failures | **0** | Single checkpoint; no stability guarantee |

**Known miss: Q20.** A multi-policy question about data sharing with carriers cited the Data Sharing Policy but missed the separately applicable Information Security Policy. This matters because correct individual citations do not automatically mean **complete multi-document coverage**.

The strict semantic audit reviewed saved answers against the normalized catalog. It did **not** independently inspect every original file, certify every alias cryptographically or run multiple statistical repeats.

Sources: [RV-045 report](docs/validation/RV045_LEAN_EVALUATION_RESULTS.json), [strict semantic audit](docs/validation/RV045_SEMANTIC_AUDIT_46_CASES.md) and [RV-044 answer criteria](docs/architecture/19_rv044_lean_v2_and_answer_criteria.md).

### Evaluation Dimensions

The longer-term evaluation model separates:

- Retrieval quality and ranked source coverage.
- Source authority, lifecycle and applicability.
- Evidence sufficiency and multi-document completeness.
- Claim grounding, factual correctness and citation integrity.
- Abstention/clarification behavior.
- Cost, latency, reproducibility and regression stability.

A successful API call, a passing regex assertion and a convincing answer are **three different kinds of evidence**. No single one establishes overall enterprise reliability.

## Governance, Traceability & Runtime Controls

The current application is governed by explicit code-level contracts rather than assuming a model's instructions will be followed.

| Control | Current behavior |
|---|---|
| Catalog identity | Snapshot and cached embeddings validated against canonical source identities |
| Citation integrity | Evidence aliases resolved to known, presented canonical units |
| Source scoping | Explicit document-ID restrictions applied to retrieval and recovery |
| Evidence threshold | No model-labelled direct evidence triggers refusal in the lean contract |
| Bounded execution | Restricted extra retrieval, model output size and deadline |
| Language | Target language checks and bounded repair when applicable |
| Budget | Per-question, per-session and in-process daily ceilings |
| Auditability | Source excerpts, document metadata, usage report and evaluation artifacts |
| CI discipline | Offline checks separated from paid LLM replay |

At the recorded RV-045 configuration, limits include **USD 0.30 per question**, **USD 0.50 per session** and **USD 1.00 per day for the current server process**. These are *estimated application controls*, not an OpenAI account-wide billing cap; the daily counter resets on process restart. The active configuration is [`config/lean_runtime.json`](config/lean_runtime.json).

### Security & Privacy Boundaries

This is a **demonstration environment**, not a corporate document platform. Its shared demo password does not implement identity-based roles, tenant isolation or per-document permissions. Uploads are session-local in application memory, and their textual contents are sent to the external model provider.

Do not submit passwords, internal contracts, personal data or confidential company information to this public demonstration.

## Technology Stack

| Component | Technology / Approach |
|---|---|
| Core language | Python |
| Web experience | Streamlit |
| Offline document ingestion | Docling, parser adapters |
| Office / XLSX handling | openpyxl and format-specific Python libraries |
| Canonical content | Typed application-owned schemas |
| Embedding model | OpenAI `text-embedding-3-small` |
| Vector retrieval | NumPy / cosine similarity |
| Lexical retrieval | BM25 with filtered bilingual queries |
| Fusion & selection | Adaptive fusion and bounded evidence assembly |
| AI generation | OpenAI structured-response contracts |
| Claim verification | Separate LLM review + Python-derived verdict |
| Testing / evaluation | pytest, YAML fixtures, deterministic checks and stored replays |
| Version control / CI | Git and GitHub Actions |
| Cloud deployment | Render, Streamlit and environment variables |

The codebase includes additional retrieval and orchestration components for experiments; their presence in the repository **does not imply use by the deployed path**.

## Project Structure

Simplified repository structure, emphasizing the active path:

~~~text
enterprise-knowledge-ai-system/
├── app/
│   ├── frontend/
│   │   ├── main.py                 # Streamlit experience
│   │   └── access.py               # Demo access boundary
│   ├── service/
│   │   ├── knowledge_service.py    # Catalog + scope + budgets
│   │   └── upload_reader.py        # In-memory upload parsing
│   ├── ingestion/                  # IngestionRouter + canonical parsing
│   ├── chunking/                   # Evidence units + verified snapshot
│   ├── retrieval/                  # Semantic, lexical, hybrid methods
│   ├── orchestration/
│   │   ├── lean_pipeline.py        # Active retrieve / answer / verify
│   │   ├── lean_live_provider.py   # Structured model integration
│   │   └── ...                     # Separate experimental pipelines
│   ├── evaluation/                 # Retrieval and answer evaluation
│   └── scripts/                    # Engineering and validation scripts
├── config/
│   └── lean_runtime.json
├── data/
│   ├── source/corporate_repository/
│   └── ground_truth/
├── docs/
│   ├── architecture/              # Current design and proposals
│   ├── validation/                # Corpus, benchmarks, audits
│   ├── images/                    # Product visuals and live demo
│   └── project_audit/
├── tests/
├── .github/workflows/ci.yml
├── render.yaml
├── requirements.txt
├── requirements-deploy.txt
└── README.md
~~~

Historical experimental paths are intentionally retained for traceability and future design comparisons.

## Getting Started — Local Development

### 1. Clone the Repository

~~~powershell
git clone https://github.com/RodsSoares/enterprise-knowledge-ai-system.git
cd enterprise-knowledge-ai-system
~~~

### 2. Create and Activate a Virtual Environment

~~~powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
~~~

### 3. Install Dependencies

~~~powershell
python -m pip install -r requirements.txt
~~~

For deployment, a separately maintained `requirements-deploy.txt` provides the lean production dependency set.

### 4. Configure Model Access

In the active terminal session, configure your own API key:

~~~powershell
$env:OPENAI_API_KEY = "your-openai-api-key"
~~~

Never commit secrets into the repository. The model names, budgets, corpus snapshot paths and provider-price assumptions are declared in [`config/lean_runtime.json`](config/lean_runtime.json).

### 5. Start the Web Application

~~~powershell
streamlit run app/frontend/main.py
~~~

The service loads and verifies the checked-in corpus snapshot and embeddings. To run against a changed corpus, rebuild its artifacts through the dedicated validation pipeline; do not manually replace a snapshot without its matching vectors.

### 6. Run the Tests

~~~powershell
python -m pytest -q
~~~

### 7. Deploy and Operate

The Render blueprint in [`render.yaml`](render.yaml) runs the Streamlit entry point from `main`. Secrets are configured through the Render dashboard and deployment is manual, not automatic on every push. See [deployment documentation](docs/validation/RENDER_MVP_DEPLOYMENT.md) for operational caveats.

## Automated Tests & CI

The automated test suite covers modules across ingestion, structure-preserving normalization, chunking, indexing, retrieval, answer contracts, orchestration and service integration.

The GitHub Actions workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on pushes and pull requests to `main`. It executes:

1. Offline unit/integration tests with pinned dependencies.
2. Frontend syntax and Render manifest checks.
3. A scan for evaluation-harness leakage in the indexed corpus.
4. Structural validation of the **archived** 46-case RV-045 evaluation results.

**CI does not execute 46 paid OpenAI model calls on each commit.** A green CI run confirms the configured offline checks, not complete live-model semantic reliability.

The historical README and validation records contain earlier full-suite numbers from local development. Those results are useful checkpoints but are **not promoted here as a freshly rerun test total**.

### Validation Discipline

~~~text
Implement / Refactor
       ↓
Unit Tests
       ↓
Integration & Contract Tests
       ↓
Source / Evidence Audits
       ↓
Recorded Model Evaluation (when needed)
       ↓
Review Regressions and Known Gaps
       ↓
Documentation + Commit
~~~

The objective is not merely to execute a pipeline. Each increment should improve the ability to retrieve, preserve, assess and explain enterprise evidence reliably.

## Engineering Practices

The implementation follows several recurring engineering decisions:

- **Layered responsibilities:** parsing, retrieval, generation, verification, evaluation and experience stay separable.
- **Explicit contracts:** source identity, citation aliases, model decisions and budgets are validated.
- **Deterministic first:** use Python for checks expressible as rules and LLM reasoning for interpretation.
- **Versioned evidence:** immutable snapshots and matching embeddings support reproducibility.
- **Bounded context and cost:** avoid uncontrolled searches, overlong evidence packages and unbudgeted calls.
- **Testable interfaces:** fake or offline providers support repeatable regression without paid inference.
- **Negative-case evaluation:** clarifications, abstentions and omissions matter as much as answered cases.
- **Architecture honesty:** distinguish implemented production-path features from separate experimental assets.
- **Documentation as evidence:** preserve decisions, measurements, methodology and limitations.

The architecture is designed to evolve without treating every new research component as a mandatory dependency of the running MVP.

## Roadmap & Current Development Stage

### Current Development Stage

**Delivered:** a functioning Streamlit Lean RAG MVP built on the cleaned RV-045 corpus, with hybrid retrieval, citable evidence, controlled answer generation, independent review, usage guardrails and a deployed demo.

**Not yet delivered:** a production enterprise platform with robust authorization, per-document ACL, permanent multi-user storage, service API, audit-grade logging and formal acceptance by business owners.

### Next Engineering Increments

| Priority | Increment | Acceptance concern |
|---|---|---|
| 1 | Q20 multi-policy completeness | Cite all materially applicable policies without irrelevant additions |
| 2 | Human/semantic answer audit | Confirm entailment, negation, exceptions and real source applicability |
| 3 | Retrieval stability and coverage | Hold-out and repeat-run tests, not only one saved case execution |
| 4 | Source fidelity | Improve granularity of PPTX and complex document evidence |
| 5 | Runtime observability and hardening | Better metrics, cost controls, upload validation and operational reliability |
| 6 | Advanced evidence assurance | Promote research only after scoped, independent evaluations |
| 7 | Enterprise capabilities | SSO, authorization, persistence and API, subject to demonstrated need |

Earlier Stage-1 orchestration, Evidence Assurance, v3/v4.2 and specialized reranking are valuable engineering explorations. They are **candidate future capabilities**, not claims about the current Streamlit request lifecycle.

## Documentation & Engineering History

The repository deliberately retains deeper technical material instead of flattening the entire development history into the portfolio entry point.

| Document | What it contains |
|---|---|
| [Current Lean MVP Architecture](docs/architecture/21_current_lean_mvp_architecture.md) | Authoritative implementation, sequence, contracts and risk boundaries |
| [RV-045 Clean Corpus & MVP Interface](docs/architecture/20_rv045_clean_corpus_and_mvp_interface.md) | Corpus revision and current checkpoint |
| [RV-044 Lean v2 & Answer Criteria](docs/architecture/19_rv044_lean_v2_and_answer_criteria.md) | Claim validation and answer-quality experiments |
| [RV-045 Semantic Audit](docs/validation/RV045_SEMANTIC_AUDIT_46_CASES.md) | Case-by-case review and limitations |
| [Retrieval Validation](docs/validation/RETRIEVAL_VALIDATION.md) | Historical retrieval runs, rankings and anomalies |
| [Render MVP Deployment](docs/validation/RENDER_MVP_DEPLOYMENT.md) | Deployment, credentials and runtime behavior |
| [Full Historical README](README_ENGINEERING_HISTORY.md) | Original long-form narrative, experimental results and earlier proposals |
| [Architecture Research](docs/architecture/) | Prior iterations, evidence-planning proposals and diagnostics |

The older material is retained for audit and learning, but **new readers should start with the implemented MVP specification**.

## Why This Project?

A useful enterprise AI system must do more than produce fluent text. It must handle heterogeneous source formats, preserve traceability, expose uncertainty, distinguish document lifecycle, bound resource use and maintain explicit testable decision boundaries.

This project demonstrates a progression from document ingestion and retrieval benchmarks toward a **working, evaluated knowledge application**. Its differentiated engineering objective is to connect document intelligence, hybrid search, structured generation, deterministic safeguards and claim-level review into a coherent, inspectable system.

### Other Projects in the AI Portfolio

- [AI Supply Chain Copilot](https://github.com/RodsSoares/ai-supply-chain-copilot) — multi-domain Decision Intelligence for Inventory and Transportation.
- [My LinkedIn Agentic AI System](https://github.com/RodsSoares/linkedin-agentic-ai-system) — human-centered agentic opportunity intelligence, research, writing and quality workflows.

The three projects demonstrate complementary designs: **operational decision intelligence**, **human-centered agentic orchestration** and **enterprise evidence-grounded knowledge access**.

## License

This repository is presented for educational, software-engineering and portfolio purposes. The enterprise documents and business scenarios are **synthetic or fictional**, and should not be interpreted as executed contracts, binding policies or legal advice.

The repository does not imply production certification, guaranteed factual accuracy, enterprise-wide authorization, or commercial licensing rights that have not been explicitly granted.
