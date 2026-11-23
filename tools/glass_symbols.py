#!/home/claude/build/emblem-venv/bin/python
"""glass_symbols.py OUTDIR [NAME...]

White emblem symbols (512x512, transparent) for the glass emblem tiles
(tools/blender/glass_icons.py gem RRGGBB SYMBOL.png OUT.png). Drawn in a 64x64
space at 8x. Emblem colours are pure, deep RGB colours (the user: deep red,
deep green, deep blue and violet; no pinks or browns); see TILES. Public domain.
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_iconsets import G, WHITE, joystick, note  # noqa: E402

# chosen by the user 2026-11-16 (docs/iconsets/glass/emblem_*.png): R3, G3, B3, V3. Violet replaced
# yellow, which did not fit the deep glass colours.
RED, GREEN, BLUE, VIOLET = "940000", "007711", "0028A5", "72008E"

# emblem tile name: (symbol, colour)
TILES = {
    "EmMusic": ("music", RED),
    "EmGames": ("games", GREEN),
    "EmPicture": ("picture", BLUE),
    "EmStar": ("star", VIOLET),
    "EmCommodity": ("keycap", VIOLET),             # the commodities' family emblem (user picked B 2026-11-22)
    # SYS: drawers (group 1)
    "EmPrefs": ("gear", BLUE),
    "EmUtilities": ("wrench", VIOLET),
    "EmSystem": ("chip", RED),
    "EmStorage": ("stack", GREEN),
    "EmStartup": ("power", RED),
    "EmDevs": ("plug", VIOLET),
    "EmInternet": ("globe", BLUE),
    "EmEmulation": ("games", GREEN),
    "EmDocs": ("book", VIOLET),
    "EmMUI": ("window", BLUE),
    # disks and devices (group 2)
    "EmWarning": ("warning", RED),
    "EmHome": ("home", GREEN),
    # Internet project icons (group 4): the DV08 network globe + these (Open Connection: SdConnections)
    "EmConnNew": ("plus", BLUE),
    "EmConnEdit": ("pencil", BLUE),
    # files by type (group 3)
    "EmDocument": ("document", VIOLET),
    "EmVideo": ("video", RED),
    "EmCode": ("code", GREEN),
    "EmFont": ("font", VIOLET),
    # the Presets drawer in Prefs (group 4, 2026-11-16: a drawer, so the glass drawer + this emblem)
    "EmPresets": ("presets", BLUE),
    # Presets sub-drawers (2026-11-21, variants until the user picks)
    "SdPrAmiDock": ("dock", BLUE),
    "SdPrDefault": ("default", BLUE),
    # Presets/Patterns (DO03): SdMuiPatterns, the user picked the MUI/Patterns tile
    "SdPrPointers": ("pointers", BLUE),
    "SdPrSilverGreen": ("silvergreen", BLUE),
    "SdPrSounds": ("sounds", BLUE),
    "SdPyLib": ("pylib", RED),
}
# archives (group 3): the glass crate + a tile with the format letters
ARCHIVES = ["LHA", "LZX", "ZIP", "GZ", "BZ2", "TAR", "7Z", "ARJ", "RAR", "ZOO"]
TILES.update({"Em" + a: (a.lower(), GREEN) for a in ARCHIVES})


def erase(c, draw):
    """cut what draw(g) paints out of c"""
    g = G(64)
    draw(g)
    a = np.asarray(c.im.getchannel("A"), np.float32) * (1 - np.asarray(g.im.getchannel("A"), np.float32) / 255)
    c.im.putalpha(Image.fromarray(a.astype(np.uint8), "L"))


def s_music(c):
    note(c, 11.1, 9.8, 2.4, WHITE)


def s_games(c):
    joystick(c, 10.2, 10.2, 2.3, WHITE, WHITE, WHITE, WHITE)


def s_picture(c):
    c.rect((9, 13, 55, 51), None, WHITE, 3.2)
    c.ellipse((37, 18.5, 46, 27.5), WHITE)
    c.poly((11, 49, 24, 31, 32, 41, 39, 34, 53, 49), WHITE)


def s_star(c):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = 25 if i % 2 == 0 else 10.5
        pts += [32 + r * math.cos(a), 34 + r * math.sin(a)]
    c.poly(pts, WHITE)


def s_gear(c):
    pts = []
    for i in range(32):
        a = i / 32 * 2 * math.pi
        r = 25 if (i % 4) in (1, 2) else 18.5
        pts += [32 + r * math.cos(a), 32 + r * math.sin(a)]
    c.poly(pts, WHITE)
    erase(c, lambda g: g.ellipse((24, 24, 40, 40), WHITE))


def s_wrench(c):
    c.line((44, 20, 15, 49), WHITE, 9)
    c.ellipse((9, 43, 21, 55), WHITE)
    c.ellipse((31, 3, 59, 31), WHITE)
    erase(c, lambda g: g.poly((41.5, 13.5, 48.5, 20.5, 62, 7, 55, 0), WHITE))


def s_chip(c):
    c.rrect((17, 17, 47, 47), 3, WHITE)
    erase(c, lambda g: g.rect((22.5, 22.5, 41.5, 41.5), WHITE))
    c.rect((26, 26, 38, 38), WHITE)
    for p in (22, 28, 36, 42):
        c.rect((p - 1.6, 9, p + 1.6, 17), WHITE)
        c.rect((p - 1.6, 47, p + 1.6, 55), WHITE)
        c.rect((9, p - 1.6, 17, p + 1.6), WHITE)
        c.rect((47, p - 1.6, 55, p + 1.6), WHITE)


def s_stack(c):
    c.ellipse((13, 8, 51, 22), WHITE)
    c.rect((13, 15, 51, 49), WHITE)
    c.ellipse((13, 42, 51, 56), WHITE)
    for y in (15, 26.5, 38):
        erase(c, lambda g, y=y: g.arc((13, y - 7 + 4.5, 51, y + 7 + 4.5), 0, 180, WHITE, 2.6))


def s_power(c):
    c.arc((13, 15, 51, 53), -55, 235, WHITE, 6.5)
    c.line((32, 8, 32, 31), WHITE, 6.5)
    c.ellipse((28.75, 4.75, 35.25, 11.25), WHITE)
    c.ellipse((28.75, 27.75, 35.25, 34.25), WHITE)


def s_plug(c):
    c.rrect((18, 22, 46, 42), 5, WHITE)
    c.rrect((23, 8, 29, 23), 1.5, WHITE)
    c.rrect((35, 8, 41, 23), 1.5, WHITE)
    c.line((32, 41, 32, 49, 40, 56), WHITE, 5.5)


def s_globe(c):
    c.ellipse((9, 9, 55, 55), None, WHITE, 4.2)
    c.ellipse((22, 9, 42, 55), None, WHITE, 3.2)
    c.line((32, 10, 32, 54), WHITE, 3.2)
    c.line((10, 32, 54, 32), WHITE, 3.2)
    c.line((13.5, 21, 50.5, 21), WHITE, 3)
    c.line((13.5, 43, 50.5, 43), WHITE, 3)


def s_book(c):
    c.poly((6, 15, 30, 19, 30, 53, 6, 49), WHITE)
    c.poly((34, 19, 58, 15, 58, 49, 34, 53), WHITE)
    for y in (26, 32.5, 39):
        erase(c, lambda g, y=y: g.line((10.5, y - 2, 25.5, y + 0.5), WHITE, 2.2))
        erase(c, lambda g, y=y: g.line((38.5, y + 0.5, 53.5, y - 2), WHITE, 2.2))


def s_window(c):
    c.rrect((7, 11, 57, 53), 3, None, WHITE, 4)
    c.rect((7, 11, 57, 22), WHITE)
    erase(c, lambda g: (g.rect((42, 14, 47, 19.5), WHITE), g.rect((50, 14, 55, 19.5), WHITE)))
    c.rect((13, 29, 39, 34), WHITE)
    c.rect((13, 40, 31, 45), WHITE)
    c.rect((44, 29, 51, 46), WHITE)


def s_warning(c):
    c.poly((32, 6, 59, 54, 5, 54), WHITE)
    erase(c, lambda g: g.poly((32, 15.5, 51.5, 49.5, 12.5, 49.5), WHITE))
    c.rrect((29.2, 22, 34.8, 38), 2.2, WHITE)
    c.ellipse((28.8, 41, 35.2, 47.4), WHITE)


def s_home(c):
    c.poly((32, 7, 58, 31, 51, 31, 51, 55, 13, 55, 13, 31, 6, 31), WHITE)
    erase(c, lambda g: g.rect((27, 39, 37, 55.5), WHITE))
    c.rect((41, 10, 47, 22), WHITE)


def text(c, t, box, path, axes=None, stretch=1.0):
    """t in white, fitted into box (64-space) and centred there; stretch: how much taller than the
    font's own shape the letters may become to fill the box (tall condensed letters read at 28px)"""
    n = c.im.size[0] / 64
    f = ImageFont.truetype(path, 400)
    if axes:
        f.set_variation_by_axes(axes)
    l, tp, r, b = f.getbbox(t)
    glyphs = Image.new("RGBA", (r - l, b - tp), (0, 0, 0, 0))
    ImageDraw.Draw(glyphs).text((-l, -tp), t, font=f, fill=WHITE)
    x0, y0, x1, y1 = (v * n for v in box)
    k = min((x1 - x0) / (r - l), (y1 - y0) / (b - tp))
    ky = min(k * stretch, (y1 - y0) / (b - tp))
    w, h = round((r - l) * k), round((b - tp) * ky)
    glyphs = glyphs.resize((w, h), Image.LANCZOS)
    c.im.alpha_composite(glyphs, (round((x0 + x1 - w) / 2), round((y0 + y1 - h) / 2)))


