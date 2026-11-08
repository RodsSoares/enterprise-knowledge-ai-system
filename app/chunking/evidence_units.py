"""Experimental structural units; does not change RetrievalChunk or the baseline.

No LLM, embeddings, inferred normative roles, or arbitrary character slicing.
Parents are expansion targets, not automatic dependencies of every child.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
import re

from app.chunking.block_serializer import BlockSerializer
from app.ingestion.schemas import NormalizedContent, SpreadsheetBlock, TableBlock, TextBlock


REPRESENTATION_VERSION = "evidence-units/1"


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class SourceRef:
    """Pointer into one normalized block; text offsets are Unicode code points."""
    block_id: str
    field: str
    start: int | None = None
    end: int | None = None


@dataclass(frozen=True)
class EvidenceUnit:
    unit_id: str
    document_id: str
    source_revision: str
    representation_version: str
    structural_role: str
    section_path: tuple[str, ...]
    parent_id: str | None
    dependency_ids: tuple[str, ...]
    source_refs: tuple[SourceRef, ...]
    reading_text: str
    search_text: str
    status: str
    searchable: bool


@dataclass(frozen=True)
class SpreadsheetHeader:
    """Reviewed structural declaration, never inferred from question/answer data."""
    block_id: str
    sheet_name: str
    cells: tuple[str, ...]
    expected_labels: tuple[str, ...]


@dataclass(frozen=True)
class UnitConfig:
    max_chars: int = 1800
    spreadsheet_headers: tuple[SpreadsheetHeader, ...] = ()

    def __post_init__(self):
        if type(self.max_chars) is not int or self.max_chars < 1:
            raise ValueError("max_chars must be a positive integer")
        ids = [h.block_id for h in self.spreadsheet_headers]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate spreadsheet header declaration")

    @classmethod
    def from_dict(cls, raw):
        if set(raw) != {"max_chars", "spreadsheet_headers"}:
            raise ValueError("Expected max_chars and spreadsheet_headers")
        headers = tuple(SpreadsheetHeader(h["block_id"], h["sheet_name"],
            tuple(h["cells"]), tuple(h["expected_labels"])) for h in raw["spreadsheet_headers"])
        if any(set(h) != {"block_id", "sheet_name", "cells", "expected_labels"}
               for h in raw["spreadsheet_headers"]):
            raise ValueError("Unexpected header configuration field")
        return cls(raw["max_chars"], headers)


def _section(block):
    return getattr(getattr(block, "location", None), "section_path", ())


def _coord(value):
    match = re.fullmatch(r"([A-Z]+)([1-9][0-9]*)", value)
    if not match:
        raise ValueError("Invalid cell coordinate")
    col = 0
    for char in match[1]:
        col = col * 26 + ord(char) - 64
    return int(match[2]), col


class EvidenceUnitBuilder:
    def __init__(self, config=None):
        self.config = config or UnitConfig()

    def build(self, content: NormalizedContent, *, document_id: str,
              source_revision: str, title: str) -> tuple[EvidenceUnit, ...]:
        if not all(isinstance(x, str) and x.strip() for x in (document_id, title)):
            raise ValueError("Document identity and title required")
        if not re.fullmatch(r"[0-9a-f]{64}", source_revision):
            raise ValueError("source_revision must be a SHA-256 digest")
        blocks = content.ordered_blocks
        by_id = {b.block_id: b for b in blocks}
        hints = {h.block_id: h for h in self.config.spreadsheet_headers}
        if any(key not in by_id or not isinstance(by_id[key], SpreadsheetBlock) for key in hints):
            raise ValueError("Header declaration targets an unknown spreadsheet block")
        serializer = BlockSerializer()
        units = []

        def add(role, text, refs, section=(), parent=None, dependencies=(),
                status="ready", searchable=True):
            refs = tuple(dict.fromkeys(refs))
            if not text.strip():
                raise ValueError("Empty evidence unit")
            # A larger parent is retained as an explicit expansion target.
            if len(text) > self.config.max_chars:
                status = "oversized" if status == "ready" else status + ":oversized"
                searchable = False
            payload = dict(document_id=document_id, source_revision=source_revision,
                representation_version=REPRESENTATION_VERSION, structural_role=role,
                section_path=tuple(section), parent_id=parent, dependency_ids=tuple(dependencies),
                source_refs=refs, reading_text=text, status=status, searchable=searchable)
            uid = document_id + "::unit-" + digest({**payload,
                "source_refs": [asdict(r) for r in refs]})
            search = f"Document: {document_id}\nTitle: {title}\n"
            if section:
                search += "Section: " + " > ".join(section) + "\n"
            unit = EvidenceUnit(uid, search_text=search + "\n" + text, **payload)
            units.append(unit)
            return unit

        def spreadsheet(block):
            full = serializer.serialize(block)
            hint = hints.get(block.block_id)
            status = "ready" if hint else "unresolved_structure"
            parent = add("spreadsheet", full, [SourceRef(block.block_id, "")],
                         status=status, searchable=hint is None)
            if hint is None:
                return
            cells = {c.coordinate: (i, c) for i, c in enumerate(block.cells)}
            if (hint.sheet_name != block.sheet_name or not hint.cells or
                    len(hint.cells) != len(hint.expected_labels) or
                    len(set(hint.cells)) != len(hint.cells)):
                raise ValueError("Invalid spreadsheet header declaration")
            coords = [_coord(c) for c in hint.cells]
            header_row = coords[0][0]
            cols = [c for _, c in coords]
            if (any(row != header_row for row, _ in coords) or
                    cols != list(range(min(cols), max(cols) + 1))):
                raise ValueError("Headers must form one contiguous row")
            for coord, label in zip(hint.cells, hint.expected_labels):
                if (coord not in cells or not isinstance(label, str) or not label.strip()
                        or cells[coord][1].value != label or cells[coord][1].formula is not None):
                    raise ValueError("Header label differs from canonical source")
            if len(set(hint.expected_labels)) != len(hint.expected_labels):
                raise ValueError("Ambiguous duplicate column labels")
            positions = {_coord(c.coordinate): (i, c) for i, c in enumerate(block.cells)}
            rows = sorted({r for r, _ in positions})
            # Conservative: no discarded title, footer, sparse region or second table.
            if (rows != list(range(header_row, max(rows) + 1)) or len(rows) < 2
                    or set(positions) != {(r, c) for r in rows for c in cols}):
                raise ValueError("Declared spreadsheet must be a complete rectangular region")
            for row in rows[1:]:
                lines, refs = [f"Sheet: {block.sheet_name}; row: {row}"], []
                for header, label, col in zip(hint.cells, hint.expected_labels, cols):
                    index, cell = positions[(row, col)]
                    hi, _ = cells[header]
                    lines.append(f"{label} [{header}] | {serializer._serialize_spreadsheet_cell(cell)}")
                    refs.extend((SourceRef(block.block_id, f"cells/{hi}"),
                                 SourceRef(block.block_id, f"cells/{index}")))
                add("table_record", "\n".join(lines), refs, parent=parent.unit_id)

        def emit_group(group):
            section = _section(group[0])
            text = "\n\n".join(serializer.serialize(b) or "[No textual projection]" for b in group)
            whole_refs = [SourceRef(b.block_id, "") for b in group]
            if len(group) > 1:
                navigation = all(isinstance(b, TextBlock) and b.kind in ("heading", "title")
                                 for b in group)
                has_text = any(serializer.serialize(b) for b in group)
                parent = add("navigation" if navigation else "section", text, whole_refs, section,
                             status="ready" if has_text else "no_text",
                             searchable=has_text and not navigation and len(text) <= self.config.max_chars)
            else:
                parent = None
            heading_blocks = [b for b in group if isinstance(b, TextBlock)
                              and b.kind in ("heading", "title")]
            for block in group:
                parent_id = parent.unit_id if parent else None
                if isinstance(block, TableBlock):
                    intro = [b for b in group if isinstance(b, TextBlock) and b.order < block.order]
                    notes = [b for b in group if isinstance(b, TextBlock) and b.order > block.order]
                    suffix = "\n\n".join(b.text for b in notes)
                    prefix = "\n\n".join(b.text for b in intro)
                    refs = [SourceRef(b.block_id, "text", 0, len(b.text)) for b in [*intro, *notes]]
                    table_text = serializer.serialize(block)
                    table = add("table", (prefix + "\n\n" if prefix else "") + table_text
                        + ("\n\n" + suffix if suffix else ""),
                        [*refs, SourceRef(block.block_id, "")], section, parent_id,
                        searchable=parent is None or not parent.searchable)
                    # Small tables stay whole; large tables can be located by row.
                    if len(table.reading_text) > self.config.max_chars and block.headers:
                        for index, row in enumerate(block.rows):
                            body = "\n".join(f"{h}: {'' if v is None else v}"
                                for h, v in zip(block.headers, row))
                            caption = f"Caption: {block.caption}\n" if block.caption else ""
                            add("table_record", (prefix + "\n\n" if prefix else "") + caption + body
                                + ("\n\n" + suffix if suffix else ""),
                                [*refs, SourceRef(block.block_id, "headers"),
                                 SourceRef(block.block_id, f"rows/{index}"),
                                 *([SourceRef(block.block_id, "caption")] if block.caption else [])],
                                section, table.unit_id)
                elif isinstance(block, TextBlock):
                    role = block.kind
                    if parent and parent.searchable:
                        continue
                    heads = [b for b in heading_blocks if b.order < block.order]
                    prefix = "\n\n".join(b.text for b in heads)
                    head_refs = [SourceRef(b.block_id, "text", 0, len(b.text)) for b in heads]
                    spans = [(0, len(block.text))]
                    if len(block.text) > self.config.max_chars:
                        # Split only at paragraph boundaries, retaining all source characters.
                        ends = [m.end() for m in re.finditer(r"\n\s*\n", block.text)]
                        boundaries = [0, *ends, len(block.text)]
                        spans = [(a, b) for a, b in zip(boundaries, boundaries[1:]) if a < b
                                 and block.text[a:b].strip()]
                    for start, end in spans:
                        value = block.text[start:end]
                        add(role, (prefix + "\n\n" if prefix else "") + value,
                            [*head_refs, SourceRef(block.block_id, "text", start, end)], section,
                            parent_id, status="fragment_requires_review" if len(spans) > 1 else "ready",
                            searchable=role not in ("heading", "title"))
                else:
                    add(type(block).__name__.removesuffix("Block").lower(),
                        serializer.serialize(block) or "[No textual projection]",
                        [SourceRef(block.block_id, "")], section, parent_id,
                        status="ready" if serializer.serialize(block) else "no_text",
                        searchable=bool(serializer.serialize(block)) and parent is None)

        group = []
        for block in blocks:
            if isinstance(block, SpreadsheetBlock):
                if group:
                    emit_group(group)
                    group = []
                spreadsheet(block)
                continue
            same = group and _section(block) and _section(block) == _section(group[0])
            if group and not same:
                emit_group(group)
                group = []
            group.append(block)
        if group:
            emit_group(group)
        validate_units(tuple(units), content)
        return tuple(units)


def validate_units(units, content):
    """Validate origin and graph, not semantic applicability or entailment."""
    catalog = {u.unit_id: u for u in units}
    if len(catalog) != len(units) or not units:
        raise ValueError("Nonempty unique units required")
    source = {b.block_id: asdict(b) for b in content.blocks}
    for unit in units:
        if not unit.source_refs:
            raise ValueError("Unit without source")
        for ref in unit.source_refs:
            value = source[ref.block_id]
            for segment in ref.field.split("/") if ref.field else ():
                value = value[int(segment)] if isinstance(value, (tuple, list)) else value[segment]
            if ref.start is not None or ref.end is not None:
                if (not isinstance(value, str) or type(ref.start) is not int or
                        type(ref.end) is not int or not 0 <= ref.start < ref.end <= len(value)):
                    raise ValueError("Invalid source offsets")
        visiting, visited = set(), set()

        def visit(uid):
            if uid in visiting:
                raise ValueError("Cyclic unit relationships")
            if uid in visited:
                return
            if uid not in catalog:
                raise ValueError("Unknown related unit")
            visiting.add(uid)
            target = catalog[uid]
            if (target.document_id, target.source_revision) != (unit.document_id, unit.source_revision):
                raise ValueError("Cross-document structural relationship")
            for dep in (*target.dependency_ids, *((target.parent_id,) if target.parent_id else ())):
                visit(dep)
            visiting.remove(uid)
            visited.add(uid)
        visit(unit.unit_id)


def materialize(units, selected_ids, *, max_chars):
    """Atomic context assembly; never silently truncate or include a whole parent."""
    if type(max_chars) is not int or max_chars < 1:
        raise ValueError("Positive context limit required")
    catalog = {u.unit_id: u for u in units}
    selected, visiting = {}, set()

    def take(uid):
        if uid in visiting:
            raise ValueError("Cyclic dependency")
        if uid in selected:
            return
        unit = catalog[uid]
        if unit.status != "ready":
            raise ValueError(f"Unit requires review: {unit.status}")
        visiting.add(uid)
        for dep in unit.dependency_ids:
            take(dep)
        visiting.remove(uid)
        selected[uid] = unit
    for uid in selected_ids:
        take(uid)
    rendered = "\n\n".join(u.reading_text for u in selected.values())
    if len(rendered) > max_chars:
        raise ValueError("Context budget exceeded; nothing was truncated")
    return tuple(selected.values()), rendered
