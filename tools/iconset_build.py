#!/home/claude/build/emblem-venv/bin/python
"""iconset_build.py check|export [OUTDIR]|icons|package

The glass icon set as a package: which stock icon gets which image, selected image and emblem
(MAPPING), the final images (SOURCES, EMBLEMS), a check against a full listing of the guest
(build/work/inventory_full.txt: List SYS: ENVARC:Sys ALL LFORMAT "%P%N|%L"), and the export:

  OUTDIR/images/<name>.png   the images for ENVARC:sys/emblem/<SET>/ (bases 64x64, emblems 28x28)
  OUTDIR/mapping.txt         one line per icon: ICONPATH|TOOLTYPE|TOOLTYPE...  (for the installer)
  docs/iconset_mapping.md    the same for people, and every stock icon NOT mapped (the gaps)

  icons     build/iconset/icons/: the pictures of the package's own (native) icons as ARGB + a
            mkicons.script; run it in the guest with mkicon (see package/icons/README.md) and copy
            out/*.info to package/iconset/icons/
  package   export + the set's archive dist/<ARCHIVE>.lha (emblem_icons_glenz.lha) (stage build/stage-iconset): Install
            (package/iconset/Install with the names filled in), Images/<SET>/, Scripts/Backup and
            Scripts/Convert (generated from the mapping), Scripts/Verify, Scripts/Restore.body,
            Icons/Restore.info (docs/iconset_plan.md "The icon set's installer")

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
SET = os.environ.get("ICONSET", "glenz")          # the set's images: ENVARC:sys/emblem/<SET>/ (user, 2026-11-17)
NAME = "Glenz"                                     # the set's name: package drawer, Install, Restore
ARCHIVE = "emblem_icons_glenz"                     # dist/<ARCHIVE>.lha
BACKUP = "SYS:GlenzBackup"                         # where the set's Install saves the icons it changes
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
# the "do" icons (docs/iconset_plan.md DO08-DO13, CO01-CO16, picked 2026-11-22/23): own glass objects,
# with the bloom their sheets were approved with
DO_PROGRAMS = {"amiupdate": 0.5, "rollback": 0.5, "amigs": 0.5, "amipdf": 0.5, "sgrab": 0.5, "python": 0.86}
for _n, _b in DO_PROGRAMS.items():
    SOURCES["p_" + _n] = (f"do/{_n}.png", f"do/{_n}_open.png", _b)
COMMODITIES = {"AmiDock": "amidock", "AsyncWB": "asyncwb", "AutoBorderSize": "autobordersize", "AutoInfo": "autoinfo",
               "AutoPoint": "autopoint", "ClickToFront": "clicktofront", "ContextMenus": "contextmenus",
               "CrossDOS": "crossdos", "DefIcons": "deficons", "DepthToFront": "depthtofront", "Exchange": "exchange",
               "FKey": "fkey", "MouseBlanker": "mouseblanker", "NoCapsLock": "nocapslock", "RAWBInfo": "rawbinfo",
               "ScreenBlankerEngine": "screenblankerengine"}
for _n in COMMODITIES.values():
    SOURCES["c_" + _n] = (f"co/{_n}.png", f"co/{_n}_open.png", 0.86)


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
# the "do" icons (docs/iconset_plan.md, decided one by one 2026-11-21..23)
for n, t in (("AmiDock", "SdPrAmiDock"), ("Default", "SdPrDefault"), ("Patterns", "SdMuiPatterns"),
             ("Pointers", "SdPrPointers"), ("SilverGreen", "SdPrSilverGreen"), ("Sounds", "SdPrSounds")):
    m("SYS:Prefs/Presets/" + n, "drawer", t)                     # DO01-DO06
m("SYS:System/Python/Lib", "drawer", "SdPyLib")                 # DO07
for path, n in (("SYS:System/AmiUpdate/AmiUpdate", "amiupdate"), ("SYS:System/AmiUpdate/System_RollBack", "rollback"),
                ("SYS:Utilities/AmiGS/AmiGS", "amigs"), ("SYS:Utilities/AmiPDF/AmiPDF", "amipdf"),
                ("SYS:Utilities/SGrab/SGrab", "sgrab"), ("SYS:System/Python/Python", "python")):
    m(path, "p_" + n)                                           # DO08-DO13
for f, n in COMMODITIES.items():
    m("SYS:Utilities/Commodities/" + f, "c_" + n, "EmCommodity")  # DO14 emblem, CO01-CO16
for path in ("SYS:ChangeLog.guide", "SYS:Utilities/SGrab/SGrab.guide"):
    m(path, "file", "EmDocs")                                   # the guides: as def_guide

# left alone on purpose (group 6): pointers, frames, overlays, dock and window icons
LEFT_ALONE = {"def_iconify", "def_window", "def_docky", "def_extras_dock", "def_internet_dock", "def_players_dock",
              "def_play", "def_kingcon", "def_pictureframe", "def_previewframe", "def_textframe", "icon_leftout",
              "icon_noaccess", "icon_nodrop", "update.prefs"}


# whole drawers left alone, decided by the user: (prefix, why)
LEFT_ALONE_DRAWERS = [
    ("SYS:Emulation/", "everything below SYS:Emulation (the classic Workbench 3.1 disk, the ROMs; user "
                       "2026-11-17: only the two drawer icons in SYS:Emulation get the set)"),
]


def left_alone(path):
    n = path.split("/")[-1]
    if any(path.lower().startswith(p.lower()) for p, _ in LEFT_ALONE_DRAWERS):
        return True
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


LEFT_COUNT = {}   # icons left alone per LEFT_ALONE_DRAWERS entry (filled by check())

# The user's decisions on the stock icons not mapped yet, per drawer (2026-11-17; the IDs of that
# review): "do" = to be made later, "dont" = left alone for good, "later" = set aside for now.
GAP_DECISIONS = {
    "do":    ["SYS:", "SYS:Prefs/Presets", "SYS:System/AmiUpdate", "SYS:System/Python",
              "SYS:Utilities/AmiGS", "SYS:Utilities/AmiPDF", "SYS:Utilities/Commodities", "SYS:Utilities/SGrab"],
    "dont":  ["SYS:Documentation", "SYS:Documentation/AmiSSL", "SYS:Documentation/MiniGL/demos",
              "SYS:Documentation/SFTPHandler", "SYS:Prefs"],
    "later": ["SYS:Devs/DataTypes", "SYS:Devs/DOSDrivers", "SYS:Devs/Monitors", "SYS:Devs/Printers", "SYS:MUI",
              "SYS:MUI/Demos", "SYS:MUI/Docs", "SYS:MUI/Docs/Deutsch", "SYS:MUI/Docs/English",
              "SYS:MUI/Docs/Italiano", "SYS:MUI/Icons", "SYS:MUI/Rexx", "SYS:Prefs/Presets/AmiDock",
              "SYS:Prefs/Presets/Default", "SYS:Prefs/Presets/SilverGreen", "SYS:Storage/DOSDrivers",
              "SYS:Storage/Monitors", "SYS:Storage/NetInterfaces", "SYS:Storage/Printers", "SYS:Utilities/Blankers",
              "SYS:Utilities/Dockies"],
}
GAP_TITLES = {"do": "To do (decided, not made yet)", "dont": "Not needed (left alone)",
              "later": "Set aside for now", None: "Still to decide"}


def gap_decision(drawer):
    for k, ds in GAP_DECISIONS.items():
        if any(drawer.lower() == d.lower() for d in ds):
            return k
    return None


def check():
    icons = listing()
    LEFT_COUNT.clear()
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
    LEFT_COUNT["noparent"] = 0
    for key, (base, kind) in icons.items():
        parent = base.rsplit("/", 1)[0] if "/" in base else base.split(":")[0] + ":"
        if key not in seen and not left_alone(base) and not key.startswith("sys:prefs/env-archive/") and \
                (parent + "Disk" if parent.endswith(":") else parent).lower() not in icons:
            LEFT_COUNT["noparent"] += 1   # its drawer has no icon (user 2026-11-17): left alone
            continue
        if key in seen or left_alone(base) or key.startswith("sys:prefs/env-archive/"):
            if key not in seen and left_alone(base):
                for p, _ in LEFT_ALONE_DRAWERS:
                    if key.startswith(p.lower()):
                        LEFT_COUNT[p] = LEFT_COUNT.get(p, 0) + 1
            continue
        d = base.rsplit("/", 1)[0] if "/" in base else base.split(":")[0] + ":"
        gaps[d].append((base.split("/")[-1], kind))
    return bad, seen, gaps


def settings(base, em):
    """SHADOW on the emblems: the set was drawn with it, whatever EMBLEMMETHOD the user has"""
    es = [f"IMAGE={SET}/{base}", f"IMAGESELECTED={SET}/{base}_sel"]
    if em:
        es += [f"EMBLEM={SET}/{em},{AT},SHADOW", f"EMBLEMSELECTED={SET}/{em},{AT},SHADOW"]
    return es


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
            fh.write(path + ".info|" + "|".join(settings(b, e)) + "\n")
    print(f"{len(used)} bases (x2), {len(ems)} emblems -> {img}; {len(MAPPING)} icons -> mapping.txt")


# --- the set's package ------------------------------------------------------------

LHA = os.environ.get("LHA", os.path.expanduser("~/linux_archivers/lha/lha"))
PKG = os.path.join(ROOT, "package", "iconset")
SHADOW_PREFS = "EMBLEMMETHOD=SHADOW\nSHADOWOFFSET=2,2\nSHADOWBLUR=2\nSHADOWOPACITY=55\n"


def split(path):
    """'SYS:Prefs/Printer.info' -> ('SYS', 'Prefs/Printer.info')"""
    root, _, rel = path.partition(":")
    assert root in ("SYS", "ENVARC") and rel, path
    return root, rel


def files_changed():
    """every file the Install changes: the mapped icons and the settings file"""
    return [p + ".info" for p, _, _ in MAPPING] + ["ENVARC:sys/emblem.prefs"]


def script_backup():
    """Scripts/Backup B: copies every file that exists and isn't in the backup yet to
    B/files/<root>/<path> (Copy CLONE) and adds its MD5 to B/<root>.md5, the name relative to
    the root; an update so never replaces a saved original"""
    L = [".KEY B/A", ".BRA {", ".KET }",
         "; Backup: made by tools/iconset_build.py from the set's mapping. Saves every file the",
         "; set's Install changes (if it exists and isn't saved yet) and its MD5 checksum.",
         "; Public domain.", "", "FailAt 21", ""]
    dirs = sorted({f"{r}/{os.path.dirname(rel)}".rstrip("/") for r, rel in map(split, files_changed())})
    for d in dirs:
        L.append(f'MakeDir >NIL: "{{B}}/files/{d}" ALL')
    L.append("")
    for path in files_changed():
        root, rel = split(path)
        L += [f'If EXISTS "{path}"',
              f'  If NOT EXISTS "{{B}}/files/{root}/{rel}"',
              f'    Copy "{path}" "{{B}}/files/{root}/{rel}" CLONE QUIET',
              f'    CD {root}:',
              f'    MD5Sum "{rel}" >>"{{B}}/{root}.md5"',
              "  EndIf"]
        if path == "ENVARC:sys/emblem.prefs":
            # no settings file before: Restore deletes the one the Install writes
            L += ["Else", '  If NOT EXISTS "{B}/files/ENVARC/sys/emblem.prefs"',
                  '    Echo >"{B}/NoPrefs" "There was no ENVARC:sys/emblem.prefs before."', "  EndIf"]
        L.append("EndIf")
    L += ["CD SYS:", ""]
    return "\n".join(L)


def script_convert():
    """Scripts/Convert B: every icon that is saved in B becomes an Emblem icon with its tool
    types; changed default icons are copied to ENV:Sys (the ones in use)"""
    L = [".KEY B/A", ".BRA {", ".KET }",
         "; Convert: made by tools/iconset_build.py from the set's mapping. Only icons with a saved",
         "; copy in the backup drawer are changed. Public domain.", "",
         "FailAt 21", "Set done 0", "Set failed 0", ""]
    for path, b, e in MAPPING:
        root, rel = split(path + ".info")
        L += [f'If EXISTS "{path}.info"',
              f'  If EXISTS "{{B}}/files/{root}/{rel}"',
              f'    C:EmblemIcon >NIL: "{path}.info" TO=EMBLEM SET="{"|".join(settings(b, e))}" QUIET',
              "    If WARN",
              f'      Echo "Not changed: {path}.info"',
              "      Set failed `Eval $failed + 1`",
              "    Else",
              "      Set done `Eval $done + 1`"]
        if root == "ENVARC" and rel.lower().startswith("sys/"):
            L.append(f'      Copy >NIL: "{path}.info" "ENV:{rel}" CLONE QUIET')
        L += ["    EndIf", "  EndIf", "EndIf"]
    L += ["", 'Echo "$done icons have their new pictures."', "If $failed GT 0",
          '  Echo "$failed could not be changed (listed above)."', "  Quit 5", "EndIf", ""]
    return "\n".join(L)


def icon_pictures():
    """the package's own icons (native, made in the guest by mkicon): name -> (normal, selected,
    type, default tool, tool types, stack, window); pictures composed from the set's images by the
    module's engine (build/host/render) with the set's shadow"""
    return {
        NAME: (("drawer", "EmPicture"), "DRAWER", None, (), None, (80, 60, 420, 200)),
        "Install": (("p_installer", None), "PROJECT", "SYS:Utilities/Installer",
                    (f"APPNAME={NAME}", "MINUSER=AVERAGE", "DEFUSER=AVERAGE", f"LOGFILE=T:{NAME}_install.log"),
                    32768, None),
        "Restore": (("file", "EmCode"), "PROJECT", "C:IconX",
                    (f"WINDOW=CON:60/40/620/320/{NAME} Restore/AUTO/CLOSE/WAIT",), 16384, None),
    }


def icons(out):
    import subprocess
    import tempfile
    img = os.path.join(ROOT, "build", "iconset", SET, "images")
    os.makedirs(out, exist_ok=True)
    lines = ["; made by tools/iconset_build.py icons: run in a drawer with mkicon and the .argb files",
             "FailAt 21", "MakeDir >NIL: out"]
    with tempfile.TemporaryDirectory() as tmp:
        prefs = os.path.join(tmp, "emblem.prefs")
        open(prefs, "w").write(SHADOW_PREFS)
        for name, ((base, em), typ, tool, tts, stack, window) in icon_pictures().items():
            tt = [f"IMAGE={base}", f"IMAGESELECTED={base}_sel"]
            if em:
                tt += [f"EMBLEM={em},{AT}", f"EMBLEMSELECTED={em},{AT}"]
            pre = os.path.join(tmp, "r")
            r = subprocess.run([os.path.join(ROOT, "build", "host", "render"), "--dir", img, "--prefs", prefs,
                                "--out", pre] + tt, capture_output=True, text=True).stdout
            assert "composed=1" in r, r
            for i, suffix in ((1, ""), (2, ".sel")):
                im = Image.open(f"{pre}_{i}.png").convert("RGBA")
                assert im.size == (64, 64), im.size
                im.save(os.path.join(out, f"{name}{suffix}.png"))
                open(os.path.join(out, f"{name}{suffix}.argb"), "wb").write(
                    b"".join(bytes((a, r_, g, b_)) for (r_, g, b_, a) in im.get_flattened_data()))
            args = [f'"out/{name}"', f"ARGB={name}.argb", f"SELECTED={name}.sel.argb", "TYPE=" + typ]
            if tool:
                args.append(f'"TOOL={tool}"')
            if stack:
                args.append(f"STACK={stack}")
            if window:
                args.append("WINDOW=%d,%d,%d,%d" % window)
            args += [f'"TT={t}"' for t in tts]
            lines.append("mkicon " + " ".join(args))
    open(os.path.join(out, "mkicons.script"), "w").write("\n".join(lines) + "\n")
    print(f"{len(icon_pictures())} icon pictures + mkicons.script -> {out}")


def package():
    import shutil
    import subprocess
    exp = os.path.join(ROOT, "build", "iconset", SET)
    export(exp)
    stage = os.path.join(ROOT, "build", "stage-iconset")
    shutil.rmtree(stage, ignore_errors=True)
    d = os.path.join(stage, NAME)
    os.makedirs(os.path.join(d, "Scripts"))
    os.makedirs(os.path.join(d, "Icons"))
    shutil.copytree(os.path.join(exp, "images"), os.path.join(d, "Images", SET))
    inst = open(os.path.join(PKG, "Install")).read()
    for k, v in (("@NAME@", NAME), ("@SET@", SET), ("@BACKUP@", BACKUP), ("@COUNT@", str(len(MAPPING)))):
        inst = inst.replace(k, v)
    assert "@" not in inst.replace("@app-name", "").replace("@user-level", "").replace("@askchoice-help", "") \
        .replace("@askbool-help", "").replace("@makedir-help", "").replace("@textfile-help", "") \
        .replace("@copyfiles-help", ""), "a placeholder is left in Install"
    open(os.path.join(d, "Install"), "w", encoding="latin-1").write(inst)
    open(os.path.join(d, "Scripts", "Backup"), "w").write(script_backup())
    open(os.path.join(d, "Scripts", "Convert"), "w").write(script_convert())
    for f in ("Verify", "Restore.body"):
        shutil.copy(os.path.join(PKG, f), os.path.join(d, "Scripts", f))
    ic = os.path.join(PKG, "icons")
    missing = [n for n in icon_pictures() if not os.path.exists(os.path.join(ic, n + ".info"))]
    if missing:
        sys.exit(f"package/iconset/icons/ has no {', '.join(missing)}.info: run `iconset_build.py icons` and mkicon")
    shutil.copy(os.path.join(ic, NAME + ".info"), os.path.join(stage, NAME + ".info"))
    shutil.copy(os.path.join(ic, "Install.info"), os.path.join(d, "Install.info"))
    shutil.copy(os.path.join(ic, "Restore.info"), os.path.join(d, "Icons", "Restore.info"))
    out = os.path.join(ROOT, "dist", ARCHIVE + ".lha")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out):
        os.remove(out)
    subprocess.run([LHA, "aq2o5", out, NAME + ".info", NAME], cwd=stage, check=True)
    n = sum(len(f) for _, _, f in os.walk(stage))
    print(f"{n} files -> {out} ({os.path.getsize(out) // 1024} KB)")


def doc(gaps):
    lines = [f"# The icon set's mapping (working name \"{SET}\")", "",
             "Generated by tools/iconset_build.py from the decisions in docs/iconset_plan.md, checked against a",
             "full listing of the OS 4.1 guest. Every icon here becomes an Emblem icon with these settings",
             f"(images in ENVARC:sys/emblem/{SET}/; IMAGESELECTED is the base name + \"_sel\").", "",
             f"{len(MAPPING)} icons.", "", "| Icon | Image | Emblem |", "|---|---|---|"]
    for path, b, e in MAPPING:
        lines.append(f"| {path}.info | {b} | {e or ''} |")
    lines += ["", "## Not mapped (the stock icon stays)", "",
              "Left alone on purpose: the mouse pointers, frames, overlays and dock/window icons in ENVARC:Sys;"]
    lines += [f"{why} ({LEFT_COUNT.get(p, 0)} icons)." if i == len(LEFT_ALONE_DRAWERS) - 1 else f"{why} ({LEFT_COUNT.get(p, 0)} icons);"
              for i, (p, why) in enumerate(LEFT_ALONE_DRAWERS)]
    lines += [f"Icons in a drawer that has no icon itself (user 2026-11-17) ({LEFT_COUNT.get('noparent', 0)} icons).",
              "", "Every other stock icon not in the table, by drawer and the user's decision (2026-11-17; kind:",
              "file / drawer / icon only):"]
    for dec in ("do", "dont", "later", None):
        ds = [d for d in sorted(gaps, key=str.lower) if gap_decision(d) == dec]
        if not ds:
            continue
        lines += ["", f"### {GAP_TITLES[dec]} ({sum(len(gaps[d]) for d in ds)} icons)", ""]
        for d in ds:
            items = sorted(gaps[d])
            lines.append(f"- **{d}** ({len(items)}): " + ", ".join(f"{n}" + ("" if k == "file" else f" ({k})")
                                                                    for n, k in items))
    open(os.path.join(ROOT, "docs", "iconset_mapping.md"), "w").write("\n".join(lines) + "\n")


def main():
    bad, seen, gaps = check()
    per = collections.Counter()
    for d, v in gaps.items():
        per[gap_decision(d)] += len(v)
    print(f"{len(MAPPING)} icons mapped, {sum(len(v) for v in gaps.values())} stock icons not mapped in {len(gaps)} drawers"
          f" (to do {per['do']}, not needed {per['dont']}, set aside {per['later']}, undecided {per[None]}),"
          f" {bad} problems")
    doc(gaps)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd in ("export", "package", "icons") and bad:
        sys.exit(f"no {cmd}: fix the problems first")
    if cmd == "export":
        export(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "build", "iconset", SET))
    elif cmd == "icons":
        export(os.path.join(ROOT, "build", "iconset", SET))
        icons(os.path.join(ROOT, "build", "iconset", "icons"))
    elif cmd == "package":
        package()
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
