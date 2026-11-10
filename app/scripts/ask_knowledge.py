"""Interactive local RAG demo. Index once, ask independent questions, exit /sair."""
import argparse
import json
import os
from pathlib import Path
import re

from app.generation.openai_answer_provider import OpenAIAnswerProvider
from app.generation.rag_service import build_service
from app.retrieval.openai_embeddings import OpenAIEmbeddingProvider


def discover_sources(root):
    if not root.is_dir():
        raise ValueError(f"Corpus directory not found: {root}")
    suffixes = {".pdf", ".docx", ".xlsx", ".pptx", ".md", ".txt"}
    paths = sorted(p for p in root.rglob("DOC-*")
                   if p.is_file() and p.suffix.lower() in suffixes
                   and re.match(r"^DOC-\d+_", p.name))
    ids = [p.stem.split("_", 1)[0] for p in paths]
    if not paths or len(ids) != len(set(ids)):
        raise ValueError("Corpus must contain DOC-number_name files with unique document IDs")
    return paths


def load_chunks(paths):
    from app.ingestion.ingestion_router import IngestionRouter
    from app.chunking.structure_aware_chunker import StructureAwareChunker
    router, chunker = IngestionRouter(), StructureAwareChunker(1200, 1800)
    chunks = []
    for path in paths:
        print(f"Processando {path.name}...", flush=True)
        parsed = chunker.chunk(router.parse(path), path, path.stem.split("_", 1)[0])
        if not parsed:
            raise ValueError(f"No chunks produced: {path}")
        chunks.extend(parsed)
    return chunks


def print_result(result):
    if result.answer.status == "abstained":
        print("\nAbstenção:", result.answer.abstention_reason)
    else:
        print("\nResposta:")
        for claim in result.answer.claims:
            print(f"- {claim.text} [{', '.join(claim.citation_ids)}]")
        used = dict.fromkeys(cid for c in result.answer.claims for cid in c.citation_ids)
        print("\nFontes:")
        by_id = {p.citation_id: p for p in result.context.passages}
        for cid in used:
            passage = by_id[cid]
            print(f"[{cid}] {json.dumps(passage.citation_metadata(), ensure_ascii=False)}")
            print(passage.chunk.text)
    if result.generation:
        print("\nModelo:", result.generation.model, "| Tokens:", result.generation.usage)
    print(f"Tempo da pergunta: {result.elapsed_seconds:.2f}s")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=Path("data/source/corporate_repository"))
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    parser.add_argument("--question")
    parser.add_argument("--output", type=Path, help="Save one question/result; refuses existing files")
    args = parser.parse_args(argv)
    if not args.model.strip():
        parser.error("--model must not be empty")
    if args.question is not None and (not args.question.strip() or len(args.question) > 4000):
        parser.error("--question must contain 1–4000 characters")
    if args.output and (args.question is None or args.output.exists()):
        parser.error("--output requires --question and a new output filename")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        parser.error("Set OPENAI_API_KEY in your local environment")
    paths = discover_sources(args.corpus)
    print(f"Corpus: {len(paths)} documentos | Modelo: {args.model}")
    print("Sessão com chamadas reais à API. Índice em memória; perguntas independentes.")
    print("Validação estrutural de citações; sustentação semântica ainda em avaliação.")
    from openai import OpenAI
    with OpenAI(timeout=60.0, max_retries=0) as client:
        chunks = load_chunks(paths)
        print(f"Indexando {len(chunks)} chunks...", flush=True)
        service = build_service(chunks, OpenAIEmbeddingProvider(client),
                                OpenAIAnswerProvider(client, model=args.model))
        while True:
            try:
                question = args.question if args.question is not None else input("\nPergunta (/sair): ")
            except EOFError:
                break
            if question.strip() == "/sair":
                break
            if not question.strip():
                continue
            result = service.ask(question)
            print_result(result)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                with args.output.open("x", encoding="utf-8") as file:
                    json.dump(result.to_dict(), file, ensure_ascii=False, indent=2)
                print("Salvo:", args.output)
            if args.question is not None:
                break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