SANS = "/usr/share/fonts/truetype/ubuntu/UbuntuSans[wdth,wght].ttf"     # axes: width 75-100, weight 100-800
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"


def amiga_a(c, box):
    """the Amiga key's "A" (as on the stock OS 4.1 commodity keycaps): slanted, a thin left stroke, a thick
    right stroke, a thin crossbar, foot serifs; fitted into box (64-space)"""
    x0, y0, x1, y1 = box
    P = lambda pts: tuple(v for u, w in pts for v in (x0 + u * (x1 - x0), y0 + w * (y1 - y0)))
    for part in (((0.50, 0.0), (0.60, 0.0), (0.20, 0.95), (0.10, 0.95)),          # left stroke (thin)
                 ((0.46, 0.0), (0.68, 0.0), (0.88, 0.95), (0.62, 0.95)),          # right stroke (thick)
                 ((0.30, 0.60), (0.74, 0.60), (0.76, 0.70), (0.26, 0.70)),        # crossbar
                 ((0.36, 0.0), (0.68, 0.0), (0.68, 0.07), (0.36, 0.07)),          # top serif
                 ((0.0, 0.91), (0.32, 0.91), (0.32, 1.0), (0.0, 1.0)),            # left foot
                 ((0.54, 0.91), (1.0, 0.91), (1.0, 1.0), (0.54, 1.0))):           # right foot
        c.poly(P(part), WHITE)


