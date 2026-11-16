#!/home/claude/build/emblem-venv/bin/python
"""make_iconsets.py OUTDIR

Five concept icon sets for Emblem (sci-fi / game inspired). The base images
are drawn with light blue, white and black only (blended into gradients,
glosses and shadows), thin lines, and drawers (not folders); the emblems are
colourful. Every set has the same ten preview icons, composed with the
Emblem engine (build/host/render):

  01 drawer            02 drawer, selected (open)   03 drawer + music emblem
  04 drawer + games    05 file                      06 file + picture emblem
  07 device (disk)     08 archive                   09 preferences
  10 tool (program)

Writes OUTDIR/T<n>/<name>.png (base images and emblems), OUTDIR/T<n>.png
(the preview sheet of set n) and OUTDIR/overview.png (all sets).
Public domain.
"""
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENDER = os.path.join(ROOT, "build", "host", "render")
SS = 8

# --- the base palette: light blue (hue 210, not cyan), white, black, and blends of them ---


def mix(a, b, f):
    return tuple(round(a[i] + (b[i] - a[i]) * f) for i in range(3)) + (a[3] if len(a) > 3 else 255,)


BLUE = (148, 194, 240, 255)
WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)
BLUE2 = mix(BLUE, WHITE, 0.55)        # pale
BLUE3 = mix(BLUE, BLACK, 0.18)        # shaded
DEEP = mix(BLUE, BLACK, 0.36)         # deep shade
NONE = (0, 0, 0, 0)

LW = 1.1       # outline width (pixels at 64x64)
FW = 0.75      # fine detail lines


def rgba(c, a):
    return c[:3] + (a,)


def lighten(c, f):
    return mix(c, WHITE, f)


def darken(c, f):
    return mix(c, BLACK, f)


# emblem colours
MAGENTA = (232, 50, 168, 255)
ORANGE = (252, 142, 28, 255)
GREEN = (40, 186, 92, 255)
YELLOW = (255, 214, 50, 255)
RED = (232, 52, 64, 255)
PURPLE = (142, 82, 226, 255)
SKY = (96, 182, 250, 255)


# --- gradients ---------------------------------------------------------------------------

_grid = {}


def grid(n):
    if n not in _grid:
        yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
        _grid[n] = ((xx + 0.5) / SS, (yy + 0.5) / SS)
    return _grid[n]


def _stops(stops):
    """colours spread evenly, or explicit (t, colour) pairs"""
    if all(len(s) == 2 for s in stops):
        return list(stops)
    n = len(stops)
    return [(i / (n - 1), s) for i, s in enumerate(stops)]


def _interp(stops, t):
    ts = [s[0] for s in stops]
    out = np.empty(t.shape + (4,), np.float32)
    for ch in range(4):
        out[..., ch] = np.interp(t, ts, [s[1][ch] for s in stops])
    return out


class Lin:
    """linear gradient from (x0, y0) to (x1, y1) (icon pixels); stops: colours or (t, colour)"""

    def __init__(self, x0, y0, x1, y1, *stops):
        self.a, self.b, self.stops = (x0, y0), (x1, y1), _stops(stops)

    def render(self, n):
        xx, yy = grid(n)
        dx, dy = self.b[0] - self.a[0], self.b[1] - self.a[1]
        t = ((xx - self.a[0]) * dx + (yy - self.a[1]) * dy) / (dx * dx + dy * dy)
        return _interp(self.stops, np.clip(t, 0, 1))


class Rad:
    """radial (elliptic) gradient around (cx, cy)"""

    def __init__(self, cx, cy, rx, ry, *stops):
        self.c, self.r, self.stops = (cx, cy), (rx, ry), _stops(stops)

    def render(self, n):
        xx, yy = grid(n)
        t = np.sqrt(((xx - self.c[0]) / self.r[0]) ** 2 + ((yy - self.c[1]) / self.r[1]) ** 2)
        return _interp(self.stops, np.clip(t, 0, 1))


def V(y0, y1, *stops):
    return Lin(0, y0, 0, y1, *stops)


def H(x0, x1, *stops):
    return Lin(x0, 0, x1, 0, *stops)


def gloss(y0, y1, a=170):
    """glass-like shine: bright at the top, still visible at its lower edge"""
    return V(y0, y1, rgba(WHITE, a), rgba(WHITE, round(a * 0.3)))


# --- the canvas ----------------------------------------------------------------------------

class G:
    """drawn SS times larger; coordinates in final pixels; fills may be colours or gradients"""

    def __init__(self, size):
        self.size, self.n = size, size * SS
        self.im = Image.new("RGBA", (self.n, self.n), NONE)

    def p(self, *v):
        return [x * SS for x in v]

    def _new(self):
        return Image.new("RGBA", (self.n, self.n), NONE)

    def mask(self, shape):
        m = Image.new("L", (self.n, self.n), 0)
        self._draw(ImageDraw.Draw(m), shape, fill=255)
        return m

    def _draw(self, d, shape, fill=None, outline=None, width=0):
        k = shape[0]
        if k == "poly":
            if fill is not None:
                d.polygon(self.p(*shape[1]), fill=fill)
            if outline is not None:
                pts = list(shape[1])
                d.line(self.p(*pts, pts[0], pts[1]), fill=outline, width=width, joint="curve")
        elif k == "rrect":
            d.rounded_rectangle(self.p(*shape[1]), radius=round(shape[2] * SS), fill=fill,
                                outline=outline, width=width)
        elif k == "ellipse":
            d.ellipse(self.p(*shape[1]), fill=fill, outline=outline, width=width)
        elif k == "rect":
            d.rectangle(self.p(*shape[1]), fill=fill, outline=outline, width=width)

    def paint(self, m, fill):
        if isinstance(fill, tuple):
            layer = Image.new("RGBA", (self.n, self.n), fill)
            a = np.asarray(m, np.float32) * (fill[3] / 255.0)
            layer.putalpha(Image.fromarray(a.astype(np.uint8), "L"))
        else:
            src = fill.render(self.n)
            src[..., 3] *= np.asarray(m, np.float32) / 255.0
            layer = Image.fromarray(np.clip(src, 0, 255).astype(np.uint8), "RGBA")
        self.im.alpha_composite(layer)

    def shape(self, shape, fill=None, outline=None, width=LW):
        if fill is not None:
            self.paint(self.mask(shape), fill)
        if outline is not None:
            layer = self._new()
            self._draw(ImageDraw.Draw(layer), shape, outline=outline, width=max(1, round(width * SS)))
            self.im.alpha_composite(layer)

    # shorthands (outline only when given)
    def poly(self, pts, fill=None, outline=None, width=LW):
        self.shape(("poly", tuple(pts)), fill, outline, width)

    def rrect(self, box, r, fill=None, outline=None, width=LW):
        self.shape(("rrect", tuple(box), r), fill, outline, width)

    def ellipse(self, box, fill=None, outline=None, width=LW):
        self.shape(("ellipse", tuple(box)), fill, outline, width)

    def rect(self, box, fill=None, outline=None, width=LW):
        self.shape(("rect", tuple(box)), fill, outline, width)

    def line(self, pts, fill, width=FW):
        layer = self._new()
        ImageDraw.Draw(layer).line(self.p(*pts), fill=fill, width=max(1, round(width * SS)), joint="curve")
        self.im.alpha_composite(layer)

    def arc(self, box, a0, a1, fill, width=FW):
        layer = self._new()
        ImageDraw.Draw(layer).arc(self.p(*box), a0, a1, fill=fill, width=max(1, round(width * SS)))
        self.im.alpha_composite(layer)

    # effects
    def _blurred(self, alpha_img, blur, dx=0, dy=0):
        if dx or dy:
            moved = Image.new("L", alpha_img.size, 0)
            moved.paste(alpha_img, (round(dx * SS), round(dy * SS)))
            alpha_img = moved
        return alpha_img.filter(ImageFilter.GaussianBlur(blur * SS)) if blur else alpha_img

    def _colour_layer(self, alpha, colour, opacity):
        layer = Image.new("RGBA", (self.n, self.n), colour[:3] + (0,))
        a = np.asarray(alpha, np.float32) * opacity
        layer.putalpha(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "L"))
        return layer

    def ground(self, cx, cy, rx, ry, opacity=0.45, blur=2.2, colour=BLACK):
        """a soft shadow (or glow) on the ground, drawn before the object"""
        m = Image.new("L", (self.n, self.n), 0)
        ImageDraw.Draw(m).ellipse(self.p(cx - rx, cy - ry, cx + rx, cy + ry), fill=255)
        self.im.alpha_composite(self._colour_layer(self._blurred(m, blur), colour, opacity))

    def inner_shadow(self, shape, dx=0.0, dy=1.2, blur=1.2, opacity=0.55, colour=BLACK):
        """darkens the inside of a shape near its top (a recess)"""
        m = self.mask(shape)
        inv = Image.eval(m, lambda v: 255 - v)
        s = np.asarray(self._blurred(inv, blur, dx, dy), np.float32) * (np.asarray(m, np.float32) / 255.0)
        self.im.alpha_composite(self._colour_layer(Image.fromarray(s.astype(np.uint8), "L"), colour, opacity))

    def glow(self, draw, colour, blur=1.5, opacity=0.9):
        """draw(g) draws onto a fresh canvas; its shape is blurred in colour onto this one"""
        g = G(self.size)
        draw(g)
        self.im.alpha_composite(self._colour_layer(self._blurred(g.im.getchannel("A"), blur), colour, opacity))

    def done(self, shadow=None, halo=None):
        """shadow = (dx, dy, blur, opacity): a drop shadow of the whole picture;
        halo = (colour, blur, opacity): a glow round it"""
        im = self.im
        a = im.getchannel("A")
        out = self._new()
        if halo:
            out.alpha_composite(self._colour_layer(self._blurred(a, halo[1]), halo[0], halo[2]))
        if shadow:
            out.alpha_composite(self._colour_layer(self._blurred(a, shadow[2], shadow[0], shadow[1]), BLACK, shadow[3]))
        out.alpha_composite(im)
        return out.resize((self.size, self.size), Image.BOX)


