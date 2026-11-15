#!/home/claude/build/amiga-fleet-venv/bin/python
"""run_os4.py: tests of emblem.iconmodule in the OS4 guest, driven from the
host through MCPd (amiga_fleet_mcp).

Needs: build/os4/{emblem.iconmodule,EmblemIcon,icontest} ("make os4") and a
running guest reachable as target "os4-amigaone".

  run_os4.py            test with the module already installed in the guest
  run_os4.py --deploy   install build/os4/emblem.iconmodule, reboot, then test
  run_os4.py --step=2   only the step 2 tests (default: all)

Step 1, for every test icon (made natively by icontest, plus copies of system
icons), comparing the icon's own data (icontest raw dump):
 1. dump native -> EmblemIcon TO=EMBLEM -> dump: same apart from the format
 2. tool type edit + save keeps the Emblem format (Information window path)
 3. snapshot (ICONPUTA_OnlyUpdatePosition) changes only the 8 position bytes
 4. DupDiskObject + save under a new name stays Emblem and identical
 5. EmblemIcon TO=AMIGA -> dump: same as the original native dump

Step 2 (IMAGE=/IMAGESELECTED= default images from ENVARC:sys/emblem, test
images from tests/os4/make_test_pngs.py):
 - composed images are the decoded PNGs (CRC), also for PngSuite colour types
 - the icon's own images survive every save of a composed icon, a duplicate
   and the conversion back to a native icon
 - missing or too large images are ignored; a changed file shows after 2 s
 - a program that sets new images makes them the icon's own

Step 3 (EMBLEM=/EMBLEMSELECTED=, sizes, positions, clipping, INTERNAL, the
NONE/DARK/BRIGHT/GRAY methods): for each case the module's images must be
exactly what build/host/render makes from the icon's own images (icontest
pixels) and the same tool types; the icon's own images stay in the file.

Step 4 (SHADOW, GLOW, emblem.prefs): the same comparison with the built-in
settings and with prefs files in ENV:sys (and ENVARC:sys only); the host
renderer gets the same file with --prefs.

Step 5 (robustness and speed): see plan section 13 and --only= below.

Step 6 (the package, dist/Emblem.lha from tools/make_lha.sh; only with
--step=6, as it takes the module out of the guest, installs it with the
Install script, removes it again and resets the guest three times): Install
run by the Installation Utility in Novice mode (ENV:EmblemInstallTest), the
welcome and the last window clicked; files in place; an update run keeps the
settings and the user's own images; after a restart the ten examples are
exactly the host renders (art/, the installed settings); Remove turns a
user's Emblem icon back into a native one with its own picture and tool
types and leaves the system as it was before the install.
"""
import asyncio
import json
import os
import random
import re
import struct
import subprocess
import socket
import sys
import time

from amiga_fleet_mcp.config import load_config
from amiga_fleet_mcp.fleet import Fleet
from amiga_fleet_mcp.tools import fs as fs_tool

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OS4 = os.path.join(ROOT, "build", "os4")
WORK = os.path.join(ROOT, "build", "work")
TARGET = "os4-amigaone"
MONITOR = os.path.expanduser("~/build/os4-qemu/monitor.sock")
G = "RAM:et"
G2 = "RAM:et2"
G3 = "RAM:et3"
G4 = "RAM:et4"
RENDER = os.path.join(ROOT, "build", "host", "render")
IMGDIR = "ENVARC:sys/emblem"
TESTPNG = os.path.join(ROOT, "build", "os4test")

MADE = ["argb", "argb1", "clut", "clut1", "planar", "drawer"]
SYSTEM = ["SYS:Devs", "SYS:Prefs", "SYS:Utilities/Clock", "SYS:Disk", "SYS:Utilities/MultiView",
          "SYS:Prefs/Workbench", "SYS:Tools/Commodities/Exchange"]

results = []


