"""glass_utils.py: the Utilities and System programs of the glass icon set (group 4), loaded by
glass_icons.py after glass_prefs.py, into the same namespace (helpers, materials, printer_body, ...).

Each program is a glass object of its own with one moving part (its selected image), no emblem (the
user, 2026-11-16). Every name was checked against docs/iconset_inventory.md: all programs, no drawers.
Public domain.
"""
import math

import bpy
from mathutils import Matrix, Vector


def mini_page(name, w, h, lines, mat=None):
    """a small upright glass page (bottom at z = 0) with lines of text: lines = [(dx, length), ...]"""
    p = box(name, 0, 0, h / 2, w, 0.02, h, glass_material(name + "_g", ICE, 0.08), 0.006)
    wire(p, name + "_wire", mat or m_edge, 0.006)
    for k, (dx, ln) in enumerate(lines):
        box(f"{name}_l{k}", dx, -0.016, h - 0.1 - k * 0.09, ln, 0.008, 0.025, m_core, 0)


# --- batch U1 (UT01-UT08) ------------------------------------------------------------------------

def u_filecompare(sel):
    """UT01 FileCompare: a glass balance with a page on each pan; selected: the beam tips, they differ"""
    L, zp, tilt = 0.85, 1.55, 14

    def stand():
        b = box("bal_base", 0, 0, 0.06, 1.0, 0.6, 0.12, m_glass, 0.04)
        wire(b, "bal_base_wire")
        cylinder("bal_post", 0, 0, 0.12 + (zp - 0.12) / 2, 0.06, zp - 0.12, m_glass)
        cylinder("bal_post_core", 0, 0, 0.12 + (zp - 0.12) / 2, 0.016, zp - 0.16, m_core, verts=12)
        bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.0, radius2=0.09, depth=0.12, location=(0, 0, zp + 0.02))
        c = bpy.context.object
        c.name = "bal_pointer"
        bpy.ops.object.shade_smooth()
        register(c, m_hot)
    turned(built(stand), TURN)

    def beam():
        bm = box("bal_beam", 0, 0, 0, 2 * L, 0.07, 0.07, m_glass, 0.02)
        wire(bm, "bal_beam_wire", m_edge, 0.01)
        cylinder("bal_hub", 0, 0, 0, 0.08, 0.1, m_hot, axis="Y")
    piv = TURN @ at(0, 0, zp + 0.08)
    moving(beam, piv, piv @ rot("Y", tilt), sel)

    def pan(side, lines):
        def fn():
            cylinder(f"bal_pan{side}", 0, 0, 0, 0.36, 0.04, m_glass)
            torus(f"bal_pan{side}_rim", 0, 0, 0.02, 0.36, 0.012, m_edge)
            for k in range(3):
                ang = k * 120 + 90
                line(f"bal_string{side}{k}", [(0.33 * math.cos(math.radians(ang)), 0.33 * math.sin(math.radians(ang)), 0.02),
                                              (0, 0, 0.62)], m_core, 0.005)
            pg = built(lambda: mini_page(f"bal_page{side}", 0.42, 0.5, lines))
            turned(pg, at(0, 0, 0.02))
        return fn
    drop = L * math.sin(math.radians(tilt))
    for side, sx, lines in ((-1, -L, [(0, 0.3), (-0.03, 0.24), (0, 0.3), (-0.05, 0.2)]),
                            (1, L, [(0, 0.3), (0.03, 0.18), (0, 0.3), (-0.08, 0.14)])):
        m0 = TURN @ at(sx, 0, zp + 0.08 - 0.62)
        m1 = TURN @ at(sx * math.cos(math.radians(tilt)), 0, zp + 0.08 - 0.62 - side * drop)
        moving(pan(side, lines), m0, m1, sel)


def u_graphicdump(sel):
    """UT02 GraphicDump: the glass printer, a page with a screen grab (a screen, a window on it)"""
    def art(yf, w, h, zmin):
        x0, x1, zb, zt = -w / 2 + 0.1, w / 2 - 0.1, h - 0.85, h - 0.1
        frame = [(x0, yf, zt), (x1, yf, zt), (x1, yf, zb), (x0, yf, zb), (x0, yf, zt)]
        for k, part in enumerate(clipped(frame, zmin)):
            line(f"gd_screen{k}", part, m_edge, 0.008)
        if zt - 0.05 >= zmin:
            box("gd_bar", 0, yf, zt - 0.05, x1 - x0 - 0.04, 0.008, 0.03, m_core, 0)
        wx0, wx1, wzb, wzt = x0 + 0.12, x1 - 0.2, zb + 0.15, zt - 0.17
        win = [(wx0, yf, wzt), (wx1, yf, wzt), (wx1, yf, wzb), (wx0, yf, wzb), (wx0, yf, wzt)]
        for k, part in enumerate(clipped(win, zmin)):
            line(f"gd_win{k}", part, m_hot, 0.01)
        if wzt - 0.04 >= zmin:
            box("gd_win_title", (wx0 + wx1) / 2, yf, wzt - 0.04, wx1 - wx0 - 0.04, 0.008, 0.025, m_hot, 0)
        for k in range(3):
            z = wzt - 0.14 - k * 0.1
            if z >= zmin:
                box(f"gd_win_line{k}", (wx0 + wx1) / 2 - 0.03, yf, z, wx1 - wx0 - 0.16, 0.008, 0.02, m_core, 0)
    printer(sel, art)


def u_initprinter(sel):
    """UT03 InitPrinter: the glass printer, its print head on a rail seen through the glass; selected:
    the head returned to its start (the printer initialised)"""
    turned(built(printer_body), TURN)
    zr = PRN_H - 0.16

    def rail():
        cylinder("ip_rail", 0, -0.05, zr, 0.02, PRN_W - 0.3, m_core, verts=12).rotation_euler = (0, math.pi / 2, 0)
        box("ip_home", -PRN_W / 2 + 0.22, -0.05, zr, 0.03, 0.12, 0.12, m_edge, 0)
    turned(built(rail), TURN)

    def head():
        h = box("ip_head", 0, 0, 0, 0.22, 0.2, 0.16, m_glass, 0.02)
        wire(h, "ip_head_wire", m_hot, 0.008)
        box("ip_nozzle", 0, -0.11, -0.04, 0.12, 0.02, 0.04, m_hot, 0)
    moving(head, TURN @ at(0.5, -0.05, zr), TURN @ at(-PRN_W / 2 + 0.36, -0.05, zr), sel)


