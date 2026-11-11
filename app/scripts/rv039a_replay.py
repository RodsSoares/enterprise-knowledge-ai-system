"""RV-039A one-shot no-API replay of saved retrieval traces + lexical recovery.

Compares document-level candidate coverage, *not* final-answer quality.
Do not use the known target ID in ranking or runtime query construction.
"""
import json
from pathlib import Path

from app.chunking.evidence_snapshot import verify_snapshot
from app.retrieval.lexical_index import BM25LexicalIndex
from app.retrieval.lexical_query_filter import filter_lexical_query
from app.retrieval.adaptive_fusion import FusionPolicy, fuse_ranked, controlled_bilingual_query


def unique_documents(unit_ids, id_to_document, limit=5):
    out = []
    for uid in unit_ids:
        if uid in id_to_document and id_to_document[uid] not in out:
            out.append(id_to_document[uid])
        if len(out) >= limit:
            break
    return out


def score_docs(selected, expected):
    expected = set(expected)
    return dict(recall=len(expected.intersection(selected)) / len(expected),
                full=expected.issubset(selected))


def replay_saved_queries(saved):
    rows, abstention_cases = [], []
    for q in saved["questions"]:
        if not q["expected_evidence"]:
            abstention_cases.append({"question_id": q["question_id"],
                                    "expected_behavior": q.get("expected_behavior")})
            continue
        traces = q["candidate_traces"]
        vector = traces["vector"]
        lexical = traces["lexical_bilingual"]
        id_to_document = {x["chunk_id"]: x["document_id"] for x in vector + lexical}
        expected = q["expected_evidence"]
        row = {"question_id": q["question_id"], "expected_document_ids": expected,
               "arms": {}}
        for count in (0, 2, 3, 5):
            ids, _ = fuse_ranked(vector, lexical, top_k=20,
                                 policy=FusionPolicy(protected_vector_units=count))
            selected = unique_documents(ids, id_to_document)
            row["arms"]["protected_units_" + str(count)] = dict(
                documents=selected, **score_docs(selected, expected))
        for arm in ("vector", "hybrid_control", "hybrid_bilingual", "hybrid_protected3"):
            if arm in q["arms"]:
                docs = q["arms"][arm]["document_ids"]
                row["arms"]["historical_" + arm] = dict(
                    documents=docs, **score_docs(docs, expected))
        rows.append(row)
    summary = {}
    for key in rows[0]["arms"]:
        valid = [row["arms"][key] for row in rows if key in row["arms"]]
        summary[key] = {
            "questions": len(valid),
            "mean_document_recall_5": round(sum(v["recall"] for v in valid)/len(valid), 4),
            "full_document_evidence_5": round(sum(v["full"] for v in valid)/len(valid), 4),
        }
    return {"status": "offline_ablation_complete", "sample_size": len(rows),
            "excluded_abstention_cases": abstention_cases,
            "metric_level": "unique_document_ids_from_saved_chunk_ranks",
            "comparability_warning": "New policy uses unit-prefix; RV036 protected3 uses document-prefix and historical selection. Do not equate them.",
            "summary": summary, "questions": rows}


def replay_lexical_probe(snapshot, probe):
    units = tuple(u for u in verify_snapshot(snapshot) if u.searchable and u.status == "ready")
    catalog = {u.unit_id: u for u in units}
    target_id = probe["canonical_target_id"]
    if target_id not in catalog or catalog[target_id].document_id != probe["canonical_document_id"]:
        raise ValueError("Canonical probe target is not in verified snapshot")
    idx = BM25LexicalIndex()
    idx.add([u.unit_id for u in units], [u.search_text for u in units])
    query = probe["query"]
    variants = {"original_pt": query,
                "controlled_pt_en": controlled_bilingual_query(query)}
    report = {}
    for name, raw in variants.items():
        filtered = filter_lexical_query(raw)
        hits = idx.search(filtered, top_k=20) if filtered else ()
        ids = [hit.chunk_id for hit in hits]
        report[name] = {
            "lexical_query": filtered,
            "retrieved": len(ids),
            "canonical_target_rank": ids.index(target_id) + 1 if target_id in ids else None,
            "top_5_document_ids": [catalog[uid].document_id for uid in ids[:5]],
        }
    return {"status": "offline_lexical_probe_complete",
            "snapshot_id": snapshot["snapshot_id"], "target_document": probe["canonical_document_id"],
            "target_id_for_diagnostic_only": target_id,
            "variants": report, "api_calls": 0}


def main():
    base = Path("docs/validation")
    saved = json.loads((base/"RV036_BILINGUAL_RETRIEVAL_RESULTS_local.json").read_text(encoding="utf-8"))
    snapshot = json.loads((base/"EVIDENCE_UNITS_SNAPSHOT_local.json").read_text(encoding="utf-8"))
    probe = json.loads((base/"RV038D2A_RECOVERY_PROBE_local.json").read_text(encoding="utf-8"))
    result = {"experiment": "RV-039A", "mode": "offline_no_api",
              "candidate_replay": replay_saved_queries(saved),
              "lexical_probe": replay_lexical_probe(snapshot, probe),
              "notes": ["Question IDs and expected documents are evaluation-only, not used by runtime retrieval.",
                        "Metrics are for documents on saved RV036 chunk traces, not RV039 live unit retrieval."]}
    dest = base/"RV039A_ARCHITECTURE_REPLAY_local.json"
    with dest.open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("RV-039A | OFFLINE REPLAY")
    for name, metrics in result["candidate_replay"]["summary"].items():
        print(f"{name:30s} recall={metrics['mean_document_recall_5']:.4f} full={metrics['full_document_evidence_5']:.4f}")
    print("\nRV-038D2A C7 canonical target lexical ranks:")
    for name, arm in result["lexical_probe"]["variants"].items():
        print(f"{name:20s} hits={arm['retrieved']} target_rank={arm['canonical_target_rank']}")
    print("Saved:", dest)
    print("API calls: 0 | Baseline untouched")

if __name__ == "__main__":
    main()
