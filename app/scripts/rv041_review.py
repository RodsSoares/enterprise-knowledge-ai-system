"""Create blind source-grounded human review sheets or score reviewed copies.

Two distinct actions:
  python -m app.scripts.rv041_review make --report ... --snapshot ... --template ... --mapping ...
  python -m app.scripts.rv041_review score --reviewed ... --mapping ... --output ...
Neither mode invokes an LLM or alters a source document.
"""
import argparse
import json
from pathlib import Path

from app.chunking.evidence_snapshot import verify_snapshot, file_hash
from app.qualification.rv041_protocol import (
    PROTOCOL, load_cases, select_cases, save_review_packet, score_review_packet,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    make = sub.add_parser("make")
    make.add_argument("--report", required=True, type=Path)
    make.add_argument("--snapshot", required=True, type=Path)
    make.add_argument("--cases", default="docs/validation/RV041_CASES_FROZEN.json", type=Path)
    make.add_argument("--template", required=True, type=Path)
    make.add_argument("--mapping", required=True, type=Path)
    score = sub.add_parser("score")
    score.add_argument("--reviewed", required=True, type=Path)
    score.add_argument("--mapping", required=True, type=Path)
    score.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.command == "make":
        report = json.loads(args.report.read_text(encoding="utf-8"))
        if report.get("protocol") != PROTOCOL:
            parser.error("Wrong report protocol")
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
        if (report.get("snapshot_id") != snapshot.get("snapshot_id")
                or report.get("input_hashes", {}).get("snapshot") != file_hash(args.snapshot)
                or report.get("input_hashes", {}).get("cases") != file_hash(args.cases)):
            parser.error("Mismatch between reviewed report and canonical source snapshot")
        units = verify_snapshot(snapshot, root=Path.cwd())
        cases = select_cases(load_cases(args.cases), report["cohort"])
        if [case["case_id"] for case in cases] != report["case_ids"]:
            parser.error("Frozen case identities differ from live report")
        count = save_review_packet(report, cases, {u.unit_id: u for u in units},
                                   template_path=args.template, mapping_path=args.mapping)
        print(f"Blind review packet: {count} rows | {args.template}")
        print(f"Private arm mapping: {args.mapping} (keep separate until scores are finalized)")
        return 0
    if args.output.exists():
        parser.error("Score summary exists; use a new filename")
    result = score_review_packet(args.reviewed, args.mapping)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Review:", result["status"], "|", result["reviewed_rows"], "/", result["expected_rows"])
    if result["status"] == "complete":
        for arm, row in result["arms"].items():
            print(arm, "mean score:", row["mean_score_out_of_12"], "critical errors:", row["critical_errors"])
    print("Saved:", args.output)
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
