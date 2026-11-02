Retrieval Validation Log
Persistent validation record for the Enterprise Knowledge AI System
retrieval layer.

This document records meaningful retrieval experiments, observed
results, and architectural findings. It is intentionally separate from
the automatically generated PROJECT_AUDIT.md.
RV-001 --- Real Vector Retrieval / DOC-005
Date: 2026-10-08
Status: PASS
Validation type: Live smoke test / single-document semantic
retrieval
Objective
Validate the first real end-to-end vector retrieval flow using an
enterprise corpus document, real parsing and normalization,
structure-aware chunking, real OpenAI embeddings, an exact
cosine-similarity vector index, and semantic retrieval.
Source document
data/source/corporate_repository/policies/DOC-005_Data_Sharing_Policy.pdf
Query
What rules apply when confidential information is shared externally?

The query was intentionally phrased as a semantic question rather than
copied directly from a document section title.
Pipeline
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
Configuration
  Parameter              Value
  Embedding provider     OpenAI
Embedding model        text-embedding-3-small
Embedding dimensions   1536
Vector index           NumPyVectorIndex
Similarity             Cosine similarity
top_k                5
Chunk target size      1200 characters
Chunk maximum size     1800 characters
Canonical blocks       20
Retrieval chunks       10
Retrieval results
          Rank            Score Chunk           Section          Assessment

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

Top evidence
Rank 1 --- Section 5. Approved channels
Confidential information shared externally must use an approved secure
channel or controlled platform appropriate to the information
classification. Corporate email alone does not convert an otherwise
unapproved transfer into an approved secure transfer.

Rank 2 --- Section 4. Sharing with transportation carriers
Transportation carriers may receive only the information required to
execute the contracted logistics service. Customer or shipment data
classified as confidential must not be transmitted through ordinary
unprotected email merely because the recipient is a contracted
carrier.

Assessment
PASS.

The vector retrieval pipeline correctly ranked substantive policy
evidence above scope, purpose, and document-level metadata.

The highest-ranked chunk directly addresses the rules for externally
sharing confidential information. The second-ranked chunk provides a
more specific application of the same policy concept to transportation
carriers.

This result validates the technical flow:
- real enterprise PDF parsing and canonical normalization;
- structure-aware chunk creation;
- real OpenAI embedding generation;
- vector indexing with normalized embeddings;
- query embedding;
- exact cosine-similarity search;
- conversion of vector hits into ranked RetrievalCandidate objects.
The cosine scores are similarity values used for ranking and must not
be interpreted as percentages of relevance.
Architectural finding
The experiment used a single document and therefore did not expose
cross-document identifier collisions during execution. However, the
current chunk identifiers are document-local, for example:
chunk-00001
chunk-00002
...
Indexing multiple independently chunked documents can therefore produce
duplicate chunk_id values.

Required before multi-document vector indexing: define a globally
unique retrieval-chunk identity strategy while preserving document
provenance.
Next validation
RV-002 --- Multi-document Vector Retrieval

Prerequisites:
1. Define and test global chunk identity.
2. Build retrieval chunks across multiple corpus documents.
3. Index the resulting multi-document corpus.
4. Execute semantic queries where relevant and distracting documents
   compete for ranking.
5. Evaluate whether the correct document and evidence are recovered in
   the Top-K.
RV-002 --- Multi-document Vector Retrieval
Date: 2026-11-01
Status: PASS
Validation type: Live smoke test / multi-document vector-only retrieval
Objective
Validate shared vector retrieval across multiple competing enterprise
documents after introducing globally unique retrieval-chunk identity.
Corpus and identity
Five enterprise PDF documents were parsed, normalized, chunked, embedded, and
indexed in a shared vector index:
- DOC-005 — Data Sharing Policy
- DOC-006 — Information Security Policy
- DOC-022 — Supplier Management Policy
- DOC-023 — AI Governance Policy
- DOC-024 — AI Security Standard
The corpus produced 48 RetrievalChunks, and global chunk identity was
validated with 48/48 unique IDs using document-scoped identifiers such as:
DOC-005::chunk-00001
DOC-006::chunk-00001
Evaluation
Five semantic queries were executed with relevant and distracting documents
competing in the same vector index.
Metric	Result
Hit@1	80.0%
Hit@3	100.0%
Hit@5	100.0%
MRR	0.8667


Assessment
PASS.

The experiment demonstrated that:
- globally unique chunk identity works across documents;
- multiple enterprise documents can share one vector index safely;
- relevant evidence is consistently discovered within Top-3;
- vector-only retrieval provides a measurable baseline before hybrid retrieval.
RV-002 is retained as the smaller multi-document vector-only baseline. It
should not be overwritten by later, harder Golden Set experiments.
Next validation
RV-003 --- Golden Set A / Multi-Format Vector Retrieval Baseline

Expand evaluation to the complete currently materialized corpus, route
heterogeneous formats through the common ingestion boundary, and evaluate
retrieval systematically against corpus-eligible Golden Set questions.
RV-003 --- Golden Set A / Multi-Format Vector Retrieval Baseline
Date: 2026-11-01
Status: COMPLETE / BASELINE RECORDED
Validation type: Live Golden Set benchmark / multi-format,
multi-document vector-only retrieval
Objective
Establish the first systematic retrieval-quality baseline against Golden Set A
using the complete currently materialized enterprise corpus.

