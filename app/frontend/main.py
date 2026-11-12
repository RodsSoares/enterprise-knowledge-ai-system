"""Streamlit interface for the Enterprise Knowledge AI System (lean pipeline).

Run from the repository root:  streamlit run app/frontend/main.py
Needs OPENAI_API_KEY. Each question makes about three API calls; the sidebar
shows what was spent and the session stops at the configured ceiling.
"""
from html import escape
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

# status -> (label, tone). Tones map to the CSS classes below.
STATUS = {
    "answered_pending_human_review": ("Resposta verificada", "ok"),
    "answered_with_reservations": ("Resposta com ressalvas", "warn"),
    "clarification_required": ("Preciso de mais informações para responder", "human"),
    "abstained": ("Evidência insuficiente nos documentos disponíveis", "warn"),
    "review_rejected": ("Resposta retida pela verificação", "warn"),
    "execution_failed": ("Falha na execução", "error"),
    "budget_exceeded": ("Limite de custo da pergunta atingido", "error"),
}
ICONS = {"ok": "✓", "warn": "!", "info": "i", "human": "?", "error": "×"}
# Document lifecycle -> (chip label, tone), as in the project artwork.
LIFECYCLE = {"active": ("Vigente", "ok"), "superseded": ("Substituído", "warn"),
             "historical": ("Histórico", "info")}
