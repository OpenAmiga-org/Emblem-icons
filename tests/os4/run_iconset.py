#!/home/claude/build/amiga-fleet-venv/bin/python
"""run_iconset.py: the icon set's installer in the OS4 guest, the whole cycle, driven from the host
through MCPd (helpers from run_os4.py).

Needs dist/emblem_icons_glenz.lha (tools/iconset_build.py package) and a plugin archive with EmblemIcon
1.2 or newer:  OUT=$PWD/build/test/emblem_icons.lha RELEASES=/nonexistent tools/make_lha.sh
(--plugin=PATH for another one). If the module isn't running, the plugin is installed first.

  1. before: MD5, size, date, protection and comment of every file the set changes
  2. install: the backup (one exact copy per existing file, MD5 lists), Restore, the marker,
     the images, the settings; every mapped icon is an Emblem icon with its settings; after a
     restart a few icons are composed by the module exactly like the host renders them;
     Workbench screenshots of SYS: and SYS:Prefs
  3. install again (update): the backup is the same, nothing added twice
  4. Restore (QUIET): every file is back exactly (MD5 + date + protection + comment), also the
     ENV: copies; the marker is gone
  5. install again after the restore: the old backup becomes .old, a fresh one is made
  6. Remove (Installer): the files are back again, the images are gone, nothing else is left
Public domain.
"""
import asyncio
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_os4 as T  # noqa: E402

ROOT = T.ROOT
NAME, SET, B = "Glenz", "glenz", "SYS:GlenzBackup"     # as in tools/iconset_build.py
SETLHA = os.path.join(ROOT, "dist", "emblem_icons_glenz.lha")
PLUGIN = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--plugin=")),
              os.path.join(ROOT, "build", "test", "emblem_icons.lha"))
SETPKG = "RAM:setpkg"
MAPPING = os.path.join(ROOT, "build", "iconset", SET, "mapping.txt")
ok = T.ok


def changed_files():
    m = [l.split("|", 1)[0] for l in open(MAPPING).read().splitlines() if l.strip()]
    return m + ["ENVARC:sys/emblem.prefs"]


SETTING_KEYS = ("IMAGE", "IMAGESELECTED", "EMBLEM", "EMBLEMSELECTED")


def shown_lists(out):
    """(tool types, settings) from EmblemIcon's listing of one icon"""
    lists, cur = {"Tool types:": [], "Settings:": []}, None
    for l in out.splitlines():
        if l.strip() in lists:
            cur = lists[l.strip()]
        elif cur is not None and l.startswith("    "):
            cur.append(l.strip())
        else:
            cur = None
    return lists["Tool types:"], lists["Settings:"]


def env_copy(p):
    """the copy in use in ENV: of an ENVARC: file"""
    return "ENV:" + p.split(":", 1)[1] if p.startswith("ENVARC:") else None


async def state(g, paths, tag):
    """{path: (md5, size, date, time, protection, comment)} of the files that exist"""
    lines = ["FailAt 21", f"Delete RAM:{tag}.md5 RAM:{tag}.lst QUIET"]
    for p in paths:
        lines += [f'If EXISTS "{p}"', f'  MD5Sum "{p}" >>RAM:{tag}.md5',
                  f'  List "{p}" LFORMAT "{p}|%L|%D|%T|%A|%C" >>RAM:{tag}.lst', "EndIf"]
    await T.script(g, f"{tag}.script", lines, timeout=300)
    md5 = (await g.down(f"RAM:{tag}.md5", os.path.join(T.WORK, f"{tag}.md5"))).decode("latin-1")
    lst = (await g.down(f"RAM:{tag}.lst", os.path.join(T.WORK, f"{tag}.lst"))).decode("latin-1")
    sums = {}
    for l in md5.splitlines():
        if "  " in l:
            h, n = l.split("  ", 1)
            sums[n.lower()] = h
    out = {}
    for l in lst.splitlines():
        p, size, date, tim, prot, comment = l.split("|", 5)
        out[p] = (sums.get(p.lower()), size, date, tim, prot, comment)
    return out


