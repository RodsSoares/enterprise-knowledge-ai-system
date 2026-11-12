"""Turn a file sent by the user into citable evidence units.

The corpus is parsed offline with Docling. A file sent in the chat is read at
runtime on a small server, so this module uses only light libraries (pypdf,
python-docx, openpyxl, python-pptx) and keeps structure as far as they expose
it: headings, pages, slides and spreadsheet rows. Scanned PDFs have no text
layer and are refused. Nothing is written to disk.
"""
from hashlib import sha256
from io import BytesIO
from pathlib import PurePath
import re

from app.chunking.evidence_units import EvidenceUnit, SourceRef

SUPPORTED_SUFFIXES = (".pdf", ".docx", ".xlsx", ".pptx", ".md", ".txt")
REPRESENTATION = "upload-units/1"
MAX_UNIT_CHARS = 1500
MAX_ROWS_PER_SHEET = 400


class UploadError(ValueError):
    """The file cannot be used; the message is safe to show to the user."""


def _clean(text):
    return re.sub(r"[ \t]+", " ", text.replace("\x00", " ")).strip()


def _pack(section, paragraphs):
    """Group consecutive paragraphs of one section into bounded passages."""
    passages, current = [], ""
    for paragraph in paragraphs:
        paragraph = _clean(paragraph)
        if not paragraph:
            continue
        while len(paragraph) > MAX_UNIT_CHARS:
            cut = paragraph.rfind(" ", 0, MAX_UNIT_CHARS)
            cut = cut if cut > MAX_UNIT_CHARS // 2 else MAX_UNIT_CHARS
            if current:
                passages.append((section, current))
                current = ""
            passages.append((section, paragraph[:cut]))
            paragraph = paragraph[cut:].strip()
        if current and len(current) + len(paragraph) + 1 > MAX_UNIT_CHARS:
            passages.append((section, current))
            current = ""
        current = (current + "\n" + paragraph) if current else paragraph
    if current:
        passages.append((section, current))
    return passages


def _read_pdf(data):
    from pypdf import PdfReader
    reader = PdfReader(BytesIO(data))
    if reader.is_encrypted:
        raise UploadError("PDF protegido por senha.")
    passages = []
    for number, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        passages += _pack((f"Página {number}",), re.split(r"\n\s*\n", text))
    return passages


def _read_docx(data):
    import docx
    document = docx.Document(BytesIO(data))
    passages, section, body = [], (), []
    for paragraph in document.paragraphs:
        text = _clean(paragraph.text)
        if not text:
            continue
        style = (paragraph.style.name or "") if paragraph.style is not None else ""
        if style.startswith("Heading") or style == "Title":
            passages += _pack(section, body)
            section, body = (text[:120],), []
        else:
            body.append(text)
    passages += _pack(section, body)
    for index, table in enumerate(document.tables, 1):
        rows = [" | ".join(_clean(cell.text) for cell in row.cells) for row in table.rows]
        passages += _pack((f"Tabela {index}",), rows)
    return passages


def _read_xlsx(data):
    from openpyxl import load_workbook
    workbook = load_workbook(BytesIO(data), read_only=True, data_only=True)
    passages = []
    try:
        for sheet in workbook:
            rows = sheet.iter_rows(values_only=True)
            header = None
            for number, row in enumerate(rows, 1):
                if number > MAX_ROWS_PER_SHEET:
                    break
                cells = ["" if value is None else _clean(str(value)) for value in row]
                if not any(cells):
                    continue
                if header is None:
                    header = cells
                    continue
                pairs = [f"{label or 'Coluna ' + str(i)}: {value}"
                         for i, (label, value) in enumerate(zip(header, cells), 1) if value]
                passages += _pack((sheet.title, f"Linha {number}"), ["\n".join(pairs)])
    finally:
        workbook.close()
    return passages


def _read_pptx(data):
    from pptx import Presentation
    passages = []
    for number, slide in enumerate(Presentation(BytesIO(data)).slides, 1):
        texts = [_clean(shape.text_frame.text) for shape in slide.shapes if shape.has_text_frame]
        texts = [text for text in texts if text]
        if not texts:
            continue
        title = texts[0].splitlines()[0][:100]
        passages += _pack((f"Slide {number}: {title}",), texts)
    return passages


def _read_text(data, markdown):
    text = data.decode("utf-8-sig", errors="replace")
    passages, section, body = [], (), []
    for block in re.split(r"\n\s*\n", text):
        first = block.strip().splitlines()[0] if block.strip() else ""
        if markdown and first.startswith("#"):
            passages += _pack(section, body)
            section, body = (first.lstrip("# ").strip()[:120],), block.strip().splitlines()[1:]
        else:
            body.append(block)
    return passages + _pack(section, body)


def read_passages(name, data):
    """(section_path, text) passages of a supported file."""
    suffix = PurePath(name).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise UploadError("Formato não suportado: " + (suffix or "sem extensão")
                          + ". Use " + ", ".join(SUPPORTED_SUFFIXES) + ".")
    if not data:
        raise UploadError("Arquivo vazio.")
    try:
        if suffix == ".pdf":
            passages = _read_pdf(data)
        elif suffix == ".docx":
            passages = _read_docx(data)
        elif suffix == ".xlsx":
            passages = _read_xlsx(data)
        elif suffix == ".pptx":
            passages = _read_pptx(data)
        else:
            passages = _read_text(data, markdown=suffix == ".md")
    except UploadError:
        raise
    except Exception as exc:  # corrupt or unexpected file content
        raise UploadError("Não foi possível ler o arquivo (" + type(exc).__name__ + ").") from exc
    if not passages:
        raise UploadError("Nenhum texto encontrado. PDFs digitalizados (imagem) não são suportados.")
    return passages


def build_units(document_id, name, data):
    """Evidence units of an uploaded file, in reading order."""
    revision = sha256(data).hexdigest()
    units = []
    for index, (section, text) in enumerate(read_passages(name, data)):
        reading = (" › ".join(section) + "\n\n" + text) if section else text
        digest = sha256((revision + str(index) + reading).encode("utf-8")).hexdigest()
        units.append(EvidenceUnit(
            unit_id=f"{document_id}::unit-{digest}", document_id=document_id,
            source_revision=revision, representation_version=REPRESENTATION,
            structural_role="section", section_path=tuple(section), parent_id=None,
            dependency_ids=(), source_refs=(SourceRef(f"upload-{index}", ""),),
            reading_text=reading,
            search_text=f"Document: {document_id}\nTitle: {name}\n\n{reading}",
            status="ready", searchable=True))
    return tuple(units)
