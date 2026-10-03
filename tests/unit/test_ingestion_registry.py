"""Unit tests for the controlled document registry loader."""

from pathlib import Path

import pytest
import yaml

from app.ingestion.registry import load_document_registry


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REAL_REGISTRY = PROJECT_ROOT / "data" / "ground_truth" / "document_registry.yaml"


def write_registry(tmp_path: Path, documents: list[dict]) -> Path:
    path = tmp_path / "document_registry.yaml"
    payload = {
        "schema_version": "0.1",
        "documents": documents,
    }
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
    return path


def valid_document(
    document_id: str = "DOC-001",
    key: str = "transportation_policy_2026",
    **overrides,
) -> dict:
    document = {
        "document_id": document_id,
        "key": key,
        "title": "Transportation Policy",
        "document_type": "corporate_policy",
        "format": "pdf",
        "domain": "transportation",
        "version": "3.0",
        "effective_date": "2026-01-01",
        "status": "active",
        "authority_level": 4,
        "supersedes": None,
        "superseded_by": None,
        # Evaluation-only fields deliberately exist in the source registry.
        "canonical_fact_paths": ["canonical_knowledge.transportation.otif"],
        "evaluation_roles": ["current_authority"],
    }
    document.update(overrides)
    return document


def test_real_registry_loads_all_27_controlled_documents() -> None:
    registry = load_document_registry(REAL_REGISTRY)

    assert len(registry.documents) == 27


def test_real_registry_supports_lookup_by_id_and_key() -> None:
    registry = load_document_registry(REAL_REGISTRY)

    by_id = registry.by_id("DOC-001")
    by_key = registry.by_key("transportation_policy_2026")

    assert by_id == by_key
    assert by_id.title == "Transportation Policy"
    assert by_id.status == "active"
    assert by_id.authority_level == 4


def test_real_registry_preserves_lifecycle_relationship() -> None:
    registry = load_document_registry(REAL_REGISTRY)

    current = registry.by_id("DOC-001")
    previous = registry.by_id("DOC-002")

    assert current.supersedes == "DOC-002"
    assert previous.superseded_by == "DOC-001"
    assert previous.status == "superseded"


def test_real_registry_preserves_entity_references() -> None:
    registry = load_document_registry(REAL_REGISTRY)

    atlas_contract = registry.by_id("DOC-014")

    assert atlas_contract.entity_refs == ("CAR-ATLAS",)


def test_runtime_metadata_excludes_evaluation_only_fields() -> None:
    registry = load_document_registry(REAL_REGISTRY)
    document = registry.by_id("DOC-001")

    assert not hasattr(document, "canonical_fact_paths")
    assert not hasattr(document, "evaluation_roles")


def test_real_registry_contains_only_supported_authority_levels() -> None:
    registry = load_document_registry(REAL_REGISTRY)

    assert {document.authority_level for document in registry.documents} <= {
        1,
        2,
        3,
        4,
    }


def test_real_registry_contains_expected_formats() -> None:
    registry = load_document_registry(REAL_REGISTRY)

    assert {document.format for document in registry.documents} == {
        "pdf",
        "docx",
        "xlsx",
        "pptx",
        "md",
        "txt",
    }


def test_lookup_unknown_document_id_raises_key_error() -> None:
    registry = load_document_registry(REAL_REGISTRY)

    with pytest.raises(KeyError, match="DOC-999"):
        registry.by_id("DOC-999")


def test_lookup_unknown_document_key_raises_key_error() -> None:
    registry = load_document_registry(REAL_REGISTRY)

    with pytest.raises(KeyError, match="unknown_key"):
        registry.by_key("unknown_key")


def test_loader_rejects_duplicate_document_ids(tmp_path: Path) -> None:
    path = write_registry(
        tmp_path,
        [
            valid_document(),
            valid_document(key="different_key"),
        ],
    )

    with pytest.raises(ValueError, match="Duplicate document_id"):
        load_document_registry(path)


def test_loader_rejects_duplicate_document_keys(tmp_path: Path) -> None:
    path = write_registry(
        tmp_path,
        [
            valid_document(),
            valid_document(document_id="DOC-002"),
        ],
    )

    with pytest.raises(ValueError, match="Duplicate document keys"):
        load_document_registry(path)


@pytest.mark.parametrize("authority_level", [0, 5, -1])
def test_loader_rejects_invalid_authority_level(
    tmp_path: Path,
    authority_level: int,
) -> None:
    path = write_registry(
        tmp_path,
        [valid_document(authority_level=authority_level)],
    )

    with pytest.raises(ValueError, match="authority_level"):
        load_document_registry(path)


def test_loader_rejects_invalid_lifecycle_status(tmp_path: Path) -> None:
    path = write_registry(
        tmp_path,
        [valid_document(status="draft")],
    )

    with pytest.raises(ValueError, match="lifecycle status"):
        load_document_registry(path)


def test_loader_rejects_unknown_supersedes_reference(tmp_path: Path) -> None:
    path = write_registry(
        tmp_path,
        [valid_document(supersedes="DOC-999")],
    )

    with pytest.raises(ValueError, match="unknown document"):
        load_document_registry(path)


def test_loader_rejects_inconsistent_lifecycle_relationship(
    tmp_path: Path,
) -> None:
    current = valid_document(
        document_id="DOC-001",
        key="current_policy",
        supersedes="DOC-002",
    )
    previous = valid_document(
        document_id="DOC-002",
        key="previous_policy",
        status="superseded",
        superseded_by=None,
    )
    path = write_registry(tmp_path, [current, previous])

    with pytest.raises(ValueError, match="Inconsistent lifecycle relationship"):
        load_document_registry(path)


def test_loader_requires_path_object() -> None:
    with pytest.raises(TypeError, match="path"):
        load_document_registry("document_registry.yaml")


def test_loader_rejects_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "missing.yaml"

    with pytest.raises(FileNotFoundError):
        load_document_registry(path)
