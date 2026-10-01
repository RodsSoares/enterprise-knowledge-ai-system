# Enterprise Knowledge AI System

An Enterprise RAG system designed to transform heterogeneous and
fragmented corporate knowledge into a trustworthy and searchable
enterprise intelligence layer.

## Objective

Organizations store critical knowledge across policies, procedures,
contracts, spreadsheets, presentations, incident reports, meeting
minutes, and other disconnected sources.

The Enterprise Knowledge AI System is designed to ingest, organize,
retrieve, and synthesize this knowledge while preserving source
traceability, document authority, versioning, and evidence.

The system should answer enterprise questions based on available
organizational knowledge rather than relying on unsupported model
knowledge.

## Core Principles

-   Evidence before generation
-   Retrieval quality before answer fluency
-   Source traceability
-   Document authority and version awareness
-   Explicit handling of insufficient evidence
-   Deterministic controls where appropriate
-   AI where semantic interpretation adds value
-   Evaluation as part of the architecture

## Initial Scope

The first version will use a controlled synthetic enterprise corpus
containing heterogeneous corporate information across multiple formats,
including:

-   PDF
-   DOCX
-   XLSX
-   PPTX
-   Markdown / text

The corpus will include policies, SOPs, contracts, KPI definitions,
approval matrices, incident reports, meeting minutes, action trackers,
governance documents, and AI-related corporate documentation.

## Target Architecture

``` text
Enterprise Sources
        ↓
Multi-format Ingestion
        ↓
Parsing & Normalization
        ↓
Metadata Extraction
        ↓
Chunking
        ↓
Embeddings & Indexing
        ↓
Hybrid Retrieval
(Vector + Lexical + Metadata)
        ↓
Candidate Fusion
        ↓
Reranking
        ↓
Context Assembly
        ↓
Grounded Generation
        ↓
Citation & Evidence Validation
        ↓
Final Answer / Abstention
```

## Retrieval Strategy

The system will explore retrieval beyond pure vector similarity.

The target architecture combines:

-   Semantic vector retrieval
-   Lexical retrieval
-   Metadata filtering
-   Candidate fusion
-   Reranking

This allows the system to distinguish semantic similarity from actual
contextual relevance.

For example, many corporate documents may contain the term "AI", while
only a subset may be relevant to a question involving AI, confidential
supplier information, contracts, security, or approval authority.

## Ground Truth and Evaluation

The project will use a controlled ground-truth dataset containing:

-   Canonical enterprise facts
-   Document registry
-   Golden question set
-   Expected evidence
-   Relevant source documents
-   Plausible distractor documents
-   Expected system behavior

Evaluation will distinguish between:

1.  Retrieval quality --- whether the system found the correct evidence.
2.  Generation quality --- whether the answer is correctly grounded in
    that evidence.

The system must also support cases where the correct behavior is to
abstain because sufficient evidence does not exist in the enterprise
corpus.

## Project Status

**Status:** Architecture and dataset design

Current focus:

1.  System architecture
2.  Synthetic enterprise corpus design
3.  Ground-truth specification
4.  Retrieval and evaluation strategy

Implementation choices such as embedding models, vector storage, parsing
libraries, reranking models, and orchestration frameworks remain
intentionally open.