def diff(a, b, keys=None):
    """paths whose entries differ (keys: which fields, default all)"""
    bad = []
    for p in sorted(set(a) | set(b)):
        x, y = a.get(p), b.get(p)
        if keys is not None and x and y:
            x, y = tuple(x[k] for k in keys), tuple(y[k] for k in keys)
        if x != y:
            bad.append(f"{p}: {x} -> {y}")
    return bad


async def set_installer(g, action, timeout=1200):
    """the set's Install in Novice mode with all defaults (ENV:IconSetInstallTest)"""
    await g.cmd(f"SetEnv IconSetInstallTest {action}", timeout=10)
    await g.cmd("Delete RAM:set.log QUIET", timeout=10)
    await g.cmd(f"CD {SETPKG}/{NAME}\nRun >NIL: SYS:Utilities/Installer Install APPNAME={NAME} "
                "MINUSER=NOVICE DEFUSER=NOVICE LOGFILE=RAM:set.log NOPRETEND", timeout=20)
    await asyncio.sleep(6)
    T.guest_py("click", 838, 667)            # "Proceed With Install" (welcome, mode Novice)
    t0 = time.time()
    while time.time() - t0 < timeout:
        await asyncio.sleep(4)
        rc, out = await g.cmd("Status COMMAND=SYS:Utilities/Installer", timeout=10)
        if rc != 0:
            break
    took = time.time() - t0
    ok(f"set {action}: the Installer has ended ({took:.0f} s)", rc != 0, out)
    await g.cmd("UnSetEnv IconSetInstallTest", timeout=10)
    rc, log = await g.cmd("Type RAM:set.log", timeout=20)
    return log


async def unpack_set(g):
    await g.cmd(f"Delete {SETPKG} ALL QUIET FORCE", timeout=20)
    await g.cmd(f"MakeDir {SETPKG}", timeout=10)
    await g.up(SETLHA, f"RAM:{NAME}.lha")
    rc, out = await g.cmd(f"CD {SETPKG}\nLhA -q x RAM:{NAME}.lha", timeout=60)
    ok("set package unpacks with LhA", rc == 0, out)


async def emblem_count(g, where):
    """the total EmblemIcon prints last ("242 Emblem icons"; it lists them before)"""
    rc, out = await g.cmd(f"C:EmblemIcon {where} QUIET", timeout=300)
    for l in reversed(out.strip().splitlines()):
        w = l.split()
        if len(w) >= 3 and w[0].isdigit() and w[1] == "Emblem" and w[2].startswith("icon"):
            return int(w[0]), out
    return None, out


async def lines(g, cmd):
    rc, out = await g.cmd(cmd, timeout=60)
    return [l for l in out.splitlines() if l.strip()]


async def compose_check(g, icons):
    """the module's composed images = build/host/render with the same images and settings"""
    await g.cmd(f"Delete {T.G} ALL QUIET FORCE\nMakeDir {T.G}", timeout=20)
    await g.up(os.path.join(T.OS4, "icontest"), f"{T.G}/icontest")
    imgroot = os.path.join(T.WORK, "setimgs")
    os.makedirs(imgroot, exist_ok=True)
    link = os.path.join(imgroot, SET)
    if not os.path.islink(link):
        os.symlink(os.path.join(ROOT, "build", "iconset", SET, "images"), link)
    prefs = os.path.join(T.WORK, "set.prefs")
    await g.down("ENVARC:sys/emblem.prefs", prefs)
    for n in icons:
        key = n.replace(":", "_").replace("/", "_").replace(" ", "")
        for i in (1, 2):
            lf = os.path.join(T.WORK, f"set_{key}_{i}.argb")
            if os.path.exists(lf):
                os.remove(lf)
        rc, out = await g.cmd(f'{T.G}/icontest raw pixels "{n}" {T.G}/set_{key}')
        args = [T.RENDER, "--dir", imgroot, "--prefs", prefs]
        for i in (1, 2):
            if f"pixels{i}=" in out:
                lf = os.path.join(T.WORK, f"set_{key}_{i}.argb")
                await g.down(f"{T.G}/set_{key}_{i}.argb", lf)
                args += [f"--own{i}", lf]
        rc, rawt = await g.dump(f'"{n}"')
        want = subprocess.run(args + [l[3:] for l in rawt if l.startswith("es=")], capture_output=True,
                              text=True).stdout.split()
        want = dict(w.split("=", 1) for w in want if "=" in w)
        rc, comp = await g.dump(f'"{n}"', raw=False)
        got = (T.val(comp, "size"), (T.val(comp, "img1") or "").upper(),
               (T.val(comp, "img2") or "").upper() if T.val(comp, "real2") == "1" else None)
        ok(f"composed = host render: {n}", want.get("composed") == "1"
           and got == (want["size"], want["img1"], want.get("img2")), f"guest {got} host {want}")


