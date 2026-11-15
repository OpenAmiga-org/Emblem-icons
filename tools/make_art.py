#!/home/claude/build/emblem-venv/bin/python
"""make_art.py OUTDIR

Draws the sample art set of the Emblem package: default images (64x64) and
emblems (32x32) as PNG files for ENVARC:sys/emblem, plus the pictures of
the package's own (native) icons as raw ARGB for tools/os4/mkicon.
Everything here is drawn by this script, so the art is public domain like
the rest of the project. Placeholder art: replace the PNGs with real art
whenever there is some.

    tools/make_art.py art [--preview SHEET.png]
        art/*.png        the files in the package (ENVARC:sys/emblem)
        art/own/*.png    own pictures of example icons
        art/icons/       *.argb + mkicons.script for the package's native icons
        SHEET.png        all pictures on one sheet, with IDs (A.., P..)
"""
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter

SS = 8                       # supersampling for smooth edges
OUTLINE = (34, 36, 48, 255)  # the dark rim around every emblem

# colours
YELLOW = (240, 196, 82, 255)
YELLOW_D = (214, 160, 52, 255)
YELLOW_L = (252, 222, 130, 255)
PAPER = (246, 246, 240, 255)
PAPER_S = (214, 226, 246, 255)
LINE = (130, 134, 150, 255)
BLUE = (40, 120, 210, 255)
BLUE_D = (24, 78, 150, 255)
BLUE_L = (120, 180, 240, 255)
GREEN = (52, 170, 84, 255)
GREEN_D = (30, 120, 56, 255)
RED = (220, 50, 50, 255)
RED_D = (160, 28, 36, 255)
ORANGE = (240, 140, 40, 255)
GREY = (170, 174, 186, 255)
GREY_D = (110, 114, 128, 255)
GREY_L = (214, 216, 224, 255)
WHITE = (255, 255, 255, 255)
BROWN = (190, 136, 80, 255)
BROWN_D = (140, 96, 52, 255)
SKY = (150, 200, 245, 255)
PURPLE = (130, 80, 190, 255)


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


# --- default images (64x64) -------------------------------------------------

def drawer_closed(c):
    # back with the tab, then the front
    c.rrect((5, 9, 28, 20), 3, YELLOW_D, OUTLINE, 1.5)
    c.rrect((5, 14, 59, 55), 4, YELLOW_D, OUTLINE, 1.5)
    c.rrect((5, 19, 59, 55), 4, YELLOW, OUTLINE, 1.5)
    c.line((9, 23, 55, 23), YELLOW_L, 1.5)


def img_drawer_ns():
    c = Canvas(64)
    drawer_closed(c)
    return c.done()


def img_drawer_s():
    """the open drawer: papers inside, the front tilted down"""
    c = Canvas(64)
    c.rrect((5, 9, 28, 20), 3, YELLOW_D, OUTLINE, 1.5)
    c.rrect((5, 14, 59, 55), 4, YELLOW_D, OUTLINE, 1.5)
    c.poly((12, 26, 50, 22, 52, 46, 14, 48), PAPER, OUTLINE, 1.2)
    c.poly((16, 22, 54, 20, 54, 44, 16, 46), WHITE, OUTLINE, 1.2)
    c.poly((2, 30, 62, 30, 59, 55, 5, 55), YELLOW, OUTLINE, 1.5)
    c.line((7, 34, 57, 34), YELLOW_L, 1.5)
    return c.done()


def page(c, fill, fold):
    c.poly((13, 4, 41, 4, 51, 14, 51, 60, 13, 60), fill, OUTLINE, 1.5)
    c.poly((41, 4, 41, 14, 51, 14), fold, OUTLINE, 1.2)
    for y in (22, 28, 34, 40, 46, 52):
        c.line((19, y, 45 if y != 52 else 34, y), LINE, 1.5)


def img_document_ns():
    c = Canvas(64)
    page(c, PAPER, GREY_L)
    return c.done()


def img_document_s():
    c = Canvas(64)
    page(c, PAPER_S, BLUE_L)
    return c.done()


