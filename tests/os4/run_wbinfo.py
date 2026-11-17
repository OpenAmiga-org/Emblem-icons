#!/home/claude/build/amiga-fleet-venv/bin/python
"""run_wbinfo.py: Workbench's Information window (RAWBInfo, Icons > Information...) and Emblem icons.

The real window is opened (ARexx INFO), changed with its gadgets, keyboard shortcuts and pop-up menu,
and saved; then the icon's own data (icontest raw dump: images, planar fallback, tool types, settings)
and the composed picture are compared with what must come out:

  save unchanged (nothing written), a tool type and the stack, Frameless, Default, Default + Restore
  (exactly as before), Delete alternate image and Paste (the other image stays the file's own, not the
  composed picture), Load (a PNG), Drop planar data (no fallback in the file), a drawer's Show/View,
  type change, Load default icon (a normal default icon), Save as default "tool" (put back after).

Needs the plugin running in the guest (--deploy copies build/os4/emblem.iconmodule and restarts) and
build/os4/{icontest,EmblemIcon}. Coordinates are the guest screen's (1920x1080). Public domain.
"""
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_os4 as T  # noqa: E402

ok = T.ok
G = "RAM:et"
W, W0 = "RAM:wbi", "RAM:wbi0"          # test icons, pristine copies
SET = "IMAGE=DrawerNS|IMAGESELECTED=DrawerS|EMBLEM=EmblemMusic,28,28,34,32|EMBLEMSELECTED=EmblemMusic,28,28,34,32"
ES = [f"es={s}" for s in SET.split("|")]

# The pop-up menu opens with the last used top-level item under the pointer (P); rows are 20 pixels
# apart. Submenu items: (x, dy from their parent's row).
P = (300, 200)
TOP = ["Project", "Type", "Icon image", "Tool types"]
SUB = {
    "Icon image": (400, {"Default": -126, "Paste": -88, "Restore": -69, "Extras": -25, "Drop planar data": 126}),
    "Project": (414, {"Save as default": -12, "Load default icon": 6}),
    "Extras": (597, {"Delete alternate image": 38}),
}
state = {"cur": "Icon image"}


def gp(*a):
    T.guest_py(*[str(x) for x in a])


async def windows(g):
    return await g.m.request("wb.windows")


async def info_window(g, name):
    for _ in range(10):
        for w in await windows(g):
            if w["title"] == f"RAM Disk:wbi/{name}":
                return w
        await asyncio.sleep(0.5)
    return None


async def open_info(g, name):
    lf = os.path.join(T.WORK, "inf.rexx")
    open(lf, "w").write(f"/* */\nADDRESS WORKBENCH\nINFO NAME '{W}/{name}'\n")
    await g.up(lf, "RAM:inf.rexx")
    await g.cmd("Run >NIL: C:rx RAM:inf.rexx", timeout=10)   # INFO returns when the window closes
    w = await info_window(g, name)
    await asyncio.sleep(1)
    return w


async def save(g, w):
    gp("click", w["left"] + 46, w["top"] + w["height"] - 40)
    for _ in range(10):
        await asyncio.sleep(0.5)
        if not any(x["title"] == w["title"] for x in await windows(g)):
            return True
    return False


async def answer_yes(g):
    """the "Are you sure?" requester: its left button"""
    for _ in range(8):
        await asyncio.sleep(0.5)
        for w in await windows(g):
            if w["height"] < 200 and w["width"] > 300 and w["top"] > 300:
                gp("click", w["left"] + 37, w["top"] + 123)
                await asyncio.sleep(1)
                return True
    return False


async def key(chord):
    gp("key", chord)
    await asyncio.sleep(0.6)


