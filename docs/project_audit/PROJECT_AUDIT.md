# PROJECT AUDIT — Enterprise Knowledge AI System

Version: 1.0
Generated: 2026-11-06 17:46:46

> This file is generated automatically by `app/scripts/project_audit.py`.
> Do not edit it manually.

## 1. Snapshot Integrity

```text
PASS

- HEAD before: 17e5bc0
- HEAD after: 17e5bc0
- Fingerprint before: 08cf02a4ed1255328c148b99c59e8a72ad2687e5181fe3851b7f8c4eb7174ef7
- Fingerprint after: 08cf02a4ed1255328c148b99c59e8a72ad2687e5181fe3851b7f8c4eb7174ef7
- Repository content remained stable during audit collection.
```

- Audit started: 2026-11-06 17:45:08
- Audit finished: 2026-11-06 17:46:46
- Duration: 97.98 seconds

## 2. Environment

- Python: 3.14.6
- Executable: `C:\Users\rods_\Desktop\AI - LAB\enterprise-knowledge-ai-system\.venv\Scripts\python.exe`
- Platform: Windows-10-10.0.19045-SP0

## 3. Git State

- Branch: `main`
- Commit: `17e5bc0`

### Status

```text
?? app/retrieval/cross_encoder_scorer.py
?? app/retrieval/lexical_query_filter.py
?? app/retrieval/prefix_preserving_selector.py
?? app/retrieval/reranker.py
?? data/ground_truth/reranking_challenge_b.json
?? docs/validation/RV008_IMPLEMENTATION_GUIDE.md
?? docs/validation/RV008_RESULTS.json
?? docs/validation/RV009_ANALYSIS.md
?? docs/validation/RV009_REPLAY_RESULTS.json
?? docs/validation/RV009_REPLAY_RESULTS_local.json
?? docs/validation/RV010_IMPLEMENTATION_GUIDE.md
?? docs/validation/RV010_LIVE_RESULTS.json
?? docs/validation/RV010_PASSAGE_REVIEW.md
?? docs/validation/RV010_REVIEW_RESULTS.json
?? docs/validation/RV011_CANDIDATE_TRACE.json
?? docs/validation/RV012_ANALYSIS_AND_GUIDE.md
?? docs/validation/RV012_LEXICAL_REPLAY_RESULTS.json
?? docs/validation/RV012_LEXICAL_REPLAY_RESULTS_local.json
?? docs/validation/RV013_FILTERED_RERANK_RESULTS.json
?? docs/validation/RV013_IMPLEMENTATION_GUIDE.md
?? tests/smoke/smoke_candidate_trace.py
?? tests/smoke/smoke_filtered_reranking.py
?? tests/smoke/smoke_lexical_filter_replay.py
?? tests/smoke/smoke_prefix_reranking_live.py
?? tests/smoke/smoke_reranking_experiment.py
?? tests/smoke/smoke_reranking_replay.py
?? tests/unit/test_candidate_trace.py
?? tests/unit/test_cross_encoder_scorer.py
?? tests/unit/test_filtered_reranking.py
?? tests/unit/test_lexical_filter_replay.py
?? tests/unit/test_lexical_query_filter.py
?? tests/unit/test_prefix_preserving_selector.py
?? tests/unit/test_prefix_reranking_live.py
?? tests/unit/test_reranker.py
?? tests/unit/test_reranking_replay.py
```

## 4. Code Metrics

- Python files: **90**
- Total Python lines: **12801**
- Effective Python lines: **10189**
- Functions: **685**
- Classes: **64**
- TODO/FIXME occurrences: **2**
- Files with syntax errors: **0**

## 5. Project Structure

```text
enterprise-knowledge-ai-system/
    [FILE] .gitignore
    [DIR] app/
        [DIR] chunking/
            [FILE] block_serializer.py
            [FILE] schemas.py
            [FILE] structure_aware_chunker.py
        [DIR] evaluation/
            [FILE] __init__.py
            [FILE] golden_set_loader.py
            [FILE] retrieval_evaluator.py
            [FILE] retrieval_metrics.py
            [FILE] schemas.py
        [DIR] generation/
        [DIR] ingestion/
            [FILE] docling_parser.py
            [FILE] document_parser.py
            [FILE] ingestion_router.py
            [FILE] pptx_native_enricher.py
            [FILE] registry.py
            [FILE] schemas.py
            [FILE] xlsx_parser.py
        [DIR] retrieval/
            [FILE] candidate_fusion.py
            [FILE] cross_encoder_scorer.py
            [FILE] document_diversifier.py
            [FILE] embeddings.py
            [FILE] hybrid_retriever.py
            [FILE] lexical_index.py
            [FILE] lexical_query_filter.py
            [FILE] lexical_retriever.py
            [FILE] openai_embeddings.py
            [FILE] prefix_preserving_selector.py
            [FILE] reranker.py
            [FILE] schemas.py
            [FILE] search_text.py
            [FILE] vector_index.py
            [FILE] vector_indexer.py
            [FILE] vector_retriever.py
        [DIR] scripts/
            [FILE] project_audit.py
    [DIR] data/
        [DIR] ground_truth/
            [FILE] canonical_facts.yaml
            [FILE] document_registry.yaml
            [FILE] golden_questions.yaml
            [FILE] reranking_challenge_b.json
        [DIR] source/
            [DIR] contracts/
            [DIR] corporate_repository/
                [DIR] governance/
                    [FILE] DOC-012_Approval_Authority_Matrix.xlsx
                [DIR] guidelines/
                    [FILE] DOC-025_AI_Procurement_Guidelines.md
                    [FILE] DOC-026_AI_Workforce_Enablement_Guide.pptx
                [DIR] policies/
                    [FILE] DOC-005_Data_Sharing_Policy.pdf
                    [FILE] DOC-006_Information_Security_Policy.pdf
                    [FILE] DOC-007_Document_Governance_Policy.pdf
                    [FILE] DOC-022_Supplier_Management_Policy.pdf
                    [FILE] DOC-023_AI_Governance_Policy.pdf
                [DIR] sops/
                    [FILE] DOC-010_Security_Incident_SOP.docx
                [DIR] standards/
                    [FILE] DOC-024_AI_Security_Standard.pdf
            [DIR] incidents/
            [DIR] minutes/
            [DIR] policies/
            [DIR] reference/
            [DIR] sops/
            [DIR] standards/
    [DIR] docs/
        [DIR] architecture/
            [FILE] 01_system_overview.md
            [FILE] 02_enterprise_universe_and_source_strategy.md
        [DIR] images/
            [FILE] architecture-overview.png
            [FILE] art-architecture-overview.png
            [FILE] art-featured-product.png
            [FILE] art-featured.png
            [FILE] art-system-overview.png
        [DIR] project_audit/
        [DIR] validation/
            [FILE] RETRIEVAL_VALIDATION.md
            [FILE] RV008_IMPLEMENTATION_GUIDE.md
            [FILE] RV008_RESULTS.json
            [FILE] RV009_ANALYSIS.md
            [FILE] RV009_REPLAY_RESULTS.json
            [FILE] RV009_REPLAY_RESULTS_local.json
            [FILE] RV010_IMPLEMENTATION_GUIDE.md
            [FILE] RV010_LIVE_RESULTS.json
            [FILE] RV010_PASSAGE_REVIEW.md
            [FILE] RV010_REVIEW_RESULTS.json
            [FILE] RV011_CANDIDATE_TRACE.json
            [FILE] RV012_ANALYSIS_AND_GUIDE.md
            [FILE] RV012_LEXICAL_REPLAY_RESULTS.json
            [FILE] RV012_LEXICAL_REPLAY_RESULTS_local.json
            [FILE] RV013_FILTERED_RERANK_RESULTS.json
            [FILE] RV013_IMPLEMENTATION_GUIDE.md
    [FILE] README.md
    [FILE] requirements.txt
    [DIR] tests/
        [DIR] integration/
            [FILE] test_docling_corpus_integration.py
            [FILE] test_docling_docx_integration.py
            [FILE] test_docling_pdf_integration.py
            [FILE] test_docling_pptx_integration.py
            [FILE] test_document_parser_pptx_integration.py
            [FILE] test_ingestion_router_integration.py
            [FILE] test_xlsx_corpus_integration.py
        [DIR] smoke/
            [FILE] smoke_bm25_language_experiment.py
            [FILE] smoke_candidate_trace.py
            [FILE] smoke_document_diversity_experiment.py
            [FILE] smoke_filtered_reranking.py
            [FILE] smoke_golden_set_hybrid_retrieval.py
            [FILE] smoke_golden_set_vector_retrieval.py
            [FILE] smoke_hybrid_v03_end_to_end.py
            [FILE] smoke_lexical_filter_replay.py
            [FILE] smoke_multi_document_vector_retrieval.py
            [FILE] smoke_openai_embeddings.py
            [FILE] smoke_prefix_reranking_live.py
            [FILE] smoke_reranking_experiment.py
            [FILE] smoke_reranking_replay.py
            [FILE] smoke_retrieval_diagnostics.py
            [FILE] smoke_vector_retrieval.py
        [DIR] unit/
            [FILE] test_block_serializer.py
            [FILE] test_candidate_fusion.py
            [FILE] test_candidate_trace.py
            [FILE] test_chunking_schemas.py
            [FILE] test_cross_encoder_scorer.py
            [FILE] test_docling_parser.py
            [FILE] test_document_diversifier.py
            [FILE] test_document_parser.py
            [FILE] test_embedding_contract.py
            [FILE] test_evaluation_schemas.py
            [FILE] test_filtered_reranking.py
            [FILE] test_golden_set_loader.py
            [FILE] test_hybrid_retriever.py
            [FILE] test_ingestion_registry.py
            [FILE] test_ingestion_router.py
            [FILE] test_ingestion_schemas.py
            [FILE] test_lexical_filter_replay.py
            [FILE] test_lexical_index.py
            [FILE] test_lexical_query_filter.py
            [FILE] test_lexical_retriever.py
            [FILE] test_openai_embeddings.py
            [FILE] test_pptx_native_enricher.py
            [FILE] test_prefix_preserving_selector.py
            [FILE] test_prefix_reranking_live.py
            [FILE] test_reranker.py
            [FILE] test_reranking_replay.py
            [FILE] test_retrieval_evaluator.py
            [FILE] test_retrieval_metrics.py
            [FILE] test_retrieval_schemas.py
            [FILE] test_search_text.py
            [FILE] test_structure_aware_chunker.py
            [FILE] test_structure_aware_chunker_multiblock.py
            [FILE] test_vector_index.py
            [FILE] test_vector_indexer.py
            [FILE] test_vector_retriever.py
            [FILE] test_xlsx_parser.py
```

