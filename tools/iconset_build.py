#!/home/claude/build/emblem-venv/bin/python
"""iconset_build.py check|export [OUTDIR]

The glass icon set as a package: which stock icon gets which image, selected image and emblem
(MAPPING), the final images (SOURCES, EMBLEMS), a check against a full listing of the guest
(build/work/inventory_full.txt: List SYS: ENVARC:Sys ALL LFORMAT "%P%N|%L"), and the export:

  OUTDIR/images/<name>.png   the images for ENVARC:sys/emblem/<SET>/ (bases 64x64, emblems 28x28)
  OUTDIR/mapping.txt         one line per icon: ICONPATH|TOOLTYPE|TOOLTYPE...  (for the installer)
  docs/iconset_mapping.md    the same for people, and every stock icon NOT mapped (the gaps)

Everything comes from docs/iconset_plan.md (the user's decisions, 2026-11-15/16). The set's name is a
working name, in one place (SET, or the environment ICONSET). Public domain.
"""
import collections
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glass_sheet import LIGHTBLUE, bloom  # noqa: E402
import glass_symbols as gs  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = os.path.join(ROOT, "build", "glass")
SET = os.environ.get("ICONSET", "glass")          # working name (the user names the set later)
AT = "0,0,36,35"                                  # emblems: their own size (28x28), lower right
LISTING = os.path.join(ROOT, "build", "work", "inventory_full.txt")

# --- the images: base name -> (normal render, selected render, bloom threshold) -------------------
DEV = 0.86            # devices: large light glass, only the brightest parts glow (as approved)
SOURCES = {
    "drawer": ("drawer.png", "drawer_open.png", 0.5),
    "device": ("device.png", "device_lit.png", DEV),
    "floppy": ("floppy.png", "floppy_lit.png", DEV),
    "disc": ("disc.png", "disc_lit.png", DEV),
    "ram": ("ram.png", "ram_lit.png", DEV),
    "usb": ("usb.png", "usb_lit.png", DEV),
    "network": ("network.png", "network_lit.png", DEV),
    "trashcan": ("trashcan.png", "trashcan_full.png", DEV),
    "file": ("g3/sheet/file.png", "g3/sheet/file_open.png", 0.5),
    "archive": ("g3/sheet/archive.png", "g3/sheet/archive_open.png", 0.5),
    "tool": ("tool/tool.png", "tool/tool_open.png", 0.5),
}
PROGRAM_DIRS = {
    "g4": "shell multiview notepad clock calculator find format help iconedit unarc",
    "g5": "ahi amigainput asl compatibility console deficons dos fontprefs gui",
    "g6": "input internet locale notifications palette picasso96 pointer popupmenu",
    "g7": "printer printergfx printerps screenblanker screenmode screens serial sound time",
    "g8": "timezone uboot updates url usbprefs wbpattern wbstartup workbench",
    "g9": "filecompare graphicdump initprinter installer keyshow logviewer memacs partitionwizard",
    "g10": "playcd prefsobjects printfiles rawdisk showconfig usbinspector biosupdater fixfonts",
    "g11": "formatcdrw grimreaper mounter rexxmast ringhio typemanager mediatoolbox",
}
for _d, _names in PROGRAM_DIRS.items():
    for _n in _names.split():
        SOURCES["p_" + _n] = (f"{_d}/{_n}.png", f"{_d}/{_n}_open.png", 0.5)


def emblem_source(name):
    """an emblem's render and bloom threshold: the glass tiles (Em*, Sd*) and the program emblems (Ep_*)"""
    if name.startswith("Ep_"):
        return os.path.join(G, "emb", name + ".png"), 0.86
    return os.path.join(G, name + ".png"), 0.5


# --- the mapping: icon -> (base, emblem) ---------------------------------------------------------
E = "ENVARC:Sys/"
MAPPING = []          # (icon path without .info, base, emblem or None)


