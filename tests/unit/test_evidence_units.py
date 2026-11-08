"""Structural fidelity and atomic context assembly; no model-quality assertions."""
from dataclasses import replace

import pytest

from app.chunking.evidence_units import (
    EvidenceUnitBuilder, SpreadsheetHeader, UnitConfig, materialize, validate_units,
)
from app.ingestion.schemas import (
    NormalizedContent, SourceLocation, SpreadsheetBlock, SpreadsheetCell, TableBlock, TextBlock,
)


REVISION = "a" * 64


def build(blocks, config=None):
    return EvidenceUnitBuilder(config).build(NormalizedContent(tuple(blocks)),
        document_id="DOC-099", title="Example policy", source_revision=REVISION)


def table_section():
    location = SourceLocation(page_number=1, section_path=("Controls",))
    return (
        TextBlock("heading", 0, "heading", "Controls", location),
        TableBlock("rules", 1, (("Public", "Approved public use"),
            ("Restricted", "Explicit authorization")), location, ("Class", "Requirement"),
            parent_id="heading"),
        TextBlock("note", 2, "paragraph", "An operational SOP cannot grant an exception.", location),
    )


def matrix():
    values = (("Decision", "Required Approval", "Additional Review", "Notes"),
              ("Confidential data in AI", "Security + AI Governance", "Data Owner", "Tool AND use case approved"),
              ("New contract", "Procurement", "Legal", "Within budget"))
    block = SpreadsheetBlock("sheet", 0, "Approvals", tuple(
        SpreadsheetCell(f"{chr(65+c)}{r+1}", value) for r, row in enumerate(values)
        for c, value in enumerate(row)))
    hint = SpreadsheetHeader("sheet", "Approvals", ("A1", "B1", "C1", "D1"), values[0])
    return block, hint


def test_section_keeps_heading_table_and_notes_despite_different_types():
    units = build(table_section())
    searchable = [u for u in units if u.searchable]
    assert len(searchable) == 1
    unit = searchable[0]
    assert unit.structural_role == "section"
    assert all(s in unit.reading_text for s in ("Controls", "Public", "Restricted", "cannot grant"))
    assert {r.block_id for r in unit.source_refs} == {"heading", "rules", "note"}
    assert "DOC-099" in unit.search_text and "Example policy" in unit.search_text


def test_sections_do_not_merge_and_no_section_is_not_a_shared_section():
    blocks = [TextBlock("a", 0, "paragraph", "First", SourceLocation(section_path=("A",))),
              TextBlock("b", 1, "paragraph", "Second", SourceLocation(section_path=("B",))),
              TextBlock("c", 2, "paragraph", "Unscoped"), TextBlock("d", 3, "paragraph", "Separate")]
    assert [u.reading_text for u in build(blocks)] == ["First", "Second", "Unscoped", "Separate"]


def test_headings_alone_are_navigation_not_searchable_rule_units():
    location = SourceLocation(section_path=("Scope",))
    units = build([TextBlock("a", 0, "title", "Policy", location),
                   TextBlock("b", 1, "heading", "Scope", location)])
    assert not any(u.searchable for u in units)
    assert units[0].structural_role == "navigation"


def test_matrix_records_preserve_approval_review_conjunction_and_coordinates():
    block, hint = matrix()
    units = build([block], UnitConfig(1800, (hint,)))
    rows = [u for u in units if u.structural_role == "table_record"]
    assert len(rows) == 2
    row = rows[0]
    assert "Required Approval [B1] | B2 = Security + AI Governance" in row.reading_text
    assert "Additional Review [C1] | C2 = Data Owner" in row.reading_text
    assert "Tool AND use case approved" in row.reading_text
    assert "New contract" not in row.reading_text
    assert row.parent_id == units[0].unit_id
    assert len(row.source_refs) == 8
    chosen, rendered = materialize(units, [row.unit_id], max_chars=1800)
    assert chosen == (row,) and "New contract" not in rendered


