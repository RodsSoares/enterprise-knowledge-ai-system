"""Unit tests for the canonical ingestion schemas."""

from datetime import date
from pathlib import Path

import pytest

from app.ingestion.schemas import CanonicalDocument


def build_document(**overrides) -> CanonicalDocument:
    """Create a valid canonical document with optional field overrides."""
    values = {
        "document_id": "DOC-001",
        "key": "transportation_policy_2026",
        "title": "Transportation Policy",
        "source_path": Path(
            "data/source/corporate_repository/policies/"
            "DOC-001_Transportation_Policy_2026.pdf"
        ),
        "format": "pdf",
        "document_type": "corporate_policy",
        "domain": "transportation",
        "version": "3.0",
        "effective_date": date(2026, 1, 1),
        "status": "active",
        "authority_level": 4,
        "extracted_text": "Controlled transportation policy content.",
        "supersedes": "DOC-002",
        "superseded_by": None,
        "entity_refs": (),
    }
    values.update(overrides)
    return CanonicalDocument(**values)


def test_canonical_document_preserves_identity_governance_and_content() -> None:
    document = build_document()

    assert document.document_id == "DOC-001"
    assert document.key == "transportation_policy_2026"
    assert document.title == "Transportation Policy"
    assert document.format == "pdf"
    assert document.document_type == "corporate_policy"
    assert document.domain == "transportation"
    assert document.version == "3.0"
    assert document.effective_date == date(2026, 1, 1)
    assert document.status == "active"
    assert document.authority_level == 4
    assert document.supersedes == "DOC-002"
    assert document.superseded_by is None
    assert document.extracted_text == "Controlled transportation policy content."


def test_canonical_document_supports_entity_references() -> None:
    document = build_document(
        document_id="DOC-014",
        key="carrier_atlas_contract",
        title="Carrier Atlas Contract",
        document_type="contract",
        domain="transportation",
        version="2026",
        authority_level=3,
        supersedes=None,
        entity_refs=("CAR-ATLAS",),
    )

    assert document.entity_refs == ("CAR-ATLAS",)


@pytest.mark.parametrize("authority_level", [1, 2, 3, 4])
def test_canonical_document_accepts_registry_authority_levels(
    authority_level: int,
) -> None:
    document = build_document(authority_level=authority_level)

    assert document.authority_level == authority_level


@pytest.mark.parametrize("authority_level", [0, 5, -1])
def test_canonical_document_rejects_invalid_authority_level(
    authority_level: int,
) -> None:
    with pytest.raises(ValueError, match="authority_level"):
        build_document(authority_level=authority_level)


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("document_id", ""),
        ("key", "   "),
        ("title", ""),
        ("document_type", ""),
        ("domain", ""),
        ("version", ""),
        ("extracted_text", "   "),
    ],
)
def test_canonical_document_rejects_required_blank_fields(
    field_name: str,
    invalid_value: str,
) -> None:
    with pytest.raises(ValueError):
        build_document(**{field_name: invalid_value})


def test_canonical_document_requires_path_object() -> None:
    with pytest.raises(TypeError, match="source_path"):
        build_document(source_path="data/source/document.pdf")


@pytest.mark.parametrize("relationship_field", ["supersedes", "superseded_by"])
def test_document_cannot_reference_itself_as_lifecycle_relationship(
    relationship_field: str,
) -> None:
    with pytest.raises(ValueError, match="itself"):
        build_document(**{relationship_field: "DOC-001"})