## 6. Python Files

| File | Lines | Functions | Classes | TODOs | Syntax |
|---|---:|---:|---:|---:|---|
| `app/chunking/block_serializer.py` | 165 | 7 | 1 | 0 | OK |
| `app/chunking/schemas.py` | 59 | 1 | 1 | 0 | OK |
| `app/chunking/structure_aware_chunker.py` | 224 | 12 | 2 | 0 | OK |
| `app/evaluation/__init__.py` | 1 | 0 | 0 | 0 | OK |
| `app/evaluation/golden_set_loader.py` | 113 | 5 | 3 | 0 | OK |
| `app/evaluation/retrieval_evaluator.py` | 120 | 3 | 3 | 0 | OK |
| `app/evaluation/retrieval_metrics.py` | 61 | 4 | 0 | 0 | OK |
| `app/evaluation/schemas.py` | 39 | 1 | 1 | 0 | OK |
| `app/ingestion/docling_parser.py` | 206 | 9 | 1 | 0 | OK |
| `app/ingestion/document_parser.py` | 80 | 4 | 1 | 0 | OK |
| `app/ingestion/ingestion_router.py` | 63 | 4 | 1 | 0 | OK |
| `app/ingestion/pptx_native_enricher.py` | 279 | 11 | 1 | 0 | OK |
| `app/ingestion/registry.py` | 254 | 10 | 2 | 0 | OK |
| `app/ingestion/schemas.py` | 441 | 14 | 11 | 0 | OK |
| `app/ingestion/xlsx_parser.py` | 93 | 4 | 1 | 0 | OK |
| `app/retrieval/candidate_fusion.py` | 79 | 2 | 2 | 0 | OK |
| `app/retrieval/cross_encoder_scorer.py` | 109 | 3 | 1 | 0 | OK |
| `app/retrieval/document_diversifier.py` | 51 | 1 | 1 | 0 | OK |
| `app/retrieval/embeddings.py` | 17 | 2 | 1 | 0 | OK |
| `app/retrieval/hybrid_retriever.py` | 43 | 2 | 1 | 0 | OK |
| `app/retrieval/lexical_index.py` | 88 | 4 | 2 | 0 | OK |
| `app/retrieval/lexical_query_filter.py` | 56 | 4 | 2 | 0 | OK |
| `app/retrieval/lexical_retriever.py` | 29 | 2 | 1 | 0 | OK |
| `app/retrieval/openai_embeddings.py` | 74 | 4 | 1 | 0 | OK |
| `app/retrieval/prefix_preserving_selector.py` | 57 | 2 | 1 | 0 | OK |
| `app/retrieval/reranker.py` | 125 | 9 | 3 | 0 | OK |
| `app/retrieval/schemas.py` | 26 | 1 | 1 | 0 | OK |
| `app/retrieval/search_text.py` | 13 | 1 | 0 | 0 | OK |
| `app/retrieval/vector_index.py` | 91 | 5 | 2 | 0 | OK |
| `app/retrieval/vector_indexer.py` | 36 | 2 | 1 | 0 | OK |
| `app/retrieval/vector_retriever.py` | 58 | 2 | 1 | 0 | OK |
| `app/scripts/project_audit.py` | 712 | 27 | 0 | 2 | OK |
| `tests/integration/test_docling_corpus_integration.py` | 111 | 9 | 0 | 0 | OK |
| `tests/integration/test_docling_docx_integration.py` | 138 | 11 | 0 | 0 | OK |
| `tests/integration/test_docling_pdf_integration.py` | 150 | 14 | 0 | 0 | OK |
| `tests/integration/test_docling_pptx_integration.py` | 97 | 10 | 0 | 0 | OK |
| `tests/integration/test_document_parser_pptx_integration.py` | 92 | 8 | 0 | 0 | OK |
| `tests/integration/test_ingestion_router_integration.py` | 29 | 1 | 0 | 0 | OK |
| `tests/integration/test_xlsx_corpus_integration.py` | 113 | 11 | 0 | 0 | OK |
| `tests/smoke/smoke_bm25_language_experiment.py` | 141 | 2 | 0 | 0 | OK |
| `tests/smoke/smoke_candidate_trace.py` | 329 | 10 | 0 | 0 | OK |
| `tests/smoke/smoke_document_diversity_experiment.py` | 188 | 3 | 0 | 0 | OK |
| `tests/smoke/smoke_filtered_reranking.py` | 246 | 6 | 0 | 0 | OK |
| `tests/smoke/smoke_golden_set_hybrid_retrieval.py` | 129 | 4 | 0 | 0 | OK |
| `tests/smoke/smoke_golden_set_vector_retrieval.py` | 281 | 6 | 0 | 0 | OK |
| `tests/smoke/smoke_hybrid_v03_end_to_end.py` | 156 | 3 | 0 | 0 | OK |
| `tests/smoke/smoke_lexical_filter_replay.py` | 278 | 8 | 0 | 0 | OK |
| `tests/smoke/smoke_multi_document_vector_retrieval.py` | 343 | 6 | 1 | 0 | OK |
| `tests/smoke/smoke_openai_embeddings.py` | 33 | 1 | 0 | 0 | OK |
| `tests/smoke/smoke_prefix_reranking_live.py` | 302 | 9 | 0 | 0 | OK |
| `tests/smoke/smoke_reranking_experiment.py` | 246 | 5 | 0 | 0 | OK |
| `tests/smoke/smoke_reranking_replay.py` | 220 | 7 | 0 | 0 | OK |
| `tests/smoke/smoke_retrieval_diagnostics.py` | 132 | 4 | 0 | 0 | OK |
| `tests/smoke/smoke_vector_retrieval.py` | 106 | 1 | 0 | 0 | OK |
| `tests/unit/test_block_serializer.py` | 182 | 6 | 0 | 0 | OK |
| `tests/unit/test_candidate_fusion.py` | 101 | 14 | 0 | 0 | OK |
| `tests/unit/test_candidate_trace.py` | 173 | 13 | 0 | 0 | OK |
| `tests/unit/test_chunking_schemas.py` | 193 | 10 | 0 | 0 | OK |
| `tests/unit/test_cross_encoder_scorer.py` | 132 | 10 | 0 | 0 | OK |
| `tests/unit/test_docling_parser.py` | 330 | 20 | 1 | 0 | OK |
| `tests/unit/test_document_diversifier.py` | 68 | 9 | 0 | 0 | OK |
| `tests/unit/test_document_parser.py` | 266 | 12 | 0 | 0 | OK |
| `tests/unit/test_embedding_contract.py` | 37 | 5 | 1 | 0 | OK |
| `tests/unit/test_evaluation_schemas.py` | 50 | 6 | 0 | 0 | OK |
| `tests/unit/test_filtered_reranking.py` | 142 | 11 | 0 | 0 | OK |
| `tests/unit/test_golden_set_loader.py` | 59 | 6 | 0 | 0 | OK |
| `tests/unit/test_hybrid_retriever.py` | 113 | 14 | 0 | 0 | OK |
| `tests/unit/test_ingestion_registry.py` | 226 | 19 | 0 | 0 | OK |
| `tests/unit/test_ingestion_router.py` | 100 | 9 | 0 | 0 | OK |
| `tests/unit/test_ingestion_schemas.py` | 670 | 38 | 0 | 0 | OK |
| `tests/unit/test_lexical_filter_replay.py` | 82 | 8 | 0 | 0 | OK |
| `tests/unit/test_lexical_index.py` | 47 | 6 | 0 | 0 | OK |
| `tests/unit/test_lexical_query_filter.py` | 76 | 8 | 0 | 0 | OK |
| `tests/unit/test_lexical_retriever.py` | 42 | 4 | 0 | 0 | OK |
| `tests/unit/test_openai_embeddings.py` | 175 | 17 | 8 | 0 | OK |
| `tests/unit/test_pptx_native_enricher.py` | 280 | 16 | 0 | 0 | OK |
| `tests/unit/test_prefix_preserving_selector.py` | 101 | 10 | 0 | 0 | OK |
| `tests/unit/test_prefix_reranking_live.py` | 108 | 9 | 0 | 0 | OK |
| `tests/unit/test_reranker.py` | 174 | 15 | 0 | 0 | OK |
| `tests/unit/test_reranking_replay.py` | 122 | 12 | 0 | 0 | OK |
| `tests/unit/test_retrieval_evaluator.py` | 85 | 6 | 0 | 0 | OK |
| `tests/unit/test_retrieval_metrics.py` | 39 | 6 | 0 | 0 | OK |
| `tests/unit/test_retrieval_schemas.py` | 86 | 6 | 0 | 0 | OK |
| `tests/unit/test_search_text.py` | 54 | 5 | 0 | 0 | OK |
| `tests/unit/test_structure_aware_chunker.py` | 208 | 13 | 0 | 0 | OK |
| `tests/unit/test_structure_aware_chunker_multiblock.py` | 86 | 3 | 0 | 0 | OK |
| `tests/unit/test_vector_index.py` | 115 | 10 | 0 | 0 | OK |
| `tests/unit/test_vector_indexer.py` | 101 | 8 | 2 | 0 | OK |
| `tests/unit/test_vector_retriever.py` | 124 | 10 | 1 | 0 | OK |
| `tests/unit/test_xlsx_parser.py` | 132 | 10 | 0 | 0 | OK |

## 7. Enterprise Knowledge Corpus

- Total source documents: **10**

### Documents by extension

- `.docx`: 1
- `.md`: 1
- `.pdf`: 6
- `.pptx`: 1
- `.xlsx`: 1

### Documents by source area

- `corporate_repository`: 10

### Source documents

