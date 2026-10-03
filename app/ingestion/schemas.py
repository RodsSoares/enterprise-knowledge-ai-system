"""Canonical ingestion schemas for the Enterprise Knowledge AI System.

This module defines the deterministic contract produced by the ingestion layer.
Format-specific parsers are responsible for extracting content, while the
document registry is responsible for controlled identity and governance metadata.

Evaluation-only metadata such as ``canonical_fact_paths`` and
``evaluation_roles`` intentionally does not belong to this runtime contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal


DocumentFormat = Literal["pdf", "docx", "xlsx", "pptx", "md", "txt"]
LifecycleStatus = Literal["active", "superseded", "historical"]


@dataclass(frozen=True, slots=True)
class CanonicalDocument:
    """Canonical representation of an enterprise document after ingestion.

    Content comes from the physical source document.
    Identity and governance metadata come from the controlled document registry.
    """

    document_id: str
    key: str
    title: str

    source_path: Path
    format: DocumentFormat

    document_type: str
    domain: str
    version: str
    effective_date: date
    status: LifecycleStatus
    authority_level: int

    extracted_text: str

    supersedes: str | None = None
    superseded_by: str | None = None
    entity_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate invariants that belong to the canonical document contract."""
        if not self.document_id.strip():
            raise ValueError("document_id must not be empty.")

        if not self.key.strip():
            raise ValueError("key must not be empty.")

        if not self.title.strip():
            raise ValueError("title must not be empty.")

        if not self.document_type.strip():
            raise ValueError("document_type must not be empty.")

        if not self.domain.strip():
            raise ValueError("domain must not be empty.")

        if not self.version.strip():
            raise ValueError("version must not be empty.")

        if not isinstance(self.source_path, Path):
            raise TypeError("source_path must be a pathlib.Path.")

        if self.authority_level not in {1, 2, 3, 4}:
            raise ValueError("authority_level must be one of: 1, 2, 3, 4.")

        if not self.extracted_text.strip():
            raise ValueError("extracted_text must not be empty.")

        if self.document_id in {self.supersedes, self.superseded_by}:
            raise ValueError("A document cannot supersede or be superseded by itself.")