def u_installer(sel):
    """UT04 Installation Utility: a glass software box with its flaps closed, a glowing disc inside;
    selected: the flaps opened"""
    W, D, H = 1.25, 0.9, 0.85

    def body():
        b = open_box("inst_box", 0, 0, H / 2, W, D, H, m_glass, wall=0.035)
        wire(b, "inst_box_wire")
        box("inst_label", 0, -D / 2 - 0.006, H * 0.6, 0.7, 0.01, 0.06, m_core, 0)
        line("inst_arrow", [(-0.08, -D / 2 - 0.008, H * 0.42), (0, -D / 2 - 0.008, H * 0.3), (0.08, -D / 2 - 0.008, H * 0.42)],
             m_hot, 0.014)
        cylinder("inst_disc", 0, 0.05, H * 0.6, 0.3, 0.03, m_hot, axis="Y")
        cylinder("inst_disc_hole", 0, 0.03, H * 0.6, 0.06, 0.035, lacquer_material("inst_hole"), axis="Y")
        torus("inst_disc_ring", 0, 0.03, H * 0.6, 0.2, 0.008, m_core, axis="Y")
    turned(built(body), TURN)

    for sgn in (-1, 1):
        def flap(sgn=sgn):
            f = box(f"inst_flap{sgn}", -sgn * W / 4, 0, 0.015, W / 2 - 0.01, D - 0.02, 0.03, m_glass, 0.01)
            wire(f, f"inst_flap{sgn}_wire", m_edge, 0.008)
        hinge = TURN @ at(sgn * W / 2, 0, H)
        moving(flap, hinge, hinge @ rot("Y", sgn * 125), sel)          # up and outwards


def u_keyshow(sel):
    """UT05 KeyShow: a glass keyboard section (sloping), rows of keys and a space bar; selected: one key
    pressed down and lit"""
    W, D, h0, h1 = 1.9, 1.05, 0.14, 0.34
    a = math.degrees(math.atan2(h1 - h0, D))

    def on_top(x, y, lift=0.0):
        return at(x, y, h0 + (y + D / 2) / D * (h1 - h0) + lift) @ rot("X", a)

    def body():
        v = [(-W / 2, -D / 2, 0), (W / 2, -D / 2, 0), (W / 2, D / 2, 0), (-W / 2, D / 2, 0),
             (-W / 2, -D / 2, h0), (W / 2, -D / 2, h0), (W / 2, D / 2, h1), (-W / 2, D / 2, h1)]
        o = slab("kbd", v, m_glass, 0.03)
        wire(o, "kbd_wire")
        for r in range(3):
            for c in range(6):
                if (r, c) == (1, 2):
                    continue
                k = box(f"key{r}{c}", 0, 0, 0, 0.24, 0.22, 0.1, m_glass, 0.03)
                w = wire(k, f"key{r}{c}_wire", m_core, 0.006)
                turned([k, w], on_top(-0.75 + c * 0.3 + r * 0.06, 0.28 - r * 0.27, 0.06))
        sp = box("key_space", 0, 0, 0, 1.0, 0.22, 0.1, m_glass, 0.03)
        w = wire(sp, "key_space_wire", m_core, 0.006)
        turned([sp, w], on_top(0.05, -0.38, 0.06))

    def key():
        k = box("key_shown", 0, 0, 0, 0.24, 0.22, 0.1, m_hot if sel else m_glass, 0.03)
        wire(k, "key_shown_wire", m_hot, 0.008)
    turned(built(body), TURN)
    m = on_top(-0.75 + 2 * 0.3 + 0.06, 0.28 - 0.27, 0.06)
    moving(key, TURN @ m, TURN @ m @ at(0, 0, -0.05), sel)


def u_logviewer(sel):
    """UT06 LogViewer: a glass scroll hanging from a roller between two posts, lines of log on it;
    selected: unrolled further, more lines"""
    zr, W = 1.62, 1.2
    L = 0.75 if not sel else 1.25

    def body():
        b = box("log_base", 0, 0, 0.05, W + 0.5, 0.6, 0.1, m_glass, 0.04)
        wire(b, "log_base_wire")
        for sgn in (-1, 1):
            cylinder(f"log_post{sgn}", sgn * (W / 2 + 0.12), 0, 0.1 + (zr - 0.1) / 2, 0.04, zr - 0.1, m_glass)
            sphere(f"log_knob{sgn}", sgn * (W / 2 + 0.12), 0, zr + 0.02, 0.06, m_hot)
        r = cylinder("log_roller", 0, 0, zr, 0.1, W + 0.15, m_glass)
        r.rotation_euler = (0, math.pi / 2, 0)
        o = torus("log_roller_glow", 0, 0, zr, 0.1, 0.01, m_edge)
        o.rotation_euler = (0, math.pi / 2, 0)
        p = box("log_paper", 0, -0.1, zr - L / 2, W, 0.015, L, glass_material("log_paper_g", ICE, 0.08), 0.004)
        wire(p, "log_paper_wire", m_edge, 0.006)
        n = int((L - 0.1) / 0.1)
        for k in range(n):
            ln = (0.8, 0.55, 0.95, 0.4, 0.7, 0.85)[k % 6]
            box(f"log_line{k}", -W / 2 + 0.1 + ln / 2, -0.11, zr - 0.15 - k * 0.1, ln, 0.008, 0.025, m_hot if k == n - 1 else m_core, 0)
        bw = cylinder("log_weight", 0, -0.1, zr - L, 0.045, W + 0.05, m_glass)
        bw.rotation_euler = (0, math.pi / 2, 0)
    turned(built(body), TURN)


def u_memacs(sel):
    """UT07 MEmacs: a glass page of indented text (code) with a glowing block cursor; selected: the
    next line typed, the cursor at its end"""
    W, H = 1.25, 1.6
    lines = [(0.0, 0.6), (0.15, 0.7), (0.15, 0.45), (0.3, 0.55), (0.3, 0.35), (0.15, 0.2), (0.0, 0.1)]

    def body():
        p = box("emacs_page", 0, 0, H / 2, W, 0.1, H, m_glass, 0.03)
        wire(p, "emacs_page_wire")
        yf = -0.056
        box("emacs_mode", 0, yf, 0.12, W - 0.1, 0.01, 0.07, glass_material("emacs_mode_g", ICE, 0.05), 0.004)
        box("emacs_mode_text", -0.2, yf - 0.006, 0.12, 0.5, 0.008, 0.02, m_core, 0)
        n = len(lines) if sel else len(lines) - 1
        for k in range(n):
            ind, ln = lines[k]
            box(f"emacs_l{k}", -W / 2 + 0.12 + ind + ln / 2, yf, H - 0.18 - k * 0.17, ln, 0.008, 0.035,
                m_hot if k == n - 1 else m_core, 0)
        ind, ln = lines[n - 1]
        xc = -W / 2 + 0.12 + ind + ln + 0.06
        box("emacs_cursor", xc, yf - 0.006, H - 0.18 - (n - 1) * 0.17, 0.06, 0.012, 0.1, m_hot, 0)
    turned(built(body), TURN)


