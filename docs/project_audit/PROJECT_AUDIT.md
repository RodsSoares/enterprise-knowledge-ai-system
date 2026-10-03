# PROJECT AUDIT — Enterprise Knowledge AI System

Version: 1.0
Generated: 2026-10-03 01:22:00

> This file is generated automatically by `app/scripts/project_audit.py`.
> Do not edit it manually.

## 1. Snapshot Integrity

```text
PASS

- HEAD before: f19fad3
- HEAD after: f19fad3
- Fingerprint before: b2429064d7472c6727cc8d7ad22600a7b3180fdd43470529a6726c240b1f7da3
- Fingerprint after: b2429064d7472c6727cc8d7ad22600a7b3180fdd43470529a6726c240b1f7da3
- Repository content remained stable during audit collection.
```

- Audit started: 2026-10-03 01:21:55
- Audit finished: 2026-10-03 01:22:00
- Duration: 4.83 seconds

## 2. Environment

- Python: 3.14.6
- Executable: `C:\Users\rods_\Desktop\AI - LAB\enterprise-knowledge-ai-system\.venv\Scripts\python.exe`
- Platform: Windows-10-10.0.19045-SP0

## 3. Git State

- Branch: `main`
- Commit: `f19fad3`

### Status

```text
?? app/
?? docs/images/art-featured.png
```

## 4. Code Metrics

- Python files: **1**
- Total Python lines: **708**
- Effective Python lines: **470**
- Functions: **28**
- Classes: **0**
- TODO/FIXME occurrences: **2**
- Files with syntax errors: **0**

## 5. Project Structure

```text
enterprise-knowledge-ai-system/
    [FILE] .gitignore
    [DIR] app/
        [DIR] evaluation/
        [DIR] generation/
        [DIR] ingestion/
        [DIR] retrieval/
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
            [FILE] art-featured.png
            [FILE] art-system-overview.png
        [DIR] project_audit/
    [FILE] README.md
    [DIR] tests/
        [DIR] integration/
        [DIR] unit/
```

## 6. Python Files

| File | Lines | Functions | Classes | TODOs | Syntax |
|---|---:|---:|---:|---:|---|
| `app/scripts/project_audit.py` | 708 | 28 | 0 | 2 | OK |

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

## 9. Test Execution

```text
C:\Users\rods_\Desktop\AI - LAB\enterprise-knowledge-ai-system\.venv\Scripts\python.exe: No module named pytest
```

## 10. Test Discovery / Behavioral Contracts

```text
C:\Users\rods_\Desktop\AI - LAB\enterprise-knowledge-ai-system\.venv\Scripts\python.exe: No module named pytest
```

## 11. Recent Commits

```text
f19fad3 | 2026-10-01 18:25:11 -0300 | docs: add conceptual system overview to README
390b18e | 2026-10-01 18:01:13 -0300 | feat: establish enterprise knowledge universe and ground truth
3142cc7 | 2026-10-01 15:35:58 -0300 | docs: initialize Enterprise Knowledge AI System
```

## 12. Working Tree

```text
State: DIRTY

Files:
?? app/
?? docs/images/art-featured.png
```

## 13. Declared Dependencies

```text
requirements.txt not found.
```

## 14. Installed Dependencies

```text
Sem saída.
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