def s_keycap(c):
    """a solid keycap with the Amiga key's "A" cut out of it"""
    c.rrect((6, 6, 58, 58), 9, WHITE)
    erase(c, lambda g: amiga_a(g, (15, 14, 49, 50)))


def s_presets(c):
    """a fan of three swatch cards on a pin: solid cards, a gap between them, a swatch window each"""
    px, py = 32, 50
    for k, a in enumerate((-36, 0, 36)):
        r = math.radians(a)

        def pt(x, y):
            return (px + x * math.cos(r) - y * math.sin(r), py + x * math.sin(r) + y * math.cos(r))
        card = sum([pt(-7, 5), pt(7, 5), pt(7, -40), pt(-7, -40)], ())
        erase(c, lambda g, cs=card: g.poly(cs, WHITE, WHITE, 6))
        c.poly(card, WHITE)
        win = sum([pt(-3.5, -36), pt(3.5, -36), pt(3.5, -27), pt(-3.5, -27)], ())
        erase(c, lambda g, w=win: g.poly(w, WHITE))
    erase(c, lambda g: g.ellipse((px - 4, py - 4, px + 4, py + 4), WHITE))


def s_document(c):
    """a laid-out page (pdf, PostScript): a picture block and lines of text"""
    c.poly((12, 5, 41, 5, 52, 16, 52, 59, 12, 59), None, WHITE, 3.4)
    c.poly((40, 5, 40, 17, 52, 17), WHITE)
    c.rect((18, 22, 46, 34), WHITE)
    for y in (40, 46.5, 53):
        c.rect((18, y, 46 if y < 50 else 36, y + 3), WHITE)


def s_video(c):
    """a strip of film with a play triangle"""
    c.rrect((5, 12, 59, 52), 3, WHITE)
    for x in range(9, 58, 9):
        erase(c, lambda g, x=x: (g.rect((x - 2.2, 15, x + 2.2, 19.5), WHITE), g.rect((x - 2.2, 44.5, x + 2.2, 49), WHITE)))
    erase(c, lambda g: g.poly((25, 23, 43, 32, 25, 41), WHITE))