async def menu(path):
    """pick path (top item, submenu item[, item]) from the pop-up menu"""
    gp("rmb", "down", *P)                 # the first press after a start is sometimes lost
    await asyncio.sleep(0.4)
    gp("rmb", "up")
    await asyncio.sleep(0.4)
    gp("rmb", "down", *P)
    await asyncio.sleep(0.9)
    y = P[1] + 9 + (TOP.index(path[0]) - TOP.index(state["cur"])) * 20
    moves = [(290, y)]
    x, items = SUB[path[0]]
    moves += [(360, y), (x, y + items[path[1]])]
    if len(path) > 2:
        y2 = y + items[path[1]]
        x2, items2 = SUB[path[1]]
        moves += [(x2 - 70, y2), (x2, y2 + items2[path[2]])]
    for mx, my in moves:
        gp("move", mx, my)
        await asyncio.sleep(0.35)
    await asyncio.sleep(0.4)
    gp("shot", "wbinfo_menu_" + path[-1].replace(" ", "_"), 0, 0, 900, 600)
    gp("rmb", "up")
    state["cur"] = path[0]
    await asyncio.sleep(1)


async def dump(g, name, raw=True):
    rc, out = await g.cmd(f'{G}/icontest {"raw " if raw else ""}dump "{W}/{name}"', timeout=20)
    return [l for l in out.splitlines() if l.strip()]


def val(lines, k):
    return T.val(lines, k)


def changed(a, b):
    """{key: (before, after)} of the dump lines that differ (tt=/es= compared as lists)"""
    d = {}
    for k in sorted({l.split("=", 1)[0] for l in a + b}):
        x = [l for l in a if l.split("=", 1)[0] == k]
        y = [l for l in b if l.split("=", 1)[0] == k]
        if x != y:
            d[k] = (x, y)
    return d


async def fresh(g, name):
    await g.cmd(f"Copy {W0}/{name}.info {W}/ CLONE QUIET", timeout=10)
    return await dump(g, name), await dump(g, name, raw=False)


async def mtime(g, name):
    rc, out = await g.cmd(f'List "{W}/{name}.info" LFORMAT "%D %T %L"', timeout=10)
    return out.strip()


async def setup(g):
    await g.cmd(f"MakeDir {G}", timeout=10)
    await g.up(os.path.join(T.OS4, "icontest"), f"{G}/icontest")
    await g.up(os.path.join(T.OS4, "EmblemIcon"), f"{G}/EmblemIcon")
    await T.script(g, "wbi.script", [
        f"Delete {W} {W0} ALL QUIET FORCE", f"MakeDir {W} {W0}",
        f"Copy SYS:Utilities/Clock#? {W}/ CLONE QUIET",
        f"Copy SYS:Prefs/Presets#? {W}/ ALL CLONE QUIET",
        f"Copy SYS:S/Startup-Sequence {W}/Notes", f"Copy ENVARC:Sys/def_project.info {W}/Notes.info",
        f"Copy SYS:Utilities/Clock {W}/Native", f"Copy SYS:Utilities/Clock.info {W}/Native.info",
        f'{G}/EmblemIcon {W}/(Clock|Notes|Presets).info QUIET SET="{SET}"',
        f"Copy {W}/#?.info {W0}/ CLONE QUIET"], timeout=60)


