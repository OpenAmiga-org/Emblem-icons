#!/home/claude/build/emblem-venv/bin/python
"""glass_emblems_sheet.py DIR OUT.png

All emblem tiles of tools/glass_symbols.py TILES (rendered to DIR/<name>.png by glass_icons.py) at
3x and at real size (28x28), on a dark and a light backdrop. Public domain.
"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glass_sheet import bloom  # noqa: E402
from glass_symbols import TILES  # noqa: E402

DARK, LIGHT = (18, 20, 28, 255), (190, 192, 190, 255)


def main():
    d, out = sys.argv[1:3]
    names = list(TILES)
    cw = 2 * 84 + 30
    cols = 7
    rows = (len(names) + cols - 1) // cols
    rh = 84 + 40 + 24
    sheet = Image.new("RGB", (cols * cw + 20, 30 + rows * rh), (255, 255, 255))
    dr = ImageDraw.Draw(sheet)
    dr.text((10, 8), "Emblem tiles at 3x and real size, dark and light: R3 940000, G3 007711, B3 0028A5, V3 72008E",
            fill=(0, 0, 0))
    for k, n in enumerate(names):
        x0, y0 = 10 + (k % cols) * cw, 30 + (k // cols) * rh
        em = bloom(Image.open(os.path.join(d, n + ".png")).convert("RGBA"))
        small = em.resize((28, 28), Image.LANCZOS)
        for j, bg in enumerate((DARK, LIGHT)):
            t = Image.new("RGBA", (84, 84), bg)
            t.alpha_composite(em.resize((84, 84), Image.LANCZOS))
            sheet.paste(t.convert("RGB"), (x0 + j * 88, y0))
            t = Image.new("RGBA", (40, 36), bg)
            t.alpha_composite(small, (6, 4))
            sheet.paste(t.convert("RGB"), (x0 + j * 88, y0 + 86))
        sym, col = TILES[n]
        dr.text((x0, y0 + 124), f"{n[2:]}: {sym}, {col}", fill=(0, 0, 0))
    sheet.save(out)
    print("emblems ->", out)


if __name__ == "__main__":
    main()
