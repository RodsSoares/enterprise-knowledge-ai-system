"""RV-045: remove evaluation-harness text from the corpus documents.

A corpus document must read like a company document. This script removes
benchmark references, "synthetic / proposed / requires review" disclaimers and
instructions addressed to the reader or to the RAG system, and rewrites the few
sentences that carried a real rule mixed with such text. Business facts
(thresholds, roles, deadlines, percentages) are not changed.

PDFs are regenerated with ReportLab from the parsed structure stored in the
RV-044 snapshot. DOCX, PPTX, XLSX, Markdown and text files are edited in place.
No API call. Run once from the repository root, then rebuild the snapshot.
"""
import argparse
import json
from pathlib import Path
import re

CORPUS = Path("data/source/corporate_repository")
SOURCE_SNAPSHOT = Path("docs/validation/EVIDENCE_UNITS_SNAPSHOT_27DOC.json")

# Exact rewrites, applied before any sentence is dropped.
REWRITES = (
    ("proposed synthetic follow-up required", "follow-up required"),
    # A very short header line is read as a heading by the PDF layout model.
    ("DOC-004 | Version 1.4 | ACTIVE", "DOC-004 | Version 1.4 | Effective 2026-01-01 | ACTIVE"),
    ("Proposed notification window", "Notification window"),
    ("; active according to the document registry. This is a synthetic contract, not a real executed agreement.",
     "; active."),
    ("; active according to the document registry. This is a synthetic\ncontract, not a real executed agreement.",
     "; active."),
    ("Carrier selection is a human-authorized decision: the system must not invent a final recommendation unsupported by evidence.",
     "Carrier selection is a human-authorized decision and must be supported by documented evidence."),
    ("Active from 2026-01-01; authority level 4.", "Active from 2026-01-01."),
    ("It must not be used to answer current-policy questions.", "It is not current operating authority."),
    ("Exact historical category SLAs are not fixed by canonical facts; do not infer them from the current policy.",
     "Category-level delivery commitments for this period were defined in operational procedures and are not restated in this policy."),
    ("Historical comparison: DOC-001, DOC-019. Expected use: Q11 and Q28; distractor for Q10.",
     "DOC-001 (current Transportation Policy); DOC-019 (2025 committee minutes)."),
    ("Atlas and Nova both have delay penalties but use different bases and caps; Orion has no delay penalty clause. Contract terms must be assessed individually, and none of these contracts alone authorizes a final carrier selection.",
     "Contract terms are assessed on their own. This contract does not by itself authorize a final carrier selection."),
    ("This 2024 operational procedure is superseded. It is deliberately retained for conflict-resolution tests and must not be treated as current authority.",
     "This operational procedure was issued in 2024 and has been superseded."),
    ("External operational partners may receive customer information through corporate email. This historical statement conflicts with the active Information Security Policy DOC-006 when information is confidential.",
     "External operational partners may receive customer information through corporate email."),
    ("This document contains terms such as AI, supplier, carrier, approval, security, data, and contract. It is operational guidance, not the authoritative source for approval authority, confidential-data controls, or mandatory enterprise training.",
     "This guideline is operational guidance. Approval authority, confidential-data controls and mandatory enterprise training are defined in the governing policies and standards."),
)
# A sentence containing any of these is removed.
DROP = re.compile(
    r"synthetic|\bRV\d{3}\b|canonical[_ ]facts?|canonical fact|This threshold is canonical|benchmark|"
    r"golden set|expected use:|distractor|evaluation corpus|requir\w+ (acceptance|review)|pending review|"
    r"must not be used to answer|do not (infer|recommend|confuse)|semantic neighbor|"
    r"intentionally contains|conflict-resolution tests|test-universe", re.IGNORECASE)
HEADING_SUFFIX = re.compile(
    r"\s*[-—–]\s*(controlled synthetic (detail|mechanics)|proposed synthetic (definitions|list|details))\s*$",
    re.IGNORECASE)