def u_partitionwizard(sel):
    """UT08 PartitionWizard: a disk as a standing glass pie of partitions on a stand; selected: one
    partition (wedge) slid out"""
    R, t, zc = 0.78, 0.16, 1.0
    shares = [0.2, 0.38, 0.27, 0.15]
    out = 0                                         # the wedge that slides out (upper right)

    def wedge_pts(a0, a1):
        n = max(3, int((a1 - a0) / 8))
        return [(0.0, 0.0)] + [(R * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
                                R * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]

    angles, a = [], 80
    for sh in shares:
        angles.append((a - sh * 360, a))
        a -= sh * 360

    def body():
        cylinder("pie_base", 0, 0, 0.05, 0.45, 0.1, m_glass)
        torus("pie_base_rim", 0, 0, 0.1, 0.45, 0.012, m_edge)
        cylinder("pie_post", 0, 0.05, 0.1 + (zc - R - 0.1) / 2 + 0.05, 0.05, zc - R - 0.0, m_glass)
        for k, (a0, a1) in enumerate(angles):
            if k == out:
                continue
            wedge(k, a0, a1)

    def wedge(k, a0, a1):
        mid = math.radians((a0 + a1) / 2)
        off = (0.02 * math.cos(mid), 0.02 * math.sin(mid))
        pts = [(x + off[0], z + off[1] + zc) for x, z in wedge_pts(a0, a1)]
        prism(f"pie{k}", pts, -t / 2, t / 2, m_glass)
        outline_curve(f"pie{k}_edge", [(x, -t / 2 - 0.004, z) for x, z in pts], 0.009, m_hot if k == out else m_edge)
    turned(built(body), TURN)
    a0, a1 = angles[out]
    mid = math.radians((a0 + a1) / 2)
    d = Vector((0.3 * math.cos(mid), 0, 0.3 * math.sin(mid)))
    moving(lambda: wedge(out, a0, a1), TURN, TURN @ Matrix.Translation(d), sel)


# --- batch U2 (UT09-UT14, SY01-SY02) -------------------------------------------------------------

def magnifier(name):
    """a glass magnifying glass lying in the x-y plane, the lens at the origin, the handle along -y"""
    sphere(name + "_lens", 0, 0, 0, 0.36, glass_material(name + "_lens_g", LIGHTBLUE, 0.0), scale=(1, 1, 0.16))
    torus(name + "_rim", 0, 0, 0, 0.39, 0.04, m_glass)
    torus(name + "_rim_glow", 0, 0, 0, 0.39, 0.012, m_hot)
    h = cylinder(name + "_handle", 0, 0, 0, 0.06, 0.62, m_glass)
    turned([h], at(0, -0.74, 0) @ rot("X", 90))
    c = torus(name + "_collar", 0, 0, 0, 0.07, 0.014, m_edge)
    turned([c], at(0, -0.44, 0) @ rot("X", 90))


def u_playcd(sel):
    """UT09 PlayCD: a round top-loading glass CD player, the disc seen through its lid; selected: the
    lid opened on its back hinge"""
    R, H = 0.85, 0.26

    def body():
        cylinder("cdp_body", 0, 0, H / 2, R, H, m_glass)
        torus("cdp_rim", 0, 0, H, R, 0.014, m_edge)
        torus("cdp_base_rim", 0, 0, 0.01, R, 0.01, m_core)
        cylinder("cdp_disc", 0, 0, H + 0.01, 0.62, 0.02, glass_material("cdp_disc_g", ICE, 0.04))
        for k, (r, mt) in enumerate(((0.6, m_edge), (0.42, m_core), (0.24, m_core))):
            torus(f"cdp_disc_ring{k}", 0, 0, H + 0.022, r, 0.008, mt)
        cylinder("cdp_hub", 0, 0, H + 0.03, 0.09, 0.04, m_hot)
        for k, ang in enumerate((-110, -90, -70)):
            x, y = (R + 0.005) * math.cos(math.radians(ang)), (R + 0.005) * math.sin(math.radians(ang))
            o = box(f"cdp_btn{k}", x, y, H * 0.5, 0.12, 0.03, 0.06, m_hot if k == 1 else m_core, 0.01)
            o.rotation_euler = (0, 0, math.radians(ang + 90))
    turned(built(body), TURN)

    def lid():
        cylinder("cdp_lid", 0, -R + 0.02, 0.03, R - 0.02, 0.06, m_glass)
        torus("cdp_lid_rim", 0, -R + 0.02, 0.06, R - 0.02, 0.012, m_edge)
        torus("cdp_lid_window", 0, -R + 0.02, 0.065, 0.35, 0.01, m_core)
    hinge = TURN @ at(0, R - 0.02, H + 0.035)
    moving(lid, hinge, hinge @ rot("X", -72), sel)


def u_prefsobjects(sel):
    """UT10 PrefsObjectsEditor: a glass tree of nodes on a standing glass board; selected: a branch
    opened, its two children slid out from behind it and the node below moved down to make room"""
    W, H = 1.6, 1.75
    yf = -0.05

    def node(name, x, z, mat=m_edge, lit=False):
        n = box(name, x, 0, z, 0.42, 0.05, 0.16, glass_material(name + "_g", ICE, 0.06), 0.02)
        wire(n, name + "_wire", mat, 0.007)
        box(name + "_label", x + 0.02, -0.03, z, 0.26, 0.008, 0.03, m_hot if lit else m_core, 0)

    def body():
        b = box("tree_board", 0, 0.08, H / 2, W, 0.06, H, m_glass, 0.03)
        wire(b, "tree_board_wire")
        node("tree_root", -0.45, 1.5, m_hot, True)
        node("tree_c1", -0.15, 1.2)
        node("tree_c2", -0.15, 0.9, m_hot)
        line("tree_trunk", [(-0.62, yf, 1.42), (-0.62, yf, 0.6 if not sel else 0.3)], m_core, 0.008)    # to the last node
        for z in (1.2, 0.9):
            line(f"tree_br{z}", [(-0.62, yf, z), (-0.36, yf, z)], m_core, 0.008)
        line("tree_mark_h", [(-0.4, yf - 0.03, 0.9), (-0.33, yf - 0.03, 0.9)], m_hot, 0.01)
        if not sel:                                  # + (closed) / - (open)
            line("tree_mark_v", [(-0.365, yf - 0.03, 0.865), (-0.365, yf - 0.03, 0.935)], m_hot, 0.01)
        else:
            line("tree_sub", [(-0.3, yf, 0.82), (-0.3, yf, 0.5)], m_core, 0.008)
            for z in (0.66, 0.5):
                line(f"tree_sub_br{z}", [(-0.3, yf, z), (-0.02, yf, z)], m_core, 0.008)
    turned(built(body), TURN)
    for k, z1 in enumerate((0.66, 0.5)):
        def child(k=k):
            node(f"tree_g{k}", 0, 0, m_edge)
        moving(child, TURN @ at(-0.15, 0.03, 0.9), TURN @ at(0.2, 0, z1), sel)

    def last():
        node("tree_c3", 0, 0)
        line("tree_br_c3", [(-0.47, yf, 0), (-0.21, yf, 0)], m_core, 0.008)      # its branch moves with it
    moving(last, TURN @ at(-0.15, 0, 0.6), TURN @ at(-0.15, 0, 0.3), sel)


def u_printfiles(sel):
    """UT11 PrintFiles: the glass printer, a file page (the G05 page with its folded corner) standing in
    its input tray; selected: the page fed in"""
    turned(built(printer_body), TURN)
    H, D, pw = PRN_H, PRN_D, PRN_PW
    w, h, fold = 0.8, 1.0, 0.24

    def page():
        outline = [(-w / 2, 0), (w / 2, 0), (w / 2, h - fold), (w / 2 - fold, h), (-w / 2, h)]
        prism("pf_page", outline, -0.012, 0.012, glass_material("pf_page_g", ICE, 0.08))
        outline_curve("pf_page_edge", [(x, -0.016, z) for x, z in outline], 0.007, m_edge)
        tri = [(w / 2 - fold, h), (w / 2, h - fold), (w / 2 - fold, h - fold)]
        prism("pf_fold", tri, -0.03, -0.012, m_glass)
        for k in range(5):
            box(f"pf_line{k}", -0.06, -0.018, h - 0.2 - k * 0.15, 0.5 if k % 2 else 0.6, 0.008, 0.025, m_core, 0)
    tilt = rot("X", -20)
    base = TURN @ at(0, D / 2 + 0.02, H) @ tilt
    moving(page, base @ at(0, 0, 0.12), base @ at(0, 0, -0.55), sel)


def u_rawdisk(sel):
    """UT12 RawDisk: a glass disk platter lying flat on the floor, its surface a disk layout (the user: a
    regular grid looked like a fan grille): tracks at irregular spacing, each divided into its own
    number of sectors (dividers staggered from track to track), used blocks lit at different brightness,
    two partition boundaries brighter; selected: one sector block lifted straight up out of it"""
    import random
    R, t = 1.0, 0.08
    tracks = [0.2, 0.31, 0.45, 0.56, 0.8, 0.9, 1.0]        # irregular track boundaries
    lift = (3, 25, 60)                                       # the lifted block: track 3 (0.56..0.8), 25..60 degrees
    rnd = random.Random(5)
    zt = t + 0.004

    def ring_cells(k):
        """the sector boundaries (degrees) of track k"""
        n = (5, 7, 9, 11, 16, 19)[k]
        off = rnd.uniform(0, 360 / n)
        cuts = sorted((off + i * 360 / n + rnd.uniform(-6, 6)) % 360 for i in range(n))
        if k == lift[0]:
            cuts = sorted([c for c in cuts if not (lift[1] - 8 < c < lift[2] + 8)] + [lift[1], lift[2]])
        return cuts

    def arc_pts(r, q0, q1, z):
        n = max(2, int(abs(q1 - q0) / 6))
        return [(r * math.cos(math.radians(q0 + (q1 - q0) * i / n)), r * math.sin(math.radians(q0 + (q1 - q0) * i / n)), z)
                for i in range(n + 1)]

    lit = [emission_material(f"rd_used{k}", LIGHTBLUE, st) for k, st in enumerate((0.5, 0.9, 1.5))]

    def body():
        cylinder("rd_platter", 0, 0, t / 2, R, t, glass_material("rd_platter_g", ICE, 0.04))
        for k, r in enumerate(tracks):
            torus(f"rd_track{k}", 0, 0, zt, r, 0.012 if k in (0, len(tracks) - 1) else 0.007,
                  m_edge if k in (0, len(tracks) - 1) else m_core)
        for k in range(len(tracks) - 1):
            r0, r1 = tracks[k], tracks[k + 1]
            cuts = ring_cells(k)
            for j, c in enumerate(cuts):
                q = math.radians(c)
                line(f"rd_cut{k}_{j}", [(r0 * math.cos(q), r0 * math.sin(q), zt), (r1 * math.cos(q), r1 * math.sin(q), zt)],
                     m_core, 0.005)
            for j in range(len(cuts)):                       # used blocks, lit at different brightness
                q0, q1 = cuts[j], cuts[(j + 1) % len(cuts)] + (360 if j == len(cuts) - 1 else 0)
                if k == lift[0] and abs(q0 - lift[1]) < 0.01:
                    continue
                if rnd.random() < 0.3:
                    m0, m1 = r0 + 0.012, r1 - 0.012
                    pts = [(x, y) for x, y, _ in arc_pts(m1, q0 + 1.5, q1 - 1.5, 0)] + \
                          [(x, y) for x, y, _ in arc_pts(m0, q1 - 1.5, q0 + 1.5, 0)]
                    cell = prism(f"rd_used{k}_{j}", pts, -zt - 0.003, -zt + 0.001, rnd.choice(lit))
                    turned([cell], rot("X", -90))
        for k, (q0, q1) in enumerate(((100, 175), (205, 330))):    # two partitions, outlined brighter
            line(f"rd_part{k}", arc_pts(tracks[-1] - 0.02, q0, q1, zt + 0.003), m_hot, 0.01)
        cylinder("rd_hub", 0, 0, t + 0.03, 0.09, 0.06, m_hot)
    turned(built(body), TURN)

    def sector():
        r0, r1 = tracks[lift[0]], tracks[lift[0] + 1]
        pts = [(x, y) for x, y, _ in arc_pts(r1 - 0.01, lift[1] + 1, lift[2] - 1, 0)] + \
              [(x, y) for x, y, _ in arc_pts(r0 + 0.01, lift[2] - 1, lift[1] + 1, 0)]
        sc = prism("rd_sector", pts, -t, 0.0, m_glass)              # extruded along y ...
        turned([sc], rot("X", -90))                                   # ... turned to lie flat (z 0..t)
        outline_curve("rd_sector_edge", [(x, y, t + 0.006) for x, y in pts], 0.011, m_hot)
    mid = math.radians((lift[1] + lift[2]) / 2)
    out = Vector((0.12 * math.cos(mid), 0.12 * math.sin(mid), 0.5))
    moving(sector, TURN @ at(0, 0, 0.002), TURN @ Matrix.Translation(out), sel)


def u_showconfig(sel):
    """UT13 ShowConfig: a stack of glass hardware (a board, a chip, a cooler with fins); selected: the
    stack opened up, an exploded view"""
    def board():
        b = box("sc_board", 0, 0, 0.05, 1.7, 1.2, 0.1, m_glass, 0.03)
        wire(b, "sc_board_wire")
        for k in range(5):
            line(f"sc_trace{k}", [(-0.75, -0.45 + k * 0.2, 0.104), (-0.3, -0.45 + k * 0.2, 0.104), (-0.2, -0.35 + k * 0.2, 0.104)],
                 m_core, 0.006)
        for k in range(4):
            box(f"sc_ram{k}", 0.55 + k * 0.08, 0, 0.18, 0.04, 0.9, 0.16, m_glass, 0.01)
    turned(built(board), TURN)

    def chip():
        c = box("sc_chip", 0, 0, 0.05, 0.6, 0.6, 0.1, lacquer_material("sc_chip_g"), 0.02)
        wire(c, "sc_chip_wire", m_hot, 0.008)
        box("sc_chip_die", 0, 0, 0.105, 0.3, 0.3, 0.01, m_core, 0)

    def cooler():
        b = box("sc_cool", 0, 0, 0.04, 0.7, 0.7, 0.08, m_glass, 0.02)
        wire(b, "sc_cool_wire", m_edge, 0.008)
        for k in range(7):
            f = box(f"sc_fin{k}", -0.3 + k * 0.1, 0, 0.26, 0.025, 0.7, 0.36, m_glass, 0.005)
            wire(f, f"sc_fin{k}_wire", m_core, 0.005)
    x, y = -0.25, 0.0
    moving(chip, TURN @ at(x, y, 0.1), TURN @ at(x, y, 0.45), sel)
    moving(cooler, TURN @ at(x, y, 0.2), TURN @ at(x, y, 0.95), sel)


def u_usbinspector(sel):
    """UT14 USBInspector: the USB-A plug (as in PF32) lying on the floor, a magnifier beside it;
    selected: the magnifier held over the trident"""
    def plug():
        bd = box("ui_body", -0.25, 0, 0.18, 0.9, 0.62, 0.36, m_glass, 0.08)
        wire(bd, "ui_body_wire", m_edge, 0.01)
        sh = box("ui_shell", 0.38, 0, 0.18, 0.36, 0.5, 0.2, glass_material("ui_shell_g", ICE, 0.05), 0.01)
        wire(sh, "ui_shell_wire", m_hot, 0.008)
        zt = 0.366
        xs = -0.25
        line("ui_tri", [(xs - 0.25, 0, zt), (xs + 0.2, 0, zt)], m_hot, 0.016)
        line("ui_tri_a", [(xs - 0.07, 0, zt), (xs + 0.03, -0.14, zt), (xs + 0.13, -0.14, zt)], m_hot, 0.013)
        line("ui_tri_b", [(xs - 0.14, 0, zt), (xs - 0.05, 0.12, zt), (xs + 0.06, 0.12, zt)], m_hot, 0.013)
        torus("ui_tri_c", xs - 0.28, 0, zt, 0.045, 0.013, m_hot)
        box("ui_tri_sq", xs + 0.16, -0.14, zt, 0.06, 0.06, 0.012, m_hot, 0)
        line("ui_tri_head", [(xs + 0.2, -0.06, zt), (xs + 0.29, 0, zt), (xs + 0.2, 0.06, zt)], m_hot, 0.013)
        outline_curve("ui_cable", [(-0.7, 0, 0.18), (-0.95, 0.05, 0.1), (-1.15, 0.25, 0.04)], 0.045, m_edge, closed=False)
    turned(built(plug), TURN @ rot("Z", 10))
    FRAME_EXTRA.extend(TURN @ rot("Z", 10) @ Vector(p) for p in ((-0.7, 0, 0.18), (-0.95, 0.05, 0.1), (-1.15, 0.25, 0.04)))
    lie = TURN @ at(0.75, -0.7, 0.07) @ rot("Z", 40)
    over = TURN @ rot("Z", 10) @ at(-0.25, 0, 0.75) @ rot("Z", 60) @ rot("X", 18)
    moving(lambda: magnifier("ui_mag"), lie, over, sel)


def s_biosupdater(sel):
    """SY01 BIOSUpdater: a black glass flash chip with its pins and notch, a glowing arrow above it;
    selected: the arrow dropped onto the chip (the firmware flashed)"""
    L, Wc, Hc = 1.3, 0.7, 0.2
    arrow = [(-0.12, 0.3), (-0.3, 0.3), (0, -0.05), (0.3, 0.3), (0.12, 0.3), (0.12, 0.65), (-0.12, 0.65)]

    def chip():
        c = box("bu_chip", 0, 0, 0.12 + Hc / 2, L, Wc, Hc, glass_material("bu_black", srgb((8, 10, 15)), 0.05), 0.02)
        wire(c, "bu_chip_wire", m_edge, 0.01)
        cylinder("bu_notch", -L / 2 + 0.12, 0, 0.12 + Hc + 0.003, 0.05, 0.01, m_hot)
        for k in range(3):
            box(f"bu_label{k}", 0.1, -0.15 + k * 0.15, 0.12 + Hc + 0.004, 0.7 - k * 0.15, 0.04, 0.008, m_core, 0)
        for sgn in (-1, 1):
            for k in range(8):
                pin = box(f"bu_pin{sgn}{k}", -L / 2 + 0.15 + k * 0.143, sgn * (Wc / 2 + 0.06), 0.1, 0.06, 0.14, 0.03, m_hot, 0.005)
                box(f"bu_leg{sgn}{k}", -L / 2 + 0.15 + k * 0.143, sgn * (Wc / 2 + 0.12), 0.05, 0.06, 0.03, 0.1, m_hot, 0.005)
    turned(built(chip), TURN)

    def arr():
        prism("bu_arrow", arrow, -0.08, 0.08, m_glass)
        outline_curve("bu_arrow_edge", [(x, -0.084, z) for x, z in arrow], 0.012, m_hot)
        outline_curve("bu_arrow_edge_b", [(x, 0.084, z) for x, z in arrow], 0.008, m_edge)
    moving(arr, TURN @ at(0, 0, 0.95), TURN @ at(0, 0, 0.38), sel)


def s_fixfonts(sel):
    """SY02 FixFonts: three glass type blocks in a row with glowing letters on their faces, the middle
    one askew; selected: it snapped into line"""
    S, Hb = 0.5, 0.7

    def block(name, letter):
        def fn():
            b = box(name, 0, 0, Hb / 2, S, S * 0.8, Hb, m_glass, 0.03)
            wire(b, name + "_wire")
            t = glow_text(name + "_letter", letter, 0, -S * 0.4 - 0.01, Hb * 0.55, 0.5, m_hot)
            t.location.x -= t.dimensions.x / 2
        return fn

    def base():
        p = box("ff_plate", 0, 0, 0.04, 2.0, 0.9, 0.08, m_glass, 0.03)
        wire(p, "ff_plate_wire", thickness=0.012)
    turned(built(base), TURN)
    for k, (x, ch) in enumerate(((-0.62, "A"), (0.62, "C"))):
        turned(built(block(f"ff_block{k}", ch)), TURN @ at(x, 0, 0.08))
    straight = TURN @ at(0, 0, 0.08)
    askew = TURN @ at(0.06, -0.14, 0.08) @ rot("Z", 22) @ at(0, 0, 0.12) @ rot("Y", 9)
    moving(block("ff_block_mid", "B"), askew, straight, sel)


# --- batch U3 (SY03-SY09) ------------------------------------------------------------------------

def rr_pts(w, h, r, steps=6):
    """a rounded rectangle (x, z) around the origin"""
    pts = []
    for cx, cz, a0 in ((w / 2 - r, -h / 2 + r, -90), (w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180)):
        for i in range(steps + 1):
            q = math.radians(a0 + 90 * i / steps)
            pts.append((cx + r * math.cos(q), cz + r * math.sin(q)))
    return pts


def glow_text_flat(name, text, x, y, z, size, mat, font=None):
    """glowing letters lying face up at height z, centred on x, y"""
    bpy.ops.object.text_add(location=(0, 0, 0))
    tx = bpy.context.object
    tx.data.body = text
    if font:
        tx.data.font = bpy.data.fonts.load(font)
    tx.data.size = size
    tx.data.extrude = 0.004
    tx.data.align_x = "CENTER"
    tx.data.align_y = "CENTER"
    bpy.ops.object.convert(target="MESH")
    tx = bpy.context.object
    tx.name = name
    tx.location = (x, y, z)
    return register(tx, mat)


def s_formatcdrw(sel):
    """SY03 FormatCDRW: a hollow glass drive (Format's family), a disc on its tray out in front;
    selected: the tray slid in"""
    W, D, H = 1.9, 1.5, 0.5
    zs = H * 0.5
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, H / 2))
    drv = bpy.context.object
    drv.name = "cdrw_drive"
    drv.scale = (W, D, H)
    bpy.ops.object.transform_apply(scale=True)
    shell_part(drv, 0.04)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -D / 2, zs))
    cut = bpy.context.object
    cut.name = "cdrw_slot_cutter"
    cut.scale = (1.45, 0.3, 0.1)
    bpy.ops.object.transform_apply(scale=True)
    cut.hide_render = True
    b = drv.modifiers.new("slot", "BOOLEAN")
    b.operation = "DIFFERENCE"
    b.object = cut
    for f in drv.data.polygons:
        f.use_smooth = True
    register(drv, m_glass)
    wire(drv, "cdrw_drive_wire")
    yf = -D / 2 - 0.006
    outline_curve("cdrw_slot", [(-0.72, yf, zs - 0.05), (0.72, yf, zs - 0.05), (0.72, yf, zs + 0.05), (-0.72, yf, zs + 0.05)],
                  0.008, m_hot)
    cylinder("cdrw_led", 0.78, yf - 0.005, 0.12, 0.04, 0.03, m_hot, axis="Y")
    box("cdrw_eject", 0.75, yf - 0.01, H * 0.8, 0.14, 0.03, 0.05, m_core, 0.01)

    def tray():
        t = box("cdrw_tray", 0, 0, 0, 1.36, 1.4, 0.05, glass_material("cdrw_tray_g", ICE, 0.08), 0.01)
        wire(t, "cdrw_tray_wire", m_edge, 0.008)
        cylinder("cdrw_disc", 0, -0.05, 0.035, 0.56, 0.02, glass_material("cdrw_disc_g", ICE, 0.03))
        for k, (r, mt) in enumerate(((0.55, m_edge), (0.38, m_core), (0.2, m_core))):
            torus(f"cdrw_ring{k}", 0, -0.05, 0.048, r, 0.008, mt)
        cylinder("cdrw_hub", 0, -0.05, 0.055, 0.07, 0.03, m_hot)
    moving(tray, at(0, -D / 2 - 0.5, zs), at(0, -D / 2 + 0.68, zs), sel)       # out: still in the slot