async def screenshots(g, tag):
    for w, x, y, ww, hh in (("SYS:", 40, 60, 900, 300), ("SYS:Prefs", 40, 380, 1100, 560)):
        await T.rexx(g, "wset.rexx", [f"WINDOW '{w}' OPEN", f"CHANGEWINDOW '{w}' {x} {y} {ww} {hh}"])
    await g.cmd("Wait 6", timeout=20)
    T.guest_py("shot", f"iconset_{tag}")
    await T.rexx(g, "wset2.rexx", ["WINDOW 'SYS:Prefs' CLOSE"])


async def main():
    os.makedirs(T.WORK, exist_ok=True)
    g = T.Guest()
    files = changed_files()
    print(f"-- the icon set: {len(files)} files it may change")

    # a clean start: no backup, no images; the plugin running
    await g.cmd(f'Delete "{B}" "{B}.info" "{B}.old" "{B}.old.info" ENVARC:sys/emblem/{SET} ENV:sys/emblem/{SET} '
                "ALL QUIET FORCE", timeout=60)
    # the built module and EmblemIcon (src/*_rev.h) must be the ones in the guest
    vers = [re.search(r'#define VERS\s+"([^"]+)"', open(os.path.join(ROOT, "src", f)).read()).group(1)
            for f in ("emblem.iconmodule_rev.h", "EmblemIcon_rev.h")]
    rc, out = await g.cmd("Version emblem.iconmodule\nVersion C:EmblemIcon", timeout=10)
    if rc != 0 or not all(v + " " in out for v in vers):
        print("  installing the plugin first:", PLUGIN, "| guest has:", " ".join(out.split()))
        await T.unpack(g, PLUGIN)
        log = await T.run_installer(g, "install")
        ok("plugin installed", "Exiting script" in log, log[-300:])
        g = await T.reset(g)
    rc, out = await g.cmd("Version emblem.iconmodule\nVersion C:EmblemIcon", timeout=10)
    ok("plugin running, EmblemIcon 1.2+", rc == 0 and "EmblemIcon 1." in out
       and "EmblemIcon 1.0 " not in out and "EmblemIcon 1.1 " not in out, out)
    n0, _ = await emblem_count(g, "SYS: ALL")
    before = await state(g, files, "before")
    envfiles = [env_copy(p) for p in files if env_copy(p)]
    env_before = await state(g, envfiles, "envbefore")
    exist = [p for p in files if p in before]
    print(f"  {len(exist)} of them exist; {n0} Emblem icons in SYS: before")
    ok("EmblemIcon counts the Emblem icons in SYS:", n0 is not None)

    # --- 2. install
    await unpack_set(g)
    log = await set_installer(g, "install")
    ok("install: script ran to the end", "Exiting script" in log, log[-600:])
    ok("install: nothing aborted", "Aborting" not in log and "abort" not in log.lower(), log[-600:])
    for f in [f"{B}.info", f"{B}/Restore", f"{B}/Restore.info", f"{B}/Installed", f"{B}/SYS.md5",
              f"{B}/ENVARC.md5"]:
        rc, out = await g.cmd(f'List "{f}" LFORMAT "%N %A"', timeout=10)
        ok(f"install: {f}", rc == 0, out)
    rc, out = await g.cmd(f'List "{B}/Restore" LFORMAT "%A"', timeout=10)
    ok("install: Restore has the script bit", "s" in out.strip()[:4], out)
    saved = await lines(g, f'List "{B}/files" ALL FILES LFORMAT "%P%N"')
    ok(f"install: one saved copy per existing file ({len(saved)})", len(saved) == len(exist),
       f"{len(saved)} vs {len(exist)}")
    sums = await lines(g, f'Type "{B}/SYS.md5" "{B}/ENVARC.md5"')
    ok(f"install: one MD5 line per saved copy ({len(sums)})", len(sums) == len(exist))
    # the saved copies are the originals, byte for byte (checked on the host against "before")
    copies = await state(g, [f"{B}/files/{p.replace(':', '/', 1)}" for p in exist], "copies")
    bad = [p for p in exist if copies.get(f"{B}/files/{p.replace(':', '/', 1)}", (None,))[0] != before[p][0]]
    ok("install: every saved copy has the original's MD5", not bad, "; ".join(bad[:5]))
    bad = [p for p in exist if copies.get(f"{B}/files/{p.replace(':', '/', 1)}", (0, 0, 0, 0, 0, 0))[2:]
           != before[p][2:]]
    ok("install: ... and its date, protection and comment", not bad, "; ".join(bad[:5]))
    imgs = await lines(g, f'List ENVARC:sys/emblem/{SET} FILES LFORMAT "%N"')
    nimg = len(os.listdir(os.path.join(ROOT, "build", "iconset", SET, "images")))
    ok(f"install: the {nimg} images", len(imgs) == nimg, f"{len(imgs)}")
    rc, prefs = await g.cmd("Type ENVARC:sys/emblem.prefs", timeout=10)
    ok("install: the set's shadow in emblem.prefs", "SHADOWOFFSET=2,2" in prefs and "SHADOWOPACITY=55" in prefs, prefs)
    rc, prefs_env = await g.cmd("Type ENV:sys/emblem.prefs", timeout=10)
    ok("install: ENV: has the same settings", prefs_env == prefs)
    n1, out = await emblem_count(g, "SYS: ALL")
    mapped = len([p for p in exist if p != "ENVARC:sys/emblem.prefs"])
    ok(f"install: every mapped icon is an Emblem icon ({n1} in SYS: incl. ENVARC:Sys)", n1 - n0 == mapped,
       f"{n1} - {n0} vs {mapped}; {out[-200:]}")
    rc, out = await g.cmd('C:EmblemIcon "SYS:Prefs/Printer.info"', timeout=20)
    tts, ess = shown_lists(out)
    ok("install: settings of SYS:Prefs/Printer", f"IMAGE={SET}/p_printer" in ess
       and any("EmPrefs,0,0,36,35,SHADOW" in s for s in ess), out)
    ok("install: ... none of them in its tool types", not [t for t in tts if t.split("=")[0].upper() in SETTING_KEYS], out)
    after_inst = await state(g, files, "afterinst")
    env_after = await state(g, envfiles, "envafter")
    sysdefs = [p for p in exist if p.startswith("ENVARC:Sys/")]
    bad = [p for p in sysdefs if env_after.get(env_copy(p), (None,))[0] != after_inst[p][0]]
    ok("install: ENV:Sys has the changed default icons", not bad, "; ".join(bad[:5]))
    ok("no crash while installing", await T.crashes(g) == 0)

    # after a restart: the module composes them like the host
    g = await T.reset(g)
    await compose_check(g, ["SYS:Prefs", "SYS:Utilities/Clock", "SYS:Prefs/Printer", "ENVARC:Sys/def_drawer",
                            "SYS:Disk", "SYS:Utilities/MultiView", "ENVARC:Sys/def_lha"])
    await screenshots(g, "installed")

    # --- 3. install again: an update keeps the backup
    sums1 = await lines(g, f'Type "{B}/SYS.md5" "{B}/ENVARC.md5"')
    await unpack_set(g)
    log = await set_installer(g, "install")
    ok("update: script ran to the end", "Exiting script" in log, log[-600:])
    sums2 = await lines(g, f'Type "{B}/SYS.md5" "{B}/ENVARC.md5"')
    ok("update: the MD5 lists are unchanged", sums2 == sums1, f"{len(sums1)} -> {len(sums2)}")
    copies2 = await state(g, [f"{B}/files/{p.replace(':', '/', 1)}" for p in exist], "copies2")
    ok("update: the saved copies are unchanged", not diff(copies, copies2), "; ".join(diff(copies, copies2)[:5]))
    rc, prefs2 = await g.cmd("Type ENVARC:sys/emblem.prefs", timeout=10)
    ok("update: the shadow settings are not added twice", prefs2 == prefs, prefs2)
    n2, _ = await emblem_count(g, "SYS: ALL")
    ok("update: still every mapped icon an Emblem icon", n2 == n1, f"{n2} vs {n1}")

    # --- 4. Restore
    rc, out = await g.cmd(f'Execute "{B}/Restore" QUIET', timeout=300)
    ok("Restore: return code 0", rc == 0, out)
    ok("Restore: says every icon is back", "Every saved icon is back" in out, out[-400:])
    restored = await state(g, files, "restored")
    d = diff(before, restored)
    ok("Restore: every file exactly as before (MD5, size, date, protection, comment)", not d, "; ".join(d[:5]))
    env_restored = await state(g, envfiles, "envrestored")
    d = diff(env_before, env_restored, keys=(0, 1))
    ok("Restore: the ENV: copies have the original contents", not d, "; ".join(d[:5]))
    rc, out = await g.cmd(f'List "{B}/Installed"', timeout=10)
    ok("Restore: the marker is gone", rc != 0, out)
    n3, _ = await emblem_count(g, "SYS: ALL")
    ok("Restore: as many Emblem icons as before", n3 == n0, f"{n3} vs {n0}")
    ok("no crash while restoring", await T.crashes(g) == 0)

    # --- 5. install after the restore: the old backup becomes .old
    log = await set_installer(g, "install")
    ok("install after Restore: script ran to the end", "Exiting script" in log, log[-600:])
    for f in [f"{B}.old/Restore", f"{B}.old.info", f"{B}/Installed"]:
        rc, out = await g.cmd(f'List "{f}" LFORMAT "%N"', timeout=10)
        ok(f"install after Restore: {f}", rc == 0, out)
    copies3 = await state(g, [f"{B}/files/{p.replace(':', '/', 1)}" for p in exist], "copies3")
    bad = [p for p in exist if copies3.get(f"{B}/files/{p.replace(':', '/', 1)}", (None,))[0] != before[p][0]]
    ok("install after Restore: the fresh backup has the originals", not bad, "; ".join(bad[:5]))

    # --- 6. Remove with the Installer
    await unpack_set(g)
    log = await set_installer(g, "remove")
    ok("remove: script ran to the end", "Exiting script" in log, log[-600:])
    removed = await state(g, files, "removed")
    d = diff(before, removed)
    ok("remove: every file exactly as before", not d, "; ".join(d[:5]))
    for f in [f"ENVARC:sys/emblem/{SET}", f"ENV:sys/emblem/{SET}", f"{B}/Installed"]:
        rc, out = await g.cmd(f'List "{f}" LFORMAT "%N"', timeout=10)
        ok(f"removed: {f}", rc != 0, out)
    n4, _ = await emblem_count(g, "SYS: ALL")
    ok("remove: as many Emblem icons as before", n4 == n0, f"{n4} vs {n0}")
    ok("no crash while removing", await T.crashes(g) == 0)

    # leave the guest clean: no backups (the plugin stays installed)
    await g.cmd(f'Delete "{B}" "{B}.info" "{B}.old" "{B}.old.info" {SETPKG} RAM:{NAME}.lha ALL QUIET FORCE',
                timeout=60)
    passed = sum(1 for _, c in T.results if c)
    print(f"\n{passed}/{len(T.results)} passed")
    return 0 if passed == len(T.results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
