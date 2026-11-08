"""Versioned structural catalog. Rebuild verification detects projection drift.

Separate format from orchestration.snapshot v1; never passed to its loader.
Hashes detect accidental changes; they are not signatures/authentication.
"""
from dataclasses import asdict, fields, is_dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath

from app.ingestion import schemas
from app.chunking.evidence_units import EvidenceUnitBuilder, UnitConfig, digest
from app.retrieval.lexical_index import BM25LexicalIndex


SCHEMA_VERSION = "evidence-catalog/2.0"
_TYPES = {name: getattr(schemas, name) for name in (
    "NormalizedContent", "TextBlock", "TableBlock", "SpreadsheetBlock", "SpreadsheetCell",
    "SourceLocation", "ChartBlock", "ChartSeries", "ChartSourceReference", "ImageBlock")}


def encode(value):
    if is_dataclass(value):
        if type(value).__name__ not in _TYPES:
            raise ValueError("Unsupported canonical type")
        return {"type": type(value).__name__, "fields": {
            f.name: encode(getattr(value, f.name)) for f in fields(value)}}
    if isinstance(value, tuple):
        return [encode(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError("Unsupported canonical value")


def decode(value):
    if isinstance(value, list):
        return tuple(decode(v) for v in value)
    if isinstance(value, dict):
        if set(value) != {"type", "fields"} or value["type"] not in _TYPES:
            raise ValueError("Unsupported serialized canonical type")
        cls = _TYPES[value["type"]]
        if set(value["fields"]) != {f.name for f in fields(cls)}:
            raise ValueError("Canonical fields differ from schema")
        return cls(**{k: decode(v) for k, v in value["fields"].items()})
    return value


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def relative_path(value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("Use repository-relative POSIX paths")
    p = PurePosixPath(value)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("Path escapes repository")
    return Path(*p.parts)


def document_record(content, *, document_id, title, source_path, source_revision,
                    config=None, metadata=None):
    config = config or UnitConfig()
    relative_path(source_path)
    units = EvidenceUnitBuilder(config).build(content, document_id=document_id,
        title=title, source_revision=source_revision)
    return dict(document_id=document_id, title=title, source_path=source_path,
        source_revision=source_revision, metadata=metadata or {}, configuration=asdict(config),
        canonical=encode(content), units=[asdict(u) for u in units])


def make_snapshot(documents, *, provenance=None):
    payload = dict(schema_version=SCHEMA_VERSION, documents=documents,
                   provenance=provenance or {})
    # JSON-normalize tuples so load/save comparisons have the same representation.
    payload = json.loads(json.dumps(payload, ensure_ascii=False, allow_nan=False))
    envelope = dict(snapshot_id=digest(payload), snapshot=payload)
    verify_snapshot(envelope)
    return envelope


def verify_snapshot(envelope, *, root=None):
    if set(envelope) != {"snapshot_id", "snapshot"}:
        raise ValueError("Unexpected snapshot envelope")
    payload = envelope["snapshot"]
    if payload["schema_version"] != SCHEMA_VERSION or digest(payload) != envelope["snapshot_id"]:
        raise ValueError("Snapshot version/hash mismatch")
    documents = payload["documents"]
    ids = [d["document_id"] for d in documents]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Nonempty unique documents required")
    all_units = []
    for record in documents:
        path = relative_path(record["source_path"])
        if root is not None:
            resolved = (Path(root) / path).resolve()
            if not resolved.is_relative_to(Path(root).resolve()):
                raise ValueError("Source path escapes repository")
            if file_hash(resolved) != record["source_revision"]:
                raise ValueError("Physical source changed; prepare again")
        content = decode(record["canonical"])
        if not isinstance(content, schemas.NormalizedContent):
            raise ValueError("Expected NormalizedContent")
        units = EvidenceUnitBuilder(UnitConfig.from_dict(record["configuration"])).build(content,
            document_id=record["document_id"], title=record["title"],
            source_revision=record["source_revision"])
        if digest([asdict(u) for u in units]) != digest(record["units"]):
            raise ValueError("Units differ from deterministic canonical reconstruction")
        all_units.extend(units)
    if len({u.unit_id for u in all_units}) != len(all_units):
        raise ValueError("Duplicate unit IDs")
    if root is not None:
        for item in payload["provenance"].get("input_files", []):
            path = (Path(root) / relative_path(item["path"])).resolve()
            if not path.is_relative_to(Path(root).resolve()) or file_hash(path) != item["sha256"]:
                raise ValueError("Preparation input changed")
    return tuple(all_units)


def build_lexical_index(envelope):
    """Same searchable text envelope for future vector and current lexical indexing."""
    units = tuple(u for u in verify_snapshot(envelope) if u.searchable)
    if not units:
        raise ValueError("No searchable units; inspect oversized/unresolved sources")
    index = BM25LexicalIndex()
    index.add([u.unit_id for u in units], [u.search_text for u in units])
    return index
