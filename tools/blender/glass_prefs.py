"""glass_prefs.py: the Prefs editors of the glass icon set (group 4), loaded by glass_icons.py after
glass_programs.py, into the same namespace (materials, box, wire, moving, turned, ...).

Each editor is a glass object of its own with one moving part (its selected image); the icon gets the
blue gear emblem lower right, so the moving parts keep clear of that corner. Public domain.
"""
import math

import bpy
from mathutils import Matrix, Vector


def slab(name, verts, mat, bevel=0.02):
    """a closed mesh from 8 corner points (a box that may be skewed): bottom 0-3, top 4-7"""
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    o = mesh_obj(name, verts, faces, mat)
    if bevel:
        m = o.modifiers.new("bevel", "BEVEL")
        m.width = bevel
        m.segments = 3
        m.limit_method = "NONE"
    for f in o.data.polygons:
        f.use_smooth = True
    return o


def window(name, W, H, z0, T=0.12, title=True):
    """a glass window panel standing on z0 (x -W/2..W/2): title bar with close and depth gadgets.
    Returns the y of its front surface"""
    p = box(name, 0, 0, z0 + H / 2, W, T, H, m_glass, 0.03)
    wire(p, name + "_wire")
    yf = -T / 2 - 0.006
    if title:
        tb = 0.2
        zt = z0 + H - tb / 2 - 0.04
        outline_curve(name + "_title", [(-W / 2 + 0.05, yf, zt - tb / 2), (W / 2 - 0.05, yf, zt - tb / 2)], 0.007,
                      m_core, closed=False)
        for k, x in enumerate((-W / 2 + 0.14, W / 2 - 0.14)):
            q = 0.06
            outline_curve(f"{name}_gad{k}", [(x - q, yf, zt - q), (x + q, yf, zt - q), (x + q, yf, zt + q),
                                             (x - q, yf, zt + q)], 0.007, m_edge)
        box(name + "_titlebar", 0, yf, zt, W - 0.5, 0.01, 0.04, m_core, 0)
    return yf


def p_ahi(sel):
    """PF01 AHI: a glass audio mixer, sloping top, three faders, knobs and level meters; selected: the
    left fader slides up"""
    W, D, h0, h1 = 1.9, 1.3, 0.22, 0.62
    a = math.atan2(h1 - h0, D)

    def top(y):
        return h0 + (y + D / 2) / D * (h1 - h0)

    def on_top(x, y, lift=0.0):
        return at(x, y, top(y) + lift) @ rot("X", math.degrees(a))

    def body():
        v = [(-W / 2, -D / 2, 0), (W / 2, -D / 2, 0), (W / 2, D / 2, 0), (-W / 2, D / 2, 0),
             (-W / 2, -D / 2, h0), (W / 2, -D / 2, h0), (W / 2, D / 2, h1), (-W / 2, D / 2, h1)]
        o = slab("mixer", v, m_glass)
        wire(o, "mixer_wire")
        for k, x in enumerate((-0.6, -0.25, 0.1)):
            tr = box(f"track{k}", 0, 0, 0, 0.03, 0.85, 0.01, m_core, 0)
            turned([tr], on_top(x, -0.12, 0.006))
        for k, x in enumerate((-0.25, 0.1)):
            kn = box(f"fader{k}", 0, 0, 0, 0.2, 0.12, 0.09, m_glass, 0.02)
            wire(kn, f"fader{k}_wire", m_edge, 0.008)
            turned([kn, objects[-1]], on_top(x, -0.3 + k * 0.25, 0.05))
        for k in range(3):
            c = cylinder(f"knob{k}", 0, 0, 0.05, 0.08, 0.1, m_glass)
            r = torus(f"knob{k}_rim", 0, 0, 0.1, 0.08, 0.01, m_edge)
            turned([c, r], on_top(0.45 + (k % 2) * 0.28, -0.25 + k * 0.28))
        for k in range(5):                            # level meters on the top, at the back
            ln = 0.12 + 0.06 * (k % 3)
            lv = box(f"meter{k}", 0, ln / 2, 0, 0.05, ln, 0.01, m_hot if k < 3 else m_core, 0)
            turned([lv], on_top(-0.8 + k * 0.1, 0.38, 0.006))

    def fader():
        kn = box("fader_l", 0, 0, 0, 0.2, 0.12, 0.09, m_glass, 0.02)
        wire(kn, "fader_l_wire", m_hot, 0.009)
    turned(built(body), TURN)
    moving(fader, TURN @ on_top(-0.6, -0.45, 0.05), TURN @ on_top(-0.6, 0.22, 0.05), sel)


def p_amigainput(sel):
    """PF02 AmigaInput: a glass joystick, a fire button; selected: the stick tilted"""
    def body():
        b = box("joy_base", 0, 0, 0.18, 1.3, 1.3, 0.36, m_glass, 0.12)
        wire(b, "joy_base_wire")
        torus("joy_gaiter", 0, 0, 0.37, 0.2, 0.03, m_glass)
        torus("joy_gaiter_glow", 0, 0, 0.385, 0.2, 0.012, m_edge)
        cylinder("joy_fire", -0.4, 0.35, 0.39, 0.12, 0.07, m_hot)
        torus("joy_fire_rim", -0.4, 0.35, 0.36, 0.14, 0.012, m_edge)

    def stick():
        cylinder("joy_stick", 0, 0, 0.5, 0.075, 1.0, m_glass)
        cylinder("joy_stick_core", 0, 0, 0.5, 0.02, 0.95, m_core, verts=16)
        sphere("joy_ball", 0, 0, 1.05, 0.21, m_glass)
        sphere("joy_ball_core", 0, 0, 1.05, 0.08, m_hot)
    turned(built(body), TURN)
    pivot = TURN @ at(0, 0, 0.36)
    moving(stick, pivot, pivot @ rot("Y", 13), sel)            # to the right, half the first tilt (user)


def p_asl(sel):
    """PF03 ASL: a requester window with a file list and OK / Cancel; selected: the selection bar moved
    down a row"""
    W, H, z0 = 1.6, 1.75, 0.08
    rows = [z0 + H - 0.42 - k * 0.2 for k in range(5)]

    def body():
        yf = window("asl", W, H, z0)
        outline_curve("asl_list", [(-W / 2 + 0.12, yf, rows[-1] - 0.13), (W / 2 - 0.12, yf, rows[-1] - 0.13),
                                   (W / 2 - 0.12, yf, rows[0] + 0.13), (-W / 2 + 0.12, yf, rows[0] + 0.13)], 0.007, m_edge)
        for k, z in enumerate(rows):
            box(f"asl_row{k}", -0.05 if k % 2 else 0.05, yf, z, 0.9 if k % 2 else 1.05, 0.01, 0.04, m_core, 0)
            box(f"asl_dr{k}", -W / 2 + 0.25, yf, z, 0.08, 0.01, 0.07, m_edge, 0)
        for k, x in enumerate((-0.42, 0.42)):
            bt = box(f"asl_button{k}", x, yf - 0.03, z0 + 0.2, 0.55, 0.06, 0.18, m_glass, 0.02)
            wire(bt, f"asl_button{k}_wire", m_hot if k == 0 else m_edge, 0.008)
    turned(built(body), TURN)

    def bar():
        b = box("asl_sel", 0, 0, 0, W - 0.32, 0.03, 0.17, glass_material("asl_sel_g", ICE, 0.05), 0.01)
        wire(b, "asl_sel_wire", m_hot, 0.008)
    yb = -0.06 - 0.03
    moving(bar, TURN @ at(0, yb, rows[1]), TURN @ at(0, yb, rows[2]), sel)


def p_compatibility(sel):
    """PF04 Compatibility: two glass puzzle pieces, the old (dim edges) and the new; selected: slid
    together"""
    S, r, t = 0.85, 0.2, 0.18

    def arc(cx, cz, a0, a1, step):
        return [(cx + r * math.cos(math.radians(a)), cz + r * math.sin(math.radians(a))) for a in range(a0, a1 + step if step > 0 else a1 + step, step)]
    knob = [(0, 0), (S, 0)] + arc(S + 0.6 * r, S / 2, -135, 135, 15) + [(S, S), (0, S)]
    hole = [(0, 0), (S, 0), (S, S), (0, S)] + arc(0.6 * r, S / 2, 135, -135, -15)
    z0 = 0.1

    def old():
        pr = prism("piece_old", [(x - S, z + z0) for x, z in knob], -t / 2, t / 2, m_glass)
        outline_curve("piece_old_edge", [(x - S, -t / 2 - 0.004, z + z0) for x, z in knob], 0.009, m_core)
        outline_curve("piece_old_edge_b", [(x - S, t / 2 + 0.004, z + z0) for x, z in knob], 0.007, m_core)
        box("piece_old_chip", -S / 2, -t / 2 - 0.006, S / 2 + z0, 0.3, 0.01, 0.3, m_core, 0)
        return pr

    def new():
        prism("piece_new", [(x, z + z0) for x, z in hole], -t / 2, t / 2, m_glass)
        outline_curve("piece_new_edge", [(x, -t / 2 - 0.004, z + z0) for x, z in hole], 0.009, m_hot)
        outline_curve("piece_new_edge_b", [(x, t / 2 + 0.004, z + z0) for x, z in hole], 0.007, m_edge)
    turned(built(old), TURN @ at(-0.2, 0, 0))
    moving(new, TURN @ at(0.25, 0, 0), TURN @ at(-0.2, 0, 0), sel)


def glow_text(name, text, x, y, z, size, mat, font=None):
    """glowing letters standing on the plane y (facing the viewer), left edge at x, centred on z;
    returns the object (its width: dimensions.x)"""
    bpy.ops.object.text_add(location=(0, 0, 0))
    tx = bpy.context.object
    tx.data.body = text
    if font:
        tx.data.font = bpy.data.fonts.load(font)
    tx.data.size = size
    tx.data.extrude = 0.006
    tx.data.align_y = "CENTER"
    bpy.ops.object.convert(target="MESH")
    tx = bpy.context.object
    tx.name = name
    tx.rotation_euler = (math.pi / 2, 0, 0)
    tx.location = (x, y, z)
    bpy.context.view_layer.update()
    return register(tx, mat)


MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"


def p_console(sel):
    """PF05 Console: a small glass window with a prompt and a size gadget; selected: the command LIST
    typed at the prompt, about to be sent (the window stays as it is)"""
    T, W, H = 0.12, 1.2, 0.95
    x0, z0 = -0.6, 0.08
    yf = -T / 2 - 0.006

    def body():
        p = box("con", x0 + W / 2, 0, z0 + H / 2, W, T, H, m_glass, 0.03)
        wire(p, "con_wire")
        zt = z0 + H - 0.14
        box("con_title", x0 + W / 2, yf, zt - 0.08, W - 0.1, 0.01, 0.012, m_core, 0)
        q = 0.05
        outline_curve("con_close", [(x0 + 0.1, yf, zt - q), (x0 + 0.2, yf, zt - q), (x0 + 0.2, yf, zt + q),
                                    (x0 + 0.1, yf, zt + q)], 0.007, m_edge)
        zp = zt - 0.27
        line("con_prompt", [(x0 + 0.15, yf, zp + 0.07), (x0 + 0.24, yf, zp), (x0 + 0.15, yf, zp - 0.07)])
        xc = x0 + 0.33
        if sel:
            cmd = glow_text("con_list", "LIST", xc, yf, zp, 0.17, m_hot, MONO)
            xc += cmd.dimensions.x + 0.04
        box("con_cursor", xc + 0.05, yf, zp, 0.1, 0.012, 0.12, m_hot, 0)
        xr, zb = x0 + W - 0.07, z0 + 0.07
        line("con_size", [(xr - 0.16, yf, zb), (xr, yf, zb), (xr, yf, zb + 0.16), (xr - 0.16, yf, zb)], m_hot, 0.012)
    turned(built(body), TURN)


def p_deficons(sel):
    """PF06 DefIcons: a glass card index (open tray) with tabbed cards; selected: one card popped up"""
    W, D, H = 1.5, 1.3, 0.55
    cards = [-0.42, -0.25, -0.08, 0.09, 0.26, 0.43]
    tabs = [-0.45, -0.15, 0.15, 0.45, -0.3, 0.0]

    def body():
        tr = open_box("tray", 0, 0, H / 2, W, D, H, m_glass, wall=0.04)
        wire(tr, "tray_wire")
        box("tray_label", 0, -D / 2 - 0.006, H * 0.55, 0.45, 0.01, 0.12, m_core, 0)
        for k, y in enumerate(cards):
            if k == 2:
                continue
            card(k, 0, y, 0)

    def card(k, x, y, z):
        c = box(f"card{k}", x, y, z + 0.5, W - 0.14, 0.03, 0.9, glass_material(f"card{k}g", ICE, 0.08), 0.01)
        wire(c, f"card{k}_wire", m_edge if k != 2 else m_hot, 0.006)
        t = box(f"card{k}_tab", x + tabs[k], y, z + 1.0, 0.28, 0.03, 0.12, m_glass, 0.01)
        wire(t, f"card{k}_tab_wire", m_core if k != 2 else m_hot, 0.006)
    turned(built(body), TURN)
    moving(lambda: card(2, 0, 0, 0), TURN @ at(0, cards[2], 0), TURN @ at(0, cards[2], 0.5), sel)


def p_dos(sel):
    """PF07 DOS: a glass disk platter with a read/write arm under a clear glass cover; selected: the arm
    swung over the platter"""
    px, py, za = 0.7, 0.55, 0.36

    def body():
        b = box("dos_base", 0, 0, 0.07, 1.9, 1.6, 0.14, m_glass, 0.05)
        wire(b, "dos_base_wire")
        cylinder("platter", -0.2, 0.05, 0.22, 0.62, 0.03, glass_material("platter_g", ICE, 0.04))
        for k, (rr, mat) in enumerate(((0.62, m_edge), (0.45, m_core), (0.3, m_core))):
            torus(f"platter_ring{k}", -0.2, 0.05, 0.24, rr, 0.01, mat)
        cylinder("spindle", -0.2, 0.05, 0.26, 0.08, 0.08, m_hot)
        cylinder("arm_pivot", px, py, 0.25, 0.1, 0.24, m_glass)
        torus("arm_pivot_rim", px, py, 0.37, 0.1, 0.012, m_edge)
        # a clear glass cover over the drive (user): sides and top, open underneath
        cv = open_box("dos_cover", 0, 0, 0, 1.84, 1.54, 0.36, m_glass, wall=0.03)
        turned([cv], at(0, 0, 0.14 + 0.18) @ rot("X", 180))
        wire(cv, "dos_cover_wire", thickness=0.012)

    def arm():
        a = box("arm", 0.47, 0, 0, 0.95, 0.09, 0.035, m_glass, 0.01)
        wire(a, "arm_wire", m_edge, 0.008)
        box("arm_head", 0.95, 0, -0.04, 0.1, 0.08, 0.05, m_hot, 0.01)
    turned(built(body), Matrix.Identity(4))
    piv = at(px, py, za)
    moving(arm, piv @ rot("Z", -90), piv @ rot("Z", -151), sel)


def p_font(sel):
    """PF08 Font: a glass type block with a raised glowing A on its face, on a glass plate; selected:
    the block lifted straight up"""
    S, Hb = 0.95, 1.25

    def plate():
        p = box("font_plate", 0, 0, 0.04, 1.8, 1.4, 0.08, m_glass, 0.03)
        wire(p, "font_plate_wire", thickness=0.012)
    turned(built(plate), TURN)

    def block():
        b = box("type_block", 0, 0, Hb / 2, S, S * 0.8, Hb, m_glass, 0.04)
        wire(b, "type_block_wire")
        bpy.ops.object.text_add(location=(0, 0, 0))
        tx = bpy.context.object
        tx.data.body = "A"
        tx.data.extrude = 0.03
        tx.data.size = 0.95
        tx.data.align_x = "CENTER"
        tx.data.align_y = "CENTER"
        bpy.ops.object.convert(target="MESH")
        tx = bpy.context.object
        tx.name = "type_A"
        tx.rotation_euler = (math.pi / 2, 0, 0)
        tx.location = (0, -S * 0.4 - 0.03, Hb * 0.55)
        register(tx, m_hot)
        box("type_nick", 0, -S * 0.4 - 0.006, 0.18, S * 0.6, 0.01, 0.03, m_core, 0)
    base = TURN @ at(0, 0, 0.08)
    moving(block, base, base @ at(0, 0, 0.45), sel)                    # straight up, no tilt (user)


def p_gui(sel):
    """PF09 GUI: a glass window with a slider and a checkbox; selected: the slider knob slid across"""
    W, H, z0 = 1.75, 1.45, 0.08
    zs = z0 + H - 0.55

    def body():
        yf = window("gui", W, H, z0)
        box("gui_track", 0, yf, zs, W - 0.4, 0.012, 0.03, m_core, 0)
        zc = zs - 0.38
        q = 0.09
        outline_curve("gui_check", [(-W / 2 + 0.25 - q, yf, zc - q), (-W / 2 + 0.25 + q, yf, zc - q),
                                    (-W / 2 + 0.25 + q, yf, zc + q), (-W / 2 + 0.25 - q, yf, zc + q)], 0.008, m_edge)
        line("gui_tick", [(-W / 2 + 0.19, yf, zc), (-W / 2 + 0.24, yf, zc - 0.05), (-W / 2 + 0.33, yf, zc + 0.07)], m_hot, 0.014)
        box("gui_label", -0.05, yf, zc, 0.7, 0.01, 0.04, m_core, 0)
    turned(built(body), TURN)

    def knob():
        k = box("gui_knob", 0, 0, 0, 0.16, 0.07, 0.22, m_glass, 0.02)
        wire(k, "gui_knob_wire", m_hot, 0.009)
    yk = -0.06 - 0.035
    moving(knob, TURN @ at(-W / 2 + 0.35, yk, zs), TURN @ at(W / 2 - 0.35, yk, zs), sel)


PROGRAMS.update({"ahi": p_ahi, "amigainput": p_amigainput, "asl": p_asl, "compatibility": p_compatibility,
                 "console": p_console, "deficons": p_deficons, "dos": p_dos, "fontprefs": p_font, "gui": p_gui})


# --- batch 2 (PF10-PF18) -------------------------------------------------------------------------

def p_input(sel):
    """PF10 Input: a glass two-button mouse, its cable leaving at the back; selected: the left button
    clicked down"""
    W, D, H = 0.95, 1.4, 0.36

    def body():
        b = box("mouse", 0, 0, H / 2, W, D, H, m_glass, 0.07)
        wire(b, "mouse_wire")
        rb = box("mouse_btn_r", 0.235, 0.33, H + 0.03, 0.4, 0.6, 0.06, m_glass, 0.03)
        wire(rb, "mouse_btn_r_wire", m_edge, 0.008)
        box("mouse_split", 0, 0.33, H + 0.035, 0.02, 0.6, 0.05, m_core, 0)
        outline_curve("mouse_cable", cable, 0.035, m_edge, closed=False)
    cable = [(0, D / 2, H * 0.5), (0, D / 2 + 0.18, H * 0.42), (-0.12, D / 2 + 0.34, 0.12), (-0.38, D / 2 + 0.42, 0.04)]
    turned(built(body), TURN)
    FRAME_EXTRA.extend(TURN @ Vector(p) for p in cable)          # (curves are not measured by the framing)

    def left():
        lb = box("mouse_btn_l", 0, 0, 0, 0.4, 0.6, 0.06, m_glass, 0.03)
        wire(lb, "mouse_btn_l_wire", m_hot, 0.009)
    up = at(-0.235, 0.33, H + 0.03)
    moving(left, TURN @ up, TURN @ at(0, 0, -0.045) @ up @ rot("X", -4), sel)


