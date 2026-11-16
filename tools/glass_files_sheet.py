#!/home/claude/build/emblem-venv/bin/python
"""glass_files_sheet.py DIR OUT.png [FLIP.gif]

Group 3 (files by type, through the def_ icons) of the glass set: the glass page with a type
emblem, and the glass crate with a format-letters tile, normal and selected (the page split in two,
its front half opened; the crate's lid opened), emblems lower right, composed by the Emblem engine
(build/host/render). Uses the renders in DIR: file.png, file_open.png, archive.png,
archive_open.png (tools/blender/glass_icons.py) and the Em*.png tiles. Public domain.
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glass_sheet import LIGHTBLUE, bloom  # noqa: E402
from glass_symbols import ARCHIVES  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENDER = os.path.join(ROOT, "build", "host", "render")
PREFS = "EMBLEMMETHOD=SHADOW\nSHADOWOFFSET=2,2\nSHADOWBLUR=2\nSHADOWOPACITY=55\n"
AT = "0,0,36,35"
DARK, LIGHT = (18, 20, 28, 255), (190, 192, 190, 255)
PER_ROW = 7

# id, label (the def_ icons it stands for), emblem
TYPES = [
    ("FT01", "text, project", None),
    ("FT02", "pdf, ps, eps", "EmDocument"),
    ("FT03", "html, http, ftp", "EmInternet"),
    ("FT04", "guide", "EmDocs"),
    ("FT05", "picture", "EmPicture"),
    ("FT06", "sound", "EmMusic"),
    ("FT07", "video", "EmVideo"),
    ("FT08", "script, code", "EmCode"),
    ("FT09", "font", "EmFont"),
    ("FT10", "library, system", "EmSystem"),
    ("FT11", "device, handler", "EmDevs"),
    ("FT12", "mui", "EmMUI"),
    ("FT13", "prefs file", "EmPrefs"),
    ("FT14", "disk image", "EmStorage"),
]
ARCS = [("AR01", "archive", None)] + [(f"AR{k + 2:02d}", a, "Em" + a) for k, a in enumerate(ARCHIVES)]
SECTIONS = [("File types: the glass page + a type emblem", "file", TYPES),
            ("Archives: the glass crate + the format letters", "archive", ARCS)]
FLIP = ["FT05", "FT08", "AR02", "AR04"]


def main():
    d, out = sys.argv[1:3]
    flip = sys.argv[3] if len(sys.argv) > 3 else None
    idir = os.path.join(d, "icons")
    os.makedirs(idir, exist_ok=True)
    for base in ("file", "archive"):
        for n in (base, base + "_open"):
            bloom(Image.open(os.path.join(d, n + ".png")).convert("RGBA"), LIGHTBLUE).resize((64, 64), Image.LANCZOS) \
                .save(os.path.join(idir, n + ".png"))
    for _, _, items in SECTIONS:
        for _, _, em in items:
            if em:
                bloom(Image.open(os.path.join(d, em + ".png")).convert("RGBA")).resize((28, 28), Image.LANCZOS) \
                    .save(os.path.join(idir, em + ".png"))
    prefs = os.path.join(idir, "emblem.prefs")
    open(prefs, "w").write(PREFS)

    composed = {}
    for _, base, items in SECTIONS:
        for iid, label, em in items:
            tts = [f"IMAGE={base}", f"IMAGESELECTED={base}_open"]
            if em:
                tts += [f"EMBLEM={em},{AT}", f"EMBLEMSELECTED={em},{AT}"]
            pre = os.path.join(idir, "_r")
            r = subprocess.run([RENDER, "--dir", idir, "--prefs", prefs, "--out", pre] + tts,
                               capture_output=True, text=True).stdout
            assert "composed=1" in r, r
            composed[iid] = (Image.open(pre + "_1.png").convert("RGBA"), Image.open(pre + "_2.png").convert("RGBA"))

    cw, cell = 150, 128
    W = 12 + PER_ROW * cw
    blocks = []                         # (title, [(id, label, image)])
    for title, _, items in SECTIONS:
        for state, sub in ((0, ""), (1, ", selected")):
            for k in range(0, len(items), PER_ROW):
                chunk = items[k:k + PER_ROW]
                blocks.append((title + sub if k == 0 else None,
                               [(iid, f"{iid} {label}", composed[iid][state]) for iid, label, _ in chunk]))
    H = 30 + sum((18 if t else 0) + 2 * (cell + 22) + 2 * 84 + 14 for t, _ in blocks)
    sheet = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    dr = ImageDraw.Draw(sheet)
    dr.text((12, 8), "Group 3, files by type: 2x on dark and light, then real size on dark and light.", fill=(0, 0, 0))
    y = 30
    for title, row in blocks:
        if title:
            dr.text((12, y), title, fill=(120, 0, 0))
            y += 18
        for bg in (DARK, LIGHT):
            for k, (_, label, im) in enumerate(row):
                x = 12 + k * cw
                t = Image.new("RGBA", (cell, cell), bg)
                t.alpha_composite(im.resize((cell, cell), Image.LANCZOS))
                sheet.paste(t, (x, y))
                dr.text((x, y + cell + 4), label, fill=(0, 0, 0))
            y += cell + 22
        for bg in (DARK, LIGHT):
            dr.rectangle((0, y, W, y + 80), fill=bg)
            for k, (_, label, im) in enumerate(row):
                sheet.alpha_composite(im, (12 + k * cw + 32, y + 8))
            y += 84
        y += 14
    sheet.convert("RGB").save(out)
    print("sheet ->", out)

    if flip:
        frames = []
        for state in (0, 1):
            row = Image.new("RGBA", (len(FLIP) * (cell + 8 + 72) + 8, cell + 16), (255, 255, 255, 255))
            x = 8
            for iid in FLIP:
                im = composed[iid][state]
                t = Image.new("RGBA", (cell, cell), DARK)
                t.alpha_composite(im.resize((cell, cell), Image.LANCZOS))
                row.paste(t, (x, 8))
                t = Image.new("RGBA", (64, 64), LIGHT)
                t.alpha_composite(im)
                row.paste(t, (x + cell + 4, 8 + 32))
                x += cell + 8 + 72
            frames.append(row.convert("RGB"))
        frames[0].save(flip, save_all=True, append_images=frames[1:], duration=[900, 900], loop=0)
        print("flip ->", flip)


if __name__ == "__main__":
    main()
