#!/usr/bin/env python3
"""make_bad_files.py OUTDIR GOOD.info...

Broken and odd variants of good Emblem icon files for the step 5 guest test
(run_os4.py). Writes OUTDIR/bad/*.info (must not crash anything; loading
may fail) and OUTDIR/odd/*.info (unusual but valid: must load).
"""
import os
import random
import struct
import sys


def chunks(b):
    """[(offset, id, length)] of the chunks after FORM....EMBL"""
    out, pos = [], 12
    while pos + 8 <= len(b):
        cid, ln = b[pos:pos + 4], struct.unpack(">I", b[pos + 4:pos + 8])[0]
        out.append((pos, cid, ln))
        pos += 8 + ln + (ln & 1)
    return out


def setu32(b, off, v):
    b[off:off + 4] = struct.pack(">I", v & 0xFFFFFFFF)


def setu16(b, off, v):
    b[off:off + 2] = struct.pack(">H", v & 0xFFFF)


def rebuild(parts):
    body = b"EMBL" + b"".join(parts)
    return b"FORM" + struct.pack(">I", len(body)) + body


def chunk_bytes(b, off, ln):
    return bytes(b[off:off + 8 + ln + (ln & 1)])


def variants(good, tag, rnd):
    v = {}
    n = len(good)
    for cut in sorted({0, 1, 11, 12, 23, 24, 43, 44, 57, 58, 59, n // 3, n // 2, n - 2, n - 1}):
        if 0 <= cut < n:
            v[f"trunc{cut}"] = good[:cut]
    b = bytearray(good); setu32(b, 4, 0x7FFFFFFF); v["form_huge"] = b
    b = bytearray(good); setu32(b, 4, 36); v["form_small"] = b
    b = bytearray(good); setu32(b, 4, n - 8 + 5); v["form_long"] = b
    b = bytearray(good); setu16(b, 20, 2); v["head_version2"] = b
    b = bytearray(good); setu16(b, 20, 0xFFFF); v["head_version_ffff"] = b
    b = bytearray(good); b[22] = 0; v["head_type0"] = b
    b = bytearray(good); b[22] = 255; v["head_type255"] = b
    b = bytearray(good); setu32(b, 16, 0); v["head_len0"] = b
    for i, (off, cid, ln) in enumerate(chunks(good)):
        name = cid.decode("latin-1").strip()
        for what, val in (("ffff", 0xFFFFFFFF), ("plus", ln + 1000), ("minus1", ln - 1), ("zero", 0)):
            if val < 0:
                continue
            b = bytearray(good); setu32(b, off + 4, val); v[f"c{i}_{name}_{what}"] = b
        d = off + 8
        if cid == b"IMAG" and ln >= 12:
            kind = good[d + 1]
            for what, fn in (("w0", lambda b: setu16(b, d + 4, 0)), ("w65535", lambda b: setu16(b, d + 4, 65535)),
                             ("w257", lambda b: setu16(b, d + 4, 257)), ("h0", lambda b: setu16(b, d + 6, 0)),
                             ("kind0", lambda b: b.__setitem__(d + 1, 0)), ("kind9", lambda b: b.__setitem__(d + 1, 9)),
                             ("comp2", lambda b: b.__setitem__(d + 2, 2)), ("state5", lambda b: b.__setitem__(d, 5))):
                b = bytearray(good); fn(b); v[f"c{i}_{what}"] = b
            hdr = 8 + (4 + 3 * struct.unpack(">H", good[d + 8:d + 10])[0] if kind == 2 else 8 if kind == 3 else 0)
            if hdr + 4 <= ln:
                dl = struct.unpack(">I", good[d + hdr:d + hdr + 4])[0]
                for what, val in (("dl_plus1", dl + 1), ("dl_minus1", dl - 1), ("dl_huge", 0xFFFFFFF0)):
                    b = bytearray(good); setu32(b, d + hdr, val); v[f"c{i}_{what}"] = b
                # garbage in the (compressed) pixel data
                for k in range(4):
                    b = bytearray(good)
                    for _ in range(1 + k * 3):
                        p = d + hdr + 4 + rnd.randrange(max(1, ln - hdr - 4))
                        b[p] = rnd.randrange(256)
                    v[f"c{i}_pixgarbage{k}"] = b
            if kind == 2:
                for what, fn in (("pal0", lambda b: setu16(b, d + 8, 0)), ("pal300", lambda b: setu16(b, d + 8, 300)),
                                 ("trans999", lambda b: setu16(b, d + 10, 999))):
                    b = bytearray(good); fn(b); v[f"c{i}_{what}"] = b
            if kind == 3:
                for what, val in (("depth0", 0), ("depth9", 9), ("depth8", 8)):
                    b = bytearray(good); setu16(b, d + 12, val); v[f"c{i}_{what}"] = b
        if cid == b"TTYP" and ln >= 1:
            b = bytearray(good); b[d + ln - 1] = ord("X"); v[f"c{i}_ttyp_nonul"] = b
        if cid == b"DRAW":
            b = bytearray(good); setu32(b, off + 4, 10); v[f"c{i}_draw_short"] = b
    for k in range(120):
        b = bytearray(good)
        for _ in range(1 + rnd.randrange(8)):
            b[12 + rnd.randrange(n - 12)] = rnd.randrange(256)
        v[f"rnd{k}"] = b
    return {f"{tag}_{k}": bytes(b) for k, b in v.items()}


def odd_variants(good, tag):
    """unusual but valid files"""
    v = {}
    cs = chunks(good)
    parts = [chunk_bytes(good, off, ln) for off, cid, ln in cs]
    # without drawer data (a drawer icon must still open on Workbench)
    if any(cid == b"DRAW" for _, cid, _ in cs):
        v["nodraw"] = rebuild([chunk_bytes(good, off, ln) for off, cid, ln in cs if cid != b"DRAW"])
    # 200 KB of tool types
    tt = b"".join(b"KEY%05d=" % i + b"v" * 30 + b"\0" for i in range(5000))
    v["bigtt"] = rebuild([p for (off, cid, ln), p in zip(cs, parts) if cid != b"TTYP"]
                         + [b"TTYP" + struct.pack(">I", len(tt)) + tt + (b"\0" if len(tt) & 1 else b"")])
    # an unknown chunk and a PAD chunk
    v["extra_chunks"] = rebuild(parts + [b"XTRA" + struct.pack(">I", 3) + b"abc\0", b"PAD " + struct.pack(">I", 4) + bytes(4)])
    # no images at all
    v["noimages"] = rebuild([p for (off, cid, ln), p in zip(cs, parts) if cid != b"IMAG"] + [b"PAD " + struct.pack(">I", 20) + bytes(20)])
    return {f"{tag}_{k}": b for k, b in v.items()}


def main():
    out = sys.argv[1]
    rnd = random.Random(5)
    for sub in ("bad", "odd"):
        d = os.path.join(out, sub)
        os.makedirs(d, exist_ok=True)
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))
    nb = no = 0
    for path in sys.argv[2:]:
        good = open(path, "rb").read()
        tag = os.path.basename(path).split(".")[0]
        for name, data in variants(good, tag, rnd).items():
            open(os.path.join(out, "bad", name + ".info"), "wb").write(data)
            nb += 1
        for name, data in odd_variants(good, tag).items():
            open(os.path.join(out, "odd", name + ".info"), "wb").write(data)
            no += 1
    print(f"{nb} broken, {no} odd files in {out}")


if __name__ == "__main__":
    main()