def p_internet(sel):
    """PF11 Internet: a glass antenna mast on a base, signal rings round its tip; selected: the
    antenna telescoped up"""
    def body():
        b = box("mast_base", 0, 0, 0.12, 1.0, 1.0, 0.24, m_glass, 0.08)
        wire(b, "mast_base_wire")
        cylinder("mast0", 0, 0, 0.24 + 0.4, 0.11, 0.8, m_glass)
        torus("mast0_rim", 0, 0, 1.04, 0.11, 0.014, m_edge)
        cylinder("mast0_core", 0, 0, 0.64, 0.02, 0.78, m_core, verts=16)
        box("mast_led", 0, -0.5, 0.15, 0.2, 0.02, 0.05, m_hot, 0)

    def top():
        cylinder("mast1", 0, 0, -0.35, 0.075, 0.8, m_glass)
        torus("mast1_rim", 0, 0, 0.05, 0.075, 0.012, m_edge)
        cylinder("mast2", 0, 0, 0.3, 0.045, 0.6, m_glass)
        cylinder("mast2_core", 0, 0, 0.0, 0.016, 1.3, m_core, verts=16)
        sphere("mast_tip", 0, 0, 0.62, 0.09, m_hot)
        for k, r in enumerate((0.26, 0.42)):
            torus(f"signal{k}", 0, 0, 0.62, r, 0.012, m_core if k else m_edge)
    turned(built(body), TURN)
    moving(top, TURN @ at(0, 0, 1.04), TURN @ at(0, 0, 1.6), sel)


def p_locale(sel):
    """PF12 Locale: a glass flag on a pole, a glowing ring on it; selected: the flag raised to the top"""
    def body():
        cylinder("pole_base", -0.45, 0, 0.06, 0.4, 0.12, m_glass)
        torus("pole_base_rim", -0.45, 0, 0.12, 0.4, 0.012, m_edge)
        cylinder("pole", -0.45, 0, 1.08, 0.045, 1.95, m_glass)
        cylinder("pole_core", -0.45, 0, 1.08, 0.014, 1.9, m_core, verts=16)
        sphere("pole_knob", -0.45, 0, 2.08, 0.08, m_hot)

    def flag():
        nx, nz = 16, 6
        L, Hf = 1.05, 0.62
        verts = [(i / nx * L, 0.07 * math.sin(i / nx * math.pi * 1.6) * (i / nx), j / nz * Hf)
                 for i in range(nx + 1) for j in range(nz + 1)]
        faces = [(i * (nz + 1) + j, (i + 1) * (nz + 1) + j, (i + 1) * (nz + 1) + j + 1, i * (nz + 1) + j + 1)
                 for i in range(nx) for j in range(nz)]
        f = mesh_obj("flag", verts, faces, m_glass)
        shell_part(f, 0.03)
        for p in f.data.polygons:
            p.use_smooth = True
        edge = [verts[i * (nz + 1)] for i in range(nx + 1)] + [verts[nx * (nz + 1) + j] for j in range(nz + 1)] + \
            [verts[i * (nz + 1) + nz] for i in range(nx, -1, -1)]
        outline_curve("flag_edge", [(x, y - 0.02, z) for x, y, z in edge], 0.01, m_edge, closed=True)
        torus("flag_ring", L * 0.5, -0.06, Hf / 2, 0.15, 0.022, m_hot, axis="Y")
    turned(built(body), TURN)
    moving(flag, TURN @ at(-0.41, 0, 0.75), TURN @ at(-0.41, 0, 1.42), sel)


def p_notifications(sel):
    """PF13 Notifications: a glass bell hanging from a bracket; selected: the bell swung, its clapper
    lagging behind"""
    pz = 1.72

    def body():
        b = box("bell_base", -0.2, 0, 0.07, 1.3, 0.8, 0.14, m_glass, 0.05)
        wire(b, "bell_base_wire")
        cylinder("bell_post", -0.7, 0, 0.14 + 0.85, 0.06, 1.7, m_glass)
        cylinder("bell_post_core", -0.7, 0, 0.99, 0.016, 1.6, m_core, verts=16)
        a = box("bell_arm", -0.3, 0, 1.86, 0.92, 0.12, 0.1, m_glass, 0.03)
        wire(a, "bell_arm_wire", m_edge, 0.01)
        cylinder("bell_hook", 0.05, 0, 1.78, 0.03, 0.14, m_hot)

    def bell():
        bpy.ops.mesh.primitive_cone_add(vertices=64, radius1=0.48, radius2=0.2, depth=0.62, location=(0, 0, -0.5))
        c = bpy.context.object
        c.name = "bell_body"
        bpy.ops.object.shade_smooth()
        register(c, m_glass)
        cut_faces(sphere("bell_top", 0, 0, -0.19, 0.2, m_glass), lambda v: v.z > -0.2)
        torus("bell_lip", 0, 0, -0.81, 0.48, 0.035, m_glass)
        torus("bell_lip_glow", 0, 0, -0.81, 0.49, 0.012, m_hot)
        torus("bell_band", 0, 0, -0.42, 0.36, 0.01, m_edge)

    def clapper():
        cylinder("clapper_rod", 0, 0, -0.45, 0.018, 0.5, m_edge, verts=12)
        sphere("clapper_ball", 0, 0, -0.78, 0.08, m_hot)
    turned(built(body), TURN)
    piv = TURN @ at(0.05, 0, pz)
    moving(bell, piv, piv @ rot("Y", 24), sel)
    moving(clapper, piv, piv @ rot("Y", 9), sel)


def p_palette(sel):
    """PF14 Palette: a glass painter's palette leaning back, glowing paint wells, a thumb hole, a brush;
    selected: the brush dipped into a well"""
    P = TURN @ at(0, 0, 0.03) @ rot("X", -40)        # leaning back like on an easel
    pts = []
    for k in range(48):
        a = k / 48 * 2 * math.pi
        r = 1.0 + 0.08 * math.cos(2 * a)
        pts.append((r * 1.05 * math.cos(a), 0.75 * r * math.sin(a) + 0.8))
    wells = [(-0.62, 1.15), (-0.25, 1.38), (0.18, 1.42), (0.58, 1.22), (0.78, 0.82)]
    mats = [m_hot, m_core, m_edge, emission_material("paint_white", srgb((240, 246, 255)), 2.4), m_core]

    def body():
        pal = prism("palette", pts, -0.04, 0.04, m_glass)
        hole = cylinder("thumb_cut", -0.55, 0, 0.55, 0.16, 0.3, None, axis="Y")
        b = pal.modifiers.new("hole", "BOOLEAN")
        b.operation = "DIFFERENCE"
        b.object = hole
        hole.hide_render = True
        objects.remove(hole)
        outline_curve("palette_edge", [(x, -0.044, z) for x, z in pts], 0.01, m_edge)
        torus("thumb_ring", -0.55, -0.044, 0.55, 0.16, 0.012, m_edge, axis="Y")
        for k, ((x, z), mt) in enumerate(zip(wells, mats)):
            cylinder(f"well{k}", x, -0.05, z, 0.13, 0.025, mt, axis="Y")
            torus(f"well{k}_rim", x, -0.06, z, 0.14, 0.01, m_glass, axis="Y")
        return hole
    objs = built(body)
    turned(objs + [bpy.data.objects["thumb_cut"]], P)

    def brush():
        bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.01, radius2=0.07, depth=0.25, location=(0, 0, 0.125))
        t = bpy.context.object
        t.name = "brush_tip"
        bpy.ops.object.shade_smooth()
        register(t, m_hot)
        cylinder("brush_ferrule", 0, 0, 0.33, 0.07, 0.16, m_glass)
        torus("brush_ring", 0, 0, 0.41, 0.07, 0.01, m_edge)
        cylinder("brush_handle", 0, 0, 0.95, 0.05, 1.1, m_glass)
        cylinder("brush_core", 0, 0, 0.95, 0.014, 1.05, m_core, verts=12)
    lie = at(-0.1, -0.12, 0.35) @ rot("Y", 68)
    dip = at(wells[2][0], -0.07, wells[2][1]) @ aim((0.35, -0.85, 0.35))
    moving(brush, P @ lie, P @ dip, sel)


def p_picasso96(sel):
    """PF15 Picasso96Mode: a glass graphics card standing on its edge (fan, chip, contacts, a bracket
    with a port); selected: a monitor plug pushed into the port"""
    L, Hc, t = 1.9, 0.85, 0.06

    def body():
        c = box("gfx_card", 0, 0, 0.2 + Hc / 2, L, t, Hc, m_glass, 0.02)
        wire(c, "gfx_card_wire", thickness=0.012)
        br = box("gfx_bracket", -L / 2 - 0.03, 0, 0.2 + Hc / 2 + 0.05, 0.05, 0.3, Hc + 0.25, glass_material("bracket", ICE, 0.1), 0.01)
        wire(br, "gfx_bracket_wire", m_edge, 0.008)
        q = 0.07
        outline_curve("gfx_port", [(-L / 2 - 0.06, -q * 1.6, 0.7 - q), (-L / 2 - 0.06, q * 1.6, 0.7 - q),
                                   (-L / 2 - 0.06, q * 1.6, 0.7 + q), (-L / 2 - 0.06, -q * 1.6, 0.7 + q)], 0.008, m_hot)
        yf = -t / 2
        cylinder("gfx_fan", 0.35, yf - 0.04, 0.2 + Hc / 2, 0.32, 0.08, m_glass, axis="Y")
        torus("gfx_fan_rim", 0.35, yf - 0.085, 0.2 + Hc / 2, 0.32, 0.012, m_edge, axis="Y")
        cylinder("gfx_fan_hub", 0.35, yf - 0.09, 0.2 + Hc / 2, 0.07, 0.02, m_hot, axis="Y")
        for k in range(7):
            bl = box(f"gfx_blade{k}", 0, 0, 0, 0.05, 0.01, 0.2, m_core, 0)
            turned([bl], at(0.35, yf - 0.088, 0.2 + Hc / 2) @ rot("Y", k * 360 / 7 + 15) @ at(0, 0, 0.16) @ rot("Y", 25))
        ch = box("gfx_chip", -0.4, yf - 0.025, 0.2 + Hc / 2, 0.36, 0.05, 0.36, lacquer_material("gfx_chip"), 0.01)
        wire(ch, "gfx_chip_wire", m_core, 0.007)
        for k in range(18):
            box(f"gfx_pin{k}", -0.55 + k * 0.065, yf - 0.006, 0.2 + 0.05, 0.035, 0.01, 0.09, m_hot, 0)
        box("gfx_slot", 0.05, 0, 0.1, L * 0.75, 0.3, 0.2, glass_material("slot", ICE, 0.15), 0.03)

    def plug():
        p = box("plug", -0.15, 0, 0, 0.3, 0.32, 0.2, m_glass, 0.03)
        wire(p, "plug_wire", m_edge, 0.009)
        box("plug_tip", 0.03, 0, 0, 0.06, 0.2, 0.12, m_hot, 0.01)
        outline_curve("plug_cable", [(-0.3, 0, 0), (-0.55, 0, -0.05), (-0.75, 0, -0.35), (-0.8, 0, -0.68)], 0.04,
                      m_edge, closed=False)
    turned(built(body), TURN)
    moving(plug, TURN @ at(-L / 2 - 0.5, 0, 0.7), TURN @ at(-L / 2 - 0.06, 0, 0.7), sel)