def s_grimreaper(sel):
    """SY04 GrimReaper (it catches crashing programs): the Amiga's Guru Meditation alert as a black glass
    panel on a stand (the user's choice, 2026-11-16), its frame and two lines of text in the base colour;
    normal: the frame dark; selected: the frame blinked on (lit), like the real alert"""
    W, H, T, z0 = 2.0, 0.78, 0.12, 0.32
    yf = -T / 2 - 0.006
    frame_mat = m_hot if sel else lacquer_material("guru_frame_off")

    def body():
        b = box("guru_base", 0, 0.05, 0.05, 1.1, 0.55, 0.1, m_glass, 0.04)
        wire(b, "guru_base_wire", thickness=0.012)
        box("guru_neck", 0, 0.05, 0.1 + (z0 - 0.1) / 2, 0.3, 0.1, z0 - 0.1, m_glass, 0.02)
        p = box("guru_panel", 0, 0, z0 + H / 2, W, T, H, glass_material("guru_black", srgb((8, 10, 15)), 0.04), 0.03)
        wire(p, "guru_panel_wire", m_edge, 0.01)
        i = 0.07
        fr = [(-W / 2 + i, yf, z0 + i), (W / 2 - i, yf, z0 + i), (W / 2 - i, yf, z0 + H - i), (-W / 2 + i, yf, z0 + H - i)]
        outline_curve("guru_frame", fr, 0.028, frame_mat)
        for k, (txt, z) in enumerate((("Software Failure.", z0 + H * 0.64), ("Guru Meditation #80000004", z0 + H * 0.34))):
            t = glow_text(f"guru_text{k}", txt, 0, yf - 0.004, z, 0.11, m_hot, MONO)
            t.location.x -= t.dimensions.x / 2
    turned(built(body), TURN)