# --- shared shapes and symbols -------------------------------------------------------------

def dashed(c, x0, y0, x1, y1, fill, width=FW, dash=2.0, gap=1.5):
    n = math.hypot(x1 - x0, y1 - y0)
    if n == 0:
        return
    ux, uy, t = (x1 - x0) / n, (y1 - y0) / n, 0.0
    while t < n:
        e = min(t + dash, n)
        c.line((x0 + ux * t, y0 + uy * t, x0 + ux * e, y0 + uy * e), fill, width)
        t = e + gap


def chamfer(x0, y0, x1, y1, a, b=None):
    b = a if b is None else b
    return (x0 + a, y0, x1, y0, x1, y1 - b, x1 - b, y1, x0, y1, x0, y0 + a)


def chamfer4(x0, y0, x1, y1, a):
    return (x0 + a, y0, x1 - a, y0, x1, y0 + a, x1, y1 - a, x1 - a, y1, x0 + a, y1, x0, y1 - a, x0, y0 + a)


def hexagon(cx, cy, r, rot=0.0):
    pts = []
    for i in range(6):
        a = math.radians(60 * i + rot)
        pts += [cx + r * math.cos(a), cy + r * math.sin(a)]
    return pts


def note(c, x, y, k, fill):
    P = lambda *v: [x + v[i] * k if i % 2 == 0 else y + v[i] * k for i in range(len(v))]
    c.poly(P(5, 2, 17, 0, 17, 3.5, 5, 5.5), fill)
    c.rect(P(4.6, 3, 6.4, 16), fill)
    c.rect(P(15.6, 1, 17.4, 14), fill)
    c.ellipse(P(0, 13.5, 6.4, 18.5), fill)
    c.ellipse(P(11, 11.5, 17.4, 16.5), fill)


def joystick(c, x, y, k, base, knob, stick, button=RED):
    P = lambda *v: [x + v[i] * k if i % 2 == 0 else y + v[i] * k for i in range(len(v))]
    c.rrect(P(1, 13, 19, 19), 2.5 * k, base)
    c.line(P(10, 14, 8.5, 5), stick, 2.0 * k)
    c.ellipse(P(4.5, 0, 12.5, 8), knob)
    c.ellipse(P(14, 14.5, 17, 17.5), button)


def symbol_shadow(c, fn, colour):
    """draw a symbol with a soft dark shadow under it"""
    c.glow(lambda g: fn(g, BLACK), BLACK, 0.7, 0.35)
    fn(c, colour)


def badge_fill(x0, y0, x1, y1, colour):
    w, h = x1 - x0, y1 - y0
    return Rad(x0 + w * 0.38, y0 + h * 0.3, w * 0.75, h * 0.75, lighten(colour, 0.45), colour, darken(colour, 0.3))


def badge_gloss(c, x0, y0, x1, y1):
    w, h = x1 - x0, y1 - y0
    c.ellipse((x0 + w * .16, y0 + h * .06, x1 - w * .16, y0 + h * .52), gloss(y0 + h * .06, y0 + h * .52, 150))


# =========================================================================================
# T1 Cargo Bay: glossy starship lockers
# =========================================================================================

class Cargo:
    name = "Cargo Bay"
    blurb = "glossy starship lockers: hull panels, rivets, glowing light strips"
    emblem_at = "26,26,36,35"
    SH = (0.8, 1.4, 1.1, 0.35)    # drop shadow of every base image

    def rivets(self, c, pts):
        for x, y in pts:
            c.ellipse((x - 1.1, y - 1.1, x + 1.1, y + 1.1), Rad(x - .4, y - .4, 1.5, 1.5, WHITE, BLUE3), BLACK, 0.5)

    def light(self, c, x0, x1, y):
        c.glow(lambda g: g.line((x0, y, x1, y), WHITE, 1.6), BLUE, 1.3, 1.0)
        c.line((x0, y, x1, y), WHITE, 1.3)

    def front(self, c, box, r=3):
        x0, y0, x1, y1 = box
        c.rrect(box, r, V(y0, y1, BLUE2, BLUE, BLUE3, DEEP), BLACK, LW)
        c.rrect((x0 + 1.2, y0 + 1.2, x1 - 1.2, y0 + (y1 - y0) * .42), r - 1, gloss(y0, y0 + (y1 - y0) * .45, 170))
        c.line((x0 + r, y0 + 1.1, x1 - r, y0 + 1.1), rgba(WHITE, 230), 0.7)

    def handle(self, c, box):
        c.rrect(box, 2.4, V(box[1], box[3], DEEP, BLUE3), BLACK, FW)
        c.inner_shadow(("rrect", box, 2.4), dy=0.9, blur=0.7, opacity=0.6)
        c.line((box[0] + 1.5, box[3] + 0.9, box[2] - 1.5, box[3] + 0.9), rgba(WHITE, 220), 0.8)

    def top(self, c, y):
        c.poly((11, y, 53, y, 59, y + 7, 5, y + 7), V(y, y + 7, WHITE, BLUE2), BLACK, LW)

    def body(self, c, box):
        c.rrect(box, 4.5, V(box[1], box[3], WHITE, BLUE2, mix(BLUE2, BLUE, .5)), BLACK, LW)
        c.line((box[0] + 4.5, box[1] + 1.1, box[2] - 4.5, box[1] + 1.1), WHITE, 0.7)

    def drawer(self):
        c = G(64)
        c.ground(32, 57.5, 27, 2.6, 0.4)
        self.top(c, 8)
        self.body(c, (5, 15, 59, 56))
        self.front(c, (9.5, 20.5, 54.5, 51.5))
        self.handle(c, (23, 26.5, 41, 31.5))
        self.light(c, 14, 26, 46.5)
        self.rivets(c, [(7.9, 18), (56.1, 18), (7.9, 53.2), (56.1, 53.2)])
        return c.done(self.SH)

    def drawer_open(self):
        c = G(64)
        c.ground(32, 60, 28, 2.5, 0.4)
        self.top(c, 2)
        self.body(c, (5, 9, 59, 42))
        bay = (9.5, 13, 54.5, 36)
        c.rrect(bay, 3, V(13, 36, DEEP, BLUE3, BLUE), BLACK, FW)
        c.inner_shadow(("rrect", bay, 3), dy=2, blur=1.6, opacity=0.6)
        c.poly((9.5, 30, 54.5, 30, 58, 40, 6, 40), V(30, 40, BLUE2, WHITE), BLACK, FW)
        for x in (16, 23, 30, 37):
            c.rrect((x, 22, x + 5, 35), 1, V(22, 35, WHITE, BLUE), BLACK, FW)
        self.front(c, (4.5, 39, 59.5, 59))
        self.handle(c, (23, 44, 41, 49))
        self.rivets(c, [(7.9, 12), (56.1, 12)])
        return c.done(self.SH)

    def file(self):
        c = G(64)
        c.ground(33, 59, 16, 2, 0.35)
        c.rrect((15, 4, 49, 59), 5, V(4, 59, WHITE, BLUE2), BLACK, LW)
        scr = (19.5, 10, 44.5, 47)
        c.rrect(scr, 2, V(10, 47, BLUE, BLUE3, DEEP), BLACK, FW)
        for y, x1 in ((16, 40), (21, 40), (26, 40), (31, 34)):
            c.glow(lambda g, y=y, x1=x1: g.line((23.5, y, x1, y), WHITE, 1.4), WHITE, 0.8, 0.6)
            c.line((23.5, y, x1, y), WHITE, 1.2)
        c.poly((20.5, 11, 36, 11, 20.5, 32), Lin(20, 11, 30, 22, rgba(WHITE, 110), rgba(WHITE, 0)))
        c.ellipse((29.5, 50.5, 34.5, 55.5), Rad(31.2, 52, 3.5, 3.5, WHITE, BLUE), BLACK, FW)
        return c.done(self.SH)

    def device(self):
        c = G(64)
        c.ground(32, 52, 27, 2.6, 0.4)
        c.rrect((5, 16, 59, 49), 5, V(16, 49, WHITE, BLUE2), None)
        c.rrect((5.4, 38, 58.6, 48.6), 4.5, V(38, 49, BLUE, BLUE3))
        c.rect((5.4, 38, 58.6, 41), V(38, 41, BLUE, BLUE))
        c.line((5.5, 38, 58.5, 38), BLACK, FW)
        c.rrect((5, 16, 59, 49), 5, None, BLACK, LW)
        c.rrect((5.8, 16.8, 58.2, 26), 4.2, gloss(17, 27, 160))
        slot = (11, 24, 35, 28)
        c.rrect(slot, 1.5, V(24, 28, DEEP, BLUE3), BLACK, FW)
        c.inner_shadow(("rrect", slot, 1.5), dy=0.8, blur=0.6, opacity=0.6)
        for x in (11, 14.5, 18):
            c.line((x, 32, x, 35), BLACK, FW)
        c.glow(lambda g: g.ellipse((42, 21, 53, 32), WHITE), BLUE, 1.6, 1.0)
        c.ellipse((42, 21, 53, 32), Rad(47.5, 26.5, 5.5, 5.5, WHITE, BLUE2, BLUE), BLACK, LW)
        c.ellipse((45.5, 24.5, 49.5, 28.5), WHITE)
        self.light(c, 40, 54, 44)
        return c.done(self.SH)

    def archive(self):
        c = G(64)
        c.ground(32, 58, 27, 2.6, 0.45)
        c.rrect((7, 15, 57, 57), 3, V(15, 57, BLUE2, BLUE, BLUE3), BLACK, LW)
        c.rrect((7, 15, 57, 24), 3, V(15, 24, WHITE, BLUE2), BLACK, LW)
        for x in (17, 41):
            c.rect((x, 15.6, x + 6, 56.4), H(x, x + 6, BLUE2, WHITE, BLUE2))
            c.line((x, 16, x, 56), BLACK, FW)
            c.line((x + 6, 16, x + 6, 56), BLACK, FW)
        c.rrect((7.8, 24.8, 56.2, 34), 2, gloss(25, 34, 90))
        c.rrect((27, 30, 37, 41), 1.5, Rad(30, 32, 7, 8, WHITE, BLUE2, BLUE), BLACK, FW)
        c.ellipse((30.6, 33, 33.4, 35.8), BLACK)
        c.rect((31.5, 35, 32.5, 38.5), BLACK)
        return c.done(self.SH)

    def prefs(self):
        c = G(64)
        c.ground(32, 58, 26, 2.5, 0.4)
        c.rrect((5, 6, 59, 57), 6, V(6, 57, WHITE, BLUE2), BLACK, LW)
        c.rrect((6, 7, 58, 24), 5, gloss(7, 24, 120))
        for y, kx in ((18, 22), (29, 40)):
            c.line((12, y, 52, y), DEEP, 1.4)
            c.line((12, y + 1, 52, y + 1), WHITE, 0.7)
            c.glow(lambda g, kx=kx, y=y: g.rrect((kx - 3.5, y - 4, kx + 3.5, y + 4), 1.8, BLACK), BLACK, 0.8, 0.35)
            c.rrect((kx - 3.5, y - 4, kx + 3.5, y + 4), 1.8, V(y - 4, y + 4, WHITE, BLUE), BLACK, FW)
        c.glow(lambda g: g.ellipse((11, 37, 27, 53), BLACK), BLACK, 1.0, 0.35)
        c.ellipse((11, 37, 27, 53), Rad(16.5, 41.5, 12, 12, WHITE, BLUE, BLUE3), BLACK, LW)
        c.line((19, 45, 23.5, 40.5), WHITE, 1.6)
        for i, x in enumerate((35, 42, 49)):
            if i < 2:
                c.glow(lambda g, x=x: g.ellipse((x - 2.3, 42.7, x + 2.3, 47.3), WHITE), BLUE, 1.2, 1.0)
            c.ellipse((x - 2.3, 42.7, x + 2.3, 47.3), Rad(x - .6, 44.4, 2.6, 2.6, WHITE, BLUE) if i < 2 else V(43, 47, BLUE3, BLUE2),
                      BLACK, FW)
        return c.done(self.SH)

    def tool(self):
        """a power cell"""
        c = G(64)
        c.ground(32, 60, 15, 2, 0.4)
        c.rrect((25, 4, 39, 10), 1.5, H(25, 39, BLUE3, BLUE2, BLUE3), BLACK, LW)
        c.rrect((16, 9, 48, 59), 6, H(16, 48, BLUE2, WHITE, WHITE, BLUE2, BLUE), BLACK, LW)
        for k in range(4):
            y = 15 + k * 10.5
            box = (21.5, y, 42.5, y + 7.5)
            if k:
                c.glow(lambda g, box=box: g.rrect(box, 2, WHITE), BLUE, 1.3, 0.9)
            c.rrect(box, 2, V(y, y + 7.5, WHITE, BLUE, BLUE3) if k else V(y, y + 7.5, BLUE2, BLUE2), BLACK, FW)
        c.rect((19, 10, 23, 57), H(19, 23, rgba(WHITE, 0), rgba(WHITE, 170), rgba(WHITE, 0)))
        self.rivets(c, [(19.5, 12.5), (44.5, 12.5)])
        return c.done(self.SH)

    # emblems: glossy round mission patches
    def patch(self, colour):
        c = G(28)
        c.ellipse((1, 1, 27, 27), badge_fill(1, 1, 27, 27, colour), BLACK, 0.9)
        c.ellipse((3, 3, 25, 25), None, rgba(WHITE, 150), 0.6)
        return c

    def em_music(self):
        c = self.patch(MAGENTA)
        symbol_shadow(c, lambda g, col: note(g, 6, 5.5, 0.9, col), WHITE)
        badge_gloss(c, 1, 1, 27, 27)
        return c.done()

    def em_games(self):
        c = self.patch(ORANGE)
        symbol_shadow(c, lambda g, col: joystick(g, 5, 5, 0.9, col, col, col, col), WHITE)
        badge_gloss(c, 1, 1, 27, 27)
        return c.done()

    def em_picture(self):
        c = G(28)
        c.ellipse((1, 1, 27, 27), V(1, 20, lighten(SKY, .4), SKY))
        c.ellipse((15, 6, 21, 12), Rad(17, 8, 4, 4, WHITE, YELLOW))
        m = c.mask(("ellipse", (1, 1, 27, 27)))
        hills = G(28)
        hills.poly((1, 22, 10, 11, 15, 17, 18, 14, 27, 22, 27, 27, 1, 27), V(11, 27, lighten(GREEN, .3), darken(GREEN, .25)))
        a = np.asarray(hills.im.getchannel("A"), np.float32) * np.asarray(m, np.float32) / 255
        hills.im.putalpha(Image.fromarray(a.astype(np.uint8), "L"))
        c.im.alpha_composite(hills.im)
        badge_gloss(c, 1, 1, 27, 27)
        c.ellipse((1, 1, 27, 27), None, BLACK, 0.9)
        return c.done()


