# PROJECT AUDIT — Enterprise Knowledge AI System

Version: 1.0
Generated: 2026-10-08 03:27:30

> This file is generated automatically by `app/scripts/project_audit.py`.
> Do not edit it manually.

## 1. Snapshot Integrity

```text
PASS

- HEAD before: e6f8769
- HEAD after: e6f8769
- Fingerprint before: c6d71022c8d8ca1a210bbe386ee68993ed607453ed0297cab9f9ed8d73f8c63d
- Fingerprint after: c6d71022c8d8ca1a210bbe386ee68993ed607453ed0297cab9f9ed8d73f8c63d
- Repository content remained stable during audit collection.
```

- Audit started: 2026-10-08 03:26:44
- Audit finished: 2026-10-08 03:27:30
- Duration: 46.10 seconds

## 2. Environment

- Python: 3.14.6
- Executable: `C:\Users\rods_\Desktop\AI - LAB\enterprise-knowledge-ai-system\.venv\Scripts\python.exe`
- Platform: Windows-10-10.0.19045-SP0

## 3. Git State

- Branch: `main`
- Commit: `e6f8769`

### Status

```text
A  app/retrieval/embeddings.py
A  app/retrieval/openai_embeddings.py
A  app/retrieval/schemas.py
A  app/retrieval/search_text.py
A  app/retrieval/vector_index.py
A  app/retrieval/vector_indexer.py
A  app/retrieval/vector_retriever.py
 M app/scripts/project_audit.py
 M docs/project_audit/PROJECT_AUDIT.md
A  docs/validation/RETRIEVAL_VALIDATION.md
M  requirements.txt
A  tests/smoke/smoke_openai_embeddings.py
A  tests/smoke/smoke_vector_retrieval.py
A  tests/unit/test_embedding_contract.py
A  tests/unit/test_openai_embeddings.py
A  tests/unit/test_retrieval_schemas.py
A  tests/unit/test_search_text.py
A  tests/unit/test_vector_index.py
A  tests/unit/test_vector_indexer.py
A  tests/unit/test_vector_retriever.py
?? docs/images/architecture-overview.png
```

## 4. Code Metrics

- Python files: **41**
- Total Python lines: **6727**
- Effective Python lines: **5137**
- Functions: **377**
- Classes: **40**
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
        [DIR] generation/
        [DIR] ingestion/
            [FILE] docling_parser.py
            [FILE] document_parser.py
            [FILE] pptx_native_enricher.py
            [FILE] registry.py
            [FILE] schemas.py
            [FILE] xlsx_parser.py
        [DIR] retriev/
        [DIR] retrieval/
            [FILE] embeddings.py
            [FILE] openai_embeddings.py
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
            [FILE] art-featured-product.png
            [FILE] art-featured.png
            [FILE] art-system-overview.png
        [DIR] project_audit/
        [DIR] validation/
            [FILE] RETRIEVAL_VALIDATION.md
    [FILE] README.md
    [FILE] requirements.txt
    [DIR] tests/
        [DIR] integration/
            [FILE] test_docling_corpus_integration.py
            [FILE] test_docling_docx_integration.py
            [FILE] test_docling_pdf_integration.py
            [FILE] test_docling_pptx_integration.py
            [FILE] test_document_parser_pptx_integration.py
            [FILE] test_xlsx_corpus_integration.py
        [DIR] smoke/
            [FILE] smoke_openai_embeddings.py
            [FILE] smoke_vector_retrieval.py
        [DIR] unit/
            [FILE] test_block_serializer.py
            [FILE] test_chunking_schemas.py
            [FILE] test_docling_parser.py
            [FILE] test_document_parser.py
            [FILE] test_embedding_contract.py
            [FILE] test_ingestion_registry.py
            [FILE] test_ingestion_schemas.py
            [FILE] test_openai_embeddings.py
            [FILE] test_pptx_native_enricher.py
            [FILE] test_retrieval_schemas.py
            [FILE] test_search_text.py
            [FILE] test_structure_aware_chunker.py
            [FILE] test_vector_index.py
            [FILE] test_vector_indexer.py
            [FILE] test_vector_retriever.py
            [FILE] test_xlsx_parser.py
