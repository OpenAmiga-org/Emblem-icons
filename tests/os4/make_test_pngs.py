#!/home/claude/build/emblem-venv/bin/python
"""Test images for the step 2 guest tests (run_os4.py calls this).

Writes build/os4test/*.png (to upload to ENVARC:sys/emblem/) and
build/os4test/expected.json: width, height and CRC-32 of the A,R,G,B bytes
each image must decode to, plus the expected centred selected images.
"""
import json
import os
import shutil
import sys
import zlib

import png

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "build", "os4test")
SUITE = os.path.join(ROOT, "tests", "samples", "pngsuite")
sys.path.insert(0, os.path.join(ROOT, "tests", "host"))
from make_png_refs import convert  # noqa: E402


def write_rgba(path, w, h, fn):
    rows = []
    argb = bytearray()
    for y in range(h):
        row = []
        for x in range(w):
            r, g, b, a = fn(x, y)
            row += [r, g, b, a]
            argb += bytes((a, r, g, b))
        rows.append(row)
    with open(path, "wb") as f:
        png.Writer(w, h, greyscale=False, alpha=True).write(f, rows)
    return w, h, bytes(argb)


def centred(dw, dh, src, sw, sh):
    """cp_place_centred(): C integer division truncates toward zero."""
    ox, oy = int((dw - sw) / 2), int((dh - sh) / 2)
    out = bytearray(dw * dh * 4)
    for y in range(sh):
        ty = oy + y
        if not 0 <= ty < dh:
            continue
        for x in range(sw):
            tx = ox + x
            if 0 <= tx < dw:
                out[4 * (ty * dw + tx):4 * (ty * dw + tx) + 4] = src[4 * (y * sw + x):4 * (y * sw + x) + 4]
    return bytes(out)


def icontest_argb_selected(w=48, h=40):
    """The selected image of 'icontest make argb' (see tests/os4/icontest.c) as it
    is after icon.library saved it natively: fully transparent pixels lose their colour."""
    out = bytearray()
    for y in range(h):
        for x in range(w):
            if x < 2 or y < 2 or x >= w - 2 or y >= h - 2:
                out += bytes(4)
            else:
                out += bytes((0xFF, 255 - x * 255 // w, 0x20, y * 255 // h))
    return bytes(out)


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    exp = {}

    def add(name, w, h, argb):
        exp[name] = {"w": w, "h": h, "crc": "%08X" % zlib.crc32(argb)}
        return argb

    ns = add("EmblemTestNS", *write_rgba(os.path.join(OUT, "EmblemTestNS.png"), 64, 64,
             lambda x, y: (x * 4, y * 4, 128, 255 if 4 <= x < 60 and 4 <= y < 60 else (x * 8) & 255)))
    add("EmblemTestS", *write_rgba(os.path.join(OUT, "EmblemTestS.png"), 64, 64,
        lambda x, y: (255 - x * 4, 64, y * 4, 255 if 6 <= x < 58 and 6 <= y < 58 else 0)))
    big = add("EmblemTestBig", *write_rgba(os.path.join(OUT, "EmblemTestBig.png"), 80, 60,
              lambda x, y: ((x * 3) & 255, (y * 4) & 255, (x ^ y) & 255, 200)))
    add("EmblemTestHuge", *write_rgba(os.path.join(OUT, "EmblemTestHuge.png"), 300, 8,
        lambda x, y: (x & 255, 0, 0, 255)))
    add("EmblemTestNS2", *write_rgba(os.path.join(OUT, "EmblemTestNS2.png"), 64, 64,
        lambda x, y: (10, (x + y) & 255, 200, 255)))
    # emblems: a round badge with a soft edge (partial alpha), a small striped one
    def badge(x, y):
        dx, dy = x - 11.5, y - 11.5
        d = (dx * dx + dy * dy) ** 0.5
        a = 255 if d < 10 else (0 if d > 12 else int((12 - d) * 127))
        return (220, 40 + x * 8, 40, a)
    add("EmblemTestE1", *write_rgba(os.path.join(OUT, "EmblemTestE1.png"), 24, 24, badge))
    add("EmblemTestE2", *write_rgba(os.path.join(OUT, "EmblemTestE2.png"), 16, 10,
        lambda x, y: ((x * 16) & 255, 255 if y % 3 else 0, 90, 160 if x % 4 else 255)))
    for s in ("basn3p04", "basi6a16", "tbrn2c08", "basn0g01", "basi3p02"):
        w, h, argb = convert(os.path.join(SUITE, s + ".png"))
        shutil.copy(os.path.join(SUITE, s + ".png"), os.path.join(OUT, f"EmblemTest_{s}.png"))
        add(f"EmblemTest_{s}", w, h, bytes(argb))

    exp["centred_big_on_ns"] = {"crc": "%08X" % zlib.crc32(centred(64, 64, big, 80, 60))}
    exp["centred_argbsel_on_ns"] = {"crc": "%08X" % zlib.crc32(centred(64, 64, icontest_argb_selected(), 48, 40))}
    a1 = b"".join(bytes(((0xFF102030 + i) >> 24 & 255, (0xFF102030 + i) >> 16 & 255,
                         (0xFF102030 + i) >> 8 & 255, (0xFF102030 + i) & 255)) for i in range(400))
    exp["setimg1"] = {"crc": "%08X" % zlib.crc32(a1)}
    json.dump(exp, open(os.path.join(OUT, "expected.json"), "w"), indent=1)
    print(f"{len(os.listdir(OUT)) - 1} test images in {OUT}")


if __name__ == "__main__":
    main()