def s_mounter(sel):
    """SY05 Mounter: a glass drive rack with two bays (the lower one holding a drive), a drive in front
    of the empty upper bay; selected: the drive slid into the bay (mounted)"""
    W, Hb, D = 1.4, 0.42, 1.3

    def drive_box(name):
        d = box(name, 0, 0, 0, W - 0.16, D - 0.1, Hb - 0.1, m_glass, 0.03)
        wire(d, name + "_wire", m_edge, 0.008)
        cylinder(name + "_led", (W - 0.16) / 2 - 0.12, -(D - 0.1) / 2 - 0.01, -0.08, 0.035, 0.02, m_hot, axis="Y")
        box(name + "_slot", -0.1, -(D - 0.1) / 2 - 0.006, 0.04, 0.7, 0.01, 0.03, m_core, 0)

    def rack():
        for k in range(2):
            bay = open_box(f"mnt_bay{k}", 0, 0, 0, W, Hb, D, m_glass, wall=0.03)
            turned([bay], at(0, 0, Hb / 2 + 0.05 + k * Hb) @ rot("X", 90))
            wire(bay, f"mnt_bay{k}_wire", m_edge, 0.01)
        b = box("mnt_feet", 0, 0, 0.025, W + 0.1, D + 0.05, 0.05, m_glass, 0.02)
        lower = built(lambda: drive_box("mnt_drive0"))
        turned(lower, at(0, 0.03, Hb / 2 + 0.05))
    turned(built(rack), TURN)
    zu = Hb / 2 + 0.05 + Hb
    moving(lambda: drive_box("mnt_drive1"), TURN @ at(0, -D - 0.25, zu), TURN @ at(0, 0.03, zu), sel)


