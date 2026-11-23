#!/home/claude/build/emblem-venv/bin/python
"""glass_programs_sheet.py DIR OUT.png [FLIP.gif] [SET]

Group 4 (programs) of the glass set, first batch: each program its own glass object, normal and
selected (one part moved), composed by the Emblem engine (build/host/render) like the real icons.
Uses the renders in DIR (<name>.png and <name>_open.png from tools/blender/glass_icons.py).
FLIP.gif: all of them switching between normal and selected. SET: programs (default) or prefs1, ...
(the Prefs editors, with the blue gear emblem, EmPrefs.png in DIR). ORIGINAL=<stock .info file>: the
stock icon (its two ARGB images) shown first, labelled "Original" (the user, 2026-11-23). Public domain.
"""
import os
import struct
import subprocess
import sys
import zlib

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glass_sheet import LIGHTBLUE, bloom  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENDER = os.path.join(ROOT, "build", "host", "render")
PREFS = "EMBLEMMETHOD=SHADOW\nSHADOWOFFSET=2,2\nSHADOWBLUR=2\nSHADOWOPACITY=55\n"
AT = "0,0,36,35"
DARK, LIGHT = (18, 20, 28, 255), (190, 192, 190, 255)
PER_ROW = 5

# id, program, render name, selected (what moves), emblem
ITEMS = [
    ("PR01", "Shell", "shell", "command typed, new prompt", None),
    ("PR02", "MultiView", "multiview", "lids open", None),
    ("PR03", "NotePad", "notepad", "pen writes", None),
    ("PR04", "Clock", "clock", "hands move on", None),
    ("PR05", "Calculator", "calculator", "= pressed", None),
    ("PR06", "Find", "find", "magnifier lifts", None),
    ("PR07", "Format", "format", "floppy slides in", None),
    ("PR08", "Help", "help", "cover opens", None),
    ("PR09", "IconEdit", "iconedit", "pencil moves on", None),
    ("PR10", "UnArc", "unarc", "small crate rises", None),
]