async def main():
    os.makedirs(T.WORK, exist_ok=True)
    g = T.Guest()
    if "--deploy" in sys.argv:
        await g.up(os.path.join(T.OS4, "emblem.iconmodule"), "LIBS:IconModules/emblem.iconmodule")
        g = await T.reset(g)
    rc, out = await g.cmd("Version emblem.iconmodule", timeout=10)
    ok("module running", rc == 0, out)
    await setup(g)
    c0 = await T.crashes(g)
    for n in ("Clock", "Notes", "Presets"):
        d = await dump(g, n)
        ok(f"test icon {n}: Emblem icon with the settings", T.fmt(d) == "Emblem" and [l for l in d if l.startswith("es=")] == ES,
           " ".join(d[:3]))

    # 1. Save without a change: nothing is written
    b, bc = await fresh(g, "Clock")
    t0 = await mtime(g, "Clock")
    w = await open_info(g, "Clock")
    ok("the Information window opens for an Emblem icon", w is not None)
    if not w:
        return 1
    gp("shot", "wbinfo_emblem", 0, 0, 640, 400)
    await save(g, w)
    ok("save unchanged: the file is not written", await mtime(g, "Clock") == t0 and await dump(g, "Clock") == b)

    # 2. a tool type and the stack (Icon tab)
    b, bc = await fresh(g, "Clock")
    w = await open_info(g, "Clock")
    gp("click", 163, 78)                  # Icon tab
    await asyncio.sleep(0.8)
    gp("click", 300, 257)                 # the line FORMAT=0
    await key("end")
    await key("return")
    gp("type", "WBITEST=1")
    await asyncio.sleep(0.5)
    gp("click", 275, 114)                 # stack +
    await asyncio.sleep(0.5)
    await save(g, w)
    a = await dump(g, "Clock")
    c = changed(b, a)
    ok("tool type + stack: only those changed", set(c) == {"tt", "stack"} and "tt=WBITEST=1" in a, str(c)[:400])
    ac = await dump(g, "Clock", False)
    ok("tool type + stack: the composed picture is the same",
       [l for l in ac if l.startswith("img")] == [l for l in bc if l.startswith("img")])

    # 3. Frameless
    b, bc = await fresh(g, "Clock")
    w = await open_info(g, "Clock")
    await key("ramiga+f")
    await save(g, w)
    c = changed(b, await dump(g, "Clock"))
    ok("Frameless: only the flag", c == {"frameless": (["frameless=0"], ["frameless=1"])}, str(c))

    # 4. Default: the icon's own images become the default tool's; the settings stay
    b, bc = await fresh(g, "Clock")
    w = await open_info(g, "Clock")
    await key("ramiga+e")
    await save(g, w)
    a, ac = await dump(g, "Clock"), await dump(g, "Clock", False)
    c = changed(b, a)
    ok("Default: own images replaced, settings and tool types kept", "img1" in c and "es" not in c and "tt" not in c
       and T.fmt(a) == "Emblem", str(c)[:400])
    ok("Default: the composed picture is the same (IMAGE= covers the own one)",
       [l for l in ac if l.startswith("img")] == [l for l in bc if l.startswith("img")])

    # 5. Default, then Restore: exactly as before (the aspect too)
    b, bc = await fresh(g, "Clock")
    w = await open_info(g, "Clock")
    await key("ramiga+e")
    await key("ramiga+r")
    await save(g, w)
    c = changed(b, await dump(g, "Clock"))
    ok("Default + Restore: the icon is exactly as before", not c, str(c))

    # 6. Delete alternate image: the normal image stays the file's own (not the composed picture)
    b, bc = await fresh(g, "Clock")
    w = await open_info(g, "Clock")
    await menu(["Icon image", "Extras", "Delete alternate image"])
    await save(g, w)
    a = await dump(g, "Clock")
    c = changed(b, a)
    ok("Delete alternate image: own normal image kept, selected one gone",
       val(a, "img1") == val(b, "img1") and val(a, "real2") == "0" and "es" not in c, str(c)[:400])

    # 7. Drop planar data: no planar fallback in the file (the module makes one at load)
    b, bc = await fresh(g, "Clock")
    s0 = (await mtime(g, "Clock")).split()[-1]
    w = await open_info(g, "Clock")
    await menu(["Icon image", "Drop planar data"])
    await save(g, w)
    c = changed(b, await dump(g, "Clock"))
    s1 = (await mtime(g, "Clock")).split()[-1]
    ok("Drop planar data: only the fallback changed, the file is smaller",
       set(c) <= {"fallback1", "fallback2"} and c and int(s1) < int(s0), f"{c} {s0} -> {s1}")

    # 8. Copy a picture from a normal icon, Paste it into an Emblem icon: its selected image stays its own
    b, bc = await fresh(g, "Notes")
    w = await open_info(g, "Native")
    await key("ramiga+c")
    gp("click", w["left"] + w["width"] - 26, w["top"] + w["height"] - 40)   # Cancel
    await asyncio.sleep(1)
    w = await open_info(g, "Notes")
    await key("ramiga+v")
    await save(g, w)
    a = await dump(g, "Notes")
    c = changed(b, a)
    ok("Paste: new normal image, the selected one stays the file's own",
       "img1" in c and val(a, "img2") == val(b, "img2") and "es" not in c, str(c)[:400])

    # 9. Load a PNG as the picture
    b, bc = await fresh(g, "Clock")
    w = await open_info(g, "Clock")
    await key("ramiga+o")
    await asyncio.sleep(1.5)
    gp("type", "ENVARC:sys/emblem/EmblemStar.png")
    await asyncio.sleep(0.5)
    await key("return")
    await asyncio.sleep(1)
    await key("return")
    await asyncio.sleep(1)
    await save(g, w)
    a = await dump(g, "Clock")
    c = changed(b, a)
    ok("Load (PNG): new normal image, the selected one stays the file's own",
       "img1" in c and val(a, "img2") == val(b, "img2") and "es" not in c, str(c)[:400])

    # 10. a drawer's Show and View
    b, bc = await fresh(g, "Presets")
    w = await open_info(g, "Presets")
    gp("click", 207, 78)                  # Icon tab
    await asyncio.sleep(0.8)
    gp("click", 186, 114)                 # Show: next choice
    await asyncio.sleep(0.5)
    gp("click", 391, 114)                 # View: next choice
    await asyncio.sleep(0.5)
    await save(g, w)
    c = changed(b, await dump(g, "Presets"))
    ok("drawer Show/View: only the drawer data changed", set(c) == {"drawer"}, str(c))

    # 11. type change (Project -> Tool, confirmed): images and settings stay
    b, bc = await fresh(g, "Notes")
    w = await open_info(g, "Notes")
    await key("ramiga+3")
    await answer_yes(g)
    await save(g, w)
    a = await dump(g, "Notes")
    c = changed(b, a)
    ok("type change: type and stack, nothing else", val(a, "type") == "3" and set(c) <= {"type", "stack"}, str(c))

    # 12. Load default icon (confirmed): the icon becomes the normal default icon, as the window says
    b, bc = await fresh(g, "Clock")
    w = await open_info(g, "Clock")
    await key("ramiga+l")
    await answer_yes(g)
    await save(g, w)
    a = await dump(g, "Clock")
    ok("Load default icon: a normal icon without settings", T.fmt(a) == "Amiga" and not [l for l in a if l.startswith("es=")],
       " ".join(a[:4]))

    # 13. Save as default "tool": def_tool becomes this Emblem icon (then put back)
    await g.cmd("Delete RAM:defbak ALL QUIET\nMakeDir RAM:defbak\nCopy ENVARC:Sys/def_tool.info RAM:defbak/arc.info CLONE QUIET\n"
                "Copy ENV:Sys/def_tool.info RAM:defbak/env.info CLONE QUIET", timeout=20)
    b, bc = await fresh(g, "Clock")
    w = await open_info(g, "Clock")
    await menu(["Project", "Save as default"])
    await asyncio.sleep(2)
    rc, d = await g.cmd(f"{G}/icontest raw dump ENV:Sys/def_tool", timeout=20)
    d = d.splitlines()
    ok('Save as default "tool": def_tool is the Emblem icon with its settings',
       T.fmt(d) == "Emblem" and [l for l in d if l.startswith("es=")] == ES, " ".join(d[:3]))
    await g.cmd("Copy RAM:defbak/arc.info ENVARC:Sys/def_tool.info CLONE QUIET\n"
                "Copy RAM:defbak/env.info ENV:Sys/def_tool.info CLONE QUIET", timeout=20)
    for x in await windows(g):
        if x["title"].startswith("RAM Disk:wbi"):                            # Cancel what is left
            gp("click", x["left"] + x["width"] - 26, x["top"] + x["height"] - 40)
            await asyncio.sleep(1)

    ok("no crash", await T.crashes(g) == c0)
    passed = sum(1 for _, c in T.results if c)
    print(f"\n{passed}/{len(T.results)} passed")
    return 0 if passed == len(T.results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