def s_code(c):
    """a Shell prompt: a window with > and _"""
    c.rrect((5, 10, 59, 54), 4, None, WHITE, 3.4)
    c.line((15, 22, 27, 32, 15, 42), WHITE, 4.4)
    c.rect((31, 39.5, 47, 44), WHITE)


def s_font(c):
    text(c, "Aa", (6, 10, 58, 54), SERIF)


def letters(c, t):
    text(c, t, (5, 9, 59, 55) if len(t) > 2 else (9, 9, 55, 55), SANS, [75, 800], 1.7)


for _a in ARCHIVES:
    globals()["s_" + _a.lower()] = lambda c, t=_a: letters(c, t)


# --- sub-drawer symbols (2026-11-16): after the OS 4.1 icons (docs/iconsets/glass/reference/) ----------

def page(c, box, fold=7, filled=False, w=3.2):
    x0, y0, x1, y1 = box
    pts = (x0, y0, x1 - fold, y0, x1, y0 + fold, x1, y1, x0, y1)
    if filled:
        c.poly(pts, WHITE)
    else:
        c.poly(pts, None, WHITE, w)
    c.poly((x1 - fold, y0, x1 - fold, y0 + fold, x1, y0 + fold), WHITE)


def magnifier(c, cx, cy, r, w=4.2):
    c.ellipse((cx - r, cy - r, cx + r, cy + r), None, WHITE, w)
    a = math.radians(45)
    c.line((cx + (r + 1) * math.cos(a), cy + (r + 1) * math.sin(a), cx + (r + 12) * math.cos(a), cy + (r + 12) * math.sin(a)),
           WHITE, 6)


def s_amigs(c):
    page(c, (6, 3, 44, 50))
    text(c, "PS", (11, 11, 35, 27), SANS, [75, 800], 1.2)
    erase(c, lambda g: g.ellipse((28, 28, 56, 56), WHITE))
    magnifier(c, 42, 42, 10)


def s_amipdf(c):
    page(c, (6, 3, 44, 50))
    text(c, "PDF", (10, 11, 36, 27), SANS, [75, 800], 1.3)
    erase(c, lambda g: g.ellipse((28, 28, 56, 56), WHITE))
    magnifier(c, 42, 42, 10)


def s_printer(c):
    c.rect((18, 6, 46, 24), None, WHITE, 3)
    c.rrect((6, 22, 58, 46), 4, WHITE)
    erase(c, lambda g: g.rect((14, 37, 50, 41), WHITE))
    c.rect((18, 44, 46, 58), WHITE)
    erase(c, lambda g: (g.rect((22, 48, 42, 50), WHITE), g.rect((22, 53, 36, 55), WHITE)))
    c.ellipse((48, 27, 53, 32), None, None)


def s_camera(c):
    c.rrect((5, 18, 59, 54), 6, WHITE)
    c.rect((20, 11, 36, 19), WHITE)
    erase(c, lambda g: g.ellipse((19, 23, 45, 49), WHITE))
    c.ellipse((23, 27, 41, 45), None, WHITE, 3.5)
    c.ellipse((29, 33, 35, 39), WHITE)
    erase(c, lambda g: g.rect((47, 23, 54, 28), WHITE))


def s_amiupdate(c):
    pts = []
    for i in range(32):
        a = i / 32 * 2 * math.pi
        r = 27 if (i % 4) in (1, 2) else 20.5
        pts += [32 + r * math.cos(a), 32 + r * math.sin(a)]
    c.poly(pts, WHITE)
    erase(c, lambda g: g.ellipse((17, 17, 47, 47), WHITE))
    c.ellipse((21, 21, 43, 43), WHITE)


def s_python(c):
    """the Boing ball with a ring round its middle (the Python program's icon)"""
    c.ellipse((13, 13, 51, 51), WHITE)
    for i in range(6):
        for j in range(6):
            if (i + j) % 2:
                erase(c, lambda g, i=i, j=j: g.rect((13 + i * 6.4, 13 + j * 6.4, 19.4 + i * 6.4, 19.4 + j * 6.4), WHITE))
    c.ellipse((13, 13, 51, 51), None, WHITE, 3)
    erase(c, lambda g: g.ellipse((1, 25, 63, 43), None, WHITE, 8))
    c.ellipse((3, 27, 61, 41), None, WHITE, 3.5)