The experiment intentionally measures the existing vector-only retrieval
stack before introducing BM25, metadata-aware retrieval, candidate fusion, or
reranking.
Corpus
The benchmark materialized 10 enterprise documents spanning five source
formats:
- PDF
- DOCX
- XLSX
- PPTX
- Markdown
Format-specific parser selection was hidden behind the ingestion boundary, and
all sources were normalized into the canonical content model before chunking.
Chunking and global identity
The complete corpus produced:
- 79 RetrievalChunks
- 10 represented documents
- 79/79 globally unique chunk IDs
- global chunk identity validation: PASS
The multi-format chunking path included spreadsheet evidence from DOC-012
and presentation evidence from DOC-026.
Golden Set scope
Golden Set A contains 36 questions.

For the current materialized corpus:
Scope	Count
Golden Set questions	36
Corpus-eligible questions	14
Positive retrieval questions scored	13
Deferred eligible non-positive questions	1
Blocked / deferred total	23


Q29 is intentionally deferred from positive retrieval scoring because the
corpus contains no positive expected evidence for that question. It belongs to
the later answer/abstention evaluation layer.
Configuration
Parameter	Value
Embedding provider	OpenAI
Embedding model	text-embedding-3-small
Embedding dimensions	1536
Vector index	NumPyVectorIndex
Similarity	Cosine similarity
Retrieval depth	Top-5 chunks
Chunk target size	1200 characters
Chunk maximum size	1800 characters
Retrieval strategy	Vector-only


Aggregate results
Metric	Result
Hit@1	76.9%
Hit@3	100.0%
Hit@5	100.0%
Recall@1	43.6%
Recall@3	87.2%
Recall@5	92.3%
MRR	0.8846


Per-question results
QID	Expected documents	Hit@1	Hit@3	Hit@5	R@1	R@3	R@5	RR
Q05	DOC-012	0	1	1	0.00	1.00	1.00	0.500
Q20	DOC-005, DOC-006	1	1	1	0.50	0.50	0.50	1.000
Q21	DOC-006	0	1	1	0.00	1.00	1.00	0.500
Q22	DOC-005, DOC-006	1	1	1	0.50	1.00	1.00	1.000
Q23	DOC-010	1	1	1	1.00	1.00	1.00	1.000
Q25	DOC-007	0	1	1	0.00	1.00	1.00	0.500
Q26	DOC-022	1	1	1	1.00	1.00	1.00	1.000
Q31	DOC-023, DOC-024	1	1	1	0.50	1.00	1.00	1.000
Q32	DOC-023, DOC-005, DOC-012	1	1	1	0.33	0.67	1.00	1.000
Q33	DOC-024, DOC-006	1	1	1	0.50	1.00	1.00	1.000
Q34	DOC-023, DOC-012	1	1	1	0.50	0.50	0.50	1.000
Q35	DOC-023, DOC-024, DOC-006	1	1	1	0.33	0.67	1.00	1.000
Q36	DOC-026, DOC-023	1	1	1	0.50	1.00	1.00	1.000


Ranking findings
The three Hit@1 misses were all near misses:
- Q05: expected DOC-012, recovered at rank 2;
- Q21: expected DOC-006, recovered at rank 2;
- Q25: expected DOC-007, recovered at rank 2.
This indicates that the principal near-term weakness is ranking quality rather
than basic candidate discovery.

Two multi-document questions also expose remaining recall opportunities:
- Q20: DOC-005 was recovered, while expected DOC-006 did not appear in
  Top-5;
- Q34: DOC-023 was recovered, while expected DOC-012 did not appear in
  Top-5.
Architectural findings
RV-003 validates the following capabilities together:
- format-agnostic ingestion across the current five materialized formats;
- canonical normalization of heterogeneous enterprise sources;
- multi-block structure-aware chunking, including spreadsheet evidence;
- global multi-document chunk identity;
- shared real-embedding vector indexing;
- Golden Set-driven corpus eligibility classification;
- deterministic retrieval metrics;
- separation of positive retrieval evaluation from abstention evaluation.
The vector-only baseline demonstrates strong candidate discovery:
Hit@3 and Hit@5 are both 100%. The lower Hit@1 and incomplete multi-document
Recall@5 provide a concrete reason to evolve ranking rather than changing the
ingestion foundation without evidence.
Baseline decision
This experiment is now the frozen Golden Set A vector-only baseline.

Future retrieval strategies should be compared against:
Hit@1     76.9%
Hit@3    100.0%
Hit@5    100.0%
Recall@1  43.6%
Recall@3  87.2%
Recall@5  92.3%
MRR        0.8846
The next retrieval increment should improve ranking and expected-document
coverage without regressing the already validated Top-3 discovery behavior.
Next retrieval increment
Retrieval v0.2 --- Hybrid Retrieval & Candidate Fusion

Planned direction:
Query
 ├── Vector Retrieval
 └── Lexical / BM25 Retrieval
          ↓
    Candidate Fusion
          ↓
       Reranking
          ↓
      Final Top-K
Initial comparison targets:
1. improve Hit@1 beyond 76.9%;
2. preserve 100% Hit@3;
3. improve Recall@5 beyond 92.3%;
4. improve MRR beyond 0.8846;
5. preserve global identity, provenance, and multi-format behavior.
Validation principles
- Smoke-test success alone is not treated as retrieval quality
  evidence; ranked evidence must be inspected.
- Raw cosine similarity is not a relevance percentage.
- Retrieval quality is evaluated systematically against corpus-eligible
  questions from golden_questions.yaml.
- Retrieval evaluation and generation evaluation remain separate
  concerns.
- Future retrieval baselines should preserve enough configuration and
  result detail to support comparison across vector, lexical, hybrid,
  fusion, and reranking strategies.