# --- emblems (32x32) ------------------------------------------------------

def em_music():
    c = Canvas(32)
    c.poly((11, 6, 27, 3, 27, 9, 11, 12), BLUE)
    c.rect((10.5, 7, 13, 24), BLUE)
    c.rect((24.5, 4, 27, 21), BLUE)
    c.ellipse((4, 20, 13, 27), BLUE)
    c.ellipse((18, 17, 27, 24), BLUE)
    return c.done(1.3)


def em_pictures():
    c = Canvas(32)
    c.rrect((3, 6, 29, 26), 2, WHITE)
    c.rect((5.5, 8.5, 26.5, 23.5), SKY)
    c.ellipse((19, 10, 24, 15), (255, 210, 60, 255))
    c.poly((5.5, 23.5, 12, 14, 17, 20, 20, 17, 26.5, 23.5), GREEN)
    return c.done(1.3)


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


def em_internet():
    c = Canvas(32)
    c.ellipse((3, 3, 29, 29), BLUE)
    for box in ((10, 3.5, 22, 28.5), (15.2, 3.5, 16.8, 28.5)):
        c.ellipse(box, None, BLUE_L, 1.2)
    c.line((3.5, 16, 28.5, 16), BLUE_L, 1.2)
    c.arc((3.5, -6, 28.5, 14), 30, 150, BLUE_L, 1.2)
    c.arc((3.5, 18, 28.5, 38), 210, 330, BLUE_L, 1.2)
    # a little land
    c.poly((7, 9, 12, 7, 13, 12, 10, 15, 6, 13), GREEN)
    c.poly((18, 18, 24, 17, 25, 22, 20, 25, 17, 22), GREEN)
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


def em_games():
    """a joystick: base, stick and a red knob"""
    c = Canvas(32)
    c.rrect((4, 20, 28, 28), 3, GREY_D)
    c.ellipse((20, 21.5, 25, 25.5), RED)
    c.line((14, 22, 12, 9), (60, 60, 70, 255), 3)
    c.ellipse((7, 3, 17, 13), RED)
    c.ellipse((9, 5, 12, 8), (255, 150, 150, 255))
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


def em_download():
    c = Canvas(32)
    c.poly((11, 3, 21, 3, 21, 13, 27, 13, 16, 24, 5, 13, 11, 13), GREEN)
    c.line((12.5, 4.5, 12.5, 14), (120, 210, 140, 255), 1.2)
    c.line((4, 22, 4, 28, 28, 28, 28, 22), GREY_D, 2.5)
    return c.done(1.3)


def em_archive():
    c = Canvas(32)
    c.poly((3, 11, 16, 6, 29, 11, 16, 16), (220, 170, 110, 255))
    c.poly((3, 11, 16, 16, 16, 29, 3, 24), BROWN)
    c.poly((29, 11, 16, 16, 16, 29, 29, 24), BROWN_D)
    c.poly((9.5, 8.5, 22.5, 13.5, 22.5, 18, 20, 17, 20, 14.5, 7, 9.5), (250, 235, 200, 255))
    return c.done(1.3)


def star(c, cx, cy, r_out, r_in, fill):
    import math
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = r_out if i % 2 == 0 else r_in
        pts += [cx + r * math.cos(a), cy + r * math.sin(a)]
    c.poly(pts, fill)


def em_star():
    c = Canvas(32)
    star(c, 16, 17, 14, 6, (255, 200, 40, 255))
    star(c, 16, 17, 8, 3.4, (255, 230, 130, 255))
    return c.done(1.3)


def em_heart():
    c = Canvas(32)
    c.ellipse((3, 5, 17, 19), RED)
    c.ellipse((15, 5, 29, 19), RED)
    c.poly((4, 14.5, 28, 14.5, 16, 28), RED)
    c.ellipse((7, 8, 11, 12), (255, 140, 140, 255))
    return c.done(1.3)


