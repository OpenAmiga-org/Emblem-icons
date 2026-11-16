#!/home/claude/build/emblem-venv/bin/python
"""drawer_probe_sheet.py DIR OUT.png

Bloom, scaling and the probe sheet for tools/blender/drawer_probe.py renders
(DIR/<state>_<variant>.png, 512x512 transparent). Bloom: the bright pixels
(emissive edges, hot highlights) glow light blue around themselves. Each
icon is scaled to 64x64 (real size) and 128x128 (2x), and the 64x64 icons are
saved as DIR/<state>_<variant>_64.png. Public domain.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

LIGHTBLUE = np.array([148, 194, 240], np.float32)
VARIANTS = [("blend", "wire back, glass, solid front"),
            ("glass", "all glenz glass"), ("solid", "all black lacquer")]
STATES = ["closed", "open"]


def bloom(im):
    a = np.asarray(im, np.float32) / 255.0
    rgb, al = a[..., :3], a[..., 3:4]
    lum = (rgb * [0.3, 0.55, 0.15]).sum(-1, keepdims=True)
    src = np.clip((lum - 0.55) / 0.45, 0, 1) * al          # bright parts only
    glow = np.zeros(a.shape[:2], np.float32)
    s = Image.fromarray((src[..., 0] * 255).astype(np.uint8), "L")
    for r, w in ((3, 0.6), (9, 0.5), (22, 0.35)):
        glow += np.asarray(s.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0 * w
    glow = np.clip(glow, 0, 1)[..., None]
    # glow adds light blue light, and makes those pixels visible on any backdrop
    out_rgb = rgb * al + LIGHTBLUE / 255.0 * glow * (1 - al * 0.5)
    out_a = np.clip(al + glow * 0.85, 0, 1)
    out_rgb = np.where(out_a > 0, out_rgb / np.maximum(out_a, 1e-6), 0)
    out = np.concatenate([np.clip(out_rgb, 0, 1), out_a], -1)
    return Image.fromarray((out * 255).astype(np.uint8), "RGBA")


def main():
    d, out = sys.argv[1:3]
    icons = {}
    for v, _ in VARIANTS:
        for st in STATES:
            f = os.path.join(d, f"{st}_{v}.png")
            if os.path.exists(f):
                big = bloom(Image.open(f).convert("RGBA"))
                icons[(st, v)] = (big.resize((64, 64), Image.LANCZOS), big.resize((128, 128), Image.LANCZOS))
                icons[(st, v)][0].save(os.path.join(d, f"{st}_{v}_64.png"))
    DARK, LIGHT = (18, 20, 28, 255), (190, 192, 190, 255)
    cw = 2 * 128 + 3 * 12
    W = 12 + len(VARIANTS) * (cw + 12)
    rowh = 128 + 24
    H = 40 + 2 * rowh + 2 * 96 + 20
    sheet = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    dr = ImageDraw.Draw(sheet)
    dr.text((12, 8), "Drawer probe D01-D06: closed and open (selected) at 2x on dark and light; real size below",
            fill=(0, 0, 0))
    for k, (v, desc) in enumerate(VARIANTS):
        x0 = 12 + k * (cw + 12)
        dr.text((x0, 24), f"D{k * 2 + 1:02d}/D{k * 2 + 2:02d}  {v}: {desc}", fill=(0, 0, 0))
        for r, bgc in enumerate((DARK, LIGHT)):
            y = 40 + r * rowh
            for j, st in enumerate(STATES):
                if (st, v) not in icons:
                    continue
                tile = Image.new("RGBA", (128, 128), bgc)
                tile.alpha_composite(icons[(st, v)][1])
                sheet.paste(tile, (x0 + 12 + j * 140, y))
    # real size strips
    y = 40 + 2 * rowh + 6
    for bgc, label in ((DARK, "real size, dark"), (LIGHT, "real size, light")):
        dr.rectangle((0, y, W, y + 90), fill=bgc)
        dr.text((12, y + 4), label, fill=(220, 220, 220) if bgc == DARK else (0, 0, 0))
        x = 140
        for v, _ in VARIANTS:
            for st in STATES:
                if (st, v) in icons:
                    sheet.alpha_composite(icons[(st, v)][0], (x, y + 14))
                    x += 76
            x += 30
        y += 96
    sheet.convert("RGB").save(out)
    print("sheet ->", out)


if __name__ == "__main__":
    main()
