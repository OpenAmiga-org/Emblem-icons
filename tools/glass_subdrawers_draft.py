#!/home/claude/build/emblem-venv/bin/python
"""glass_subdrawers_draft.py OUT.png

A flat 2D draft of the sub-drawer emblems (tools/glass_symbols.py SUBDRAWERS): each in its parent
drawer's colour, grouped by parent, large and at tile size (28 px) on dark. For agreeing the symbols
before the glass tiles are rendered. Public domain.
"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glass_symbols as g  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYM = os.path.join(ROOT, "build", "glass", "symbols")


def main():
    out = sys.argv[1]
    os.makedirs(SYM, exist_ok=True)
    for n in sorted({sym for _, _, _, sym in g.SUBDRAWERS}):
        c = g.G(64)
        g.SYMBOLS[n](c)
        c.im.save(os.path.join(SYM, n + ".png"))
    parents = []
    for p, *_ in g.SUBDRAWERS:
        if p not in parents:
            parents.append(p)
    cell, small = 112, 28
    rows = [(p, [(n, t, sym) for pp, n, t, sym in g.SUBDRAWERS if pp == p]) for p in parents]
    W, H = 14 + 9 * 124, 40 + len(rows) * (20 + cell + 22 + 40 + 20)
    sheet = Image.new("RGB", (W, H), (236, 236, 236))
    d = ImageDraw.Draw(sheet)
    d.text((14, 10), "Sub-drawer emblems, 2D draft: the parent drawer's colour, the symbol after the OS 4.1 icon. "
                     "Large, then tile size (28 px) on dark.", fill=(0, 0, 0))
    y = 36
    for p, items in rows:
        col = tuple(int(g.PARENT_COLOUR[p][i:i + 2], 16) for i in (0, 2, 4))
        d.text((14, y), f"{p}  (colour {g.PARENT_COLOUR[p]})", fill=(120, 0, 0))
        y += 20
        for k, (n, t, sym) in enumerate(items):
            x = 14 + k * 124
            tile = Image.new("RGBA", (cell, cell), (0, 0, 0, 0))
            ImageDraw.Draw(tile).rounded_rectangle((2, 2, cell - 3, cell - 3), 16, fill=col + (255,),
                                                   outline=tuple(min(255, v + 90) for v in col) + (255,), width=3)
            s = Image.open(os.path.join(SYM, sym + ".png")).resize((int(cell * 0.72),) * 2, Image.LANCZOS)
            tile.alpha_composite(s, ((cell - s.size[0]) // 2, (cell - s.size[1]) // 2))
            sheet.paste(tile, (x, y), tile)
            d.text((x, y + cell + 4), n, fill=(0, 0, 0))
            d.rectangle((x, y + cell + 22, x + 44, y + cell + 58), fill=(18, 20, 28))
            sm = tile.resize((small, small), Image.LANCZOS)
            sheet.paste(sm, (x + 8, y + cell + 26), sm)
        y += cell + 22 + 40 + 20
    sheet.save(out)
    print("draft ->", out)


if __name__ == "__main__":
    main()