def em_lock():
    c = Canvas(32)
    c.arc((8, 2, 24, 20), 180, 360, GREY_L, 3.2)
    c.line((9.6, 11, 9.6, 15), GREY_L, 3.2)
    c.line((22.4, 11, 22.4, 15), GREY_L, 3.2)
    c.rrect((5, 14, 27, 29), 2.5, (240, 180, 40, 255))
    c.ellipse((14, 18, 18, 22), (90, 60, 20, 255))
    c.rect((15, 21, 17, 25.5), (90, 60, 20, 255))
    return c.done(1.3)


def em_check():
    c = Canvas(32)
    c.ellipse((3, 3, 29, 29), GREEN)
    c.line((9, 16.5, 14, 21.5, 23, 10.5), WHITE, 3.2)
    return c.done(1.3)


def em_warning():
    c = Canvas(32)
    c.poly((16, 3, 30, 28, 2, 28), (255, 205, 40, 255))
    c.line((16, 11, 16, 19.5), OUTLINE, 3.0)
    c.ellipse((14.4, 22.2, 17.6, 25.4), OUTLINE)
    return c.done(1.3)


IMAGES = {
    "DrawerNS": img_drawer_ns,
    "DrawerS": img_drawer_s,
    "DocumentNS": img_document_ns,
    "DocumentS": img_document_s,
}

EMBLEMS = {
    "EmblemMusic": em_music,
    "EmblemPictures": em_pictures,
    "EmblemVideo": em_video,
    "EmblemInternet": em_internet,
    "EmblemMail": em_mail,
    "EmblemPrefs": em_prefs,
    "EmblemTools": em_tools,
    "EmblemGames": em_games,
    "EmblemText": em_text,
    "EmblemCode": em_code,
    "EmblemDownload": em_download,
    "EmblemArchive": em_archive,
    "EmblemStar": em_star,
    "EmblemHeart": em_heart,
    "EmblemLock": em_lock,
    "EmblemCheck": em_check,
    "EmblemWarning": em_warning,
}


# --- own pictures of example icons (not in ENVARC:sys/emblem) -------------------

def own_tools():
    """64x64: the own picture of the INTERNAL example (a big wrench)"""
    c = Canvas(64)
    wrench(c, 2, 0, 0, GREY_L)
    return c.done(2.0)


OWN = {"Tools": own_tools}


# --- the package's own icons (native, made in the guest by mkicon) -------------

def ic_package():
    """the package drawer: a closed drawer with a star emblem"""
    c = Canvas(64)
    drawer_closed(c)
    im = c.done()
    im.alpha_composite(em_star().resize((30, 30), Image.LANCZOS), (32, 27))
    return im


def ic_drawer():
    return img_drawer_ns()


def ic_examples():
    c = Canvas(64)
    drawer_closed(c)
    im = c.done()
    im.alpha_composite(em_check().resize((28, 28), Image.LANCZOS), (33, 28))
    return im


def ic_install():
    c = Canvas(64)
    c.poly((8, 26, 32, 16, 56, 26, 32, 36), (250, 220, 160, 255), OUTLINE, 1.5)
    c.poly((8, 26, 32, 36, 32, 61, 8, 51), BROWN, OUTLINE, 1.5)
    c.poly((56, 26, 32, 36, 32, 61, 56, 51), BROWN_D, OUTLINE, 1.5)
    c.poly((26, 1, 38, 1, 38, 14, 45, 14, 32, 27, 19, 14, 26, 14), GREEN, OUTLINE, 1.5)
    return c.done()


def ic_guide():
    c = Canvas(64)
    page(c, PAPER, GREY_L)
    im = c.done()
    im.alpha_composite(em_star().resize((26, 26), Image.LANCZOS), (34, 34))
    return im


def ic_text():
    c = Canvas(64)
    page(c, PAPER, GREY_L)
    return c.done()


def ic_tool():
    """EmblemIcon (a tool): a drawer with the wrench emblem"""
    c = Canvas(64)
    drawer_closed(c)
    im = c.done()
    im.alpha_composite(em_tools().resize((30, 30), Image.LANCZOS), (32, 27))
    return im


