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
Retrieval v0.2–v0.3 — Hybrid Retrieval and Document-Aware Selection
RV-004 — Golden Set A / Hybrid Retrieval Baseline
Date: 2026-11-04
Status: COMPLETE / BASELINE RECORDED
Validation type: Paired live Golden Set comparison (vector-only vs hybrid)
Objective and configuration
Compare vector-only retrieval against hybrid retrieval on the same materialized corpus and Golden Set questions, without changing the vector baseline. The hybrid path uses VectorRetriever, LexicalRetriever backed by BM25LexicalIndex, and ReciprocalRankFusion (RRF).
- Corpus: 10 documents, five formats, 79 globally unique retrieval chunks.
- Positive Golden Set A questions: 13 (Q05, Q20–Q23, Q25–Q26, Q31–Q36).
- Vector branch: OpenAI text-embedding-3-small (1536 dimensions), exact cosine similarity.
- Lexical branch: BM25 on indexed chunk search text.
- Candidate depth: Top-20 per retrieval branch.
- Fusion: RRF with k=60.
- Final evaluation depth: Top-5 chunks.
- Positive document-level retrieval metrics only; Q29 abstention case excluded.
Aggregate results
Metric	Vector-only	Hybrid PT
Hit@1	76.9%	76.9%
Hit@3	100.0%	100.0%
Hit@5	100.0%	100.0%
Recall@1	43.6%	43.6%
Recall@3	87.2%	87.2%
Recall@5	92.3%	92.3%
MRR	0.8846	0.8846


The aggregate metrics were unchanged. The first expected-document rank improved for Q25 (rank 2 to 1) and worsened for Q26 (rank 1 to 2), illustrating that rank fusion can help some queries and hurt others. Q20 still missed DOC-006 in Top-5; Q34 still missed DOC-012.

Decision: Do not claim hybrid superiority from the RV-004 metrics. Diagnose candidate coverage and final selection before tuning RRF or introducing a reranker.
RV-005 — Retrieval Candidate Diagnostics
Date: 2026-11-04
Status: COMPLETE / DIAGNOSTIC
Validation type: Per-chunk Vector@20, BM25@20, RRF@20, and final RRF@5 inspection

Four targeted queries were examined: Q20, Q26, Q32, Q34.
Question	Expected evidence	Vector first relevant chunk position(s)	BM25 PT candidates	Final Top-5 issue
Q20	DOC-005, DOC-006	1, 7	0	DOC-006 excluded
Q26	DOC-022	1	18	RRF promoted DOC-010 ahead of DOC-022
Q32	DOC-023, DOC-005, DOC-012	1, 4, 5	0	All expected documents present
Q34	DOC-023, DOC-012	1, 9	0	DOC-012 excluded


All expected documents appeared in at least one Top-20 candidate pool. Therefore, the two missing-document cases were final-selection problems, not total candidate-discovery failures.

The BM25 branch returned zero candidates for three of the four examined Portuguese-language queries, motivating a controlled language-alignment experiment. On Q20, four of five final chunks came from DOC-005; repeated chunks from the same document consumed slots that could have represented complementary evidence.

Decision: Evaluate language alignment and document-aware final selection independently.
RV-006A — BM25 Language Alignment Experiment
Date: 2026-11-04
Status: COMPLETE / EXPERIMENTAL
Validation type: Same-corpus, same-question comparison with fixed English query translations

Three strategies were compared: vector-only (original Portuguese questions), Hybrid PT (Portuguese BM25 queries), and Hybrid EN-BM25 (Portuguese vector queries plus manually fixed English translations for the lexical branch). No runtime translation service or LLM-based translation was introduced.

BM25 returned at least one candidate for 2/13 Portuguese queries versus 13/13 English translations. This confirms a substantial lexical query/corpus language mismatch in the tested setup, but not an end-to-end quality improvement.
Metric	Vector-only	Hybrid PT	Hybrid EN-BM25
Hit@1	76.9%	76.9%	76.9%
Hit@3	100.0%	100.0%	100.0%
Hit@5	100.0%	100.0%	100.0%
Recall@1	43.6%	43.6%	43.6%
Recall@3	87.2%	87.2%	85.9%
Recall@5	92.3%	92.3%	92.3%
MRR	0.8846	0.8846	0.8846


Decision: Do not integrate translation into the production retrieval path based solely on increased BM25 candidate counts. Preserve this experiment as evidence that lexical coverage and final evidence quality are different properties.
RV-006B — Document Diversity Selection Experiment
Date: 2026-11-04
Status: COMPLETE / EXPERIMENTAL SUCCESS
Validation type: Five-strategy comparison with document-aware Top-5 selection

A document-aware selection strategy was applied after RRF over a wider candidate pool. It preserves the highest-ranked candidate, then prioritizes previously unrepresented documents in original ranking order, and finally fills any remaining positions from the best unselected chunks. This approach retains a five-chunk output while reducing repeated-document concentration.

