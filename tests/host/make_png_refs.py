#!/home/claude/build/emblem-venv/bin/python
"""Reference ARGB dumps for the PNG decoder test, made with pypng.

For every tests/samples/pngsuite/*.png that is not a corrupt one (x*.png),
writes build/pngref/<name>.argb: 8-byte header (u32 width, u32 height,
big-endian) and then A, R, G, B bytes per pixel, by the decoder's rules:
16-bit samples keep the high byte, low gray depths scale by 255/(2^d-1),
palette alpha from tRNS, gray/RGB tRNS keys compared on the raw values.
"""
import os
import struct
import sys

import png

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "tests", "samples", "pngsuite")
DST = os.path.join(ROOT, "build", "pngref")


def to8(v, depth):
    if depth == 16:
        return v >> 8
    return {1: 255, 2: 85, 4: 17, 8: 1}[depth] * v


def convert(path):
    r = png.Reader(filename=path)
    w, h, rows, info = r.read()
    depth = info["bitdepth"]
    out = bytearray()
    if "palette" in info and info["planes"] == 1 and not info["greyscale"]:
        pal = info["palette"]
        for row in rows:
            for c in row:
                e = pal[c] if c < len(pal) else (0, 0, 0)
                out += bytes((e[3] if len(e) == 4 else 255, e[0], e[1], e[2]))
        return w, h, out
    planes = info["planes"]
    key = info.get("transparent")
    for row in rows:
        row = list(row)
        for i in range(0, len(row), planes):
            px = row[i:i + planes]
            if info["greyscale"]:
                g = px[0]
                a = to8(px[1], depth) if info["alpha"] else (0 if key is not None and g == key[0] else 255)
                g8 = to8(g, depth)
                out += bytes((a, g8, g8, g8))
            else:
                rr, gg, bb = px[0], px[1], px[2]
                if info["alpha"]:
                    a = to8(px[3], depth)
                else:
                    a = 0 if key is not None and (rr, gg, bb) == tuple(key) else 255
                out += bytes((a, to8(rr, depth), to8(gg, depth), to8(bb, depth)))
    return w, h, out


def main():
    os.makedirs(DST, exist_ok=True)
    n = 0
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(".png") or f.startswith("x"):
            continue
        try:
            w, h, data = convert(os.path.join(SRC, f))
        except Exception as e:
            print(f"skip {f}: {e}")
            continue
        open(os.path.join(DST, f[:-4] + ".argb"), "wb").write(struct.pack(">II", w, h) + data)
        n += 1
    print(f"{n} references in {DST}")


if __name__ == "__main__":
    sys.exit(main())
