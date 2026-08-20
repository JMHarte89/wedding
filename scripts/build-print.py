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
from docx.oxml.ns import qn
from docx.shared import Inches, Mm, Pt, RGBColor

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


def _leaf_sprig(size_px=720, colour=PETROL_RGB, alpha=170):
    """A thin botanical sprig growing up and to the right.

    Drawn at 4x and downsampled so the strokes stay hairline-fine — this is
    trim, not clip art. Transparent background so coloured paper shows through.
    """
    ss = 4
    S = size_px * ss
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    col = colour + (alpha,)
    stroke = max(1, int(S * 0.006))

    # Stem: gentle arc from bottom-left to top-right.
    p0 = (0.10 * S, 0.93 * S)
    p1 = (0.32 * S, 0.42 * S)
    p2 = (0.93 * S, 0.10 * S)
    stem = _quad(p0, p1, p2)
    d.line(stem, fill=col, width=stroke, joint="curve")

    def tangent(t):
        u = 1 - t
        dx = 2 * u * (p1[0] - p0[0]) + 2 * t * (p2[0] - p1[0])
        dy = 2 * u * (p1[1] - p0[1]) + 2 * t * (p2[1] - p1[1])
        n = (dx * dx + dy * dy) ** 0.5 or 1.0
        return dx / n, dy / n

    def bez(t):
        u = 1 - t
        return (
            u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
            u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1],
        )

    # Alternating leaves, tapering towards the tip.
    for t, side, scale in ((0.20, 1, 1.00), (0.40, -1, 0.92),
                           (0.60, 1, 0.78), (0.78, -1, 0.62)):
        bx, by = bez(t)
        tx, ty = tangent(t)
        ang = math.atan2(ty, tx) + side * math.radians(42)
        length = 0.26 * S * scale
        width = 0.085 * S * scale
        ax, ay = math.cos(ang), math.sin(ang)
        px, py = -ay, ax                      # perpendicular
        tipx, tipy = bx + ax * length, by + ay * length
        midx, midy = bx + ax * length * 0.45, by + ay * length * 0.45

        # Almond outline: two arcs bulging either side of the leaf axis.
        upper = _quad((bx, by), (midx + px * width, midy + py * width), (tipx, tipy), 28)
        lower = _quad((tipx, tipy), (midx - px * width, midy - py * width), (bx, by), 28)
        d.line(upper + lower + [upper[0]], fill=col, width=stroke, joint="curve")
        # Faint midrib.
        d.line([(bx, by), (tipx, tipy)], fill=colour + (int(alpha * 0.55),),
               width=max(1, stroke // 2))

    return img.resize((size_px, size_px), Image.LANCZOS)


def leaf_variants():
    """Corner sprigs, keyed by corner. Base grows up-right from bottom-left."""
    base = _leaf_sprig()
    bl = base
    br = base.transpose(Image.FLIP_LEFT_RIGHT)
    tl = base.transpose(Image.FLIP_TOP_BOTTOM)
    tr = tl.transpose(Image.FLIP_LEFT_RIGHT)
    out = {}
    for key, im in (("tl", tl), ("tr", tr), ("bl", bl), ("br", br)):
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        buf.seek(0)
        out[key] = buf.getvalue()
    return out


LEAVES = None


def leaf_stream(corner):
    return io.BytesIO(LEAVES[corner])


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


def corner_trim(section, leaf_in=0.52):
    """Leaf sprigs in all four corners, via the header and footer.

    Header/footer keeps them out of the text flow and repeats them on every
    page — which is what we want for the multi-page table cards.
    """
    col_w = section.page_width - section.left_margin - section.right_margin

    for part, corners in ((section.header, ("tl", "tr")),
                          (section.footer, ("bl", "br"))):
        p = part.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.tab_stops.add_tab_stop(col_w, WD_TAB_ALIGNMENT.RIGHT)
        left, right = corners
        p.add_run().add_picture(leaf_stream(left), width=Inches(leaf_in))
        p.add_run().add_tab()
        p.add_run().add_picture(leaf_stream(right), width=Inches(leaf_in))


def new_doc(width_mm, height_mm, *, landscape=False, margin_mm=18,
            centre=True, leaf_in=0.52):
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
    corner_trim(sec, leaf_in=leaf_in)
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
    doc = new_doc(148, 210, landscape=True, margin_mm=14, centre=True, leaf_in=0.46)

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
    doc = new_doc(210, 297, margin_mm=28, centre=True, leaf_in=0.7)
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
    doc = new_doc(210, 297, margin_mm=28, centre=True, leaf_in=0.7)
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
    doc = new_doc(148, 210, margin_mm=16, centre=True, leaf_in=0.5)
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
         font=FONT_BODY, size=12.5, colour=INK, space_after=4)
    add_qr(doc, GOFUNDME_URL, "Scan for our honeymoon fund", size_in=1.0)
    doc.save(OUT_DIR / "gifts.docx")


def main():
    global LEAVES
    if not CSV_PATH.exists():
        sys.exit(f"Can't find {CSV_PATH}")
    LEAVES = leaf_variants()
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