G = "EmPrefs"
SETS = {
    "programs": ("Programs, first batch", ITEMS),
    "prefs1": ("Prefs editors, batch 1", [
        ("PF01", "AHI", "ahi", "fader up", G),
        ("PF02", "AmigaInput", "amigainput", "stick tilts", G),
        ("PF03", "ASL", "asl", "selection moves down", G),
        ("PF04", "Compatibility", "compatibility", "pieces join", G),
        ("PF05", "Console", "console", "window grows", G),
        ("PF06", "DefIcons", "deficons", "card pops up", G),
        ("PF07", "DOS", "dos", "arm swings over", G),
        ("PF08", "Font", "fontprefs", "block stamps", G),
        ("PF09", "GUI", "gui", "slider moves", G),
    ]),
    "prefs2": ("Prefs editors, batch 2", [
        ("PF10", "Input", "input", "left button clicks", G),
        ("PF11", "Internet", "internet", "antenna extends", G),
        ("PF12", "Locale", "locale", "flag raised", G),
        ("PF13", "Notifications", "notifications", "bell swings", G),
        ("PF14", "Palette", "palette", "brush dips", G),
        ("PF15", "Picasso96Mode", "picasso96", "plug goes in", G),
        ("PF16", "Pointer", "pointer", "pointer clicks", G),
        ("PF17", "PopupMenu", "popupmenu", "submenu slides out", G),
        ("PF18", "Presets (drawer)", "drawer", "drawer opens", "EmPresets"),
    ]),
    "prefs3": ("Prefs editors, batch 3", [
        ("PF19", "Printer", "printer", "page comes out", G),
        ("PF20", "PrinterGfx", "printergfx", "picture comes out", G),
        ("PF21", "PrinterPS", "printerps", "curve page comes out", G),
        ("PF22", "ScreenBlanker", "screenblanker", "moon moves", G),
        ("PF23", "ScreenMode", "screenmode", "frame grows", G),
        ("PF24", "Screens", "screens", "front screen dragged down", G),
        ("PF25", "Serial", "serial", "plug goes in", G),
        ("PF26", "Sound", "sound", "cone pushes out", G),
        ("PF27", "Time", "time", "07:30, lit from within", G),
    ]),
    "prefs4": ("Prefs editors, batch 4", [
        ("PF28", "Timezone", "timezone", "globe turns", G),
        ("PF29", "UBoot", "uboot", "rocket lifts off", G),
        ("PF30", "Updates", "updates", "arrow drops in", G),
        ("PF31", "URL", "url", "links join", G),
        ("PF32", "USB", "usbprefs", "plug goes in", G),
        ("PF33", "WBPattern", "wbpattern", "roller rolls on", G),
        ("PF34", "WBStartup", "wbstartup", "rocker on, lit", G),
        ("PF35", "Workbench", "workbench", "windows open", G),
    ]),
    "utils1": ("Utilities, batch U1 (no emblem)", [
        ("UT01", "FileCompare", "filecompare", "the beam tips", None),
        ("UT02", "GraphicDump", "graphicdump", "screen grab comes out", None),
        ("UT03", "InitPrinter", "initprinter", "head returns home", None),
        ("UT04", "Installation Utility", "installer", "flaps open", None),
        ("UT05", "KeyShow", "keyshow", "key pressed, lit", None),
        ("UT06", "LogViewer", "logviewer", "unrolls further", None),
        ("UT07", "MEmacs", "memacs", "a line typed", None),
        ("UT08", "PartitionWizard", "partitionwizard", "wedge slides out", None),
    ]),
    "utils2": ("Utilities and System, batch U2 (no emblem)", [
        ("UT09", "PlayCD", "playcd", "lid opens", None),
        ("UT10", "PrefsObjectsEditor", "prefsobjects", "branch opens", None),
        ("UT11", "PrintFiles", "printfiles", "page feeds in", None),
        ("UT12", "RawDisk", "rawdisk", "sector lifts out (flat platter)", None),
        ("UT13", "ShowConfig", "showconfig", "exploded view", None),
        ("UT14", "USBInspector", "usbinspector", "magnifier over it", None),
        ("SY01", "BIOSUpdater", "biosupdater", "arrow onto the chip", None),
        ("SY02", "FixFonts", "fixfonts", "block snaps in line", None),
    ]),
    "utils3": ("System, batch U3 (no emblem)", [
        ("SY03", "FormatCDRW", "formatcdrw", "tray slides in", None),
        ("SY04", "GrimReaper", "grimreaper", "the Guru frame blinks on", None),
        ("SY05", "Mounter", "mounter", "drive into the bay", None),
        ("SY06", "RexxMast", "rexxmast", "crown lifts, lit", None),
        ("SY07", "RinghioServer", "ringhio", "a second notification", None),
        ("SY08", "TypeManager", "typemanager", "letter block lifts out", None),
        ("SY09", "Media Toolbox", "mediatoolbox", "partition resized", None),
    ]),
    "progemblems": ("Program drawers: the glass drawer + a glass version of the program's own icon", [
        ("SDP1", "Python", "drawer", "drawer opens", "Ep_python"),
        ("SDP2", "AmiUpdate", "drawer", "drawer opens", "Ep_amiupdate"),
        ("SDP3", "AmiPDF", "drawer", "drawer opens", "Ep_amipdf"),
        ("SDP4", "AmiGS", "drawer", "drawer opens", "Ep_amigs"),
        ("SDP5", "SGrab", "drawer", "drawer opens", "Ep_sgrab"),
        ("SDP6", "Ghostscript", "drawer", "drawer opens", "Ep_ghostscript"),
    ]),
    "internet_icons": ("Internet project icons: the DV08 network globe + a blue emblem (selected: lit from inside)", [
        ("IN01", "Open Connection", "network", "lit from inside", "SdConnections"),
        ("IN02", "New Connection", "network", "lit from inside", "EmConnNew"),
        ("IN03", "Edit Connection", "network", "lit from inside", "EmConnEdit"),
    ]),
    "presets_drawer": ("Presets is a drawer: the glass drawer + a swatch fan emblem", [
        ("PF18B", "Presets, blue", "drawer", "drawer opens", "EmPresets"),
        ("PF18V", "Presets, violet", "drawer", "drawer opens", "EmPresetsV"),
    ]),
    # the "do" icons (2026-11-21), one by one: Presets sub-drawers, the parent's blue
    "do_viewers": ("Utilities/AmiGS/AmiGS and Utilities/AmiPDF/AmiPDF: the page + magnifier (AmiGS variant A)", [
        ("DO10", "AmiGS", "amigs", "magnifier lifts", None),
        ("DO11", "AmiPDF", "amipdf", "magnifier lifts", None),
    ]),
    "do_sgrab": ("Utilities/SGrab/SGrab: the glass camera (the drawer emblem's), three ways to move", [
        ("DO12 A", "button + flash", "sgrab_a", "button + flash fire", None),
        ("DO12 B", "lens", "sgrab_b", "lens extends", None),
        ("DO12 C", "flash burst", "sgrab_c", "flash fires with rays", None),
    ]),
    "do_python": ("System/Python/Python: the Boing ball with its ring (the drawer emblem's), three ways to move", [
        ("DO13 A", "ball turns", "python_a", "checks turn", None),
        ("DO13 B", "bounce", "python_b", "jumps up", None),
        ("DO13 C", "ring", "python_c", "ring tilts, glows", None),
    ]),
    "co_amidock": ("Commodities/AmiDock: own glass object + the EmCommodity emblem", [
        ("CO01 A", "dock bar", "amidock_a", "middle icon up", "EmCommodity"),
        ("CO01 B", "red button", "amidock_b", "pressed, lit", "EmCommodity"),
        ("CO01 C", "upright dock", "amidock_c", "top icon out", "EmCommodity"),
    ]),
    "co_asyncwb": ("Commodities/AsyncWB (copies in the background): own glass object + the EmCommodity emblem", [
        ("CO02 A", "busy spinner", "asyncwb_a", "spinner turns", "EmCommodity"),
        ("CO02 B", "progress bar", "asyncwb_b", "bar fills", "EmCommodity"),
        ("CO02 C", "page moves", "asyncwb_c", "page arrives", "EmCommodity"),
    ]),
    "co_autobordersize": ("Commodities/AutoBorderSize (resize by catching the border): own glass object + EmCommodity", [
        ("CO03 A", "arrow on border", "autobordersize_a", "window wider", "EmCommodity"),
        ("CO03 B", "corner arrow", "autobordersize_b", "window bigger", "EmCommodity"),
        ("CO03 C", "border lights", "autobordersize_c", "wider, border lit", "EmCommodity"),
    ]),
    "co_autoinfo": ("Commodities/AutoInfo (an icon's information under the pointer): own glass object + EmCommodity", [
        ("CO04 A", "info card", "autoinfo_a", "card pops up", "EmCommodity"),
        ("CO04 B", "info sign", "autoinfo_b", "dot hops up", "EmCommodity"),
        ("CO04 C", "pointer", "autoinfo_c", "card slides out", "EmCommodity"),
    ]),
    "co_autopoint": ("Commodities/AutoPoint (the window under the pointer becomes active): own glass object + EmCommodity", [
        ("CO05 A", "back window", "autopoint_a", "its title lights", "EmCommodity"),
        ("CO05 B", "pointer moves", "autopoint_b", "onto it, lit", "EmCommodity"),
        ("CO05 C", "comes forward", "autopoint_c", "lit, forward", "EmCommodity"),
    ]),
    "co_clicktofront": ("Commodities/ClickToFront (the window you click on comes to the front): own glass object + EmCommodity", [
        ("CO06 A", "double click", "clicktofront_a", "to the front", "EmCommodity"),
        ("CO06 B", "swap", "clicktofront_b", "windows swap", "EmCommodity"),
        ("CO06 C", "three windows", "clicktofront_c", "back one forward", "EmCommodity"),
    ]),
    "co_contextmenus": ("Commodities/ContextMenus (pop-up menus where you click): own glass object + EmCommodity", [
        ("CO07 A", "menu", "contextmenus_a", "next item lit", "EmCommodity"),
        ("CO07 B", "pops up", "contextmenus_b", "menu appears", "EmCommodity"),
        ("CO07 C", "submenu", "contextmenus_c", "submenu out", "EmCommodity"),
    ]),
    "co_crossdos": ("Commodities/CrossDOS (reads and writes PC disks): own glass object + EmCommodity", [
        ("CO08 A", "floppy", "crossdos_a", "shutter opens", "EmCommodity"),
        ("CO08 B", "page out", "crossdos_b", "page rises", "EmCommodity"),
        ("CO08 C", "two-way arrow", "crossdos_c", "arrow lights", "EmCommodity"),
    ]),
    "co_deficons": ("Commodities/DefIcons (files without an icon get one by their type): own glass object + EmCommodity", [
        ("CO09 A", "typed pages", "deficons_a", "pages fan out", "EmCommodity"),
        ("CO09 B", "plain page", "deficons_b", "gets its type", "EmCommodity"),
        ("CO09 C", "stack", "deficons_c", "front page lifts", "EmCommodity"),
    ]),
    "co_depthtofront": ("Commodities/DepthToFront (the depth gadget brings a window to the front): own glass object + EmCommodity", [
        ("CO10 A", "depth gadget", "depthtofront_a", "to the front", "EmCommodity"),
        ("CO10 B", "two squares", "depthtofront_b", "back one forward", "EmCommodity"),
        ("CO10 C", "swap", "depthtofront_c", "windows swap", "EmCommodity"),
    ]),
    "co_exchange": ("Commodities/Exchange (turns the commodities on and off, shows and quits them): own glass object + EmCommodity", [
        ("CO11 A", "switches", "exchange_a", "one switched off", "EmCommodity"),
        ("CO11 B", "dot display", "exchange_b", "letters scroll", "EmCommodity"),
        ("CO11 C", "list", "exchange_c", "row selected, off", "EmCommodity"),
    ]),
    "co_fkey": ("Commodities/FKey (keys that start programs and do other actions): own glass object + EmCommodity", [
        ("CO12 A", "F1 key", "fkey_a", "pressed", "EmCommodity"),
        ("CO12 B", "three keys", "fkey_b", "middle pressed", "EmCommodity"),
        ("CO12 C", "key + window", "fkey_c", "window pops up", "EmCommodity"),
    ]),
    "co_mouseblanker": ("Commodities/MouseBlanker (hides the pointer while you type): own glass object + EmCommodity", [
        ("CO13 A", "window", "mouseblanker_a", "pointer fades", "EmCommodity"),
        ("CO13 B", "keys", "mouseblanker_b", "key down, pointer fades", "EmCommodity"),
        ("CO13 C", "typing", "mouseblanker_c", "text typed, pointer fades", "EmCommodity"),
    ]),
    "co_nocapslock": ("Commodities/NoCapsLock (Caps Lock does nothing): own glass object + EmCommodity", [
        ("CO14 A", "light", "nocapslock_a", "pressed, light out", "EmCommodity"),
        ("CO14 B", "no-sign", "nocapslock_b", "pressed, sign lit", "EmCommodity"),
        ("CO14 C", "A to a", "nocapslock_c", "pressed, small a", "EmCommodity"),
    ]),
    "co_rawbinfo": ("Commodities/RAWBInfo (Workbench's Information window, made with ReAction): own glass object + EmCommodity", [
        ("CO15 A", "info sign", "rawbinfo_a", "sign forward", "EmCommodity"),
        ("CO15 B", "page + window", "rawbinfo_b", "window pops up", "EmCommodity"),
        ("CO15 C", "info window", "rawbinfo_c", "field edited", "EmCommodity"),
    ]),
    "co_screenblankerengine": ("Commodities/ScreenBlankerEngine (blanks the screen when the computer is left alone): own glass object + EmCommodity", [
        ("CO16 A", "roller blind", "screenblankerengine_a", "blind down", "EmCommodity"),
        ("CO16 B", "blanks", "screenblankerengine_b", "screen dark, stars", "EmCommodity"),
        ("CO16 C", "sleeps", "screenblankerengine_c", "dark, stars, Zz", "EmCommodity"),
    ]),
}