def m(path, base, emblem=None):
    MAPPING.append((path, base, emblem))


# group 1: drawers
m(E + "def_drawer", "drawer")
for d, em in (("Prefs", "EmPrefs"), ("Utilities", "EmUtilities"), ("System", "EmSystem"), ("Storage", "EmStorage"),
              ("WBStartup", "EmStartup"), ("Devs", "EmDevs"), ("Internet", "EmInternet"), ("Emulation", "EmEmulation"),
              ("Documentation", "EmDocs"), ("MUI", "EmMUI")):
    m("SYS:" + d, "drawer", em)
# group 2: disks and devices (def_hdf, def_mdf, def_cdda are files: group 3)
for n in ("def_disk",):
    m(E + n, "device")
for n in ("def_sys", "disk_system"):
    m(E + n, "device", "EmSystem")
m("SYS:Disk", "device", "EmSystem")
for n in ("def_work", "disk_work"):
    m(E + n, "device", "EmHome")
for n in ("def_DF0", "def_DF1", "def_DF2", "def_DF3", "def_FD0", "def_FD1", "def_PC0", "def_crossdos"):
    m(E + n, "floppy")
for n in ["def_CD%d" % k for k in range(7)] + ["def_cd", "def_dvd"]:
    m(E + n, "disc")
for n in ("def_ram", "def_RAD"):
    m(E + n, "ram")
for n in ("def_zipdisk", "def_jazdisk", "def_modisk", "def_pccard"):
    m(E + n, "usb")
m(E + "def_baddisk", "device", "EmWarning")
m(E + "def_trashcan", "trashcan")
m("SYS:Trashcan", "trashcan")
# group 3: files by type (sys is the System volume, not a file type)
FILES = {
    None: "ascii ftxt rtf tex file project",
    "EmDocument": "pdf ps eps",
    "EmInternet": "html http ftp",
    "EmDocs": "guide amigaguide",
    "EmPicture": "picture ilbm jpeg gif png bmp tiff brush animbrush",
    "EmMusic": "sound 8svx aiff aifc wav mp2 mp3 mpa ahx sfx cdda",
    "EmVideo": "video anim avi mpeg wmv asf cdxl",
    "EmCode": "script arexx py pyc php js make fd install",
    "EmFont": "font outlinefont",
    "EmSystem": "library datatype loadmodule kickstart bin system",
    "EmDevs": "device handler filesystem mount monitor",
    "EmMUI": "mui",
    "EmPrefs": "prefs",
    "EmStorage": "hdf mdf",
}
for em, names in FILES.items():
    for n in names.split():
        m(E + "def_" + n, "file", em)
m(E + "def_archive", "archive")
for em, names in (("EmLHA", "lha lharc"), ("EmLZX", "lzx"), ("EmZIP", "zip pkzip"), ("EmGZ", "gzip"), ("EmBZ2", "bz2"),
                  ("EmTAR", "tar"), ("Em7Z", "7zip"), ("EmARJ", "arj"), ("EmRAR", "rar"), ("EmZOO", "zoo")):
    for n in names.split():
        m(E + "def_" + n, "archive", em)
m(E + "def_tool", "tool")
# group 4: programs (Prefs editors with the gear; Utilities and System without an emblem)
PREFS = {"AHI": "ahi", "AmigaInput": "amigainput", "ASL": "asl", "Compatibility": "compatibility", "Console": "console",
         "DefIcons": "deficons", "DOS": "dos", "Font": "fontprefs", "GUI": "gui", "Input": "input", "Internet": "internet",
         "Locale": "locale", "Notifications": "notifications", "Palette": "palette", "Picasso96Mode": "picasso96",
         "Pointer": "pointer", "PopupMenu": "popupmenu", "Printer": "printer", "PrinterGfx": "printergfx",
         "PrinterPS": "printerps", "ScreenBlanker": "screenblanker", "ScreenMode": "screenmode", "Screens": "screens",
         "Serial": "serial", "Sound": "sound", "Time": "time", "Timezone": "timezone", "UBoot": "uboot",
         "Updates": "updates", "URL": "url", "USB": "usbprefs", "WBPattern": "wbpattern", "WBStartup": "wbstartup",
         "Workbench": "workbench"}