- `data/source/corporate_repository/governance/DOC-012_Approval_Authority_Matrix.xlsx`
- `data/source/corporate_repository/guidelines/DOC-025_AI_Procurement_Guidelines.md`
- `data/source/corporate_repository/guidelines/DOC-026_AI_Workforce_Enablement_Guide.pptx`
- `data/source/corporate_repository/policies/DOC-005_Data_Sharing_Policy.pdf`
- `data/source/corporate_repository/policies/DOC-006_Information_Security_Policy.pdf`
- `data/source/corporate_repository/policies/DOC-007_Document_Governance_Policy.pdf`
- `data/source/corporate_repository/policies/DOC-022_Supplier_Management_Policy.pdf`
- `data/source/corporate_repository/policies/DOC-023_AI_Governance_Policy.pdf`
- `data/source/corporate_repository/sops/DOC-010_Security_Incident_SOP.docx`
- `data/source/corporate_repository/standards/DOC-024_AI_Security_Standard.pdf`

## 8. Ground Truth

| Artifact | Status |
|---|:---:|
| `canonical_facts.yaml` | PRESENT |
| `document_registry.yaml` | PRESENT |
| `golden_questions.yaml` | PRESENT |

### Ground-truth files

- `data/ground_truth/canonical_facts.yaml`
- `data/ground_truth/document_registry.yaml`
- `data/ground_truth/golden_questions.yaml`
- `data/ground_truth/reranking_challenge_b.json`

## 9. Test Suite

Execution mode: **DISCOVERY ONLY**

Full test execution is intentionally not performed by the project audit.

Validation command:

```text
python -m pytest
```

The audit maps the discovered test suite and behavioral contracts. Full regression
execution remains an explicit validation step outside the audit so long-running
integration tests do not make snapshot generation slow or timeout-prone.

## 10. Test Discovery / Behavioral Contracts

