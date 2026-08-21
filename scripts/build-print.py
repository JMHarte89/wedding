#!/usr/bin/env python
"""
Build the printed materials for the day into print/*.docx.

    python scripts/build-print.py

Table cards are generated from data/guestlist.csv and the menu is read from
js/menu.js — the same file the website renders from — so re-run this after any
change to the guest list, the seating or the menu. Nothing here is hand-keyed.

Run scripts/extract-border.py first (or after changing print/sunflower.jpg) to
regenerate the watercolour border in assets/.

Design rules (these print onto coloured stock):
  * No shading or background fill anywhere — the paper must show through.
    The border art is keyed to transparency for exactly this reason.
  * Ink only, in the site palette: ink #222d2a, petrol #2c5d63, wax #883a2d.
  * Fraunces / EB Garamond aren't installed on this machine, so we use the
    same fallbacks the site's CSS declares: Georgia for display, Garamond
    for body.
"""

import csv
import io
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import qrcode
from qrcode.constants import ERROR_CORRECT_Q
from PIL import Image

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from docx.shared import Inches, Mm, Pt, RGBColor
from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "guestlist.csv"
MENU_PATH = ROOT / "js" / "menu.js"
OUT_DIR = ROOT / "print"

# Watercolour border, lifted from print/sunflower.jpg by scripts/extract-border.py.
# Transparent everywhere except the artwork, so coloured stock still shows through.
BORDER_LANDSCAPE = ROOT / "assets" / "border-landscape.png"
BORDER_PORTRAIT = ROOT / "assets" / "border-portrait.png"

AGENDA_URL = "https://jmharte89.github.io/wedding/agenda.html"
GOFUNDME_URL = "https://gofund.me/c3356285c"

# Site palette (css/invitation.css :root)
INK = RGBColor(0x22, 0x2D, 0x2A)
PETROL = RGBColor(0x2C, 0x5D, 0x63)
WAX = RGBColor(0x88, 0x3A, 0x2D)

PETROL_RGB = (0x2C, 0x5D, 0x63)
INK_RGB = (0x22, 0x2D, 0x2A)
WAX_RGB = (0x88, 0x3A, 0x2D)

# Fraunces and EB Garamond are webfonts and aren't installed locally; these
# are the exact fallbacks --font-display / --font-body name in the CSS.
FONT_DISPLAY = "Georgia"
FONT_BODY = "Garamond"

# Members that are placeholders rather than people.
PLACEHOLDERS = {"plus-one", "plus one", "+1", "daughter", "son", "child", "tbc"}

# Table-card type sizes, taken from the Elm card as hand-edited in the .docx.
TABLE_NAME_SIZE_PT = 48
NAME_SIZE_PT = 18

# Place cards use first names for the couple and their own — a place card is
# addressed to the person sitting there, not a register entry. Everyone else
# keeps their full name, so this is a deliberate short list, not a rule.
PLACE_CARD_NAMES = {
    "Jase Harte": "Jase",
    "Becki Harte": "Becki",
    "Thomas Carruthers": "Thomas",
}


# ----------------------------------------------------------------------
# Artwork
# ----------------------------------------------------------------------

def _quad(p0, p1, p2, steps=48):
    """Points along a quadratic bezier."""
    out = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        out.append((
            u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
            u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1],
        ))
    return out


def page_ornament(w_mm, h_mm):
    """The full-page trim: the watercolour sunflower-and-foliage border.

    Sourced from print/sunflower.jpg and prepared by scripts/extract-border.py,
    which strips the text that was composited into that JPEG and keys the white
    field to transparent so coloured stock still shows through.

    Returned at page size and pinned to the page by corner_trim(), which is
    what keeps it symmetric — the original tab-stop approach inherited the
    built-in Header style's centre tab and pulled the right-hand art toward
    the middle of the page.

    A-series pages are all 1:root-2, so the landscape scan serves landscape
    pages and its rotation serves portrait ones. The source is 1.486 against
    1.414 — a 5% difference, absorbed in the fit and invisible on foliage.
    """
    src = BORDER_LANDSCAPE if w_mm >= h_mm else BORDER_PORTRAIT
    if not src.exists():
        sys.exit(f"Missing {src} — run: python scripts/extract-border.py")
    buf = io.BytesIO()
    Image.open(src).convert("RGBA").save(buf, format="PNG")
    buf.seek(0)
    return buf


