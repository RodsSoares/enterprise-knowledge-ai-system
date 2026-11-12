"""Create the embedding cache for an evidence-unit snapshot.

Dry run by default: verifies the snapshot and reports how many units would be
embedded. Paid execution needs --execute and --confirm-paid and makes one or
more embedding calls under an explicit cost cap.
"""
import argparse
import json
import os
from pathlib import Path

from app.chunking.evidence_snapshot import verify_snapshot
from app.orchestration.live_provider import BudgetedClient, RunBudget
from app.retrieval.evidence_unit_retriever import make_cache, read_cache
from app.retrieval.openai_embeddings import OpenAIEmbeddingProvider
from app.scripts.compare_stage1_orchestration import load_config

BATCH = 64


def main(argv=None, *, sdk_factory=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--snapshot", type=Path, required=True)
    p.add_argument("--config", type=Path, default=Path("docs/validation/STAGE1_RUN_CONFIG_local.json"))
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--max-cost-usd", default="0.10")
    p.add_argument("--execute", action="store_true")
    p.add_argument("--confirm-paid", action="store_true")
    a = p.parse_args(argv)
    if a.output.exists():
        p.error("Output exists; choose a new path")
    if a.execute != a.confirm_paid:
        p.error("Paid run requires BOTH --execute and --confirm-paid")
    try:
        config, _ = load_config(a.config)
        snapshot = json.loads(a.snapshot.read_text(encoding="utf-8"))
        units = verify_snapshot(snapshot, root=Path.cwd())
        model = config["models"]["embedding"]
        texts = tuple(u.search_text for u in units if u.searchable)
        if not texts:
            raise ValueError("Snapshot has no searchable unit")
        if a.execute and sdk_factory is None and not os.getenv("OPENAI_API_KEY", "").strip():
            raise ValueError("OPENAI_API_KEY environment variable is required")
    except (ValueError, KeyError, TypeError, OSError) as exc:
        p.error("Preflight failed: " + type(exc).__name__ + ": " + str(exc))
    print(f"Snapshot {snapshot['snapshot_id'][:12]}: {len(texts)} unidades pesquisáveis, "
          f"{sum(map(len, texts))} caracteres, modelo {model}")
    if not a.execute:
        print("Dry run. Nenhuma chamada paga.")
        return 0
    if sdk_factory is None:
        from openai import OpenAI
        sdk_factory = OpenAI
    calls = -(-len(texts) // BATCH)
    with sdk_factory(timeout=60, max_retries=0) as sdk:
        client = BudgetedClient(sdk, RunBudget(2_000_000, 1, calls, 300, a.max_cost_usd),
                                {model: config["prices"][model]})
        provider = OpenAIEmbeddingProvider(client, model=model)
        vectors = []
        for start in range(0, len(texts), BATCH):
            vectors.extend(list(row) for row in provider.embed_documents(texts[start:start + BATCH]))
    cache = make_cache(units, model, vectors)
    read_cache(cache, units, model)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("x", encoding="utf-8") as out:
        json.dump(cache, out, ensure_ascii=False, allow_nan=False)
    print(f"Cache salvo em {a.output} | custo estimado USD {client.report()['estimated_cost_usd']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
