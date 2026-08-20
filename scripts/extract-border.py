#!/usr/bin/env python
"""
Turn print/sunflower.jpg into a reusable border layer.

    python scripts/extract-border.py

The source is a flattened JPEG: watercolour border + composited text + QR code
on an opaque white field. Two things have to happen before it can be reused:

  1. Remove the composited text and QR. They are dark and almost completely
     desaturated (measured mean saturation 8) whereas the artwork is strongly
     saturated (sunflower centres measure 116), so saturation separates them
     cleanly where a brightness threshold would not.

  2. Key the white field to transparent. These documents print onto coloured
     stock and the standing rule is that the paper shows through — an opaque
     white page image would defeat that entirely. A soft ramp keeps the pale
     watercolour washes as genuine semi-transparent tints rather than
     clipping them away.

Writes assets/border-landscape.png and assets/border-portrait.png.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "print" / "sunflower.jpg"
OUT_DIR = ROOT / "assets"

# White-key ramp, measured against the source: fully opaque at or below
# WHITE_LO, fully transparent at or above WHITE_HI, linear between.
WHITE_LO, WHITE_HI = 200, 250

# Text/QR: dark and desaturated. Generous on saturation, tight on brightness.
TEXT_SAT_MAX = 30
TEXT_VAL_MAX = 175


def extract():
    if not SRC.exists():
        sys.exit(f"Can't find {SRC}")

    rgb = np.array(Image.open(SRC).convert("RGB")).astype(np.int16)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mn = rgb.min(axis=2)
    mx = rgb.max(axis=2)
    sat = mx - mn

    # --- 1. white key -------------------------------------------------
    alpha = np.clip((WHITE_HI - mn) * 255.0 / (WHITE_HI - WHITE_LO), 0, 255)

    # --- 2. drop the composited text and QR ---------------------------
    # The site's ink is a cool dark teal (blue >= red); every dark tone in the
    # artwork is warm — foliage greens and sunflower browns all run red > blue.
    # That one comparison spares the leaf outlines, which a saturation test
    # alone was biting notches out of.
    dark_neutral = (sat < TEXT_SAT_MAX) & (mx < TEXT_VAL_MAX) & (b >= r - 3)

    # Colour alone isn't enough: the deepest shadow inside a sunflower centre
    # is also dark and only weakly saturated, and keying on colour alone
    # punched holes through the middle of three blooms.
    #
    # What actually separates them is context. A glyph or QR module sits in a
    # field of white; a sunflower centre is ringed by petals. So require the
    # neighbourhood to be mostly white before deleting anything.
    near_white = (mn > 236) & (sat < 18)
    local_white = np.array(
        Image.fromarray((near_white * 255).astype(np.uint8))
        .filter(ImageFilter.BoxBlur(24))
    ) / 255.0

    # The whiteness test suits thin glyphs but fails in the middle of a QR
    # code, which is a dense black block whose neighbourhood is mostly black —
    # that left a grey ghost of the QR floating in the centre. Very dark and
    # very neutral is unambiguous print ink (no watercolour tone here comes
    # close: the deepest sunflower shadow still measures ~55 saturation), so
    # remove that regardless of context.
    definite_ink = (sat < 14) & (mx < 100)

    text = definite_ink | (dark_neutral & (local_white > 0.42))

    # Grow the mask slightly to swallow JPEG ringing around the glyph edges,
    # which is paler than the glyph itself and would survive as grey fringing.
    grown = np.array(
        Image.fromarray((text * 255).astype(np.uint8))
        .filter(ImageFilter.MaxFilter(9))
    ) > 127
    alpha[grown] = 0

    # --- 3. sweep up specks -------------------------------------------
    # A little antialiased debris from the removed text survives as isolated
    # flecks. Genuine artwork in the middle of the page is always part of the
    # garland, so anything small AND unconnected to it is safe to drop.
    try:
        from scipy import ndimage
        solid = alpha > 40
        labels, n = ndimage.label(solid)
        if n:
            sizes = ndimage.sum(solid, labels, range(1, n + 1))
            tiny = np.isin(labels, np.nonzero(sizes < 400)[0] + 1)
            alpha[tiny] = 0
            print(f"specks removed: {int(tiny.sum())} px "
                  f"in {int((sizes < 400).sum())} fragments")
    except ImportError:
        print("scipy not available — skipping speck cleanup")

    out = np.dstack([rgb.astype(np.uint8), alpha.astype(np.uint8)])
    land = Image.fromarray(out, "RGBA")

    OUT_DIR.mkdir(exist_ok=True)
    land.save(OUT_DIR / "border-landscape.png")
    # A-series pages are all the same shape, so one rotation serves A4 and A5
    # portrait alike. Rotating (rather than stretching) keeps the sunflowers
    # circular.
    land.transpose(Image.ROTATE_90).save(OUT_DIR / "border-portrait.png")

    kept = (alpha > 8).mean() * 100
    print(f"source      : {land.width} x {land.height}")
    print(f"text removed: {grown.mean()*100:.1f}% of pixels")
    print(f"ink kept    : {kept:.1f}% of pixels")
    print(f"wrote {OUT_DIR / 'border-landscape.png'}")
    print(f"wrote {OUT_DIR / 'border-portrait.png'}")


if __name__ == "__main__":
    extract()