# the sub-drawers (tools/glass_symbols.py SUBDRAWERS), a sheet per parent (Storage and Devs together):
# the glass drawer + the emblem; IDs SD01... in SUBDRAWERS order
import glass_symbols as _gs  # noqa: E402
_SD = [(f"SD{i + 1:02d}", p, n, t) for i, (p, n, t, _) in enumerate(_gs.SUBDRAWERS)]
for _key, _parents in (("sub_utilities", ("SYS:Utilities",)), ("sub_system", ("SYS:System",)),
                       ("sub_internet", ("SYS:Internet",)), ("sub_emulation", ("SYS:Emulation",)),
                       ("sub_mui", ("SYS:MUI",)), ("sub_storagedevs", ("SYS:Storage", "SYS:Devs")),
                       ("sub_documentation", ("SYS:Documentation",))):
    SETS[_key] = (" + ".join(_parents) + " sub-drawers: the glass drawer + an emblem",
                  [(i, (p.split(":")[1] + "/" if len(_parents) > 1 else "") + n, "drawer", "drawer opens", t)
                   for i, p, n, t in _SD if p in _parents])


def stock_images(path):
    """the normal and selected images of an OS 4 icon (.info with FORM ICON, ARGB chunks), 64x64 RGBA"""
    d = open(path, "rb").read()
    i = d.find(b"FACE")
    w, h = d[i + 8] + 1, d[i + 9] + 1
    ims, p = [], 0
    while len(ims) < 2:
        p = d.find(b"ARGB", p + 1)
        if p < 0:
            break
        body = d[p + 8:p + 8 + struct.unpack(">I", d[p + 4:p + 8])[0]]
        for off in range(20):
            try:
                raw = zlib.decompress(body[off:])
                break
            except zlib.error:
                raw = b""
        if len(raw) >= w * h * 4:
            im = Image.frombytes("RGBA", (w, h), raw[:w * h * 4], "raw", "ARGB")
            c = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            c.alpha_composite(im, ((64 - w) // 2, (64 - h) // 2)) if w <= 64 and h <= 64 else None
            ims.append(c if w <= 64 and h <= 64 else im.resize((64, 64), Image.LANCZOS))
    if len(ims) == 1:
        ims.append(ims[0])
    return ims


def main():
    global ITEMS
    d, out = sys.argv[1:3]
    flip = sys.argv[3] if len(sys.argv) > 3 else None
    title, ITEMS = SETS[sys.argv[4] if len(sys.argv) > 4 else "programs"]
    idir = os.path.join(d, "icons")
    os.makedirs(idir, exist_ok=True)
    for _, _, n, _, em in ITEMS:
        for m in (n, n + "_open"):
            # BASE_BLOOM: 0.5 (default) or 0.86 for device-like bases (large light glass would wash out)
            bloom(Image.open(os.path.join(d, m + ".png")).convert("RGBA"), LIGHTBLUE, float(os.environ.get("BASE_BLOOM", "0.5"))) \
                .resize((64, 64), Image.LANCZOS).save(os.path.join(idir, m + ".png"))
        if em:
            # program emblems (Ep_*: white pages, coloured details) glow only from their brightest parts
            bloom(Image.open(os.path.join(d, em + ".png")).convert("RGBA"), None, 0.86 if em.startswith("Ep_") else 0.5) \
                .resize((28, 28), Image.LANCZOS).save(os.path.join(idir, em + ".png"))
    prefs = os.path.join(idir, "emblem.prefs")
    open(prefs, "w").write(PREFS)

    composed = {}
    for iid, _, n, _, em in ITEMS:
        tts = [f"IMAGE={n}", f"IMAGESELECTED={n}_open"]
        if em:
            tts += [f"EMBLEM={em},{AT}", f"EMBLEMSELECTED={em},{AT}"]
        pre = os.path.join(idir, "_r")
        r = subprocess.run([RENDER, "--dir", idir, "--prefs", prefs, "--out", pre] + tts,
                           capture_output=True, text=True).stdout
        assert "composed=1" in r, r
        composed[iid] = (Image.open(pre + "_1.png").convert("RGBA"), Image.open(pre + "_2.png").convert("RGBA"))
    if os.environ.get("ORIGINAL"):
        composed["Original"] = tuple(stock_images(os.environ["ORIGINAL"]))
        ITEMS = [("Original", "(stock)", None, "", None)] + list(ITEMS)

    cw, cell = 170, 150
    W = 12 + PER_ROW * cw
    blocks = []
    for state, title in ((0, title), (1, "Selected (one part moves)")):
        for k in range(0, len(ITEMS), PER_ROW):
            chunk = ITEMS[k:k + PER_ROW]
            blocks.append((title if k == 0 else None,
                           [(f"{iid} {prog}" + (f": {what}" if state and what else ""), composed[iid][state])
                            for iid, prog, _, what, _ in chunk]))
    H = 30 + sum((18 if t else 0) + 2 * (cell + 22) + 2 * 84 + 14 for t, _ in blocks)
    sheet = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    dr = ImageDraw.Draw(sheet)
    dr.text((12, 8), "Group 4: about 2x on dark and light, then real size on dark and light.", fill=(0, 0, 0))
    y = 30
    for title, row in blocks:
        if title:
            dr.text((12, y), title, fill=(120, 0, 0))
            y += 18
        for bg in (DARK, LIGHT):
            for k, (label, im) in enumerate(row):
                x = 12 + k * cw
                t = Image.new("RGBA", (cell, cell), bg)
                t.alpha_composite(im.resize((cell, cell), Image.LANCZOS))
                sheet.paste(t, (x, y))
                dr.text((x, y + cell + 4), label, fill=(0, 0, 0))
            y += cell + 22
        for bg in (DARK, LIGHT):
            dr.rectangle((0, y, W, y + 80), fill=bg)
            for k, (label, im) in enumerate(row):
                sheet.alpha_composite(im, (12 + k * cw + 43, y + 8))
            y += 84
        y += 14
    sheet.convert("RGB").save(out)
    print("sheet ->", out)

    if flip:
        frames = []
        rows = (len(ITEMS) + PER_ROW - 1) // PER_ROW
        for state in (0, 1):
            fr = Image.new("RGBA", (PER_ROW * (cell + 8) + 8, rows * (cell + 26) + 8), (255, 255, 255, 255))
            fd = ImageDraw.Draw(fr)
            for k, (iid, prog, _, _, _) in enumerate(ITEMS):
                x, y = 8 + (k % PER_ROW) * (cell + 8), 8 + (k // PER_ROW) * (cell + 26)
                t = Image.new("RGBA", (cell, cell), DARK)
                t.alpha_composite(composed[iid][state].resize((cell, cell), Image.LANCZOS))
                fr.paste(t, (x, y))
                fd.text((x, y + cell + 4), f"{iid} {prog}", fill=(0, 0, 0))
            frames.append(fr.convert("RGB"))
        frames[0].save(flip, save_all=True, append_images=frames[1:], duration=[900, 900], loop=0)
        print("flip ->", flip)


if __name__ == "__main__":
    main()
