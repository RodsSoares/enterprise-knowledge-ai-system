# Retrieval Validation Log

Persistent validation record for the **Enterprise Knowledge AI System**
retrieval layer.

This document records meaningful retrieval experiments, observed
results, and architectural findings. It is intentionally separate from
the automatically generated `PROJECT_AUDIT.md`.

------------------------------------------------------------------------

## RV-001 --- Real Vector Retrieval / DOC-005

**Date:** 2026-10-08\
**Status:** PASS\
**Validation type:** Live smoke test / single-document semantic
retrieval

### Objective

Validate the first real end-to-end vector retrieval flow using an
enterprise corpus document, real parsing and normalization,
structure-aware chunking, real OpenAI embeddings, an exact
cosine-similarity vector index, and semantic retrieval.

### Source document

`data/source/corporate_repository/policies/DOC-005_Data_Sharing_Policy.pdf`

### Query

> What rules apply when confidential information is shared externally?

The query was intentionally phrased as a semantic question rather than
copied directly from a document section title.

### Pipeline

``` text
DOC-005 PDF
    ↓
DoclingParser
    ↓
Canonical Normalization
    ↓
20 Canonical Blocks
    ↓
StructureAwareChunker
    ↓
10 RetrievalChunks
    ↓
build_search_text()
    ↓
OpenAIEmbeddingProvider
    ↓
text-embedding-3-small
    ↓
NumPyVectorIndex
    ↓
Query Embedding
    ↓
Cosine Similarity
    ↓
Top-5 RetrievalCandidates
```

### Configuration

  Parameter              Value
  ---------------------- --------------------------
  Embedding provider     OpenAI
  Embedding model        `text-embedding-3-small`
  Embedding dimensions   1536
  Vector index           `NumPyVectorIndex`
  Similarity             Cosine similarity
  `top_k`                5
  Chunk target size      1200 characters
  Chunk maximum size     1800 characters
  Canonical blocks       20
  Retrieval chunks       10

### Retrieval results

  -------------------------------------------------------------------------------------
              Rank            Score Chunk           Section          Assessment
  ---------------- ---------------- --------------- ---------------- ------------------
                 1         0.584809 `chunk-00006`   5\. Approved     Primary
                                                    channels         substantive
                                                                     evidence

                 2         0.571160 `chunk-00005`   4\. Sharing with Relevant
                                                    transportation   complementary
                                                    carriers         evidence

                 3         0.550386 `chunk-00003`   2\. Scope        Contextual
                                                                     evidence

                 4         0.535726 `chunk-00002`   1\. Purpose      Contextual
                                                                     evidence

                 5         0.527767 `chunk-00001`   DATA SHARING     Document-level
                                                    POLICY           metadata/context
  -------------------------------------------------------------------------------------

### Top evidence

**Rank 1 --- Section 5. Approved channels**

> Confidential information shared externally must use an approved secure
> channel or controlled platform appropriate to the information
> classification. Corporate email alone does not convert an otherwise
> unapproved transfer into an approved secure transfer.

**Rank 2 --- Section 4. Sharing with transportation carriers**

> Transportation carriers may receive only the information required to
> execute the contracted logistics service. Customer or shipment data
> classified as confidential must not be transmitted through ordinary
> unprotected email merely because the recipient is a contracted
> carrier.

### Assessment

**PASS.**

The vector retrieval pipeline correctly ranked substantive policy
evidence above scope, purpose, and document-level metadata.

The highest-ranked chunk directly addresses the rules for externally
sharing confidential information. The second-ranked chunk provides a
more specific application of the same policy concept to transportation
carriers.

This result validates the technical flow:

-   real enterprise PDF parsing and canonical normalization;
-   structure-aware chunk creation;
-   real OpenAI embedding generation;
-   vector indexing with normalized embeddings;
-   query embedding;
-   exact cosine-similarity search;
-   conversion of vector hits into ranked `RetrievalCandidate` objects.

The cosine scores are similarity values used for ranking and **must not
be interpreted as percentages of relevance**.

### Architectural finding

The experiment used a single document and therefore did not expose
cross-document identifier collisions during execution. However, the
current chunk identifiers are document-local, for example:

``` text
chunk-00001
chunk-00002
...
```

Indexing multiple independently chunked documents can therefore produce
duplicate `chunk_id` values.

**Required before multi-document vector indexing:** define a globally
unique retrieval-chunk identity strategy while preserving document
provenance.

### Next validation

**RV-002 --- Multi-document Vector Retrieval**

Prerequisites:

1.  Define and test global chunk identity.
2.  Build retrieval chunks across multiple corpus documents.
3.  Index the resulting multi-document corpus.
4.  Execute semantic queries where relevant and distracting documents
    compete for ranking.
5.  Evaluate whether the correct document and evidence are recovered in
    the Top-K.

------------------------------------------------------------------------

## Validation principles

-   Smoke-test success alone is not treated as retrieval quality
    evidence; ranked evidence must be inspected.
-   Raw cosine similarity is not a relevance percentage.
-   Retrieval quality will later be evaluated systematically against
    `golden_questions.yaml`.
-   Retrieval evaluation and generation evaluation remain separate
    concerns.
-   Future retrieval baselines should preserve enough configuration and
    result detail to support comparison across vector, lexical, hybrid,
    fusion, and reranking strategies.
