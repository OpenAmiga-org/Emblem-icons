#!/home/claude/build/emblem-venv/bin/python
"""render_sheet.py IMAGEDIR OWNDIR OUT.png [CASES.json]

A contact sheet of composed icons, rendered with build/host/render (the
module's own code): for each case the normal and the selected image at 2x
on a Workbench-like grey, with its ID and tool types.

IMAGEDIR: default images and emblems (Name.png). OWNDIR: the icons' own
images as <Icon>_1.argb / <Icon>_2.argb ("icontest pixels").
A case is [id, icon, [tool types...], caption] or with a fifth element, the
text of an emblem.prefs file for that case. CASES.json may also be a name
from this script (step3, step4).
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENDER = os.path.join(ROOT, "build", "host", "render")
BG = (170, 170, 170)

STEP3 = [
    ["R01", "Devs", [], "SYS:Devs as it is (reference)"],
    ["R02", "Devs", ["IMAGE=DrawerNS", "IMAGESELECTED=DrawerS", "EMBLEM=EmblemPrefs,24,24,34,26",
                     "EMBLEMSELECTED=EmblemPrefs,24,24,33,27"], "default drawer + emblem, 24x24"],
    ["R03", "AHI", ["IMAGE=DrawerNS", "IMAGESELECTED=DrawerS", "EMBLEM=EmblemAHI,0,0,23,2",
                    "EMBLEMSELECTED=EmblemAHI,0,0,23,2"], "spec's AHI example: emblem at own size"],
    ["R04", "Prefs", ["EMBLEM=EmblemStar,20,20,42,0", "EMBLEMSELECTED=EmblemStar,20,20,42,0"],
     "emblem on the icon's own image (no IMAGE)"],
    ["R05", "Utilities", ["EMBLEM=EmblemInternet,28,28,34,34,NONE"], "method NONE"],
    ["R06", "Utilities", ["EMBLEM=EmblemInternet,28,28,34,34,DARK"], "method DARK (25 % darker)"],
    ["R07", "Utilities", ["EMBLEM=EmblemInternet,28,28,34,34,BRIGHT"], "method BRIGHT (25 % toward white)"],
    ["R08", "Utilities", ["EMBLEM=EmblemInternet,28,28,34,34,GRAY"], "method GRAY"],
    ["R09", "Devs", ["IMAGE=DrawerNS,GRAY", "IMAGESELECTED=DrawerS,DARK", "EMBLEM=EmblemInternet,24,24,36,28"],
     "methods on the default images"],
    ["R10", "Clock", ["IMAGE=DrawerNS", "IMAGESELECTED=DrawerS", "EMBLEM=INTERNAL,32,32,26,22",
                      "EMBLEMSELECTED=INTERNAL,32,32,26,22"], "INTERNAL: the icon's own image as emblem"],
    ["R11", "Devs", ["EMBLEM=EmblemStar,48,0,30,30"], "32x32 emblem scaled up to 48x48, clipped"],
    ["R12", "Devs", ["EMBLEM=EmblemPrefs,0,40,-12,-12"], "negative position, clipped at the top left"],
]


STEP4 = [
    ["S01", "Devs", ["IMAGE=DrawerNS", "IMAGESELECTED=DrawerS", "EMBLEM=EmblemPrefs,24,24,34,26,SHADOW",
                     "EMBLEMSELECTED=EmblemPrefs,24,24,33,27,SHADOW"], "spec's Devs example: emblem SHADOW"],
    ["S02", "AHI", ["IMAGE=DrawerNS", "IMAGESELECTED=DrawerS", "EMBLEM=EmblemAHI,0,0,23,2,SHADOW",
                    "EMBLEMSELECTED=EmblemAHI,0,0,23,2,SHADOW"], "spec's AHI example (SHADOW)"],
    ["S03", "Prefs", ["EMBLEM=EmblemStar,20,20,40,2,GLOW", "EMBLEMSELECTED=EmblemStar,20,20,40,2,GLOW"],
     "emblem GLOW on the icon's own image"],
    ["S04", "Prefs", ["EMBLEM=EmblemPrefs,20,20,40,2,NONE", "EMBLEMSELECTED=EmblemPrefs,20,20,40,2,GLOW"],
     "spec's MUI example: NONE, selected GLOW"],
    ["S05", "Utilities", ["EMBLEM=EmblemInternet,28,28,34,34,SHADOW", "EMBLEMSELECTED=EmblemInternet,28,28,34,34,SHADOW"],
     "shadow clipped at the image's edge"],
    ["S06", "Devs", ["IMAGE=DrawerNS,SHADOW", "IMAGESELECTED=DrawerS,SHADOW", "EMBLEM=EmblemPrefs,24,24,34,26,SHADOW"],
     "SHADOW on the default images too"],
    ["S07", "Devs", ["IMAGE=DrawerNS,GLOW", "IMAGESELECTED=DrawerS,GLOW"], "GLOW on the default images"],
    ["S08", "Devs", ["IMAGE=DrawerNS", "IMAGESELECTED=DrawerS", "EMBLEM=EmblemPrefs,24,24,34,26",
                     "EMBLEMSELECTED=EmblemPrefs,24,24,33,27"], "no methods; prefs METHOD=SHADOW", "METHOD=SHADOW\n"],
    ["S09", "Devs", ["IMAGE=DrawerNS", "IMAGESELECTED=DrawerS", "EMBLEM=EmblemPrefs,24,24,34,26",
                     "EMBLEMSELECTED=EmblemPrefs,24,24,33,27"], "no methods; prefs EMBLEMMETHOD=SHADOW",
     "EMBLEMMETHOD=SHADOW\n"],
    ["S10", "Utilities", ["EMBLEM=EmblemInternet,28,28,30,30", "EMBLEMSELECTED=EmblemInternet,28,28,30,30"],
     "prefs: yellow glow, size 3", "EMBLEMMETHOD=GLOW\nGLOWCOLOR=FFD040\nGLOWSIZE=3\nGLOWOPACITY=90\n"],
    ["S11", "Utilities", ["EMBLEM=EmblemInternet,28,28,30,30", "EMBLEMSELECTED=EmblemInternet,28,28,30,30"],
     "prefs: tighter, darker shadow", "EMBLEMMETHOD=SHADOW\nSHADOWOFFSET=2,2\nSHADOWBLUR=1\nSHADOWOPACITY=70\n"],
    ["S12", "Clock", ["IMAGE=DrawerNS", "IMAGESELECTED=DrawerS", "EMBLEM=INTERNAL,32,32,26,22",
                      "EMBLEMSELECTED=INTERNAL,32,32,26,22"], "spec's INTERNAL example; prefs SHADOW",
     "EMBLEMMETHOD=SHADOW\n"],
]


def argb_to_image(path):
    b = open(path, "rb").read()
    w, h = int.from_bytes(b[0:4], "big"), int.from_bytes(b[4:8], "big")
    px = b[8:]
    rgba = bytes(px[i + j] for i in range(0, len(px), 4) for j in (1, 2, 3, 0))
    return Image.frombytes("RGBA", (w, h), rgba)


def main():
    imgdir, owndir, out = sys.argv[1:4]
    named = {"step3": STEP3, "step4": STEP4}
    arg = sys.argv[4] if len(sys.argv) > 4 else "step3"
    cases = named[arg] if arg in named else json.load(open(arg))
    tmp = os.path.join(os.path.dirname(os.path.abspath(out)), ".sheet_tmp")
    os.makedirs(tmp, exist_ok=True)
    cells = []
    for case in cases:
        cid, icon, tts, caption = case[:4]
        prefs = case[4] if len(case) > 4 else None
        own = [os.path.join(owndir, f"{icon}_{i}.argb") for i in (1, 2)]
        args = [RENDER, "--dir", imgdir, "--out", os.path.join(tmp, cid)]
        if prefs:
            pf = os.path.join(tmp, "case.prefs")
            open(pf, "w").write(prefs)
            args += ["--prefs", pf]
        for i, f in enumerate(own):
            if os.path.exists(f):
                args += [f"--own{i + 1}", f]
        r = subprocess.run(args + tts, capture_output=True, text=True).stdout
        imgs = []
        for i in (1, 2):
            p = os.path.join(tmp, f"{cid}_{i}.png")
            if "composed=1" in r and os.path.exists(p):
                imgs.append(Image.open(p).convert("RGBA"))
            elif "composed=1" not in r and os.path.exists(own[i - 1]):
                imgs.append(argb_to_image(own[i - 1]))
            if os.path.exists(p):
                os.remove(p)
        cells.append((cid, icon, tts, caption, imgs, prefs))

    cw, ch, cols = 300, 232, 3
    rows = (len(cells) + cols - 1) // cols
    sheet = Image.new("RGB", (cw * cols, ch * rows), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for n, (cid, icon, tts, caption, imgs, prefs) in enumerate(cells):
        x0, y0 = (n % cols) * cw, (n // cols) * ch
        d.text((x0 + 6, y0 + 4), f"{cid}  {icon}: {caption}", fill=(0, 0, 0))
        d.rectangle((x0 + 6, y0 + 20, x0 + 6 + 2 * 128 + 12, y0 + 20 + 128 + 4), fill=BG)
        for i, im in enumerate(imgs):
            big = im.resize((im.width * 2, im.height * 2), Image.NEAREST)
            tile = Image.new("RGBA", big.size, BG + (255,))
            tile.alpha_composite(big)
            sheet.paste(tile.convert("RGB"), (x0 + 8 + i * 136, y0 + 22))
        d.text((x0 + 8, y0 + 152), "normal" + ("            selected" if len(imgs) > 1 else ""), fill=(90, 90, 90))

        def fit(t):
            while t and d.textlength(t) > cw - 12:
                t = t[:-2] + "~"
            return t
        for k, t in enumerate(tts[:4]):
            d.text((x0 + 6, y0 + 164 + 12 * k), fit(t), fill=(30, 30, 140))
        if prefs:
            d.text((x0 + 6, y0 + 214), fit("prefs: " + prefs.strip().replace("\n", "; ")), fill=(140, 30, 30))
    sheet.save(out)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    print(f"{len(cells)} cases -> {out}")


if __name__ == "__main__":
    main()
