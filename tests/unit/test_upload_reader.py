"""Reader for files attached in the chat; files are built in memory, no API calls."""
from io import BytesIO

import pytest

from app.service.upload_reader import UploadError, build_units, read_passages


def docx_bytes():
    import docx
    document = docx.Document()
    document.add_heading("Política de Viagens", level=1)
    document.add_paragraph("Reembolsos exigem recibo e aprovação do gestor em até 30 dias.")
    document.add_heading("Hospedagem", level=1)
    document.add_paragraph("O limite de diária é de R$ 450 em capitais.")
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def xlsx_bytes():
    from openpyxl import Workbook
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Limites"
    sheet.append(["Categoria", "Limite", "Aprovador"])
    sheet.append(["Passagem aérea", "R$ 3.000", "Gerente"])
    sheet.append(["Hospedagem", "R$ 450", "Coordenador"])
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def pptx_bytes():
    from pptx import Presentation
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[1])
    slide.shapes.title.text = "Regras de reembolso"
    slide.placeholders[1].text = "Recibo obrigatório\nPrazo de 30 dias"
    buffer = BytesIO()
    presentation.save(buffer)
    return buffer.getvalue()


def pdf_bytes(text="Reembolsos exigem recibo e aprovação do gestor."):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buffer = BytesIO()
    page = canvas.Canvas(buffer, pagesize=A4)
    if text:
        page.drawString(72, 760, text)
    page.showPage()
    page.save()
    return buffer.getvalue()


def test_docx_keeps_headings_as_sections():
    passages = read_passages("viagens.docx", docx_bytes())
    assert [section for section, _ in passages] == [("Política de Viagens",), ("Hospedagem",)]
    assert "R$ 450" in passages[1][1]


def test_xlsx_rows_carry_their_column_labels():
    passages = read_passages("limites.xlsx", xlsx_bytes())
    assert passages[0][0] == ("Limites", "Linha 2")
    assert "Categoria: Passagem aérea" in passages[0][1] and "Aprovador: Gerente" in passages[0][1]
    assert len(passages) == 2


def test_pptx_is_split_by_slide_with_its_title():
    (section, text), = read_passages("regras.pptx", pptx_bytes())
    assert section == ("Slide 1: Regras de reembolso",) and "Prazo de 30 dias" in text


def test_pdf_text_is_read_by_page_and_image_only_pdf_is_refused():
    (section, text), = read_passages("regras.pdf", pdf_bytes())
    assert section == ("Página 1",) and "recibo" in text
    with pytest.raises(UploadError, match="digitalizados"):
        read_passages("scan.pdf", pdf_bytes(text=""))


def test_markdown_and_text_are_supported():
    markdown = "# Escopo\n\nVale para todos.\n\n# Prazo\n\nTrinta dias.".encode("utf-8")
    assert [s for s, _ in read_passages("regra.md", markdown)] == [("Escopo",), ("Prazo",)]
    assert read_passages("nota.txt", "Uma regra simples.".encode("utf-8"))[0][1] == "Uma regra simples."


def test_unsupported_empty_and_corrupt_files_are_refused_with_a_clear_message():
    with pytest.raises(UploadError, match="Formato não suportado"):
        read_passages("planilha.csv", b"a,b")
    with pytest.raises(UploadError, match="vazio"):
        read_passages("vazio.txt", b"")
    with pytest.raises(UploadError, match="Não foi possível ler"):
        read_passages("quebrado.docx", b"not a zip file")


def test_long_text_is_split_into_bounded_passages():
    passages = read_passages("longo.txt", ("palavra " * 1000).encode("utf-8"))
    assert len(passages) > 3 and all(len(text) <= 1500 for _, text in passages)


def test_units_are_ready_searchable_and_uniquely_identified():
    units = build_units("UP-01", "viagens.docx", docx_bytes())
    assert len({u.unit_id for u in units}) == len(units) == 2
    assert all(u.status == "ready" and u.searchable and u.document_id == "UP-01" for u in units)
    assert units[0].search_text.startswith("Document: UP-01\nTitle: viagens.docx")
    assert units[0].reading_text.startswith("Política de Viagens")