def s_blankers(c):
    c.rrect((6, 6, 58, 46), 5, None, WHITE, 4)
    c.poly((26, 46, 38, 46, 42, 56, 22, 56), WHITE)
    c.ellipse((19, 13, 39, 33), WHITE)
    erase(c, lambda g: g.ellipse((25, 10, 45, 30), WHITE))
    c.ellipse((44, 15, 47, 18), WHITE)
    c.ellipse((40, 30, 42, 32), WHITE)


def s_commodities(c):
    c.rrect((5, 8, 59, 54), 5, None, WHITE, 4)
    text(c, "CX", (13, 16, 51, 46), SANS, [75, 800], 1.2)


def s_dockies(c):
    c.ellipse((12, 4, 52, 44), None, WHITE, 4)
    c.ellipse((19, 11, 45, 37), WHITE)
    c.rrect((4, 49, 60, 58), 3, WHITE)


def pages(c):
    c.rect((20, 4, 50, 44), None, WHITE, 3)
    c.rect((12, 12, 42, 54), WHITE)
    for k in range(4):
        erase(c, lambda g, k=k: g.rect((17, 20 + k * 8, 37 - (k % 2) * 6, 23 + k * 8), WHITE))


def s_actionlogs(c):
    pages(c)
    erase(c, lambda g: g.poly((44, 26, 60, 26, 52, 40, 62, 40, 40, 63, 45, 46, 36, 46), WHITE))
    c.poly((46, 28, 57, 28, 50, 40, 59, 40, 42, 59, 46, 44, 39, 44), WHITE)


def s_connlogs(c):
    pages(c)
    erase(c, lambda g: g.rect((38, 30, 62, 62), WHITE))
    c.rect((42, 42, 58, 54), WHITE)
    c.rect((45, 34, 48, 42), WHITE)
    c.rect((52, 34, 55, 42), WHITE)
    c.line((50, 54, 50, 62), WHITE, 3)


def rj45_plug(c, x0, y0):
    c.rect((x0, y0 + 10, x0 + 30, y0 + 40), WHITE)
    c.rect((x0 + 10, y0, x0 + 20, y0 + 10), WHITE)
    for k in range(6):
        erase(c, lambda g, k=k: g.rect((x0 + 4 + k * 4, y0 + 12, x0 + 6 + k * 4, y0 + 20), WHITE))


def s_connections(c):
    rj45_plug(c, 17, 4)
    c.line((32, 44, 32, 52, 46, 58), WHITE, 4)


def s_reports(c):
    c.line((8, 6, 8, 56, 58, 56), WHITE, 3.5)
    for k, h in enumerate((18, 34, 26, 44)):
        c.rect((14 + k * 11, 52 - h, 22 + k * 11, 52), WHITE)


def s_templates(c):
    for k in range(7):
        c.line((12, 6 + k * 7.4, 12, 9.5 + k * 7.4), WHITE, 3)
        c.line((50, 6 + k * 7.4, 50, 9.5 + k * 7.4), WHITE, 3)
    for k in range(6):
        c.line((14 + k * 6.4, 6, 17.5 + k * 6.4, 6), WHITE, 3)
        c.line((14 + k * 6.4, 58, 17.5 + k * 6.4, 58), WHITE, 3)
    c.rect((29, 20, 33, 44), WHITE)
    c.rect((19, 30, 43, 34), WHITE)


def floppy(c, x0, y0, s=48):
    k = s / 48
    c.poly((x0, y0, x0 + 42 * k, y0, x0 + 48 * k, y0 + 6 * k, x0 + 48 * k, y0 + 48 * k, x0, y0 + 48 * k), WHITE)
    erase(c, lambda g: g.rect((x0 + 12 * k, y0, x0 + 36 * k, y0 + 16 * k), WHITE))
    c.rect((x0 + 26 * k, y0 + 3 * k, x0 + 32 * k, y0 + 13 * k), WHITE)
    erase(c, lambda g: g.rect((x0 + 9 * k, y0 + 25 * k, x0 + 39 * k, y0 + 43 * k), WHITE))     # the label, framed


def s_dosdrivers(c):
    floppy(c, 8, 8)


def s_amigadisks(c):
    c.poly((18, 4, 52, 4, 58, 10, 58, 44, 18, 44), None, WHITE, 3)
    floppy(c, 6, 18, 40)