```text
tests/integration/test_docling_corpus_integration.py::test_doc_025_is_parsed_from_physical_corpus
tests/integration/test_docling_corpus_integration.py::test_doc_025_preserves_document_title
tests/integration/test_docling_corpus_integration.py::test_doc_025_preserves_expected_sections[1. Purpose]
tests/integration/test_docling_corpus_integration.py::test_doc_025_preserves_expected_sections[2. Procurement considerations]
tests/integration/test_docling_corpus_integration.py::test_doc_025_preserves_expected_sections[3. AI supplier due diligence]
tests/integration/test_docling_corpus_integration.py::test_doc_025_preserves_expected_sections[4. Approval boundary]
tests/integration/test_docling_corpus_integration.py::test_doc_025_preserves_expected_sections[5. Supplier data]
tests/integration/test_docling_corpus_integration.py::test_doc_025_preserves_expected_sections[6. Evaluation role]
tests/integration/test_docling_corpus_integration.py::test_doc_025_preserves_authority_boundary_statement
tests/integration/test_docling_corpus_integration.py::test_doc_025_preserves_inline_spacing
tests/integration/test_docling_corpus_integration.py::test_doc_025_preserves_supplier_data_boundary
tests/integration/test_docling_corpus_integration.py::test_doc_025_section_content_keeps_structural_provenance
tests/integration/test_docling_corpus_integration.py::test_doc_025_remains_guidance_not_decision_authority
tests/integration/test_docling_docx_integration.py::test_doc_010_is_parsed_from_physical_corpus
tests/integration/test_docling_docx_integration.py::test_doc_010_preserves_document_title_text
tests/integration/test_docling_docx_integration.py::test_doc_010_preserves_expected_sections[1. Purpose]
tests/integration/test_docling_docx_integration.py::test_doc_010_preserves_expected_sections[2. Trigger]
tests/integration/test_docling_docx_integration.py::test_doc_010_preserves_expected_sections[3. Immediate actions]
tests/integration/test_docling_docx_integration.py::test_doc_010_preserves_expected_sections[4. Supplier disclosure]
tests/integration/test_docling_docx_integration.py::test_doc_010_preserves_expected_sections[5. Closure]
tests/integration/test_docling_docx_integration.py::test_doc_010_preserves_expected_sections[6. Related documents]
tests/integration/test_docling_docx_integration.py::test_doc_010_preserves_all_immediate_action_steps
tests/integration/test_docling_docx_integration.py::test_doc_010_immediate_actions_keep_section_provenance
tests/integration/test_docling_docx_integration.py::test_doc_010_preserves_supplier_disclosure_rule
tests/integration/test_docling_docx_integration.py::test_doc_010_preserves_evidence_protection_instruction
tests/integration/test_docling_docx_integration.py::test_doc_010_preserves_closure_requirements
tests/integration/test_docling_docx_integration.py::test_doc_010_preserves_related_document_references
tests/integration/test_docling_pdf_integration.py::test_doc_005_is_parsed_from_physical_corpus
tests/integration/test_docling_pdf_integration.py::test_doc_005_preserves_policy_title_text
tests/integration/test_docling_pdf_integration.py::test_doc_005_preserves_expected_sections[1. Purpose]
tests/integration/test_docling_pdf_integration.py::test_doc_005_preserves_expected_sections[2. Scope]
tests/integration/test_docling_pdf_integration.py::test_doc_005_preserves_expected_sections[3. Information classification and minimum controls]
tests/integration/test_docling_pdf_integration.py::test_doc_005_preserves_expected_sections[4. Sharing with transportation carriers]
tests/integration/test_docling_pdf_integration.py::test_doc_005_preserves_expected_sections[5. Approved channels]
tests/integration/test_docling_pdf_integration.py::test_doc_005_preserves_expected_sections[6. Supplier and AI-related use]
tests/integration/test_docling_pdf_integration.py::test_doc_005_preserves_expected_sections[7. Exceptions]
tests/integration/test_docling_pdf_integration.py::test_doc_005_preserves_page_provenance
tests/integration/test_docling_pdf_integration.py::test_doc_005_extracts_classification_table
tests/integration/test_docling_pdf_integration.py::test_doc_005_table_preserves_page_provenance
tests/integration/test_docling_pdf_integration.py::test_doc_005_preserves_confidential_sharing_rule
tests/integration/test_docling_pdf_integration.py::test_doc_005_preserves_carrier_restriction
tests/integration/test_docling_pdf_integration.py::test_doc_005_preserves_approved_channel_rule
tests/integration/test_docling_pdf_integration.py::test_doc_005_preserves_ai_cross_policy_reference
tests/integration/test_docling_pdf_integration.py::test_doc_005_preserves_exception_boundary
tests/integration/test_docling_pptx_integration.py::test_doc_026_is_parsed_from_physical_corpus
tests/integration/test_docling_pptx_integration.py::test_doc_026_preserves_guide_title_text
tests/integration/test_docling_pptx_integration.py::test_doc_026_does_not_invent_title_semantics
tests/integration/test_docling_pptx_integration.py::test_doc_026_maps_docling_page_ordinals_to_slides
tests/integration/test_docling_pptx_integration.py::test_doc_026_preserves_slide_specific_content[AI Workforce Enablement Guide-1]
tests/integration/test_docling_pptx_integration.py::test_doc_026_preserves_slide_specific_content[Mandatory baseline training-2]
tests/integration/test_docling_pptx_integration.py::test_doc_026_preserves_slide_specific_content[Role-specific learning-3]
tests/integration/test_docling_pptx_integration.py::test_doc_026_preserves_slide_specific_content[What training does not do-4]
tests/integration/test_docling_pptx_integration.py::test_doc_026_preserves_mandatory_baseline_training
tests/integration/test_docling_pptx_integration.py::test_doc_026_preserves_role_specific_learning
tests/integration/test_docling_pptx_integration.py::test_doc_026_preserves_training_governance_boundary
tests/integration/test_document_parser_pptx_integration.py::test_doc_026_is_parsed_through_document_parser
tests/integration/test_document_parser_pptx_integration.py::test_doc_026_preserves_all_four_slide_locations
tests/integration/test_document_parser_pptx_integration.py::test_doc_026_preserves_known_text_after_composition
tests/integration/test_document_parser_pptx_integration.py::test_doc_026_has_no_native_chart_blocks
tests/integration/test_document_parser_pptx_integration.py::test_doc_026_preserves_docling_order_when_no_charts_exist
tests/integration/test_document_parser_pptx_integration.py::test_doc_026_preserves_existing_pptx_semantics
tests/integration/test_ingestion_router_integration.py::test_ingestion_router_routes_xlsx_without_exposing_parser_choice
tests/integration/test_xlsx_corpus_integration.py::test_doc_012_is_parsed_from_physical_corpus
tests/integration/test_xlsx_corpus_integration.py::test_doc_012_preserves_worksheet_names
tests/integration/test_xlsx_corpus_integration.py::test_doc_012_preserves_worksheet_ranges
tests/integration/test_xlsx_corpus_integration.py::test_doc_012_approval_matrix_preserves_headers
tests/integration/test_xlsx_corpus_integration.py::test_doc_012_preserves_new_ai_tool_approval_rule
tests/integration/test_xlsx_corpus_integration.py::test_doc_012_preserves_confidential_supplier_data_rule
tests/integration/test_xlsx_corpus_integration.py::test_doc_012_document_control_preserves_identity
tests/integration/test_xlsx_corpus_integration.py::test_doc_012_document_control_preserves_governance_metadata
tests/integration/test_xlsx_corpus_integration.py::test_doc_012_cells_are_preserved_as_native_spreadsheet_cells
tests/unit/test_block_serializer.py::test_serializer_preserves_text_block_content
tests/unit/test_block_serializer.py::test_serializer_serializes_table_structure_deterministically
tests/unit/test_block_serializer.py::test_serializer_serializes_spreadsheet_structure_deterministically
tests/unit/test_block_serializer.py::test_serializer_serializes_chart_structure_deterministically
tests/unit/test_block_serializer.py::test_serializer_uses_image_caption_when_available
tests/unit/test_block_serializer.py::test_serializer_returns_none_for_image_without_caption
tests/unit/test_candidate_fusion.py::test_empty_rankings
tests/unit/test_candidate_fusion.py::test_shared_candidate_is_promoted
tests/unit/test_candidate_fusion.py::test_scores_use_ranks_not_source_scores
tests/unit/test_candidate_fusion.py::test_ties_follow_first_seen_order
tests/unit/test_candidate_fusion.py::test_top_k_limits_output_and_reassigns_rank
tests/unit/test_candidate_fusion.py::test_invalid_rrf_k[0]
tests/unit/test_candidate_fusion.py::test_invalid_rrf_k[-1]
tests/unit/test_candidate_fusion.py::test_invalid_rrf_k[1.2]
tests/unit/test_candidate_fusion.py::test_invalid_rrf_k[True]
tests/unit/test_candidate_fusion.py::test_invalid_top_k[0]
tests/unit/test_candidate_fusion.py::test_invalid_top_k[-1]
tests/unit/test_candidate_fusion.py::test_invalid_top_k[1.2]
tests/unit/test_candidate_fusion.py::test_invalid_top_k[True]
tests/unit/test_candidate_fusion.py::test_rejects_duplicate_methods
tests/unit/test_candidate_fusion.py::test_rejects_duplicate_chunk_within_ranking
tests/unit/test_candidate_fusion.py::test_rejects_conflicting_chunk_provenance
tests/unit/test_candidate_fusion.py::test_rejects_duplicate_ranks
tests/unit/test_candidate_fusion.py::test_rejects_mixed_methods_in_ranking
tests/unit/test_candidate_trace.py::test_full_vector_ranking_has_the_same_top20_as_a_top20_request_including_ties
tests/unit/test_candidate_trace.py::test_document_present_does_not_mean_the_reference_passage_was_selected
tests/unit/test_candidate_trace.py::test_full_rank_does_not_leak_candidates_past_top20_into_baseline
tests/unit/test_candidate_trace.py::test_rrf_cutoff_is_distinguished_from_retriever_depth
tests/unit/test_candidate_trace.py::test_final_selection_cutoff_is_distinguished_from_same_document_passage_loss
tests/unit/test_candidate_trace.py::test_reference_group_uses_any_acceptable_alternative
tests/unit/test_candidate_trace.py::test_empty_target_is_rejected
tests/unit/test_candidate_trace.py::test_trace_exposes_literal_collision_and_separate_rrf_contributions
tests/unit/test_candidate_trace.py::test_windows_absolute_helper_fingerprint_uses_only_known_local_path
tests/unit/test_candidate_trace.py::test_review_distinguishes_document_hit_from_missing_reference_evidence
tests/unit/test_candidate_trace.py::test_review_rejects_inconsistent_evidence[row_metric-Metric mismatch]
tests/unit/test_candidate_trace.py::test_review_rejects_inconsistent_evidence[group_metric-Metric mismatch]
tests/unit/test_candidate_trace.py::test_review_rejects_inconsistent_evidence[query-definition changed]
tests/unit/test_candidate_trace.py::test_review_rejects_inconsistent_evidence[coverage-coverage mismatch]
tests/unit/test_candidate_trace.py::test_review_rejects_inconsistent_evidence[duplicate_question-missing or duplicated]
tests/unit/test_candidate_trace.py::test_review_rejects_inconsistent_evidence[score_order-order disagrees]
tests/unit/test_candidate_trace.py::test_review_rejects_inconsistent_evidence[source_binding-binding mismatch]
tests/unit/test_candidate_trace.py::test_review_rejects_inconsistent_evidence[unstable-stable RV-010]
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_preserves_content_and_source_traceability
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_supports_multi_block_and_multi_page_provenance
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_supports_slide_provenance
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_supports_worksheet_provenance
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_rejects_empty_required_text_fields[chunk_id-]
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_rejects_empty_required_text_fields[chunk_id-   ]
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_rejects_empty_required_text_fields[document_id-]
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_rejects_empty_required_text_fields[document_id-   ]
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_rejects_empty_required_text_fields[text-]
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_rejects_empty_required_text_fields[text-   ]
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_rejects_negative_order
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_requires_source_blocks
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_requires_content_types
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_rejects_duplicate_provenance_values
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_rejects_invalid_page_number
tests/unit/test_cross_encoder_scorer.py::test_lazy_loading_pinned_revision_batch_order_and_local_inference
tests/unit/test_cross_encoder_scorer.py::test_invalid_configuration_rejected_without_loading[options0]
tests/unit/test_cross_encoder_scorer.py::test_invalid_configuration_rejected_without_loading[options1]
tests/unit/test_cross_encoder_scorer.py::test_invalid_configuration_rejected_without_loading[options2]
tests/unit/test_cross_encoder_scorer.py::test_invalid_configuration_rejected_without_loading[options3]
tests/unit/test_cross_encoder_scorer.py::test_invalid_configuration_rejected_without_loading[options4]
tests/unit/test_cross_encoder_scorer.py::test_invalid_configuration_rejected_without_loading[options5]
tests/unit/test_cross_encoder_scorer.py::test_invalid_configuration_rejected_without_loading[options6]
tests/unit/test_cross_encoder_scorer.py::test_invalid_configuration_rejected_without_loading[options7]
tests/unit/test_cross_encoder_scorer.py::test_invalid_pair_inputs_rejected_before_loading[-passages0]
tests/unit/test_cross_encoder_scorer.py::test_invalid_pair_inputs_rejected_before_loading[None-passages1]
tests/unit/test_cross_encoder_scorer.py::test_invalid_pair_inputs_rejected_before_loading[q-single string]
tests/unit/test_cross_encoder_scorer.py::test_invalid_pair_inputs_rejected_before_loading[q-passages3]
tests/unit/test_cross_encoder_scorer.py::test_invalid_pair_inputs_rejected_before_loading[q-passages4]
tests/unit/test_cross_encoder_scorer.py::test_missing_optional_dependency_reports_actionable_error
tests/unit/test_cross_encoder_scorer.py::test_multiclass_model_rejected
tests/unit/test_cross_encoder_scorer.py::test_oversized_query_fails_explicitly_instead_of_dropping_query_text
tests/unit/test_cross_encoder_scorer.py::test_nonfinite_logits_rejected[scores0]
tests/unit/test_cross_encoder_scorer.py::test_nonfinite_logits_rejected[scores1]
tests/unit/test_cross_encoder_scorer.py::test_wrong_output_shape_rejected
tests/unit/test_cross_encoder_scorer.py::test_download_failure_is_visible_and_does_not_mark_provider_loaded
tests/unit/test_docling_parser.py::test_markdown_inline_normalization_preserves_semantic_spacing
tests/unit/test_docling_parser.py::test_markdown_inline_normalization_preserves_block_structure
tests/unit/test_docling_parser.py::test_source_location_maps_pdf_ordinal_to_page_number
tests/unit/test_docling_parser.py::test_source_location_maps_pptx_ordinal_to_slide_number
tests/unit/test_docling_parser.py::test_source_location_preserves_missing_provenance
tests/unit/test_docling_parser.py::test_docling_parser_normalizes_markdown_structure
tests/unit/test_docling_parser.py::test_docling_parser_preserves_section_path
tests/unit/test_docling_parser.py::test_docling_parser_returns_deterministic_block_order
tests/unit/test_docling_parser.py::test_docling_parser_text_projection_contains_source_content
tests/unit/test_docling_parser.py::test_docling_parser_rejects_missing_source
tests/unit/test_docling_parser.py::test_docling_parser_rejects_non_path_input
tests/unit/test_docling_parser.py::test_markdown_baseline_does_not_create_spreadsheet_blocks
tests/unit/test_docling_parser.py::test_docling_parser_builds_section_path_by_heading_level
tests/unit/test_docling_parser.py::test_docling_parser_preserves_picture_as_image_block
tests/unit/test_docling_parser.py::test_docling_parser_preserves_resolved_picture_caption
tests/unit/test_document_diversifier.py::test_diversifies_and_pins_first
tests/unit/test_document_diversifier.py::test_backfills_in_original_order
tests/unit/test_document_diversifier.py::test_top_k_one_keeps_original_leader
tests/unit/test_document_diversifier.py::test_empty_pool_returns_empty_tuple
tests/unit/test_document_diversifier.py::test_top_k_larger_than_pool
tests/unit/test_document_diversifier.py::test_all_chunks_from_one_document_are_backfilled
tests/unit/test_document_diversifier.py::test_rejects_duplicate_chunk_ids
tests/unit/test_document_diversifier.py::test_rejects_invalid_top_k[0]
tests/unit/test_document_diversifier.py::test_rejects_invalid_top_k[-1]
tests/unit/test_document_diversifier.py::test_rejects_invalid_top_k[True]
tests/unit/test_document_diversifier.py::test_rejects_invalid_top_k[1.5]
tests/unit/test_document_diversifier.py::test_rejects_invalid_top_k[5]
tests/unit/test_document_parser.py::test_document_parser_routes_docling_formats_to_docling_only[.pdf]
tests/unit/test_document_parser.py::test_document_parser_routes_docling_formats_to_docling_only[.docx]
tests/unit/test_document_parser.py::test_document_parser_routes_docling_formats_to_docling_only[.md]
tests/unit/test_document_parser.py::test_document_parser_routes_xlsx_to_specialized_parser_only
tests/unit/test_document_parser.py::test_document_parser_composes_pptx_docling_content_and_native_charts
tests/unit/test_document_parser.py::test_pptx_composition_orders_blocks_by_slide_then_source_kind
tests/unit/test_document_parser.py::test_pptx_composition_preserves_text_projection_without_flattening_charts
tests/unit/test_document_parser.py::test_pptx_without_native_charts_returns_docling_content_unchanged
tests/unit/test_document_parser.py::test_document_parser_rejects_non_path_input
tests/unit/test_document_parser.py::test_document_parser_rejects_formats_without_an_ingestion_strategy[document.txt]
tests/unit/test_document_parser.py::test_document_parser_rejects_formats_without_an_ingestion_strategy[document.csv]
tests/unit/test_document_parser.py::test_document_parser_rejects_formats_without_an_ingestion_strategy[document]
tests/unit/test_embedding_contract.py::test_fake_provider_satisfies_embedding_provider_protocol
tests/unit/test_embedding_contract.py::test_embedding_provider_preserves_document_order
tests/unit/test_embedding_contract.py::test_embedding_provider_returns_single_query_embedding
tests/unit/test_evaluation_schemas.py::test_valid_question
tests/unit/test_evaluation_schemas.py::test_rejects_empty_required_text[question_id]
tests/unit/test_evaluation_schemas.py::test_rejects_empty_required_text[question]
tests/unit/test_evaluation_schemas.py::test_rejects_empty_required_text[question_class]
tests/unit/test_evaluation_schemas.py::test_rejects_empty_required_text[retrieval_challenge]
tests/unit/test_evaluation_schemas.py::test_rejects_empty_required_text[expected_behavior]
tests/unit/test_evaluation_schemas.py::test_rejects_duplicate_evidence
tests/unit/test_evaluation_schemas.py::test_rejects_evidence_distractor_overlap
tests/unit/test_evaluation_schemas.py::test_abstention_allows_empty_expected_evidence
tests/unit/test_filtered_reranking.py::test_one_scoring_call_uses_original_query_and_preserves_both_score_provenances
tests/unit/test_filtered_reranking.py::test_fixed_membership_does_not_claim_to_repair_missing_passages
tests/unit/test_filtered_reranking.py::test_score_ties_keep_control_order_and_do_not_invent_a_gain
tests/unit/test_filtered_reranking.py::test_scorer_failure_propagates_without_a_successful_baseline_fallback
tests/unit/test_filtered_reranking.py::test_unexpected_selection_size_is_rejected_before_inference
tests/unit/test_filtered_reranking.py::test_decision_reports_losses_separately_from_aggregate_improvement[IMPROVEMENT-REGRESSION-False-True-REGRESSION_KEEP_FILTER_ONLY]
tests/unit/test_filtered_reranking.py::test_decision_reports_losses_separately_from_aggregate_improvement[IMPROVEMENT-NO_FIRST_RANK_GAIN-True-True-MIXED_RESULTS_REVIEW_REQUIRED]
tests/unit/test_filtered_reranking.py::test_decision_reports_losses_separately_from_aggregate_improvement[IMPROVEMENT-NO_FIRST_RANK_GAIN-False-True-CANDIDATE_FOR_REVIEW]
tests/unit/test_filtered_reranking.py::test_decision_reports_losses_separately_from_aggregate_improvement[NO_FIRST_RANK_GAIN-NO_FIRST_RANK_GAIN-False-True-NO_MEASURED_GAIN_KEEP_FILTER_ONLY]
tests/unit/test_filtered_reranking.py::test_decision_reports_losses_separately_from_aggregate_improvement[IMPROVEMENT-REGRESSION-True-False-INPUT_CHANGED_DURING_RUN]
tests/unit/test_filtered_reranking.py::test_local_paths_do_not_make_an_identical_saved_selection_fail_validation
tests/unit/test_filtered_reranking.py::test_changed_replay_is_rejected_before_model_loading[selection-selection changed]
tests/unit/test_filtered_reranking.py::test_changed_replay_is_rejected_before_model_loading[query-definition changed]
tests/unit/test_filtered_reranking.py::test_changed_replay_is_rejected_before_model_loading[binding-binding changed]
tests/unit/test_filtered_reranking.py::test_changed_replay_is_rejected_before_model_loading[policy-configuration changed]
tests/unit/test_filtered_reranking.py::test_changed_replay_is_rejected_before_model_loading[group_metrics-Metric mismatch]
tests/unit/test_filtered_reranking.py::test_changed_replay_is_rejected_before_model_loading[duplicates-missing or duplicated]
tests/unit/test_filtered_reranking.py::test_changed_replay_is_rejected_before_model_loading[coverage-coverage changed]
tests/unit/test_golden_set_loader.py::test_loader_reads_real_golden_set
tests/unit/test_golden_set_loader.py::test_rejects_duplicate_question_ids
tests/unit/test_golden_set_loader.py::test_materialized_question_is_evaluable
tests/unit/test_golden_set_loader.py::test_missing_evidence_blocks_question
tests/unit/test_golden_set_loader.py::test_abstention_without_evidence_is_evaluable
tests/unit/test_hybrid_retriever.py::test_combines_overlapping_candidates_and_preserves_methods
tests/unit/test_hybrid_retriever.py::test_passes_candidate_depth_to_both_retrievers
tests/unit/test_hybrid_retriever.py::test_top_k_larger_than_candidate_depth_expands_search
tests/unit/test_hybrid_retriever.py::test_top_k_limits_fused_results
tests/unit/test_hybrid_retriever.py::test_empty_retrievals_return_empty_tuple
tests/unit/test_hybrid_retriever.py::test_single_retrieval_method_is_supported
tests/unit/test_hybrid_retriever.py::test_rejects_blank_query[]
tests/unit/test_hybrid_retriever.py::test_rejects_blank_query[  ]
tests/unit/test_hybrid_retriever.py::test_rejects_blank_query[\n]
tests/unit/test_hybrid_retriever.py::test_rejects_invalid_top_k[0]
tests/unit/test_hybrid_retriever.py::test_rejects_invalid_top_k[-1]
tests/unit/test_hybrid_retriever.py::test_rejects_invalid_top_k[1.5]
tests/unit/test_hybrid_retriever.py::test_rejects_invalid_top_k[True]
tests/unit/test_hybrid_retriever.py::test_rejects_invalid_candidate_depth[0]
tests/unit/test_hybrid_retriever.py::test_rejects_invalid_candidate_depth[-1]
tests/unit/test_hybrid_retriever.py::test_rejects_invalid_candidate_depth[1.5]
tests/unit/test_hybrid_retriever.py::test_rejects_invalid_candidate_depth[True]
tests/unit/test_hybrid_retriever.py::test_propagates_vector_failure_without_running_lexical
tests/unit/test_hybrid_retriever.py::test_propagates_lexical_failure
tests/unit/test_ingestion_registry.py::test_real_registry_loads_all_27_controlled_documents
tests/unit/test_ingestion_registry.py::test_real_registry_supports_lookup_by_id_and_key
tests/unit/test_ingestion_registry.py::test_real_registry_preserves_lifecycle_relationship
tests/unit/test_ingestion_registry.py::test_real_registry_preserves_entity_references
tests/unit/test_ingestion_registry.py::test_runtime_metadata_excludes_evaluation_only_fields
tests/unit/test_ingestion_registry.py::test_real_registry_contains_only_supported_authority_levels
tests/unit/test_ingestion_registry.py::test_real_registry_contains_expected_formats
tests/unit/test_ingestion_registry.py::test_lookup_unknown_document_id_raises_key_error
tests/unit/test_ingestion_registry.py::test_lookup_unknown_document_key_raises_key_error
tests/unit/test_ingestion_registry.py::test_loader_rejects_duplicate_document_ids
tests/unit/test_ingestion_registry.py::test_loader_rejects_duplicate_document_keys
tests/unit/test_ingestion_registry.py::test_loader_rejects_invalid_authority_level[0]
tests/unit/test_ingestion_registry.py::test_loader_rejects_invalid_authority_level[5]
tests/unit/test_ingestion_registry.py::test_loader_rejects_invalid_authority_level[-1]
tests/unit/test_ingestion_registry.py::test_loader_rejects_invalid_lifecycle_status
tests/unit/test_ingestion_registry.py::test_loader_rejects_unknown_supersedes_reference
tests/unit/test_ingestion_registry.py::test_loader_rejects_inconsistent_lifecycle_relationship
tests/unit/test_ingestion_registry.py::test_loader_requires_path_object
tests/unit/test_ingestion_registry.py::test_loader_rejects_missing_file
tests/unit/test_ingestion_router.py::test_router_exposes_supported_formats_without_parser_details[policy.pdf]
tests/unit/test_ingestion_router.py::test_router_exposes_supported_formats_without_parser_details[procedure.docx]
tests/unit/test_ingestion_router.py::test_router_exposes_supported_formats_without_parser_details[matrix.xlsx]
tests/unit/test_ingestion_router.py::test_router_exposes_supported_formats_without_parser_details[training.pptx]
tests/unit/test_ingestion_router.py::test_router_exposes_supported_formats_without_parser_details[guideline.md]
tests/unit/test_ingestion_router.py::test_router_support_check_is_case_insensitive
tests/unit/test_ingestion_router.py::test_router_rejects_unknown_extension_before_dispatch
tests/unit/test_ingestion_router.py::test_router_rejects_non_path_input
tests/unit/test_ingestion_router.py::test_router_rejects_missing_file
tests/unit/test_ingestion_router.py::test_router_dispatches_and_returns_canonical_contract
tests/unit/test_ingestion_router.py::test_router_rejects_noncanonical_parser_output
tests/unit/test_ingestion_router.py::test_supported_suffixes_match_public_contract
tests/unit/test_ingestion_schemas.py::test_source_location_accepts_supported_structural_locators
tests/unit/test_ingestion_schemas.py::test_source_location_rejects_invalid_locators[page_number-0]
tests/unit/test_ingestion_schemas.py::test_source_location_rejects_invalid_locators[slide_number-0]
tests/unit/test_ingestion_schemas.py::test_source_location_rejects_invalid_locators[sheet_name-   ]
tests/unit/test_ingestion_schemas.py::test_source_location_rejects_invalid_locators[cell_range-]
tests/unit/test_ingestion_schemas.py::test_text_block_preserves_hierarchy_and_provenance
tests/unit/test_ingestion_schemas.py::test_table_block_preserves_tabular_relationships
tests/unit/test_ingestion_schemas.py::test_table_block_rejects_inconsistent_row_widths
tests/unit/test_ingestion_schemas.py::test_table_block_rejects_header_width_mismatch
tests/unit/test_ingestion_schemas.py::test_spreadsheet_block_preserves_cells_formulas_and_range
tests/unit/test_ingestion_schemas.py::test_spreadsheet_block_rejects_duplicate_coordinates
tests/unit/test_ingestion_schemas.py::test_chart_source_reference_preserves_resolved_lineage
tests/unit/test_ingestion_schemas.py::test_chart_source_reference_preserves_unresolved_lineage
tests/unit/test_ingestion_schemas.py::test_resolved_chart_source_requires_sheet_and_range[None-$A$1:$A$5]
tests/unit/test_ingestion_schemas.py::test_resolved_chart_source_requires_sheet_and_range[Planilha2-None]
tests/unit/test_ingestion_schemas.py::test_chart_source_reference_rejects_empty_resource
tests/unit/test_ingestion_schemas.py::test_chart_series_accepts_presented_values_without_source_reference
tests/unit/test_ingestion_schemas.py::test_chart_series_accepts_source_reference_without_materialized_values
tests/unit/test_ingestion_schemas.py::test_chart_series_rejects_missing_values_and_source_reference
tests/unit/test_ingestion_schemas.py::test_chart_block_preserves_presented_chart_structure_and_slide_provenance
tests/unit/test_ingestion_schemas.py::test_chart_block_rejects_empty_series
tests/unit/test_ingestion_schemas.py::test_chart_block_rejects_invalid_required_fields[-0-LINE-block_id must not be empty]
tests/unit/test_ingestion_schemas.py::test_chart_block_rejects_invalid_required_fields[chart-001--1-LINE-order must be greater than or equal to 0]
tests/unit/test_ingestion_schemas.py::test_chart_block_rejects_invalid_required_fields[chart-001-0-   -chart_type must not be empty]
tests/unit/test_ingestion_schemas.py::test_chart_block_rejects_self_parent
tests/unit/test_ingestion_schemas.py::test_normalized_content_accepts_chart_block_and_orders_it_deterministically
tests/unit/test_ingestion_schemas.py::test_text_projection_does_not_flatten_chart_data_implicitly
tests/unit/test_ingestion_schemas.py::test_unresolved_chart_relationship_is_valid_canonical_evidence_state
tests/unit/test_ingestion_schemas.py::test_image_block_preserves_visual_evidence_and_provenance
tests/unit/test_ingestion_schemas.py::test_image_block_rejects_invalid_fields[-0-None-block_id must not be empty]
tests/unit/test_ingestion_schemas.py::test_image_block_rejects_invalid_fields[image-001--1-None-order must be greater than or equal to 0]
tests/unit/test_ingestion_schemas.py::test_image_block_rejects_invalid_fields[image-001-0-   -caption must not be empty when provided]
tests/unit/test_ingestion_schemas.py::test_image_block_rejects_self_parent
tests/unit/test_ingestion_schemas.py::test_normalized_content_accepts_image_without_flattening_it_to_text
tests/unit/test_ingestion_schemas.py::test_normalized_content_orders_blocks_deterministically
tests/unit/test_ingestion_schemas.py::test_normalized_content_rejects_duplicate_block_ids
tests/unit/test_ingestion_schemas.py::test_normalized_content_rejects_duplicate_orders
tests/unit/test_ingestion_schemas.py::test_normalized_content_rejects_unknown_parent
tests/unit/test_ingestion_schemas.py::test_text_projection_is_derived_from_typed_blocks
tests/unit/test_ingestion_schemas.py::test_canonical_document_combines_registry_metadata_and_normalized_content
tests/unit/test_ingestion_schemas.py::test_extracted_text_remains_backward_compatible_projection
tests/unit/test_ingestion_schemas.py::test_canonical_document_rejects_empty_required_strings[document_id-]
tests/unit/test_ingestion_schemas.py::test_canonical_document_rejects_empty_required_strings[key- ]
tests/unit/test_ingestion_schemas.py::test_canonical_document_rejects_empty_required_strings[title-]
tests/unit/test_ingestion_schemas.py::test_canonical_document_rejects_empty_required_strings[document_type-]
tests/unit/test_ingestion_schemas.py::test_canonical_document_rejects_empty_required_strings[domain-]
tests/unit/test_ingestion_schemas.py::test_canonical_document_rejects_empty_required_strings[version-]
tests/unit/test_ingestion_schemas.py::test_canonical_document_rejects_invalid_authority_level[0]
tests/unit/test_ingestion_schemas.py::test_canonical_document_rejects_invalid_authority_level[5]
tests/unit/test_ingestion_schemas.py::test_canonical_document_rejects_invalid_authority_level[-1]
tests/unit/test_ingestion_schemas.py::test_canonical_document_rejects_self_supersession
tests/unit/test_lexical_filter_replay.py::test_replay_rejects_changed_catalog_text
tests/unit/test_lexical_filter_replay.py::test_full_vector_trace_must_include_each_catalog_chunk_exactly_once[missing]
tests/unit/test_lexical_filter_replay.py::test_full_vector_trace_must_include_each_catalog_chunk_exactly_once[duplicate]
tests/unit/test_lexical_filter_replay.py::test_cached_vector_evidence_must_be_finite_sorted_and_provenanced[nan]
tests/unit/test_lexical_filter_replay.py::test_cached_vector_evidence_must_be_finite_sorted_and_provenanced[unsorted]
tests/unit/test_lexical_filter_replay.py::test_cached_vector_evidence_must_be_finite_sorted_and_provenanced[wrong_document]
tests/unit/test_lexical_filter_replay.py::test_reproduced_ranks_with_different_scores_do_not_count_as_valid_reproduction
tests/unit/test_lexical_filter_replay.py::test_disabling_diversity_can_lose_required_documents_even_with_same_top1
tests/unit/test_lexical_filter_replay.py::test_diagnostic_full_vector_ranking_does_not_expand_the_algorithm_input_depth
tests/unit/test_lexical_index.py::test_tokenization_preserves_identifiers
tests/unit/test_lexical_index.py::test_ranking_and_positive_matches_only
tests/unit/test_lexical_index.py::test_ties_are_stable
tests/unit/test_lexical_index.py::test_invalid_corpus[ids0-texts0]
tests/unit/test_lexical_index.py::test_invalid_corpus[ids1-texts1]
tests/unit/test_lexical_index.py::test_invalid_corpus[ids2-texts2]
tests/unit/test_lexical_index.py::test_invalid_corpus[ids3-texts3]
tests/unit/test_lexical_index.py::test_invalid_search
tests/unit/test_lexical_index.py::test_reindex_replaces_corpus
tests/unit/test_lexical_query_filter.py::test_grammatical_collision_no_longer_outvotes_semantic_leader_and_vector_query_is_unchanged
tests/unit/test_lexical_query_filter.py::test_content_terms_identifiers_numbers_and_negations_survive
tests/unit/test_lexical_query_filter.py::test_empty_filtered_query_abstains_only_from_the_lexical_branch
tests/unit/test_lexical_query_filter.py::test_remaining_terms_are_sent_for_rescoring_before_topk_is_applied
tests/unit/test_lexical_query_filter.py::test_delegate_failure_is_not_silently_converted_to_an_empty_ranking
tests/unit/test_lexical_query_filter.py::test_invalid_query_is_rejected[None]
tests/unit/test_lexical_query_filter.py::test_invalid_query_is_rejected[42]
tests/unit/test_lexical_query_filter.py::test_invalid_query_is_rejected[]
tests/unit/test_lexical_query_filter.py::test_invalid_query_is_rejected[   ]
tests/unit/test_lexical_query_filter.py::test_invalid_depth_is_rejected_even_when_all_terms_would_be_removed[0]
tests/unit/test_lexical_query_filter.py::test_invalid_depth_is_rejected_even_when_all_terms_would_be_removed[-1]
tests/unit/test_lexical_query_filter.py::test_invalid_depth_is_rejected_even_when_all_terms_would_be_removed[True]
tests/unit/test_lexical_query_filter.py::test_invalid_depth_is_rejected_even_when_all_terms_would_be_removed[1.5]
tests/unit/test_lexical_retriever.py::test_returns_canonical_candidates_with_provenance
tests/unit/test_lexical_retriever.py::test_duplicate_chunk_ids_rejected
tests/unit/test_lexical_retriever.py::test_unknown_index_hit_rejected
tests/unit/test_openai_embeddings.py::test_openai_provider_satisfies_embedding_provider_protocol
tests/unit/test_openai_embeddings.py::test_embed_documents_calls_openai_with_expected_contract
tests/unit/test_openai_embeddings.py::test_embed_documents_restores_response_order_using_openai_index
tests/unit/test_openai_embeddings.py::test_embed_documents_returns_empty_tuple_without_api_call
tests/unit/test_openai_embeddings.py::test_embed_query_calls_openai_with_single_text
tests/unit/test_openai_embeddings.py::test_provider_supports_explicit_model_configuration
tests/unit/test_openai_embeddings.py::test_embed_query_rejects_empty_text[]
tests/unit/test_openai_embeddings.py::test_embed_query_rejects_empty_text[ ]
tests/unit/test_openai_embeddings.py::test_embed_query_rejects_empty_text[\n\t]
tests/unit/test_openai_embeddings.py::test_embed_documents_rejects_empty_document_text
tests/unit/test_openai_embeddings.py::test_provider_rejects_empty_model_name
tests/unit/test_openai_embeddings.py::test_embed_documents_rejects_incomplete_openai_response
tests/unit/test_pptx_native_enricher.py::test_extract_charts_preserves_native_chart_structure
tests/unit/test_pptx_native_enricher.py::test_extract_charts_preserves_slide_provenance
tests/unit/test_pptx_native_enricher.py::test_extract_charts_assigns_deterministic_ids_and_global_order
tests/unit/test_pptx_native_enricher.py::test_extract_charts_preserves_chart_without_title
tests/unit/test_pptx_native_enricher.py::test_extract_charts_returns_empty_tuple_when_no_charts
tests/unit/test_pptx_native_enricher.py::test_extract_charts_resolves_ooxml_lineage_to_embedded_workbook
tests/unit/test_pptx_native_enricher.py::test_extract_charts_preserves_unresolved_ooxml_reference
tests/unit/test_pptx_native_enricher.py::test_extract_charts_does_not_materialize_embedded_workbook_as_blocks
tests/unit/test_pptx_native_enricher.py::test_extract_charts_rejects_missing_file
tests/unit/test_pptx_native_enricher.py::test_extract_charts_rejects_non_pptx_file
tests/unit/test_pptx_native_enricher.py::test_extract_charts_requires_path_instance
tests/unit/test_prefix_preserving_selector.py::test_only_reorders_inside_protected_document_groups_and_preserves_provenance
tests/unit/test_prefix_preserving_selector.py::test_duplicate_documents_preserve_unique_document_prefix_not_chunk_positions
tests/unit/test_prefix_preserving_selector.py::test_ties_follow_baseline_order_even_if_scored_sequence_is_reversed
tests/unit/test_prefix_preserving_selector.py::test_short_selection_and_empty_selection_are_supported
tests/unit/test_prefix_preserving_selector.py::test_invalid_prefix_configuration_is_rejected[0]
tests/unit/test_prefix_preserving_selector.py::test_invalid_prefix_configuration_is_rejected[-1]
tests/unit/test_prefix_preserving_selector.py::test_invalid_prefix_configuration_is_rejected[True]
tests/unit/test_prefix_preserving_selector.py::test_invalid_prefix_configuration_is_rejected[1.5]
tests/unit/test_prefix_preserving_selector.py::test_invalid_prefix_configuration_is_rejected[3]
tests/unit/test_prefix_preserving_selector.py::test_incomplete_or_extra_scored_candidates_are_rejected
tests/unit/test_prefix_preserving_selector.py::test_duplicate_chunk_ids_are_rejected_on_both_sides
tests/unit/test_prefix_preserving_selector.py::test_same_identity_with_changed_source_is_rejected[text]
tests/unit/test_prefix_preserving_selector.py::test_same_identity_with_changed_source_is_rejected[fusion_score]
tests/unit/test_prefix_preserving_selector.py::test_same_identity_with_changed_source_is_rejected[fusion_rank]
tests/unit/test_prefix_reranking_live.py::test_challenge_b_is_frozen_and_covers_12_new_cases_and_ten_documents
tests/unit/test_prefix_reranking_live.py::test_loading_frozen_json_accepts_windows_line_endings_and_utf8_bom
tests/unit/test_prefix_reranking_live.py::test_changed_question_definition_is_rejected_before_scoring
tests/unit/test_prefix_reranking_live.py::test_source_snapshot_mismatch_is_rejected
tests/unit/test_prefix_reranking_live.py::test_reference_passages_are_checked_against_actual_chunk_content
tests/unit/test_prefix_reranking_live.py::test_frozen_data_guard_checks_exact_known_files
tests/unit/test_prefix_reranking_live.py::test_b_regression_cannot_be_hidden_by_a_improvement
tests/unit/test_prefix_reranking_live.py::test_comparison_preserves_the_existing_no_regression_gate
tests/unit/test_reranker.py::test_scores_entire_pool_before_selecting_top_k_and_preserves_provenance
tests/unit/test_reranker.py::test_equal_scores_keep_input_order_including_negative_scores
tests/unit/test_reranker.py::test_empty_pool_does_not_call_scorer
tests/unit/test_reranker.py::test_invalid_queries_fail_before_scoring[]
tests/unit/test_reranker.py::test_invalid_queries_fail_before_scoring[  ]
tests/unit/test_reranker.py::test_invalid_queries_fail_before_scoring[None]
tests/unit/test_reranker.py::test_invalid_queries_fail_before_scoring[42]
tests/unit/test_reranker.py::test_invalid_output_depth_rejected[0]
tests/unit/test_reranker.py::test_invalid_output_depth_rejected[-1]
tests/unit/test_reranker.py::test_invalid_output_depth_rejected[1.5]
tests/unit/test_reranker.py::test_invalid_output_depth_rejected[True]
tests/unit/test_reranker.py::test_duplicate_identity_rejected_before_scoring
tests/unit/test_reranker.py::test_malformed_provider_scores_are_not_silently_accepted[scores0]
tests/unit/test_reranker.py::test_malformed_provider_scores_are_not_silently_accepted[scores1]
tests/unit/test_reranker.py::test_malformed_provider_scores_are_not_silently_accepted[scores2]
tests/unit/test_reranker.py::test_malformed_provider_scores_are_not_silently_accepted[scores3]
tests/unit/test_reranker.py::test_malformed_provider_scores_are_not_silently_accepted[scores4]
tests/unit/test_reranker.py::test_malformed_provider_scores_are_not_silently_accepted[scores5]
tests/unit/test_reranker.py::test_malformed_provider_scores_are_not_silently_accepted[scores6]
tests/unit/test_reranker.py::test_malformed_provider_scores_are_not_silently_accepted[scores7]
tests/unit/test_reranker.py::test_provider_failure_propagates_without_baseline_substitution
tests/unit/test_reranker.py::test_diversity_uses_reranker_leader_and_keeps_both_original_rankings
tests/unit/test_reranker.py::test_selection_backfills_same_document_and_handles_short_empty_pools
tests/unit/test_reranker.py::test_real_hybrid_fusion_composes_with_reranking_before_diversity
tests/unit/test_reranker.py::test_benchmark_gate_requires_gain_without_metric_regression[changes0-NO_FIRST_RANK_GAIN]
tests/unit/test_reranker.py::test_benchmark_gate_requires_gain_without_metric_regression[changes1-READY_FOR_PASSAGE_REVIEW]
tests/unit/test_reranker.py::test_benchmark_gate_requires_gain_without_metric_regression[changes2-REGRESSION]
tests/unit/test_reranker.py::test_benchmark_gate_requires_gain_without_metric_regression[changes3-REGRESSION]
tests/unit/test_reranker.py::test_benchmark_does_not_promote_against_a_drifted_baseline
tests/unit/test_reranking_replay.py::test_global_sort_and_banded_sort_have_distinct_membership_invariants
tests/unit/test_reranking_replay.py::test_ties_preserve_baseline_order_inside_each_band
tests/unit/test_reranking_replay.py::test_invalid_cached_scores_rejected[nan]
tests/unit/test_reranking_replay.py::test_invalid_cached_scores_rejected[inf]
tests/unit/test_reranking_replay.py::test_invalid_cached_scores_rejected[True]
tests/unit/test_reranking_replay.py::test_invalid_cached_scores_rejected[0.5]
tests/unit/test_reranking_replay.py::test_invalid_candidate_selection_rejected[ids0]
tests/unit/test_reranking_replay.py::test_invalid_candidate_selection_rejected[ids1]
tests/unit/test_reranking_replay.py::test_invalid_candidate_selection_rejected[ids2]
tests/unit/test_reranking_replay.py::test_invalid_candidate_selection_rejected[ids3]
tests/unit/test_reranking_replay.py::test_document_duplicates_rejected_for_document_prefix_constraint
tests/unit/test_reranking_replay.py::test_metric_definition_deduplicates_documents_like_original_evaluator
tests/unit/test_reranking_replay.py::test_replay_reproduces_source_and_never_mutates_input
tests/unit/test_reranking_replay.py::test_expected_documents_do_not_influence_ordering
tests/unit/test_reranking_replay.py::test_source_metric_inconsistency_stops_replay
tests/unit/test_reranking_replay.py::test_unstable_source_is_rejected
tests/unit/test_reranking_replay.py::test_same_average_gate_is_applied_without_relaxing_recall_at_3
tests/unit/test_retrieval_evaluator.py::test_evaluator_scores_eligible_positive_evidence_questions
tests/unit/test_retrieval_evaluator.py::test_evaluator_skips_question_blocked_by_missing_corpus_document
tests/unit/test_retrieval_evaluator.py::test_evaluator_defers_abstention_question_to_later_layer
tests/unit/test_retrieval_evaluator.py::test_evaluator_requires_results_for_each_scored_question
tests/unit/test_retrieval_evaluator.py::test_evaluator_rejects_unsupported_k_configuration
tests/unit/test_retrieval_metrics.py::test_hit_at_k_detects_expected_document
tests/unit/test_retrieval_metrics.py::test_recall_at_k_measures_multi_document_coverage
tests/unit/test_retrieval_metrics.py::test_reciprocal_rank_uses_first_expected_document
tests/unit/test_retrieval_metrics.py::test_metrics_do_not_double_count_multiple_chunks_from_same_document
tests/unit/test_retrieval_metrics.py::test_empty_expected_evidence_scores_zero
tests/unit/test_retrieval_metrics.py::test_k_must_be_positive[hit_at_k]
tests/unit/test_retrieval_metrics.py::test_k_must_be_positive[recall_at_k]
tests/unit/test_retrieval_schemas.py::test_retrieval_candidate_preserves_chunk_and_search_result_metadata
tests/unit/test_retrieval_schemas.py::test_retrieval_candidate_accepts_supported_methods[vector]
tests/unit/test_retrieval_schemas.py::test_retrieval_candidate_accepts_supported_methods[lexical]
tests/unit/test_retrieval_schemas.py::test_retrieval_candidate_rejects_unsupported_methods[]
tests/unit/test_retrieval_schemas.py::test_retrieval_candidate_rejects_unsupported_methods[semantic]
tests/unit/test_retrieval_schemas.py::test_retrieval_candidate_rejects_unsupported_methods[bm25]
tests/unit/test_retrieval_schemas.py::test_retrieval_candidate_rejects_unsupported_methods[VECTOR]
tests/unit/test_retrieval_schemas.py::test_retrieval_candidate_requires_one_based_positive_rank[0]
tests/unit/test_retrieval_schemas.py::test_retrieval_candidate_requires_one_based_positive_rank[-1]
tests/unit/test_retrieval_schemas.py::test_retrieval_candidate_requires_one_based_positive_rank[-10]
tests/unit/test_retrieval_schemas.py::test_retrieval_candidate_is_immutable
tests/unit/test_search_text.py::test_build_search_text_returns_original_text_without_section_context
tests/unit/test_search_text.py::test_build_search_text_adds_single_section_context
tests/unit/test_search_text.py::test_build_search_text_preserves_section_hierarchy
tests/unit/test_search_text.py::test_build_search_text_does_not_mutate_canonical_chunk_text
tests/unit/test_structure_aware_chunker.py::test_chunker_groups_text_blocks_from_same_section
tests/unit/test_structure_aware_chunker.py::test_chunker_starts_new_chunk_when_section_changes
tests/unit/test_structure_aware_chunker.py::test_chunker_splits_same_section_before_exceeding_max_size
tests/unit/test_structure_aware_chunker.py::test_chunker_preserves_multi_page_provenance
tests/unit/test_structure_aware_chunker.py::test_chunker_preserves_source_order
tests/unit/test_structure_aware_chunker.py::test_chunker_splits_single_text_block_that_exceeds_max_size
tests/unit/test_structure_aware_chunker.py::test_chunker_starts_new_chunk_after_reaching_target_size
tests/unit/test_structure_aware_chunker.py::test_chunker_rejects_zero_target_chars
tests/unit/test_structure_aware_chunker.py::test_chunker_rejects_zero_max_chars
tests/unit/test_structure_aware_chunker.py::test_chunker_rejects_target_chars_greater_than_max_chars
tests/unit/test_structure_aware_chunker.py::test_chunker_generates_globally_unique_ids_across_documents
tests/unit/test_structure_aware_chunker.py::test_chunker_rejects_empty_document_id[]
tests/unit/test_structure_aware_chunker.py::test_chunker_rejects_empty_document_id[   ]
tests/unit/test_structure_aware_chunker_multiblock.py::test_chunker_serializes_spreadsheet_blocks_into_retrieval_chunks
tests/unit/test_structure_aware_chunker_multiblock.py::test_chunker_preserves_text_behavior_and_global_identity
tests/unit/test_structure_aware_chunker_multiblock.py::test_oversized_spreadsheet_serialization_respects_max_chars
tests/unit/test_vector_index.py::test_vector_index_returns_candidates_by_cosine_similarity
tests/unit/test_vector_index.py::test_vector_index_uses_cosine_similarity_not_vector_magnitude
tests/unit/test_vector_index.py::test_vector_index_limits_results_to_top_k
tests/unit/test_vector_index.py::test_vector_index_returns_all_available_results_when_top_k_is_larger
tests/unit/test_vector_index.py::test_vector_index_breaks_equal_score_ties_by_insertion_order
tests/unit/test_vector_index.py::test_vector_index_rejects_invalid_index_data[chunk_ids0-embeddings0-chunk_ids]
tests/unit/test_vector_index.py::test_vector_index_rejects_invalid_index_data[chunk_ids1-embeddings1-same number]
tests/unit/test_vector_index.py::test_vector_index_rejects_invalid_index_data[chunk_ids2-embeddings2-duplicates]
tests/unit/test_vector_index.py::test_vector_index_rejects_invalid_index_data[chunk_ids3-embeddings3-consistent dimensions]
tests/unit/test_vector_index.py::test_vector_index_rejects_invalid_index_data[chunk_ids4-embeddings4-zero vectors]
tests/unit/test_vector_index.py::test_vector_index_rejects_search_before_indexing
tests/unit/test_vector_index.py::test_vector_index_rejects_invalid_top_k
tests/unit/test_vector_index.py::test_vector_index_rejects_query_with_wrong_dimension
tests/unit/test_vector_index.py::test_vector_index_rejects_zero_query_vector
tests/unit/test_vector_indexer.py::test_vector_indexer_builds_search_text_and_indexes_embeddings
tests/unit/test_vector_indexer.py::test_vector_indexer_rejects_empty_chunk_collection
tests/unit/test_vector_indexer.py::test_vector_indexer_rejects_embedding_count_mismatch
tests/unit/test_vector_retriever.py::test_vector_retriever_returns_canonical_retrieval_candidates
tests/unit/test_vector_retriever.py::test_vector_retriever_returns_original_canonical_chunk_objects
tests/unit/test_vector_retriever.py::test_vector_retriever_rejects_empty_query[]
tests/unit/test_vector_retriever.py::test_vector_retriever_rejects_empty_query[ ]
tests/unit/test_vector_retriever.py::test_vector_retriever_rejects_empty_query[\n\t]
tests/unit/test_vector_retriever.py::test_vector_retriever_rejects_empty_chunk_collection
tests/unit/test_vector_retriever.py::test_vector_retriever_rejects_duplicate_chunk_ids
tests/unit/test_vector_retriever.py::test_vector_retriever_rejects_unknown_chunk_id_from_index
tests/unit/test_xlsx_parser.py::test_parser_preserves_worksheet_boundaries
tests/unit/test_xlsx_parser.py::test_parser_preserves_sheet_ranges
tests/unit/test_xlsx_parser.py::test_parser_preserves_cell_coordinates_values_and_types
tests/unit/test_xlsx_parser.py::test_parser_preserves_formula_in_formula_field
tests/unit/test_xlsx_parser.py::test_parser_omits_empty_cells
tests/unit/test_xlsx_parser.py::test_parser_assigns_stable_block_order
tests/unit/test_xlsx_parser.py::test_parser_rejects_missing_file
tests/unit/test_xlsx_parser.py::test_parser_rejects_non_xlsx_source
tests/unit/test_xlsx_parser.py::test_parser_rejects_workbook_without_content

526 tests collected in 53.76s
```