def qr_png(url, modules_colour=INK_RGB):
    """QR with a transparent background so the paper provides the light field.

    Keeping the quiet zone transparent rather than white is what lets these
    sit on coloured stock without a white tile around them. Decoding is
    verified against the rendered PDF, not just the generated image.
    """
    qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_Q,
                       box_size=16, border=3)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, _g, _b, _a = px[x, y]
            if r > 128:                       # light module -> let paper through
                px[x, y] = (0, 0, 0, 0)
            else:
                px[x, y] = modules_colour + (255,)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ----------------------------------------------------------------------
# Document furniture
# ----------------------------------------------------------------------

def style_run(run, *, font, size, colour, bold=False, italic=False,
              spacing=None, caps=False):
    run.font.name = font
    run.font.size = Pt(size)
    run.font.color.rgb = colour
    run.bold = bold
    run.italic = italic
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = rpr.makeelement(qn("w:rFonts"), {})
        rpr.insert(0, rf)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(attr), font)
    if spacing is not None:                   # letter-spacing, in twentieths pt
        sp = rpr.makeelement(qn("w:spacing"), {qn("w:val"): str(int(spacing * 20))})
        rpr.append(sp)
    if caps:
        rpr.append(rpr.makeelement(qn("w:caps"), {qn("w:val"): "1"}))
    return run


def para(container, text="", *, align=WD_ALIGN_PARAGRAPH.CENTER,
         space_before=0, space_after=6, **run_kw):
    p = container.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    if text:
        style_run(p.add_run(text), **run_kw)
    return p


def set_page(section, width_mm, height_mm, *, landscape=False, margin_mm=18):
    if landscape:
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width = Mm(max(width_mm, height_mm))
        section.page_height = Mm(min(width_mm, height_mm))
    else:
        section.orientation = WD_ORIENT.PORTRAIT
        section.page_width = Mm(min(width_mm, height_mm))
        section.page_height = Mm(max(width_mm, height_mm))
    section.left_margin = Mm(margin_mm)
    section.right_margin = Mm(margin_mm)
    section.top_margin = Mm(margin_mm)
    section.bottom_margin = Mm(margin_mm)
    section.header_distance = Mm(9)
    section.footer_distance = Mm(9)


def vertically_centre(section):
    sect_pr = section._sectPr
    v = sect_pr.makeelement(qn("w:vAlign"), {qn("w:val"): "center"})
    sect_pr.append(v)


_ANCHOR = (
    '<wp:anchor xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/'
    'wordprocessingDrawing" distT="0" distB="0" distL="0" distR="0" '
    'simplePos="0" relativeHeight="0" behindDoc="1" locked="0" '
    'layoutInCell="1" allowOverlap="1">'
    '<wp:simplePos x="0" y="0"/>'
    '<wp:positionH relativeFrom="page"><wp:posOffset>{x}</wp:posOffset></wp:positionH>'
    '<wp:positionV relativeFrom="page"><wp:posOffset>{y}</wp:posOffset></wp:positionV>'
    '<wp:extent cx="{cx}" cy="{cy}"/>'
    '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
    '<wp:wrapNone/>'
    '<wp:docPr id="{did}" name="Trim {did}"/>'
    '<wp:cNvGraphicFramePr/>'
    '{graphic}'
    '</wp:anchor>'
)


def corner_trim(section, did=1, panel=None):
    """Lay the page trim behind the text, pinned to the page itself.

    The image is placed as a floating anchor at an exact page offset, so its
    position cannot be perturbed by margins, paragraph styles or inherited tab
    stops. Living in the header means it repeats on every page — needed for
    the multi-page card documents — without taking part in the body's layout.

    `panel` is an optional (x_mm, y_mm, w_mm, h_mm) rectangle. Default is the
    whole page; the folded place cards pass the bottom half so the border
    lands only on the face that ends up outward once the card is folded.
    """
    if panel is None:
        x_mm, y_mm = 0.0, 0.0
        w_mm, h_mm = section.page_width.mm, section.page_height.mm
    else:
        x_mm, y_mm, w_mm, h_mm = panel

    stream = page_ornament(w_mm, h_mm)

    p = section.header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = Pt(1)
    run = p.add_run()
    run.font.size = Pt(1)                 # keep the header line height at nil
    run.add_picture(stream, width=Mm(w_mm), height=Mm(h_mm))

    # Convert the inline drawing python-docx just made into a page anchor.
    inline = run._element.find(qn("w:drawing")).find(qn("wp:inline"))
    graphic = inline.find(qn("a:graphic"))
    extent = inline.find(qn("wp:extent"))
    xml = _ANCHOR.format(
        cx=extent.get("cx"), cy=extent.get("cy"), did=did,
        x=int(Mm(x_mm)), y=int(Mm(y_mm)),
        graphic=etree.tostring(graphic).decode("utf-8"),
    )
    inline.getparent().replace(inline, parse_xml(xml))


