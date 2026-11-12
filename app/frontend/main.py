"""Streamlit interface for the Enterprise Knowledge AI System (lean pipeline).

Run from the repository root:  streamlit run app/frontend/main.py
Needs OPENAI_API_KEY. The default model is open to anyone; protected models
are unlocked with APP_ACCESS_PASSWORD. Each question makes about three API
calls, limited by ceilings per question, per session and per day.
"""
from html import escape
import os
import time
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import streamlit as st  # noqa: E402

from app.frontend.access import password_is_configured, password_matches  # noqa: E402
from app.service.knowledge_service import (  # noqa: E402
    DailyBudgetExceeded, KnowledgeService, ModelLocked, SessionBudgetExceeded, load_runtime_config,
)
from app.service.upload_reader import SUPPORTED_SUFFIXES, UploadError  # noqa: E402

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
             "historical": ("Histórico", "info"), "uploaded": ("Enviado por você", "human")}
SCOPE_LABELS = {"corpus": "Base do MVP (27 documentos)", "uploads": "Meus documentos",
                "all": "Base do MVP + meus documentos"}
MIME = {".pdf": "application/pdf", ".md": "text/markdown", ".txt": "text/plain",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}
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
.ek-chip.ek-human { color:#C4B5FD; }
.ek-doc { display:flex; justify-content:space-between; align-items:center; gap:10px; padding:.45rem .8rem;
    border:1px solid var(--line); border-radius:10px; background:var(--panel); font-size:.88rem; }
.ek-doc a { color:var(--cyan2); text-decoration:none; font-weight:600; white-space:nowrap; }
.ek-doc a:hover { text-decoration:underline; }
.ek-privacy { color:var(--muted); font-size:.76rem; margin-top:.3rem; }
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


def get_service():
    """A separate budget, query cache and set of uploaded documents per browser session."""
    if "knowledge_service" not in st.session_state:
        from openai import OpenAI
        st.session_state["knowledge_service"] = KnowledgeService(
            OpenAI(timeout=60, max_retries=0), load_runtime_config()
        )
    return st.session_state["knowledge_service"]


def choose_model(service):
    """Model picker. The default model is open; protected models need the password.

    Returns the model to use and whether protected models are unlocked.
    """
    config = service.config
    names = list(config["models"])
    # Option labels stay constant: a label that changed after the unlock would
    # make Streamlit treat the picker as a new widget and reset the choice.
    selected = st.radio("Modelo de resposta", names, index=names.index(config["default_model"]),
                        key="model_choice",
                        format_func=lambda name: config["models"][name]["label"]
                        + (" · requer senha" if service.is_protected(name) else ""))
    unlocked = st.session_state.get("premium_unlocked") is True
    if service.is_protected(selected) and not unlocked:
        secret = os.getenv("APP_ACCESS_PASSWORD", "")
        if not password_is_configured(secret):
            st.caption("Este modelo não está disponível nesta implantação.")
        else:
            with st.form("premium_unlock", clear_on_submit=True):
                supplied = st.text_input("Senha para liberar este modelo", type="password")
                submitted = st.form_submit_button("Liberar", use_container_width=True)
            if submitted:
                attempts = st.session_state.get("premium_failed_attempts", 0)
                if password_matches(supplied, secret):
                    st.session_state["premium_unlocked"] = True
                    st.session_state["premium_failed_attempts"] = 0
                    st.rerun()
                st.session_state["premium_failed_attempts"] = attempts + 1
                time.sleep(min(1 + attempts, 5))
                st.error("Senha incorreta.")
        st.caption("Enquanto não for liberado, as respostas usam "
                   + config["models"][config["default_model"]]["label"] + ".")
        return config["default_model"], False
    rate = config["models"][selected].get("measured_pass_rate")
    if rate:
        st.caption("Aprovação medida: " + rate)
    return selected, unlocked


def show_documents(answer, service, key):
    """One row per cited document, with a way to open it and check the answer."""
    documents = {}
    for source in answer.sources:
        documents.setdefault(source.document_id, source)
    st.markdown('<div class="ek-sources">Documentos referenciados</div>', unsafe_allow_html=True)
    for document_id, source in documents.items():
        label, chip = LIFECYCLE.get(source.status, (source.status, "info"))
        name = f"{escape(document_id)} — {escape(source.title)}"
        if source.version:
            name += f" v{escape(source.version)}"
        link = ""
        if source.source_path:
            url = service.config["repository_blob_url"] + quote(source.source_path)
            link = f'<a href="{url}" target="_blank" rel="noopener">Abrir no GitHub ↗</a>'
        left, right = st.columns([5, 1.6])
        left.markdown(f'<div class="ek-doc"><span>{name}<span class="ek-chip ek-{chip}">{escape(label)}'
                      f'</span></span>{link}</div>', unsafe_allow_html=True)
        if source.source_path:
            filename = Path(source.source_path).name
            right.download_button("Baixar", service.source_file(source.source_path), file_name=filename,
                                  mime=MIME.get(Path(filename).suffix.lower(), "application/octet-stream"),
                                  key=f"dl-{key}-{document_id}", use_container_width=True)
        else:
            right.caption("arquivo enviado nesta sessão")


def show(answer, service, key):
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
        show_documents(answer, service, key)
        st.markdown('<div class="ek-sources">Trechos citados</div>', unsafe_allow_html=True)
        for source in answer.sources:
            title = f"[{source.alias}] {source.document_id} — {source.title}"
            if source.version:
                title += f" v{source.version}"
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
        f'<div class="ek-meta">{escape(answer.model)} · {escape(SCOPE_LABELS[answer.scope])} · '
        f'{answer.calls} chamadas · '
        f'{answer.input_tokens:,} tokens de entrada · {answer.output_tokens:,} de saída · '
        f'US$ {answer.cost_usd:.4f} · {answer.elapsed_seconds:.1f}s</div>', unsafe_allow_html=True)


