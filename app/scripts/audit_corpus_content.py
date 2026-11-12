"""Find evaluation-harness text inside the documents the RAG indexes.

A corpus document should read like a real company document. Text that talks
about the test itself reaches the model as evidence and changes its answers:

* leakage      - golden-question ids, "benchmark coverage", "distractor";
* disclaimer   - "synthetic", "proposed ... requires review", harness versions;
* instruction  - sentences that tell the reader or the system how to answer.

Reads an evidence-unit snapshot, makes no API call, and exits with status 1
when anything is found, so it can gate a corpus release.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

PATTERNS = {
    "leakage": (
        r"\bQ\d{2}\b", r"golden set", r"benchmark coverage", r"evaluation_questions",
        r"expected use:", r"\bdistractor", r"semantic neighbor", r"evaluation role",
        r"conflict-resolution tests", r"evaluation corpus",
    ),
    "disclaimer": (
        r"\bRV\d{3}\b", r"\bsynthetic\b", r"canonical[_ ]facts?", r"benchmark (freeze|review)",
        r"test-universe", r"proposed (definitions?|for acceptance|notification)",
        r"requir\w+ (acceptance|review|consistency review)", r"pending review",
        r"not a real executed agreement", r"controlled \w* ?corpus",
    ),
    "instruction": (
        r"must not be used to answer", r"do not (infer|recommend|confuse)",
        r"the system must not", r"retrieval caution", r"use this sop only to",
        r"must not be treated as current authority", r"this document intentionally",
    ),
}
COMPILED = {kind: [re.compile(p, re.IGNORECASE) for p in patterns]
            for kind, patterns in PATTERNS.items()}


def audit_text(text):
    """Kinds of harness text found in one passage, with the matched phrases."""
    found = {}
    for kind, expressions in COMPILED.items():
        hits = sorted({m.group(0) for e in expressions for m in e.finditer(text)})
        if hits:
            found[kind] = hits
    return found


def audit_snapshot(snapshot):
    findings = []
    for document in snapshot["snapshot"]["documents"]:
        for unit in document["units"]:
            if not unit["searchable"]:
                continue
            found = audit_text(unit["reading_text"])
            if found:
                findings.append({"document_id": document["document_id"],
                                 "section": " › ".join(unit["section_path"]),
                                 "kinds": found, "text": unit["reading_text"]})
    return findings


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--snapshot", type=Path, default=Path("docs/validation/EVIDENCE_UNITS_SNAPSHOT_27DOC.json"))
    p.add_argument("--output", type=Path, help="Optional JSON report")
    p.add_argument("--show", action="store_true", help="Print every affected passage")
    a = p.parse_args(argv)
    snapshot = json.loads(a.snapshot.read_text(encoding="utf-8"))
    findings = audit_snapshot(snapshot)
    documents = len(snapshot["snapshot"]["documents"])
    searchable = sum(u["searchable"] for d in snapshot["snapshot"]["documents"] for u in d["units"])
    per_document = Counter(f["document_id"] for f in findings)
    per_kind = Counter(kind for f in findings for kind in f["kinds"])
    print(f"{len(findings)} de {searchable} trechos pesquisáveis contêm texto do ambiente de teste, "
          f"em {len(per_document)} de {documents} documentos.")
    print("Por tipo:", dict(per_kind))
    for document_id in sorted(per_document):
        kinds = sorted({k for f in findings if f["document_id"] == document_id for k in f["kinds"]})
        print(f"  {document_id}: {per_document[document_id]} trechos ({', '.join(kinds)})")
    if a.show:
        for f in findings:
            print(f"\n[{f['document_id']}] {f['section']} {f['kinds']}\n{f['text']}")
    if a.output:
        a.output.write_text(json.dumps({"snapshot_id": snapshot["snapshot_id"], "documents": documents,
            "searchable_units": searchable, "findings": findings}, ensure_ascii=False, indent=2),
            encoding="utf-8")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
