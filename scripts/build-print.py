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

    Type tightens as a table grows so even the 21-name top table stays on its
    own single card — the row count, not the name count, is what costs height.
    """
    n = len(names)
    cols = 1 if n <= 6 else (2 if n <= 14 else 3)
    rows = -(-n // cols)
    if rows >= 7:
        size, lead = 11.5, 0
    elif rows >= 6:
        size, lead = 12.0, 1
    else:
        size, lead = 12.5, 1
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
    tables = read_tables()
    # 22mm clears the vine's deepest inward ink (~19.5mm) with a little air,
    # while leaving enough height for the 21-name top table on one card.
    doc = new_doc(148, 210, landscape=True, margin_mm=22, centre=True, did=11)

    for idx, (name, people) in enumerate(tables):
        kicker = para(doc, "", font=FONT_DISPLAY, size=8.5, colour=PETROL,
                      space_after=4)
        if idx:
            # Break lives on the first run of the new card, not in a spacer
            # paragraph — an empty paragraph would throw off vertical centring.
            kicker.add_run().add_break(WD_BREAK.PAGE)
        style_run(kicker.add_run("You are seated at"), font=FONT_DISPLAY,
                  size=8.5, colour=PETROL, spacing=2.4, caps=True)
        para(doc, name, font=FONT_DISPLAY, size=28, colour=INK,
             bold=True, space_after=2)
        rule(doc)
        names_block(doc, people)
        add_qr(doc, AGENDA_URL, "Scan for the order of the day", size_in=0.82)

    OUT_DIR.mkdir(exist_ok=True)
    doc.save(OUT_DIR / "table-cards.docx")
    return tables


def build_place_cards(tables):
    """One folded place card per person on the top table.

    Printed on A5 portrait and folded in half across the middle, giving a
    148 x 105mm tent card. Everything — border and name — sits in the BOTTOM
    half of the sheet, so once the top half is folded back it becomes the
    outward face. The top half is left completely blank: it becomes the back
    support, and anything printed there would show through on light stock.

    Fold at the halfway point; aligning the sheet's corners lands it exactly
    on the top edge of the border, so no printed fold guide is needed.
    """
    top = next((people for name, people in tables
                if name.strip().lower() == "top table"), [])
    if not top:
        print("  (no top table found — skipping place cards)")
        return []

    PAGE_W, PAGE_H = 148.0, 210.0
    HALF = PAGE_H / 2                     # 105mm — the fold line

    doc = new_doc(
        PAGE_W, PAGE_H,
        margins=(16, HALF + 12, 16, 16),  # text lives in the lower panel only
        centre=True, did=61,
        panel=(0.0, HALF, PAGE_W, HALF),  # border on the bottom half only
    )

    for idx, person in enumerate(top):
        kicker = para(doc, "", font=FONT_DISPLAY, size=7.5, colour=PETROL,
                      space_after=3)
        if idx:
            kicker.add_run().add_break(WD_BREAK.PAGE)
        style_run(kicker.add_run("Top Table"), font=FONT_DISPLAY, size=7.5,
                  colour=PETROL, spacing=2.4, caps=True)

        # Long names need to step down a size or they crowd the foliage.
        size = 26 if len(person) <= 15 else (22 if len(person) <= 20 else 19)
        para(doc, person, font=FONT_DISPLAY, size=size, colour=INK,
             bold=True, space_after=3)
        para(doc, "· · ·", font=FONT_DISPLAY, size=8, colour=PETROL,
             spacing=2.4, space_after=0)

    doc.save(OUT_DIR / "place-cards.docx")
    return top


def build_menu(menu):
    """The food menu on a single A4 portrait page.

    A5 was the original intent, but it does not survive contact with the
    content: three courses and twenty-odd dishes with descriptions need about
    168mm of column, and the watercolour border claims roughly a quarter of an
    A5 sheet. Fitting it meant 6.9pt descriptions that still collided with the
    foliage. A4 keeps the same border and the same layout at a size people can
    actually read at a table.

    Left-aligned rather than centred — a centred ragged list of dish names is
    hard to scan.
    """
    # The border's corner blooms reach much further in than the middle of each
    # edge, so the margins are asymmetric: wider top and bottom to clear the
    # sunflowers, tighter left and right where only thin stems run.
    doc = new_doc(210, 297, centre=False, did=51,
                  margins=(38, 40, 38, 46))

    para(doc, "Becki & Jase", font=FONT_DISPLAY, size=8, colour=PETROL,
         spacing=2.4, caps=True, space_after=2)
    para(doc, "Food on the Day", font=FONT_DISPLAY, size=22, colour=INK,
         bold=True, space_after=2)
    para(doc, "· · ·", font=FONT_DISPLAY, size=8.5, colour=PETROL,
         spacing=2.6, space_after=7)

    for bi, block in enumerate(menu.get("blocks", [])):
        para(doc, block["heading"], font=FONT_DISPLAY, size=12.5, colour=INK,
             bold=True, align=WD_ALIGN_PARAGRAPH.LEFT,
             space_before=(8 if bi else 0), space_after=0)
        if block.get("time"):
            # Serving time echoes the website's timeline styling: small,
            # letter-spaced, petrol.
            para(doc, block["time"], font=FONT_BODY, size=8.5, colour=PETROL,
                 italic=True, spacing=0.5, align=WD_ALIGN_PARAGRAPH.LEFT,
                 space_after=4)

        for group in block.get("groups", []):
            if group.get("subheading"):
                para(doc, group["subheading"], font=FONT_DISPLAY, size=7.5,
                     colour=PETROL, spacing=1.8, caps=True,
                     align=WD_ALIGN_PARAGRAPH.LEFT,
                     space_before=4, space_after=2.5)
            for item in group.get("items", []):
                has_detail = bool(item.get("detail"))
                # Gap goes on the name when there's no detail line. An empty
                # spacer paragraph still costs a full line box, and across the
                # eleven-item buffet that alone overflowed the page.
                para(doc, item["name"], font=FONT_BODY, size=9.2, colour=INK,
                     align=WD_ALIGN_PARAGRAPH.LEFT,
                     space_after=(0 if has_detail else 2.0))
                if has_detail:
                    para(doc, item["detail"], font=FONT_BODY, size=7.8,
                         colour=INK, italic=True,
                         align=WD_ALIGN_PARAGRAPH.LEFT, space_after=2.5)

    para(doc, "· · ·", font=FONT_DISPLAY, size=8.5, colour=PETROL,
         spacing=2.6, space_before=7, space_after=4)
    para(doc, menu.get("footnote", ""), font=FONT_BODY, size=7.8,
         colour=PETROL, italic=True, align=WD_ALIGN_PARAGRAPH.LEFT,
         space_after=0)
    # No keep_with_next here: welding the closing rule to the last dish makes
    # Word push the whole group to a second page rather than split it, which
    # is the opposite of what a one-page menu needs.

    doc.save(OUT_DIR / "menu.docx")


def build_ring_blessing():
    doc = new_doc(210, 297, margin_mm=34, centre=True, did=21)
    para(doc, "For Becki & Jase", font=FONT_DISPLAY, size=10, colour=PETROL,
         spacing=3.0, caps=True, space_after=10)
    para(doc, "Bless These Rings", font=FONT_DISPLAY, size=34, colour=INK,
         bold=True, space_after=6)
    rule(doc)
    for line in (
        "These two rings will be exchanged today, and worn for a lifetime.",
        "Before they are, we would love them to pass through your hands.",
    ):
        para(doc, line, font=FONT_BODY, size=15, colour=INK, space_after=8)
    para(doc,
         "Hold them for a moment. Make a silent wish for the marriage — for "
         "patience, for laughter, for many ordinary happy years — and then "
         "pass them gently on.",
         font=FONT_BODY, size=15, colour=INK, italic=True, space_before=4,
         space_after=14)
    para(doc, "By the time they reach the altar, they will be carrying "
              "every good thing you wished into them.",
         font=FONT_BODY, size=15, colour=INK, space_after=12)
    rule(doc)
    para(doc, "Thank you", font=FONT_DISPLAY, size=13, colour=WAX,
         italic=True, space_after=0)
    doc.save(OUT_DIR / "ring-blessing.docx")


def build_favours():
    doc = new_doc(210, 297, margin_mm=34, centre=True, did=31)
    para(doc, "With our thanks", font=FONT_DISPLAY, size=10, colour=PETROL,
         spacing=3.0, caps=True, space_after=10)
    para(doc, "A Little Something", font=FONT_DISPLAY, size=34, colour=INK,
         bold=True, space_after=6)
    rule(doc)
    para(doc,
         "Thank you for being here today. Having you with us is the part "
         "we'll remember.",
         font=FONT_BODY, size=15, colour=INK, space_after=10)
    para(doc,
         "Please take a cork from the jar on your way — each one is stamped "
         "with today's date.",
         font=FONT_BODY, size=15, colour=INK, space_after=10)
    para(doc,
         "A small thing, from a day of rather a lot of them. Keep it "
         "somewhere you'll come across it by accident, and think of us.",
         font=FONT_BODY, size=15, colour=INK, italic=True, space_after=14)
    rule(doc)
    para(doc, "Becki & Jase  ·  29 August 2026", font=FONT_DISPLAY, size=12,
         colour=WAX, space_after=0)
    doc.save(OUT_DIR / "favours.docx")


def build_gifts():
    # 26mm: the rotated border reaches further in on the short edge of an A5
    # portrait page than it does on a landscape one, and at 20mm the body copy
    # was running into the foliage.
    doc = new_doc(148, 210, margin_mm=26, centre=True, did=41)
    para(doc, "Becki & Jase", font=FONT_DISPLAY, size=8.5, colour=PETROL,
         spacing=2.4, caps=True, space_after=8)
    para(doc, "Gifts", font=FONT_DISPLAY, size=30, colour=INK,
         bold=True, space_after=4)
    rule(doc)
    # Tone lifted from index.html, section id="no-gifts".
    para(doc,
         "We have a house, we have stuff, and between the kids and the dogs "
         "there's barely room for anything else.",
         font=FONT_BODY, size=12.5, colour=INK, space_after=8)
    para(doc, "The greatest gift you can give us is being there.",
         font=FONT_BODY, size=13.5, colour=INK, italic=True, space_after=8)
    para(doc,
         "But if you'd really like to do something, we're saving for our "
         "honeymoon — any contribution, however small, means the world.",
         font=FONT_BODY, size=12, colour=INK, space_after=4)
    add_qr(doc, GOFUNDME_URL, "Scan for our honeymoon fund", size_in=1.0)
    doc.save(OUT_DIR / "gifts.docx")


def main():
    if not CSV_PATH.exists():
        sys.exit(f"Can't find {CSV_PATH}")
    if not MENU_PATH.exists():
        sys.exit(f"Can't find {MENU_PATH}")
    OUT_DIR.mkdir(exist_ok=True)

    menu = read_menu()
    tables = build_table_cards()
    top = build_place_cards(tables)
    build_menu(menu)
    build_ring_blessing()
    build_favours()
    build_gifts()

    dishes = sum(len(g.get("items", []))
                 for b in menu["blocks"] for g in b.get("groups", []))
    print(f"Fonts: display={FONT_DISPLAY}, body={FONT_BODY}")
    print(f"Menu: {len(menu['blocks'])} blocks, {dishes} items "
          f"(read from js/menu.js)")
    print(f"Table cards: {len(tables)}")
    for name, people in tables:
        print(f"  {name:<12} {len(people):>2} — {', '.join(people)}")
    total = sum(len(p) for _, p in tables)
    print(f"Total seated people: {total}")
    print(f"Place cards (top table, one per person): {len(top)}")


if __name__ == "__main__":
    main()
