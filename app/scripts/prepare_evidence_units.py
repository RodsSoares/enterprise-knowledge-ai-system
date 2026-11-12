"""Prepare/verify the experimental structural catalog; zero OpenAI calls."""
import argparse
from collections import Counter
from dataclasses import asdict
import importlib.metadata
import json
from pathlib import Path
import re

from app.chunking.evidence_snapshot import (
    build_lexical_index, document_record, file_hash, make_snapshot, relative_path, verify_snapshot,
)
from app.chunking.evidence_units import UnitConfig
from app.ingestion.registry import load_document_registry


def prepare(corpus, registry_path, config_path, *, parse=None):
    corpus, registry_path, config_path = (relative_path(Path(p).as_posix())
                                         for p in (corpus, registry_path, config_path))
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    if set(raw) != {"max_chars", "documents"}:
        raise ValueError("Config requires max_chars and documents")
    UnitConfig(raw["max_chars"])
    paths = sorted(p for p in corpus.rglob("DOC-*") if p.is_file()
        and p.suffix.lower() in {".pdf", ".docx", ".xlsx", ".pptx", ".md", ".txt"}
        and re.match(r"^DOC-\d+_", p.name))
    ids = [p.stem.split("_", 1)[0] for p in paths]
    if not ids or len(ids) != len(set(ids)) or set(raw["documents"]) - set(ids):
        raise ValueError("Missing/duplicate documents or unmatched structural configuration")
    registry = load_document_registry(registry_path)
    before = {p: file_hash(p) for p in [*paths, registry_path, config_path]}
    records = []
    router = None
    for path, doc_id in zip(paths, ids):
        metadata = registry.by_id(doc_id)
        settings = raw["documents"].get(doc_id)
        hints = []
        if settings:
            if set(settings) != {"source_sha256", "spreadsheet_headers"}:
                raise ValueError("Unexpected document configuration")
            if settings["source_sha256"] != before[path]:
                raise ValueError(f"Structural declaration needs review for changed source: {doc_id}")
            hints = settings["spreadsheet_headers"]
            if hints:
                if path.suffix.lower() != ".xlsx":
                    raise ValueError("Spreadsheet declaration on a non-XLSX source")
                from openpyxl import load_workbook
                workbook = load_workbook(path, read_only=False)
                try:
                    for h in hints:
                        if workbook[h["sheet_name"]].merged_cells.ranges:
                            raise ValueError("Merged worksheet needs explicit structural review")
                finally:
                    workbook.close()
        config = UnitConfig.from_dict(dict(max_chars=raw["max_chars"], spreadsheet_headers=hints))
        print(f"Preparando {doc_id}: {path.name}", flush=True)
        if parse is not None:
            content = parse(path)
        elif path.suffix.lower() == ".xlsx":
            from app.ingestion.xlsx_parser import XlsxParser
            content = XlsxParser().parse(path)
        else:
            if router is None:
                from app.ingestion.ingestion_router import IngestionRouter
                router = IngestionRouter()
            content = router.parse(path)
        records.append(document_record(content, document_id=doc_id, title=metadata.title,
            source_path=path.as_posix(), source_revision=before[path], config=config,
            metadata=json.loads(json.dumps(asdict(metadata), default=str))))
    if any(file_hash(p) != h for p, h in before.items()):
        raise ValueError("Source or configuration changed during preparation")
    versions = {}
    for name in ("docling", "openpyxl"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "not_installed"
    code = [Path(__file__), Path("app/retrieval/lexical_index.py")]
    for directory in ("app/chunking", "app/ingestion"):
        code.extend(sorted(Path(directory).glob("*.py")))
    provenance = dict(input_files=[dict(path=p.as_posix(), sha256=before[p])
        for p in (registry_path, config_path)], package_versions=versions,
        code_hashes={p.name if p.is_absolute() else p.as_posix(): file_hash(p) for p in code},
        paid_api_calls=0, semantic_evaluation="not_performed")
    return make_snapshot(records, provenance=provenance)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=Path("data/source/corporate_repository"))
    parser.add_argument("--registry", type=Path, default=Path("data/ground_truth/document_registry.yaml"))
    parser.add_argument("--config", type=Path, default=Path("docs/validation/EVIDENCE_UNITS_CONFIG.json"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--query", help="Optional lexical inspection, not semantic evaluation")
    args = parser.parse_args(argv)
    if bool(args.output) == bool(args.verify):
        parser.error("Choose --output NEW_FILE or --verify EXISTING_FILE")
    if args.output and args.output.exists():
        parser.error("Output exists; choose a new filename")
    try:
        if args.verify:
            snapshot = json.loads(args.verify.read_text(encoding="utf-8"))
        else:
            snapshot = prepare(args.corpus, args.registry, args.config)
        units = verify_snapshot(snapshot, root=Path.cwd())
        index = build_lexical_index(snapshot)
        hits = index.search(args.query, top_k=5) if args.query else ()
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as out:
                json.dump(snapshot, out, ensure_ascii=False, indent=2, allow_nan=False)
        print(f"catalog_valid: {len(units)} units; {sum(u.searchable for u in units)} searchable")
        print("Status:", dict(Counter(u.status for u in units)))
        print("Snapshot:", snapshot["snapshot_id"])
        for hit in hits:
            print(hit.rank, hit.chunk_id, f"BM25={hit.score:.4f}")
        return 0
    except (ValueError, KeyError, OSError, TypeError) as exc:
        parser.exit(1, f"preparation_failed: {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