# =========================================================================================
# T2 Hologram: glowing translucent isometric objects
# =========================================================================================

class Holo:
    name = "Hologram"
    blurb = "glowing isometric holograms: translucent gradient faces over a light emitter"
    emblem_at = "26,26,36,36"
    S = 15.0
    HALO = (BLUE, 1.8, 0.75)

    def iso(self, cx, cy, x, y, z):
        k = self.S
        return cx + (x - y) * k * 0.866, cy + (x + y) * k * 0.5 - z * k

    def flat(self, pts):
        return [v for p in pts for v in p]

    def box(self, c, cx, cy, x0, y0, z0, dx, dy, dz, a=230):
        I = lambda x, y, z: self.iso(cx, cy, x, y, z)
        x1, y1, z1 = x0 + dx, y0 + dy, z0 + dz
        top = [I(x0, y0, z1), I(x1, y0, z1), I(x1, y1, z1), I(x0, y1, z1)]
        left = [I(x0, y1, z0), I(x1, y1, z0), I(x1, y1, z1), I(x0, y1, z1)]
        right = [I(x1, y0, z0), I(x1, y1, z0), I(x1, y1, z1), I(x1, y0, z1)]
        ty0, ty1 = min(p[1] for p in top), max(p[1] for p in top)
        c.poly(self.flat(top), V(ty0, ty1, rgba(WHITE, a), rgba(BLUE2, a)), BLACK, FW)
        ly0, ly1 = min(p[1] for p in left), max(p[1] for p in left)
        c.poly(self.flat(left), V(ly0, ly1, rgba(BLUE2, a), rgba(BLUE, a)), BLACK, FW)
        ry0, ry1 = min(p[1] for p in right), max(p[1] for p in right)
        c.poly(self.flat(right), V(ry0, ry1, rgba(BLUE, a), rgba(BLUE3, a)), BLACK, FW)
        p0, p1 = I(x1, y1, z1), I(x1, y1, z0)
        c.line((p0[0], p0[1], p1[0], p1[1]), rgba(WHITE, 200), 0.6)

    def face_rect(self, c, cx, cy, plane, u0, v0, u1, v1, fill=None, outline=BLACK, w=FW, at=None):
        I = lambda x, y, z: self.iso(cx, cy, x, y, z)
        if plane == "x":
            pts = [I(at, u0, v0), I(at, u1, v0), I(at, u1, v1), I(at, u0, v1)]
        else:
            pts = [I(u0, at, v0), I(u1, at, v0), I(u1, at, v1), I(u0, at, v1)]
        c.poly(self.flat(pts), fill, outline, w)
        return pts

    def emitter(self, c, cx, cy, rx=20):
        c.ground(cx, cy, rx, rx * 0.22, 0.85, 2.4, BLUE)
        c.ellipse((cx - rx * .6, cy - rx * .11, cx + rx * .6, cy + rx * .11),
                  Rad(cx, cy, rx * .6, rx * .11, WHITE, rgba(BLUE2, 0)))

    def drawer(self):
        c = G(64)
        self.emitter(c, 32, 56)
        cx, cy = 32, 22
        self.box(c, cx, cy, 0, 0, 0, 2.0, 1.4, 1.6)
        self.face_rect(c, cx, cy, "x", 0.15, 0.2, 1.25, 1.4, V(20, 50, rgba(WHITE, 150), rgba(BLUE2, 60)), at=2.0)
        self.face_rect(c, cx, cy, "x", 0.42, 0.98, 0.98, 1.14, WHITE, at=2.0)
        return c.done(halo=self.HALO)

    def drawer_open(self):
        c = G(64)
        self.emitter(c, 32, 56)
        cx, cy = 28, 20
        self.box(c, cx, cy, 0, 0, 0, 2.0, 1.4, 1.6)
        self.face_rect(c, cx, cy, "x", 0.15, 0.2, 1.25, 1.4, rgba(DEEP, 200), at=2.0)
        self.box(c, cx, cy, 2.0, 0.15, 0.2, 0.9, 1.1, 0.9, a=245)
        self.face_rect(c, cx, cy, "x", 0.45, 0.6, 0.85, 0.7, WHITE, at=2.9)
        I = lambda xx, y, z: self.iso(cx, cy, xx, y, z)
        for i in range(3):
            x = 2.15 + i * 0.25
            pts = [I(x, 0.3, 1.1), I(x, 1.1, 1.1), I(x, 1.1, 1.45), I(x, 0.3, 1.45)]
            c.poly(self.flat(pts), V(20, 40, WHITE, BLUE2), BLACK, FW)
        return c.done(halo=self.HALO)

    def file(self):
        c = G(64)
        self.emitter(c, 32, 58, 16)
        c.poly((24, 57, 40, 57, 50, 30, 14, 30), V(30, 57, rgba(BLUE, 0), rgba(BLUE, 120)))
        I = lambda x, z: (14 + x * 13 * .866, 45 - x * 13 * 0.5 - z * 13)
        pts = [I(0, 0), I(2.2, 0), I(2.2, 2.55), I(0.5, 2.55), I(0, 2.05)]
        c.poly(self.flat(pts), Lin(14, 10, 40, 40, rgba(WHITE, 245), rgba(BLUE2, 235)), BLACK, LW)
        c.poly(self.flat([I(0, 2.05), I(0.5, 2.55), I(0.5, 2.05)]), V(5, 15, WHITE, BLUE), BLACK, FW)
        for k in range(5):
            z = 1.75 - k * 0.32
            a, b = I(0.3, z), I(1.9 if k < 4 else 1.2, z)
            c.line((a[0], a[1], b[0], b[1]), BLUE, 1.3)
        return c.done(halo=self.HALO)

    def device(self):
        c = G(64)
        self.emitter(c, 32, 58, 22)
        cx, cy = 32, 32
        self.box(c, cx, cy, 0, 0, 0, 1.8, 1.8, 0.7)
        self.face_rect(c, cx, cy, "x", 0.2, 0.3, 1.2, 0.4, DEEP, at=1.8)
        self.face_rect(c, cx, cy, "y", 0.25, 0.25, 0.5, 0.45, WHITE, at=1.8)
        tx, ty = self.iso(cx, cy, 0.9, 0.9, 1.35)
        bx, by = self.iso(cx, cy, 0.9, 0.9, 0.7)
        c.poly((bx - 5, by - 1, bx + 5, by - 1, tx + 12, ty, tx - 12, ty), V(ty, by, rgba(BLUE, 90), rgba(BLUE, 10)))
        c.glow(lambda g: g.ellipse((tx - 12, ty - 6.9, tx + 12, ty + 6.9), WHITE), BLUE, 1.6, 0.9)
        c.ellipse((tx - 12, ty - 6.9, tx + 12, ty + 6.9),
                  Rad(tx - 3, ty - 2, 14, 8, rgba(WHITE, 240), rgba(BLUE2, 220), rgba(BLUE, 210)), BLACK, FW)
        c.ellipse((tx - 3, ty - 1.7, tx + 3, ty + 1.7), WHITE, BLACK, FW)
        return c.done(halo=self.HALO)

    def archive(self):
        c = G(64)
        self.emitter(c, 32, 58, 22)
        cx, cy = 32, 26
        u = 0.95
        for (x, y, z) in ((0, 0, 0), (u, 0, 0), (0, u, 0), (u, u, 0)):
            self.box(c, cx, cy, x, y, z, u, u, u)
        self.box(c, cx, cy, 0.48, 0.48, u, u, u, u)
        self.face_rect(c, cx, cy, "x", 0.48, u + 0.35, 0.48 + u, u + 0.6, WHITE, at=0.48 + u)
        return c.done(halo=self.HALO)

    def prefs(self):
        c = G(64)
        self.emitter(c, 32, 56, 22)
        cx, cy = 32, 26
        self.box(c, cx, cy, 0, 0, 0, 2.1, 1.6, 0.35)
        for (x, y, h) in ((0.55, 0.55, 0.55), (1.35, 0.55, 0.4)):
            bx, by = self.iso(cx, cy, x, y, 0.35)
            tx, ty = self.iso(cx, cy, x, y, 0.35 + h)
            r = 5.2
            c.ellipse((bx - r, by - r * .58, bx + r, by + r * .58), BLUE3, BLACK, FW)
            c.rect((bx - r, ty, bx + r, by), H(bx - r, bx + r, BLUE2, BLUE, BLUE3))
            c.line((bx - r, ty, bx - r, by), BLACK, FW)
            c.line((bx + r, ty, bx + r, by), BLACK, FW)
            c.ellipse((tx - r, ty - r * .58, tx + r, ty + r * .58), Rad(tx - 1, ty - 1, r * 1.2, r, WHITE, BLUE2), BLACK, FW)
            c.line((tx, ty, tx + 3, ty - 1.6), BLACK, FW)
        a, b = self.iso(cx, cy, 0.3, 1.25, 0.35), self.iso(cx, cy, 1.8, 1.25, 0.35)
        c.line((a[0], a[1], b[0], b[1]), DEEP, 1.2)
        k = self.iso(cx, cy, 1.2, 1.25, 0.35)
        c.rrect((k[0] - 3, k[1] - 4.5, k[0] + 3, k[1] + 1), 1.2, V(k[1] - 4.5, k[1] + 1, WHITE, BLUE), BLACK, FW)
        return c.done(halo=self.HALO)

    def tool(self):
        c = G(64)
        self.emitter(c, 32, 56, 20)
        cx, cy = 32, 22
        self.box(c, cx, cy, 0, 0, 0, 1.6, 1.6, 1.0)
        for t in (0.35, 0.8, 1.25):
            a, b = self.iso(cx, cy, t, 0.15, 1.0), self.iso(cx, cy, t, 1.45, 1.0)
            c.line((a[0], a[1], b[0], b[1]), BLUE, 1.0)
        pts = [self.iso(cx, cy, *v) for v in ((0.5, 0.5, 1.0), (1.1, 0.5, 1.0), (1.1, 1.1, 1.0), (0.5, 1.1, 1.0))]
        c.glow(lambda g: g.poly(self.flat(pts), WHITE), BLUE, 1.5, 1.0)
        c.poly(self.flat(pts), Rad(cx, pts[0][1] + 4, 8, 5, WHITE, BLUE), BLACK, FW)
        for t in (0.3, 0.7, 1.1, 1.5):
            a = self.iso(cx, cy, 1.6, t, 0.25)
            c.line((a[0], a[1], a[0] + 2.6, a[1] + 1.5), BLACK, FW)
            b = self.iso(cx, cy, t, 1.6, 0.25)
            c.line((b[0], b[1], b[0] - 2.6, b[1] + 1.5), BLACK, FW)
        return c.done(halo=self.HALO)

    # emblems: bright glyphs with a gradient and a glow of their own colour
    def em_music(self):
        c = G(28)
        c.glow(lambda g: note(g, 3, 3, 1.15, WHITE), MAGENTA, 1.4, 0.8)
        note(c, 3, 3, 1.15, V(2, 26, lighten(MAGENTA, .4), MAGENTA, darken(MAGENTA, .25)))
        return c.done()

    def em_games(self):
        c = G(28)
        c.glow(lambda g: joystick(g, 3, 2.5, 1.1, WHITE, WHITE, WHITE, WHITE), ORANGE, 1.4, 0.7)
        joystick(c, 3, 2.5, 1.1, V(16, 24, lighten(PURPLE, .3), darken(PURPLE, .2)),
                 Rad(10, 4.5, 6, 6, lighten(ORANGE, .6), ORANGE, darken(ORANGE, .2)), (60, 60, 70, 255))
        return c.done()

    def em_picture(self):
        c = G(28)
        c.glow(lambda g: g.rrect((2, 4, 26, 24), 1.5, WHITE), SKY, 1.4, 0.8)
        c.rrect((2, 4, 26, 24), 1.5, WHITE)
        c.rect((4, 6, 24, 22), V(6, 22, lighten(SKY, .45), SKY))
        c.ellipse((16, 8, 21, 13), Rad(18, 10, 4, 4, WHITE, YELLOW))
        c.poly((4, 22, 11, 12, 16, 18, 19, 15, 24, 22), V(12, 22, lighten(GREEN, .3), darken(GREEN, .2)))
        return c.done()