Compared strategies: Vector-only, Hybrid PT, Hybrid PT + Diversity, Hybrid EN-BM25, Hybrid EN-BM25 + Diversity.
Metric	Hybrid PT	Hybrid PT + Diversity	Hybrid EN-BM25	Hybrid EN-BM25 + Diversity
Hit@1	76.9%	76.9%	76.9%	76.9%
Hit@3	100.0%	100.0%	100.0%	100.0%
Hit@5	100.0%	100.0%	100.0%	100.0%
Recall@1	43.6%	43.6%	43.6%	43.6%
Recall@3	87.2%	87.2%	85.9%	89.7%
Recall@5	92.3%	100.0%	92.3%	100.0%
MRR	0.8846	0.8846	0.8846	0.8846


Document diversity recovered both missing expected-document cases:
- Q20: DOC-006 entered the final Top-5 alongside DOC-005.
- Q34: DOC-012 entered the final Top-5 alongside DOC-023.
For both language variants, Recall@5 improved by approximately 7.69 percentage points without observed regressions in Hit@1, Hit@3, Hit@5, or MRR on the tested set. The English variant improved Recall@3 relative to Hybrid EN-BM25 but was not needed to achieve full Recall@5.

Decision: Prefer Hybrid PT + Diversity as the integration candidate: it reaches the measured objective without introducing a translation dependency. The experiment does not establish that one chunk per document is always sufficient for answering questions.
RV-007 — Hybrid Retrieval v0.3 End-to-End Validation
Date: 2026-11-04
Status: PASS
Validation type: Integrated smoke benchmark, Golden Set A positive retrieval
Implementation under test
- app/retrieval/document_diversifier.py: independent DocumentDiversifier for document-aware selection.
- app/retrieval/hybrid_retriever.py: optional document-diversifier integration; original behavior remains available when disabled.
- tests/unit/test_document_diversifier.py: unit coverage for selection behavior.
- tests/smoke/smoke_hybrid_v03_end_to_end.py: integrated benchmark and backward-compatibility check.
The user reported 379 tests passed, 4 warnings in 56.18 seconds in the full suite before the RV-007 smoke run. The warnings were not individually classified. The integrated smoke then completed with RV-007: PASS.
Corpus and scope
- 10 materialized documents in PDF, DOCX, XLSX, PPTX, and Markdown.
- 79 retrieval chunks; global identity 79/79 PASS.
- 13 positive Golden Set A questions; Q29 abstention intentionally not scored.
- Top-5 chunk retrieval, with document-level expected-evidence evaluation.
- Paired comparisons: Vector-only, Hybrid v0.2-compatible, Hybrid v0.3 + Diversity.
Final results
Metric	Vector-only	Hybrid v0.2-compatible	Hybrid v0.3 + Diversity	Change vs v0.2
Hit@1	76.9%	76.9%	76.9%	0 pp
Hit@3	100.0%	100.0%	100.0%	0 pp
Hit@5	100.0%	100.0%	100.0%	0 pp
Recall@1	43.6%	43.6%	43.6%	0 pp
Recall@3	87.2%	87.2%	87.2%	0 pp
Recall@5	92.3%	92.3%	100.0%	+7.69 pp
MRR	0.8846	0.8846	0.8846	0.0000


The integrated run reproduced the RV-006B document-coverage improvement. The non-diversified hybrid path preserved the previously measured v0.2 metrics. Q20 and Q34 recovered the expected additional documents in the diversified final Top-5.
Assessment and limitations
PASS — Integrated Hybrid Retrieval v0.3 positive document-level benchmark.

The 100% Recall@5 result means all expected document IDs appeared among the final five chunks for these 13 positive Golden Set A questions. It is not a claim of 100% answer accuracy, passage sufficiency, citation correctness, source authority, or generalization to larger corpora.

Remaining limitations and validation requirements:
1. Passage-level relevance: document-level matches do not prove that the selected chunk contains the exact passage needed for a grounded answer.
2. Multi-chunk evidence: diversification may displace complementary chunks from the same source; assess questions requiring multiple passages per document.
3. Corpus and sample size: 10 documents and 13 positive questions are insufficient for general performance guarantees.
4. Abstention: Q29 and other no-answer cases require a separate negative/abstention evaluation.
5. Governance: document versions, effective dates, source authority, supersession, and conflicting policies are not validated by these ranking metrics.
6. Generation: factual accuracy, citations, and compliance remain outside the scope of RV-007.
7. Warnings: four full-suite warnings should be inspected and classified before release hardening.
Architecture decision and next milestone
Retain Hybrid PT + optional DocumentDiversifier as the v0.3 candidate configuration, with backward compatibility preserved. Record the RV-003 vector-only baseline unchanged; do not retroactively rewrite earlier measurements.

Next: complete documentation/audit updates and a final test/commit checkpoint, then evaluate a Reranking Layer using the frozen baselines. Reranking should target better first-position quality (Hit@1, MRR) and passage relevance without regressing the demonstrated document-level Recall@5. Answer grounding, citation validation, evidence freshness/authority, and abstention remain separate subsequent evaluation stages.