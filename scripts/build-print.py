#!/usr/bin/env python
"""
Build the printed materials for the day into print/*.docx.

    python scripts/build-print.py

Table cards are generated from data/guestlist.csv, so re-run this after any
change to the guest list or the seating. Nothing here is hand-keyed.

Design rules (these print onto coloured stock):
  * No shading or background fill anywhere — the paper must show through.
  * Ink only, in the site palette: ink #222d2a, petrol #2c5d63, wax #883a2d.
  * Fraunces / EB Garamond aren't installed on this machine, so we use the
    same fallbacks the site's CSS declares: Georgia for display, Garamond
    for body.
"""

import csv
import io
import math
import re
import sys
from pathlib import Path

import qrcode
from qrcode.constants import ERROR_CORRECT_Q
from PIL import Image, ImageDraw

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from docx.shared import Inches, Mm, Pt, RGBColor
from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "guestlist.csv"
OUT_DIR = ROOT / "print"

AGENDA_URL = "https://jmharte89.github.io/wedding/agenda.html"
GOFUNDME_URL = "https://gofund.me/c3356285c"

# Site palette (css/invitation.css :root)
INK = RGBColor(0x22, 0x2D, 0x2A)
PETROL = RGBColor(0x2C, 0x5D, 0x63)
WAX = RGBColor(0x88, 0x3A, 0x2D)

PETROL_RGB = (0x2C, 0x5D, 0x63)
INK_RGB = (0x22, 0x2D, 0x2A)

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


def _sprig(d, cx, cy, size, angle, col, stroke, leaves=3):
    """A small olive sprig centred on (cx, cy), lying along `angle`."""
    ax, ay = math.cos(angle), math.sin(angle)
    x0, y0 = cx - ax * size / 2, cy - ay * size / 2
    x1, y1 = cx + ax * size / 2, cy + ay * size / 2

    # Barely-there bow — the stem should read as a crisp chamfer, not a curve.
    px, py = -ay, ax
    bow = size * 0.045
    ctrl = ((x0 + x1) / 2 + px * bow, (y0 + y1) / 2 + py * bow)
    d.line(_quad((x0, y0), ctrl, (x1, y1)), fill=col, width=stroke, joint="curve")

    # Evenly spaced and symmetric about the centre, kept clear of the stem
    # ends so a leaf never collides with the rule it meets.
    spread = (0.28, 0.50, 0.72) if leaves == 3 else \
        tuple(0.26 + i * (0.48 / max(1, leaves - 1)) for i in range(leaves))
    for i, t in enumerate(spread):
        u = 1 - t
        bx = u * u * x0 + 2 * u * t * ctrl[0] + t * t * x1
        by = u * u * y0 + 2 * u * t * ctrl[1] + t * t * y1
        side = 1 if i % 2 == 0 else -1
        la = angle + side * math.radians(50)
        ll = size * 0.27
        lw = ll * 0.36
        lax, lay = math.cos(la), math.sin(la)
        lpx, lpy = -lay, lax
        tipx, tipy = bx + lax * ll, by + lay * ll
        mx, my = bx + lax * ll * 0.45, by + lay * ll * 0.45
        upper = _quad((bx, by), (mx + lpx * lw, my + lpy * lw), (tipx, tipy), 24)
        lower = _quad((tipx, tipy), (mx - lpx * lw, my - lpy * lw), (bx, by), 24)
        d.line(upper + lower + [upper[0]], fill=col, width=stroke, joint="curve")


def page_ornament(w_mm, h_mm, dpi=200, ss=2, colour=PETROL_RGB, alpha=200):
    """The full-page trim: a double rule that breaks at each corner, with an
    olive sprig bridging the break.

    Drawn once per page size as a single transparent layer, so it can be
    anchored to the page at an exact offset. That is what keeps the corners
    symmetric — the previous tab-stop approach inherited the built-in Header
    style's centre tab and pulled the right-hand art toward the middle.

    Ink only: everything outside the strokes stays fully transparent, so the
    coloured stock shows through.
    """
    mmpx = dpi / 25.4
    W, H = int(w_mm * mmpx), int(h_mm * mmpx)
    img = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    col = colour + (alpha,)
    col_soft = colour + (int(alpha * 0.72),)

    def P(v):
        return v * mmpx * ss

    # Trim scales with the short edge so A4 and A5 look like one family.
    short = min(w_mm, h_mm)
    inset = P(max(10.0, short * 0.057))
    gap = P(short * 0.088)
    sep = P(1.5)

    # Stroke widths are whole final-image pixels multiplied back up by `ss`, so
    # the downsample is an exact area average and the ink keeps its full
    # density. Letting them land on fractional widths antialiases the hairline
    # into a washed-out grey that prints badly.
    px_outer = max(2, round(0.26 * mmpx))     # ~0.74pt
    px_inner = max(1, round(0.16 * mmpx))     # ~0.45pt
    w_outer = px_outer * ss
    w_inner = px_inner * ss

    Wx, Hy = W * ss, H * ss
    for off, wt, c in ((inset, w_outer, col), (inset + sep, w_inner, col_soft)):
        l, t, r, b = off, off, Wx - off, Hy - off
        d.line([(l + gap, t), (r - gap, t)], fill=c, width=wt)
        d.line([(l + gap, b), (r - gap, b)], fill=c, width=wt)
        d.line([(l, t + gap), (l, b - gap)], fill=c, width=wt)
        d.line([(r, t + gap), (r, b - gap)], fill=c, width=wt)

    # Sprig bridging each corner break: it runs between the two rule-ends,
    # i.e. perpendicular to the page diagonal, closing the corner.
    s_stroke = w_outer                        # same weight as the rule it meets
    s_size = gap * 1.414                      # spans exactly rule-end to rule-end
    l, t, r, b = inset, inset, Wx - inset, Hy - inset
    for cx, cy, ang in (
        (l + gap / 2, t + gap / 2, math.radians(135)),
        (r - gap / 2, t + gap / 2, math.radians(45)),
        (l + gap / 2, b - gap / 2, math.radians(-135)),
        (r - gap / 2, b - gap / 2, math.radians(-45)),
    ):
        _sprig(d, cx, cy, s_size, ang, col, s_stroke)

    # BOX = exact area average. `ss` is an integer factor and the strokes are
    # integer multiples of it, so this downsamples without ringing or fading.
    out = img.resize((W, H), Image.BOX)
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    buf.seek(0)
    return buf