# =========================================================================================
# T3 HUD: brushed-metal mecha interface, chamfered corners, glowing segments
# =========================================================================================

class Hud:
    name = "HUD"
    blurb = "mecha interface: brushed chamfered plates, corner brackets, glowing segments"
    emblem_at = "26,26,36,35"
    SH = (1.2, 1.6, 0.9, 0.4)

    def metal(self, x0, y0, x1, y1):
        return Lin(x0, y0, x1, y1, WHITE, BLUE2, WHITE, BLUE2, BLUE)

    def panel(self, x0, y0, x1, y1):
        return Lin(x0, y0, x0 + (x1 - x0) * .4, y1, BLUE2, BLUE, BLUE3)

    def scan(self, c, x0, y0, x1, y1):
        y = y0 + 1
        while y < y1:
            c.line((x0, y, x1, y), rgba(WHITE, 45), 0.5)
            y += 1.6

    def brackets(self, c, x0, y0, x1, y1, n=3.5):
        for (x, y, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
            c.line((x + sx * n, y, x, y, x, y + sy * n), BLACK, FW)

    def lit(self, c, box, on=True):
        if on:
            c.glow(lambda g: g.rect(box, WHITE), BLUE, 1.0, 1.0)
            c.rect(box, WHITE)
        else:
            c.rect(box, rgba(BLUE2, 200))

    def drawer(self):
        c = G(64)
        c.poly(chamfer(6, 14, 58, 54, 7), self.metal(6, 14, 58, 54), BLACK, LW)
        c.poly(chamfer(10, 20, 54, 50, 5), self.panel(10, 20, 54, 50), BLACK, FW)
        self.scan(c, 12, 21, 52, 49)
        slit = (19, 27, 45, 27, 43, 31, 21, 31)
        c.poly(slit, V(27, 31, DEEP, BLUE3), BLACK, FW)
        c.inner_shadow(("poly", slit), dy=0.8, blur=0.6, opacity=0.6)
        c.line((21, 32, 43, 32), rgba(WHITE, 200), 0.7)
        for i in range(5):
            self.lit(c, (15 + i * 5, 43, 18.2 + i * 5, 45.4), i < 3)
        c.line((40, 44.2, 49, 44.2), BLACK, FW)
        self.brackets(c, 3, 11, 61, 57)
        return c.done(self.SH)

    def drawer_open(self):
        c = G(64)
        c.poly(chamfer(6, 6, 58, 42, 7), self.metal(6, 6, 58, 42), BLACK, LW)
        bay = chamfer(10, 12, 54, 36, 4)
        c.poly(bay, V(12, 36, DEEP, BLUE3), BLACK, FW)
        c.inner_shadow(("poly", bay), dy=2, blur=1.5, opacity=0.6)
        c.poly((10, 31, 54, 31, 57, 41, 7, 41), V(31, 41, BLUE2, WHITE), BLACK, FW)
        for x in (17, 25, 33):
            c.glow(lambda g, x=x: g.poly(chamfer(x, 22, x + 6, 36, 2), WHITE), BLUE, 1.0, 0.8)
            c.poly(chamfer(x, 22, x + 6, 36, 2), V(22, 36, WHITE, BLUE), BLACK, FW)
        c.poly(chamfer(5, 40, 59, 58, 5), self.panel(5, 40, 59, 58), BLACK, LW)
        self.scan(c, 7, 41, 57, 57)
        slit = (19, 46, 45, 46, 43, 50, 21, 50)
        c.poly(slit, V(46, 50, DEEP, BLUE3), BLACK, FW)
        for x in (49, 52.5):
            c.glow(lambda g, x=x: g.line((x, 46, x + 2, 48, x, 50), WHITE, 1.0), BLUE, 0.8, 1.0)
            c.line((x, 46, x + 2, 48, x, 50), WHITE, 0.9)
        return c.done(self.SH)

    def file(self):
        c = G(64)
        c.poly((15, 5, 41, 5, 49, 13, 49, 59, 15, 59), self.metal(15, 5, 49, 59), BLACK, LW)
        c.poly((41, 5, 41, 13, 49, 13), V(5, 13, BLUE, BLUE3), BLACK, FW)
        c.rect((19.5, 10, 33, 14), H(19.5, 33, BLUE3, BLUE))
        for y, x1 in ((21, 44), (26, 44), (31, 44), (36, 44), (41, 36)):
            c.line((19.5, y, x1, y), BLACK if y == 21 else BLUE, FW if y == 21 else 1.4)
        for i in range(4):
            self.lit(c, (19.5 + i * 4, 52, 22 + i * 4, 54.5), i < 3)
        return c.done(self.SH)

    def device(self):
        c = G(64)
        c.poly(hexagon(32, 32, 26, 30), self.metal(8, 8, 56, 56), BLACK, LW)
        c.poly(hexagon(32, 32, 18, 30), Rad(28, 27, 22, 22, BLUE2, BLUE, DEEP), BLACK, FW)
        c.inner_shadow(("poly", tuple(hexagon(32, 32, 18, 30))), dy=1.5, blur=1.4, opacity=0.5)
        c.glow(lambda g: g.ellipse((25, 25, 39, 39), WHITE), BLUE, 1.6, 1.0)
        c.ellipse((25, 25, 39, 39), Rad(30, 30, 9, 9, WHITE, BLUE2), BLACK, FW)
        c.ellipse((30, 30, 34, 34), V(30, 34, BLUE, DEEP), BLACK, FW)
        for a in (90, 210, 330):
            r = math.radians(a)
            c.line((32 + 20 * math.cos(r), 32 + 20 * math.sin(r), 32 + 24 * math.cos(r), 32 + 24 * math.sin(r)), BLACK, FW)
        c.arc((21.5, 21.5, 42.5, 42.5), 200, 300, WHITE, 1.3)
        return c.done(self.SH)

    def archive(self):
        c = G(64)
        c.poly(chamfer4(6, 14, 58, 56, 6), self.panel(6, 14, 58, 56), BLACK, LW)
        self.scan(c, 8, 25, 56, 54)
        c.poly(chamfer4(6, 14, 58, 24, 4), self.metal(6, 14, 58, 24), BLACK, FW)
        c.rect((6.6, 33, 57.4, 41), H(6, 58, WHITE, BLUE2, WHITE))
        for x in range(7, 51, 6):
            c.poly((x, 41, x + 4, 33, x + 7, 33, x + 3, 41), V(33, 41, BLUE, BLUE3))
        c.line((6.5, 33, 57.5, 33), BLACK, FW)
        c.line((6.5, 41, 57.5, 41), BLACK, FW)
        c.poly(chamfer4(6, 14, 58, 56, 6), None, BLACK, LW)
        c.poly(chamfer4(26, 44, 38, 51, 1.5), self.metal(26, 44, 38, 51), BLACK, FW)
        self.lit(c, (30, 46.8, 34, 48.2))
        return c.done(self.SH)

    def prefs(self):
        c = G(64)
        c.poly(chamfer4(5, 5, 59, 59, 8), self.metal(5, 5, 59, 59), BLACK, LW)
        c.ellipse((13, 11, 51, 49), Rad(28, 25, 26, 26, BLUE2, BLUE, BLUE3))
        c.inner_shadow(("ellipse", (13, 11, 51, 49)), dy=1.5, blur=1.5, opacity=0.45)
        c.arc((13, 11, 51, 49), 135, 405, BLACK, FW)
        c.glow(lambda g: g.arc((16, 14, 48, 46), 135, 300, WHITE, 2.6), BLUE, 1.2, 1.0)
        c.arc((16, 14, 48, 46), 135, 300, WHITE, 2.2)
        for i in range(11):
            a = math.radians(135 + i * 27)
            c.line((32 + 16 * math.cos(a), 30 + 16 * math.sin(a), 32 + 18.5 * math.cos(a), 30 + 18.5 * math.sin(a)), BLACK, FW)
        a = math.radians(300)
        c.line((32, 30, 32 + 13 * math.cos(a), 30 + 13 * math.sin(a)), BLACK, 1.3)
        c.ellipse((29, 27, 35, 33), Rad(31, 29, 4, 4, WHITE, BLUE), BLACK, FW)
        c.line((14, 53, 50, 53), DEEP, 1.4)
        c.poly(chamfer(33, 50, 40, 56, 1.5), V(50, 56, WHITE, BLUE), BLACK, FW)
        return c.done(self.SH)

    def tool(self):
        c = G(64)
        c.poly(chamfer4(8, 8, 56, 56, 9), self.metal(8, 8, 56, 56), BLACK, LW)
        c.ellipse((17, 17, 47, 47), Rad(30, 28, 20, 20, BLUE2, BLUE, BLUE3), BLACK, FW)
        c.inner_shadow(("ellipse", (17, 17, 47, 47)), dy=1.4, blur=1.4, opacity=0.45)
        c.glow(lambda g: g.ellipse((22, 22, 42, 42), None, WHITE, 1.4), BLUE, 1.0, 1.0)
        c.ellipse((22, 22, 42, 42), None, WHITE, 1.2)
        for (x0, y0, x1, y1) in ((32, 12, 32, 22), (32, 42, 32, 52), (12, 32, 22, 32), (42, 32, 52, 32)):
            c.line((x0, y0, x1, y1), BLACK, FW)
        c.glow(lambda g: g.poly((32, 26, 38, 32, 32, 38, 26, 32), WHITE), BLUE, 1.2, 1.0)
        c.poly((32, 26, 38, 32, 32, 38, 26, 32), Lin(26, 26, 38, 38, WHITE, BLUE), BLACK, FW)
        return c.done(self.SH)

    # emblems: chamfered glossy colour plates
    def plate(self, colour):
        c = G(28)
        c.poly(chamfer4(1, 1, 27, 27, 5), Lin(1, 1, 27, 27, lighten(colour, .45), colour, darken(colour, .3)), BLACK, 0.9)
        c.poly(chamfer4(3, 3, 25, 25, 3.8), None, rgba(WHITE, 150), 0.6)
        return c

    def plate_gloss(self, c):
        c.poly((6, 1.6, 22, 1.6, 26.4, 6, 26.4, 10, 1.6, 10, 1.6, 6), gloss(1.6, 11, 120))

    def em_music(self):
        c = self.plate(MAGENTA)
        symbol_shadow(c, lambda g, col: note(g, 6, 5.5, 0.9, col), WHITE)
        self.plate_gloss(c)
        return c.done()

    def em_games(self):
        c = self.plate(ORANGE)
        symbol_shadow(c, lambda g, col: joystick(g, 5, 5, 0.9, col, col, col, col), WHITE)
        self.plate_gloss(c)
        return c.done()

    def em_picture(self):
        c = self.plate(GREEN)
        c.poly(chamfer4(3, 3, 25, 25, 3.8), V(3, 20, lighten(SKY, .4), SKY))
        c.ellipse((15, 6, 21, 12), Rad(17, 8, 4, 4, WHITE, YELLOW))
        c.poly((3, 22, 10, 12, 15, 18, 18, 15, 25, 22, 25, 21.2, 21.2, 25, 6.8, 25, 3, 21.2),
               V(12, 25, lighten(GREEN, .3), darken(GREEN, .2)))
        c.poly(chamfer4(1, 1, 27, 27, 5), None, BLACK, 0.9)
        return c.done()


# =========================================================================================
# T4 Blueprint: lit blueprint sheets lifted off the table
# =========================================================================================

class Blueprint:
    name = "Blueprint"
    blurb = "lit blueprint plates lifted off the table, white grid, black construction lines"
    emblem_at = "26,26,36,35"
    CL = 0.5
    SH = (1.6, 2.2, 1.6, 0.42)

    def plate(self, x0, y0, x1, y1):
        w, h = x1 - x0, y1 - y0
        return Rad(x0 + w * .35, y0 + h * .3, w * .95, h * .95, BLUE2, BLUE, BLUE3, DEEP)

    def grid(self, c, x0, y0, x1, y1, step=5.0):
        x = x0 + step
        while x < x1 - 0.5:
            c.line((x, y0 + .6, x, y1 - .6), rgba(WHITE, 120), 0.5)
            x += step
        y = y0 + step
        while y < y1 - 0.5:
            c.line((x0 + .6, y, x1 - .6, y), rgba(WHITE, 120), 0.5)
            y += step

    def sheen(self, c, x0, y0, x1, y1):
        c.poly((x0, y0, x0 + (x1 - x0) * .55, y0, x0, y0 + (y1 - y0) * .6),
               Lin(x0, y0, x0 + (x1 - x0) * .3, y0 + (y1 - y0) * .3, rgba(WHITE, 110), rgba(WHITE, 0)))

    def dim_h(self, c, x0, x1, y):
        c.line((x0, y, x1, y), BLACK, self.CL)
        for x in (x0, x1):
            c.line((x, y - 1.6, x, y + 1.6), BLACK, self.CL)
        c.poly((x0, y, x0 + 2.2, y - 1, x0 + 2.2, y + 1), BLACK)
        c.poly((x1, y, x1 - 2.2, y - 1, x1 - 2.2, y + 1), BLACK)

    def ext(self, c, x0, y0, x1, y1, n=3):
        for y in (y0, y1):
            c.line((x0 - n, y, x0 + n * .4, y), BLACK, self.CL)
            c.line((x1 - n * .4, y, x1 + n, y), BLACK, self.CL)
        for x in (x0, x1):
            c.line((x, y0 - n, x, y0 + n * .4), BLACK, self.CL)
            c.line((x, y1 - n * .4, x, y1 + n), BLACK, self.CL)

    def sheet(self, c, box, step=5.0):
        c.rect(box, self.plate(*box))
        self.grid(c, *box, step)
        self.sheen(c, *box)
        c.rect(box, None, BLACK, LW)

    def drawer(self):
        c = G(64)
        self.sheet(c, (8, 12, 56, 50))
        c.rect((13, 19, 51, 44), V(19, 44, rgba(WHITE, 40), rgba(BLUE3, 60)), WHITE, 1.1)
        c.glow(lambda g: g.rrect((25, 27, 39, 32), 2.5, BLACK), BLACK, 0.8, 0.35)
        c.rrect((25, 27, 39, 32), 2.5, V(27, 32, WHITE, BLUE2), BLACK, FW)
        self.ext(c, 8, 12, 56, 50)
        self.dim_h(c, 8, 56, 56.5)
        return c.done(self.SH)

    def drawer_open(self):
        c = G(64)
        self.sheet(c, (8, 6, 56, 42))
        bay = (13, 13, 51, 36)
        c.rect(bay, V(13, 36, DEEP, BLUE3))
        c.inner_shadow(("rect", bay), dy=2, blur=1.6, opacity=0.6)
        c.rect(bay, None, BLACK, FW)
        for (x0, y0, x1, y1) in ((13, 13, 10, 38), (51, 13, 54, 38)):
            dashed(c, x0, y0, x1, y1, WHITE, self.CL + 0.2)
        c.rect((10, 38, 54, 57), V(38, 57, WHITE, BLUE2), BLACK, LW)
        c.rrect((25, 45, 39, 50), 2.5, V(45, 50, BLUE, BLUE3), BLACK, FW)
        c.line((58.5, 18, 58.5, 32), BLACK, self.CL)
        c.poly((58.5, 34, 57.2, 31, 59.8, 31), BLACK)
        return c.done(self.SH)

    def file(self):
        c = G(64)
        pts = (14, 6, 40, 6, 50, 16, 50, 58, 14, 58)
        c.poly(pts, self.plate(14, 6, 50, 58))
        self.grid(c, 14, 6, 50, 58, 6)
        clear = G(64)
        clear.poly((40, 5, 51, 5, 51, 16), WHITE)
        a = np.asarray(c.im.getchannel("A"), np.float32) * (1 - np.asarray(clear.im.getchannel("A"), np.float32) / 255)
        c.im.putalpha(Image.fromarray(a.astype(np.uint8), "L"))
        self.sheen(c, 14, 6, 50, 58)
        c.poly(pts, None, BLACK, LW)
        c.poly((40, 6, 40, 16, 50, 16), Lin(40, 6, 50, 16, WHITE, BLUE2), BLACK, FW)
        for y, x1 in ((24, 44), (30, 44), (36, 44), (42, 34)):
            c.line((19, y, x1, y), WHITE, 1.5)
        self.ext(c, 14, 6, 50, 58, 2.5)
        return c.done(self.SH)

    def device(self):
        c = G(64)
        self.sheet(c, (6, 15, 58, 49))
        c.glow(lambda g: g.ellipse((10, 18, 38, 46), BLACK), BLACK, 1.0, 0.35)
        c.ellipse((10, 18, 38, 46), Rad(20, 26, 22, 22, WHITE, BLUE2, BLUE), BLACK, FW)
        for r in (11, 7):
            c.ellipse((24 - r, 32 - r, 24 + r, 32 + r), None, rgba(BLUE3, 160), 0.6)
        c.ellipse((22, 30, 26, 34), V(30, 34, BLUE, DEEP), BLACK, FW)
        c.line((50, 21, 33, 36), DEEP, 1.4)
        c.line((50, 21, 33, 36), BLACK, 0.5)
        c.ellipse((47.5, 18.5, 52.5, 23.5), Rad(49.5, 20.5, 3, 3, WHITE, BLUE), BLACK, FW)
        c.line((24, 32, 24, 11), BLACK, self.CL)
        c.line((10, 32, 38, 32), BLACK, self.CL)
        self.dim_h(c, 6, 58, 55)
        return c.done(self.SH)

    def archive(self):
        c = G(64)
        self.sheet(c, (9, 16, 55, 54))
        c.rect((7, 12, 57, 21), V(12, 21, WHITE, BLUE2), BLACK, LW)
        for x in (20, 44):
            dashed(c, x, 21.5, x, 53.5, WHITE, 1.4)
        c.glow(lambda g: g.rrect((27, 30, 37, 40), 1.5, BLACK), BLACK, 0.8, 0.35)
        c.rrect((27, 30, 37, 40), 1.5, V(30, 40, WHITE, BLUE2), BLACK, FW)
        c.ellipse((30.6, 32.5, 33.4, 35.3), BLACK)
        self.ext(c, 9, 16, 55, 54, 2.5)
        self.dim_h(c, 9, 55, 59)
        return c.done(self.SH)

    def prefs(self):
        c = G(64)
        c.ellipse((8, 6, 46, 44), Rad(20, 16, 34, 34, BLUE2, BLUE, BLUE3), BLACK, LW)
        c.ellipse((14, 12, 40, 38), None, WHITE, 1.0)
        for i in range(12):
            a = math.radians(i * 30)
            c.line((27 + 16 * math.cos(a), 25 + 16 * math.sin(a), 27 + 18.3 * math.cos(a), 25 + 18.3 * math.sin(a)), WHITE, 0.9)
        c.glow(lambda g: g.line((27, 25, 38, 19), BLACK, 1.3), BLACK, 0.7, 0.4)
        c.line((27, 25, 38, 19), BLACK, 1.3)
        c.ellipse((24, 22, 30, 28), Rad(26, 24, 4, 4, WHITE, BLUE2), BLACK, FW)
        c.line((27, 2, 27, 48), BLACK, self.CL)
        c.line((4, 25, 50, 25), BLACK, self.CL)
        self.sheet(c, (10, 50, 58, 56))
        c.glow(lambda g: g.rect((40, 48, 45, 58), BLACK), BLACK, 0.7, 0.4)
        c.rect((40, 48, 45, 58), V(48, 58, WHITE, BLUE2), BLACK, FW)
        return c.done(self.SH)

    def tool(self):
        c = G(64)
        pts = []
        for i in range(40):
            a = i / 40 * 2 * math.pi
            r = 22 if (i % 5) in (1, 2) else 17
            pts += [32 + r * math.cos(a), 32 + r * math.sin(a)]
        c.poly(pts, Rad(26, 24, 30, 30, BLUE2, BLUE, BLUE3), BLACK, LW)
        c.ellipse((20, 20, 44, 44), None, WHITE, 0.9)
        c.ellipse((26, 26, 38, 38), Rad(30, 30, 8, 8, WHITE, BLUE2), BLACK, FW)
        c.line((32, 4, 32, 60), BLACK, self.CL)
        c.line((4, 32, 60, 32), BLACK, self.CL)
        c.ellipse((10, 10, 54, 54), None, BLACK, self.CL)
        return c.done(self.SH)

    # emblems: glossy colour discs
    def disc(self, colour):
        c = G(28)
        c.ellipse((1, 1, 27, 27), badge_fill(1, 1, 27, 27, colour), BLACK, 0.9)
        return c

    def em_music(self):
        c = self.disc(MAGENTA)
        symbol_shadow(c, lambda g, col: note(g, 6, 5.5, 0.9, col), WHITE)
        badge_gloss(c, 1, 1, 27, 27)
        return c.done()

    def em_games(self):
        c = self.disc(ORANGE)
        symbol_shadow(c, lambda g, col: joystick(g, 5, 5, 0.9, col, col, col, col), WHITE)
        badge_gloss(c, 1, 1, 27, 27)
        return c.done()

    def em_picture(self):
        c = G(28)
        c.rect((2, 4, 26, 24), WHITE)
        c.rect((3.5, 5.5, 24.5, 22.5), V(5.5, 22.5, lighten(SKY, .45), SKY))
        c.ellipse((16, 7.5, 21, 12.5), Rad(18, 9.5, 4, 4, WHITE, YELLOW))
        c.poly((3.5, 22.5, 10, 12, 15, 18, 18, 15, 24.5, 22.5), V(12, 22.5, lighten(GREEN, .3), darken(GREEN, .2)))
        c.rect((2, 4, 26, 24), None, BLACK, 0.9)
        return c.done()


# =========================================================================================
# T5 Pixel Arcade: pixel sprites with banded shading and hard pixel shadows
# =========================================================================================

class PixelCanvas:
    def __init__(self, size):
        self.size = size
        self.im = Image.new("RGBA", (size, size), NONE)
        self.d = ImageDraw.Draw(self.im)

    def box(self, x0, y0, x1, y1, fill, outline=BLACK):
        self.d.rectangle((x0, y0, x1, y1), fill=fill, outline=outline)

    def rbox(self, x0, y0, x1, y1, fill, outline=BLACK):
        if fill:
            self.d.rectangle((x0 + 1, y0, x1 - 1, y1), fill=fill)
            self.d.rectangle((x0, y0 + 1, x1, y1 - 1), fill=fill)
        if outline:
            self.d.line((x0 + 1, y0, x1 - 1, y0), fill=outline)
            self.d.line((x0 + 1, y1, x1 - 1, y1), fill=outline)
            self.d.line((x0, y0 + 1, x0, y1 - 1), fill=outline)
            self.d.line((x1, y0 + 1, x1, y1 - 1), fill=outline)

    def vband(self, x0, y0, x1, y1, ramp, outline=BLACK, rounded=True):
        """a box shaded top to bottom in bands of the ramp's colours"""
        n = len(ramp)
        for y in range(y0, y1 + 1):
            k = min(n - 1, (y - y0) * n // (y1 - y0 + 1))
            lo = x0 + (1 if rounded and y in (y0, y1) else 0)
            hi = x1 - (1 if rounded and y in (y0, y1) else 0)
            self.d.line((lo, y, hi, y), fill=ramp[k])
        if outline:
            if rounded:
                self.rbox(x0, y0, x1, y1, None, outline)
            else:
                self.d.rectangle((x0, y0, x1, y1), outline=outline)

    def hline(self, x0, x1, y, fill):
        self.d.line((x0, y, x1, y), fill=fill)

    def vline(self, x, y0, y1, fill):
        self.d.line((x, y0, x, y1), fill=fill)

    def px(self, pts, fill):
        for x, y in pts:
            self.d.point((x, y), fill=fill)

    def sprite(self, x0, y0, rows, colours):
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch in colours:
                    self.d.point((x0 + x, y0 + y), fill=colours[ch])

    def shape(self, inside, colour, outline=BLACK):
        n = self.size
        m = [[inside(x + .5, y + .5) for x in range(n)] for y in range(n)]
        for y in range(n):
            for x in range(n):
                if not m[y][x]:
                    continue
                edge = any(not (0 <= x + dx < n and 0 <= y + dy < n and m[y + dy][x + dx])
                           for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                col = outline if edge and outline else colour(x, y)
                if col:
                    self.d.point((x, y), fill=col)

    def done(self, shadow=(2, 2, 90)):
        """a hard pixel drop shadow"""
        out = Image.new("RGBA", self.im.size, NONE)
        if shadow and shadow[2]:
            a = self.im.getchannel("A").point(lambda v: shadow[2] if v else 0)
            layer = Image.new("RGBA", self.im.size, (0, 0, 0, 255))
            layer.putalpha(a)
            sh = Image.new("RGBA", self.im.size, NONE)
            sh.paste(layer, (shadow[0], shadow[1]))
            out.alpha_composite(sh)
        out.alpha_composite(self.im)
        return out


def pramp(colour):
    return [lighten(colour, .5), lighten(colour, .2), colour, darken(colour, .25)]


class Pixel:
    name = "Pixel Arcade"
    blurb = "pixel sprites: banded shading, hard pixel shadows, cartridge, treasure chest, potion"
    emblem_at = "0,0,35,34"
    prefs_text = "EMBLEMMETHOD=SHADOW\nSHADOWBLUR=0\nSHADOWOFFSET=2,2\nSHADOWOPACITY=35\n"

    def dresser(self, c, y0, y1):
        c.d.polygon([(11, y0), (52, y0), (57, y0 + 5), (6, y0 + 5)], fill=BLUE2, outline=BLACK)
        c.hline(12, 51, y0 + 1, WHITE)
        c.hline(9, 54, y0 + 3, WHITE)
        c.vband(6, y0 + 5, 57, y1, [WHITE, WHITE, BLUE2, BLUE2, mix(BLUE2, BLUE, .5)])
        c.box(9, y1 + 1, 13, y1 + 3, BLUE3)
        c.box(50, y1 + 1, 54, y1 + 3, BLUE3)

    def front(self, c, x0, y0, x1, y1):
        c.vband(x0, y0, x1, y1, [BLUE2, BLUE, BLUE, BLUE3])
        c.hline(x0 + 1, x1 - 1, y0 + 1, WHITE)
        c.vline(x0 + 1, y0 + 1, y1 - 1, rgba(WHITE, 200))
        c.hline(x0 + 1, x1 - 1, y1 - 1, DEEP)
        c.vline(x1 - 1, y0 + 1, y1 - 1, DEEP)
        k = (x0 + x1) // 2
        c.box(k - 8, y0 + 5, k + 7, y0 + 10, DEEP)
        c.rbox(k - 7, y0 + 6, k + 6, y0 + 9, WHITE)
        c.hline(k - 6, k + 5, y0 + 8, BLUE2)
        for x in range(x0 + 4, x0 + 13, 2):
            c.px([(x, y1 - 4)], WHITE)

    def drawer(self):
        c = PixelCanvas(64)
        self.dresser(c, 8, 53)
        self.front(c, 10, 18, 53, 49)
        return c.done()

    def drawer_open(self):
        c = PixelCanvas(64)
        self.dresser(c, 2, 39)
        c.vband(10, 11, 53, 36, [DEEP, BLUE3, BLUE3, BLUE])
        c.d.polygon([(10, 30), (53, 30), (57, 40), (6, 40)], fill=BLUE2, outline=BLACK)
        c.hline(9, 54, 32, WHITE)
        for x in (15, 22, 29, 36):
            c.vband(x, 22, x + 5, 34, [WHITE, BLUE2, BLUE])
        self.front(c, 5, 39, 58, 59)
        return c.done()

    def file(self):
        c = PixelCanvas(64)
        c.d.polygon([(15, 5), (40, 5), (48, 13), (48, 58), (15, 58)], fill=WHITE, outline=BLACK)
        for y in range(40, 58):
            c.hline(16, 47, y, BLUE2 if y < 52 else mix(BLUE2, BLUE, .5))
        c.d.polygon([(40, 5), (40, 13), (48, 13)], fill=BLUE, outline=BLACK)
        c.hline(15, 48, 58, BLACK)
        c.vline(48, 13, 58, BLACK)
        for y, x1 in ((19, 43), (24, 43), (29, 43), (34, 43), (39, 33)):
            for x in range(20, x1 + 1, 2):
                if (x // 2) % 4 != 3:
                    c.px([(x, y), (x + 1, y)], BLUE3)
        c.vband(20, 46, 30, 53, [BLUE2, BLUE, BLUE3])
        return c.done()

    def device(self):
        """a game cartridge"""
        c = PixelCanvas(64)
        c.d.polygon([(12, 6), (51, 6), (51, 50), (47, 54), (16, 54), (12, 50)], fill=WHITE, outline=BLACK)
        for y in range(36, 54):
            lo, hi = (13, 50) if y < 50 else (13 + (y - 49), 50 - (y - 49))
            c.hline(lo, hi, y, BLUE2 if y < 46 else mix(BLUE2, BLUE, .5))
        c.d.line([(12, 50), (16, 54), (47, 54), (51, 50)], fill=BLACK)
        for x in range(16, 48, 3):
            c.vline(x, 9, 13, BLUE)
            c.vline(x + 1, 9, 13, WHITE)
        c.vband(17, 18, 46, 42, [BLUE, BLUE, BLUE3, DEEP])
        c.hline(18, 45, 19, BLUE2)
        c.sprite(25, 24, ["...WW...", "..WWWW..", ".WW..WW.", "WW....WW", "WWWWWWWW", "WW....WW", "WW....WW"],
                 {"W": WHITE})
        c.sprite(36, 24, ["WWWWWW", "WW..WW", "WWWWW.", "WW..WW", "WWWWWW"], {"W": WHITE})
        for x in range(18, 46, 4):
            c.box(x, 56, x + 2, 59, BLUE)
            c.vline(x + 1, 57, 58, WHITE)
        return c.done()

    def archive(self):
        """a treasure chest"""
        c = PixelCanvas(64)
        c.vband(8, 30, 55, 56, [BLUE, BLUE, BLUE3, DEEP])
        c.d.chord((8, 10, 55, 46), 180, 360, fill=BLUE2, outline=BLACK)
        for y in range(12, 16):
            c.hline(16, 47, y, WHITE)
        c.hline(8, 55, 28, BLACK)
        c.vband(8, 28, 55, 32, [WHITE, BLUE2], rounded=False)
        for x0 in (14, 46):
            c.vband(x0, 15, x0 + 3, 56, [WHITE, BLUE2, BLUE2, BLUE], rounded=False)
        c.vband(27, 26, 36, 38, [WHITE, WHITE, BLUE2])
        c.box(31, 30, 32, 34, BLACK)
        c.hline(9, 54, 50, BLUE3)
        return c.done()

    def prefs(self):
        c = PixelCanvas(64)
        cx, cy = 32, 27

        def gear(x, y):
            r = math.hypot(x - cx, y - cy)
            a = (math.degrees(math.atan2(y - cy, x - cx)) + 360) % 45
            return 6 < r <= 16 or (16 < r <= 21 and 12 < a < 33)

        def col(x, y):
            r = math.hypot(x + .5 - cx, y + .5 - cy)
            if r < 11.5:
                return BLUE if y < cy + 2 else BLUE3
            return WHITE if y < cy - 4 else BLUE2 if y < cy + 8 else mix(BLUE2, BLUE, .6)

        c.shape(gear, col)
        c.vband(8, 53, 55, 57, [BLUE, BLUE3, DEEP])
        c.vband(36, 50, 42, 60, [WHITE, BLUE2, BLUE, BLUE3])
        return c.done()

    def tool(self):
        """a potion flask"""
        c = PixelCanvas(64)
        cx, cy, r = 32, 41, 18

        def flask(x, y):
            return (math.hypot(x - cx, y - cy) <= r) or (26 <= x <= 38 and 10 <= y <= 30)

        def colour(x, y):
            if y >= 37:
                if (x, y) in ((24, 44), (25, 44), (38, 49), (31, 53), (35, 41), (28, 47)):
                    return WHITE
                return BLUE if y < 47 else BLUE3 if y < 54 else DEEP
            return WHITE if x < 33 else BLUE2

        c.shape(flask, colour)
        c.hline(16, 48, 37, BLUE2)
        c.vband(24, 4, 40, 10, [WHITE, BLUE2, BLUE])
        c.px([(23, 33), (22, 34), (21, 36), (20, 38), (19, 40)], WHITE)
        return c.done()

    # emblems: shaded pixel sprites
    def em_music(self):
        c = PixelCanvas(28)
        m = pramp(MAGENTA)
        c.sprite(3, 2, [
            "........XXXXXXXXXXXX",
            "......XXLLLLLLLLLLLX",
            "......XLMMMMMMMMMMMX",
            "......XMMXXXXXXXXMMX",
            "......XLMX......XLMX",
            "......XLMX......XLMX",
            "......XLMX......XLMX",
            "......XLMX......XLMX",
            "......XLMX......XLMX",
            "......XLMX......XLMX",
            "......XLMX......XLMX",
            "......XLMX...XXXXLMX",
            "......XLMX..XLLLMMMX",
            "..XXXXXLMX.XLMMMMMDX",
            ".XLLLMMMMX.XMMMMMMDX",
            "XLLMMMMMMX.XMMMMMDX.",
            "XMMMMMMMDX..XXXXXX..",
            "XMMMMMMDX...........",
            ".XXXXXXX............",
        ], {"X": BLACK, "L": m[0], "M": m[2], "D": m[3]})
        return c.done((1, 1, 0))

    def em_games(self):
        c = PixelCanvas(28)
        o = pramp(ORANGE)
        r = pramp(RED)
        c.sprite(3, 2, [
            "....XXXX...........",
            "...XLRRRX..........",
            "..XLWLRRRX.........",
            "..XLLRRRRX.........",
            "..XRRRRRDX.........",
            "...XRRRDX..........",
            "....XXXX...........",
            ".....XKX...........",
            ".....XKX...........",
            ".....XKX...........",
            ".....XKX...........",
            ".....XKX....XXX....",
            "XXXXXXKXXXXXXYXXXX.",
            "XoooooooooooXXXoooX",
            "XOOOOOOOOOOOOOOOOOX",
            "XOOOOOOOOOOOOOOOODX",
            "XXXXXXXXXXXXXXXXXXX",
        ], {"X": BLACK, "L": r[0], "R": r[2], "D": r[3], "W": WHITE, "K": (70, 70, 80, 255),
            "o": o[0], "O": o[2], "Y": YELLOW})
        return c.done((1, 1, 0))

    def em_picture(self):
        c = PixelCanvas(28)
        for y in range(5, 23):
            c.hline(2, 24, y, lighten(SKY, .5) if y < 9 else lighten(SKY, .25) if y < 14 else SKY)
        c.sprite(18, 6, [".YY.", "YWYY", "YYYY", ".YY."], {"Y": YELLOW, "W": WHITE})
        g = pramp(GREEN)
        c.d.polygon([(2, 22), (9, 12), (14, 18), (17, 15), (24, 22)], fill=g[2])
        c.px([(9, 12), (8, 13), (10, 13), (17, 15), (16, 16)], g[0])
        c.box(1, 4, 25, 23, None, BLACK)
        return c.done((1, 1, 0))


SETS = [Cargo(), Holo(), Hud(), Blueprint(), Pixel()]

ICONS = [
    ("01", "drawer", "drawer", [], "drawer"),
    ("02", "drawer_open", "drawer_open", [], "drawer, selected (open)"),
    ("03", "music", "drawer", ["EMBLEM=EmMusic,{at}"], "drawer + music emblem"),
    ("04", "games", "drawer", ["EMBLEM=EmGames,{at}"], "drawer + games emblem"),
    ("05", "file", "file", [], "file"),
    ("06", "picture", "file", ["EMBLEM=EmPicture,{at}"], "file + picture emblem"),
    ("07", "device", "device", [], "device (disk)"),
    ("08", "archive", "archive", [], "archive"),
    ("09", "prefs", "prefs", [], "preferences"),
    ("10", "tool", "tool", [], "tool (program)"),
]

DEFAULT_PREFS = "EMBLEMMETHOD=SHADOW\n"
BG = (190, 192, 190, 255)   # about the guest's Workbench backdrop


def build_set(n, s, out):
    d = os.path.join(out, f"T{n}")
    os.makedirs(d, exist_ok=True)
    for name in ("drawer", "drawer_open", "file", "device", "archive", "prefs", "tool"):
        getattr(s, name)().save(os.path.join(d, name + ".png"))
    s.em_music().save(os.path.join(d, "EmMusic.png"))
    s.em_games().save(os.path.join(d, "EmGames.png"))
    s.em_picture().save(os.path.join(d, "EmPicture.png"))
    prefs = os.path.join(d, "emblem.prefs")
    open(prefs, "w").write(getattr(s, "prefs_text", DEFAULT_PREFS))
    icons = []
    for iid, name, base, tts, caption in ICONS:
        tts = [t.format(at=s.emblem_at) for t in tts]
        if not tts:
            im = Image.open(os.path.join(d, base + ".png")).convert("RGBA")
        else:
            pre = os.path.join(d, "_r")
            r = subprocess.run([RENDER, "--dir", d, "--prefs", prefs, "--out", pre, f"IMAGE={base}"] + tts,
                               capture_output=True, text=True).stdout
            assert "composed=1" in r, (n, name, r)
            im = Image.open(pre + "_1.png").convert("RGBA")
            os.remove(pre + "_1.png")
        im.save(os.path.join(d, f"{iid}_{name}.png"))
        icons.append((f"T{n}-{iid}", caption, im))
    return icons


def sheet(n, s, icons, path):
    cell, scale, cols = 64, 2, 5
    w, h = cell * scale + 24, cell * scale + 34
    top = 44
    strip = 64 + 26
    W, H = w * cols, top + h * 2 + strip * 2 + 10
    out = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    dr = ImageDraw.Draw(out)
    dr.text((10, 8), f"T{n}  {s.name}", fill=(0, 0, 0))
    dr.text((10, 24), s.blurb, fill=(90, 90, 90))
    for k, (iid, cap, im) in enumerate(icons):
        x, y = (k % cols) * w + 10, top + (k // cols) * h
        bg = Image.new("RGBA", (cell * scale, cell * scale), BG)
        bg.alpha_composite(im.resize((cell * scale, cell * scale), Image.NEAREST))
        out.paste(bg, (x, y))
        dr.text((x, y + cell * scale + 4), f"{iid}  {cap}", fill=(0, 0, 0))
    y = top + h * 2 + 4
    for label, col in (("real size, light backdrop", (226, 228, 226, 255)), ("real size, dark backdrop", (52, 56, 64, 255))):
        dr.rectangle((0, y, W, y + strip - 4), fill=col)
        dr.text((10, y + 3), label, fill=(0, 0, 0) if col[0] > 128 else (230, 230, 230))
        for k, (_, _, im) in enumerate(icons):
            out.alpha_composite(im, (14 + k * 74, y + 15))
        y += strip
    out.convert("RGB").save(path)


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    allicons = []
    for n, s in enumerate(SETS, 1):
        icons = build_set(n, s, out)
        sheet(n, s, icons, os.path.join(out, f"T{n}.png"))
        allicons.append((n, s, icons))
    rowh = 64 * 2 + 30
    ov = Image.new("RGBA", (10 * 136 + 140, rowh * len(allicons) + 10), (255, 255, 255, 255))
    dr = ImageDraw.Draw(ov)
    for r, (n, s, icons) in enumerate(allicons):
        y = r * rowh + 6
        dr.text((8, y + 56), f"T{n}\n{s.name}", fill=(0, 0, 0))
        for k, (_, _, im) in enumerate(icons):
            bg = Image.new("RGBA", (128, 128), BG)
            bg.alpha_composite(im.resize((128, 128), Image.NEAREST))
            ov.paste(bg, (130 + k * 136, y))
    ov.convert("RGB").save(os.path.join(out, "overview.png"))
    print(f"{len(SETS)} sets -> {out}")


if __name__ == "__main__":
    main()
