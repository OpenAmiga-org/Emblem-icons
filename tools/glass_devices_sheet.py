#!/home/claude/build/emblem-venv/bin/python
"""glass_devices_sheet.py DIR OUT.png [FLIP.gif]

Group 2 (disks and devices) of the glass set, normal and selected (lit from
inside; the trashcan: full), emblems lower right, composed by the Emblem engine
(build/host/render). Uses the renders in DIR (<name>.png and <name>_lit.png from
tools/blender/glass_icons.py, Em*.png tiles). FLIP.gif: a few of them switching
between normal and selected. Public domain.
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
AT = "0,0,36,35"
BLOOM = 0.86          # only the bright parts glow (large light glass areas would wash out)
DARK, LIGHT = (18, 20, 28, 255), (190, 192, 190, 255)

# id, label, normal image, selected image, emblem
ITEMS = [
    ("DV01", "hard disk", "device", "device_lit", None),
    ("DV02", "System", "device", "device_lit", "EmSystem"),
    ("DV03", "Work", "device", "device_lit", "EmHome"),
    ("DV04", "floppy", "floppy", "floppy_lit", None),
    ("DV05", "optical", "disc", "disc_lit", None),
    ("DV06", "RAM", "ram", "ram_lit", None),
    ("DV07", "removable", "usb", "usb_lit", None),
    ("DV08", "network", "network", "network_lit", None),
    ("DV09", "bad disk", "device", "device_lit", "EmWarning"),
    ("DV10", "trashcan", "trashcan", "trashcan_full", None),
]
FLIP = ["DV02", "DV04", "DV05", "DV10"]


def main():
    d, out = sys.argv[1:3]
    flip = sys.argv[3] if len(sys.argv) > 3 else None
    idir = os.path.join(d, "icons")
    os.makedirs(idir, exist_ok=True)
    for _, _, a, b, em in ITEMS:
        for n in (a, b):
            bloom(Image.open(os.path.join(d, n + ".png")).convert("RGBA"), LIGHTBLUE, BLOOM).resize((64, 64), Image.LANCZOS) \
                .save(os.path.join(idir, n + ".png"))
        if em:
            bloom(Image.open(os.path.join(d, em + ".png")).convert("RGBA")).resize((28, 28), Image.LANCZOS) \
                .save(os.path.join(idir, em + ".png"))
    prefs = os.path.join(idir, "emblem.prefs")
    open(prefs, "w").write(PREFS)

    normal, selected = [], []
    for iid, label, a, b, em in ITEMS:
        tts = [f"IMAGE={a}", f"IMAGESELECTED={b}"]
        if em:
            tts += [f"EMBLEM={em},{AT}", f"EMBLEMSELECTED={em},{AT}"]
        pre = os.path.join(idir, "_r")
        r = subprocess.run([RENDER, "--dir", idir, "--prefs", prefs, "--out", pre] + tts, capture_output=True, text=True).stdout
        assert "composed=1" in r, r
        normal.append((iid, f"{iid} {label}", Image.open(pre + "_1.png").convert("RGBA")))
        selected.append((iid, f"{iid} {label}, selected", Image.open(pre + "_2.png").convert("RGBA")))

    rows = [("Disks and devices, emblem lower right", normal), ("Selected (lit from inside; trashcan: full)", selected)]
    cw, cell = 150, 128
    W = 12 + len(ITEMS) * cw
    H = 34 + len(rows) * (18 + 2 * (cell + 22) + 2 * 84 + 14)
    sheet = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    dr = ImageDraw.Draw(sheet)
    dr.text((12, 8), "Group 2, disks and devices: 2x on dark and light, then real size on dark and light.", fill=(0, 0, 0))
    y = 30
    for title, items in rows:
        dr.text((12, y), title, fill=(120, 0, 0))
        y += 18
        for bg in (DARK, LIGHT):
            for k, (_, label, im) in enumerate(items):
                x = 12 + k * cw
                t = Image.new("RGBA", (cell, cell), bg)
                t.alpha_composite(im.resize((cell, cell), Image.LANCZOS))
                sheet.paste(t, (x, y))
                dr.text((x, y + cell + 4), label, fill=(0, 0, 0))
            y += cell + 22
        for bg in (DARK, LIGHT):
            dr.rectangle((0, y, W, y + 80), fill=bg)
            for k, (_, label, im) in enumerate(items):
                sheet.alpha_composite(im, (12 + k * cw + 32, y + 8))
            y += 84
        y += 14
    sheet.convert("RGB").save(out)
    print("sheet ->", out)

    if flip:
        frames = []
        for state in (normal, selected):
            row = Image.new("RGBA", (len(FLIP) * (cell + 8 + 72) + 8, cell + 16), (255, 255, 255, 255))
            x = 8
            for iid, _, im in state:
                if iid not in FLIP:
                    continue
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