```

## 6. Python Files

| File | Lines | Functions | Classes | TODOs | Syntax |
|---|---:|---:|---:|---:|---|
| `app/chunking/block_serializer.py` | 165 | 7 | 1 | 0 | OK |
| `app/chunking/schemas.py` | 55 | 1 | 1 | 0 | OK |
| `app/chunking/structure_aware_chunker.py` | 168 | 5 | 1 | 0 | OK |
| `app/ingestion/docling_parser.py` | 206 | 9 | 1 | 0 | OK |
| `app/ingestion/document_parser.py` | 80 | 4 | 1 | 0 | OK |
| `app/ingestion/pptx_native_enricher.py` | 279 | 11 | 1 | 0 | OK |
| `app/ingestion/registry.py` | 254 | 10 | 2 | 0 | OK |
| `app/ingestion/schemas.py` | 441 | 14 | 11 | 0 | OK |
| `app/ingestion/xlsx_parser.py` | 93 | 4 | 1 | 0 | OK |
| `app/retrieval/embeddings.py` | 17 | 2 | 1 | 0 | OK |
| `app/retrieval/openai_embeddings.py` | 74 | 4 | 1 | 0 | OK |
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
| `tests/integration/test_xlsx_corpus_integration.py` | 113 | 11 | 0 | 0 | OK |
| `tests/smoke/smoke_openai_embeddings.py` | 33 | 1 | 0 | 0 | OK |
| `tests/smoke/smoke_vector_retrieval.py` | 106 | 1 | 0 | 0 | OK |
| `tests/unit/test_block_serializer.py` | 182 | 6 | 0 | 0 | OK |
| `tests/unit/test_chunking_schemas.py` | 171 | 10 | 0 | 0 | OK |
| `tests/unit/test_docling_parser.py` | 330 | 20 | 1 | 0 | OK |
| `tests/unit/test_document_parser.py` | 266 | 12 | 0 | 0 | OK |
| `tests/unit/test_embedding_contract.py` | 37 | 5 | 1 | 0 | OK |
| `tests/unit/test_ingestion_registry.py` | 226 | 19 | 0 | 0 | OK |
| `tests/unit/test_ingestion_schemas.py` | 670 | 38 | 0 | 0 | OK |
| `tests/unit/test_openai_embeddings.py` | 175 | 17 | 8 | 0 | OK |
| `tests/unit/test_pptx_native_enricher.py` | 280 | 16 | 0 | 0 | OK |
| `tests/unit/test_retrieval_schemas.py` | 85 | 6 | 0 | 0 | OK |
| `tests/unit/test_search_text.py` | 53 | 5 | 0 | 0 | OK |
| `tests/unit/test_structure_aware_chunker.py` | 174 | 11 | 0 | 0 | OK |
| `tests/unit/test_vector_index.py` | 115 | 10 | 0 | 0 | OK |
| `tests/unit/test_vector_indexer.py` | 100 | 8 | 2 | 0 | OK |
| `tests/unit/test_vector_retriever.py` | 123 | 10 | 1 | 0 | OK |
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
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_preserves_content_and_source_traceability
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_supports_multi_block_and_multi_page_provenance
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_supports_slide_provenance
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_supports_worksheet_provenance
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_rejects_empty_required_text_fields[chunk_id-]
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_rejects_empty_required_text_fields[chunk_id-   ]
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_rejects_empty_required_text_fields[text-]
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_rejects_empty_required_text_fields[text-   ]
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_rejects_negative_order
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_requires_source_blocks
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_requires_content_types
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_rejects_duplicate_provenance_values
tests/unit/test_chunking_schemas.py::test_retrieval_chunk_rejects_invalid_page_number
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

271 tests collected in 12.84s
```