HEADER_TAIL = re.compile(
    r"\s*(\|\s*)?(SYNTHETIC CONTROLLED CORPUS|Controlled synthetic (enterprise )?corpus).*$", re.DOTALL)
SENTENCES = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")
HEADING_RENAMES = {"6. Traceability": "6. Related documents",
                   "Authority and provenance": "Related documents",
                   "Comparison and authority": "Selection authority"}
# Sections removed with their content (heading text after suffix cleaning).
DROP_SECTIONS = {"Document control", "6. Evaluation role", "Retrieval caution",
                 "Current authority notice", "Historical interpretation", "IMPORTANT_NONE"}
XLSX_DROP_ROWS = {"Corpus Note", "corpus_type", "detail_status", "evaluation_questions",
                  "synthetic_detail_status", "authority_level", "format"}
XLSX_RENAME = {"canonical_OTIF_target": "OTIF_target"}
XLSX_DROP_COLUMNS = {"Canonical status"}


def clean_heading(text):
    text = HEADING_SUFFIX.sub("", text.strip())
    return HEADING_RENAMES.get(text, text)


def clean_text(text):
    """Cleaned paragraph; empty string when nothing but harness text remains."""
    text = " ".join(text.split())
    for old, new in REWRITES:
        text = text.replace(" ".join(old.split()), new)
    text = HEADER_TAIL.sub("", text) if re.match(r"^(DOC-\d{3}|Document ID)", text) else text
    kept = [s for s in SENTENCES.split(text) if s.strip() and not DROP.search(s)]
    return " ".join(kept).strip(" *")


def clean_blocks(blocks):
    """blocks: list of (kind, value). Returns cleaned blocks without emptied sections."""
    sections, current = [], None
    for kind, value in blocks:
        if kind in ("heading", "title"):
            current = [clean_heading(value), kind, []]
            sections.append(current)
        else:
            if current is None:
                current = [None, None, []]
                sections.append(current)
            if kind == "table":
                current[2].append((kind, value))
            else:
                text = clean_text(value)
                if text:
                    current[2].append((kind, text))
    result = []
    for index, (heading, kind, body) in enumerate(sections):
        if heading in DROP_SECTIONS:
            continue
        # The first heading is the document title; later headings need content.
        if heading is not None and (body or index == 0):
            result.append((kind, heading))
        result.extend(body)
    return result


def pdf_blocks(document):
    blocks = []
    for block in document["canonical"]["fields"]["blocks"]:
        fields = block["fields"]
        if block["type"] == "TextBlock":
            blocks.append((fields["kind"], fields["text"]))
        elif block["type"] == "TableBlock":
            blocks.append(("table", fields["rows"]))
    return blocks


def write_pdf(path, blocks):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from xml.sax.saxutils import escape
    title = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=16, leading=20, spaceAfter=6)
    heading = ParagraphStyle("heading", fontName="Helvetica-Bold", fontSize=13, leading=16,
                             spaceBefore=14, spaceAfter=5)
    body = ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=13, spaceAfter=4)
    cell = ParagraphStyle("cell", fontName="Helvetica", fontSize=8.5, leading=10.5)
    head = ParagraphStyle("head", parent=cell, fontName="Helvetica-Bold")
    story, first = [], True
    for kind, value in blocks:
        if kind in ("heading", "title"):
            story.append(Paragraph(escape(value), title if first else heading))
            first = False
        elif kind == "table":
            rows = [[Paragraph(escape(str(c)), head if r == 0 else cell) for c in row]
                    for r, row in enumerate(value)]
            table = Table(rows, colWidths=[(A4[0] - 40 * mm) / len(value[0])] * len(value[0]))
            table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                                       ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                                       ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story.extend([table, Spacer(1, 6)])
        else:
            story.append(Paragraph(escape(value), body))
    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                      topMargin=18 * mm, bottomMargin=18 * mm, invariant=1).build(story)