def test_unreviewed_matrix_does_not_guess_headers():
    block, _ = matrix()
    units = build([block])
    assert len(units) == 1 and units[0].status == "unresolved_structure"
    with pytest.raises(ValueError, match="requires review"):
        materialize(units, [units[0].unit_id], max_chars=1800)


@pytest.mark.parametrize("kind", ["wrong_label", "missing_cell", "wrong_sheet", "extra_row"])
def test_ambiguous_or_stale_matrix_configuration_fails(kind):
    block, hint = matrix()
    if kind == "wrong_label":
        hint = replace(hint, expected_labels=("Wrong", *hint.expected_labels[1:]))
    elif kind == "missing_cell":
        block = replace(block, cells=block.cells[:-1])
    elif kind == "wrong_sheet":
        hint = replace(hint, sheet_name="Other")
    else:
        block = replace(block, cells=(*block.cells, SpreadsheetCell("A5", "Footnote")))
    with pytest.raises(ValueError):
        build([block], UnitConfig(1800, (hint,)))


def test_formula_is_not_executed_or_presented_as_value():
    block, hint = matrix()
    cells = list(block.cells)
    cells[-1] = replace(cells[-1], value=None, formula="=SUM(A1:A3)", data_type="f")
    row = build([replace(block, cells=tuple(cells))], UnitConfig(1800, (hint,)))[-1]
    assert "D3 [formula: =SUM(A1:A3)]" in row.reading_text
    assert "D3 =" not in row.reading_text


def test_long_table_records_keep_headings_and_following_notes():
    blocks = list(table_section())
    blocks[1] = replace(blocks[1], rows=tuple((f"Category {i}", "Explicit authorization") for i in range(12)))
    units = build(blocks, UnitConfig(200))
    rows = [u for u in units if u.structural_role == "table_record"]
    assert len(rows) == 12
    assert all("Controls" in u.reading_text and "cannot grant an exception" in u.reading_text for u in rows)
    assert all(any(r.block_id == "note" for r in u.source_refs) for u in rows)


def test_large_text_uses_exact_paragraph_offsets_but_requires_review():
    text = "Report immediately. Preserve evidence.\n\nDo not delete records without instruction."
    units = build([TextBlock("p", 0, "paragraph", text)], UnitConfig(50))
    assert "".join(text[u.source_refs[0].start:u.source_refs[0].end] for u in units) == text
    assert all(u.status == "fragment_requires_review" for u in units)
    with pytest.raises(ValueError):
        materialize(units, [units[0].unit_id], max_chars=100)


def test_indivisible_rule_is_retained_and_flagged_not_cut():
    text = "Only authorized recipients may receive restricted data when explicit approval is documented."
    unit, = build([TextBlock("p", 0, "paragraph", text)], UnitConfig(30))
    assert unit.reading_text == text and unit.status == "oversized" and not unit.searchable


def test_ids_are_deterministic_and_change_with_source_revision():
    a = build(table_section())
    assert a == build(table_section())
    b = EvidenceUnitBuilder().build(NormalizedContent(table_section()), document_id="DOC-099",
        title="Example policy", source_revision="b" * 64)
    assert set(u.unit_id for u in a).isdisjoint(u.unit_id for u in b)


def test_materialization_budget_fails_atomically_and_deduplicates():
    units = build(table_section())
    uid = units[0].unit_id
    chosen, text = materialize(units, [uid, uid], max_chars=1800)
    assert len(chosen) == 1 and text == units[0].reading_text
    with pytest.raises(ValueError, match="nothing was truncated"):
        materialize(units, [uid], max_chars=10)


def test_graph_rejects_cycle_and_invalid_offsets():
    content = NormalizedContent((TextBlock("a", 0, "paragraph", "Evidence"),))
    units = build(content.blocks)
    with pytest.raises(ValueError, match="Cyclic"):
        validate_units((replace(units[0], parent_id=units[0].unit_id),), content)
    bad = replace(units[0], source_refs=(replace(units[0].source_refs[0], end=999),))
    with pytest.raises(ValueError, match="offsets"):
        validate_units((bad,), content)