def ok(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  {detail}"), flush=True)
    return bool(cond)


class Guest:
    def __init__(self):
        self.fleet = Fleet(load_config())
        self.m = self.fleet.mcpd(TARGET)

    async def cmd(self, command, timeout=60):
        r = await self.m.request("exec.cmd", {"command": command, "timeout_ms": timeout * 1000},
                                 timeout_s=timeout + 30)
        return r.get("exit_code", -1), r.get("output", "")

    async def up(self, local, remote):
        if os.path.getsize(local) == 0:
            # the upload tool can't make an empty file: a redirection can
            await self.cmd(f'Echo >"{remote}" NOLINE ""', timeout=10)
            return
        await fs_tool.fs_upload(self.fleet, TARGET, local_path=local, remote_path=remote, verify=True)

    async def down(self, remote, local):
        if os.path.exists(local):
            os.remove(local)
        await fs_tool.fs_download(self.fleet, TARGET, remote_path=remote, local_path=local)
        return open(local, "rb").read()

    async def dump(self, name, raw=True):
        """raw: the icon's own images (EMBLEMA_NoCompose); else what programs see"""
        rc, out = await self.cmd(f"{G}/icontest {'raw ' if raw else ''}dump {name}")
        return rc, [l for l in out.splitlines() if l.strip()]


def monitor(cmd):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(MONITOR)
    s.recv(4096)
    s.sendall((cmd + "\n").encode())
    time.sleep(0.5)
    s.close()


async def wait_up(g, limit=180):
    t0 = time.time()
    await asyncio.sleep(10)
    while time.time() - t0 < limit:
        try:
            rc, out = await g.cmd("Echo up", timeout=5)
            if "up" in out:
                return True
        except Exception:
            pass
        await asyncio.sleep(3)
    return False


def strip_format(lines):
    return [l for l in lines if not l.startswith("format=")]


def fmt(lines):
    for l in lines:
        if l.startswith("format="):
            return l[7:]
    return None


async def main():
    os.makedirs(WORK, exist_ok=True)
    g = Guest()

    if "--deploy" in sys.argv:
        await g.cmd("MakeDir LIBS:IconModules", timeout=10)
        await g.up(os.path.join(OS4, "emblem.iconmodule"), "LIBS:IconModules/emblem.iconmodule")
        await g.cmd("Wait 3", timeout=10)
        monitor("system_reset")
        g = Guest()
        if not await wait_up(g):
            print("guest did not come back")
            return 2

    if "--step=6" in sys.argv:          # alone: it installs and removes the module itself
        g = await step6(g)
        passed = sum(1 for _, c in results if c)
        print(f"\n{passed}/{len(results)} passed")
        return 0 if passed == len(results) else 1

    await g.cmd(f"Delete {G} ALL QUIET FORCE", timeout=20)
    await g.cmd(f"MakeDir {G}", timeout=10)
    await g.up(os.path.join(OS4, "EmblemIcon"), f"{G}/EmblemIcon")
    await g.up(os.path.join(OS4, "icontest"), f"{G}/icontest")
    rc, out = await g.cmd("Version emblem.iconmodule", timeout=10)
    ok("module in memory", rc == 0 and "emblem.iconmodule" in out, out.strip())

    steps = {int(a.split("=")[1]) for a in sys.argv if a.startswith("--step=")} or {1, 2, 3, 4, 5}
    if 1 in steps:
        await step1(g)
    if 2 in steps:
        await step2(g)
    if 3 in steps:
        await step3(g)
    if 4 in steps:
        await step4(g)
    if 5 in steps:
        await step5(g)

    passed = sum(1 for _, c in results if c)
    print(f"\n{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


async def step1(g):
    names = []
    for k in MADE:
        rc, out = await g.cmd(f"{G}/icontest make {k} {G}/{k}")
        ok(f"make {k}", rc == 0, out.strip())
        if rc == 0:
            names.append(f"{G}/{k}")
    for s in SYSTEM:
        base = s.split("/")[-1].split(":")[-1]
        rc, out = await g.cmd(f"Copy {s}.info {G}/sys_{base}.info QUIET", timeout=20)
        if rc == 0:
            names.append(f"{G}/sys_{base}")
        else:
            print(f"(skip {s}.info: not found)")

    for n in names:
        short = n.split("/")[-1]
        rc, orig = await g.dump(n)
        if not ok(f"{short}: native dump", rc == 0 and fmt(orig) == "Amiga", "\n".join(orig)):
            continue

        rc, out = await g.cmd(f"{G}/EmblemIcon {n} TO=EMBLEM")
        ok(f"{short}: to Emblem", rc == 0 and "converted to Emblem" in out, out.strip())
        rc, conv = await g.dump(n)
        ok(f"{short}: Emblem format", fmt(conv) == "Emblem", "\n".join(conv))
        diff = [(a, b) for a, b in zip(strip_format(orig), strip_format(conv)) if a != b]
        same = strip_format(orig) == strip_format(conv)
        ok(f"{short}: same as native", same,
           "; ".join(f"{a} -> {b}" for a, b in diff) or f"{len(orig)} vs {len(conv)} lines")

        # 2. tool type edit
        rc, out = await g.cmd(f'{G}/icontest tt {n} "NEWTT=1"')
        rc2, d = await g.dump(n)
        ok(f"{short}: tool type edit keeps Emblem", rc == 0 and fmt(d) == "Emblem" and "tt=NEWTT=1" in d,
           out.strip() + " | " + " ".join(d[:3]))
        expect = strip_format(orig)
        # the new tool type comes after the old ones
        tts = [l for l in expect if l.startswith("tt=")]
        if tts:
            i = expect.index(tts[-1]) + 1
        else:
            i = [j for j, l in enumerate(expect) if l.startswith("deftool=")][0] + 1
        expect = expect[:i] + ["tt=NEWTT=1"] + expect[i:]
        ok(f"{short}: only the tool type changed", strip_format(d) == expect,
           "; ".join(f"{a} -> {b}" for a, b in zip(expect, strip_format(d)) if a != b))

        # 3. snapshot
        local = os.path.join(WORK, short + ".before")
        before = await g.down(n + ".info", local)
        rc, out = await g.cmd(f"{G}/icontest pos {n} 111 222")
        after = await g.down(n + ".info", local + ".after")
        changed = [i for i in range(min(len(before), len(after))) if before[i] != after[i]]
        ok(f"{short}: snapshot rewrites only the position",
           rc == 0 and len(before) == len(after) and all(32 <= i < 40 for i in changed),
           f"rc {rc}, sizes {len(before)}/{len(after)}, changed bytes {changed[:10]}")
        rc, d = await g.dump(n)
        ok(f"{short}: snapshot position", "pos=111,222" in d and fmt(d) == "Emblem", " ".join(d[:6]))

        # 3b. saved after a Workbench layout (screen-remapped images must not be saved)
        rc, out = await g.cmd(f"{G}/icontest layoutsave {n} 54321")
        rc2, dl = await g.dump(n)
        expect_l = [("stack=54321" if l.startswith("stack=") else l) for l in strip_format(d)]
        ok(f"{short}: save after layout keeps everything", rc == 0 and fmt(dl) == "Emblem"
           and strip_format(dl) == expect_l,
           out.strip() + " | " + "; ".join(f"{a} -> {b}" for a, b in zip(expect_l, strip_format(dl)) if a != b))
        await g.cmd(f"{G}/icontest layoutsave {n} {orig_stack(orig)}")
        rc, d = await g.dump(n)

        # 4. duplicate
        rc, out = await g.cmd(f"{G}/icontest dup {n} {n}_dup")
        rc2, dd = await g.dump(n + "_dup")
        ok(f"{short}: duplicate stays Emblem and identical", rc == 0 and fmt(dd) == "Emblem"
           and strip_format(dd) == strip_format(d), out.strip())

        # 5. back to native
        await g.cmd(f"{G}/icontest pos {n} {orig_pos(orig)}")
        rc, out = await g.cmd(f"{G}/EmblemIcon {n} TO=AMIGA")
        rc2, back = await g.dump(n)
        expect = [l for l in strip_format(orig)]
        tts = [l for l in expect if l.startswith("tt=")]
        if tts:
            i = expect.index(tts[-1]) + 1
        else:
            i = [j for j, l in enumerate(expect) if l.startswith("deftool=")][0] + 1
        expect = expect[:i] + ["tt=NEWTT=1"] + expect[i:]
        ok(f"{short}: back to Amiga, same as before", rc == 0 and fmt(back) == "Amiga"
           and strip_format(back) == expect,
           out.strip() + " | " + "; ".join(f"{a} -> {b}" for a, b in zip(expect, strip_format(back)) if a != b))

    # EmblemIcon on a missing icon and on an already converted one
    rc, out = await g.cmd(f"{G}/EmblemIcon {G}/nonexistent TO=EMBLEM")
    ok("missing icon: error, rc 10", rc == 10 and out.startswith("Error:"), out.strip())

    await step1_set(g)


def tts(lines):
    return [l[3:] for l in lines if l.startswith("tt=")]


def no_tts(lines):
    return [l for l in strip_format(lines) if not l.startswith("tt=")]


async def step1_set(g):
    """EmblemIcon 1.1: SET, UNSET and TYPE (bulk tool types)"""
    T = f"{G}/tt"
    EI = f"{G}/EmblemIcon"
    await g.cmd(f"Delete {T} ALL QUIET FORCE", timeout=20)
    await g.cmd(f"MakeDir {T}", timeout=10)
    for src, dst in (("drawer", "d1"), ("drawer", "d2"), ("argb", "p1"), ("argb", "p2")):
        await g.cmd(f"Copy {G}/{src}.info {T}/{dst}.info QUIET", timeout=10)
    rc, d1n = await g.dump(f"{T}/d1")
    rc, p1n = await g.dump(f"{T}/p1")
    ok("SET test icons: d1 a drawer, p1 not", val(d1n, "type") == "2" and val(p1n, "type") != "2",
       f"{val(d1n, 'type')} {val(p1n, 'type')}")

    # convert and set in one go; the icon's own images and other data stay
    rc, out = await g.cmd(f'{EI} {T}/d1 TO=EMBLEM SET="IMAGE=GlassDrawer|EMBLEM=INTERNAL,30,30,33,30"')
    rc2, d1 = await g.dump(f"{T}/d1")
    ok("SET with TO=EMBLEM: converted, tool types added", rc == 0 and "converted to Emblem, tool types changed" in out
       and fmt(d1) == "Emblem" and tts(d1) == tts(d1n) + ["IMAGE=GlassDrawer", "EMBLEM=INTERNAL,30,30,33,30"], out + " " + str(tts(d1)))
    ok("SET with TO=EMBLEM: own images and data unchanged", no_tts(d1) == no_tts(d1n), diffs(no_tts(d1n), no_tts(d1)))

    # replace in place (key case ignored), duplicates removed
    await g.cmd(f'{G}/icontest tt {T}/d1 "IMAGE=Duplicate"')
    rc, out = await g.cmd(f'{EI} {T}/d1 SET="image=Other"')
    rc2, d1b = await g.dump(f"{T}/d1")
    want = tts(d1n) + ["image=Other", "EMBLEM=INTERNAL,30,30,33,30"]
    ok("SET replaces the first IMAGE in place and drops the duplicate", rc == 0 and tts(d1b) == want and fmt(d1b) == "Emblem",
       f"{out} {tts(d1b)}")
    rc, out = await g.cmd(f'{EI} {T}/d1 SET="image=Other"')
    ok("SET again: no change", rc == 0 and "no change" in out, out)

    # back to native without the tool types: as it was
    rc, out = await g.cmd(f'{EI} {T}/d1 TO=AMIGA UNSET="IMAGE|emblem"')
    rc2, d1c = await g.dump(f"{T}/d1")
    ok("TO=AMIGA UNSET: native again, exactly as before", rc == 0 and fmt(d1c) == "Amiga"
       and strip_format(d1c) == strip_format(d1n), out + " " + diffs(strip_format(d1n), strip_format(d1c)))

    # TYPE with ALL: only the drawer icons
    await g.cmd(f"{EI} {T}/p2 TO=EMBLEM QUIET")
    rc, out = await g.cmd(f'{EI} {T} ALL TYPE=DRAWER TO=EMBLEM SET="IMAGE=GlassDrawer"', timeout=60)
    dumps = {}
    for k in ("d1", "d2", "p1", "p2"):
        rc2, dumps[k] = await g.dump(f"{T}/{k}")
    ok("ALL TYPE=DRAWER TO=EMBLEM SET: both drawers converted with the tool type",
       all(fmt(dumps[k]) == "Emblem" and "IMAGE=GlassDrawer" in tts(dumps[k]) for k in ("d1", "d2"))
       and "2 icons converted to Emblem, 2 with changed tool types" in out, out)
    ok("ALL TYPE=DRAWER: other icons untouched", fmt(dumps["p1"]) == "Amiga" and fmt(dumps["p2"]) == "Emblem"
       and "IMAGE=GlassDrawer" not in tts(dumps["p1"]) + tts(dumps["p2"]), out)

    # SET without TO in an ALL run: Emblem icons only
    rc, out = await g.cmd(f'{EI} {T} ALL SET="EMBLEM=Star"', timeout=60)
    for k in ("d1", "d2", "p1", "p2"):
        rc2, dumps[k] = await g.dump(f"{T}/{k}")
    ok("ALL SET without TO: the 3 Emblem icons changed, the native one not",
       all("EMBLEM=Star" in tts(dumps[k]) for k in ("d1", "d2", "p2")) and "EMBLEM=Star" not in tts(dumps["p1"])
       and fmt(dumps["p1"]) == "Amiga" and "3 with changed tool types" in out, out)

    # all back, tool types removed
    rc, out = await g.cmd(f'{EI} {T} ALL TO=AMIGA UNSET="IMAGE|EMBLEM"', timeout=60)
    rc2, d2 = await g.dump(f"{T}/d2")
    rc3, d2n = await g.dump(f"{G}/drawer")
    ok("ALL TO=AMIGA UNSET: all native, as made", rc == 0 and fmt(d2) == "Amiga"
       and strip_format(d2) == strip_format(d2n), out + " " + diffs(strip_format(d2n), strip_format(d2)))

    # bad arguments
    rc, out = await g.cmd(f'{EI} {T}/d1 SET="NOEQUALS"')
    ok("SET without '=': error, rc 20", rc == 20 and "KEY=value" in out, out)
    rc, out = await g.cmd(f'{EI} {T}/d1 TYPE=FOLDER SET="A=B"')
    ok("unknown TYPE: error, rc 20", rc == 20 and "TYPE must be" in out, out)
    rc, out = await g.cmd(f"{EI} {T}/p1 TYPE=DRAWER TO=EMBLEM")
    rc2, p1 = await g.dump(f"{T}/p1")
    ok("single icon of another TYPE: skipped, unchanged", rc == 0 and "skipped" in out and fmt(p1) == "Amiga", out)
    await g.cmd(f"Delete {T} ALL QUIET FORCE", timeout=20)



def val(lines, key):
    for l in lines:
        if l.startswith(key + "="):
            return l[len(key) + 1:]
    return None


def add_tts(lines, new):
    """expected dump lines with tool types appended after the existing ones"""
    out = list(lines)
    tts = [l for l in out if l.startswith("tt=")]
    i = out.index(tts[-1]) + 1 if tts else [j for j, l in enumerate(out) if l.startswith("deftool=")][0] + 1
    return out[:i] + [f"tt={t}" for t in new] + out[i:]


def diffs(a, b):
    return "; ".join(f"{x} -> {y}" for x, y in zip(a, b) if x != y) or f"{len(a)} vs {len(b)} lines"


async def step2(g):
    subprocess.run([os.path.expanduser("~/build/emblem-venv/bin/python"),
                    os.path.join(ROOT, "tests", "os4", "make_test_pngs.py")], check=True)
    exp = json.load(open(os.path.join(TESTPNG, "expected.json")))
    crc = lambda k: exp[k]["crc"].upper()
    await g.cmd(f"MakeDir {IMGDIR}", timeout=10)
    await g.cmd(f"Delete {IMGDIR}/EmblemTest#? QUIET", timeout=10)
    for f in sorted(os.listdir(TESTPNG)):
        if f.endswith(".png") and f != "EmblemTestNS2.png":
            await g.up(os.path.join(TESTPNG, f), f"{IMGDIR}/{f}")
    await g.up(os.path.join(TESTPNG, "EmblemTestNS2.png"), f"{G}/EmblemTestNS2.png")
    await g.cmd(f"Delete {G2} ALL QUIET FORCE", timeout=20)
    await g.cmd(f"MakeDir {G2}", timeout=10)

    async def native(kind, name):
        if kind.startswith("SYS:"):
            rc, out = await g.cmd(f"Copy {kind}.info {name}.info QUIET")
        else:
            rc, out = await g.cmd(f"{G}/icontest make {kind} {name}")
        return rc == 0

    async def emblem_with(kind, short, tts):
        """native icon -> Emblem -> tool types added one by one (each save after
        the first one is a save of a composed icon). Returns (name, raw0)."""
        n = f"{G2}/{short}"
        if not await native(kind, n):
            ok(f"{short}: made", False)
            return None, None
        rc, raw0 = await g.dump(n)
        await g.cmd(f"{G}/EmblemIcon {n} TO=EMBLEM QUIET")
        for t in tts:
            await g.cmd(f'{G}/icontest tt {n} "{t}"')
        return n, raw0

    # --- full checks with IMAGE + IMAGESELECTED on every kind of icon
    for kind in ["argb", "argb1", "clut", "planar", "drawer", "SYS:Devs", "SYS:Disk"]:
        short = "i_" + kind.split("/")[-1].split(":")[-1]
        tts = ["IMAGE=EmblemTestNS", "IMAGESELECTED=EmblemTestS"]
        n, raw0 = await emblem_with(kind, short, tts)
        if not n:
            continue
        rc, comp = await g.dump(n, raw=False)
        ok(f"{short}: default images shown", fmt(comp) == "Emblem" and val(comp, "imgfmt") == "2"
           and val(comp, "size") == "64x64" and (val(comp, "img1") or "").upper() == crc("EmblemTestNS")
           and (val(comp, "img2") or "").upper() == crc("EmblemTestS"), " ".join(comp[-8:]))
        rc, raw = await g.dump(n)
        expect = add_tts(strip_format(raw0), tts)
        ok(f"{short}: own images kept in the file", strip_format(raw) == expect, diffs(expect, strip_format(raw)))

        rc, out = await g.cmd(f"{G}/icontest layoutsave {n} 54242")   # native icons raise small stacks
        rc2, rawl = await g.dump(n)
        expect_l = [("stack=54242" if l.startswith("stack=") else l) for l in expect]
        ok(f"{short}: save after layout keeps own images", rc == 0 and strip_format(rawl) == expect_l,
           out.strip() + " | " + diffs(expect_l, strip_format(rawl)))

        rc, out = await g.cmd(f"{G}/icontest dup {n} {n}_dup")
        rc2, rawd = await g.dump(n + "_dup")
        rc3, compd = await g.dump(n + "_dup", raw=False)
        ok(f"{short}: duplicate keeps own images", rc == 0 and strip_format(rawd) == strip_format(rawl)
           and val(compd, "img1") == val(comp, "img1"), out.strip() + " | " + diffs(strip_format(rawl), strip_format(rawd)))

        rc, out = await g.cmd(f"{G}/EmblemIcon {n} TO=AMIGA QUIET")
        rc2, back = await g.dump(n)
        ok(f"{short}: back to native with own images", rc == 0 and fmt(back) == "Amiga"
           and strip_format(back) == expect_l, out.strip() + " | " + diffs(expect_l, strip_format(back)))

    # --- single cases on the ARGB test icon (48x40 with a selected image)
    counter = [0]

    async def case(short, tts, check, kind="argb"):
        counter[0] += 1
        n, raw0 = await emblem_with(kind, f"case{counter[0]}", tts)
        if not n:
            return None
        rc, comp = await g.dump(n, raw=False)
        rc2, raw = await g.dump(n)
        ok(short, check(comp, raw, raw0), " ".join(comp[-7:]) + " || raw: " + diffs(add_tts(strip_format(raw0), tts), strip_format(raw)))
        return n

    await case("IMAGE only: own selected image centred",
               ["IMAGE=EmblemTestNS"],
               lambda c, r, r0: val(c, "size") == "64x64" and val(c, "img1").upper() == crc("EmblemTestNS")
               and val(c, "real2") == "1" and val(c, "img2").upper() == crc("centred_argbsel_on_ns"))
    await case("IMAGE only, icon without selected image",
               ["IMAGE=EmblemTestNS"],
               lambda c, r, r0: val(c, "size") == "64x64" and val(c, "img1").upper() == crc("EmblemTestNS"), "argb1")
    await case("IMAGESELECTED larger than IMAGE: centred and clipped",
               ["IMAGE=EmblemTestNS", "IMAGESELECTED=EmblemTestBig"],
               lambda c, r, r0: val(c, "size") == "64x64" and val(c, "img2").upper() == crc("centred_big_on_ns"))
    await case("IMAGESELECTED only: normal image is the icon's own",
               ["IMAGESELECTED=EmblemTestS"],
               lambda c, r, r0: val(c, "size") == "48x40" and val(c, "img1") == val(r, "img1")
               and val(c, "img2").upper() != crc("EmblemTestS"))
    await case("missing image: icon unchanged",
               ["IMAGE=EmblemTestNope", "IMAGESELECTED=EmblemTestNope2"],
               lambda c, r, r0: strip_format(c) == strip_format(r))
    await case("image larger than 256: ignored",
               ["IMAGE=EmblemTestHuge"],
               lambda c, r, r0: strip_format(c) == strip_format(r))
    await case("bad tool type ignored",
               ["IMAGE=Bad:Name"],
               lambda c, r, r0: strip_format(c) == strip_format(r))
    await case("disabled tool type ignored",
               ["(IMAGE=EmblemTestNS)"],
               lambda c, r, r0: strip_format(c) == strip_format(r))
    await case("planar icon with IMAGE only",
               ["IMAGE=EmblemTestNS"],
               lambda c, r, r0: val(c, "imgfmt") == "2" and val(c, "img1").upper() == crc("EmblemTestNS")
               and val(r, "imgfmt") == "0", "planar")
    await case("palette icon with IMAGE only",
               ["IMAGE=EmblemTestNS"],
               lambda c, r, r0: val(c, "imgfmt") == "2" and val(c, "img1").upper() == crc("EmblemTestNS")
               and val(r, "imgfmt") == "1", "clut")
    for s in ("basn3p04", "basi6a16", "tbrn2c08", "basn0g01", "basi3p02"):
        k = f"EmblemTest_{s}"
        await case(f"PNG {s} decodes on the guest", [f"IMAGE={k}"],
                   lambda c, r, r0, k=k: val(c, "size") == f"{exp[k]['w']}x{exp[k]['h']}"
                   and val(c, "img1").upper() == crc(k))

    # --- a changed image file shows after the 2 second re-check
    n = await case("change test: before", ["IMAGE=EmblemTestNS"],
                   lambda c, r, r0: val(c, "img1").upper() == crc("EmblemTestNS"))
    if n:
        await g.cmd(f"Copy {G}/EmblemTestNS2.png {IMGDIR}/EmblemTestNS.png QUIET")
        await g.cmd("Wait 3")
        rc, c = await g.dump(n, raw=False)
        ok("changed image file shows on the next load", val(c, "img1").upper() == crc("EmblemTestNS2"), " ".join(c[-4:]))
        await g.up(os.path.join(TESTPNG, "EmblemTestNS.png"), f"{IMGDIR}/EmblemTestNS.png")
        await g.cmd("Wait 3")
        rc, c = await g.dump(n, raw=False)
        ok("changed back", val(c, "img1").upper() == crc("EmblemTestNS"), " ".join(c[-4:]))

    # --- a program sets new images on a composed icon: they become the icon's own
    n, raw0 = await emblem_with("argb", "setimg", ["IMAGE=EmblemTestNS"])
    if n:
        rc, out = await g.cmd(f"{G}/icontest setimg {n}")
        rc2, raw = await g.dump(n)
        rc3, comp = await g.dump(n, raw=False)
        ok("new images from a program become the icon's own", rc == 0 and val(raw, "size") == "20x20"
           and val(raw, "img1").upper() == crc("setimg1") and val(comp, "img1").upper() == crc("EmblemTestNS"),
           out.strip() + " | " + " ".join(raw[-7:]))

    # --- load times (information, not checked)
    names = {"native": f"{G2}/bench_n", "Emblem": f"{G2}/bench_e", "composed": f"{G2}/bench_c"}
    await native("argb", names["native"])
    await native("argb", names["Emblem"])
    await g.cmd(f"{G}/EmblemIcon {names['Emblem']} TO=EMBLEM QUIET")
    await native("argb", names["composed"])
    await g.cmd(f"{G}/EmblemIcon {names['composed']} TO=EMBLEM QUIET")
    await g.cmd(f'{G}/icontest tt {names["composed"]} "IMAGE=EmblemTestNS"')
    times = []
    for k, n in names.items():
        rc, out = await g.cmd(f"{G}/icontest bench {n} 200", timeout=120)
        times.append(f"{k} {val(out.splitlines(), 'per_icon_us')} us")
    print("load time per icon (200 loads each): " + ", ".join(times))

    await g.cmd(f"Delete {IMGDIR}/EmblemTest#? QUIET", timeout=10)


STEP3_CASES = {
    "own_size": ["EMBLEM=EmblemTestE1,0,0,4,4"],
    "gray_dark": ["EMBLEM=EmblemTestE1,12,12,30,20,GRAY", "EMBLEMSELECTED=EmblemTestE1,12,12,29,21,DARK"],
    "internal": ["IMAGE=EmblemTestNS,BRIGHT", "IMAGESELECTED=EmblemTestS", "EMBLEM=INTERNAL,32,0,2,2",
                 "EMBLEMSELECTED=INTERNAL,32,0,4,4,GRAY"],
    "aspect_clip": ["EMBLEM=EmblemTestBig,0,30,-10,-5"],
    "upscale_clip": ["EMBLEM=EmblemTestE2,40,25,50,50,NONE", "EMBLEMSELECTED=EmblemTestE2,40,0,-20,30"],
    "png16": ["EMBLEM=EmblemTest_basi6a16,20,20,1,1,BRIGHT"],
    "all": ["IMAGE=EmblemTestS,DARK", "EMBLEM=EmblemTestE1,20,0,40,40", "EMBLEMSELECTED=EmblemTestE1,0,20,38,38"],
}


async def setup_images(g, gdir):
    subprocess.run([os.path.expanduser("~/build/emblem-venv/bin/python"),
                    os.path.join(ROOT, "tests", "os4", "make_test_pngs.py")], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["make", "-C", ROOT, "build/host/render"], check=True, stdout=subprocess.DEVNULL)
    await g.cmd(f"MakeDir {IMGDIR}", timeout=10)
    await g.cmd(f"Delete {IMGDIR}/EmblemTest#? QUIET", timeout=10)
    for f in sorted(os.listdir(TESTPNG)):
        if f.endswith(".png"):
            await g.up(os.path.join(TESTPNG, f), f"{IMGDIR}/{f}")
    await g.cmd(f"Delete {gdir} ALL QUIET FORCE", timeout=20)
    await g.cmd(f"MakeDir {gdir}", timeout=10)


async def check_case(g, gdir, kind, short, tts, prefs=None):
    """Make the icon, convert it, add the tool types; the module's images must be
    exactly what the host renderer makes from the icon's own images (and prefs)."""
    local = os.path.join(WORK, "cases")
    os.makedirs(local, exist_ok=True)
    n = f"{gdir}/{short}"
    if kind.startswith("SYS:"):
        rc, out = await g.cmd(f"Copy {kind}.info {n}.info QUIET")
    else:
        rc, out = await g.cmd(f"{G}/icontest make {kind} {n}")
    if rc:
        ok(f"{short}: made", False, out)
        return
    await g.cmd(f"{G}/EmblemIcon {n} TO=EMBLEM QUIET")
    rc, raw0 = await g.dump(n)
    rc, out = await g.cmd(f"{G}/icontest raw pixels {n} {n}")
    args = [RENDER, "--dir", TESTPNG]
    if prefs:
        args += ["--prefs", prefs]
    for i in (1, 2):
        if f"pixels{i}=" in out:
            lf = os.path.join(local, f"{short}_{i}.argb")
            await g.down(f"{n}_{i}.argb", lf)
            args += [f"--own{i}", lf]
    for t in tts:
        await g.cmd(f'{G}/icontest tt {n} "{t}"')
    # all of the icon's tool types (the first of a key counts)
    rc, rawt = await g.dump(n)
    alltts = [l[3:] for l in rawt if l.startswith("tt=")]
    want = subprocess.run(args + alltts, capture_output=True, text=True).stdout.split()
    want = dict(w.split("=", 1) for w in want)
    rc, comp = await g.dump(n, raw=False)
    got = {"size": val(comp, "size"), "img1": (val(comp, "img1") or "").upper(),
           "img2": (val(comp, "img2") or "").upper() if val(comp, "real2") == "1" else None}
    if want.get("composed") != "1":
        rc, rawx = await g.dump(n)
        ok(f"{short}: nothing to compose", strip_format(comp) == strip_format(rawx), diffs(strip_format(rawx), strip_format(comp)))
        return
    same = got["size"] == want["size"] and got["img1"] == want["img1"] and got["img2"] == want.get("img2")
    ok(f"{short}: module = host render", same, f"guest {got} host {want}")
    rc, raw = await g.dump(n)
    expect = add_tts(strip_format(raw0), tts)
    ok(f"{short}: own images kept", strip_format(raw) == expect, diffs(expect, strip_format(raw)))


async def step3(g):
    await setup_images(g, G3)
    for kind in ["argb", "argb1", "clut", "planar", "SYS:Devs", "SYS:Disk"]:
        base = kind.split("/")[-1].split(":")[-1]
        for case, tts in STEP3_CASES.items():
            await check_case(g, G3, kind, f"{base}_{case}", tts)
    await g.cmd(f"Delete {IMGDIR}/EmblemTest#? QUIET", timeout=10)


STEP4_CASES = {
    "shadow_clip": ["EMBLEM=EmblemTestE1,0,0,30,22,SHADOW"],
    "glow": ["EMBLEM=EmblemTestE1,16,16,10,10,GLOW", "EMBLEMSELECTED=EmblemTestE2,0,0,2,2,SHADOW"],
    "image_effects": ["IMAGE=EmblemTestNS,SHADOW", "IMAGESELECTED=EmblemTestS,GLOW", "EMBLEM=EmblemTestE1,20,0,30,30,GLOW"],
    "outside_in": ["EMBLEM=EmblemTestE1,0,0,-22,-22,SHADOW"],
    "defaults": ["IMAGE=EmblemTestNS", "IMAGESELECTED=EmblemTestS", "EMBLEM=EmblemTestE1,20,20,20,10",
                 "EMBLEMSELECTED=EmblemTestE1,20,20,21,11"],
    "explicit_none": ["EMBLEM=EmblemTestE1,20,20,20,10,NONE"],
}
STEP4_PREFS = {
    "builtin": None,
    "shadow": "METHOD=SHADOW\nSHADOWOFFSET=3,-2\nSHADOWBLUR=1\nSHADOWOPACITY=70\n",
    "glow": "# a comment\r\nIMAGEMETHOD=GRAY\r\nEMBLEMMETHOD=GLOW\r\nGLOWCOLOR=#FF8000\r\nGLOWSIZE=3\r\nGLOWOPACITY=100\r\n",
}


async def put_prefs(g, text, where="ENV:sys/emblem.prefs"):
    await g.cmd("Delete ENV:sys/emblem.prefs ENVARC:sys/emblem.prefs QUIET", timeout=10)
    if text is not None:
        lf = os.path.join(TESTPNG, "test.prefs")
        open(lf, "w", newline="").write(text)
        await g.up(lf, where)
    await g.cmd("Wait 3", timeout=10)   # the module re-checks the file every 2 seconds


async def step4(g):
    await setup_images(g, G4)
    for pname, text in STEP4_PREFS.items():
        await put_prefs(g, text)
        prefs = None
        if text is not None:
            prefs = os.path.join(TESTPNG, f"{pname}.prefs")
            open(prefs, "w", newline="").write(text)
        for kind in ["argb", "clut", "SYS:Devs"]:
            base = kind.split("/")[-1].split(":")[-1]
            for case, tts in STEP4_CASES.items():
                await check_case(g, G4, kind, f"{pname}_{base}_{case}", tts, prefs)
    # ENVARC: only (no ENV: copy): still used
    text = STEP4_PREFS["shadow"]
    await put_prefs(g, text, "ENVARC:sys/emblem.prefs")
    prefs = os.path.join(TESTPNG, "shadow.prefs")
    await check_case(g, G4, "argb", "envarc_defaults", STEP4_CASES["defaults"], prefs)
    await put_prefs(g, None)
    await g.cmd(f"Delete {IMGDIR}/EmblemTest#? QUIET", timeout=10)

G5 = "RAM:et5"


async def crashes(g):
    """crash reports in the kernel debug buffer so far"""
    await g.cmd("DumpDebugBuffer >RAM:dbg5.txt", timeout=30)
    data = await g.down("RAM:dbg5.txt", os.path.join(WORK, "dbg5.txt"))
    return data.count(b"Crashed process")


async def rexx(g, name, lines):
    lf = os.path.join(WORK, name)
    open(lf, "w").write("/* */\nOPTIONS RESULTS\nADDRESS WORKBENCH\n" + "\n".join(lines) + "\n")
    await g.up(lf, f"RAM:{name}")
    return await g.cmd(f"C:rx RAM:{name}", timeout=120)


async def script(g, name, lines, timeout=600):
    lf = os.path.join(WORK, name)
    open(lf, "w").write("\n".join(lines) + "\n")
    await g.up(lf, f"RAM:{name}")
    return await g.cmd(f"Execute RAM:{name}", timeout=timeout)


def png_bytes(w, h, fn):
    import zlib as _z
    raw = b"".join(b"\0" + bytes(c for x in range(w) for c in fn(x, y)) for y in range(h))
    def ch(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", _z.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + ch(b"IDAT", _z.compress(raw, 6)) + ch(b"IEND", b""))


def fix_png_crcs(b):
    import zlib as _z
    b = bytearray(b)
    pos = 8
    while pos + 12 <= len(b):
        ln = struct.unpack(">I", b[pos:pos + 4])[0]
        if ln > len(b) - pos - 12:
            break
        b[pos + 8 + ln:pos + 12 + ln] = struct.pack(">I", _z.crc32(bytes(b[pos + 4:pos + 8 + ln])) & 0xFFFFFFFF)
        pos += 12 + ln
    return bytes(b)


async def render_check(g, n, own_prefix, name, extra_args=(), ttfile=None):
    """the module's composition of icon n = the host renderer's (own images from own_prefix)"""
    args = [RENDER, "--dir", TESTPNG]
    for i in (1, 2):
        lf = os.path.join(WORK, f"{os.path.basename(own_prefix)}_{i}.argb")
        if os.path.exists(lf):
            args += [f"--own{i}", lf]
    if ttfile:
        args += ["--ttfile", ttfile]
    else:
        rc, rawt = await g.dump(n)
        args += [l[3:] for l in rawt if l.startswith("tt=")]
    want = subprocess.run(list(args) + list(extra_args), capture_output=True, text=True).stdout.split()
    want = dict(w.split("=", 1) for w in want if "=" in w)
    rc, comp = await g.dump(n, raw=False)
    rc2, raw = await g.dump(n)
    if want.get("composed") != "1":
        return ok(name, rc == 0 and strip_format(comp) == strip_format(raw), " ".join(comp[-6:]))
    got = (val(comp, "size"), (val(comp, "img1") or "").upper(),
           (val(comp, "img2") or "").upper() if val(comp, "real2") == "1" else None)
    return ok(name, got == (want["size"], want["img1"], want.get("img2")), f"guest {got} host {want}")


def want(section):
    only = [a.split("=", 1)[1].split(",") for a in sys.argv if a.startswith("--only=")]
    return not only or section in only[0]


async def step5(g):
    await setup_images(g, G5)
    for sub in ("base", "bad", "odd", "png", "tt", "huge", "scr", "wb", "par", "lm", "speed_n", "speed_e", "speed_c"):
        await g.cmd(f"MakeDir {G5}/{sub}", timeout=10)
    await g.up(os.path.join(OS4, "memeater"), f"{G}/memeater")
    c0 = await crashes(g)
    print(f"crash reports in the debug buffer before: {c0}")
    bad = os.path.join(WORK, "step5")
    os.makedirs(bad, exist_ok=True)
    gp = os.path.expanduser("~/build/amiga-fleet")
    rnd = random.Random(7)

    # base icons (Emblem) and their own images
    bases = ["argb", "clut", "planar", "drawer", "SYS:Devs"]
    goods = []
    for kind in bases:
        short = kind.split(":")[-1]
        n = f"{G5}/base/{short}"
        if kind.startswith("SYS:"):
            await g.cmd(f"Copy {kind}.info {n}.info QUIET")
        else:
            await g.cmd(f"{G}/icontest make {kind} {n}")
        await g.cmd(f"{G}/EmblemIcon {n} TO=EMBLEM QUIET")
        await g.cmd(f"{G}/icontest raw pixels {n} {n}")
        for i in (1, 2):
            rc, out = await g.cmd(f"List {n}_{i}.argb QUICK NOHEAD")
            if rc == 0:
                await g.down(f"{n}_{i}.argb", os.path.join(WORK, f"{short}_{i}.argb"))
        lf = os.path.join(bad, f"{short}.info")
        await g.down(f"{n}.info", lf)
        goods.append(lf)

    # --- 1. broken Emblem files: loading may fail, nothing may crash
    if want("bad"):
        print("-- broken Emblem files")
        subprocess.run([sys.executable, os.path.join(ROOT, "tests", "os4", "make_bad_files.py"), bad] + goods, check=True)
        badfiles = sorted(os.listdir(os.path.join(bad, "bad")))
        for f in badfiles:
            await g.up(os.path.join(bad, "bad", f), f"{G5}/bad/{f}")
        rc, out = await g.cmd(f"{G}/icontest loadall {G5}/bad", timeout=300)
        print("  " + out.replace("\n", " "))
        ok(f"{len(badfiles)} broken files: loadall finishes", "loaded=" in out, out)
        rc, out = await g.cmd(f"{G}/icontest raw loadall {G5}/bad", timeout=300)
        ok("broken files, raw: loadall finishes", "loaded=" in out, out)
        oddfiles = sorted(os.listdir(os.path.join(bad, "odd")))
        lines = []
        for f in oddfiles:
            await g.up(os.path.join(bad, "odd", f), f"{G5}/odd/{f}")
            obj = f"{G5}/odd/{f[:-5]}"
            lines.append(f"MakeDir {obj}" if f.startswith(("drawer", "Devs")) else f"Echo >{obj} x")
        await script(g, "odd.script", lines)
        rc, out = await g.cmd(f"{G}/icontest loadall {G5}/odd", timeout=300)
        ok(f"{len(oddfiles)} odd but valid files all load", "failed=0" in out and f"loaded={len(oddfiles)}" in out, out)
        # Workbench opens the drawers of broken and odd icons, and a drawer icon without drawer data
        await rexx(g, "w5a.rexx", [f"WINDOW '{G5}/bad' OPEN", "SAY RC"])
        await g.cmd("Wait 8", timeout=20)
        rc, out = await rexx(g, "w5b.rexx", [f"WINDOW '{G5}/odd' OPEN", f"WINDOW '{G5}/odd/drawer_nodraw' OPEN",
                                             "SAY 'nodraw1' RC", f"WINDOW '{G5}/odd/Devs_nodraw' OPEN", "SAY 'nodraw2' RC"])
        ok("Workbench opens drawers whose icons have no drawer data", "nodraw1 0" in out and "nodraw2 0" in out, out)
        await g.cmd("Wait 4", timeout=20)
        gp = os.path.expanduser("~/build/amiga-fleet")
        subprocess.run([os.path.expanduser("~/build/amiga-fleet-venv/bin/python"), os.path.join(gp, "guest.py"),
                        "shot", "emblem_step5_bad"], capture_output=True, cwd=gp)
        await rexx(g, "w5c.rexx", [f"WINDOW '{G5}/odd/drawer_nodraw' CLOSE", f"WINDOW '{G5}/odd/Devs_nodraw' CLOSE",
                                   f"WINDOW '{G5}/odd' CLOSE", f"WINDOW '{G5}/bad' CLOSE"])
        c1 = await crashes(g)
        ok("no crash with broken files (loading and on Workbench)", c1 == c0, f"{c1 - c0} new crash reports")

    # --- 2. broken PNGs as default images and emblems
    if want("png"):
        print("-- broken PNG files")
        rnd = random.Random(7)
        e1 = open(os.path.join(TESTPNG, "EmblemTestE1.png"), "rb").read()
        pngs = {}
        for f in sorted(os.listdir(os.path.join(ROOT, "tests", "samples", "pngsuite"))):
            if f.startswith("x") and f.endswith(".png"):
                pngs[f"suite_{f[:-4]}"] = open(os.path.join(ROOT, "tests", "samples", "pngsuite", f), "rb").read()
        for cut in (8, 20, 33, 60, len(e1) // 2, len(e1) - 13, len(e1) - 1):
            pngs[f"trunc{cut}"] = e1[:cut]
        for k in range(12):
            b = bytearray(e1)
            for _ in range(1 + k % 4):
                b[8 + rnd.randrange(len(b) - 8)] = rnd.randrange(256)
            pngs[f"flip{k}"] = bytes(b)
            pngs[f"flipcrc{k}"] = fix_png_crcs(b)   # CRCs fixed: reaches zlib and the filters
        pngs["empty"] = b""
        lines = []
        for k, data in pngs.items():
            open(os.path.join(TESTPNG, f"EmblemTestBad_{k}.png"), "wb").write(data)
            await g.up(os.path.join(TESTPNG, f"EmblemTestBad_{k}.png"), f"{IMGDIR}/EmblemTestBad_{k}.png")
            tf = os.path.join(bad, f"png_{k}.tt")
            open(tf, "w").write(f"IMAGE=EmblemTestBad_{k}\nEMBLEM=EmblemTestBad_{k},0,0,2,2,SHADOW\n")
            await g.up(tf, f"{G5}/png/{k}.tt")
            lines += [f"Copy {G5}/base/argb.info {G5}/png/{k}.info QUIET", f"{G}/icontest ttfile {G5}/png/{k} {G5}/png/{k}.tt"]
        await script(g, "png.script", lines)
        rc, out = await g.cmd(f"{G}/icontest loadall {G5}/png", timeout=300)
        ok(f"{len(pngs)} icons with broken PNGs all load", f"loaded={len(pngs)}" in out and "failed=0" in out, out)
        for k in pngs:
            await render_check(g, f"{G5}/png/{k}", "argb", f"broken PNG {k}: same as the host",
                               ttfile=os.path.join(bad, f"png_{k}.tt"))
        ok("no crash with broken PNGs", await crashes(g) == c0)

    # --- 3. odd tool types
    if want("tt"):
        print("-- odd tool types")
        junk = []
        for k in range(500):
            junk.append("".join(chr(rnd.choice(list(range(32, 127)) + [1, 9, 13, 31, 127, 200, 255]))
                                for _ in range(rnd.randrange(0, 60))))
        ttcases = {
            "long": ["IMAGE=" + "A" * 5000, "EMBLEM=EmblemTestE1,0,0,4,4", "X" * 20000],
            "numbers": ["EMBLEM=EmblemTestE1," + "9" * 50 + ",1,1,1", "EMBLEMSELECTED=EmblemTestE1,-2147483648,0,0,0",
                        "IMAGE=EmblemTestNS"],
            "far_away": ["EMBLEM=EmblemTestE1,8,8,99999,-99999,SHADOW", "EMBLEMSELECTED=EmblemTestE1,8,8,-100000,100000,GLOW",
                         "IMAGESELECTED=EmblemTestS,GLOW"],
            "junk": junk + ["IMAGE=EmblemTestNS", "EMBLEM=EmblemTestE1,10,10,5,5,GRAY"],
            "binary": ["EMBLEM=Emb\x01lem,1,1,1,1", "IMAGE=EmblemTestNS\x7f", "IMAGESELECTED=\xffEmblemTestS",
                       "EMBLEMSELECTED=EmblemTestE1\t,  4 , 4 , 1 , 1 , dark"],
            "many": [f"EMBLEM=EmblemTestE1,4,4,{i},{i}" for i in range(300)],
            "empty_values": ["IMAGE=", "IMAGESELECTED=,", "EMBLEM=,,,,,", "EMBLEMSELECTED=EmblemTestE1,,,,,"],
        }
        for k, tts in ttcases.items():
            tf = os.path.join(bad, f"tt_{k}.tt")
            open(tf, "w", encoding="latin-1", newline="\n").write("\n".join(tts) + "\n")
            await g.up(tf, f"{G5}/tt/{k}.tt")
            n = f"{G5}/tt/{k}"
            await g.cmd(f"Copy {G5}/base/argb.info {n}.info QUIET")
            rc, out = await g.cmd(f"{G}/icontest ttfile {n} {G5}/tt/{k}.tt")
            ok(f"tool types {k}: saved", rc == 0, out)
            await render_check(g, n, "argb", f"tool types {k}: same as the host", ttfile=tf)
        ok("no crash with odd tool types", await crashes(g) == c0)

    # --- 4. large images
    if want("huge"):
        print("-- large images")
        big = {
            "Big1024": png_bytes(1024, 1024, lambda x, y: ((x >> 2) & 255, (y >> 2) & 255, 128, 255 if (x - 512) ** 2 + (y - 512) ** 2 < 500 ** 2 else 0)),
            "Big1025": png_bytes(1025, 4, lambda x, y: (x & 255, 0, 0, 255)),
            "Noise": png_bytes(800, 800, lambda x, y: (rnd.randrange(256), rnd.randrange(256), rnd.randrange(256), 255)),
            "Img256": png_bytes(256, 256, lambda x, y: (x, y, 100, 255)),
            "Img257": png_bytes(257, 16, lambda x, y: (x & 255, y, 100, 255)),
        }
        for k, data in big.items():
            open(os.path.join(TESTPNG, f"EmblemTest{k}.png"), "wb").write(data)
            await g.up(os.path.join(TESTPNG, f"EmblemTest{k}.png"), f"{IMGDIR}/EmblemTest{k}.png")
        print(f"  noise PNG: {len(big['Noise'])} bytes (over the 2 MB limit: {len(big['Noise']) > 2 * 1024 * 1024})")
        hcases = {
            "scaled_1024_to_512": ["EMBLEM=EmblemTestBig1024,512,512,-100,-100"],
            "own_size_1024": ["EMBLEM=EmblemTestBig1024"],
            "scaled_to_513": ["EMBLEM=EmblemTestBig1024,513,0"],
            "scaled_to_48": ["EMBLEM=EmblemTestBig1024,48,48,0,0,SHADOW"],
            "width_1025": ["EMBLEM=EmblemTestBig1025,10,10"],
            "file_too_big": ["EMBLEM=EmblemTestNoise,10,10"],
            "image_256": ["IMAGE=EmblemTestImg256", "EMBLEM=EmblemTestE1,0,0,230,230,SHADOW"],
            "image_257": ["IMAGE=EmblemTestImg257"],
        }
        for k, tts in hcases.items():
            n = f"{G5}/huge/{k}"
            await g.cmd(f"Copy {G5}/base/argb.info {n}.info QUIET")
            for t in tts:
                await g.cmd(f'{G}/icontest tt {n} "{t}"')
            await render_check(g, n, "argb", f"large images {k}: same as the host")
        rc, out = await g.cmd(f"{G}/icontest bench {G5}/huge/scaled_1024_to_512 5", timeout=300)
        print(f"  1024x1024 emblem scaled to 512x512: {val(out.splitlines(), 'per_icon_us')} us per icon load")
        ok("no crash with large images", await crashes(g) == c0)

    # --- 5. low colour screens; saving after a layout there keeps the icon's own images
    if want("screens"):
        print("-- 8 and 4 bit screens")
        scr = {"c_argb": ("argb", ["IMAGE=EmblemTestNS", "EMBLEM=EmblemTestE1,20,20,40,40,SHADOW"]),
               "c_clut": ("clut", ["EMBLEM=EmblemTestE1,16,16,20,10,GLOW", "EMBLEMSELECTED=EmblemTestE1,16,16,20,10,DARK"]),
               "c_planar": ("planar", ["EMBLEM=EmblemTestE1,12,12,18,6"]),
               "c_devs": ("Devs", ["EMBLEM=EmblemTestE1,24,24,38,38,GLOW"]),
               "plain": ("drawer", [])}
        raws = {}
        for k, (b, tts) in scr.items():
            n = f"{G5}/scr/{k}"
            await g.cmd(f"Copy {G5}/base/{b}.info {n}.info QUIET")
            for t in tts:
                await g.cmd(f'{G}/icontest tt {n} "{t}"')
            raws[k] = (await g.dump(n))[1]
        names = " ".join(f"{G5}/scr/{k}" for k in scr)
        for depth in (8, 4):
            await g.cmd(f"Delete RAM:scr.txt QUIET")
            await g.cmd(f"Run >NIL: {G}/icontest screen {depth} 5 SAVE {names} >RAM:scr.txt", timeout=30)
            await asyncio.sleep(3)
            subprocess.run([os.path.expanduser("~/build/amiga-fleet-venv/bin/python"), os.path.join(gp, "guest.py"),
                            "shot", f"emblem_step5_screen{depth}"], capture_output=True, cwd=gp)
            await asyncio.sleep(5)
            rc, out = await g.cmd("Type RAM:scr.txt")
            ok(f"{depth}-bit screen: icons drawn and saved", f"drawn={len(scr)}" in out and f"saved={len(scr)}" in out, out)
            for k in scr:
                rc, d = await g.dump(f"{G5}/scr/{k}")
                ok(f"{depth}-bit screen: {k} kept its own images", strip_format(d) == strip_format(raws[k]),
                   diffs(strip_format(raws[k]), strip_format(d)))
        ok("no crash on low colour screens", await crashes(g) == c0)

    # --- 6. Workbench menus: Snapshot, Copy, Leave Out
    if want("wb"):
        print("-- Workbench menus")
        n = f"{G5}/wb/x"
        await g.cmd(f"Copy {G5}/base/argb.info {n}.info QUIET")
        await g.cmd(f"Echo >{n} x")
        await g.cmd(f'{G}/icontest tt {n} "IMAGE=EmblemTestNS"')
        await g.cmd(f'{G}/icontest tt {n} "EMBLEM=EmblemTestE1,20,20,40,40,SHADOW"')
        rc, raw0 = await g.dump(n)
        rc, comp0 = await g.dump(n, raw=False)
        await rexx(g, "w6.rexx", [f"WINDOW '{G5}/wb' OPEN", f"ICON WINDOW '{G5}/wb' NAMES 'x' SELECT",
                                  "MENU INVOKE ICONS.SNAPSHOT", "MENU INVOKE ICONS.COPY", "MENU INVOKE ICONS.LEAVEOUT"])
        await g.cmd("Wait 2")
        rc, raw1 = await g.dump(n)
        rc, comp1 = await g.dump(n, raw=False)
        same = [l for l in strip_format(raw1) if not l.startswith("pos=")] == [l for l in strip_format(raw0) if not l.startswith("pos=")]
        ok("Snapshot + Leave Out: still Emblem, own images, only the position may change", fmt(raw1) == "Emblem" and same,
           diffs(strip_format(raw0), strip_format(raw1)))
        ok("Snapshot + Leave Out: same composed images", val(comp1, "img1") == val(comp0, "img1"))
        rc, rawc = await g.dump(f"{G5}/wb/Copy_of_x")
        ok("Workbench Copy: an Emblem icon with the same own images",
           fmt(rawc) == "Emblem" and [l for l in strip_format(rawc) if not l.startswith("pos=")] == [l for l in strip_format(raw1) if not l.startswith("pos=")],
           diffs(strip_format(raw1), strip_format(rawc)))
        await rexx(g, "w6b.rexx", [f"ICON WINDOW ROOT NAMES 'x' SELECT", "MENU INVOKE ICONS.PUTAWAY",
                                   f"WINDOW '{G5}/wb' CLOSE"])
        ok("no crash with Workbench menus", await crashes(g) == c0)

    # --- 7. three programs loading composed icons at the same time
    if want("par"):
        print("-- parallel loads")
        for i in (1, 2, 3):
            pn = f"{G5}/par/p{i}"
            await g.cmd(f"Copy {G5}/base/argb.info {pn}.info QUIET")
            await g.cmd(f'{G}/icontest tt {pn} "IMAGE=EmblemTestNS,GLOW"')
            await g.cmd(f'{G}/icontest tt {pn} "EMBLEM=EmblemTestE1,{10 * i},0,30,30,SHADOW"')
            await g.cmd(f"Delete RAM:par{i}.txt QUIET")
        for i in (1, 2, 3):
            await g.cmd(f"Run >NIL: {G}/icontest bench {G5}/par/p{i} 300 >RAM:par{i}.txt")
        outs = []
        for _ in range(60):
            await asyncio.sleep(2)
            outs = [(await g.cmd(f"Type RAM:par{i}.txt"))[1] for i in (1, 2, 3)]
            if all("per_icon_us" in o for o in outs):
                break
        ok("3 parallel loaders finish", all("per_icon_us" in o and "error" not in o for o in outs), " | ".join(outs))
        for i in (1, 2, 3):
            await render_check(g, f"{G5}/par/p{i}", "argb", f"parallel p{i}: still the right pixels")
        ok("no crash with parallel loads", await crashes(g) == c0)

    # --- 8. memory: no leaks; low memory fails softly and recovers
    if want("mem"):
        print("-- memory")
        lm = f"{G5}/lm/c1"
        open(os.path.join(TESTPNG, "EmblemTestLM.png"), "wb").write(
            png_bytes(600, 600, lambda x, y: (x & 255, y & 255, (x + y) & 255, 255)))
        await g.up(os.path.join(TESTPNG, "EmblemTestLM.png"), f"{IMGDIR}/EmblemTestLM.png")
        await g.cmd(f"Copy {G5}/base/argb.info {lm}.info QUIET")
        await g.cmd(f'{G}/icontest tt {lm} "EMBLEM=EmblemTestLM,40,40,4,4,SHADOW"')
        leak_icon = f"{G5}/lm/leak"
        await g.cmd(f"Copy {G5}/base/argb.info {leak_icon}.info QUIET")
        await g.cmd(f'{G}/icontest tt {leak_icon} "IMAGE=EmblemTestNS,GLOW"')
        await g.cmd(f'{G}/icontest tt {leak_icon} "EMBLEM=EmblemTestE1,10,0,30,30,SHADOW"')
        rc, out = await g.cmd(f"{G}/icontest leak {leak_icon} 400", timeout=300)
        lost = [int(val(out.splitlines(), k) or 99999999) for k in ("private_lost", "shared_lost")]
        print(f"  400 composed loads: private {lost[0]} bytes, shared {lost[1]} bytes not back")
        ok("no leak over 400 composed loads (< 16 KB)", abs(lost[0]) < 16384 and abs(lost[1]) < 16384, out)
        rc, out = await g.cmd(f"{G}/icontest raw leak {leak_icon} 400", timeout=300)
        print("  400 raw loads: " + out.replace("\n", " "))
        await g.cmd("Delete RAM:eat.txt RAM:lowmem.txt RAM:lowmem_dump.txt QUIET")
        rc, lmraw = await g.dump(lm)
        # a fresh copy of the emblem (new date): the module decodes it again, now with too little memory
        await g.up(os.path.join(TESTPNG, "EmblemTestLM.png"), f"{IMGDIR}/EmblemTestLM.png")
        lf = os.path.join(WORK, "lowmem.script")
        open(lf, "w").write("\n".join([
            f"{G}/icontest dump {lm} >RAM:lowmem_dump.txt",
            f"{G}/icontest loadall {G5}/lm 20 >RAM:lowmem.txt",
            f"{G}/icontest bench {lm} 50 >>RAM:lowmem.txt",
            f"{G}/icontest loadall {G5}/par 5 >>RAM:lowmem.txt",
            f"Break `Status COMMAND={G}/memeater` C",
            "Echo >>RAM:lowmem.txt done"]) + "\n")
        await g.up(lf, "RAM:lowmem.script")
        await script(g, "lowmem_start.script", [
            f"Run >NIL: {G}/memeater 1500 RAM:eat.txt",
            "Wait 6",
            "Run >NIL: Execute RAM:lowmem.script"], timeout=60)
        print("  (the low memory phase runs on its own in the guest)")
        done = ""
        for _ in range(90):
            await asyncio.sleep(4)
            try:
                rc, done = await g.cmd("Type RAM:lowmem.txt", timeout=10)
            except Exception:
                continue
            if "done" in done:
                break
        print("  " + done.replace("\n", " "))
        ok("low memory: the loads ran to the end", "done" in done, done)
        try:
            rc, eat = await g.cmd("Type RAM:eat.txt", timeout=10)
            if "given back" not in eat:
                rc, out = await g.cmd(f"Status COMMAND={G}/memeater", timeout=10)
                for num in re.findall(r"(\d+)", out):
                    await g.cmd(f"Break {num} C", timeout=10)
                await asyncio.sleep(3)
                rc, eat = await g.cmd("Type RAM:eat.txt", timeout=10)
        except Exception:
            print("  guest not answering: reset")
            monitor("system_reset")
            g = Guest()
            await wait_up(g)
            eat = "(guest was reset)"
        print("  " + eat.replace("\n", " "))
        await g.cmd("Wait 3")
        rc, during = await g.cmd("Type RAM:lowmem_dump.txt")
        during = [l for l in during.splitlines() if l.strip()]
        ok("low memory: the emblem could not be decoded, the icon showed its own image",
           val(during, "img1") == val(lmraw, "img1") and val(during, "size") == val(lmraw, "size"),
           " ".join(during[-6:]))
        await render_check(g, lm, "argb", "after low memory: the emblem decoded then shows (retried)")
        ok("no crash in low memory", await crashes(g) == c0)

    # --- 9. 200 icons in a drawer: native, Emblem, Emblem composed
    if want("speed"):
        print("-- 200 icons")
        c = f"{G5}/speed_c/master"
        await g.cmd(f"Copy SYS:Devs.info {c}.info QUIET")
        await g.cmd(f"{G}/EmblemIcon {c} TO=EMBLEM QUIET")
        await g.cmd(f"Copy {c}.info {G5}/speed_e/master.info QUIET")
        await g.cmd(f'{G}/icontest tt {c} "IMAGE=EmblemTestNS"')
        await g.cmd(f'{G}/icontest tt {c} "EMBLEM=EmblemTestE1,24,24,36,36,SHADOW"')
        lines = []
        for i in range(200):
            lines += [f"Copy SYS:Devs.info {G5}/speed_n/d{i:03d}.info QUIET",
                      f"Copy {G5}/speed_e/master.info {G5}/speed_e/d{i:03d}.info QUIET",
                      f"Copy {c}.info {G5}/speed_c/d{i:03d}.info QUIET"]
        lines += [f"Delete {G5}/speed_e/master.info {c}.info QUIET"]
        await script(g, "speed.script", lines, timeout=900)
        times = {}
        for k in ("n", "e", "c"):
            rc, out = await g.cmd(f"{G}/icontest loadall {G5}/speed_{k} 3", timeout=600)
            times[k] = int(val(out.splitlines(), "per_icon_us") or 0)
            ok(f"200 icons speed_{k}: all load", "loaded=600" in out and "failed=0" in out, out)
        print(f"  load + layout per icon (3 x 200): native {times['n']} us, Emblem {times['e']} us, composed {times['c']} us")
        ok("200 composed icons load in about native time (< 2x)", times["c"] < 2 * max(times["n"], 1),
           f"{times}")
        await rexx(g, "w9.rexx", [f"WINDOW '{G5}/speed_c' OPEN", f"CHANGEWINDOW '{G5}/speed_c' 40 40 1500 900"])
        await g.cmd("Wait 6")
        subprocess.run([os.path.expanduser("~/build/amiga-fleet-venv/bin/python"), os.path.join(gp, "guest.py"),
                        "shot", "emblem_step5_200"], capture_output=True, cwd=gp)
        await rexx(g, "w9b.rexx", [f"WINDOW '{G5}/speed_c' CLOSE"])
        ok("no crash with 200 icons on Workbench", await crashes(g) == c0)

    await g.cmd(f"Delete {IMGDIR}/EmblemTest#? QUIET", timeout=10)


GP = os.path.expanduser("~/build/amiga-fleet")
PKG = "RAM:pkg"
DOCS = "SYS:Documentation/Emblem"
T6 = "SYS:EmblemT6"
WATCH = ["LIBS:IconModules", "C:", "ENVARC:sys", "ENV:sys", "SYS:Documentation"]


def guest_py(*args):
    return subprocess.run([os.path.expanduser("~/build/amiga-fleet-venv/bin/python"), os.path.join(GP, "guest.py")]
                          + [str(a) for a in args], capture_output=True, text=True, cwd=GP)


async def reset(g):
    await g.cmd("Wait 2", timeout=10)
    monitor("system_reset")
    g = Guest()
    if not await wait_up(g):
        ok("guest came back after a reset", False)
        raise SystemExit(2)
    return g


async def snapshot(g):
    """names and sizes of everything in the places Install touches"""
    await g.cmd("Delete RAM:snap.txt QUIET", timeout=10)
    for d in WATCH:
        await g.cmd(f'List "{d}" ALL LFORMAT "%P%N|%L" >>RAM:snap.txt', timeout=120)
    data = await g.down("RAM:snap.txt", os.path.join(WORK, "snap.txt"))
    return set(data.decode("latin-1").splitlines())


async def run_installer(g, action, timeout=900):
    """the Install script in Novice mode with all defaults (ENV:EmblemInstallTest)"""
    await g.cmd(f"SetEnv EmblemInstallTest {action}", timeout=10)
    await g.cmd("Delete RAM:inst.log QUIET", timeout=10)
    await g.cmd(f"CD {PKG}/Emblem\nRun >NIL: SYS:Utilities/Installer Install APPNAME=Emblem "
                "MINUSER=NOVICE DEFUSER=NOVICE LOGFILE=RAM:inst.log NOPRETEND", timeout=20)
    await asyncio.sleep(6)
    guest_py("click", 838, 667)            # "Proceed With Install" (welcome, mode Novice)
    # the script then runs without questions and, in test mode, ends without
    # its last window; the log is written when the Installer ends
    t0 = time.time()
    while time.time() - t0 < timeout:
        await asyncio.sleep(4)
        rc, out = await g.cmd("Status COMMAND=SYS:Utilities/Installer", timeout=10)
        if rc != 0:
            break
    ok(f"{action}: the Installer has ended", rc != 0, out)
    await g.cmd("UnSetEnv EmblemInstallTest", timeout=10)
    rc, log = await g.cmd("Type RAM:inst.log", timeout=20)
    return log


async def unpack(g, lha):
    await g.cmd(f"Delete {PKG} ALL QUIET FORCE", timeout=20)
    await g.cmd(f"MakeDir {PKG}", timeout=10)
    await g.up(lha, "RAM:Emblem.lha")
    rc, out = await g.cmd(f"CD {PKG}\nLhA -q x RAM:Emblem.lha", timeout=60)
    ok("package unpacks with LhA", rc == 0, out)


async def step6(g):
    lha = os.path.join(ROOT, "dist", "Emblem.lha")
    art = os.path.join(ROOT, "art")
    pngs = sorted(f for f in os.listdir(art) if f.endswith(".png"))
    examples = ["Music", "Pictures", "Internet", "Games", "Downloads", "Private", "Favourites", "Old stuff",
                "Tools", "ReadMe"]
    print("-- step 6: the package")

    # a system without Emblem, the module not in memory
    await g.cmd(f"Delete LIBS:IconModules/emblem.iconmodule C:EmblemIcon ENVARC:sys/emblem ENV:sys/emblem "
                f"ENVARC:sys/emblem.prefs ENV:sys/emblem.prefs {DOCS} {DOCS}.info {T6} {T6}.info "
                "ALL QUIET FORCE", timeout=60)
    g = await reset(g)
    rc, out = await g.cmd("Version emblem.iconmodule", timeout=10)
    ok("before: no module in memory", rc != 0, out)
    before = await snapshot(g)

    await unpack(g, lha)

    # --- install
    log = await run_installer(g, "install")
    ok("install: script ran to the end", "Exiting script" in log, log[-400:])
    for f in ["LIBS:IconModules/emblem.iconmodule", "C:EmblemIcon", "ENVARC:sys/emblem.prefs", "ENV:sys/emblem.prefs",
              f"{DOCS}.info", f"{DOCS}/Emblem.guide", f"{DOCS}/LICENSE.txt", f"{DOCS}/Emblem-format.txt",
              f"{DOCS}/Examples.info", f"{DOCS}/Examples/ReadMe"] + \
             [f"ENVARC:sys/emblem/{p}" for p in pngs] + \
             [f"{DOCS}/Examples/{e}.info" for e in examples] + [f"{DOCS}/Examples/{e}" for e in examples[:-1]]:
        rc, out = await g.cmd(f'List "{f}" LFORMAT "%N"', timeout=10)
        ok(f"installed: {f}", rc == 0, out)
    for f in ["emblem.iconmodule", "EmblemIcon"]:
        dest = "LIBS:IconModules/emblem.iconmodule" if f.endswith("iconmodule") else "C:EmblemIcon"
        got = await g.down(dest, os.path.join(WORK, f"inst_{f}"))
        ok(f"installed {f} is the built one", got == open(os.path.join(OS4, f), "rb").read())
    rc, prefs = await g.cmd("Type ENVARC:sys/emblem.prefs", timeout=10)
    ok("install: settings EMBLEMMETHOD=SHADOW (the default choice)", "\nEMBLEMMETHOD=SHADOW" in prefs, prefs)
    rc, prefs2 = await g.cmd("Type ENV:sys/emblem.prefs", timeout=10)
    ok("install: ENV: has the same settings", prefs2 == prefs)

    # --- update: settings and the user's own images stay
    await g.cmd("Copy ENVARC:sys/emblem/DrawerNS.png ENVARC:sys/emblem/MyOwn.png QUIET", timeout=10)
    await g.cmd('Echo >>ENVARC:sys/emblem.prefs "GLOWSIZE=3"', timeout=10)
    rc, prefs = await g.cmd("Type ENVARC:sys/emblem.prefs", timeout=10)
    log = await run_installer(g, "install")
    ok("update: script ran to the end", "Exiting script" in log, log[-400:])
    ok("update: no settings question (the file exists)", "Ask Choice" not in log, log[-600:])
    rc, p2 = await g.cmd("Type ENVARC:sys/emblem.prefs", timeout=10)
    ok("update: the settings are kept", p2 == prefs, p2)
    rc, out = await g.cmd("List ENVARC:sys/emblem/MyOwn.png", timeout=10)
    ok("update: the user's own image is kept", rc == 0, out)
    ok("no crash while installing", await crashes(g) == 0)

    # --- after a restart: the examples are composed exactly like the host renders
    g = await reset(g)
    rc, out = await g.cmd("Version emblem.iconmodule", timeout=10)
    ok("after install + restart: module in memory", rc == 0 and "emblem.iconmodule" in out, out)
    await g.cmd(f"Delete {G} ALL QUIET FORCE", timeout=20)
    await g.cmd(f"MakeDir {G}", timeout=10)
    await g.up(os.path.join(OS4, "icontest"), f"{G}/icontest")
    prefsfile = os.path.join(WORK, "installed.prefs")
    await g.down("ENVARC:sys/emblem.prefs", prefsfile)
    for e in examples:
        n = f'"{DOCS}/Examples/{e}"'
        key = e.replace(" ", "")
        for i in (1, 2):
            lf = os.path.join(WORK, f"ex_{key}_{i}.argb")
            if os.path.exists(lf):
                os.remove(lf)
        rc, out = await g.cmd(f'{G}/icontest raw pixels {n} {G}/ex_{key}')
        for i in (1, 2):
            if f"pixels{i}=" in out:
                await g.down(f"{G}/ex_{key}_{i}.argb", os.path.join(WORK, f"ex_{key}_{i}.argb"))
        args = [RENDER, "--dir", art, "--prefs", prefsfile]
        for i in (1, 2):
            lf = os.path.join(WORK, f"ex_{key}_{i}.argb")
            if os.path.exists(lf):
                args += [f"--own{i}", lf]
        rc, rawt = await g.dump(n)
        want = subprocess.run(args + [l[3:] for l in rawt if l.startswith("tt=")], capture_output=True,
                              text=True).stdout.split()
        want = dict(w.split("=", 1) for w in want if "=" in w)
        rc, comp = await g.dump(n, raw=False)
        got = (val(comp, "size"), (val(comp, "img1") or "").upper(),
               (val(comp, "img2") or "").upper() if val(comp, "real2") == "1" else None)
        ok(f"example {e}: composed = host render", want.get("composed") == "1"
           and got == (want["size"], want["img1"], want.get("img2")), f"guest {got} host {want}")
    rc, out = await g.cmd(f"C:EmblemIcon {DOCS} ALL QUIET", timeout=60)
    ok("EmblemIcon ALL finds the 10 examples", "10 Emblem icons" in out, out)

    # Workbench: the Examples drawer, one icon selected
    await rexx(g, "w6a.rexx", [f"WINDOW '{DOCS}/Examples' OPEN", f"CHANGEWINDOW '{DOCS}/Examples' 60 60 560 300",
                               f"WINDOW '{DOCS}/Examples' OPEN"])
    await g.cmd("Wait 5", timeout=20)
    await rexx(g, "w6b.rexx", [f"ICON WINDOW '{DOCS}/Examples' NAMES 'Favourites' SELECT"])
    await g.cmd("Wait 2", timeout=20)
    guest_py("shot", "emblem_step6_examples")
    await rexx(g, "w6c.rexx", [f"WINDOW '{DOCS}/Examples' CLOSE"])

    # a user's Emblem icon outside the examples
    await g.cmd(f"MakeDir {T6}\nCopy SYS:Prefs.info {T6}/Mine.info QUIET\nC:EmblemIcon {T6}/Mine TO=EMBLEM QUIET",
                timeout=30)
    await g.cmd(f'{G}/icontest tt {T6}/Mine "EMBLEM=EmblemStar,24,24,38,38"', timeout=10)
    rc, mine = await g.dump(f"{T6}/Mine")
    ok("user icon is an Emblem icon", fmt(mine) == "Emblem", " ".join(mine[:3]))
    ok("no crash with the examples on Workbench", await crashes(g) == 0)

    # --- remove (from the package again: the reset emptied RAM:)
    await unpack(g, lha)
    t0 = time.time()
    log = await run_installer(g, "remove")
    print(f"  remove took {time.time() - t0:.0f} s (converting the Emblem icons in SYS:)")
    ok("remove: script ran to the end", "Exiting script" in log, log[-400:])
    rc, after = await g.dump(f"{T6}/Mine")
    ok("remove: the user icon is a native icon again", fmt(after) == "Amiga", " ".join(after[:3]))
    ok("remove: ... with its own picture and tool types", strip_format(after) == strip_format(mine),
       diffs(strip_format(mine), strip_format(after)))
    for f in ["LIBS:IconModules/emblem.iconmodule", "C:EmblemIcon", "ENVARC:sys/emblem.prefs", "ENV:sys/emblem.prefs",
              DOCS, f"{DOCS}.info", "ENV:EmblemRemove.out"] + [f"ENVARC:sys/emblem/{p}" for p in pngs]:
        rc, out = await g.cmd(f'List "{f}" LFORMAT "%N"', timeout=10)
        ok(f"removed: {f}", rc != 0, out)
    rc, out = await g.cmd('List ENVARC:sys/emblem LFORMAT "%N"', timeout=10)
    ok("remove: only the user's own image stays", out.split() == ["MyOwn.png"], out)
    ok("no crash while removing", await crashes(g) == 0)

    await g.cmd(f"Delete ENVARC:sys/emblem ENV:sys/emblem {T6} {T6}.info ALL QUIET FORCE", timeout=20)
    g = await reset(g)
    rc, out = await g.cmd("Version emblem.iconmodule", timeout=10)
    ok("after remove + restart: no module in memory", rc != 0, out)
    after = await snapshot(g)
    ok("after remove the system is as before the install", after == before,
       f"new: {sorted(after - before)[:8]} gone: {sorted(before - after)[:8]}")
    return g


def orig_stack(lines):
    for l in lines:
        if l.startswith("stack="):
            return l[6:]
    return "0"


def orig_pos(lines):
    for l in lines:
        if l.startswith("pos="):
            x, y = l[4:].split(",")
            return f"{x} {y}"
    return "0 0"


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