def s_rexxmast(sel):
    """SY06 RexxMast: a glass crown (the master of ARexx) on a cushion; selected: the crown lifted and
    lit from within"""
    R, hc = 0.45, 0.3

    def cushion():
        c = box("rx_cushion", 0, 0, 0.16, 1.2, 1.2, 0.32, glass_material("rx_cushion_g", ICE, 0.2), 0.14)
        wire(c, "rx_cushion_wire", m_core, 0.008)
        for sgn in (-1, 1):
            for sgx in (-1, 1):
                sphere(f"rx_tassel{sgn}{sgx}", sgx * 0.6, sgn * 0.6, 0.16, 0.05, m_hot)
    turned(built(cushion), TURN)

    def crown():
        bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=R, depth=hc, location=(0, 0, hc / 2))
        band = bpy.context.object
        band.name = "rx_band"
        bpy.ops.object.shade_smooth()
        register(band, m_glass)
        cut_faces(band, lambda c: 0.01 < c.z < hc - 0.01)
        shell_part(band, 0.03)
        torus("rx_band_base", 0, 0, 0.01, R, 0.02, m_edge)
        torus("rx_band_top", 0, 0, hc, R, 0.014, m_edge)
        for k in range(6):
            ang = k * 60
            pt = prism(f"rx_point{k}", [(-0.13, hc - 0.01), (0.13, hc - 0.01), (0.0, hc + 0.32)], -0.015, 0.015, m_glass)
            e = outline_curve(f"rx_point{k}_edge", [(-0.13, -0.02, hc), (0.0, -0.02, hc + 0.32), (0.13, -0.02, hc)], 0.008,
                              m_hot, closed=False)
            jw = sphere(f"rx_jewel{k}", 0, 0, hc + 0.34, 0.045, m_hot)
            for o in (pt, e, jw):
                turned([o], rot("Z", ang) @ at(0, -R + 0.01, 0))
        for k in range(4):
            jw = sphere(f"rx_gem{k}", 0, 0, hc / 2, 0.05, m_hot)
            turned([jw], rot("Z", k * 90 + 30) @ at(0, -R - 0.02, 0))
    m0 = TURN @ at(0, 0, 0.3)
    m1 = TURN @ at(0, 0, 0.72)
    moving(crown, m0, m1, sel)
    if sel:                                         # lit from within
        inner = bpy.data.objects.new("rx_inner", bpy.data.lights.new("rx_inner", "POINT"))
        inner.data.energy = 25
        inner.data.shadow_soft_size = 0.25
        inner.data.color = LIGHTBLUE[:3]
        inner.location = TURN @ Vector((0, 0, 0.72 + hc * 0.6))
        bpy.context.collection.objects.link(inner)