def qr_png(url, modules_colour=INK_RGB):
    """QR with a transparent background so the paper provides the light field."""
    qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_Q,
                       box_size=16, border=3)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, _ = px[x, y]
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
    '<wp:positionH relativeFrom="page"><wp:posOffset>0</wp:posOffset></wp:positionH>'
    '<wp:positionV relativeFrom="page"><wp:posOffset>0</wp:posOffset></wp:positionV>'
    '<wp:extent cx="{cx}" cy="{cy}"/>'
    '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
    '<wp:wrapNone/>'
    '<wp:docPr id="{did}" name="Trim {did}"/>'
    '<wp:cNvGraphicFramePr/>'
    '{graphic}'
    '</wp:anchor>'
)


def corner_trim(section, did=1):
    """Lay the page trim behind the text, pinned to the page itself.

    The image is placed as a floating anchor at page offset (0,0) at exactly
    page size, so its position cannot be perturbed by margins, paragraph
    styles or inherited tab stops. Living in the header means it repeats on
    every page — needed for the multi-page table cards — without taking part
    in the body's layout.
    """
    w_mm = section.page_width.mm
    h_mm = section.page_height.mm
    stream = page_ornament(w_mm, h_mm)

    p = section.header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = Pt(1)
    run = p.add_run()
    run.font.size = Pt(1)                 # keep the header line height at nil
    run.add_picture(stream, width=section.page_width, height=section.page_height)

    # Convert the inline drawing python-docx just made into a page anchor.
    inline = run._element.find(qn("w:drawing")).find(qn("wp:inline"))
    graphic = inline.find(qn("a:graphic"))
    extent = inline.find(qn("wp:extent"))
    xml = _ANCHOR.format(
        cx=extent.get("cx"), cy=extent.get("cy"), did=did,
        graphic=etree.tostring(graphic).decode("utf-8"),
    )
    inline.getparent().replace(inline, parse_xml(xml))


def new_doc(width_mm, height_mm, *, landscape=False, margin_mm=18,
            centre=True, did=1):
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
    corner_trim(sec, did=did)
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
    """Lay the names out in 1–3 borderless columns depending on how many."""
    n = len(names)
    cols = 1 if n <= 6 else (2 if n <= 14 else 3)
    rows = -(-n // cols)
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
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(1)
        style_run(p.add_run(name), font=FONT_BODY, size=12.5, colour=INK)
    return table


# ----------------------------------------------------------------------
# The four documents
# ----------------------------------------------------------------------

def build_table_cards():
    tables = read_tables()
    doc = new_doc(148, 210, landscape=True, margin_mm=20, centre=True, did=11)

    for idx, (name, people) in enumerate(tables):
        kicker = para(doc, "", font=FONT_DISPLAY, size=8.5, colour=PETROL,
                      space_after=4)
        if idx:
            # Break lives on the first run of the new card, not in a spacer
            # paragraph — an empty paragraph would throw off vertical centring.
            kicker.add_run().add_break(WD_BREAK.PAGE)
        style_run(kicker.add_run("You are seated at"), font=FONT_DISPLAY,
                  size=8.5, colour=PETROL, spacing=2.4, caps=True)
        para(doc, name, font=FONT_DISPLAY, size=30, colour=INK,
             bold=True, space_after=2)
        rule(doc)
        names_block(doc, people)
        add_qr(doc, AGENDA_URL, "Scan for the order of the day", size_in=0.9)

    OUT_DIR.mkdir(exist_ok=True)
    doc.save(OUT_DIR / "table-cards.docx")
    return tables


def build_ring_blessing():
    doc = new_doc(210, 297, margin_mm=32, centre=True, did=21)
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
    doc = new_doc(210, 297, margin_mm=32, centre=True, did=31)
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
    # 17mm measure rather than 20: at 20 the closing line orphans "world."
    doc = new_doc(148, 210, margin_mm=17, centre=True, did=41)
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
    OUT_DIR.mkdir(exist_ok=True)

    tables = build_table_cards()
    build_ring_blessing()
    build_favours()
    build_gifts()

    print(f"Fonts: display={FONT_DISPLAY}, body={FONT_BODY}")
    print(f"Table cards: {len(tables)}")
    for name, people in tables:
        print(f"  {name:<12} {len(people):>2} — {', '.join(people)}")
    total = sum(len(p) for _, p in tables)
    print(f"Total seated people: {total}")


if __name__ == "__main__":
    main()
