#!/home/claude/build/emblem-venv/bin/python
"""glass_variants_sheet.py OUT.png FLIP.gif ID=NORMAL.png,SELECTED.png,label ...

Compare sheet for choosing a selected state: per variant the normal and the selected image large
(256px, dark backdrop, floor reflection visible) and at real size on dark and light, and a flip GIF
of all variants switching between the two states. Public domain.
"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glass_sheet import LIGHTBLUE, bloom  # noqa: E402

DARK, LIGHT = (18, 20, 28, 255), (190, 192, 190, 255)
BIG = 256


def load(path):
    im = bloom(Image.open(path).convert("RGBA"), LIGHTBLUE)
    return im.resize((BIG, BIG), Image.LANCZOS), im.resize((64, 64), Image.LANCZOS)


def main():
    out, flip = sys.argv[1:3]
    variants = []
    for arg in sys.argv[3:]:
        vid, rest = arg.split("=", 1)
        a, b, label = rest.split(",", 2)
        variants.append((vid, label, load(a), load(b)))
    cw = 2 * BIG + 24 + 160
    W, H = 12 + cw, 30 + len(variants) * (BIG + 34)
    sheet = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    dr = ImageDraw.Draw(sheet)
    dr.text((12, 8), "Normal and selected, large on dark; real size on dark and light at the right.", fill=(0, 0, 0))
    y = 30
    for vid, label, (na, ns), (sa, ss) in variants:
        for k, im in enumerate((na, sa)):
            t = Image.new("RGBA", (BIG, BIG), DARK)
            t.alpha_composite(im)
            sheet.paste(t, (12 + k * (BIG + 8), y))
        x = 12 + 2 * (BIG + 8) + 8
        for j, bg in enumerate((DARK, LIGHT)):
            dr.rectangle((x, y + j * 84, x + 152, y + j * 84 + 80), fill=bg)
            sheet.alpha_composite(ns, (x + 8, y + j * 84 + 8))
            sheet.alpha_composite(ss, (x + 80, y + j * 84 + 8))
        dr.text((12, y + BIG + 6), f"{vid} {label}: normal, selected", fill=(0, 0, 0))
        y += BIG + 34
    sheet.convert("RGB").save(out)
    print("sheet ->", out)

    frames = []
    for state in (0, 1):
        row = Image.new("RGBA", (8 + len(variants) * (BIG + 8), BIG + 40), (255, 255, 255, 255))
        rd = ImageDraw.Draw(row)
        for k, (vid, label, n, s) in enumerate(variants):
            big, small = (n, s)[state]
            t = Image.new("RGBA", (BIG, BIG), DARK)
            t.alpha_composite(big)
            row.paste(t, (8 + k * (BIG + 8), 8))
            rd.text((8 + k * (BIG + 8), BIG + 16), f"{vid} {label}", fill=(0, 0, 0))
        frames.append(row.convert("RGB"))
    frames[0].save(flip, save_all=True, append_images=frames[1:], duration=[900, 900], loop=0)
    print("flip ->", flip)


if __name__ == "__main__":
    main()