def s_ringhio(sel):
    """SY07 RinghioServer: the widescreen glass monitor of PF35 showing the Workbench (the user,
    2026-11-16), a notification balloon at the top right of the screen; selected: two notifications"""
    W, H, z0, i = WB_W, WB_H, WB_Z0, WB_I
    xl, xr, zt = -W / 2 + i, W / 2 - i, z0 + H - i
    nw, nh, nr = 0.6, 0.2, 0.05

    def note(name, z, y, lit):
        pts = [(x + xr - 0.16 - nw / 2, zz + z) for x, zz in rr_pts(nw, nh, nr)]
        prism(name, pts, y - 0.012, y + 0.008, glass_material(name + "_g", ICE, 0.06))
        outline_curve(name + "_edge", [(x, y - 0.016, zz) for x, zz in pts], 0.006, m_hot if lit else m_edge)
        xc = xr - 0.16 - nw / 2
        torus(name + "_icon", xc - nw / 2 + 0.08, y - 0.018, z, 0.035, 0.008, m_hot, axis="Y")
        box(name + "_l0", xc + 0.05, y - 0.018, z + 0.035, 0.36, 0.006, 0.02, m_hot if lit else m_core, 0)
        box(name + "_l1", xc + 0.0, y - 0.018, z - 0.035, 0.26, 0.006, 0.016, m_core, 0)

    def art(yf, W_, H_, z0_):
        y = yf - 0.006
        wb_desktop(y, xl, xr, zt)
        note("rg_note0", zt - 0.2, y - 0.03, False)
        if sel:                                     # a second notification below the first
            note("rg_note1", zt - 0.45, y - 0.03, True)

    def body():
        monitor("rg_mon", art, W=W, H=H, z0=z0)
    turned(built(body), TURN)


