"""Two paid generation calls over identical saved evidence; no retrieval/indexing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from time import perf_counter

from app.chunking.schemas import RetrievalChunk
from app.generation.answer_contract import parse_answer, request_id_for
from app.generation.openai_answer_provider import INSTRUCTIONS, SCHEMA, OpenAIAnswerProvider
from app.retrieval.evidence_context import EvidenceContext, EvidencePassage

CONDITIONAL_INSTRUCTIONS = INSTRUCTIONS + """

Antes de redigir, identifique internamente o sujeito, a ação, o objeto e as
condições de aplicação da pergunta e de cada regra. Não exponha esse raciocínio.
Na resposta final:
- Se requisitos dependem de uma categoria não informada, apresente as categorias
  separadamente com seus respectivos requisitos; não crie um requisito universal.
- Preserve expressões condicionais e ressalvas (somente, salvo, exceto, a menos
  que). Não transforme uma proibição condicional em absoluta.
- Exclua regras de outro processo que compartilham apenas palavras com a pergunta.
  Uma condição hipotética não solicitada não precisa virar um item da resposta.
- Cada afirmação deve ser verificável integralmente nos trechos citados. Divida
  afirmações que misturam requisitos ou condições diferentes.
- Prefira responder diretamente com regras aplicáveis, sem introduções genéricas.
"""


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def restore_context(saved):
    """Restore only the generation view; not original retrieval ranks or parsing."""
    question = saved["question"]
    rendered = saved["context"]["text"]
    rows = json.loads(rendered)["evidence"]
    passages = []
    for order, row in enumerate(rows):
        chunk = RetrievalChunk(chunk_id=row["chunk_id"], document_id=row["document_id"],
            order=order, text=row["text"], source_path=Path(row["source_path"]),
            source_block_ids=tuple(row["source_block_ids"]), section_path=tuple(row["section_path"]),
            page_numbers=tuple(row["page_numbers"]), slide_numbers=tuple(row["slide_numbers"]),
            sheet_names=tuple(row["sheet_names"]), content_types=("replay_unspecified",))
        passages.append(EvidencePassage(row["citation_id"], chunk, "saved_context"))
    context = EvidenceContext(tuple(passages), tuple(dict.fromkeys(
        p.chunk.document_id for p in passages)), (), rendered)
    expected = request_id_for(question, context)  # validates exact rendered text and identity
    if context.citations != saved["context"]["citations"]:
        raise ValueError("Saved citation map differs from rendered evidence")
    if saved["answer"]["request_id"] != expected:
        raise ValueError("Saved request does not match the question/context")
    if not passages:
        raise ValueError("No evidence to compare; empty context requires no LLM")
    return question, context


def compare(client, model, question, context):
    """Yield each independent arm; failures remain errors, never abstentions."""
    for name, instructions in (("current_prompt", INSTRUCTIONS),
                               ("conditional_prompt", CONDITIONAL_INSTRUCTIONS)):
        started = perf_counter()
        row = {"arm": name, "instructions": instructions, "prompt_sha256": sha(instructions),
               "request_id": request_id_for(question, context), "requested_model": model,
               "max_output_tokens": 2000}
        try:
            generated = OpenAIAnswerProvider(client, model=model,
                instructions=instructions).generate(question, context)
            row.update(model=generated.model, response_id=generated.response_id,
                       usage=generated.usage, raw=generated.raw)
            answer = parse_answer(generated.raw, question=question, context=context)
            row.update(status="CONTRACT_VALID", answer=answer.to_dict())
        except Exception as exc:
            row.update(status="ERROR", error_type=type(exc).__name__)
        row["elapsed_seconds"] = perf_counter() - started
        yield row


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", help="Default: exact model recorded in source JSON")
    args = parser.parse_args(argv)
    if args.source.resolve() == args.output.resolve() or args.output.exists():
        parser.error("Output must be a new file, different from source")
    raw = args.source.read_bytes()
    saved = json.loads(raw.decode("utf-8-sig"))
    question, context = restore_context(saved)
    model = args.model or saved["generation"]["model"]
    if not isinstance(model, str) or not model.strip():
        parser.error("Provide --model")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        parser.error("Set OPENAI_API_KEY locally")
    report = {"experiment": "RV016_SAVED_CONTEXT_GENERATION_COMPARISON",
        "status": "RUNNING", "source_sha256": hashlib.sha256(raw).hexdigest(),
        "question": question, "context": saved["context"],
        "context_sha256": sha(context.text), "requested_model": model,
        "schema": SCHEMA, "new_embedding_calls": 0, "new_parsing_calls": 0,
        "historical_answer": saved["answer"], "runs": [],
        "semantic_verdict": "PENDING_HUMAN_REVIEW",
        "limits": ["One sample per arm; stochastic variation remains.",
                   "Historical prompt was not recorded; current control is a new generation.",
                   "Reconstructed chunk order/types are placeholders, not ingestion metadata.",
                   "Contract validity does not prove correctness; no automatic promotion."]}
    print(f"Contexto salvo: {len(context.passages)} trechos | Modelo: {model}")
    print("Duas gerações pagas; zero parsing e zero embeddings novos.")
    from openai import OpenAI
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Reserve output before paying. Persist each arm so a later failure cannot lose it.
    with args.output.open("x", encoding="utf-8") as file:
        def checkpoint():
            file.seek(0)
            json.dump(report, file, ensure_ascii=False, indent=2)
            file.truncate()
            file.flush()
        checkpoint()
        with OpenAI(timeout=60.0, max_retries=0) as client:
            for row in compare(client, model, question, context):
                report["runs"].append(row)
                checkpoint()
                print(f"\n{row['arm']}: {row['status']}")
                if row["status"] == "ERROR":
                    print(row["error_type"])
                    continue
                answer = row["answer"]
                if answer["status"] == "abstained":
                    print("Abstenção:", answer["abstention_reason"])
                for claim in answer["claims"]:
                    print(f"- {claim['text']} [{', '.join(claim['citation_ids'])}]")
                print("Tokens:", row["usage"], "| Tempo:", round(row["elapsed_seconds"], 2))
        report["status"] = "COMPLETE" if all(r["status"] == "CONTRACT_VALID"
                                             for r in report["runs"]) else "COMPLETED_WITH_ERRORS"
        checkpoint()
    print("Salvo:", args.output)
    return 0 if report["status"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