# Visual language of the images in the project READMEs: the AI Supply Chain
# Copilot interface (navy panels, uppercase section labels, pill chips) and the
# Enterprise Knowledge artwork (white-to-cyan title, green check for grounded
# answers, amber for insufficient evidence, purple for human decisions).
CSS = """
<style>
:root { --bg:#020B1A; --panel:#071A33; --panel2:#0A2140; --line:#15396B; --cyan:#38BDF8;
        --cyan2:#0AD1F9; --blue:#1E6BFF; --text:#EAF4FF; --muted:#8FB0CC;
        --ok:#22C55E; --warn:#F5B301; --error:#F87171; }
.stApp { background: radial-gradient(1200px 600px at 85% -10%, #0B2F63 0%, rgba(2,11,26,0) 60%), var(--bg); }
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #04142B 0%, #020B1A 100%);
    border-right: 1px solid var(--line); }
.ek-kicker { display:flex; align-items:center; gap:14px; letter-spacing:.42em; font-size:.72rem;
    color:var(--text); text-transform:uppercase; margin-bottom:.4rem; }
.ek-kicker::after { content:""; height:2px; width:120px;
    background:linear-gradient(90deg, var(--cyan2), rgba(10,209,249,0)); }
.ek-title { font-size:2.5rem; font-weight:800; line-height:1.08; color:#fff; margin:0; }
.ek-title span { background:linear-gradient(90deg, #6BCCFB, var(--cyan2)); -webkit-background-clip:text;
    background-clip:text; color:transparent; }
.ek-tagline { border-left:3px solid var(--cyan2); padding-left:12px; color:var(--muted);
    margin:.9rem 0 1.4rem 0; font-size:.98rem; }
.ek-status { display:flex; align-items:center; gap:10px; padding:.6rem .9rem; border-radius:10px;
    border:1px solid var(--line); background:var(--panel); font-weight:600; margin-bottom:.6rem; }
.ek-status b { display:inline-flex; align-items:center; justify-content:center; width:22px; height:22px;
    border-radius:50%; font-size:.8rem; color:#02101F; }
.ek-ok { border-color:rgba(34,197,94,.55); } .ek-ok b { background:var(--ok); }
.ek-warn { border-color:rgba(245,179,1,.55); } .ek-warn b { background:var(--warn); }
.ek-info { border-color:rgba(56,189,248,.55); } .ek-info b { background:var(--cyan); }
.ek-error { border-color:rgba(248,113,113,.6); } .ek-error b { background:var(--error); }
.ek-human { border-color:rgba(167,139,250,.6); } .ek-human b { background:#A78BFA; }
.ek-steps { color:var(--cyan2); letter-spacing:.16em; font-size:.72rem; font-weight:700;
    text-transform:uppercase; margin:.2rem 0 1.2rem 0; }
.ek-head { display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap;
    padding:.5rem .9rem; margin-bottom:.7rem; border:1px solid var(--line); border-radius:12px;
    background:linear-gradient(90deg, rgba(10,33,64,.9), rgba(7,26,51,.4)); font-weight:700; font-size:.86rem; }
.ek-head em { color:var(--cyan); font-style:normal; }
.ek-chip { display:inline-block; padding:2px 10px; margin-left:6px; border-radius:999px; font-size:.7rem;
    font-weight:600; border:1px solid var(--line); color:var(--muted); }
.ek-chip.ek-ok { color:#86EFAC; } .ek-chip.ek-warn { color:#FDE68A; } .ek-chip.ek-info { color:#7DD3FC; }
.ek-brand { display:flex; align-items:center; gap:12px; margin-bottom:.2rem; }
.ek-brand b { display:inline-flex; align-items:center; justify-content:center; width:36px; height:36px;
    border-radius:10px; border:1px solid var(--cyan); color:#fff; background:var(--panel2); font-size:.9rem; }
.ek-brand span { font-weight:800; color:#fff; }
.ek-brand-sub { color:var(--muted); font-size:.8rem; margin-bottom:1rem; }
.ek-claim { padding:.55rem .8rem; margin:.35rem 0; border-left:3px solid var(--blue);
    background:rgba(10,33,64,.55); border-radius:0 8px 8px 0; }
.ek-cite { display:inline-block; margin-left:6px; padding:1px 7px; border-radius:999px; font-size:.72rem;
    border:1px solid var(--cyan); color:var(--cyan); white-space:nowrap; }
.ek-note { padding:.5rem .8rem; margin:.4rem 0; border:1px solid rgba(245,179,1,.5); border-radius:8px;
    color:#FFE08A; background:rgba(245,179,1,.07); font-size:.92rem; }
.ek-sources { color:var(--cyan); text-transform:uppercase; letter-spacing:.14em; font-size:.74rem;
    font-weight:700; margin:1rem 0 .3rem 0; }
.ek-meta { color:var(--muted); font-size:.78rem; margin-top:.6rem; }
div[data-testid="stExpander"] details { border:1px solid var(--line); background:var(--panel); border-radius:10px; }
div[data-testid="stChatMessage"] { background:rgba(7,26,51,.6); border:1px solid var(--line); border-radius:14px; }
div[data-testid="stChatInput"] textarea { background:var(--panel); }
section[data-testid="stSidebar"] .stButton button { background:var(--panel2); border:1px solid var(--line);
    color:var(--text); text-align:left; font-size:.86rem; }
section[data-testid="stSidebar"] .stButton button:hover { border-color:var(--cyan2); color:var(--cyan2); }
section[data-testid="stSidebar"] h3 { color:var(--cyan); text-transform:uppercase; letter-spacing:.14em;
    font-size:.78rem; }
div[data-testid="stMetricValue"] { color:var(--cyan2); }
</style>
"""
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
    label, tone = STATUS.get(answer.status, (answer.status, "info"))
    chips = ""
    if answer.answered:
        documents = len({source.document_id for source in answer.sources})
        chips = (f'<span><span class="ek-chip">{len(answer.claims)} afirmações</span>'
                 f'<span class="ek-chip">{documents} documento(s)</span></span>')
    heading = "Resposta fundamentada" if answer.answered else "Sem resposta dos documentos"
    st.markdown(f'<div class="ek-head"><span><em>Enterprise Knowledge</em> • {heading}</span>'
                f'{chips}</div>'
                f'<div class="ek-status ek-{tone}"><b>{ICONS[tone]}</b>{escape(label)}</div>',
                unsafe_allow_html=True)
    if answer.answered:
        for claim in answer.claims:
            chips = "".join(f'<span class="ek-cite">{escape(uid)}</span>' for uid in claim["citation_ids"])
            st.markdown(f'<div class="ek-claim">{escape(claim["text"])}{chips}</div>',
                        unsafe_allow_html=True)
        for note in answer.reservations:
            st.markdown(f'<div class="ek-note">Ressalva: {escape(note)}</div>', unsafe_allow_html=True)
        st.markdown('<div class="ek-sources">Fontes</div>', unsafe_allow_html=True)
        for source in answer.sources:
            title = f"[{source.alias}] {source.document_id} — {source.title} v{source.version}"
            if source.section:
                title += " › " + source.section
            with st.expander(title):
                label, chip = LIFECYCLE.get(source.status, (source.status, "info"))
                st.markdown(f'<span class="ek-chip ek-{chip}" style="margin-left:0">{escape(label)}</span>',
                            unsafe_allow_html=True)
                st.text(source.text)
    elif answer.message:
        st.write(answer.message)
    st.markdown(
        f'<div class="ek-meta">{escape(answer.model)} · {answer.calls} chamadas · '
        f'{answer.input_tokens:,} tokens de entrada · {answer.output_tokens:,} de saída · '
        f'US$ {answer.cost_usd:.4f} · {answer.elapsed_seconds:.1f}s</div>', unsafe_allow_html=True)


def main():
    st.set_page_config(page_title="Enterprise Knowledge AI", page_icon="📚", layout="centered")
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="ek-kicker">Rodrigo Soares</div>'
        '<h1 class="ek-title">Enterprise <span>Knowledge AI System</span></h1>'
        '<div class="ek-tagline">Múltiplas fontes. Conhecimento estruturado. Respostas confiáveis.<br>'
        'Cada afirmação cita o documento de origem; a decisão continua sendo humana.</div>'
        '<div class="ek-steps">Conectar • Processar • Governar • Recuperar • Responder</div>',
        unsafe_allow_html=True)
    if not os.getenv("OPENAI_API_KEY", "").strip():
        st.error("Defina a variável de ambiente OPENAI_API_KEY antes de iniciar.")
        st.stop()
    service = get_service()
    config = service.config
    with st.sidebar:
        st.markdown('<div class="ek-brand"><b>RS</b><span>Enterprise Knowledge AI</span></div>'
                    '<div class="ek-brand-sub">Enterprise RAG • Evidence &amp; Citations</div>',
                    unsafe_allow_html=True)
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
