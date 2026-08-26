#!/usr/bin/env python
"""
Build print/printing-instructions.docx — the sheet that goes out by email
alongside the artwork.

    python scripts/build-instructions.py

Deliberately plain. This one is a working document for whoever is at the
printer, not a piece of the wedding stationery, so no border and no
decoration — just legible type and headings you can skim on a phone.
"""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "print" / "printing-instructions.docx"

INK = RGBColor(0x22, 0x2D, 0x2A)
PETROL = RGBColor(0x2C, 0x5D, 0x63)
WAX = RGBColor(0x88, 0x3A, 0x2D)
DISPLAY = "Georgia"
BODY = "Garamond"


def _font(run, name):
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = rpr.makeelement(qn("w:rFonts"), {})
        rpr.insert(0, rf)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), name)


def para(doc, text="", *, font=BODY, size=11, colour=INK, bold=False,
         italic=False, align=WD_ALIGN_PARAGRAPH.LEFT, before=0, after=4,
         style=None):
    p = doc.add_paragraph(style=style)
    p.alignment = align
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    if text:
        r = p.add_run(text)
        r.font.size = Pt(size)
        r.font.color.rgb = colour
        r.bold = bold
        r.italic = italic
        _font(r, font)
    return p


def heading(doc, text, size=14, before=9):
    return para(doc, text, font=DISPLAY, size=size, colour=PETROL,
                bold=True, before=before, after=6)


def bullet(doc, text, bold_lead=None):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    if bold_lead:
        r = p.add_run(bold_lead)
        r.font.size = Pt(11); r.font.color.rgb = INK; r.bold = True
        _font(r, BODY)
    r = p.add_run(text)
    r.font.size = Pt(11); r.font.color.rgb = INK
    _font(r, BODY)
    return p


def build():
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = BODY
    normal.font.size = Pt(11)
    # Set the style's rFonts directly, or Word falls back to Calibri for
    # anything we don't style run-by-run (bullets, table cells).
    rpr = normal.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = rpr.makeelement(qn("w:rFonts"), {})
        rpr.insert(0, rf)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), BODY)

    sec = doc.sections[0]
    sec.page_width, sec.page_height = Mm(210), Mm(297)
    for m in ("left_margin", "right_margin"):
        setattr(sec, m, Mm(20))
    sec.top_margin, sec.bottom_margin = Mm(15), Mm(14)

    # ---------------------------------------------------------------- head
    para(doc, "BECKI & JASE  ·  29 AUGUST 2026", font=DISPLAY, size=8,
         colour=PETROL, after=2)
    para(doc, "Printing and framing instructions", font=DISPLAY, size=18,
         colour=INK, bold=True, after=3)
    para(doc, "Six documents, 39 sheets in total. Two of them need trimming; "
              "the rest print and go straight into a frame.",
         size=11, italic=True, colour=PETROL, after=7)

    # ------------------------------------------------------------ critical
    heading(doc, "First — print at actual size", before=4)
    para(doc,
         "In the print dialog, set scaling to 100%, \"Actual size\" or "
         "\"No scaling\".",
         size=11, after=4)
    para(doc,
         "Do NOT use \"Fit to page\", \"Shrink to fit\" or \"Scale to paper "
         "size\". Those change the dimensions by a few per cent, which is "
         "enough that the trimmed cards no longer fit the frames.",
         size=11, bold=True, colour=WAX, after=6)
    para(doc,
         "Print one sheet first and measure it before running the rest.",
         size=10.5, italic=True, colour=PETROL, after=2)

    # --------------------------------------------------------------- table
    heading(doc, "What to print")

    rows = [
        ("Document", "Sheets", "Paper", "Cut?"),
        ("table-cards", "9", "A4, landscape", "No"),
        ("ring-blessing", "1", "A4, portrait", "No"),
        ("gifts", "1", "A4, portrait", "No"),
        ("favours", "1", "A5, portrait", "Yes — see below"),
        ("pegging", "1", "A5, landscape", "Yes — see below"),
        ("place-cards", "26", "A6, portrait", "No — folded"),
    ]
    t = doc.add_table(rows=len(rows), cols=4)
    t.style = "Table Grid"
    widths = (Mm(52), Mm(20), Mm(40), Mm(54))
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = t.cell(ri, ci)
            cell.width = widths[ci]
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            r = p.add_run(val)
            r.font.size = Pt(10)
            r.font.color.rgb = INK if ri else PETROL
            r.bold = ri == 0
            _font(r, BODY)

    para(doc, "Designed for coloured paper — no background fill anywhere, so "
              "the stock shows through.",
         size=10.5, italic=True, colour=PETROL, before=4, after=4)

    # ----------------------------------------------------------- the cuts
    heading(doc, "The two that need cutting")
    para(doc,
         "These print onto A5 but end up smaller, so they sit properly inside "
         "the frame instead of being swallowed by its edge.",
         size=11, after=4)

    bullet(doc, "Follow the faint grey line printed near the edge. Cut along "
                "it — the line itself comes away with the offcut, so nothing "
                "shows on the finished card.", "Cut along the line. ")
    bullet(doc, "The flowers deliberately carry on past the line. That is "
                "there so a slightly wandering cut still has colour running "
                "to the edge. You are not meant to cut around them.",
           "Ignore the artwork beyond it. ")
    bullet(doc, "Anywhere within a few millimetres of the line is fine. It "
                "does not need to be exact.", "Close enough is fine. ")

    para(doc, "Finished sizes after cutting:", size=11, bold=True,
         before=4, after=3)
    bullet(doc, "130mm wide × 180mm tall", "Favours — ")
    bullet(doc, "180mm wide × 130mm tall", "Pegging — ")
    para(doc,
         "The A5 frames only show 118 × 169mm, so a 130 × 180mm card is held "
         "by the frame instead of dropping through. A4 frames show "
         "198 × 289mm and take a full sheet, which is why those aren't cut.",
         size=10.5, italic=True, colour=PETROL, before=3, after=2)

    # ------------------------------------------------------------ no cuts
    heading(doc, "The ones that don't need cutting")
    para(doc,
         "Table cards, Ring Blessing and Gifts print onto a full sheet and go "
         "straight into the frame. No line, nothing to trim.",
         size=11, after=4)

    heading(doc, "Place cards")
    para(doc,
         "26 cards, one per person on the top table. Not framed — each folds "
         "in half across the middle so it stands up.",
         size=11, after=3)
    bullet(doc, "The design sits on the bottom half of the sheet. The top "
                "half is blank on purpose — it becomes the back.")
    bullet(doc, "Fold across the middle, with the blank half folding "
                "backwards. Lining the corners up puts the fold in the right "
                "place.")
    bullet(doc, "If your printer won't take A6, print four to an A4 sheet at "
                "100% and cut into quarters — but check the first one "
                "measures 105mm across before doing the rest.")

    # The frame openings used to be a section of their own down here, but they
    # read better as a footnote beside the trim sizes they explain — and it
    # keeps the whole sheet on one page.

    OUT.parent.mkdir(exist_ok=True)
    doc.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