def clean_docx(path):
    import docx
    document = docx.Document(str(path))
    dropping = False
    for paragraph in list(document.paragraphs):
        style = paragraph.style.name
        is_heading = style.startswith("Heading") or style == "Title"
        if is_heading:
            new = clean_heading(paragraph.text)
            dropping = new in DROP_SECTIONS
        else:
            new = "" if dropping else clean_text(paragraph.text)
        if dropping or not new:
            paragraph._element.getparent().remove(paragraph._element)
        elif new != paragraph.text:
            for run in paragraph.runs[1:]:
                run._element.getparent().remove(run._element)
            if paragraph.runs:
                paragraph.runs[0].text = new
            else:
                paragraph.add_run(new)
    # Remove headings left without content before the next heading.
    paragraphs = document.paragraphs
    for index, paragraph in enumerate(paragraphs):
        if paragraph.style.name.startswith("Heading"):
            following = paragraphs[index + 1] if index + 1 < len(paragraphs) else None
            if following is None or following.style.name.startswith("Heading"):
                paragraph._element.getparent().remove(paragraph._element)
    document.save(str(path))


def clean_pptx(path):
    from pptx import Presentation
    presentation = Presentation(str(path))
    for slide in presentation.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for paragraph in list(shape.text_frame.paragraphs):
                if paragraph.text.strip() and not clean_text(paragraph.text):
                    paragraph._p.getparent().remove(paragraph._p)
    presentation.save(str(path))


def clean_xlsx(path):
    from openpyxl import load_workbook
    workbook = load_workbook(str(path))
    for sheet in workbook:
        for column in range(sheet.max_column, 0, -1):
            if sheet.cell(1, column).value in XLSX_DROP_COLUMNS:
                sheet.delete_cols(column)
        for row in range(sheet.max_row, 1, -1):
            key = sheet.cell(row, 1).value
            if key in XLSX_DROP_ROWS:
                sheet.delete_rows(row)
            elif key in XLSX_RENAME:
                sheet.cell(row, 1).value = XLSX_RENAME[key]
    workbook.save(str(path))


def clean_markup(path):
    """Markdown and plain text: headings are '#' lines or ALL-CAPS lines."""
    lines = path.read_text(encoding="utf-8").splitlines()
    output, dropping = [], False
    for line in lines:
        stripped = line.strip()
        is_heading = stripped.startswith("#") or (stripped.isupper() and len(stripped) > 3
                                                   and path.suffix == ".txt")
        if is_heading:
            name = clean_heading(stripped.lstrip("# "))
            dropping = name in DROP_SECTIONS
            if not dropping:
                output.append(line)
        elif not dropping:
            if not stripped or stripped.startswith(("**", "-")) or ":" in stripped[:12]:
                keep = line if not DROP.search(line) else None
            else:
                cleaned = clean_text(stripped.replace("**", "\0")).replace("\0", "**")
                keep = cleaned or None
            if keep is not None:
                output.append(keep)
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(output)).strip() + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--snapshot", type=Path, default=SOURCE_SNAPSHOT)
    p.add_argument("--corpus", type=Path, default=CORPUS)
    a = p.parse_args(argv)
    parsed = {d["document_id"]: d for d in
              json.loads(a.snapshot.read_text(encoding="utf-8"))["snapshot"]["documents"]}
    for path in sorted(a.corpus.rglob("DOC-*")):
        document_id = path.name.split("_", 1)[0]
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            write_pdf(path, clean_blocks(pdf_blocks(parsed[document_id])))
        elif suffix == ".docx":
            clean_docx(path)
        elif suffix == ".pptx":
            clean_pptx(path)
        elif suffix == ".xlsx":
            clean_xlsx(path)
        elif suffix in (".md", ".txt"):
            clean_markup(path)
        print("limpo:", path.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