def s_typemanager(sel):
    """SY08 TypeManager: a slanted glass type case divided into compartments, letter blocks in them with
    glowing letters on top; selected: one letter block lifted out"""
    W, D, Hc = 1.8, 1.3, 0.16
    cols, rows = 5, 4
    C = TURN @ at(0, 0, 0.3) @ rot("X", 28)        # the case, its front edge low: tilted towards the viewer
    letters = "aBcDeFgHiJkLmNoPqRsT"
    pick = (1, 2)

    def cell(c, r):
        return Vector((-W / 2 + (c + 0.5) * W / cols, -D / 2 + (r + 0.5) * D / rows, 0))

    def block(name, ch, lit):
        def fn():
            b = box(name, 0, 0, 0.08, 0.2, 0.2, 0.16, m_glass, 0.02)
            wire(b, name + "_wire", m_hot if lit else m_core, 0.006)
            glow_text_flat(name + "_ch", ch, 0, 0, 0.165, 0.16, m_hot if lit else m_edge)
        return fn

    def case():
        t = open_box("tc_case", 0, 0, Hc / 2, W, D, Hc, m_glass, wall=0.03)
        wire(t, "tc_case_wire")
        for c in range(1, cols):
            box(f"tc_wall_c{c}", -W / 2 + c * W / cols, 0, Hc / 2, 0.02, D - 0.04, Hc - 0.02, m_glass, 0)
        for r in range(1, rows):
            box(f"tc_wall_r{r}", 0, -D / 2 + r * D / rows, Hc / 2, W - 0.04, 0.02, Hc - 0.02, m_glass, 0)
        for c in range(cols):
            for r in range(rows):
                if (c, r) == pick or (c * 7 + r * 3) % 5 == 0:
                    continue
                p = cell(c, r)
                turned(built(block(f"tc_b{c}{r}", letters[(c + r * cols) % len(letters)], False)), at(p.x, p.y, 0.02))
    turned(built(case), C)
        
    def stand():
        s = box("tc_stand", 0, 0.45, 0.25, W - 0.2, 0.15, 0.5, m_glass, 0.03)
        wire(s, "tc_stand_wire", m_core, 0.008)
    turned(built(stand), TURN)
    p = cell(*pick)
    moving(block("tc_pick", "A", True), C @ at(p.x, p.y, 0.02), C @ at(p.x, p.y, 0.55), sel)


def s_mediatoolbox(sel):
    """SY09 Media Toolbox (a device and partition manager, the user: the icon must show a drive being
    worked on): a glass hard drive with its partition map on top (three partitions) and a glass wrench
    gripping the nut on the boundary of the first; selected: the wrench pushed that boundary on, the
    first partition grown"""
    W, D, H = 2.0, 1.4, 0.55
    ys, x0, x2, x3 = -0.2, -0.85, 0.4, 0.85        # the partition bar: from x0, last boundary at x2, end x3
    xd0, xd1 = -0.45, 0.15                         # the moved boundary: normal, selected
    xd = xd1 if sel else xd0

    def flat_prism(name, pts, mat, t=0.04):
        o = prism(name, pts, -t, 0.0, mat)
        turned([o], rot("X", -90))
        return o

    def body():
        b = box("mt_drive", 0, 0, H / 2, W, D, H, m_glass, 0.06)
        wire(b, "mt_drive_wire")
        cylinder("mt_platter", 0.35, 0.2, H * 0.45, 0.42, 0.025, glass_material("mt_platter_g", ICE, 0.05))
        torus("mt_platter_ring", 0.35, 0.2, H * 0.45, 0.42, 0.014, m_edge)
        cylinder("mt_hub", 0.35, 0.2, H * 0.45, 0.07, 0.05, m_hot)
        box("mt_slot", -0.3, -D / 2 - 0.005, H * 0.58, 0.9, 0.02, 0.05, m_hot, 0)
        cylinder("mt_led", 0.75, -D / 2 - 0.01, H * 0.58, 0.05, 0.03, m_hot, axis="Y")
        # the partition map on top: three partitions, the first one's end at xd
        zt = H + 0.006
        for k, (a0, a1, mt) in enumerate(((x0, xd, m_hot), (xd, x2, m_core), (x2, x3, m_edge))):
            box(f"mt_part{k}", (a0 + a1) / 2, ys, zt, a1 - a0 - 0.03, 0.3, 0.012, mt, 0.004)
        outline_curve("mt_map", [(x0 - 0.03, ys - 0.18, zt + 0.004), (x3 + 0.03, ys - 0.18, zt + 0.004),
                                 (x3 + 0.03, ys + 0.18, zt + 0.004), (x0 - 0.03, ys + 0.18, zt + 0.004)], 0.008, m_edge)
    turned(built(body), TURN)

    def tool():
        nut = cylinder("mt_nut", 0, 0, 0.06, 0.085, 0.1, m_glass, verts=6)
        torus("mt_nut_rim", 0, 0, 0.11, 0.08, 0.008, m_hot)
        outer = [(0.22 * math.cos(math.radians(q)), 0.22 * math.sin(math.radians(q))) for q in range(-150, 151, 15)]
        inner = [(0.105 * math.cos(math.radians(q)), 0.105 * math.sin(math.radians(q))) for q in range(150, -151, -15)]
        jaw = outer + inner
        handle = [(0.2, -0.075), (1.25, -0.075), (1.25, 0.075), (0.2, 0.075)]
        parts = [flat_prism("mt_jaw", jaw, m_glass, 0.06), flat_prism("mt_handle", handle, m_glass, 0.06)]
        parts.append(outline_curve("mt_jaw_edge", [(x, y, 0.065) for x, y in jaw], 0.012, m_hot))
        parts.append(outline_curve("mt_handle_edge", [(x, y, 0.065) for x, y in handle], 0.012, m_hot))
        parts.append(box("mt_handle_core", 0.72, 0, 0.066, 0.95, 0.03, 0.01, m_core, 0))
        turned(parts, at(0, 0, 0.06) @ rot("Z", 35))
        box("mt_divider", 0, 0, 0.012, 0.03, 0.34, 0.016, m_hot, 0)
    m0 = TURN @ at(xd0, ys, H)
    m1 = TURN @ at(xd1, ys, H)
    moving(tool, m0, m1, sel)


PROGRAMS.update({"filecompare": u_filecompare, "graphicdump": u_graphicdump, "initprinter": u_initprinter,
                 "installer": u_installer, "keyshow": u_keyshow, "logviewer": u_logviewer, "memacs": u_memacs,
                 "partitionwizard": u_partitionwizard, "playcd": u_playcd, "prefsobjects": u_prefsobjects,
                 "printfiles": u_printfiles, "rawdisk": u_rawdisk, "showconfig": u_showconfig,
                 "usbinspector": u_usbinspector, "biosupdater": s_biosupdater, "fixfonts": s_fixfonts,
                 "formatcdrw": s_formatcdrw, "grimreaper": s_grimreaper, "mounter": s_mounter, "rexxmast": s_rexxmast,
                 "ringhio": s_ringhio, "typemanager": s_typemanager, "mediatoolbox": s_mediatoolbox})