for f, n in PREFS.items():
    m("SYS:Prefs/" + f, "p_" + n, "EmPrefs")
UTILS = {"Calculator": "calculator", "Clock": "clock", "FileCompare": "filecompare", "GraphicDump": "graphicdump",
         "IconEdit": "iconedit", "InitPrinter": "initprinter", "Installation Utility": "installer", "KeyShow": "keyshow",
         "LogViewer": "logviewer", "MEmacs": "memacs", "MultiView": "multiview", "NotePad": "notepad",
         "PartitionWizard": "partitionwizard", "PlayCD": "playcd", "PrefsObjectsEditor": "prefsobjects",
         "PrintFiles": "printfiles", "RawDisk": "rawdisk", "ShowConfig": "showconfig", "UnArc": "unarc",
         "USBInspector": "usbinspector"}
for f, n in UTILS.items():
    m("SYS:Utilities/" + f, "p_" + n)
SYSTEM = {"BIOSUpdater": "biosupdater", "Find": "find", "FixFonts": "fixfonts", "Format": "format", "FormatCDRW": "formatcdrw",
          "GrimReaper": "grimreaper", "Help": "help", "Mounter": "mounter", "RexxMast": "rexxmast",
          "RinghioServer": "ringhio", "Shell": "shell", "TypeManager": "typemanager", "Media Toolbox": "mediatoolbox"}
for f, n in SYSTEM.items():
    m("SYS:System/" + f, "p_" + n)
for f, em in (("Open Connection", "SdConnections"), ("New Connection", "EmConnNew"), ("Edit Connection", "EmConnEdit")):
    m("SYS:Internet/" + f, "network", em)
# the sub-drawers (Presets in Prefs included)
for p, n, t, _ in gs.SUBDRAWERS:
    m(p + "/" + n, "drawer", t)

# left alone on purpose (group 6): pointers, frames, overlays, dock and window icons
LEFT_ALONE = {"def_iconify", "def_window", "def_docky", "def_extras_dock", "def_internet_dock", "def_players_dock",
              "def_play", "def_kingcon", "def_pictureframe", "def_previewframe", "def_textframe", "icon_leftout",
              "icon_noaccess", "icon_nodrop", "update.prefs"}


def left_alone(path):
    n = path.split("/")[-1]
    return path.lower().startswith("envarc:sys/") and (n.endswith("pointer") or n in LEFT_ALONE)


# --- the check -------------------------------------------------------------------------------------

def listing():
    """{icon path without .info, lower case: (path, kind)} from the guest listing"""
    entries = {}
    for line in open(LISTING, encoding="latin-1"):
        if "|" in line:
            name, size = line.rstrip("\n").rsplit("|", 1)
            entries[name.lower()] = (name, size)
    icons = {}
    for low, (name, size) in entries.items():
        if low.endswith(".info"):
            base = name[:-5]
            kind = entries.get(base.lower(), (None, None))[1]
            icons[base.lower()] = (base, "drawer" if kind == "Dir" else ("file" if kind else "icon only"))
    return icons


