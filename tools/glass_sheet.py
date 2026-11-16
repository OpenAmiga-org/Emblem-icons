#!/home/claude/build/emblem-venv/bin/python
"""glass_sheet.py DIR OUT.png

Turns the renders of tools/blender/glass_icons.py (DIR/<name>.png) into icons and a preview
sheet: bloom (bright parts glow: light blue for the base images, their own colour for the
emblems), scaling (base images 64x64, emblems 28x28, written as DIR/icons/<name>.png), the
emblem icons composed with the Emblem engine (build/host/render), and the sheet G01-G10 at 2x
on a dark and a light backdrop, with real size strips. Public domain.
"""
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENDER = os.path.join(ROOT, "build", "host", "render")
LIGHTBLUE = np.array([148, 194, 240], np.float32) / 255.0

BASES = ["drawer", "drawer_open", "file", "device", "archive", "prefs", "tool"]
EMBLEMS = ["EmMusic", "EmGames", "EmPicture", "EmStar"]
EMBLEM_NAMES = ["E01 music, deep red", "E02 games, deep green", "E03 picture, deep blue", "E04 star, yellow"]
AT = "0,0,36,35"            # emblems at their own size (28x28), lower right
ICONS = [
    ("G01", "drawer", "drawer", []),
    ("G02", "drawer, selected (open)", "drawer_open", []),
    ("G03", "drawer + music emblem", "drawer", ["EMBLEM=EmMusic," + AT]),
    ("G04", "drawer + games emblem", "drawer", ["EMBLEM=EmGames," + AT]),
    ("G05", "file", "file", []),
    ("G06", "file + picture emblem", "file", ["EMBLEM=EmPicture," + AT]),
    ("G07", "device (disk)", "device", []),
    ("G08", "archive", "archive", []),
    ("G09", "preferences", "prefs", []),
    ("G10", "tool (program)", "tool", []),
]
PREFS = "EMBLEMMETHOD=SHADOW\nSHADOWOFFSET=2,2\nSHADOWBLUR=2\nSHADOWOPACITY=55\n"


def bloom(im, tint=None, threshold=0.5):
    """bright pixels glow; tint None = in their own colour. threshold: the brightness (0-1) from
    which pixels start to glow (higher for icons with large light glass areas)"""
    a = np.asarray(im, np.float32) / 255.0
    rgb, al = a[..., :3], a[..., 3:4]
    lum = (rgb * [0.3, 0.55, 0.15]).sum(-1, keepdims=True)
    src = np.clip((lum - threshold) / (1 - threshold), 0, 1) * al
    w = src[..., 0]
    glow = np.zeros(a.shape[:2] + (3,), np.float32)
    amount = np.zeros(a.shape[:2], np.float32)
    colour = rgb * src if tint is None else np.ones_like(rgb) * tint * src
    for r, k in ((3, 0.6), (9, 0.5), (22, 0.35)):
        amount += np.asarray(Image.fromarray((w * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(r)),
                             np.float32) / 255.0 * k
        for ch in range(3):
            glow[..., ch] += np.asarray(Image.fromarray((colour[..., ch] * 255).astype(np.uint8), "L")
                                        .filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0 * k
    amount = np.clip(amount, 0, 1)[..., None]
    gcol = np.where(amount > 1e-4, glow / np.maximum(amount, 1e-4), 0)
    gcol = np.clip(gcol * 1.15, 0, 1)
    out_rgb = rgb * al + gcol * amount * (1 - al * 0.5)
    out_a = np.clip(al + amount * 0.85, 0, 1)
    out_rgb = np.where(out_a > 0, out_rgb / np.maximum(out_a, 1e-6), 0)
    return Image.fromarray((np.concatenate([np.clip(out_rgb, 0, 1), out_a], -1) * 255).astype(np.uint8), "RGBA")


def main():
    d, out = sys.argv[1:3]
    idir = os.path.join(d, "icons")
    os.makedirs(idir, exist_ok=True)
    for b in BASES:
        bloom(Image.open(os.path.join(d, b + ".png")).convert("RGBA"), LIGHTBLUE).resize((64, 64), Image.LANCZOS) \
            .save(os.path.join(idir, b + ".png"))
    for e in EMBLEMS:
        bloom(Image.open(os.path.join(d, e + ".png")).convert("RGBA")).resize((28, 28), Image.LANCZOS) \
            .save(os.path.join(idir, e + ".png"))
    prefs = os.path.join(idir, "emblem.prefs")
    open(prefs, "w").write(PREFS)
    icons = []
    for iid, cap, base, tts in ICONS:
        if not tts:
            im = Image.open(os.path.join(idir, base + ".png")).convert("RGBA")
        else:
            pre = os.path.join(idir, "_r")
            r = subprocess.run([RENDER, "--dir", idir, "--prefs", prefs, "--out", pre, "IMAGE=" + base] + tts,
                               capture_output=True, text=True).stdout
            assert "composed=1" in r, r
            im = Image.open(pre + "_1.png").convert("RGBA")
            os.remove(pre + "_1.png")
        im.save(os.path.join(idir, f"{iid}.png"))
        icons.append((iid, cap, im))

    DARK, LIGHT = (18, 20, 28, 255), (190, 192, 190, 255)
    cols, cell = 5, 128
    w, h = cell + 22, cell + 26
    top = 30
    W = 12 + cols * w
    H = top + 2 * (2 * h + 10) + 2 * 92 + 10 + 28 + 84 + 26
    sheet = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    dr = ImageDraw.Draw(sheet)
    dr.text((12, 8), "Glass set preview G01-G10 at 2x: on a dark Workbench backdrop (top), on the light one "
                     "(middle); real size below. Emblems composed by emblem.iconmodule's engine.", fill=(0, 0, 0))
    y0 = top
    for bgc in (DARK, LIGHT):
        for k, (iid, cap, im) in enumerate(icons):
            x, y = 12 + (k % cols) * w, y0 + (k // cols) * h
            tile = Image.new("RGBA", (cell, cell), bgc)
            tile.alpha_composite(im.resize((cell, cell), Image.LANCZOS))
            sheet.paste(tile, (x, y))
            dr.text((x, y + cell + 4), f"{iid}  {cap}", fill=(0, 0, 0))
        y0 += 2 * h + 10
    for bgc, label in ((DARK, "real size, dark"), (LIGHT, "real size, light")):
        dr.rectangle((0, y0, W, y0 + 88), fill=bgc)
        dr.text((12, y0 + 4), label, fill=(220, 220, 220) if bgc == DARK else (0, 0, 0))
        for k, (_, _, im) in enumerate(icons):
            sheet.alpha_composite(im, (14 + k * 74, y0 + 18))
        y0 += 92
    # the emblem tiles themselves at 3x
    y0 += 10
    dr.text((12, y0), "Emblem tiles at 3x (pure deep RGB colours), dark and light backdrop:", fill=(0, 0, 0))
    y0 += 16
    for k, (e, name) in enumerate(zip(EMBLEMS, EMBLEM_NAMES)):
        em = Image.open(os.path.join(idir, e + ".png")).convert("RGBA").resize((84, 84), Image.LANCZOS)
        for j, bgc in enumerate((DARK, LIGHT)):
            tile = Image.new("RGBA", (84, 84), bgc)
            tile.alpha_composite(em)
            sheet.paste(tile, (12 + k * 190 + j * 88, y0))
        dr.text((12 + k * 190, y0 + 88), name, fill=(0, 0, 0))
    sheet.convert("RGB").save(out)
    print("sheet ->", out)


if __name__ == "__main__":
    main()