def new_doc(width_mm, height_mm, *, landscape=False, margin_mm=18,
            centre=True, did=1, margins=None, panel=None):
    doc = Document()
    # Document-wide default so nothing falls back to Calibri.
    normal = doc.styles["Normal"]
    normal.font.name = FONT_BODY
    normal.font.size = Pt(12)
    normal.font.color.rgb = INK
    rpr = normal.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = rpr.makeelement(qn("w:rFonts"), {})
        rpr.insert(0, rf)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(attr), FONT_BODY)

    sec = doc.sections[0]
    set_page(sec, width_mm, height_mm, landscape=landscape, margin_mm=margin_mm)
    if margins:                           # (left, top, right, bottom) in mm
        l, t, r, b = margins
        sec.left_margin, sec.top_margin = Mm(l), Mm(t)
        sec.right_margin, sec.bottom_margin = Mm(r), Mm(b)
    corner_trim(sec, did=did, panel=panel)
    if centre:
        vertically_centre(sec)
    return doc


def rule(container):
    """A small centred ornament rule — three petrol dots, understated."""
    return para(container, "· · ·", font=FONT_DISPLAY, size=12, colour=PETROL,
                spacing=3.0, space_before=4, space_after=10)


def add_qr(container, url, caption, *, size_in=0.95, colour=INK_RGB):
    p = container.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(qr_png(url, colour), width=Inches(size_in))
    para(container, caption, font=FONT_BODY, size=8.5, colour=PETROL,
         italic=True, space_after=0)


# ----------------------------------------------------------------------
# Guest list
# ----------------------------------------------------------------------

def clean_member(raw):
    """'Jerome (12)' -> 'Jerome'; placeholders -> None."""
    name = re.sub(r"\s*\(\s*\d+\s*\)\s*$", "", (raw or "").strip())
    name = re.sub(r"\s+", " ", name).strip()
    if not name or name.lower() in PLACEHOLDERS:
        return None
    return name


def read_menu():
    """Load the menu from js/menu.js — the same file the website renders.

    The file is evaluated with Node rather than parsed here, so the printed
    menu is by construction the identical object the browser sees. Re-keying
    it into Python would be a second copy to keep in sync, which is exactly
    what the shared data file exists to prevent.
    """
    node = shutil.which("node")
    if not node:
        sys.exit("Node is needed to read js/menu.js (it is the menu's single "
                 "source of truth). Install Node, or run with --skip-menu.")

    script = (
        "const fs=require('fs');"
        "const root={};"
        "new Function('window',fs.readFileSync(process.argv[1],'utf8'))(root);"
        "process.stdout.write(JSON.stringify(root.WEDDING_MENU));"
    )
    out = subprocess.run([node, "-e", script, str(MENU_PATH)],
                         capture_output=True, check=True)
    menu = json.loads(out.stdout.decode("utf-8"))
    if not menu or not menu.get("blocks"):
        sys.exit("js/menu.js parsed but contained no blocks.")
    return menu


def read_tables():
    tables = {}
    order = []
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            table = (row.get("table") or "").strip()
            if not table:
                continue
            if table not in tables:
                tables[table] = []
                order.append(table)
            for m in (row.get("members") or "").split("|"):
                name = clean_member(m)
                if name and name not in tables[table]:
                    tables[table].append(name)

    # Top table leads; the rest alphabetically, for a tidy print run.
    def key(t):
        return (0, "") if t.strip().lower() == "top table" else (1, t.lower())

    return [(t, tables[t]) for t in sorted(order, key=key)]


