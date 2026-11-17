#!/home/claude/build/emblem-venv/bin/python
"""make_art.py OUTDIR

The sample art set of the Emblem package and the pictures of its own (native) icons.

Pictures made elsewhere, in the OS 4.1 icon style (tools in ~/os4icons, 2026-11-17); this script
only reads them:
    art/DrawerNS, DrawerS, DocumentNS, DocumentS.png   the default images (64x64)
    art/Emblem<Name>.png for the names in SUPPLIED     the shipped emblems (32x32)
    art/own/Tools.png                                  the INTERNAL example's own picture
    art/package/NAME.png + NAME.sel.png                the package's icons (ICONS), normal and
                                                       selected exactly as they are (the selected
                                                       ones are already made the OS 4.1 way)
Drawn here (not shipped, kept as extra emblems): the emblems in EMBLEMS.

    tools/make_art.py art [--preview SHEET.png]
        art/Emblem*.png  the drawn emblems
        art/icons/       *.argb + mkicons.script for the package's native icons
        SHEET.png        all pictures on one sheet, with IDs (A.., P..)
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

SS = 8                       # supersampling for smooth edges
OUTLINE = (34, 36, 48, 255)  # the dark rim around every emblem

# colours
PAPER = (246, 246, 240, 255)
LINE = (130, 134, 150, 255)
BLUE_L = (120, 180, 240, 255)
RED = (220, 50, 50, 255)
GREY = (170, 174, 186, 255)
GREY_D = (110, 114, 128, 255)
GREY_L = (214, 216, 224, 255)
WHITE = (255, 255, 255, 255)


class Canvas:
    """A size x size picture drawn SS times larger; coordinates in final pixels."""

    def __init__(self, size):
        self.size = size
        self.im = Image.new("RGBA", (size * SS, size * SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    @staticmethod
    def p(*v):
        return [round(x * SS) for x in v]

    def poly(self, pts, fill, outline=None, width=1.0):
        self.d.polygon(self.p(*pts), fill=fill)
        if outline:
            self.d.line(self.p(*pts, pts[0], pts[1]), fill=outline, width=round(width * SS), joint="curve")

    def rrect(self, box, r, fill, outline=None, width=1.0):
        self.d.rounded_rectangle(self.p(*box), radius=round(r * SS), fill=fill,
                                 outline=outline, width=round(width * SS) if outline else 0)

    def rect(self, box, fill):
        self.d.rectangle(self.p(*box), fill=fill)

    def ellipse(self, box, fill, outline=None, width=1.0):
        self.d.ellipse(self.p(*box), fill=fill, outline=outline,
                       width=round(width * SS) if outline else 0)

    def line(self, pts, fill, width=1.0):
        self.d.line(self.p(*pts), fill=fill, width=round(width * SS), joint="curve")

    def arc(self, box, a0, a1, fill, width=1.0):
        self.d.arc(self.p(*box), a0, a1, fill=fill, width=round(width * SS))

    def done(self, rim=0.0):
        """The final picture; rim > 0 puts a dark outline of that width around
        everything drawn (the emblem style: readable on any background)."""
        im = self.im
        if rim:
            a = im.getchannel("A")
            grown = a.filter(ImageFilter.GaussianBlur(rim * SS * 0.6)).point(lambda v: 255 if v > 8 else 0)
            grown = grown.filter(ImageFilter.GaussianBlur(SS * 0.35))
            under = Image.new("RGBA", im.size, OUTLINE)
            under.putalpha(grown)
            under.alpha_composite(im)
            im = under
        return im.resize((self.size, self.size), Image.BOX)


# --- the emblems drawn here (32x32, not shipped) ----------------------------

def em_video():
    c = Canvas(32)
    c.rrect((3, 12, 29, 28), 2, GREY_D)
    c.poly((3, 6, 27, 2, 28, 7, 4, 11), WHITE)
    for x in (8, 14, 20):
        c.poly((x, 5.3, x + 3, 4.8, x + 1, 9.8, x - 2, 10.2), GREY_D)
    for x in (6, 12, 18, 24):
        c.rect((x, 13.5, x + 3, 15.5), WHITE)
        c.rect((x, 24.5, x + 3, 26.5), WHITE)
    c.rect((6, 17, 26, 23), BLUE_L)
    return c.done(1.3)


def em_mail():
    c = Canvas(32)
    c.rrect((3, 7, 29, 25), 1.5, WHITE)
    c.line((4, 8, 16, 17, 28, 8), GREY_D, 1.4)
    c.line((4, 24, 12, 15), GREY, 1.0)
    c.line((28, 24, 20, 15), GREY, 1.0)
    c.rect((22, 9.5, 26, 13), RED)
    return c.done(1.3)


def gear(c, cx, cy, r_out, r_in, teeth, fill, hole):
    import math
    pts = []
    for i in range(teeth * 4):
        a = (i / (teeth * 4)) * 2 * math.pi
        r = r_out if (i % 4) in (1, 2) else r_in
        pts += [cx + r * math.cos(a), cy + r * math.sin(a)]
    c.poly(pts, fill)
    c.ellipse((cx - hole, cy - hole, cx + hole, cy + hole), (0, 0, 0, 0))


def em_prefs():
    c = Canvas(32)
    gear(c, 16, 16, 13.5, 10, 8, GREY, 4.2)
    # the hole must stay see-through: cut it out of the alpha
    c.d.ellipse(c.p(16 - 4.2, 16 - 4.2, 16 + 4.2, 16 + 4.2), fill=(0, 0, 0, 0))
    c.ellipse((8.5, 8.5, 23.5, 23.5), None, GREY_L, 1.0)
    return c.done(1.3)


def wrench(c, k, ox, oy, fill):
    """an open-end wrench from top right to bottom left, k = scale (1 = 32 px)"""
    def P(*v):
        return [ox + x * k if i % 2 == 0 else oy + x * k for i, x in enumerate(v)]
    c.line(P(21, 11, 7, 25), fill, 5 * k)          # handle
    c.ellipse(P(3.5, 21.5, 10.5, 28.5), fill)      # its round end
    c.ellipse(P(16, 2, 30, 16), fill)              # head
    # the jaw: a slot from the head's centre to the top right
    c.d.polygon(c.p(*P(21.2, 7.2, 24.8, 10.8, 32.5, 3.1, 28.9, -0.5)), fill=(0, 0, 0, 0))


def em_tools():
    c = Canvas(32)
    wrench(c, 1, 0, 0, GREY_L)
    return c.done(1.3)


def em_text():
    c = Canvas(32)
    c.poly((6, 3, 20, 3, 26, 9, 26, 29, 6, 29), PAPER)
    c.poly((20, 3, 20, 9, 26, 9), GREY_L)
    for y in (13, 17, 21, 25):
        c.line((9.5, y, 22.5 if y != 25 else 17, y), LINE, 1.6)
    return c.done(1.3)


def em_code():
    c = Canvas(32)
    c.rrect((2, 5, 30, 27), 4, (50, 56, 80, 255))
    c.line((11, 10, 6, 16, 11, 22), (120, 230, 140, 255), 2.2)
    c.line((21, 10, 26, 16, 21, 22), (120, 230, 140, 255), 2.2)
    c.line((18, 9, 14, 23), WHITE, 2.0)
    return c.done(1.0)


def em_heart():
    c = Canvas(32)
    c.ellipse((3, 5, 17, 19), RED)
    c.ellipse((15, 5, 29, 19), RED)
    c.poly((4, 14.5, 28, 14.5, 16, 28), RED)
    c.ellipse((7, 8, 11, 12), (255, 140, 140, 255))
    return c.done(1.3)


def em_warning():
    c = Canvas(32)
    c.poly((16, 3, 30, 28, 2, 28), (255, 205, 40, 255))
    c.line((16, 11, 16, 19.5), OUTLINE, 3.0)
    c.ellipse((14.4, 22.2, 17.6, 25.4), OUTLINE)
    return c.done(1.3)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "art")
IMAGES = ["DrawerNS", "DrawerS", "DocumentNS", "DocumentS"]      # art/<name>.png, read only
SUPPLIED = ["EmblemMusic", "EmblemPictures", "EmblemInternet", "EmblemGames", "EmblemDownload",
            "EmblemLock", "EmblemStar", "EmblemArchive", "EmblemCheck"]   # art/<name>.png, read only
OWN = ["Tools"]                                                  # art/own/<name>.png, read only

EMBLEMS = {
    "EmblemVideo": em_video,
    "EmblemMail": em_mail,
    "EmblemPrefs": em_prefs,
    "EmblemTools": em_tools,
    "EmblemText": em_text,
    "EmblemCode": em_code,
    "EmblemHeart": em_heart,
    "EmblemWarning": em_warning,
}

# the order of the A.. IDs on the sheet (as before: the images, then the emblems)
EMBLEM_ORDER = ["EmblemMusic", "EmblemPictures", "EmblemVideo", "EmblemInternet", "EmblemMail",
                "EmblemPrefs", "EmblemTools", "EmblemGames", "EmblemText", "EmblemCode", "EmblemDownload",
                "EmblemArchive", "EmblemStar", "EmblemHeart", "EmblemLock", "EmblemCheck", "EmblemWarning"]


# --- the package's own icons (native, made in the guest by mkicon) -------------

# icon types (workbench/workbench.h)
WBDRAWER, WBTOOL, WBPROJECT = 2, 3, 4

ICONS = {
    # file in the package (without .info): (type, default tool, tool types, stack, window);
    # pictures art/package/<name with _ for />.png and .sel.png
    "Emblem": (WBDRAWER, None, (), None, (80, 60, 520, 230)),
    "Install": (WBPROJECT, "SYS:Utilities/Installer",
                ("APPNAME=Emblem", "MINUSER=AVERAGE", "DEFUSER=AVERAGE", "LOGFILE=T:Emblem_install.log"),
                32768, None),
    "Emblem.guide": (WBPROJECT, "SYS:Utilities/MultiView", (), 32768, None),
    "LICENSE.txt": (WBPROJECT, "SYS:Utilities/MultiView", (), 32768, None),
    "Emblem-format.txt": (WBPROJECT, "SYS:Utilities/MultiView", (), 32768, None),
    "Examples": (WBDRAWER, None, (), None, (100, 70, 560, 300)),
    "C": (WBDRAWER, None, (), None, (120, 90, 300, 150)),
    "C/EmblemIcon": (WBTOOL, None, (), 16384, None),
    "Libs": (WBDRAWER, None, (), None, (120, 90, 300, 150)),
    "Libs/IconModules": (WBDRAWER, None, (), None, (140, 110, 300, 150)),
    "Libs/IconModules/emblem.iconmodule": (WBPROJECT, None, (), None, None),
    "Images": (WBDRAWER, None, (), None, (120, 90, 560, 300)),
    "RemoveSamples": (WBPROJECT, "C:IconX",
                      ("WINDOW=CON:80/60/560/240/Emblem samples/AUTO/CLOSE/WAIT",), 16384, None),
}


def argb(img):
    return b"".join(bytes((a, r, g, b)) for (r, g, b, a) in img.get_flattened_data())


def load(path, size):
    im = Image.open(path).convert("RGBA")
    if im.size != (size, size):
        sys.exit(f"{path}: {im.width}x{im.height}, should be {size}x{size}")
    return im


def sheet(items, cell, cols, scale=2):
    """preview: pictures at scale x on a Workbench grey, name under each"""
    rows = (len(items) + cols - 1) // cols
    w, h = cell * scale + 16, cell * scale + 28
    out = Image.new("RGBA", (w * cols, h * rows), (255, 255, 255, 255))
    d = ImageDraw.Draw(out)
    for n, (name, im) in enumerate(items):
        x, y = (n % cols) * w, (n // cols) * h
        bg = Image.new("RGBA", (cell * scale, cell * scale), (170, 170, 170, 255))
        bg.alpha_composite(im.resize((im.width * scale, im.height * scale), Image.NEAREST),
                           ((cell - im.width) * scale // 2, (cell - im.height) * scale // 2))
        out.paste(bg, (x + 8, y + 6))
        d.text((x + 8, y + cell * scale + 10), name, fill=(0, 0, 0))
    return out


def main():
    out = sys.argv[1]
    icons = os.path.join(out, "icons")
    os.makedirs(icons, exist_ok=True)
    pics = [(name, load(os.path.join(ART, name + ".png"), 64)) for name in IMAGES]
    for name in EMBLEM_ORDER:
        if name in EMBLEMS:
            im = EMBLEMS[name]()
            im.save(os.path.join(out, name + ".png"), optimize=True)
        else:
            im = load(os.path.join(ART, name + ".png"), 32)
        pics.append((name, im))
    for name in OWN:
        load(os.path.join(ART, "own", name + ".png"), 64)

    lines = ["; made by tools/make_art.py: run in a drawer with mkicon and the .argb files",
             "FailAt 21", "MakeDir >NIL: out"]
    iconpics = []
    for name, (typ, tool, tts, stack, window) in ICONS.items():
        flat = name.replace("/", "_")
        im = load(os.path.join(ART, "package", flat + ".png"), 64)
        sel = load(os.path.join(ART, "package", flat + ".sel.png"), 64)
        iconpics.append((flat, im))
        open(os.path.join(icons, flat + ".argb"), "wb").write(argb(im))
        open(os.path.join(icons, flat + ".sel.argb"), "wb").write(argb(sel))
        t = {WBDRAWER: "DRAWER", WBTOOL: "TOOL", WBPROJECT: "PROJECT"}[typ]
        args = ['"out/%s"' % flat, "ARGB=%s.argb" % flat, "SELECTED=%s.sel.argb" % flat, "TYPE=" + t]
        if tool:
            args.append('"TOOL=%s"' % tool)
        if stack:
            args.append("STACK=%d" % stack)
        if window:
            args.append("WINDOW=%d,%d,%d,%d" % window)
        args += ['"TT=%s"' % tt for tt in tts]
        lines.append("mkicon " + " ".join(args))
    open(os.path.join(icons, "mkicons.script"), "w").write("\n".join(lines) + "\n")

    # IDs on the sheet: A01... the art set, P01... the package icons
    labelled = [(f"A{n + 1:02d} {name}", im) for n, (name, im) in enumerate(pics)]
    a = sheet(labelled[:len(IMAGES)], 64, len(IMAGES))
    b = sheet(labelled[len(IMAGES):], 32, 9, scale=3)
    c = sheet([(f"P{n + 1:02d} {name.split('/')[-1]}", im) for n, ((name, _), (_, im))
               in enumerate(zip(ICONS.items(), iconpics))], 64, 7)
    full = Image.new("RGBA", (max(a.width, b.width, c.width), a.height + b.height + c.height + 40), (255, 255, 255, 255))
    d = ImageDraw.Draw(full)
    y = 0
    for title, part in (("default images (64x64)", a), ("emblems (32x32, shown 3x)", b),
                        ("the package's own icons (native, 64x64)", c)):
        d.text((8, y + 2), title, fill=(120, 0, 0))
        full.paste(part, (0, y + 14))
        y += part.height + 14
    if "--preview" in sys.argv:
        full.convert("RGB").save(sys.argv[sys.argv.index("--preview") + 1])
    print(f"{len(EMBLEMS)} emblems drawn, {len(pics) - len(EMBLEMS)} pictures read, {len(ICONS)} icons -> {out}")


if __name__ == "__main__":
    main()
