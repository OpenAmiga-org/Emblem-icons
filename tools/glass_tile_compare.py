#!/home/claude/build/emblem-venv/bin/python
"""glass_tile_compare.py OUT.png LABEL=FILE...

Compares emblem tile renders (tools/blender/glass_icons.py gem ...): each tile at 4x on a dark and a
light backdrop, on the glass drawer at 2x (composed by the Emblem engine, lower right) and at real
size. Needs build/glass/icons/drawer.png (tools/glass_drawers_sheet.py). Public domain.
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glass_sheet import bloom  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENDER = os.path.join(ROOT, "build", "host", "render")
DARK, LIGHT = (18, 20, 28, 255), (190, 192, 190, 255)


def main():
    out = sys.argv[1]
    items = [a.split("=", 1) for a in sys.argv[2:]]
    idir = os.path.join(os.path.dirname(os.path.abspath(out)), "cmp_icons")
    os.makedirs(idir, exist_ok=True)
    Image.open(os.path.join(ROOT, "build", "glass", "icons", "drawer.png")).save(os.path.join(idir, "drawer.png"))
    prefs = os.path.join(idir, "p.prefs")
    open(prefs, "w").write("EMBLEMMETHOD=SHADOW\nSHADOWOFFSET=2,2\nSHADOWBLUR=2\nSHADOWOPACITY=55\n")
    colw = 270
    sheet = Image.new("RGB", (len(items) * colw + 20, 412), (255, 255, 255))
    dr = ImageDraw.Draw(sheet)
    for k, (label, f) in enumerate(items):
        x0 = 10 + k * colw
        dr.text((x0, 6), label, fill=(0, 0, 0))
        big = bloom(Image.open(f).convert("RGBA"))
        big.resize((28, 28), Image.LANCZOS).save(os.path.join(idir, f"Em{k}.png"))
        for j, bg in enumerate((DARK, LIGHT)):
            t = Image.new("RGBA", (112, 112), bg)
            t.alpha_composite(big.resize((112, 112), Image.LANCZOS))
            sheet.paste(t.convert("RGB"), (x0 + j * 120, 24))
        pre = os.path.join(idir, "c")
        subprocess.run([RENDER, "--dir", idir, "--prefs", prefs, "--out", pre, "IMAGE=drawer",
                        f"EMBLEM=Em{k},0,0,36,35"], check=True, capture_output=True)
        ic = Image.open(pre + "_1.png").convert("RGBA")
        for j, bg in enumerate((DARK, LIGHT)):
            t = Image.new("RGBA", (112, 112), bg)
            t.alpha_composite(ic.resize((112, 112), Image.LANCZOS))
            sheet.paste(t.convert("RGB"), (x0 + j * 120, 144))
        for j, bg in enumerate((DARK, LIGHT)):
            t = Image.new("RGBA", (112, 96), bg)
            t.alpha_composite(ic, (24, 16))
            sheet.paste(t.convert("RGB"), (x0 + j * 120, 264))
        dr.text((x0, 366), "rows: tile 4x | on the drawer 2x |", fill=(90, 90, 90))
        dr.text((x0, 380), "real size (dark, light)", fill=(90, 90, 90))
    sheet.save(out)
    print("compare ->", out)


if __name__ == "__main__":
    main()