def p_pointer(sel):
    """PF16 Pointer: a glass mouse pointer arrow above a glass pad, its tip pointing down left;
    selected: the arrow pressed down onto the pad, a click ring lit round its tip"""
    arrow = [(0, 0), (0, -1.0), (0.26, -0.76), (0.45, -1.14), (0.6, -1.07), (0.41, -0.7), (0.74, -0.7)]
    t = 0.14
    tip = Vector((-0.2, 0.0, 0.16))

    def pad():
        p = box("pad", 0, 0.1, 0.06, 1.9, 1.5, 0.12, m_glass, 0.06)
        wire(p, "pad_wire")
        if sel:
            for k, r in enumerate((0.16, 0.28)):
                torus(f"click{k}", tip.x, tip.y, 0.125, r, 0.014 if k else 0.02, m_hot if k == 0 else m_core)
    turned(built(pad), TURN)

    def ptr():
        prism("pointer", arrow, -t / 2, t / 2, m_glass)
        outline_curve("pointer_edge", [(x, -t / 2 - 0.004, z) for x, z in arrow], 0.012, m_hot)
        outline_curve("pointer_edge_b", [(x, t / 2 + 0.004, z) for x, z in arrow], 0.008, m_edge)
    down = rot("Y", -135)                           # the tip (up left) turned to point down left
    m1 = at(tip.x, tip.y, tip.z) @ down
    moving(ptr, TURN @ at(0, 0, 0.45) @ m1, TURN @ m1, sel)


def p_popupmenu(sel):
    """PF17 PopupMenu: a glass menu panel with items, one highlighted with a submenu arrow; selected:
    the submenu slid out from behind it to the right"""
    W, H, z0 = 0.95, 1.55, 0.25
    items = [z0 + H - 0.2 - k * 0.27 for k in range(5)]

    def body():
        cylinder("menu_stand", 0, 0.05, 0.12, 0.08, 0.24, m_glass)
        p = box("menu", 0, 0, z0 + H / 2, W, 0.08, H, m_glass, 0.03)
        wire(p, "menu_wire")
        yf = -0.046
        for k, z in enumerate(items):
            box(f"menu_item{k}", -0.05, yf, z, W - 0.35 if k != 1 else W - 0.25, 0.01, 0.045, m_hot if k == 1 else m_core, 0)
        hl = box("menu_hl", 0, yf - 0.012, items[1], W - 0.1, 0.02, 0.2, glass_material("menu_hl_g", ICE, 0.05), 0.01)
        wire(hl, "menu_hl_wire", m_edge, 0.006)
        line("menu_sub_arrow", [(W / 2 - 0.16, yf - 0.02, items[1] + 0.05), (W / 2 - 0.1, yf - 0.02, items[1]),
                                (W / 2 - 0.16, yf - 0.02, items[1] - 0.05)], m_hot, 0.012)
    turned(built(body), TURN)

    def sub():
        p = box("submenu", 0, 0, -0.4, 0.8, 0.06, 0.8, m_glass, 0.03)
        wire(p, "submenu_wire", m_edge, 0.012)
        for k in range(3):
            box(f"sub_item{k}", -0.04, -0.036, -0.15 - k * 0.25, 0.55, 0.01, 0.04, m_core, 0)
    zt = items[1] + 0.12
    moving(sub, TURN @ at(0.0, 0.1, zt), TURN @ at(W / 2 + 0.36, -0.08, zt), sel)


PROGRAMS.update({"input": p_input, "internet": p_internet, "locale": p_locale, "notifications": p_notifications,
                 "palette": p_palette, "picasso96": p_picasso96, "pointer": p_pointer, "popupmenu": p_popupmenu})
# (Presets is a drawer in Prefs: the glass drawer + the EmPresets emblem, not an object of its own)


# --- batch 3 (PF19-PF27) -------------------------------------------------------------------------

def clipped(pts, zmin):
    """the parts of a polyline at or above z = zmin (cut where it crosses), as a list of polylines"""
    out, cur = [], []
    for a, b in zip(pts, pts[1:]):
        ia, ib = a[2] >= zmin, b[2] >= zmin
        if ia and not cur:
            cur = [a]
        if ia != ib:
            t = (zmin - a[2]) / (b[2] - a[2])
            q = tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
            if ia:
                cur.append(q)
                out.append(cur)
                cur = []
            else:
                cur = [q]
        if ib:
            cur.append(b)
    if len(cur) > 1:
        out.append(cur)
    return [c for c in out if len(c) > 1]


PRN_W, PRN_D, PRN_H, PRN_PW, PRN_PH = 1.8, 1.1, 0.58, 0.95, 1.15     # the shared glass printer


def printer_body():
    """the glass printer (PF19-PF21, UT02, UT03, UT11) without a page, around the origin"""
    W, D, H, pw = PRN_W, PRN_D, PRN_H, PRN_PW
    b = box("printer", 0, 0, H / 2, W, D, H, m_glass, 0.06)
    wire(b, "printer_wire")
    sl = 0.05
    outline_curve("printer_slot", [(-pw / 2 - sl, 0.12, H + 0.004), (pw / 2 + sl, 0.12, H + 0.004),
                                   (pw / 2 + sl, 0.28, H + 0.004), (-pw / 2 - sl, 0.28, H + 0.004)], 0.008, m_hot)
    box("printer_out", 0, -D / 2 - 0.006, H * 0.42, pw + 0.1, 0.01, 0.04, m_core, 0)
    for k in range(3):
        cylinder(f"printer_btn{k}", -W / 2 + 0.2 + k * 0.17, -D / 2 + 0.15, H + 0.01, 0.05, 0.03, m_hot if k == 0 else m_core)
    tray = box("printer_tray", 0, D / 2 + 0.05, H + 0.25, pw + 0.2, 0.05, 0.5, m_glass, 0.02)
    turned([tray], at(0, D / 2 + 0.05, H) @ rot("X", -20) @ at(0, -D / 2 - 0.05, -H))
    wire(tray, "printer_tray_wire", m_edge, 0.008)


def printer(sel, page_art):
    """PF19-PF21: a glass printer, a page in its top slot; selected: the page come out of the top.
    page_art(yf, w, h, zmin) draws the page's content on its front (local, page bottom at z = 0), only
    at or above zmin: the part still inside the printer has not been printed yet (user, 2026-11-16)"""
    H, pw, ph = PRN_H, PRN_PW, PRN_PH
    out0 = 0.18                                     # how far the page is out of the slot (normal)
    zmin = 0.0 if sel else ph - out0                # the print line, in page coordinates

    def page():
        p = box("page", 0, 0, ph / 2, pw, 0.02, ph, glass_material("page_g", ICE, 0.08), 0.008)
        wire(p, "page_wire", m_edge, 0.007)
        page_art(-0.016, pw, ph, zmin)
    turned(built(printer_body), TURN)
    lean = rot("X", -10)
    moving(page, TURN @ at(0, 0.2, H - ph + out0) @ lean, TURN @ at(0, 0.2, H - 0.05) @ lean, sel)


def p_printer(sel):
    """PF19 Printer: the printer, a page of text"""
    def art(yf, w, h, zmin):
        for k in range(6):
            z = h - 0.18 - k * 0.15
            if z + 0.015 >= zmin:
                box(f"page_text{k}", -0.04 if k % 3 == 2 else 0, yf, z, w - 0.3 - (0.12 if k % 3 == 2 else 0),
                    0.01, 0.03, m_hot if k == 0 else m_core, 0)
    printer(sel, art)


def p_printergfx(sel):
    """PF20 PrinterGfx: the printer, a page with a picture (mountains under a sun)"""
    def art(yf, w, h, zmin):
        z0 = h - 0.75
        mountains = [(-w / 2 + 0.1, yf, z0), (-0.18, yf, z0 + 0.38), (0.02, yf, z0 + 0.16), (0.22, yf, z0 + 0.45),
                     (w / 2 - 0.1, yf, z0)]
        for k, part in enumerate(clipped(mountains, zmin)):
            line(f"page_mountains{k}", part, m_hot, 0.016)
        if z0 - 0.02 >= zmin:
            box("page_ground", 0, yf, z0 - 0.02, w - 0.2, 0.01, 0.02, m_core, 0)
        if h - 0.2 - 0.08 >= zmin:
            torus("page_sun", -0.25, yf, h - 0.2, 0.08, 0.016, m_hot, axis="Y")
        x0, x1, zb, zt = -w / 2 + 0.08, w / 2 - 0.08, z0 - 0.08, h - 0.08
        frame = [(x0, yf, zt), (x1, yf, zt), (x1, yf, zb), (x0, yf, zb), (x0, yf, zt)]
        for k, part in enumerate(clipped(frame, zmin)):
            line(f"page_frame{k}", part, m_edge, 0.007)
    printer(sel, art)