## 11. Recent Commits

```text
e6f8769 | 2026-10-06 21:19:54 -0300 | docs: add featured product artwork
e13a446 | 2026-10-06 21:19:09 -0300 | feat: add deterministic structure-aware chunking foundation
9bce47f | 2026-10-04 22:51:34 -0300 | feat: complete multi-source parsing and canonical normalization
21fafa8 | 2026-10-04 01:12:51 -0300 | feat: add multi-format canonical ingestion baseline
1b2b410 | 2026-10-03 01:40:27 -0300 | fix: correct declared project dependencies
5596a6e | 2026-10-03 01:38:31 -0300 | feat: add controlled document registry loader
122818d | 2026-10-03 01:31:35 -0300 | feat: define canonical document ingestion contract
36caaa7 | 2026-10-03 01:24:50 -0300 | chore: establish project audit and development baseline
f19fad3 | 2026-10-01 18:25:11 -0300 | docs: add conceptual system overview to README
390b18e | 2026-10-01 18:01:13 -0300 | feat: establish enterprise knowledge universe and ground truth
```

## 12. Working Tree

```text
State: DIRTY

Files:
A  app/retrieval/embeddings.py
A  app/retrieval/openai_embeddings.py
A  app/retrieval/schemas.py
A  app/retrieval/search_text.py
A  app/retrieval/vector_index.py
A  app/retrieval/vector_indexer.py
A  app/retrieval/vector_retriever.py
 M app/scripts/project_audit.py
 M docs/project_audit/PROJECT_AUDIT.md
A  docs/validation/RETRIEVAL_VALIDATION.md
M  requirements.txt
A  tests/smoke/smoke_openai_embeddings.py
A  tests/smoke/smoke_vector_retrieval.py
A  tests/unit/test_embedding_contract.py
A  tests/unit/test_openai_embeddings.py
A  tests/unit/test_retrieval_schemas.py
A  tests/unit/test_search_text.py
A  tests/unit/test_vector_index.py
A  tests/unit/test_vector_indexer.py
A  tests/unit/test_vector_retriever.py
?? docs/images/architecture-overview.png

Unstaged diff:
app/scripts/project_audit.py        |  20 ++--
 docs/project_audit/PROJECT_AUDIT.md | 226 +++++++++++++++++++++++++++---------
 2 files changed, 184 insertions(+), 62 deletions(-)

Staged diff:
app/retrieval/embeddings.py             |  17 +++
 app/retrieval/openai_embeddings.py      |  74 ++++++++++++
 app/retrieval/schemas.py                |  26 +++++
 app/retrieval/search_text.py            |  13 +++
 app/retrieval/vector_index.py           |  91 +++++++++++++++
 app/retrieval/vector_indexer.py         |  36 ++++++
 app/retrieval/vector_retriever.py       |  58 ++++++++++
 docs/validation/RETRIEVAL_VALIDATION.md | 193 ++++++++++++++++++++++++++++++++
 requirements.txt                        |   4 +-
 tests/smoke/smoke_openai_embeddings.py  |  33 ++++++
 tests/smoke/smoke_vector_retrieval.py   | 106 ++++++++++++++++++
 tests/unit/test_embedding_contract.py   |  37 ++++++
 tests/unit/test_openai_embeddings.py    | 175 +++++++++++++++++++++++++++++
 tests/unit/test_retrieval_schemas.py    |  85 ++++++++++++++
 tests/unit/test_search_text.py          |  53 +++++++++
 tests/unit/test_vector_index.py         | 115 +++++++++++++++++++
 tests/unit/test_vector_indexer.py       | 100 +++++++++++++++++
 tests/unit/test_vector_retriever.py     | 123 ++++++++++++++++++++
 18 files changed, 1338 insertions(+), 1 deletion(-)
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