def ingest(service, files):
    """Add the files sent in the chat to this session. Returns user-facing notes."""
    notes = []
    for file in files:
        try:
            upload = service.add_upload(file.name, file.getvalue())
            notes.append(("ok", f"{upload.name}: {len(upload.units)} trechos indexados ({upload.document_id})."))
        except UploadError as exc:
            notes.append(("warn", f"{file.name}: {exc}"))
        except (SessionBudgetExceeded, DailyBudgetExceeded):
            notes.append(("error", f"{file.name}: limite de gasto atingido; o arquivo não foi indexado."))
        except Exception as exc:  # embedding call failed
            notes.append(("error", f"{file.name}: falha ao indexar ({type(exc).__name__})."))
    return notes


def show_notes(notes):
    for kind, text in notes:
        st.markdown(f'<div class="ek-status ek-{kind}"><b>{ICONS[kind]}</b>{escape(text)}</div>',
                    unsafe_allow_html=True)


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
        model, unlocked = choose_model(service)
        st.subheader("Fontes da resposta")
        scopes = ["corpus"] + (["uploads", "all"] if service.uploads else [])
        if st.session_state.get("scope") not in scopes:
            st.session_state["scope"] = "uploads" if service.uploads else "corpus"
        scope = st.radio("Onde buscar", scopes, key="scope", format_func=SCOPE_LABELS.get,
                         label_visibility="collapsed")
        if service.uploads:
            for upload in list(service.uploads.values()):
                st.caption(f"{upload.document_id} · {upload.name} · {len(upload.units)} trechos")
                if st.button("Remover " + upload.document_id, key="rm-" + upload.document_id,
                             use_container_width=True):
                    service.remove_upload(upload.document_id)
                    st.rerun()
        else:
            st.caption("Anexe arquivos pelo botão + do campo de pergunta para consultar os seus próprios "
                       "documentos: " + ", ".join(SUPPORTED_SUFFIXES) + ".")
        st.subheader("Consumo da sessão")
        st.metric("Gasto estimado", f"US$ {service.session_cost:.4f}")
        st.caption(f"{service.questions} pergunta(s) · teto da sessão US$ {config['max_cost_per_session_usd']}")
        st.subheader("Base de conhecimento")
        st.caption(f"{service.documents} documentos · {len(service.units)} trechos")
        st.subheader("Exemplos")
        for example in EXAMPLES:
            if st.button(example, use_container_width=True):
                st.session_state["pending"] = example
        if st.button("Reiniciar sessão", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    history = st.session_state.setdefault("history", [])
    for index, (question, answer, notes) in enumerate(history):
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            show_notes(notes)
            if answer is not None:
                show(answer, service, index)
    submitted = st.chat_input("Pergunte sobre as políticas e procedimentos ou anexe um documento",
                              accept_file="multiple", file_type=[x.lstrip(".") for x in SUPPORTED_SUFFIXES])
    st.markdown('<div class="ek-privacy">Arquivos anexados são lidos em memória só nesta sessão e enviados '
                'à OpenAI para indexação e resposta. Não anexe documentos confidenciais.</div>',
                unsafe_allow_html=True)
    files = list(submitted.files) if submitted else []
    question = (submitted.text if submitted else None) or st.session_state.pop("pending", None)
    if not question and not files:
        return
    label = question or "Anexei " + ", ".join(file.name for file in files)
    with st.chat_message("user"):
        st.write(label)
    with st.chat_message("assistant"):
        notes = []
        if files:
            with st.spinner("Lendo e indexando os documentos anexados..."):
                notes = ingest(service, files)
            if any(kind == "ok" for kind, _ in notes):
                scope = "uploads"
                st.session_state.pop("scope", None)
        show_notes(notes)
        answer = None
        if question:
            try:
                with st.spinner("Buscando evidências e verificando a resposta..."):
                    answer = service.ask(question, model=model, scope=scope, unlocked=unlocked)
            except SessionBudgetExceeded:
                st.error("O teto de gasto desta sessão foi atingido. Reinicie a sessão para continuar.")
                return
            except DailyBudgetExceeded:
                st.error("O limite diário de uso desta demonstração foi atingido. Tente novamente amanhã.")
                return
            except ModelLocked:
                st.error("Este modelo precisa ser liberado com a senha na barra lateral.")
                return
            except ValueError as exc:
                st.error(str(exc))
                return
            show(answer, service, len(history))
    history.append((label, answer, notes))
    st.rerun()


if __name__ == "__main__":
    main()