def ic_module():
    """emblem.iconmodule: a puzzle-like plug-in piece"""
    c = Canvas(64)
    c.rrect((8, 14, 52, 56), 5, BLUE, OUTLINE, 1.5)
    c.ellipse((24, 4, 36, 18), BLUE, OUTLINE, 1.5)
    c.rect((25.5, 12, 34.5, 16), BLUE)
    c.ellipse((46, 29, 60, 41), BLUE, OUTLINE, 1.5)
    c.rect((48, 30.5, 52, 39.5), BLUE)
    im = c.done()
    im.alpha_composite(em_star().resize((26, 26), Image.LANCZOS), (14, 22))
    return im


def ic_images():
    """the Images drawer"""
    c = Canvas(64)
    drawer_closed(c)
    im = c.done()
    im.alpha_composite(em_pictures().resize((28, 28), Image.LANCZOS), (33, 28))
    return im


# icon types (workbench/workbench.h)
WBDRAWER, WBTOOL, WBPROJECT = 2, 3, 4

ICONS = {
    # file in the package (without .info): (picture, type, default tool, tool types, stack, window)
    "Emblem": (ic_package, WBDRAWER, None, (), None, (80, 60, 520, 230)),
    "Install": (ic_install, WBPROJECT, "SYS:Utilities/Installer",
                ("APPNAME=Emblem", "MINUSER=AVERAGE", "DEFUSER=AVERAGE", "LOGFILE=T:Emblem_install.log"),
                32768, None),
    "Emblem.guide": (ic_guide, WBPROJECT, "SYS:Utilities/MultiView", (), 32768, None),
    "LICENSE.txt": (ic_text, WBPROJECT, "SYS:Utilities/MultiView", (), 32768, None),
    "Emblem-format.txt": (ic_text, WBPROJECT, "SYS:Utilities/MultiView", (), 32768, None),
    "Examples": (ic_examples, WBDRAWER, None, (), None, (100, 70, 560, 300)),
    "C": (ic_drawer, WBDRAWER, None, (), None, (120, 90, 300, 150)),
    "C/EmblemIcon": (ic_tool, WBTOOL, None, (), 16384, None),
    "Libs": (ic_drawer, WBDRAWER, None, (), None, (120, 90, 300, 150)),
    "Libs/IconModules": (ic_drawer, WBDRAWER, None, (), None, (140, 110, 300, 150)),
    "Libs/IconModules/emblem.iconmodule": (ic_module, WBPROJECT, None, (), None, None),
    "Images": (ic_images, WBDRAWER, None, (), None, (120, 90, 560, 300)),
}


def argb(img):
    return b"".join(bytes((a, r, g, b)) for (r, g, b, a) in img.get_flattened_data())


def selected(img):
    """a native icon's selected picture: a little darker"""
    px = [(int(r * 0.72), int(g * 0.72), int(b * 0.78), a) for (r, g, b, a) in img.get_flattened_data()]
    out = Image.new("RGBA", img.size)
    out.putdata(px)
    return out


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
    pics = []
    for name, fn in list(IMAGES.items()) + list(EMBLEMS.items()):
        im = fn()
        im.save(os.path.join(out, name + ".png"), optimize=True)
        pics.append((name, im))

    os.makedirs(os.path.join(out, "own"), exist_ok=True)
    for name, fn in OWN.items():
        fn().save(os.path.join(out, "own", name + ".png"), optimize=True)

    lines = ["; made by tools/make_art.py: run in a drawer with mkicon and the .argb files",
             "FailAt 21", "MakeDir >NIL: out"]
    iconpics = []
    for name, (fn, typ, tool, tts, stack, window) in ICONS.items():
        flat = name.replace("/", "_")
        im = fn()
        iconpics.append((flat, im))
        open(os.path.join(icons, flat + ".argb"), "wb").write(argb(im))
        open(os.path.join(icons, flat + ".sel.argb"), "wb").write(argb(selected(im)))
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
    print(f"{len(pics)} pictures, {len(ICONS)} icons -> {out}")


if __name__ == "__main__":
    main()
