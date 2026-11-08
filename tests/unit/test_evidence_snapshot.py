"""Reconstruction, source binding and offline index tests for the v2 catalog."""
import json
from pathlib import Path

import pytest

from app.chunking.evidence_snapshot import (
    build_lexical_index, document_record, file_hash, make_snapshot, verify_snapshot,
)
from app.chunking.evidence_units import UnitConfig, digest
from app.ingestion.schemas import NormalizedContent, TextBlock
from app.ingestion.xlsx_parser import XlsxParser


def snapshot(tmp_path):
    path = tmp_path / "policy.md"
    path.write_text("Restricted transfers require approval.", encoding="utf-8")
    content = NormalizedContent((TextBlock("p", 0, "paragraph", path.read_text()),))
    return make_snapshot([document_record(content, document_id="DOC-099", title="Sharing",
        source_path=path.name, source_revision=file_hash(path))])


def test_roundtrip_reconstructs_sources_and_lexical_index(tmp_path):
    envelope = json.loads(json.dumps(snapshot(tmp_path)))
    units = verify_snapshot(envelope, root=tmp_path)
    hit, = build_lexical_index(envelope).search("DOC-099")
    assert hit.chunk_id == units[0].unit_id
    assert units[0].source_refs[0].block_id == "p"


def test_changed_physical_source_invalidates_catalog(tmp_path):
    envelope = snapshot(tmp_path)
    (tmp_path / "policy.md").write_text("Changed", encoding="utf-8")
    with pytest.raises(ValueError, match="Physical source"):
        verify_snapshot(envelope, root=tmp_path)


def test_tampered_projection_rejected_even_with_recomputed_outer_hash(tmp_path):
    envelope = snapshot(tmp_path)
    envelope["snapshot"]["documents"][0]["units"][0]["reading_text"] = "Permission invented"
    envelope["snapshot_id"] = digest(envelope["snapshot"])
    with pytest.raises(ValueError, match="reconstruction"):
        verify_snapshot(envelope)


def test_v1_snapshot_not_silently_upgraded(tmp_path):
    envelope = snapshot(tmp_path)
    envelope["snapshot"]["schema_version"] = "1.0"
    envelope["snapshot_id"] = digest(envelope["snapshot"])
    with pytest.raises(ValueError, match="version"):
        verify_snapshot(envelope)


def test_real_workbook_projects_all_eight_decisions_with_original_roles():
    root = Path(__file__).resolve().parents[2]
    config = json.loads((root / "docs/validation/EVIDENCE_UNITS_CONFIG.json").read_text())
    path = root / "data/source/corporate_repository/governance/DOC-012_Approval_Authority_Matrix.xlsx"
    settings = config["documents"]["DOC-012"]
    assert file_hash(path) == settings["source_sha256"]
    content = XlsxParser().parse(path)
    record = document_record(content, document_id="DOC-012", title="Approval Authority Matrix",
        source_path=path.relative_to(root).as_posix(), source_revision=file_hash(path),
        config=UnitConfig.from_dict(dict(max_chars=config["max_chars"],
                                       spreadsheet_headers=settings["spreadsheet_headers"])))
    units = verify_snapshot(make_snapshot([record]), root=root)
    rows = [u for u in units if u.structural_role == "table_record" and "Sheet: Approval Matrix;" in u.reading_text]
    assert len(rows) == 8
    target = next(u for u in rows if "row: 9\n" in u.reading_text)
    assert "Required Approval [C1] | C9 = Information Security Owner + AI Governance Owner" in target.reading_text
    assert "Additional Review [D1] | D9 = Data Owner" in target.reading_text
    assert "Tool and use case must be approved" in target.reading_text
