"""Controlled document registry loader for the ingestion layer.

The registry is control metadata. It is not RAG corpus content and must not be
indexed as enterprise evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
from typing import Any

import yaml


DOCUMENT_ID_PATTERN = re.compile(r"^DOC-\d{3}$")
VALID_STATUSES = {"active", "superseded", "historical"}
VALID_AUTHORITY_LEVELS = {1, 2, 3, 4}
VALID_FORMATS = {"pdf", "docx", "xlsx", "pptx", "md", "txt"}


@dataclass(frozen=True, slots=True)
class DocumentMetadata:
    """Validated runtime metadata for one controlled enterprise document."""

    document_id: str
    key: str
    title: str
    document_type: str
    format: str
    domain: str
    version: str
    effective_date: date
    status: str
    authority_level: int
    supersedes: str | None = None
    superseded_by: str | None = None
    entity_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DocumentRegistry:
    """Validated collection of runtime document metadata."""

    documents: tuple[DocumentMetadata, ...]

    def by_id(self, document_id: str) -> DocumentMetadata:
        """Return one document by controlled document ID."""
        for document in self.documents:
            if document.document_id == document_id:
                return document
        raise KeyError(f"Unknown document_id: {document_id}")

    def by_key(self, key: str) -> DocumentMetadata:
        """Return one document by stable registry key."""
        for document in self.documents:
            if document.key == key:
                return document
        raise KeyError(f"Unknown document key: {key}")


def _require_non_empty_string(record: dict[str, Any], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string.")
    return value.strip()


def _parse_effective_date(value: Any) -> date:
    if isinstance(value, date):
        return value

    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                f"effective_date must use ISO format YYYY-MM-DD: {value!r}"
            ) from exc

    raise ValueError("effective_date must be a date or ISO date string.")


def _optional_document_id(value: Any, field: str) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str) or not DOCUMENT_ID_PATTERN.fullmatch(value):
        raise ValueError(f"{field} must be null or match DOC-###.")

    return value


def _parse_entity_refs(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()

    if not isinstance(value, list):
        raise ValueError("entity_refs must be a list when present.")

    refs: list[str] = []
    for ref in value:
        if not isinstance(ref, str) or not ref.strip():
            raise ValueError("entity_refs entries must be non-empty strings.")
        refs.append(ref.strip())

    if len(refs) != len(set(refs)):
        raise ValueError("entity_refs must not contain duplicates.")

    return tuple(refs)


def _parse_document(record: Any) -> DocumentMetadata:
    if not isinstance(record, dict):
        raise ValueError("Each registry document must be a mapping.")

    document_id = _require_non_empty_string(record, "document_id")
    if not DOCUMENT_ID_PATTERN.fullmatch(document_id):
        raise ValueError(
            f"document_id must match DOC-###: {document_id!r}"
        )

    document_format = _require_non_empty_string(record, "format").lower()
    if document_format not in VALID_FORMATS:
        raise ValueError(
            f"Unsupported document format for {document_id}: {document_format!r}"
        )

    status = _require_non_empty_string(record, "status").lower()
    if status not in VALID_STATUSES:
        raise ValueError(
            f"Invalid lifecycle status for {document_id}: {status!r}"
        )

    authority_level = record.get("authority_level")
    if authority_level not in VALID_AUTHORITY_LEVELS:
        raise ValueError(
            f"Invalid authority_level for {document_id}: {authority_level!r}"
        )

    return DocumentMetadata(
        document_id=document_id,
        key=_require_non_empty_string(record, "key"),
        title=_require_non_empty_string(record, "title"),
        document_type=_require_non_empty_string(record, "document_type"),
        format=document_format,
        domain=_require_non_empty_string(record, "domain"),
        version=_require_non_empty_string(record, "version"),
        effective_date=_parse_effective_date(record.get("effective_date")),
        status=status,
        authority_level=authority_level,
        supersedes=_optional_document_id(record.get("supersedes"), "supersedes"),
        superseded_by=_optional_document_id(
            record.get("superseded_by"), "superseded_by"
        ),
        entity_refs=_parse_entity_refs(record.get("entity_refs")),
    )


def _validate_unique_documents(documents: tuple[DocumentMetadata, ...]) -> None:
    ids = [document.document_id for document in documents]
    keys = [document.key for document in documents]

    duplicate_ids = sorted({value for value in ids if ids.count(value) > 1})
    duplicate_keys = sorted({value for value in keys if keys.count(value) > 1})

    if duplicate_ids:
        raise ValueError(
            f"Duplicate document_id values: {', '.join(duplicate_ids)}"
        )

    if duplicate_keys:
        raise ValueError(
            f"Duplicate document keys: {', '.join(duplicate_keys)}"
        )


def _validate_lifecycle_relationships(
    documents: tuple[DocumentMetadata, ...],
) -> None:
    by_id = {document.document_id: document for document in documents}

    for document in documents:
        if document.document_id in {document.supersedes, document.superseded_by}:
            raise ValueError(
                f"{document.document_id} cannot reference itself in lifecycle metadata."
            )

        if document.supersedes is not None and document.supersedes not in by_id:
            raise ValueError(
                f"{document.document_id} supersedes unknown document "
                f"{document.supersedes}."
            )

        if (
            document.superseded_by is not None
            and document.superseded_by not in by_id
        ):
            raise ValueError(
                f"{document.document_id} is superseded by unknown document "
                f"{document.superseded_by}."
            )

    for document in documents:
        if document.supersedes is not None:
            older = by_id[document.supersedes]
            if older.superseded_by != document.document_id:
                raise ValueError(
                    f"Inconsistent lifecycle relationship: "
                    f"{document.document_id} supersedes {older.document_id}, "
                    f"but {older.document_id}.superseded_by is "
                    f"{older.superseded_by!r}."
                )

        if document.superseded_by is not None:
            newer = by_id[document.superseded_by]
            if newer.supersedes != document.document_id:
                raise ValueError(
                    f"Inconsistent lifecycle relationship: "
                    f"{document.document_id} is superseded by "
                    f"{newer.document_id}, but {newer.document_id}.supersedes "
                    f"is {newer.supersedes!r}."
                )


def load_document_registry(path: Path) -> DocumentRegistry:
    """Load and validate controlled runtime metadata from document_registry.yaml."""
    if not isinstance(path, Path):
        raise TypeError("path must be a pathlib.Path.")

    if not path.is_file():
        raise FileNotFoundError(f"Document registry not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        payload = yaml.safe_load(file)

    if not isinstance(payload, dict):
        raise ValueError("Document registry root must be a mapping.")

    raw_documents = payload.get("documents")
    if not isinstance(raw_documents, list):
        raise ValueError("Document registry must contain a documents list.")

    documents = tuple(_parse_document(record) for record in raw_documents)

    if not documents:
        raise ValueError("Document registry must contain at least one document.")

    _validate_unique_documents(documents)
    _validate_lifecycle_relationships(documents)

    return DocumentRegistry(documents=documents)