def names_block(doc, names):
    """Lay the names out in 1–3 borderless columns depending on how many.

    Size is fixed at NAME_SIZE_PT rather than shrinking to fit: the cards are
    A4 landscape and no table now exceeds twelve people, so there is room to
    keep every card typographically identical.
    """
    n = len(names)
    cols = 1 if n <= 5 else (2 if n <= 12 else 3)
    rows = -(-n // cols)
    size, lead = NAME_SIZE_PT, 2
    table = doc.add_table(rows=rows, cols=cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True

    # Belt and braces: the default table style carries no borders, but say so
    # explicitly so a Word default can't reintroduce lines. No shading, ever.
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.makeelement(qn("w:tblBorders"), {})
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = borders.makeelement(qn("w:" + edge), {qn("w:val"): "none",
                                                 qn("w:sz"): "0",
                                                 qn("w:space"): "0"})
        borders.append(e)
    tbl_pr.append(borders)

    for i, name in enumerate(names):
        cell = table.cell(i % rows, i // rows)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(lead)
        p.paragraph_format.space_after = Pt(lead)
        style_run(p.add_run(name), font=FONT_BODY, size=size, colour=INK)
    return table


# ----------------------------------------------------------------------
# The four documents
# ----------------------------------------------------------------------

def build_table_cards():
    """One A4 landscape card per table.

    No card for the top table: those guests get an individual folded place
    card instead, so a shared list would be redundant.

    Sizes follow the Elm card as hand-edited in the .docx — 48pt table name,
    18pt guest names, 11pt kicker, and no dot rule under the heading.
    """
    tables = [(name, people) for name, people in read_tables()
              if name.strip().lower() != "top table"]

    doc = new_doc(297, 210, landscape=True, centre=True, did=11,
                  margins=(46, 30, 46, 30))

    for idx, (name, people) in enumerate(tables):
        kicker = para(doc, "", font=FONT_DISPLAY, size=11, colour=PETROL,
                      space_after=6)
        if idx:
            # Break lives on the first run of the new card, not in a spacer
            # paragraph — an empty paragraph would throw off vertical centring.
            kicker.add_run().add_break(WD_BREAK.PAGE)
        style_run(kicker.add_run("You are seated at"), font=FONT_DISPLAY,
                  size=11, colour=PETROL, spacing=2.6, caps=True)
        para(doc, name, font=FONT_DISPLAY, size=TABLE_NAME_SIZE_PT,
             colour=INK, bold=True, space_after=10)
        names_block(doc, people)
        add_qr(doc, AGENDA_URL, "Scan for the order of the day", size_in=0.95)

    OUT_DIR.mkdir(exist_ok=True)
    doc.save(OUT_DIR / "table-cards.docx")
    return tables


def build_place_cards(tables):
    """One folded place card per person on the top table.

    Printed on A6 portrait and folded in half across the middle, giving a
    105 x 74mm tent card. Everything — border and name — sits in the BOTTOM
    half of the sheet, so once the top half is folded back it becomes the
    outward face. The top half is left completely blank: it becomes the back
    support, and anything printed there would show through on light stock.

    Fold at the halfway point; aligning the sheet's corners lands it exactly
    on the top edge of the border, so no printed fold guide is needed.
    """
    top = next((people for name, people in read_tables()
                if name.strip().lower() == "top table"), [])
    if not top:
        print("  (no top table found — skipping place cards)")
        return []

    PAGE_W, PAGE_H = 105.0, 148.0         # A6
    HALF = PAGE_H / 2                     # 74mm — the fold line

    doc = new_doc(
        PAGE_W, PAGE_H,
        margins=(13, HALF + 9, 13, 8),    # text lives in the lower panel only
        centre=True, did=61,
        panel=(0.0, HALF, PAGE_W, HALF),  # border on the bottom half only
    )

    shown = []
    for idx, person in enumerate(top):
        label = PLACE_CARD_NAMES.get(person, person)
        shown.append(label)

        kicker = para(doc, "", font=FONT_DISPLAY, size=6, colour=PETROL,
                      space_after=2)
        if idx:
            kicker.add_run().add_break(WD_BREAK.PAGE)
        style_run(kicker.add_run("Top Table"), font=FONT_DISPLAY, size=6,
                  colour=PETROL, spacing=2.0, caps=True)

        # A6 halves the panel, so long names have to step down or they run
        # into the foliage. Measured against "Carole Blackshaw", the longest.
        n = len(label)
        size = 20 if n <= 11 else (17 if n <= 16 else 15)
        para(doc, label, font=FONT_DISPLAY, size=size, colour=INK,
             bold=True, space_after=2)
        para(doc, "· · ·", font=FONT_DISPLAY, size=6.5, colour=PETROL,
             spacing=2.0, space_after=0)

    doc.save(OUT_DIR / "place-cards.docx")
    return top


def build_ring_blessing():
    """A4 portrait. Wording and sizes as edited in the .docx."""
    doc = new_doc(210, 297, centre=True, did=21, margins=(40, 44, 40, 44))
    para(doc, "For Becki & Jase", font=FONT_DISPLAY, size=14, colour=PETROL,
         spacing=3.0, caps=True, space_after=12)
    para(doc, "Ring Blessing", font=FONT_DISPLAY, size=48, colour=INK,
         bold=True, space_after=8)
    rule(doc)
    para(doc,
         "These two rings will be exchanged today and worn for a lifetime.",
         font=FONT_BODY, size=18, colour=INK, space_after=12)
    para(doc,
         "Before they are, we would love you to take a moment to hold them "
         "and make a silent wish for the marriage \u2013 for patience, for "
         "laughter and for many happy years together.",
         font=FONT_BODY, size=18, colour=INK, space_after=14)
    rule(doc)
    para(doc, "Thank you", font=FONT_DISPLAY, size=18, colour=WAX,
         italic=True, space_after=0)
    doc.save(OUT_DIR / "ring-blessing.docx")


def build_favours():
    """A5 portrait. Wording as edited in the .docx."""
    doc = new_doc(148, 210, centre=True, did=31, margins=(26, 30, 26, 30))
    para(doc, "With our thanks", font=FONT_DISPLAY, size=9, colour=PETROL,
         spacing=2.6, caps=True, space_after=8)
    para(doc, "A Little Something to remember the day",
         font=FONT_DISPLAY, size=22, colour=INK, bold=True, space_after=6)
    rule(doc)
    para(doc, "Please take one or two home!",
         font=FONT_BODY, size=14, colour=INK, space_after=12)
    rule(doc)
    para(doc, "Becki & Jase  \u00b7  29th of August 2026",
         font=FONT_DISPLAY, size=11, colour=WAX, space_after=0)
    doc.save(OUT_DIR / "favours.docx")


def build_gifts():
    """A4 portrait. Wording as edited in the .docx."""
    doc = new_doc(210, 297, centre=True, did=41, margins=(44, 46, 44, 46))
    para(doc, "Becki & Jase", font=FONT_DISPLAY, size=11, colour=PETROL,
         spacing=2.8, caps=True, space_after=10)
    para(doc, "Gifts", font=FONT_DISPLAY, size=44, colour=INK,
         bold=True, space_after=6)
    rule(doc)
    para(doc,
         "We have a house, we have stuff, and between the kids and the dogs "
         "there's barely room for anything else.",
         font=FONT_BODY, size=16, colour=INK, space_after=10)
    para(doc, "The greatest gift you can give us is being here.",
         font=FONT_BODY, size=17, colour=INK, italic=True, space_after=10)
    para(doc,
         "But if you'd really like to give something, we're saving for our "
         "honeymoon \u2014 any contribution, however small, means the world.",
         font=FONT_BODY, size=16, colour=INK, space_after=6)
    add_qr(doc, GOFUNDME_URL,
           "Scan this QR code with your camera for our honeymoon fund",
           size_in=1.35)
    doc.save(OUT_DIR / "gifts.docx")


def build_pegging():
    """A5 landscape sign for the clothes-peg game.

    The heading carries the joke, so it is set as large as the border allows
    and the instruction sits quietly underneath.
    """
    doc = new_doc(210, 148, landscape=True, centre=True, did=71,
                  margins=(40, 26, 40, 26))
    para(doc, "A game", font=FONT_DISPLAY, size=9, colour=PETROL,
         spacing=2.6, caps=True, space_after=6)
    para(doc, "How Good Are You at Pegging?",
         font=FONT_DISPLAY, size=34, colour=INK, bold=True, space_after=6)
    rule(doc)
    para(doc,
         "See how many of these pegs you can surreptitiously attach to guests.",
         font=FONT_BODY, size=15, colour=INK, italic=True, space_after=0)
    doc.save(OUT_DIR / "pegging.docx")


def main():
    if not CSV_PATH.exists():
        sys.exit(f"Can't find {CSV_PATH}")
    if not MENU_PATH.exists():
        sys.exit(f"Can't find {MENU_PATH}")
    OUT_DIR.mkdir(exist_ok=True)

    # The menu is deliberately NOT printed — it lives on the website and on
    # the agenda page the QR codes point at. js/menu.js is still the source
    # for those, so nothing about the menu data has been removed.
    tables = build_table_cards()
    top = build_place_cards(tables)
    build_ring_blessing()
    build_favours()
    build_gifts()
    build_pegging()

    print(f"Fonts: display={FONT_DISPLAY}, body={FONT_BODY}")
    print(f"Table cards: {len(tables)} (top table excluded — they get "
          f"individual place cards)")
    for name, people in tables:
        print(f"  {name:<12} {len(people):>2} — {', '.join(people)}")
    total = sum(len(p) for _, p in tables)
    print(f"Seated at numbered tables: {total}")
    print(f"Place cards (top table, one per person): {len(top)}")
    print(f"  {', '.join(PLACE_CARD_NAMES.get(p, p) for p in top)}")


if __name__ == "__main__":
    main()
