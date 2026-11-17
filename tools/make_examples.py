#!/home/claude/build/emblem-venv/bin/python
"""make_examples.py ARTDIR OUTDIR [--sheet SHEET.png]
   make_examples.py --images      the images the examples take from ENVARC:sys/emblem,
                                  one name a line: the package's sample set (tools/make_lha.sh)

Builds the package's Examples drawer: empty drawers and one text file, each
with an Emblem icon (tools/mkemblem, built by `make tools`) that shows one
feature. OUTDIR gets the drawers and the .info files; package/Examples/ReadMe
is copied by tools/make_lha.sh.

--sheet also renders the examples with the module's composition code
(build/host/render through tools/render_sheet.py) with the settings the
Install script writes by default (EMBLEMMETHOD=SHADOW).
"""
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MKEMBLEM = os.path.join(ROOT, "build", "host", "mkemblem")
WINDOW = "100,70,560,300"
DEFAULT_PREFS = "EMBLEMMETHOD=SHADOW\n"

SETTING_KEYS = ("IMAGE", "IMAGESELECTED", "EMBLEM", "EMBLEMSELECTED")
D = ["IMAGE=DrawerNS", "IMAGESELECTED=DrawerS"]


def em(name, method=""):
    """EMBLEM and EMBLEMSELECTED at the drawer's lower right"""
    a = f"{name},28,28,34,32" + (f",{method}" if method else "")
    return [f"EMBLEM={a}", f"EMBLEMSELECTED={a}"]


# name, type, own images (art names; None = DrawerNS/DrawerS), settings, what it shows
EXAMPLES = [
    ("Music", "DRAWER", None, D + em("EmblemMusic"),
     "no method: the settings decide"),
    ("Pictures", "DRAWER", None, D + em("EmblemPictures", "SHADOW"), "SHADOW"),
    ("Internet", "DRAWER", None, D + em("EmblemInternet", "GLOW"), "GLOW"),
    ("Games", "DRAWER", None, D + ["EMBLEM=EmblemGames,0,0,32,30,NONE", "EMBLEMSELECTED=EmblemGames,0,0,32,30,NONE"],
     "size 0,0 = own size; NONE"),
    ("Downloads", "DRAWER", None, D + em("EmblemDownload"), "another emblem"),
    ("Private", "DRAWER", None, ["IMAGE=DrawerNS,DARK", "IMAGESELECTED=DrawerS,DARK"] + em("EmblemLock", "NONE"),
     "DARK on the default images"),
    ("Favourites", "DRAWER", None, D + ["EMBLEM=EmblemStar,24,24,20,18,GLOW", "EMBLEMSELECTED=EmblemStar,24,24,20,22,GLOW"],
     "centred; moves when selected"),
    ("Old stuff", "DRAWER", None, ["IMAGE=DrawerNS,GRAY", "IMAGESELECTED=DrawerS,GRAY"] + em("EmblemArchive", "GRAY"),
     "GRAY on image and emblem"),
    ("Tools", "DRAWER", ("own/Tools", None), D + ["EMBLEM=INTERNAL,30,30,33,30", "EMBLEMSELECTED=INTERNAL,30,30,33,30"],
     "INTERNAL: own picture as emblem"),
    ("ReadMe", "PROJECT", ("DocumentNS", "DocumentS"), ["EMBLEM=EmblemCheck,26,26,36,36", "EMBLEMSELECTED=EmblemCheck,26,26,36,36"],
     "no IMAGE=: emblem on own picture"),
]


def images():
    """the names the examples' settings take from ENVARC:sys/emblem (INTERNAL is the icon's own)"""
    names = []
    for _, _, _, tts, _ in EXAMPLES:
        for t in tts:
            key, _, val = t.partition("=")
            n = val.split(",")[0]
            if key in SETTING_KEYS and n != "INTERNAL" and n not in names:
                names.append(n)
    return names


def position(i):
    return 14 + (i % 5) * 104, 10 + (i // 5) * 100


def build(art, out):
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    for i, (name, typ, own, tts, _) in enumerate(EXAMPLES):
        own = own or ("DrawerNS", "DrawerS")
        args = [MKEMBLEM, os.path.join(out, name + ".info"), "TYPE=" + typ,
                "IMAGE=" + os.path.join(art, own[0] + ".png"), "POS=%d,%d" % position(i)]
        if own[1]:
            args.append("SELECTED=" + os.path.join(art, own[1] + ".png"))
        if typ == "DRAWER":
            os.makedirs(os.path.join(out, name))
            args.append("WINDOW=" + WINDOW)
        else:
            args += ["TOOL=SYS:Utilities/MultiView", "STACK=32768"]
        # the Emblem keys are the icon's settings (ES=), anything else a tool type
        args += [("ES=" if t.partition("=")[0] in SETTING_KEYS else "TT=") + t for t in tts]
        subprocess.run(args, check=True)
    print(f"{len(EXAMPLES)} example icons -> {out}")


def write_argb(png, path):
    from PIL import Image
    im = Image.open(png).convert("RGBA")
    px = b"".join(bytes((a, r, g, b)) for (r, g, b, a) in im.get_flattened_data())
    open(path, "wb").write(im.width.to_bytes(4, "big") + im.height.to_bytes(4, "big") + px)


def sheet(art, path):
    tmp = os.path.join(os.path.dirname(os.path.abspath(path)), ".examples_own")
    os.makedirs(tmp, exist_ok=True)
    cases = []
    for i, (name, typ, own, tts, what) in enumerate(EXAMPLES):
        own = own or ("DrawerNS", "DrawerS")
        key = name.replace(" ", "")
        write_argb(os.path.join(art, own[0] + ".png"), os.path.join(tmp, f"{key}_1.argb"))
        if own[1]:
            write_argb(os.path.join(art, own[1] + ".png"), os.path.join(tmp, f"{key}_2.argb"))
        elif os.path.exists(os.path.join(tmp, f"{key}_2.argb")):
            os.remove(os.path.join(tmp, f"{key}_2.argb"))
        cases.append([f"X{i + 1:02d}", key, tts, what, DEFAULT_PREFS])
    cf = os.path.join(tmp, "cases.json")
    json.dump(cases, open(cf, "w"))
    subprocess.run([os.path.join(ROOT, "tools", "render_sheet.py"), art, tmp, path, cf], check=True)
    shutil.rmtree(tmp)


def main():
    if sys.argv[1:] == ["--images"]:
        print("\n".join(images()))
        return
    art, out = sys.argv[1:3]
    build(art, out)
    if "--sheet" in sys.argv:
        sheet(art, sys.argv[sys.argv.index("--sheet") + 1])


if __name__ == "__main__":
    main()