## 11. Recent Commits

```text
17e5bc0 | 2026-11-04 09:54:05 -0300 | feat: validate hybrid retrieval v0.3 with document-aware selection
45a5a2c | 2026-11-04 00:33:15 -0300 | feat: implement hybrid retrieval with BM25 and RRF
43920d1 | 2026-11-02 00:00:42 -0300 | feat: establish multi-format Golden Set retrieval baseline
f5a09bb | 2026-11-01 22:25:09 -0300 | test: add multi-document vector retrieval benchmark
51519d5 | 2026-11-01 18:01:08 -0300 | feat: add globally unique retrieval chunk identity
0b5b6ee | 2026-10-08 04:22:46 -0300 | fix: restore README table formatting
efef5f8 | 2026-10-08 04:17:33 -0300 | fix: clean README markdown rendering
a036395 | 2026-10-08 04:10:51 -0300 | fix: correct README image rendering
22eb744 | 2026-10-08 04:03:35 -0300 | docs: refine README visuals and system overview
87b5c84 | 2026-10-08 03:55:06 -0300 | docs: update README and architecture overview
```

## 12. Working Tree

```text
State: DIRTY

Files:
?? app/retrieval/cross_encoder_scorer.py
?? app/retrieval/lexical_query_filter.py
?? app/retrieval/prefix_preserving_selector.py
?? app/retrieval/reranker.py
?? data/ground_truth/reranking_challenge_b.json
?? docs/validation/RV008_IMPLEMENTATION_GUIDE.md
?? docs/validation/RV008_RESULTS.json
?? docs/validation/RV009_ANALYSIS.md
?? docs/validation/RV009_REPLAY_RESULTS.json
?? docs/validation/RV009_REPLAY_RESULTS_local.json
?? docs/validation/RV010_IMPLEMENTATION_GUIDE.md
?? docs/validation/RV010_LIVE_RESULTS.json
?? docs/validation/RV010_PASSAGE_REVIEW.md
?? docs/validation/RV010_REVIEW_RESULTS.json
?? docs/validation/RV011_CANDIDATE_TRACE.json
?? docs/validation/RV012_ANALYSIS_AND_GUIDE.md
?? docs/validation/RV012_LEXICAL_REPLAY_RESULTS.json
?? docs/validation/RV012_LEXICAL_REPLAY_RESULTS_local.json
?? docs/validation/RV013_FILTERED_RERANK_RESULTS.json
?? docs/validation/RV013_IMPLEMENTATION_GUIDE.md
?? tests/smoke/smoke_candidate_trace.py
?? tests/smoke/smoke_filtered_reranking.py
?? tests/smoke/smoke_lexical_filter_replay.py
?? tests/smoke/smoke_prefix_reranking_live.py
?? tests/smoke/smoke_reranking_experiment.py
?? tests/smoke/smoke_reranking_replay.py
?? tests/unit/test_candidate_trace.py
?? tests/unit/test_cross_encoder_scorer.py
?? tests/unit/test_filtered_reranking.py
?? tests/unit/test_lexical_filter_replay.py
?? tests/unit/test_lexical_query_filter.py
?? tests/unit/test_prefix_preserving_selector.py
?? tests/unit/test_prefix_reranking_live.py
?? tests/unit/test_reranker.py
?? tests/unit/test_reranking_replay.py
```