def p_printerps(sel):
    """PF21 PrinterPS: the printer, a page with a vector curve and its control handles (PostScript)"""
    def art(yf, w, h, zmin):
        p0, c0, c1, p1 = Vector((-0.35, 0, h - 0.65)), Vector((-0.25, 0, h - 0.1)), Vector((0.2, 0, h - 0.9)), \
            Vector((0.35, 0, h - 0.25))
        pts = []
        for k in range(25):
            t = k / 24
            q = (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * c0 + 3 * (1 - t) * t * t * c1 + t ** 3 * p1
            pts.append((q.x, yf, q.z))
        for k, part in enumerate(clipped(pts, zmin)):
            line(f"page_curve{k}", part, m_hot, 0.016)
        for k, (a, b) in enumerate(((p0, c0), (p1, c1))):
            for j, part in enumerate(clipped([(a.x, yf, a.z), (b.x, yf, b.z)], zmin)):
                line(f"page_handle{k}_{j}", part, m_core, 0.006)
            for j, q in enumerate((a, b)):
                if q.z - 0.03 >= zmin:
                    box(f"page_knot{k}{j}", q.x, yf, q.z, 0.06, 0.01, 0.06, m_edge if j else m_hot, 0)
    printer(sel, art)


def monitor(name, screen_art, W=1.8, H=1.25, T=0.16, z0=0.38):
    """a glass monitor on a stand; screen_art(yf, W, H, z0) draws on its screen. Returns yf"""
    b = box(name + "_base", 0, 0.1, 0.05, 0.95, 0.6, 0.1, m_glass, 0.04)
    wire(b, name + "_base_wire", thickness=0.012)
    box(name + "_neck", 0, 0.12, 0.22, 0.2, 0.12, 0.26, m_glass, 0.02)
    s = box(name, 0, 0, z0 + H / 2, W, T, H, m_glass, 0.05)
    wire(s, name + "_wire")
    yf = -T / 2 - 0.006
    i = 0.09
    outline_curve(name + "_bezel", [(-W / 2 + i, yf, z0 + i), (W / 2 - i, yf, z0 + i), (W / 2 - i, yf, z0 + H - i),
                                    (-W / 2 + i, yf, z0 + H - i)], 0.008, m_core)
    cylinder(name + "_led", W / 2 - 0.14, yf - 0.004, z0 + 0.045, 0.025, 0.02, m_hot, axis="Y")
    if screen_art:
        screen_art(yf, W, H, z0)
    return yf


def p_screenblanker(sel):
    """PF22 ScreenBlanker: a glass monitor showing stars and a crescent moon; selected: the moon moved
    across the sky"""
    W, H, z0 = 1.8, 1.25, 0.38

    def stars(yf, W, H, z0):
        import random
        rnd = random.Random(7)
        for k in range(16):
            x = rnd.uniform(-W / 2 + 0.2, W / 2 - 0.2)
            z = rnd.uniform(z0 + 0.18, z0 + H - 0.18)
            s = rnd.choice((0.018, 0.026, 0.034))
            cylinder(f"star{k}", x, yf - 0.002, z, s, 0.01, m_hot if s > 0.03 else m_core, axis="Y", verts=12)

    def body():
        monitor("blank", stars)
    turned(built(body), TURN)

    def moon():
        cylinder("moon", 0, 0, 0, 0.17, 0.012, m_hot, axis="Y")
        cylinder("moon_shadow", 0.08, -0.01, 0.05, 0.15, 0.012, lacquer_material("moon_shadow"), axis="Y")
    yf = -0.08 - 0.012
    moving(moon, TURN @ at(-0.5, yf, z0 + H - 0.38), TURN @ at(0.45, yf, z0 + H - 0.3), sel)


def p_screenmode(sel):
    """PF23 ScreenMode: a glass monitor with a resolution frame (corner marks) inside; selected: the
    frame grown to the screen's edges"""
    W, H, z0 = 1.8, 1.25, 0.38
    f = (1.0, 0.66) if not sel else (W - 0.32, H - 0.3)

    def art(yf, W, H, z0):
        fw, fh = f
        zc = z0 + H / 2
        outline_curve("res_frame", [(-fw / 2, yf, zc - fh / 2), (fw / 2, yf, zc - fh / 2), (fw / 2, yf, zc + fh / 2),
                                    (-fw / 2, yf, zc + fh / 2)], 0.01, m_edge)
        for sx in (-1, 1):
            for sz in (-1, 1):
                x, z = sx * fw / 2, zc + sz * fh / 2
                line(f"res_corner{sx}{sz}", [(x - sx * 0.12, yf - 0.002, z), (x, yf - 0.002, z), (x, yf - 0.002, z - sz * 0.12)],
                     m_hot, 0.016)
        box("res_cross_h", 0, yf, zc, 0.14, 0.01, 0.014, m_core, 0)
        box("res_cross_v", 0, yf, zc, 0.014, 0.01, 0.14, m_core, 0)

    def body():
        monitor("smode", art)
    turned(built(body), TURN)


def p_screens(sel):
    """PF24 Screens: two Amiga screens inside a glass monitor's display, the front one covering the
    back one; selected: the front screen dragged down (the Amiga screen drag), cut off at the bottom
    of the display like on a real Amiga, the back screen's title bar and windows showing above it"""
    W, H, z0, i = 1.8, 1.25, 0.38, 0.09
    xl, xr, zb, zt = -W / 2 + i + 0.02, W / 2 - i - 0.02, z0 + i + 0.02, z0 + H - i - 0.02
    drag = 0.48 if sel else 0.0

    def screen(name, top, y, edge, art):
        h = top - zb
        p = box(name, 0, y, zb + h / 2, xr - xl, 0.02, h, glass_material(name + "_g", ICE, 0.06), 0.006)
        wire(p, name + "_wire", edge, 0.008)
        yf = y - 0.016
        tb = 0.13
        box(name + "_title", 0, yf, top - tb / 2 - 0.01, xr - xl - 0.04, 0.01, tb, glass_material(name + "_tb", ICE, 0.04), 0.004)
        for k, x in enumerate((xr - 0.1, xr - 0.24)):
            q = 0.04
            outline_curve(f"{name}_depth{k}", [(x - q, yf - 0.008, top - tb / 2 - 0.01 - q), (x + q, yf - 0.008, top - tb / 2 - 0.01 - q),
                                               (x + q, yf - 0.008, top - tb / 2 - 0.01 + q), (x - q, yf - 0.008, top - tb / 2 - 0.01 + q)],
                          0.006, m_hot)
        art(name, yf, top - tb - 0.02)

    def back_art(name, yf, ztop):
        for k in range(3):
            box(f"{name}_win{k}", -0.48 + k * 0.48, yf, ztop - 0.2, 0.38, 0.01, 0.28, m_core, 0.005)

    def front_art(name, yf, ztop):
        for k in range(5):
            z = ztop - 0.12 - k * 0.17
            if z > zb + 0.06:                           # cut off at the bottom of the display
                box(f"{name}_line{k}", -0.1, yf, z, xr - xl - 0.45, 0.01, 0.035, m_core, 0)

    def art(yf, W, H, z0):
        if sel:                                         # normal: only the screen that gets dragged (user)
            screen("scr_back", zt, yf - 0.012, m_edge, back_art)
        screen("scr_front", zt - drag, yf - 0.04, m_hot, front_art)

    def body():
        monitor("scr_mon", art)
    turned(built(body), TURN)


def p_serial(sel):
    """PF25 Serial: the Amiga's serial port, a 25-pin male D-sub (pins in a D-shaped shell) in a glass
    port block, and the cable's female D-sub (25 holes) with thumbscrews; selected: the plug pushed in.
    The port faces left, turned so it is seen at about 45 degrees"""
    tw, bw, dh = 0.95, 0.82, 0.24                  # the D: top width, bottom width, height
    zc = 0.72
    R = rot("Z", 11)
    xf = 0.3 - 0.006                               # the block's left face

    def d_shape(scale=1.0):
        return [(-bw / 2 * scale, -dh / 2 * scale), (bw / 2 * scale, -dh / 2 * scale), (tw / 2 * scale, dh / 2 * scale),
                (-tw / 2 * scale, dh / 2 * scale)]

    def rows(top, bottom):
        """the 13 + 12 positions (y, z) of a DB25"""
        return [((k - 6) * 0.062, top) for k in range(13)] + [((k - 5.5) * 0.062, bottom) for k in range(12)]

    def body():
        b = box("ser_block", 0.55, 0, 0.6, 0.5, 1.3, 1.2, m_glass, 0.05)
        wire(b, "ser_block_wire")
        # the male connector: a D-shaped shell standing out of the face, the pins inside it
        sh = prism("ser_male_shell", d_shape(1.14), -0.06, 0.06, glass_material("ser_male_g", ICE, 0.06))
        cut_faces(sh, lambda c: abs(c.y) < 0.05)
        shell_part(sh, 0.018)
        turned([sh], at(xf - 0.06, 0, zc) @ rot("Z", 90))
        for k, x in enumerate((xf - 0.12, xf - 0.004)):
            outline_curve(f"ser_male_rim{k}", [(x, y, zc + z) for y, z in d_shape(1.14)], 0.01, m_hot if k == 0 else m_edge)
        for k, (y, z) in enumerate(rows(0.045, -0.045)):
            o = cylinder(f"ser_pin{k}", 0, 0, 0, 0.014, 0.09, m_core, verts=10)
            turned([o], at(xf - 0.045, y, zc + z) @ rot("Y", 90))
        for sgn in (-1, 1):
            o = cylinder(f"ser_standoff{sgn}", 0, 0, 0, 0.05, 0.06, m_edge, verts=6)
            turned([o], at(xf - 0.03, sgn * 0.66, zc) @ rot("Y", 90))
    turned(built(body), R)

    cable = [(-0.62, 0, 0), (-0.9, 0, -0.05), (-1.1, 0, -0.35), (-1.15, 0, -zc + 0.04)]

    def plug():
        hood = box("ser_hood", -0.36, 0, 0, 0.5, 1.45, 0.42, m_glass, 0.06)
        wire(hood, "ser_hood_wire", m_edge, 0.01)
        fb = prism("ser_female", d_shape(1.0), -0.05, 0.05, glass_material("ser_female_g", ICE, 0.1))
        turned([fb], at(-0.05, 0, 0) @ rot("Z", 90))
        outline_curve("ser_female_edge", [(0.004, y, z) for y, z in d_shape(1.0)], 0.009, m_hot)
        for k, (y, z) in enumerate(rows(0.045, -0.045)):
            o = cylinder(f"ser_hole{k}", 0, 0, 0, 0.014, 0.01, m_core, verts=10)
            turned([o], at(0.004, y, z) @ rot("Y", 90))
        for sgn in (-1, 1):
            o = cylinder(f"ser_screw{sgn}", -0.06, sgn * 0.66, 0, 0.035, 0.26, m_hot, verts=12)
            o.rotation_euler = (0, math.pi / 2, 0)
        outline_curve("ser_cable", cable, 0.05, m_edge, closed=False)
    m0, m1 = R @ at(xf - 0.5, 0, zc), R @ at(xf - 0.03, 0, zc)
    for m in (m0, m1):
        FRAME_EXTRA.extend(m @ Vector(p) for p in cable)
    moving(plug, m0, m1, sel)


def p_sound(sel):
    """PF26 Sound: a glass loudspeaker; selected: the cone pushed out, a ring of sound in front"""
    W, D, H = 1.25, 0.95, 1.7
    zc = 0.72

    def body():
        b = box("spk", 0, 0, H / 2, W, D, H, m_glass, 0.07)
        wire(b, "spk_wire")
        yf = -D / 2
        torus("spk_surround", 0, yf - 0.01, zc, 0.45, 0.045, m_glass, axis="Y")
        torus("spk_surround_glow", 0, yf - 0.03, zc, 0.47, 0.012, m_edge, axis="Y")
        cylinder("spk_tweeter", 0, yf - 0.02, H - 0.32, 0.15, 0.05, m_glass, axis="Y")
        torus("spk_tweeter_rim", 0, yf - 0.045, H - 0.32, 0.15, 0.012, m_edge, axis="Y")
        sphere("spk_tweeter_dome", 0, yf - 0.03, H - 0.32, 0.08, m_hot, scale=(1, 0.5, 1))
        if sel:
            for k, (r, y) in enumerate(waves):
                torus(f"spk_wave{k}", 0, y, zc, r, 0.012, m_core if k else m_edge, axis="Y")

    def cone():
        bpy.ops.mesh.primitive_cone_add(vertices=64, radius1=0.12, radius2=0.42, depth=0.22, location=(0, 0, 0))
        c = bpy.context.object
        c.name = "spk_cone"
        bpy.ops.object.shade_smooth()
        register(c, m_glass)
        cut_faces(c, lambda v: -0.1 < v.z < 0.1)       # open at both ends: a cone, not a cup
        shell_part(c, 0.02)
        torus("spk_cone_ring", 0, 0, 0.0, 0.27, 0.008, m_core)
        sphere("spk_cap", 0, 0, -0.08, 0.13, m_hot, scale=(1, 1, 0.55))
    waves = [(0.62, -D / 2 - 0.25), (0.8, -D / 2 - 0.37)]
    turned(built(body), TURN)
    # the rings are only in the selected image: frame them in both, so the speaker stays exactly still
    FRAME_EXTRA.extend(TURN @ Vector((sx * r, y, zc + sz * r)) for r, y in waves for sx in (-1, 1) for sz in (-1, 1))
    yf = -D / 2
    face = TURN @ at(0, yf + 0.1, zc) @ rot("X", 90)          # local +z (the big end) towards the viewer
    moving(cone, face, TURN @ at(0, -0.12, 0) @ at(0, yf + 0.1, zc) @ rot("X", 90), sel)


def p_time(sel):
    """PF27 Time: a glass digital alarm clock (wedge body, snooze bar, a black glass display with
    seven-segment digits) showing 12:00, like a clock not yet set; selected: another time (07:30) and
    the clock lit from within (the user, 2026-11-16: time is better shown by a clock)"""
    W, D, h0, h1, lean = 1.8, 0.8, 0.82, 0.88, 0.18
    tilt = math.degrees(math.atan2(lean, h0))
    gain = 1.55 if sel else 1.0
    digit_mat = emission_material("clock_digits", LIGHTBLUE, 5.0 * gain)
    dim_mat = emission_material("clock_dim", LIGHTBLUE, 1.4 * gain)

    def on_face(t, out=0.0):
        """a frame on the sloping front face, t = 0 (bottom) .. 1 (top), out = towards the viewer"""
        return at(0, -D / 2 + lean * t - out, h0 * t) @ rot("X", -tilt)

    def body():
        v = [(-W / 2, -D / 2, 0), (W / 2, -D / 2, 0), (W / 2, D / 2, 0), (-W / 2, D / 2, 0),
             (-W / 2, -D / 2 + lean, h0), (W / 2, -D / 2 + lean, h0), (W / 2, D / 2, h1), (-W / 2, D / 2, h1)]
        o = slab("alarm", v, m_glass, 0.04)
        wire(o, "alarm_wire")
        win = box("alarm_window", 0, 0, 0, W - 0.24, 0.03, 0.52, glass_material("alarm_win", srgb((8, 10, 15)), 0.03), 0.02)
        wire(win, "alarm_window_wire", m_edge, 0.008)
        turned([win, objects[-1]], on_face(0.52, 0.015))
        digits = (1, 2, 0, 0) if not sel else (0, 7, 3, 0)
        parts = built(lambda: [seven(f"alarm_d{k}_", dg, x, 0, 0.2, 0.34, -0.035, digit_mat)
                               for k, (dg, x) in enumerate(zip(digits, (-0.6, -0.31, 0.12, 0.41)))])
        for k, z in enumerate((0.07, -0.07)):
            parts.append(cylinder(f"alarm_colon{k}", -0.095, -0.035, z, 0.028, 0.012, digit_mat, axis="Y", verts=12))
        parts.append(cylinder("alarm_al", -W / 2 + 0.24, -0.035, 0.19, 0.025, 0.012, dim_mat, axis="Y", verts=12))
        turned(parts, on_face(0.52, 0.015))
        sn = box("alarm_snooze", 0, D / 2 - 0.36, h1 + 0.05, W * 0.55, 0.3, 0.1, m_glass, 0.03)
        wire(sn, "alarm_snooze_wire", m_edge, 0.01)
        for k, x in enumerate((-0.68, 0.68)):
            cylinder(f"alarm_btn{k}", x, D / 2 - 0.3, h1 + 0.03, 0.07, 0.06, m_core)
        for k, x in enumerate((-0.7, 0.7)):
            box(f"alarm_foot{k}", x, 0, 0.0, 0.22, D - 0.1, 0.04, m_glass, 0.01)
    turned(built(body), TURN)
    if sel:                                         # lit from within (like the devices' selected images)
        inner = bpy.data.objects.new("alarm_inner", bpy.data.lights.new("alarm_inner", "POINT"))
        inner.data.energy = 45
        inner.data.shadow_soft_size = 0.35
        inner.data.color = LIGHTBLUE[:3]
        inner.location = TURN @ Vector((0, 0.05, h0 * 0.45))
        bpy.context.collection.objects.link(inner)


PROGRAMS.update({"printer": p_printer, "printergfx": p_printergfx, "printerps": p_printerps,
                 "screenblanker": p_screenblanker, "screenmode": p_screenmode, "screens": p_screens,
                 "serial": p_serial, "sound": p_sound, "time": p_time})


# --- batch 4 (PF28-PF35) -------------------------------------------------------------------------

def p_timezone(sel):
    """PF28 Timezone: a glass desk globe on a meridian arc, its axis tilted, a glowing time-zone band;
    selected: the globe turned, the band moved on"""
    R, zc, tilt = 0.72, 1.02, 23
    A = TURN @ at(0, 0, zc) @ rot("Y", tilt)       # the globe's own frame: its axis along local z

    def body():
        cylinder("tz_base", 0, 0, 0.05, 0.45, 0.1, m_glass)
        torus("tz_base_rim", 0, 0, 0.1, 0.45, 0.012, m_edge)
        cylinder("tz_post", 0, 0, 0.2, 0.05, 0.22, m_glass)
    turned(built(body), TURN)

    def mount():
        arc = torus("tz_arc", 0, 0, 0, R + 0.1, 0.03, m_glass)
        cut_faces(arc, lambda c: c.x < 0.05)
        arc.rotation_euler = (math.pi / 2, 0, 0)
        torus("tz_arc_glow", 0, 0, 0, R + 0.1, 0.01, m_edge).rotation_euler = (math.pi / 2, 0, 0)
        cut_faces(objects[-1], lambda c: c.x < 0.05)
    turned(built(mount), A)

    def globe():
        sphere("tz_globe", 0, 0, 0, R, m_glass)
        sphere("tz_core", 0, 0, 0, 0.12, m_core)
        torus("tz_equator", 0, 0, 0, R + 0.004, 0.009, m_edge)
        for k, zz in enumerate((0.4, -0.4)):
            torus(f"tz_par{k}", 0, 0, zz, math.sqrt(R * R - zz * zz) + 0.004, 0.006, m_core)
        for k, a in enumerate((0, 15)):                 # the time-zone band: two meridians 15 degrees apart
            o = torus(f"tz_band{k}", 0, 0, 0, R + 0.006, 0.014, m_hot)
            o.rotation_euler = (math.pi / 2, 0, math.radians(a - 60))
        for k in range(6):
            o = torus(f"tz_mer{k}", 0, 0, 0, R + 0.003, 0.005, m_core)
            o.rotation_euler = (math.pi / 2, 0, math.radians(k * 30))
    moving(globe, A, A @ rot("Z", 70), sel)


def p_uboot(sel):
    """PF29 UBoot: a glass rocket on a launch pad by its tower (boot = launch); selected: lifted off, a
    flame under it"""
    def pad():
        b = box("ub_pad", 0, 0, 0.08, 1.4, 1.1, 0.16, m_glass, 0.04)
        wire(b, "ub_pad_wire")
        torus("ub_pad_ring", 0, 0, 0.165, 0.32, 0.014, m_hot)
        for k in range(4):
            box(f"ub_tower{k}", -0.55 + (k % 2) * 0.22, 0.25 + (k // 2) * 0.22, 0.95, 0.04, 0.04, 1.6, m_glass, 0.008)
        for k in range(6):
            box(f"ub_rung{k}", -0.44, 0.36, 0.35 + k * 0.25, 0.26, 0.26, 0.02, m_edge, 0)
        box("ub_arm", -0.3, 0.2, 1.3, 0.5, 0.05, 0.05, m_glass, 0.01)
    turned(built(pad), TURN)

    def rocket():
        cylinder("ub_body", 0, 0, 0.75, 0.2, 1.0, m_glass)
        bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=0.2, radius2=0.0, depth=0.42, location=(0, 0, 1.46))
        n = bpy.context.object
        n.name = "ub_nose"
        bpy.ops.object.shade_smooth()
        register(n, m_glass)
        torus("ub_band", 0, 0, 1.24, 0.205, 0.012, m_edge)
        torus("ub_band2", 0, 0, 0.3, 0.205, 0.012, m_edge)
        o = torus("ub_window", 0, -0.2, 1.0, 0.07, 0.014, m_hot)
        o.rotation_euler = (math.pi / 2, 0, 0)
        cylinder("ub_core", 0, 0, 0.75, 0.04, 0.9, m_core, verts=16)
        for k in range(3):
            f = prism(f"ub_fin{k}", [(0.18, 0.25), (0.45, 0.25), (0.18, 0.62)], -0.02, 0.02, m_glass)
            turned([f], rot("Z", k * 120 + 30))
            e = outline_curve(f"ub_fin{k}_edge", [(0.18, 0, 0.25), (0.45, 0, 0.25), (0.18, 0, 0.62)], 0.008, m_edge)
            turned([e], rot("Z", k * 120 + 30))
        if sel:
            bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.15, radius2=0.0, depth=0.5, location=(0, 0, 0.0))
            fl = bpy.context.object
            fl.name = "ub_flame"
            fl.rotation_euler = (math.pi, 0, 0)
            bpy.ops.object.shade_smooth()
            register(fl, emission_material("ub_flame", srgb((230, 240, 255)), 6.0))
    lift = 0.62
    m0, m1 = TURN @ at(0.2, -0.05, -0.09), TURN @ at(0.2, -0.05, lift - 0.09)    # standing on the pad
    FRAME_EXTRA.extend(m1 @ Vector((x, y, z)) for x in (-0.15, 0.15) for y in (-0.15, 0.15) for z in (-0.25, 0.25))
    moving(rocket, m0, m1, sel)


def p_updates(sel):
    """PF30 Updates: a shallow glass tray, a glowing download arrow above it; selected: the arrow
    dropped into the tray"""
    arrow = [(-0.14, 0.3), (-0.34, 0.3), (0, -0.08), (0.34, 0.3), (0.14, 0.3), (0.14, 0.7), (-0.14, 0.7)]   # CCW

    def tray():
        t = open_box("upd_tray", 0, 0, 0.17, 1.6, 1.1, 0.34, m_glass, wall=0.035)
        wire(t, "upd_tray_wire")
        box("upd_bar", 0, -0.55 - 0.006, 0.17, 0.9, 0.01, 0.06, m_core, 0)
        box("upd_bar_fill", -0.2, -0.55 - 0.012, 0.17, 0.5, 0.01, 0.06, m_hot, 0)
    turned(built(tray), TURN)

    def arr():
        prism("upd_arrow", arrow, -0.08, 0.08, m_glass)
        outline_curve("upd_arrow_edge", [(x, -0.084, z) for x, z in arrow], 0.012, m_hot)
        outline_curve("upd_arrow_edge_b", [(x, 0.084, z) for x, z in arrow], 0.008, m_edge)
    moving(arr, TURN @ at(0, 0, 0.75), TURN @ at(0, 0, 0.12), sel)


def p_url(sel):
    """PF31 URL: two glass chain links; selected: the links joined"""
    def link(name):
        o = torus(name, 0, 0, 0, 0.36, 0.075, m_glass)
        o.scale = (1.55, 1, 1)
        g = torus(name + "_glow", 0, 0, 0, 0.36, 0.02, m_hot if name.endswith("b") else m_edge)
        g.scale = (1.55, 1, 1)
    zc = 0.45                                       # the standing link rests on the floor

    def first():
        link("url_a")
    turned(built(first), TURN @ at(-0.42, 0, zc) @ rot("X", 90))        # standing, along x

    def second():
        link("url_b")                                                   # lying flat, along x
    # joined: its left end passes through the standing link's right end
    moving(second, TURN @ at(1.15, 0, zc + 0.1) @ rot("Z", 25), TURN @ at(0.4, 0, zc), sel)


def p_usb(sel):
    """PF32 USB: a USB-A socket in a glass port block (an opening with a tongue and four contacts), a
    USB-A plug with the trident on its body; selected: the plug pushed in"""
    zc = 0.6
    R = rot("Z", 11)
    xf = 0.3 - 0.006
    ow, oh = 0.62, 0.24                            # the opening (y, z)

    def body():
        b = box("usb_block", 0.55, 0, 0.55, 0.5, 1.1, 1.1, m_glass, 0.05)
        wire(b, "usb_block_wire")
        outline_curve("usb_socket", [(xf, -ow / 2, zc - oh / 2), (xf, ow / 2, zc - oh / 2), (xf, ow / 2, zc + oh / 2),
                                     (xf, -ow / 2, zc + oh / 2)], 0.012, m_hot)
        tg = box("usb_tongue", xf + 0.08, 0, zc + 0.03, 0.18, ow - 0.12, 0.07, glass_material("usb_tongue_g", ICE, 0.1), 0.01)
        wire(tg, "usb_tongue_wire", m_edge, 0.006)
        for k in range(4):
            box(f"usb_contact{k}", xf + 0.04, -0.18 + k * 0.12, zc - 0.01, 0.1, 0.05, 0.012, m_core, 0)
    turned(built(body), R)

    cable = [(-0.62, 0, 0), (-0.85, 0, -0.04), (-1.0, 0, -0.3), (-1.05, 0, -zc + 0.04)]

    def plug():
        bd = box("usbp_body", -0.38, 0, 0, 0.48, 0.8, 0.36, m_glass, 0.08)
        wire(bd, "usbp_body_wire", m_edge, 0.01)
        shell = box("usbp_shell", -0.07, 0, 0, 0.14, ow - 0.03, oh - 0.03, glass_material("usbp_shell_g", ICE, 0.05), 0.01)
        wire(shell, "usbp_shell_wire", m_hot, 0.008)
        zt = 0.18 + 0.006                           # the trident on top of the body
        xs = -0.38
        line("usbp_trident", [(xs - 0.17, 0, zt), (xs + 0.13, 0, zt)], m_hot, 0.012)
        line("usbp_tri_a", [(xs - 0.05, 0, zt), (xs + 0.02, -0.1, zt), (xs + 0.09, -0.1, zt)], m_hot, 0.01)
        line("usbp_tri_b", [(xs - 0.1, 0, zt), (xs - 0.04, 0.09, zt), (xs + 0.04, 0.09, zt)], m_hot, 0.01)
        torus("usbp_tri_c", xs - 0.19, 0, zt, 0.03, 0.01, m_hot)
        box("usbp_tri_sq", xs + 0.12, -0.1, zt, 0.04, 0.04, 0.01, m_hot, 0)
        line("usbp_tri_head", [(xs + 0.13, -0.04, zt), (xs + 0.19, 0, zt), (xs + 0.13, 0.04, zt)], m_hot, 0.01)
        outline_curve("usbp_cable", cable, 0.045, m_edge, closed=False)
    m0, m1 = R @ at(xf - 0.5, 0, zc), R @ at(xf + 0.12, 0, zc)      # selected: the shell inside the socket
    for m in (m0, m1):
        FRAME_EXTRA.extend(m @ Vector(p) for p in cable)
    moving(plug, m0, m1, sel)


def p_wbpattern(sel):
    """PF33 WBPattern: a glass wall panel, a paint roller on it, the pattern it has rolled out behind it;
    selected: the roller rolled on, more pattern"""
    W, H, z0 = 1.8, 1.25, 0.12
    n = 7
    s = (W - 0.3) / n
    painted = 3 if not sel else 5

    def body():
        p = box("wbp_wall", 0, 0, z0 + H / 2, W, 0.08, H, m_glass, 0.03)
        wire(p, "wbp_wall_wire")
        cylinder("wbp_foot", 0, 0.1, 0.06, 0.5, 0.12, m_glass)
        yf = -0.046
        for c in range(painted):
            for r in range(5):
                if (r + c) % 2 == 0:
                    box(f"wbp_px{c}{r}", -W / 2 + 0.15 + s * (c + 0.5), yf, z0 + 0.15 + (r + 0.5) * (H - 0.3) / 5,
                        s * 0.86, 0.01, (H - 0.3) / 5 * 0.86, m_core if (c + r) % 4 else m_hot, 0)
    turned(built(body), TURN)

    def roller():
        cylinder("wbp_roller", 0, 0, 0, 0.14, H - 0.3, glass_material("wbp_roller_g", ICE, 0.15))
        torus("wbp_roller_t", 0, 0, (H - 0.3) / 2, 0.14, 0.012, m_edge)
        torus("wbp_roller_b", 0, 0, -(H - 0.3) / 2, 0.14, 0.012, m_edge)
        line("wbp_frame", [(0, 0, (H - 0.3) / 2 + 0.04), (0, -0.28, (H - 0.3) / 2 + 0.12), (0, -0.28, -0.15),
                           (-0.25, -0.45, -0.75)], m_edge, 0.022)
        cylinder("wbp_handle", 0, 0, 0, 0.06, 0.45, m_glass)
        turned([objects[-1]], at(-0.37, -0.52, -0.95) @ rot("X", 30) @ rot("Y", -30))
    zr = z0 + H / 2
    x0 = -W / 2 + 0.15 + s * 3 + 0.08
    x1 = -W / 2 + 0.15 + s * 5 + 0.08
    moving(roller, TURN @ at(x0, -0.2, zr), TURN @ at(x1, -0.2, zr), sel)


def p_wbstartup(sel):
    """PF34 WBStartup: an illuminated rocker switch (the user's example, 2026-11-16): a black glass
    housing with a bezel and side latches, a translucent glass rocker marked I and O, no contacts shown;
    normal: off (pressed down on O); selected: on (pressed down on I) and the rocker lit from within"""
    W, D, Hb = 0.95, 1.2, 0.5                      # the body below the bezel
    black = glass_material("rk_black", srgb((8, 10, 15)), 0.05)

    def housing():
        b = box("rk_body", 0, 0, Hb / 2, W, D, Hb, black, 0.03)
        wire(b, "rk_body_wire", m_edge, 0.01)
        # the bezel: a frame round the rocker
        fw, fd, ft, fh = W + 0.2, D + 0.2, 0.11, 0.16
        for k, (x, y, sx, sy) in enumerate(((0, -fd / 2 + ft / 2, fw, ft), (0, fd / 2 - ft / 2, fw, ft),
                                            (-fw / 2 + ft / 2, 0, ft, fd), (fw / 2 - ft / 2, 0, ft, fd))):
            fr = box(f"rk_bezel{k}", x, y, Hb + fh / 2, sx, sy, fh, black, 0.02)
            wire(fr, f"rk_bezel{k}_wire", m_edge, 0.009)
        for sgn in (-1, 1):                         # the latches on the sides
            lt = box(f"rk_latch{sgn}", sgn * (W / 2 + 0.03), 0, Hb * 0.55, 0.06, 0.32, Hb * 0.55, black, 0.01)
            wire(lt, f"rk_latch{sgn}_wire", m_core, 0.007)
    turned(built(housing), TURN)

    rock_mat = glow_through_material("rk_lit", LIGHTBLUE, 0.55) if sel else glass_material("rk_glass", ICE, 0.12)

    def rocker():
        r = box("rk_rocker", 0, 0, 0, W - 0.04, D - 0.04, 0.26, rock_mat, 0.04)
        wire(r, "rk_rocker_wire", m_hot if sel else m_edge, 0.009)
        zt = 0.135
        box("rk_mark_I", 0, D * 0.25, zt, 0.06, 0.24, 0.012, emission_material("rk_white", srgb((245, 250, 255)), 4.0), 0)
        torus("rk_mark_O", 0, -D * 0.25, zt, 0.09, 0.022, emission_material("rk_white2", srgb((245, 250, 255)), 4.0))
    piv = TURN @ at(0, 0, Hb + 0.12)
    moving(rocker, piv @ rot("X", 13), piv @ rot("X", -13), sel)     # off: the O end down; on: the I end
    if sel:                                         # lit from within
        inner = bpy.data.objects.new("rk_inner", bpy.data.lights.new("rk_inner", "POINT"))
        inner.data.energy = 14
        inner.data.shadow_soft_size = 0.3
        inner.data.color = LIGHTBLUE[:3]
        inner.location = TURN @ Vector((0, 0, Hb - 0.1))
        bpy.context.collection.objects.link(inner)


def boing_material(name):
    """the Amiga Boing ball's checker, in the base colours: light blue light and black lacquer"""
    m, nt = new_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    ck = n.new("ShaderNodeTexChecker")
    ck.inputs["Scale"].default_value = 30.0          # about 8 squares across a 0.26 ball
    nt.links.new(tc.outputs["Object"], ck.inputs["Vector"])
    em = n.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = LIGHTBLUE
    em.inputs["Strength"].default_value = 3.0
    dk = n.new("ShaderNodeBsdfPrincipled")
    dk.inputs["Base Color"].default_value = (0.004, 0.005, 0.008, 1)
    dk.inputs["Roughness"].default_value = 0.15
    mix = n.new("ShaderNodeMixShader")
    nt.links.new(ck.outputs["Fac"], mix.inputs["Fac"])
    nt.links.new(dk.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    finish(nt, mix.outputs[0])
    return m


WB_W, WB_H, WB_Z0, WB_I = 2.0, 1.15, 0.38, 0.09       # the widescreen monitor of PF35 (also SY07)


def wb_desktop(y, xl, xr, zt):
    """the booted AmigaOS 4.1 Workbench as on the guest, drawn on a monitor's display at y: the screen
    title bar, the drive icons at the top left (RAM Disk, System, Work; FTDisk below), the AmiDock down
    the right edge (PF35 Workbench, SY07 RinghioServer)"""
    box("wb_titlebar", 0, y, zt - 0.03, xr - xl, 0.01, 0.05, glass_material("wb_tb", ICE, 0.04), 0.003)
    box("wb_titletext", xl + 0.45, y - 0.006, zt - 0.03, 0.75, 0.008, 0.016, m_core, 0)
    for k, (x, z) in enumerate(((xl + 0.09, zt - 0.14), (xl + 0.25, zt - 0.14), (xl + 0.41, zt - 0.14),
                                (xl + 0.09, zt - 0.34))):
        d = box(f"wb_drive{k}", x, y - 0.01, z, 0.11, 0.02, 0.07, glass_material(f"wb_drive{k}_g", ICE, 0.08), 0.005)
        wire(d, f"wb_drive{k}_wire", m_edge, 0.004)
        box(f"wb_drive{k}_label", x, y - 0.006, z - 0.075, 0.1, 0.008, 0.014, m_core, 0)
    dk = box("wb_dock", xr - 0.06, y - 0.008, zt - 0.47, 0.09, 0.016, 0.8, glass_material("wb_dock_g", ICE, 0.06), 0.006)
    wire(dk, "wb_dock_wire", m_edge, 0.005)
    for k in range(8):
        box(f"wb_dock_icon{k}", xr - 0.06, y - 0.02, zt - 0.13 - k * 0.095, 0.055, 0.008, 0.055,
            m_hot if k in (1, 2) else m_core, 0.004)


def p_workbench(sel):
    """PF35 Workbench (the Amiga's desktop, the user 2026-11-16): a widescreen glass monitor showing a
    booted AmigaOS 4.1 Workbench as on the guest: the screen title bar, the drive icons at the top left,
    the AmiDock down the right edge (no Boing ball, user); selected: two windows opened on it, spread
    out (the System drawer with its icons, and a Shell)"""
    W, H, z0, i = 2.0, 1.15, 0.38, 0.09
    xl, xr, zb, zt = -W / 2 + i, W / 2 - i, z0 + i, z0 + H - i

    def win(name, x0, z1, w, h, y, edge, inner):
        p = box(name, x0 + w / 2, y, z1 - h / 2, w, 0.02, h, glass_material(name + "_g", ICE, 0.08), 0.006)
        wire(p, name + "_wire", edge, 0.008)
        yf = y - 0.016
        box(name + "_title", x0 + w / 2, yf, z1 - 0.045, w - 0.03, 0.01, 0.06, glass_material(name + "_tb", ICE, 0.04), 0.004)
        q = 0.02
        for k, gx in enumerate((x0 + 0.05, x0 + w - 0.05)):
            outline_curve(f"{name}_gad{k}", [(gx - q, yf - 0.006, z1 - 0.045 - q), (gx + q, yf - 0.006, z1 - 0.045 - q),
                                             (gx + q, yf - 0.006, z1 - 0.045 + q), (gx - q, yf - 0.006, z1 - 0.045 + q)],
                          0.004, m_hot)
        inner(name, yf, x0, z1 - 0.1, w)

    def art(yf, W_, H_, z0_):
        y = yf - 0.006
        wb_desktop(y, xl, xr, zt)
        # (no Boing ball: the user wants the windows spread out evenly)
        if sel:                                     # two windows opened on the Workbench
            def drawer_icons(name, yf2, x0, ztop, w):
                for k in range(6):
                    box(f"{name}_icon{k}", x0 + 0.1 + (k % 3) * 0.17, yf2 - 0.004, ztop - 0.06 - (k // 3) * 0.15, 0.08, 0.008,
                        0.06, m_edge if k % 2 else m_core, 0.003)

            def shell_lines(name, yf2, x0, ztop, w):
                line(f"{name}_prompt", [(x0 + 0.05, yf2 - 0.006, ztop - 0.02), (x0 + 0.09, yf2 - 0.006, ztop - 0.05),
                                        (x0 + 0.05, yf2 - 0.006, ztop - 0.08)], m_hot, 0.008)
                for k, ln in enumerate((0.3, 0.42, 0.22)):
                    box(f"{name}_line{k}", x0 + 0.14 + ln / 2, yf2 - 0.004, ztop - 0.05 - k * 0.08, ln, 0.008, 0.02, m_core, 0)
            # spread out: the drawer upper right (between the drive icons and the dock), the Shell
            # lower left; the lower right stays clear for the gear emblem
            win("wb_win_sys", -0.05, zt - 0.12, 0.75, 0.46, y - 0.12, m_edge, drawer_icons)
            win("wb_win_shell", xl + 0.06, zb + 0.47, 0.72, 0.36, y - 0.16, m_hot, shell_lines)   # fully inside the display

    def body():
        monitor("wb_mon", art, W=W, H=H, z0=z0)
    turned(built(body), TURN)


PROGRAMS.update({"timezone": p_timezone, "uboot": p_uboot, "updates": p_updates, "url": p_url, "usbprefs": p_usb,
                 "wbpattern": p_wbpattern, "wbstartup": p_wbstartup, "workbench": p_workbench})