def s_amigaroms(c):
    c.rect((18, 6, 46, 58), WHITE)
    erase(c, lambda g: g.ellipse((27, 1, 37, 11), WHITE))
    for k in range(6):
        c.rect((10, 10 + k * 8, 18, 13 + k * 8), WHITE)
        c.rect((46, 10 + k * 8, 54, 13 + k * 8), WHITE)
    erase(c, lambda g: g.rect((24, 22, 40, 26), WHITE))
    erase(c, lambda g: g.rect((24, 30, 34, 34), WHITE))


def s_muidemos(c):
    c.rrect((5, 8, 59, 56), 4, None, WHITE, 3.5)
    c.rect((5, 8, 59, 19), WHITE)
    c.poly((25, 26, 43, 37, 25, 48), WHITE)


def s_muiicons(c):
    for k, (x, y) in enumerate(((6, 6), (34, 6), (6, 34), (34, 34))):
        if k % 3 == 0:
            c.rrect((x, y, x + 24, y + 24), 5, WHITE)
        else:
            c.rrect((x, y, x + 24, y + 24), 5, None, WHITE, 3.5)


def s_muilibs(c):
    for k, x in enumerate((8, 20, 32)):
        c.rect((x, 10, x + 10, 56), WHITE)
        erase(c, lambda g, x=x: (g.rect((x + 2, 16, x + 8, 19), WHITE), g.rect((x + 2, 46, x + 8, 49), WHITE)))
    c.poly((44, 14, 54, 11, 60, 54, 50, 57), WHITE)


def s_muipatterns(c):
    c.rect((6, 6, 58, 58), None, WHITE, 3)
    for i in range(4):
        for j in range(4):
            if (i + j) % 2 == 0:
                c.rect((10 + i * 11.2, 10 + j * 11.2, 21.2 + i * 11.2, 21.2 + j * 11.2), WHITE)


def s_crown(c):
    c.poly((6, 22, 18, 34, 32, 12, 46, 34, 58, 22, 54, 48, 10, 48), WHITE)
    c.rect((10, 50, 54, 57), WHITE)
    for x, y in ((6, 20), (32, 10), (58, 20)):
        c.ellipse((x - 4, y - 4, x + 4, y + 4), WHITE)
    erase(c, lambda g: (g.ellipse((19, 38, 25, 44), WHITE), g.ellipse((29, 37, 35, 43), WHITE), g.ellipse((39, 38, 45, 44), WHITE)))


def s_datatypes(c):
    c.ellipse((6, 6, 44, 44), None, WHITE, 4)
    c.line((40, 40, 56, 56), WHITE, 7)
    c.ellipse((14, 14, 23, 23), WHITE)
    c.rect((26, 14, 35, 23), WHITE)
    c.poly((19, 36, 24, 26, 29, 36), WHITE)


def s_keymaps(c):
    c.rrect((6, 6, 58, 58), 7, None, WHITE, 4)
    c.rrect((13, 13, 51, 46), 4, None, WHITE, 2)
    text(c, "A", (20, 15, 44, 42), SANS, [100, 800])


def s_monitors(c):
    c.rrect((5, 6, 59, 44), 3, None, WHITE, 4)
    c.rect((12, 13, 52, 37), WHITE)
    c.rect((28, 44, 36, 52), WHITE)
    c.rect((16, 52, 48, 57), WHITE)


def s_netif(c):
    c.rect((10, 8, 54, 56), None, WHITE, 4)
    c.poly((16, 16, 48, 16, 48, 40, 40, 40, 40, 48, 24, 48, 24, 40, 16, 40), WHITE)
    for k in range(6):
        erase(c, lambda g, k=k: g.rect((20 + k * 4.4, 18, 22 + k * 4.4, 28), WHITE))


def s_amissl(c):
    c.arc((18, 4, 46, 34), 180, 360, WHITE, 5)
    c.line((18.5, 19, 18.5, 30), WHITE, 5)
    c.line((45.5, 19, 45.5, 30), WHITE, 5)
    c.rrect((10, 28, 54, 60), 5, WHITE)
    erase(c, lambda g: (g.ellipse((27, 36, 37, 46), WHITE), g.rect((30, 42, 34, 53), WHITE)))


def s_plus(c):
    """New Connection: a bold plus"""
    c.rrect((26, 6, 38, 58), 3, WHITE)
    c.rrect((6, 26, 58, 38), 3, WHITE)


