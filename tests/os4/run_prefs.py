#!/home/claude/build/amiga-fleet-venv/bin/python
"""run_prefs.py: with the icon set installed, every program in SYS:Prefs still starts from Workbench.

Many OS 4 Prefs editors read all of their icon's tool types as ReadArgs() arguments; while Emblem kept
its settings as tool types (1.0), 18 of them showed an error requester instead of their window. Since
1.1 the settings are in the icon file. This opens every program in SYS:Prefs from Workbench (ARexx
ICON ... OPEN) and checks that none shows the small requester (a window named after the program, less
than 200 pixels high) and that the icon is an Emblem icon without the Emblem keys in its tool types.

Needs the plugin running and dist/emblem_icons_glenz.lha (as run_iconset.py). Installs the set first if it
isn't installed; at the end puts the original icons back (Restore QUIET, images deleted) and resets
the guest. Screenshot: build/os4-qemu/prefs_survey.png. Public domain.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_os4 as T  # noqa: E402
import run_iconset as I  # noqa: E402

ok = T.ok
# not about Emblem: no screen modes in the QEMU guest; opens no window without a printer
EXPECTED = {"Picasso96Mode": "no screen modes in QEMU", "PrinterGfx": "no window without a printer"}


def key(w):
    return (w["title"], w["left"], w["top"], w["width"], w["height"])


async def main():
    g = T.Guest()
    rc, out = await g.cmd(f'List "{I.B}/Installed" QUICK NOHEAD', timeout=10)
    installed_here = rc != 0
    if installed_here:
        await I.unpack_set(g)
        log = await I.set_installer(g, "install")
        ok("set installed", "Exiting script" in log and "Aborting" not in log, log[-400:])
        g = await T.reset(g)
    progs = [l.strip() for l in (await g.cmd('List SYS:Prefs #?.info FILES LFORMAT "%M"', timeout=20))[1].splitlines()
             if l.strip()]
    progs = list(dict.fromkeys(progs))   # one each (a running editor opens no second window)
    progs = [p for p in progs if (await g.cmd(f'List "SYS:Prefs/{p}" FILES QUICK NOHEAD', timeout=10))[0] == 0]
    print(f"-- {len(progs)} programs in SYS:Prefs")
    await T.rexx(g, "pw.rexx", ["WINDOW 'SYS:Prefs' OPEN"])
    await asyncio.sleep(3)
    failed = []
    for p in progs:
        rc, out = await g.cmd(f'C:EmblemIcon "SYS:Prefs/{p}.info"', timeout=20)
        tts, ess = I.shown_lists(out)
        emblem = "Emblem format" in out
        bad_tt = [t for t in tts if t.split("=")[0].upper() in I.SETTING_KEYS]
        before = {key(w) for w in await g.m.request("wb.windows")}
        await T.rexx(g, "po.rexx", [f"ICON WINDOW 'SYS:Prefs' NAMES '{p}' OPEN"])
        await asyncio.sleep(4)
        new = [w for w in await g.m.request("wb.windows") if key(w) not in before]
        req = [w for w in new if w["title"].lower() == p.lower() and w["height"] < 200]
        what = ", ".join(f"'{w['title']}' {w['width']}x{w['height']}" for w in new) or "no window"
        if p in EXPECTED or not emblem:
            print(f"  {p}: {what} (not checked: {EXPECTED.get(p, 'not an Emblem icon, not in the set')})")
            continue
        good = emblem and ess and not bad_tt and not req and new
        ok(f"{p}: starts from Workbench ({what})", good,
           f"emblem={emblem} settings={ess} emblem keys in tool types={bad_tt}")
        if not good:
            failed.append(p)
    T.guest_py("shot", "prefs_survey")
    checked = sum(1 for n, _ in T.results if n.endswith(")") and "starts from Workbench" in n)
    print(f"-- {checked - len(failed)} of {checked} started, failed: {' '.join(failed) or 'none'}")

    # back to the original icons, a clean guest
    g = await T.reset(g)
    rc, out = await g.cmd(f'Execute "{I.B}/Restore" QUIET', timeout=300)
    ok("Restore QUIET puts the original icons back", rc == 0, out[-300:])
    await g.cmd(f'Delete "{I.B}" "{I.B}.info" "{I.B}.old" "{I.B}.old.info" ENVARC:sys/emblem/{I.SET} '
                f"ENV:sys/emblem/{I.SET} {I.SETPKG} ALL QUIET FORCE", timeout=60)
    await T.reset(g)
    passed = sum(1 for _, c in T.results if c)
    print(f"\n{passed}/{len(T.results)} passed")
    return 0 if passed == len(T.results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
