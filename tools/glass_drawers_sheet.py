#!/home/claude/build/emblem-venv/bin/python
"""glass_drawers_sheet.py DIR OUT.png

Group 1 (drawers) of the glass set: def_drawer and the SYS: drawers with their
emblems lower right (the user's choice), normal and selected (open). Uses the
renders in DIR (drawer.png, drawer_open.png, Em*.png from
tools/blender/glass_icons.py); everything is composed by the Emblem engine
(build/host/render).
Public domain.
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glass_sheet import LIGHTBLUE, bloom  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENDER = os.path.join(ROOT, "build", "host", "render")
PREFS = "EMBLEMMETHOD=SHADOW\nSHADOWOFFSET=2,2\nSHADOWBLUR=2\nSHADOWOPACITY=55\n"

DRAWERS = [("def_drawer", None), ("Prefs", "EmPrefs"), ("Utilities", "EmUtilities"), ("System", "EmSystem"),
           ("Storage", "EmStorage"), ("WBStartup", "EmStartup"), ("Devs", "EmDevs"), ("Internet", "EmInternet"),
           ("Emulation", "EmEmulation"), ("Documentation", "EmDocs"), ("MUI", "EmMUI")]
PLACES = [("lower right", "0,0,36,35"), ("top right", "0,0,36,1")]
DARK, LIGHT = (18, 20, 28, 255), (190, 192, 190, 255)


def compose(idir, prefs, tts, own=None):
    pre = os.path.join(idir, "_r")
    args = [RENDER, "--dir", idir, "--prefs", prefs, "--out", pre]
    if own:
        args += ["--own1", own]
    r = subprocess.run(args + tts, capture_output=True, text=True).stdout
    assert "composed=1" in r, r
    im = Image.open(pre + "_1.png").convert("RGBA")
    os.remove(pre + "_1.png")
    return im


def tile(im, bg, size=128):
    t = Image.new("RGBA", (size, size), bg)
    t.alpha_composite(im.resize((size, size), Image.LANCZOS))
    return t


def main():
    d, out = sys.argv[1:3]
    idir = os.path.join(d, "icons")
    os.makedirs(idir, exist_ok=True)
    for b in ("drawer", "drawer_open"):
        bloom(Image.open(os.path.join(d, b + ".png")).convert("RGBA"), LIGHTBLUE).resize((64, 64), Image.LANCZOS) \
            .save(os.path.join(idir, b + ".png"))
    for _, em in DRAWERS:
        if em:
            bloom(Image.open(os.path.join(d, em + ".png")).convert("RGBA")).resize((28, 28), Image.LANCZOS) \
                .save(os.path.join(idir, em + ".png"))
    prefs = os.path.join(idir, "emblem.prefs")
    open(prefs, "w").write(PREFS)
    base = Image.open(os.path.join(idir, "drawer.png")).convert("RGBA")

    rows = []      # (title, [(label, image)])
    at = PLACES[0][1]                       # lower right (chosen by the user, 2026-11-16)
    normal, selected = [], []
    for k, (name, em) in enumerate(DRAWERS):
        tts = ["IMAGE=drawer", "IMAGESELECTED=drawer_open"]
        if em:
            tts += [f"EMBLEM={em},{at}", f"EMBLEMSELECTED={em},{at}"]
        pre = os.path.join(idir, "_r")
        r = subprocess.run([RENDER, "--dir", idir, "--prefs", prefs, "--out", pre] + tts, capture_output=True, text=True).stdout
        assert "composed=1" in r, r
        normal.append((f"DR{k + 1:02d} {name}", Image.open(pre + "_1.png").convert("RGBA")))
        selected.append((f"DR{k + 1:02d} {name}, selected", Image.open(pre + "_2.png").convert("RGBA")))
    rows.append(("Drawers, emblem lower right", normal))
    rows.append(("Selected (open)", selected))
    cw, cell = 150, 128
    W = 12 + 11 * cw
    H = 34
    for title, items in rows:
        H += 18 + 2 * (cell + 22) + 2 * 84 + 14
    sheet = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    dr = ImageDraw.Draw(sheet)
    dr.text((12, 8), "Group 1, drawers: 2x on dark and light, then real size on dark and light. "
                     "Emblems: see-through coloured glass tiles with glowing edges.", fill=(0, 0, 0))
    y = 30
    for title, items in rows:
        dr.text((12, y), title, fill=(120, 0, 0))
        y += 18
        for bg in (DARK, LIGHT):
            for k, (label, im) in enumerate(items):
                x = 12 + k * cw
                sheet.paste(tile(im, bg), (x, y))
                dr.text((x, y + cell + 4), label, fill=(0, 0, 0))
            y += cell + 22
        for bg in (DARK, LIGHT):
            dr.rectangle((0, y, W, y + 80), fill=bg)
            for k, (label, im) in enumerate(items):
                sheet.alpha_composite(im, (12 + k * cw + 32, y + 8))
            y += 84
        y += 14
    sheet.convert("RGB").save(out)
    print("sheet ->", out)


if __name__ == "__main__":
    main()