def s_pencil(c):
    """Edit Connection: a pencil, writing down to the left"""
    r = math.radians(45)

    def pt(x, y):
        return (32 + x * math.cos(r) - y * math.sin(r), 32 + x * math.sin(r) + y * math.cos(r))
    body = sum([pt(-7, -30), pt(7, -30), pt(7, 14), pt(-7, 14)], ())
    c.poly(body, WHITE)
    erase(c, lambda g: g.poly(sum([pt(-8, -22), pt(8, -22), pt(8, -19), pt(-8, -19)], ()), WHITE))
    c.poly(sum([pt(-7, 17), pt(7, 17), pt(0, 31)], ()), WHITE)
    erase(c, lambda g: g.poly(sum([pt(-2.5, 26), pt(2.5, 26), pt(0, 32)], ()), WHITE))


# the "do" icons (2026-11-21): Presets sub-drawers, reviewed one by one; variants until picked
def s_dock(c):
    """Presets/AmiDock (DO01, user picked variant A 2026-11-21): a dock bar lying flat with three icons in it"""
    c.rrect((4, 18, 60, 46), 5, None, WHITE, 4)
    for x in (11, 26, 41):
        c.rrect((x, 24, x + 12, 40), 2, WHITE)


def s_default(c):
    """Presets/Default (DO02, user picked variant B 2026-11-21): a monitor showing a window (the GUI look
    for each screen size)"""
    c.rrect((4, 6, 60, 46), 4, None, WHITE, 4)
    c.rect((14, 15, 50, 37), WHITE)
    erase(c, lambda g: g.rect((17, 22, 47, 34), WHITE))
    c.rect((28, 46, 36, 54), WHITE)
    c.rrect((16, 53, 48, 59), 2, WHITE)


def arrow(c, x, y, k=1.0, gap=0):
    """a mouse pointer arrow, tip at x, y; gap: cut a margin around it first (when it lies on another)"""
    pts = [(0, 0), (0, 36), (9, 28), (15, 42), (21, 39), (15, 26), (27, 26)]
    pts = sum([(x + px * k, y + py * k) for px, py in pts], ())
    if gap:
        erase(c, lambda g: g.poly(pts, WHITE, WHITE, gap))
    c.poly(pts, WHITE)


def s_pointers(c):
    """Presets/Pointers (DO04, user picked variant A 2026-11-21): the mouse pointer arrow"""
    arrow(c, 18, 9)


def brush(c, x, y, gap=5):
    """a paint brush, bristles down left at x, y, handle up right"""
    r = math.radians(-45)

    def pt(px, py):
        return (x + px * math.cos(r) - py * math.sin(r), y + px * math.sin(r) + py * math.cos(r))
    handle = sum([pt(14, -3), pt(40, -2.5), pt(40, 2.5), pt(14, 3)], ())
    head = sum([pt(0, -5), pt(14, -5), pt(14, 5), pt(0, 5)], ())
    tip = sum([pt(-7, 0), pt(0, -5), pt(0, 5)], ())
    for part in (handle, head, tip):
        erase(c, lambda g, p=part: g.poly(p, WHITE, WHITE, gap))
    for part in (handle, head, tip):
        c.poly(part, WHITE)


def s_silvergreen(c):
    """Presets/SilverGreen, a theme (DO05, user picked variant A 2026-11-21): Default's monitor with a
    paint brush (a look restyled)"""
    s_default(c)
    brush(c, 30, 34)


def speaker(c, x=0, waves=2):
    c.poly((x + 6, 24, x + 16, 24, x + 30, 10, x + 30, 54, x + 16, 40, x + 6, 40), WHITE)
    for k in range(waves):
        r = 12 + k * 10
        pts = []
        for t in range(-50, 51, 10):
            a = math.radians(t)
            pts += [x + 30 + r * math.cos(a), 32 + r * math.sin(a)]
        c.line(tuple(pts), WHITE, 4)


def s_sounds(c):
    """Presets/Sounds (DO06, user picked variant C 2026-11-21): a waveform"""
    pts = []
    for i in range(57):  # 4 wave periods
        x = 4 + i
        env = math.sin(math.pi * i / 56)
        pts += [x, 32 - 22 * env * math.sin(i * 0.45)]
    c.line(tuple(pts), WHITE, 4)


def s_pylib(c):
    """System/Python/Lib (DO07, user picked variant C 2026-11-21): the letters py"""
    text(c, "py", (10, 10, 54, 54), SANS, [75, 800], 1.2)


