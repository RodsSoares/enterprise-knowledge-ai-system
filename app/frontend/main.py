"""Streamlit interface for the Enterprise Knowledge AI System (lean pipeline).

Run from the repository root:  streamlit run app/frontend/main.py
Needs OPENAI_API_KEY. Each question makes about three API calls; the sidebar
shows what was spent and the session stops at the configured ceiling.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import streamlit as st  # noqa: E402

from app.service.knowledge_service import (  # noqa: E402
    KnowledgeService, SessionBudgetExceeded, load_runtime_config,
)

STATUS = {
    "answered_pending_human_review": ("Resposta verificada", "success"),
    "answered_with_reservations": ("Resposta com ressalvas", "warning"),
    "clarification_required": ("Preciso de mais informações", "info"),
    "abstained": ("Sem evidência suficiente nos documentos", "info"),
    "review_rejected": ("Resposta retida pela verificação", "warning"),
    "execution_failed": ("Falha na execução", "error"),
    "budget_exceeded": ("Limite de custo da pergunta atingido", "error"),
}
EXAMPLES = (
    "Qual é a meta vigente de OTIF para operações nacionais?",
    "Quem aprova uma nova ferramenta de IA?",
    "Enviei acidentalmente dados confidenciais a um fornecedor. O que devo fazer agora?",
    "Compare as regras de penalidade dos contratos das transportadoras Atlas e Nova.",
    "Qual é a política da empresa para transporte de material radioativo?",
)


@st.cache_resource(show_spinner="Carregando o catálogo de evidências...")
def get_service():
    from openai import OpenAI
    return KnowledgeService(OpenAI(timeout=60, max_retries=0), load_runtime_config())


def show(answer):
    label, kind = STATUS.get(answer.status, (answer.status, "info"))
    getattr(st, kind)(label)
    if answer.answered:
        for claim in answer.claims:
            st.markdown("- " + claim["text"] + "  `" + ", ".join(claim["citation_ids"]) + "`")
        for note in answer.reservations:
            st.warning("Ressalva: " + note)
        st.markdown("**Fontes**")
        for source in answer.sources:
            title = f"[{source.alias}] {source.document_id} — {source.title} v{source.version} ({source.status})"
            if source.section:
                title += " › " + source.section
            with st.expander(title):
                st.text(source.text)
    elif answer.message:
        st.write(answer.message)
    st.caption(f"{answer.model} · {answer.calls} chamadas · {answer.input_tokens:,} tokens de entrada · "
               f"{answer.output_tokens:,} de saída · US$ {answer.cost_usd:.4f} · {answer.elapsed_seconds:.1f}s")


def main():
    st.set_page_config(page_title="Enterprise Knowledge AI", page_icon="📚", layout="centered")
    st.title("Enterprise Knowledge AI System")
    st.caption("Respostas baseadas somente nos documentos corporativos, com citação de cada afirmação. "
               "A resposta é um apoio: a decisão continua sendo humana.")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        st.error("Defina a variável de ambiente OPENAI_API_KEY antes de iniciar.")
        st.stop()
    service = get_service()
    config = service.config
    with st.sidebar:
        st.subheader("Modelo")
        names = list(config["models"])
        model = st.radio("Modelo de resposta", names, index=names.index(config["default_model"]),
                         format_func=lambda name: config["models"][name]["label"])
        rate = config["models"][model].get("measured_pass_rate")
        if rate:
            st.caption("Aprovação medida: " + rate)
        st.subheader("Consumo da sessão")
        st.metric("Gasto estimado", f"US$ {service.session_cost:.4f}")
        st.caption(f"{service.questions} pergunta(s) · teto da sessão US$ {config['max_cost_per_session_usd']} · "
                   f"teto por pergunta US$ {config['max_cost_per_question_usd']}")
        st.subheader("Base de conhecimento")
        st.caption(f"{service.documents} documentos · {len(service.units)} trechos")
        st.subheader("Exemplos")
        for example in EXAMPLES:
            if st.button(example, use_container_width=True):
                st.session_state["pending"] = example
    history = st.session_state.setdefault("history", [])
    for question, answer in history:
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            show(answer)
    question = st.chat_input("Pergunte sobre as políticas e procedimentos") or st.session_state.pop("pending", None)
    if question:
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            try:
                with st.spinner("Buscando evidências e verificando a resposta..."):
                    answer = service.ask(question, model=model)
            except SessionBudgetExceeded:
                st.error("O teto de gasto desta sessão foi atingido. Ajuste "
                         "max_cost_per_session_usd em config/lean_runtime.json para continuar.")
                return
            except ValueError as exc:
                st.error(str(exc))
                return
            show(answer)
        history.append((question, answer))
        st.rerun()


if __name__ == "__main__":
    main()