## 13. Declared Dependencies

```text
pytest==9.1.1
PyYAML==6.0.3
docling==2.133.0
numpy==2.5.3
openai==3.26.0
```

## 14. Installed Dependencies

```text
accelerate==1.15.0
annotated-doc==0.0.5
annotated-types==0.8.0
antlr4-python3-runtime==4.9.3
anyio==4.15.1
attrs==26.1.0
beautifulsoup4==4.15.0
certifi==2026.7.22
charset-normalizer==3.5.2
click==8.5.0
colorama==0.4.6
colorlog==6.12.0
defusedxml==0.7.1
dill==0.4.1
doclang==0.7.3
docling==2.133.0
docling-core==2.99.0
docling-ibm-models==4.0.3
docling-parse==7.22.1
docling-slim==2.133.0
et_xmlfile==2.0.0
Faker==40.40.0
filelock==4.0.10
filetype==1.2.0
fsspec==2026.9.0
h11==0.16.0
hf-xet==1.6.0
httpcore==1.0.9
httpcore2==2.13.1
httpx==0.28.1
httpx2==2.13.1
huggingface_hub==1.33.0
idna==3.20
iniconfig==2.3.0
Jinja2==3.1.6
jiter==0.17.0
jsonref==1.1.0
jsonschema==4.26.0
jsonschema-specifications==2025.9.1
langcodes==3.5.1
latex2mathml==3.81.1
lxml==6.1.3
mail-parser==4.8.0
markdown-it-py==4.2.0
marko==2.2.4
MarkupSafe==3.0.4
mdurl==0.1.2
mpire==2.10.2
mpmath==1.3.0
multiprocess==0.70.19
networkx==3.7
numpy==2.5.3
olefile==0.47
omegaconf==2.3.1
openai==3.26.0
opencv-python==5.0.0.93
openpyxl==3.1.5
packaging==26.3
pandas==3.0.6
pillow==12.3.0
pluggy==1.6.0
polyfactory==3.3.0
psutil==7.2.2
pyclipper==1.4.0
pydantic==2.13.5
pydantic-settings==2.15.0
pydantic_core==2.46.5
Pygments==2.21.0
pylatexenc==2.11
pypdfium2==5.13.0
pytest==9.1.1
python-dateutil==2.9.0.post0
python-docx==1.2.0
python-dotenv==1.2.4
python-oxmsg==0.0.2
python-pptx==1.0.2
pywin32==312
PyYAML==6.0.3
rapidocr==3.9.2
referencing==0.37.0
regex==2026.9.29
requests==2.34.2
rich==15.0.0
rpds-py==2026.6.3
rtree==1.4.1
safetensors==0.8.0
scipy==1.18.1
semchunk==3.2.5
setuptools==84.0.0
shapely==2.1.2
shellingham==1.5.4
six==1.17.0
sniffio==1.3.1
soupsieve==2.10
sympy==1.14.0
tabulate==0.10.0
tokenizers==0.23.2
torch==2.14.1
torchvision==0.29.1
tqdm==4.70.1
transformers==5.18.0
tree-sitter==0.26.0
tree-sitter-c==0.24.2
tree-sitter-javascript==0.25.0
tree-sitter-python==0.25.0
tree-sitter-typescript==0.23.2
truststore==0.10.4
typer==0.26.8
typing-inspection==0.4.4
typing_extensions==4.16.0
tzdata==2026.5
urllib3==2.8.0
websockets==16.1.1
xlsxwriter==3.2.9
```

---

## Audit Purpose

This artifact is an automated snapshot of the current technical
state of the Enterprise Knowledge AI System.

Its purpose is to support development continuity, architecture
review, debugging, handoffs, and context recovery between human
developers and AI coding agents.

The audit records observable repository facts. Architectural intent,
design decisions, business semantics, and planned capabilities remain
the responsibility of the human-maintained project documentation.