# the sub-drawers with icons of their own (docs/iconset_inventory.md): (parent, drawer, tile, symbol); the
# colour is the parent drawer's (the user, 2026-11-16)
PARENT_COLOUR = {"SYS:Utilities": VIOLET, "SYS:System": RED, "SYS:Internet": BLUE, "SYS:Emulation": GREEN,
                 "SYS:MUI": BLUE, "SYS:Storage": GREEN, "SYS:Devs": VIOLET, "SYS:Documentation": VIOLET,
                 "SYS:Prefs": BLUE}
SUBDRAWERS = [
    ("SYS:Prefs", "Presets", "EmPresets", "presets"),
    ("SYS:Utilities", "AmiGS", "SdAmiGS", "amigs"),
    ("SYS:Utilities", "AmiPDF", "SdAmiPDF", "amipdf"),
    ("SYS:Utilities", "Blankers", "SdBlankers", "blankers"),
    ("SYS:Utilities", "Commodities", "SdCommodities", "commodities"),
    ("SYS:Utilities", "Dockies", "SdDockies", "dockies"),
    ("SYS:Utilities", "Ghostscript", "SdPrinterV", "printer"),
    ("SYS:Utilities", "SGrab", "SdSGrab", "camera"),
    ("SYS:System", "AmiUpdate", "SdAmiUpdate", "amiupdate"),
    ("SYS:System", "Python", "SdPython", "python"),
    ("SYS:Internet", "Action logs", "SdActionLogs", "actionlogs"),
    ("SYS:Internet", "Connection logs", "SdConnLogs", "connlogs"),
    ("SYS:Internet", "Connections", "SdConnections", "connections"),
    ("SYS:Internet", "Reports", "SdReports", "reports"),
    ("SYS:Internet", "Templates", "SdTemplates", "templates"),
    ("SYS:Emulation", "AmigaDisks", "SdAmigaDisks", "amigadisks"),
    ("SYS:Emulation", "AmigaROMs", "SdAmigaROMs", "amigaroms"),
    ("SYS:MUI", "Demos", "SdMuiDemos", "muidemos"),
    ("SYS:MUI", "Docs", "SdMuiDocs", "book"),
    ("SYS:MUI", "Icons", "SdMuiIcons", "muiicons"),
    ("SYS:MUI", "Images", "EmPicture", "picture"),
    ("SYS:MUI", "Libs", "SdMuiLibs", "muilibs"),
    ("SYS:MUI", "Patterns", "SdMuiPatterns", "muipatterns"),
    ("SYS:MUI", "Presets", "EmPresets", "presets"),
    ("SYS:MUI", "Rexx", "SdMuiRexx", "crown"),
] + [(p, n, ("SdSt" if p == "SYS:Storage" else "SdDv") + t, sym) for p in ("SYS:Storage", "SYS:Devs")
     for n, t, sym in (("Datatypes" if p == "SYS:Storage" else "DataTypes", "Datatypes", "datatypes"),
                       ("DOSDrivers", "DOSDrivers", "dosdrivers"), ("KeyMaps", "KeyMaps", "keymaps"),
                       ("Monitors", "Monitors", "monitors"), ("NetInterfaces", "NetIf", "netif"),
                       ("Printers", "Printers", "printer"))] + [
    ("SYS:Documentation", "AmiSSL", "SdAmiSSL", "amissl"),
]
# program drawers (approved 2026-11-16): no tile, a glass version of the program's own icon
# (tools/blender/glass_emblems.py, rendered as build/glass/emb/Ep_<name>.png)
PROGRAM_EMBLEMS = {"AmiGS": "Ep_amigs", "AmiPDF": "Ep_amipdf", "Ghostscript": "Ep_ghostscript", "SGrab": "Ep_sgrab",
                   "AmiUpdate": "Ep_amiupdate", "Python": "Ep_python"}
SUBDRAWERS = [(p, n, PROGRAM_EMBLEMS.get(n, t), sym) for p, n, t, sym in SUBDRAWERS]
for _p, _n, _t, _sym in SUBDRAWERS:
    if not _t.startswith("Ep_"):
        TILES.setdefault(_t, (_sym, PARENT_COLOUR[_p]))


SYMBOLS = {k[2:]: v for k, v in globals().items() if k.startswith("s_")}


def main():
    out = sys.argv[1]
    names = sys.argv[2:] or list(SYMBOLS)
    os.makedirs(out, exist_ok=True)
    for n in names:
        c = G(64)
        SYMBOLS[n](c)
        c.im.save(os.path.join(out, n + ".png"))
    print(len(names), "symbols ->", out)


if __name__ == "__main__":
    main()