def check():
    icons = listing()
    bad = 0
    seen = set()
    for path, base, em in MAPPING:
        key = path.lower()
        if key in seen:
            print("TWICE", path)
            bad += 1
        seen.add(key)
        if key not in icons:
            print("NOT ON THE GUEST", path)
            bad += 1
        kind = icons.get(key, (None, "?"))[1]
        if base == "drawer" and kind != "drawer" and not path.startswith(E):
            print("A DRAWER IMAGE ON A NON-DRAWER", path, kind)
            bad += 1
        if base != "drawer" and kind == "drawer" and not path.startswith(E) and base != "trashcan":
            print("A DRAWER GIVEN ANOTHER IMAGE", path, base)
            bad += 1
        a, b, _ = SOURCES[base]
        for f in (a, b):
            if not os.path.exists(os.path.join(G, f)):
                print("NO RENDER", f)
                bad += 1
        if em and not os.path.exists(emblem_source(em)[0]):
            print("NO EMBLEM", em)
            bad += 1
    gaps = collections.defaultdict(list)
    for key, (base, kind) in icons.items():
        if key in seen or left_alone(base) or key.startswith("sys:prefs/env-archive/"):
            continue
        d = base.rsplit("/", 1)[0] if "/" in base else base.split(":")[0] + ":"
        gaps[d].append((base.split("/")[-1], kind))
    return bad, seen, gaps


def tooltypes(base, em):
    tt = [f"IMAGE={SET}/{base}", f"IMAGESELECTED={SET}/{base}_sel"]
    if em:
        tt += [f"EMBLEM={SET}/{em},{AT}", f"EMBLEMSELECTED={SET}/{em},{AT}"]
    return tt


def export(out):
    img = os.path.join(out, "images")
    os.makedirs(img, exist_ok=True)
    used = sorted({b for _, b, _ in MAPPING})
    for b in used:
        a, s, th = SOURCES[b]
        for f, n in ((a, b), (s, b + "_sel")):
            bloom(Image.open(os.path.join(G, f)).convert("RGBA"), LIGHTBLUE, th).resize((64, 64), Image.LANCZOS) \
                .save(os.path.join(img, n + ".png"))
    ems = sorted({e for _, _, e in MAPPING if e})
    for e in ems:
        f, th = emblem_source(e)
        bloom(Image.open(f).convert("RGBA"), None, th).resize((28, 28), Image.LANCZOS).save(os.path.join(img, e + ".png"))
    with open(os.path.join(out, "mapping.txt"), "w") as fh:
        for path, b, e in MAPPING:
            fh.write(path + ".info|" + "|".join(tooltypes(b, e)) + "\n")
    print(f"{len(used)} bases (x2), {len(ems)} emblems -> {img}; {len(MAPPING)} icons -> mapping.txt")


def doc(gaps):
    lines = [f"# The icon set's mapping (working name \"{SET}\")", "",
             "Generated by tools/iconset_build.py from the decisions in docs/iconset_plan.md, checked against a",
             "full listing of the OS 4.1 guest. Every icon here becomes an Emblem icon with these tool types",
             f"(images in ENVARC:sys/emblem/{SET}/; IMAGESELECTED is the base name + \"_sel\").", "",
             f"{len(MAPPING)} icons.", "", "| Icon | Image | Emblem |", "|---|---|---|"]
    for path, b, e in MAPPING:
        lines.append(f"| {path}.info | {b} | {e or ''} |")
    lines += ["", "## Not mapped (the stock icon stays)", "",
              "Left alone on purpose: the mouse pointers, frames, overlays and dock/window icons in ENVARC:Sys.",
              "Every other stock icon not in the table, by drawer (to decide; kind: file / drawer / icon only):", ""]
    for d in sorted(gaps):
        items = sorted(gaps[d])
        lines.append(f"- **{d}** ({len(items)}): " + ", ".join(f"{n}" + ("" if k == "file" else f" ({k})") for n, k in items))
    open(os.path.join(ROOT, "docs", "iconset_mapping.md"), "w").write("\n".join(lines) + "\n")


def main():
    bad, seen, gaps = check()
    print(f"{len(MAPPING)} icons mapped, {sum(len(v) for v in gaps.values())} stock icons not mapped in {len(gaps)} drawers,"
          f" {bad} problems")
    doc(gaps)
    if len(sys.argv) > 1 and sys.argv[1] == "export":
        if bad:
            sys.exit("not exported: fix the problems first")
        export(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "build", "iconset", SET))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
