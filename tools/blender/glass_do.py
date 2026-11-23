"""glass_do.py: the "do" programs of the glass icon set (2026-11-21), loaded by glass_icons.py into its
namespace after glass_emblems.py. Each reuses the glass model of the program's own icon that its drawer's
emblem already has (glass_emblems.py), standing on the floor as a program object; the user picks one of a
few variants, one by one. Public domain.
"""
import math

import bpy
from mathutils import Matrix, Vector

DO_SCALE = 1.3


def stood(objs, zc, k=DO_SCALE):
    """emblem models are built round (0, 0, zc0=0.55); stand them on the floor, scaled, turned to the camera"""
    turned(objs, TURN @ at(0, 0, zc) @ Matrix.Scale(k, 4) @ at(0, 0, -0.55))
    for o in objs:                  # the framing measures meshes only: add the curves' points
        if o.type == "CURVE" and not o.hide_render:
            for sp in o.data.splines:
                FRAME_EXTRA.extend(o.matrix_world @ p.co.xyz for p in sp.points)
    return objs


def drop(o):
    """leave a built part out (hidden, not deleted: the dispatcher removes everything a build made)"""
    o.hide_render = True
    objects.remove(o)


def obj(objs, name):
    return next(o for o in objs if o.name.split(".")[0] == name)      # (a second build gets .001 names)


def amiupdate(sel):
    """DO08 AmiUpdate (user picked variant A 2026-11-21): the glass gear with its red button; selected: the
    button pressed in, brighter"""
    objs = built(e_amiupdate)
    if sel:
        b = obj(objs, "au_button")
        b.location.y += 0.07
        b.data.materials.clear()
        b.data.materials.append(accent_glass("au_red_lit", RED_HOT, 3.2, 0.03))
    stood(objs, 0.72 * DO_SCALE + 0.03)


def back_arrow(name, y, R, a0, a1, mat, thick=0.04, head=0.13):
    """a circular arrow at radius R in the x-z plane (centre 0, 0.55), from angle a0 to a1 (degrees,
    counter-clockwise as seen from the front = turning back), the head at a1"""
    pts = []
    for k in range(25):
        a = math.radians(a0 + (a1 - a0) * k / 24)
        pts.append((-R * math.cos(a), y, 0.55 + R * math.sin(a)))
    objs = [outline_curve(name, pts, thick, mat, closed=False)]
    a = math.radians(a1)
    tx, tz = -R * math.cos(a), 0.55 + R * math.sin(a)                 # the tip's base on the circle
    dx, dz = -math.sin(a), -math.cos(a)                                # the arrow's direction there
    if a1 < a0:
        dx, dz = -dx, -dz
    nx, nz = -dz, dx
    tri = [(tx + nx * head, tz + nz * head), (tx - nx * head, tz - nz * head), (tx + dx * head * 1.4, tz + dz * head * 1.4)]
    objs.append(prism(name + "_head", tri, y - 0.03, y + 0.03, mat))
    return objs


def rb_clock(hands_back=False):
    """System_RollBack's clock: a glass clock face with glowing hands and ticks (round 0, 0.55)"""
    R, T = 0.5, 0.2
    yf = -T / 2 - 0.006
    cylinder("rb_body", 0, 0, 0.55, R, T, m_glass, axis="Y")
    for k, (y, mat) in enumerate(((-T / 2, m_edge), (T / 2, m_core))):
        torus(f"rb_rim{k}", 0, y, 0.55, R, 0.012, mat, axis="Y")
    for k in range(12):
        big = k % 3 == 0
        tk = box(f"rb_tick{k}", 0, yf, 0, 0.035 if big else 0.022, 0.012, 0.11 if big else 0.06, m_hot if big else m_core, 0)
        turned([tk], at(0, 0, 0.55) @ rot("Y", k * 30) @ at(0, 0, R * 0.74))
    cylinder("rb_hub", 0, yf - 0.01, 0.55, 0.045, 0.03, m_hot, axis="Y")
    hh, mm = (9, 10) if hands_back else (10, 10)
    for name, deg, length, width in (("rb_hour", (hh + mm / 60) * 30, R * 0.5, 0.05), ("rb_min", mm * 6, R * 0.72, 0.035)):
        h = box(name, 0, yf - 0.012, length / 2 - 0.05, width, 0.012, length, m_hot, 0)
        turned([h], at(0, 0, 0.55) @ rot("Y", deg))


def rollback(sel):
    """DO09 System_RollBack (user picked variant C 2026-11-21): AmiUpdate's glass gear with a green back arrow in front; selected: the arrow turned back"""
    green = accent_glass("rb_green", GREEN_LIT, 1.8, 0.03)

    def make():
        objs = built(e_amiupdate)
        for n in ("au_button", "au_seat", "au_seat_glow"):
            drop(obj(objs, n))
        d = 70 if sel else 0
        back_arrow("rb_arrow", -0.18, 0.31, 320 + d, 50 + d, green, 0.04, 0.15)
    stood(built(make), 0.72 * DO_SCALE + 0.03)


def viewer(fn, prefix, sel, how):
    """AmiGS / AmiPDF: the drawer emblem's page + swirl + label + magnifier, standing; selected: the
    magnifier moves (how: "lift" = lifts and tilts towards the viewer, "slide" = slides over the swirl)"""
    objs = built(fn)
    mag = [o for o in objs if o.name.split(".")[0].startswith(prefix + "_mag")]
    turned(mag, at(0, 0, 0.16))          # the emblem's handle would sink below the floor
    if sel:
        m = {"lift": at(0.02, -0.16, 0.22) @ at(0.33, -0.25, 0.3) @ rot("X", -25) @ at(-0.33, 0.25, -0.3),
             "slide": at(-0.3, -0.02, 0.32)}[how]
        turned(mag, m)
    stood(objs, 0.74)


def amigs(sel):
    """DO10 AmiGS (user picked variant A 2026-11-21, the page stays white): selected: the magnifier lifts
    and tilts towards the viewer"""
    viewer(e_amigs, "ps", sel, "lift")


def amipdf(sel):
    """DO11 AmiPDF: the same as AmiGS (they share their icon), with PDF"""
    viewer(e_amipdf, "pdf", sel, "lift")


def sgrab(sel, how):
    """DO12 SGrab (user picked variant A 2026-11-22): the drawer emblem's glass camera, standing; selected (how): "a" = the button pressed and
    the flash fires, "b" = the lens extends, "c" = the flash fires with a burst of light in front"""
    objs = built(e_sgrab)                 # (built turned by Z -18: moves go through R)
    R = rot("Z", -18)
    f = obj(objs, "cam_flash")            # the flash is dim until it fires
    fire = sel and how in ("a", "c")
    f.data.materials.clear()
    f.data.materials.append(emission_material("cam_flash_fire" if fire else "cam_flash_off",
                                              srgb((255, 255, 250) if fire else (150, 165, 190)), 16.0 if fire else 0.5))
    if sel and how == "a":
        b = obj(objs, "cam_button")
        turned([b], at(0, 0, -0.05))
        b.data.materials.clear()
        b.data.materials.append(accent_glass("cam_button_lit", RED_HOT, 3.5, 0.03))
    if sel and how == "b":
        lens = [o for o in objs if o.name.split(".")[0].startswith(("cam_lens", "cam_glint"))]
        turned(lens, R @ at(0, -0.2, 0) @ R.inverted())
        objs.append(turned([cylinder("cam_tube", 0, -0.28, 0.42, 0.23, 0.22, m_glass, axis="Y")], R)[0])
    if sel and how == "c":
        ray = emission_material("cam_ray_m", srgb((255, 255, 235)), 8.0)
        for k in range(8):
            ln = 0.22 if k % 2 == 0 else 0.13
            r = box(f"cam_ray{k}", 0, 0, 0.1 + ln / 2, 0.018, 0.01, ln, ray, 0)
            objs.append(turned([r], R @ at(0.4, -0.25, 0.68) @ rot("Y", k * 45))[0])
    stood(objs, 0.46 * DO_SCALE)


def python(sel, how):
    """DO13 the Python icon (user picked variant A 2026-11-22): the drawer emblem's Boing ball with its yellow glass ring, standing; selected
    (how): "a" = the ball turns (the checks move on), "b" = ball and ring bounce up, "c" = the ring tilts
    the other way and glows"""
    objs = built(e_python)
    if sel and how == "a":
        b = obj(objs, "py_ball")
        b.rotation_euler.z += math.radians(30)
    if sel and how == "b":
        turned(objs, at(0, 0, 0.28))
    if sel and how == "c":
        for n in ("py_ring", "py_ring_glow"):
            obj(objs, n).rotation_euler = (math.radians(-16), math.radians(24), 0)
        g = obj(objs, "py_ring_glow")
        g.data.materials.clear()
        g.data.materials.append(emission_material("py_ring_hotter", srgb((255, 225, 90)), 9.0))
    stood(objs, 0.62 * DO_SCALE)


# ---- the 16 commodities: own glass objects + the EmCommodity emblem (user 2026-11-21/22) ----

ACCENTS = (srgb((230, 40, 40)), srgb((40, 210, 90)), srgb((60, 120, 255)))


def dock_tile(name, colour, k):
    """a small glass dock icon: a clear cube with a coloured glass core"""
    t = box(name, 0, 0, 0, 0.44, 0.44, 0.44, m_glass, 0.06)
    wire(t, name + "_wire", m_edge, 0.01)
    sphere(name + "_core", 0, 0, 0, 0.13, accent_glass(f"{name}_c{k}", colour, 1.8, 0.03))


def amidock_c(sel, how):
    """CO01 AmiDock (user picked "a" 2026-11-22): "a" = a glass dock bar with three icons, selected: the middle one pops up;
    "b" = the stock icon's red button on a glass base, selected: pressed in, brighter;
    "c" = an upright dock, selected: the top icon slides out"""
    if how == "a":
        def bar():
            b = box("dock_bar", 0, 0, 0.12, 1.9, 0.62, 0.24, m_glass, 0.06)
            wire(b, "dock_bar_wire")
            box("dock_glow", 0, -0.32, 0.12, 1.7, 0.01, 0.03, m_hot, 0)
            for k, x in ((0, -0.6), (2, 0.6)):
                dock_tile(f"dock_t{k}", ACCENTS[k], k)
                turned(objects[-3:], at(x, 0, 0.47))
        turned(built(bar), TURN)
        moving(lambda: dock_tile("dock_t1", ACCENTS[1], 1), TURN @ at(0, 0, 0.47), TURN @ at(0, -0.1, 0.82), sel)
    elif how == "b":
        def base():
            b = box("ad_base", 0, 0, 0.18, 1.3, 1.3, 0.36, m_glass, 0.08)
            wire(b, "ad_base_wire")
            torus("ad_seat", 0, 0, 0.37, 0.42, 0.05, m_glass)
            torus("ad_seat_glow", 0, 0, 0.38, 0.44, 0.014, m_hot)
        turned(built(base), TURN)

        def dome():
            bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=0.4, location=(0, 0, 0))
            d = bpy.context.object
            d.name = "ad_dome"
            d.scale = (1, 1, 0.6)
            bpy.ops.object.shade_smooth()
            register(d, accent_glass("ad_red_lit" if sel else "ad_red", RED_HOT, 3.4 if sel else 1.6, 0.03))
        moving(dome, TURN @ at(0, 0, 0.42), TURN @ at(0, 0, 0.34), sel)
    else:
        def stand():
            b = box("dock_up", 0, 0, 0.95, 0.66, 0.5, 1.9, m_glass, 0.06)
            wire(b, "dock_up_wire")
            box("dock_up_glow", -0.34, -0.2, 0.95, 0.01, 0.01, 1.7, m_hot, 0)
            for k, z in ((1, 0.95), (2, 0.4)):
                dock_tile(f"dock_t{k}", ACCENTS[k], k)
                turned(objects[-3:], at(0, -0.05, z))
        turned(built(stand), TURN)
        moving(lambda: dock_tile("dock_t0", ACCENTS[0], 0), TURN @ at(0, -0.05, 1.5), TURN @ at(0.55, -0.15, 1.5), sel)


def spinner(name, R, sel):
    """a busy spinner: a ring of green glass dots, brighter round the ring; selected: turned on a step and lit"""
    for k in range(8):
        a = math.radians(90 - k * 45 - (45 if sel else 0))
        g = 0.4 + 2.6 * (1 - k / 8) * (1.6 if sel else 1.0)
        sphere(f"{name}{k}", R * math.cos(a), 0, R * math.sin(a), 0.06 + 0.025 * (1 - k / 8),
               accent_glass(f"{name}_m{k}{int(sel)}", GREEN_LIT, g, 0.03))


def asyncwb_c(sel, how):
    """CO02 AsyncWB (user picked "a" 2026-11-22; Workbench copies, moves and deletes in the background): "a" = two glass windows,
    a green busy spinner on the front one, selected: it turns on and lights up; "b" = a window with a
    progress bar, selected: the bar fills; "c" = two windows side by side and a page between them,
    selected: the page arrives in the right one"""
    if how in ("a", "b"):
        def wins():
            if how == "a":
                turned(built(lambda: window("aw_back", 1.3, 1.1, 0)), at(-0.3, 0.35, 0.35))
            yf = window("aw_front", 1.4, 1.2, 0)
            if how == "b":
                tr = box("aw_trough", 0, yf - 0.01, 0.45, 1.0, 0.03, 0.2, m_glass, 0.02)
                wire(tr, "aw_trough_wire", m_edge, 0.008)
                L = 0.9 if sel else 0.38
                box("aw_fill", -0.47 + L / 2, yf - 0.03, 0.45, L, 0.03, 0.14, accent_glass("aw_green", GREEN_LIT, 2.2, 0.03), 0.01)
            else:
                sp = built(lambda: spinner("aw_dot", 0.27, sel))
                turned(sp, at(-0.22, yf - 0.06, 0.52))
        objs = built(wins)
        turned(objs, TURN @ at(0.12, 0, 0))
    else:
        def two():
            for k, x in enumerate((-0.6, 0.6)):
                turned(built(lambda k=k: window(f"aw_w{k}", 0.95, 0.95, 0)), at(x, 0, 0))
        turned(built(two), TURN)

        def page():
            pg = box("aw_page", 0, 0, 0, 0.36, 0.03, 0.46, accent_glass("aw_page_g", GREEN_LIT, 1.4, 0.03), 0.01)
            wire(pg, "aw_page_wire", m_hot, 0.008)
        moving(page, TURN @ at(-0.6, -0.16, 0.42), TURN @ at(0.6, -0.16, 0.42) if sel else TURN @ at(-0.05, -0.3, 0.55), sel)


def dbl_arrow(name, L, w, mat):
    """a flat double arrow along x (length L, shaft width w) in the x-z plane round the origin"""
    h = w * 2.4
    pts = [(-L / 2, 0), (-L / 2 + h, h), (-L / 2 + h, w / 2), (L / 2 - h, w / 2), (L / 2 - h, h), (L / 2, 0),
           (L / 2 - h, -h), (L / 2 - h, -w / 2), (-L / 2 + h, -w / 2), (-L / 2 + h, -h)]
    return prism(name, pts, -0.03, 0.03, mat)


def autobordersize_c(sel, how):
    """CO03 AutoBorderSize (user picked "c" 2026-11-23; windows resized by catching their border; user 2026-11-23: the arrows by the
    border; kept off the lower right, where the emblem sits): "a" = a double arrow on the left border,
    selected: the border dragged out, the window wider; "b" = a diagonal double arrow on the upper right
    corner, selected: the window bigger both ways; "c" = as "a", and the caught border lights up blue"""
    blue = accent_glass("abs_blue", srgb((60, 120, 255)), 2.4, 0.03)
    W0, H0, dW, dH = 1.3, 1.1, 0.4, 0.25
    W = W0 + (dW if sel else 0)
    H = H0 + (dH if sel and how == "b" else 0)
    if how == "b":
        xl = -W0 / 2                               # the lower left corner stays put
    else:
        xl = W0 / 2 - W                            # the right edge stays put

    def win():
        p = box("abs_win", xl + W / 2, 0, H / 2, W, 0.12, H, m_glass, 0.03)
        wire(p, "abs_win_wire")
        yf = -0.066
        box("abs_title", xl + W / 2, yf - 0.01, H - 0.12, W - 0.1, 0.02, 0.14, m_core, 0.01)
        if how == "c" and sel:
            box("abs_border", xl + 0.03, yf - 0.012, H / 2, 0.06, 0.025, H - 0.04, blue, 0)
        a = dbl_arrow("abs_arrow", 0.6, 0.09, m_hot)
        a.visible_shadow = False
        if how == "b":
            turned([a], at(xl + W, yf - 0.06, H) @ rot("Y", -45))
        else:
            turned([a], at(xl, yf - 0.06, H * 0.5))
    turned(built(win), TURN)
    # both sizes in the framing, so the two images match
    if how == "b":
        box_pts = [(x, z) for x in (-W0 / 2, W0 / 2 + dW + 0.25) for z in (0, H0 + dH + 0.25)]
    else:
        box_pts = [(x, z) for x in (W0 / 2 - W0 - dW - 0.32, W0 / 2) for z in (0, H0)]
    FRAME_EXTRA.extend(TURN @ Vector((x, 0, z)) for x, z in box_pts)


YELLOW_TIP = srgb((255, 196, 0))


def glass_page(name):
    """a clear glass page with a folded corner and glowing edges, standing (bottom at z = 0)"""
    w, h, fold = 0.8, 1.0, 0.22
    outline = [(-w / 2, 0), (w / 2, 0), (w / 2, h - fold), (w / 2 - fold, h), (-w / 2, h)]
    prism(name, outline, -0.05, 0.05, m_glass)
    outline_curve(name + "_edge", [(x, -0.055, z) for x, z in outline], 0.012, m_edge)
    prism(name + "_fold", [(w / 2 - fold, h), (w / 2, h - fold), (w / 2 - fold, h - fold)], -0.08, -0.05, m_glass)
    for k in range(4):
        box(f"{name}_l{k}", -0.05, -0.06, 0.72 - k * 0.16, 0.5, 0.01, 0.035, m_core, 0)


def mouse_pointer(name, k=1.0, ghost=False):
    """a flat glowing mouse pointer (tip at the origin, pointing up left) in the x-z plane; ghost: a
    faint frosted outline (the pointer hidden)"""
    pts = [(0, 0), (0, -0.62), (0.15, -0.48), (0.26, -0.72), (0.36, -0.67), (0.25, -0.43), (0.45, -0.43)]
    mat = glass_material("ptr_ghost", ICE, 0.35) if ghost else m_hot
    o = prism(name, [(x * k, z * k) for x, z in pts], -0.03, 0.03, mat)
    o.visible_shadow = False
    o.hide_render = ghost                     # hidden: only a faint outline left
    outline_curve(name + "_edge", [(x * k, -0.035, z * k) for x, z in pts], 0.005 if ghost else 0.008,
                  m_core if ghost else m_edge)
    return o


def info_card(name, w=0.8, h=0.5, glow=1.4):
    """a yellow glass info card (as the stock AutoInfo icon's "Info" window), three text lines"""
    c = box(name, 0, 0, 0, w, 0.05, h, accent_glass(name + f"_g{glow}", YELLOW_TIP, glow, 0.03), 0.02)
    wire(c, name + "_wire", m_edge, 0.008)
    for k in range(3):
        box(f"{name}_l{k}", -w * 0.08 * k, -0.035, h * 0.22 - k * h * 0.22, w * (0.7 - 0.16 * k), 0.01, 0.035, m_hot, 0)


def autoinfo_c(sel, how):
    """CO04 AutoInfo (user picked "a" 2026-11-23; shows an icon's information when the pointer rests on it): "a" = a glass page icon
    with a yellow info card above it, selected: the card pops up and lights; "b" = a glass info sign (i in a
    ring), selected: the dot of the i hops up; "c" = the pointer on a page icon, selected: the yellow info
    card slides out beside it"""
    if how == "a":
        turned(built(lambda: glass_page("ai_page")), TURN @ at(-0.25, 0.1, 0))
        moving(lambda: info_card("ai_card", glow=3.0 if sel else 1.8), TURN @ at(0.25, -0.2, 0.75),
               TURN @ at(0.3, -0.25, 1.15), sel)
    elif how == "b":
        blue = accent_glass("ai_blue", srgb((60, 120, 255)), 1.8, 0.03)

        def sign():
            cylinder("ai_disc", 0, 0, 0.62, 0.6, 0.12, m_glass, axis="Y")
            torus("ai_ring", 0, -0.07, 0.62, 0.6, 0.035, m_edge, axis="Y")
            box("ai_stem", 0, -0.08, 0.5, 0.15, 0.06, 0.48, blue, 0.03)
            box("ai_foot", 0.0, -0.08, 0.29, 0.3, 0.06, 0.06, blue, 0.01)
        turned(built(sign), TURN)
        moving(lambda: sphere("ai_dot", 0, 0, 0, 0.1, accent_glass("ai_dot_g", srgb((60, 120, 255)), 2.4 if sel else 1.8, 0.03)),
               TURN @ at(0, -0.09, 0.9), TURN @ at(0, -0.12, 1.38), sel)
    else:
        def scene():
            turned(built(lambda: glass_page("ai_page")), at(-0.35, 0.1, 0))
            turned(built(lambda: mouse_pointer("ai_ptr", 0.8)), at(-0.1, -0.15, 0.85))
        turned(built(scene), TURN)
        # not selected: the card is folded away to a dot at the pointer's tip
        moving(lambda: info_card("ai_card", glow=2.6), TURN @ at(-0.1, -0.12, 0.85) @ Matrix.Scale(0.02, 4),
               TURN @ at(0.45, -0.15, 0.85), sel)


def tb_window(name, W, H, active, glow=2.2):
    """a glass window with a title bar: blue glass when active, clear when not; returns its front y"""
    p = box(name, 0, 0, H / 2, W, 0.1, H, m_glass, 0.03)
    wire(p, name + "_wire")
    yf = -0.056
    tb = accent_glass(f"{name}_on{glow}", srgb((60, 120, 255)), glow, 0.03) if active else m_glass
    t = box(name + "_title", 0, yf - 0.012, H - 0.11, W - 0.06, 0.025, 0.16, tb, 0.01)
    if not active:
        wire(t, name + "_title_wire", m_core, 0.006)
    for k in range(3):
        box(f"{name}_l{k}", -W * 0.1, yf - 0.01, H - 0.38 - k * 0.17, W * 0.6, 0.01, 0.035, m_core, 0)
    return yf


def autopoint_c(sel, how):
    """CO05 AutoPoint (user picked "c" 2026-11-23; the window under the pointer becomes the active one): "a" = two windows, the
    pointer on the back one, selected: its title bar lights up (active); "b" = one window and the pointer
    beside it, selected: the pointer moves onto it and its title bar lights; "c" = as "a", selected: the
    back window also comes forward"""
    if how in ("a", "c"):
        def wins():
            turned(built(lambda: tb_window("ap_front", 1.1, 0.95, not sel)), at(0.25, -0.05, 0))
        turned(built(wins), TURN)
        back = lambda: tb_window("ap_back", 1.1, 0.95, sel)
        if how == "a":
            turned(built(back), TURN @ at(-0.3, 0.35, 0.4))
        else:
            moving(back, TURN @ at(-0.3, 0.35, 0.4), TURN @ at(-0.3, -0.25, 0.4), sel)
        turned(built(lambda: mouse_pointer("ap_ptr", 0.75)), TURN @ at(-0.62, -0.4, 1.12))
    else:
        turned(built(lambda: tb_window("ap_win", 1.2, 1.05, sel)), TURN @ at(0.15, 0, 0))
        moving(lambda: mouse_pointer("ap_ptr", 0.75), TURN @ at(-0.75, -0.2, 0.75), TURN @ at(-0.1, -0.2, 0.75), sel)


def click_rings(name, n=2):
    """the double click: n thin glowing rings round the origin, in the x-z plane"""
    for k in range(n):
        o = torus(f"{name}{k}", 0, 0, 0, 0.12 + 0.1 * k, 0.012, m_hot, axis="Y")
        o.visible_shadow = False


def clicktofront_c(sel, how):
    """CO06 ClickToFront (user picked "a" 2026-11-23; the window you click on comes to the front): "a" = two windows, the pointer
    double-clicking the back one (two rings), selected: it comes to the front, active; "b" = the same
    without the rings, selected: the two windows swap places; "c" = three windows stacked, the pointer on the
    rearmost, selected: it comes to the front"""
    if how in ("a", "b"):
        front = lambda: tb_window("cf_front", 1.1, 0.95, not sel)
        back = lambda: tb_window("cf_back", 1.1, 0.95, sel)
        P_front, P_back = TURN @ at(0.25, -0.05, 0), TURN @ at(-0.3, 0.35, 0.4)
        if how == "b":
            moving(front, P_front, TURN @ at(0.25, 0.45, 0.0), sel)
        else:
            turned(built(front), P_front)
        moving(back, P_back, TURN @ at(-0.3, -0.35, 0.4), sel)
        tip = TURN @ at(-0.62, -0.55, 1.12)
        turned(built(lambda: mouse_pointer("cf_ptr", 0.75)), tip)
        if how == "a":
            turned(built(lambda: click_rings("cf_click")), tip)
    else:
        pos = [at(-0.45, 0.45, 0.5), at(-0.1, 0.12, 0.25), at(0.25, -0.2, 0)]
        for k in (1, 2):
            turned(built(lambda k=k: tb_window(f"cf_w{k}", 1.0, 0.85, False)), TURN @ pos[k])
        moving(lambda: tb_window("cf_w0", 1.0, 0.85, sel), TURN @ pos[0], TURN @ at(-0.45, -0.5, 0.5), sel)
        turned(built(lambda: mouse_pointer("cf_ptr", 0.7)), TURN @ at(-0.75, -0.6, 1.25))


PROGRAMS.update({"clicktofront_a": lambda sel: clicktofront_c(sel, "a"),
                 "clicktofront_b": lambda sel: clicktofront_c(sel, "b"),
                 "clicktofront_c": lambda sel: clicktofront_c(sel, "c")})
def popup_menu(name, rows=4, lit=0, w=0.7):
    """a glass pop-up menu: rows of item lines, row lit (blue glass bar) or None; top left at the origin"""
    rh = 0.17
    h = rows * rh + 0.06
    p = box(name, w / 2, 0, -h / 2, w, 0.05, h, glass_material("menu_tint", srgb((150, 185, 235)), 0.06), 0.02)
    wire(p, name + "_wire", m_hot, 0.012)
    blue = accent_glass(name + "_lit", srgb((60, 120, 255)), 2.4, 0.03)
    for k in range(rows):
        z = -0.03 - rh / 2 - k * rh
        if k == lit:
            box(f"{name}_bar", w / 2, -0.035, z, w - 0.06, 0.02, rh - 0.03, blue, 0.01)
        box(f"{name}_l{k}", 0.08 + (w * (0.55 - 0.1 * (k % 2))) / 2, -0.05, z, w * (0.55 - 0.1 * (k % 2)), 0.01, 0.035,
            m_hot if k == lit else m_core, 0)


def contextmenus_c(sel, how):
    """CO07 ContextMenus (user picked "a" 2026-11-23; menus that pop up where you click): "a" = a window with a glass pop-up menu, an
    item lit under the pointer, selected: the next item lit, the pointer moved down to it; "b" = a window
    and the pointer, selected: the menu pops up at the pointer; "c" = the menu with a lit item, selected:
    its submenu slides out"""
    turned(built(lambda: window("cm_win", 1.15, 1.0, 0)), TURN @ at(-0.2, 0.45, 0))
    origin = TURN @ at(-0.42, -0.25, 0.92)
    if how == "a":
        turned(built(lambda: popup_menu("cm_menu", 4, 1 if sel else 0)), origin)
        moving(lambda: mouse_pointer("cm_ptr", 0.6), origin @ at(0.5, -0.06, -0.12), origin @ at(0.5, -0.06, -0.29), sel)
    elif how == "b":
        moving(lambda: popup_menu("cm_menu", 4, 0), origin @ Matrix.Scale(0.02, 4), origin, sel)
        turned(built(lambda: mouse_pointer("cm_ptr", 0.6)), origin @ at(0.02, -0.08, 0.02))
    else:
        turned(built(lambda: popup_menu("cm_menu", 4, 1)), origin)
        turned(built(lambda: mouse_pointer("cm_ptr", 0.6)), origin @ at(0.5, -0.08, -0.29))
        moving(lambda: popup_menu("cm_sub", 3, 0 if sel else None, 0.6), origin @ at(0.1, 0.06, -0.2),
               origin @ at(0.68, -0.02, -0.2), sel)


PROGRAMS.update({"contextmenus_a": lambda sel: contextmenus_c(sel, "a"),
                 "contextmenus_b": lambda sel: contextmenus_c(sel, "b"),
                 "contextmenus_c": lambda sel: contextmenus_c(sel, "c")})
PROGRAMS.update({"clicktofront": lambda sel: clicktofront_c(sel, "a"),
                 "contextmenus": lambda sel: contextmenus_c(sel, "a")})
PROGRAMS.update({"autopoint": lambda sel: autopoint_c(sel, "c")})
PROGRAMS.update({"autopoint_a": lambda sel: autopoint_c(sel, "a"), "autopoint_b": lambda sel: autopoint_c(sel, "b"),
                 "autopoint_c": lambda sel: autopoint_c(sel, "c"),
                 "autoinfo": lambda sel: autoinfo_c(sel, "a")})
PROGRAMS.update({"autoinfo_a": lambda sel: autoinfo_c(sel, "a"), "autoinfo_b": lambda sel: autoinfo_c(sel, "b"),
                 "autoinfo_c": lambda sel: autoinfo_c(sel, "c"),
                 "autobordersize": lambda sel: autobordersize_c(sel, "c")})
PROGRAMS.update({"autobordersize_a": lambda sel: autobordersize_c(sel, "a"),
                 "autobordersize_b": lambda sel: autobordersize_c(sel, "b"),
                 "autobordersize_c": lambda sel: autobordersize_c(sel, "c")})
PROGRAMS.update({"asyncwb": lambda sel: asyncwb_c(sel, "a")})
PROGRAMS.update({"asyncwb_a": lambda sel: asyncwb_c(sel, "a"), "asyncwb_b": lambda sel: asyncwb_c(sel, "b"),
                 "asyncwb_c": lambda sel: asyncwb_c(sel, "c")})
PROGRAMS.update({"amidock": lambda sel: amidock_c(sel, "a")})
PROGRAMS.update({"amidock_a": lambda sel: amidock_c(sel, "a"), "amidock_b": lambda sel: amidock_c(sel, "b"),
                 "amidock_c": lambda sel: amidock_c(sel, "c")})
PROGRAMS.update({"sgrab": lambda sel: sgrab(sel, "a"), "python": lambda sel: python(sel, "a"),
                 "python_a": lambda sel: python(sel, "a"), "python_b": lambda sel: python(sel, "b"),
                 "python_c": lambda sel: python(sel, "c")})
PROGRAMS.update({"amiupdate": amiupdate, "rollback": rollback, "amigs": amigs, "amipdf": amipdf,
                 "sgrab_a": lambda sel: sgrab(sel, "a"), "sgrab_b": lambda sel: sgrab(sel, "b"),
                 "sgrab_c": lambda sel: sgrab(sel, "c")})


def crossdos_c(sel, how):
    """CO08 CrossDOS (user picked "a" 2026-11-23; reads and writes PC (FAT) disks): "a" = the glass floppy, selected: its shutter
    slides open; "b" = the floppy with a glass page sticking out of its top, selected: the page rises out;
    "c" = the floppy with a blue double arrow across it (Amiga and PC), selected: the arrow lights up
    and the shutter opens"""
    turned(built(lambda: floppy(sel and how != "b")), Matrix.Identity(4))
    if how == "b":
        moving(lambda: glass_page("cd_page"), at(0.15, 0.2, 0.95) @ Matrix.Scale(0.9, 4),
               at(0.15, 0.2, 1.45) @ Matrix.Scale(0.9, 4), sel)
    elif how == "c":
        mat = accent_glass("cd_arrow_g", srgb((60, 120, 255)), 3.0 if sel else 1.2, 0.03)
        a = dbl_arrow("cd_arrow", 1.3, 0.11, mat)
        a.visible_shadow = False
        turned([a], at(0, 0, 0) @ rot("Z", -14) @ at(-0.05, -0.2, 0.42))


PROGRAMS.update({"crossdos": lambda sel: crossdos_c(sel, "a"),
                 "crossdos_a": lambda sel: crossdos_c(sel, "a"),
                 "crossdos_b": lambda sel: crossdos_c(sel, "b"),
                 "crossdos_c": lambda sel: crossdos_c(sel, "c")})


def typed_page(name, kind):
    """a glass page with a coloured type mark on its front: "pic" a blue picture with a green hill,
    "snd" a red sound disc, "txt" yellow lines; None: plain"""
    glass_page(name)
    yf = -0.08
    if kind == "pic":
        box(name + "_pic", -0.05, yf, 0.45, 0.5, 0.03, 0.38, accent_glass("tp_blue", srgb((60, 120, 255)), 2.0, 0.03), 0.01)
        prism(name + "_hill", [(-0.27, 0.28), (0.0, 0.5), (0.2, 0.28)], yf - 0.04, yf - 0.02,
              accent_glass("tp_green", GREEN_LIT, 2.0, 0.03))
    elif kind == "snd":
        cylinder(name + "_snd", -0.05, yf, 0.45, 0.22, 0.04, accent_glass("tp_red", RED_HOT, 2.0, 0.03), axis="Y")
        cylinder(name + "_snd_hub", -0.05, yf - 0.03, 0.45, 0.06, 0.03, m_hot, axis="Y")
    elif kind == "txt":
        for k in range(3):
            box(f"{name}_t{k}", -0.05, yf, 0.6 - k * 0.15, 0.5 if k < 2 else 0.3, 0.03, 0.06,
                accent_glass("tp_yellow", YELLOW, 2.0, 0.03), 0)


def deficons_c(sel, how):
    """CO09 DefIcons (user picked "a" 2026-11-23; gives files without an icon one by their type): "a" = three glass pages, each with
    a type mark (picture, sound, text), selected: they fan out; "b" = a plain glass page, selected: it gets
    its type mark (a picture); "c" = a stack of pages, selected: the front one lifts and shows its mark"""
    if how == "a":
        kinds = ("txt", "snd", "pic")
        for k, kind in enumerate(kinds):
            ang = (k - 1) * (18 if sel else 7)
            moving(lambda k=k, kind=kind: typed_page(f"di_p{k}", kind),
                   TURN @ at(-0.25 + k * 0.25, 0.3 - k * 0.25, 0.12) @ rot("Y", (k - 1) * 7),
                   TURN @ at(-0.45 + k * 0.45, 0.3 - k * 0.25, 0.15) @ rot("Y", ang), sel)
    elif how == "b":
        turned(built(lambda: typed_page("di_page", "pic" if sel else None)), TURN @ Matrix.Scale(1.25, 4))
    else:
        for k, kind in enumerate(("snd", "txt")):
            turned(built(lambda k=k, kind=kind: typed_page(f"di_s{k}", kind)), TURN @ at(-0.2 + k * 0.1, 0.3 - k * 0.15, 0.1 - k * 0.05))
        moving(lambda: typed_page("di_front", "pic" if sel else None), TURN @ at(0.0, 0.0, -0.1),
               TURN @ at(0.05, -0.15, 0.35), sel)


PROGRAMS.update({"deficons": lambda sel: deficons_c(sel, "a"),
                 "deficons_a": lambda sel: deficons_c(sel, "a"),
                 "deficons_b": lambda sel: deficons_c(sel, "b"),
                 "deficons_c": lambda sel: deficons_c(sel, "c")})


def depth_gadget(name, s=0.14, lit=False):
    """the depth gadget: two overlapping squares (the back one up right), glowing blue when lit"""
    mat = accent_glass(name + "_g", srgb((60, 120, 255)), 2.6, 0.03) if lit else m_core
    for k, (dx, dz, dy) in enumerate(((s * 0.3, s * 0.3, 0.0), (-s * 0.2, -s * 0.2, -0.015))):
        b = box(f"{name}_{k}", dx, dy, dz, s, 0.012, s, mat if k == 1 or not lit else m_glass, 0.005)
        wire(b, f"{name}_{k}_wire", m_hot, 0.006)


def depthtofront_c(sel, how):
    """CO10 DepthToFront (user picked "a" 2026-11-23; the depth gadget brings a window to the front): "a" = two windows, the pointer on
    the back one's lit depth gadget, selected: it comes to the front; "b" = a large glass depth gadget, its
    two squares, selected: the back square comes to the front; "c" = as "a", selected: the two windows swap
    places"""
    W, H = 1.1, 0.95

    def win(name, active, gadget_lit):
        tb_window(name, W, H, active)
        depth_gadget(name + "_dg", lit=gadget_lit)
        bpy.context.view_layer.update()
        for o in objects[-4:]:
            o.location = Vector(o.location) + Vector((W / 2 - 0.14, -0.085, H - 0.11))
    if how in ("a", "c"):
        P_front, P_back = TURN @ at(0.25, -0.05, 0), TURN @ at(-0.3, 0.35, 0.4)
        if how == "c":
            moving(lambda: win("dt_front", not sel, False), P_front, TURN @ at(0.25, 0.55, 0.0), sel)
        else:
            turned(built(lambda: win("dt_front", not sel, False)), P_front)
        moving(lambda: win("dt_back", sel, True), P_back, TURN @ at(-0.3, -0.35, 0.4), sel)
        tip = TURN @ at(-0.3 + W / 2 - 0.12, -0.6, 0.4 + H - 0.14)
        turned(built(lambda: mouse_pointer("dt_ptr", 0.7)), tip)
    else:
        s, blue = 0.85, accent_glass("dt_blue", srgb((60, 120, 255)), 2.4, 0.03)

        def square(name, mat):
            b = box(name, 0, 0, 0, s, 0.1, s, mat, 0.03)
            wire(b, name + "_wire")
        P_a, P_b = TURN @ at(0.18, 0.15, 0.85), TURN @ at(-0.18, -0.15, 0.5)
        turned(built(lambda: square("dt_sq_a", blue if sel else m_glass)), P_b if sel else P_a)   # the back one
        turned(built(lambda: square("dt_sq_b", m_glass)), P_a if sel else P_b)
        FRAME_EXTRA.extend(P @ Vector((x, 0, z)) for P in (P_a, P_b) for x in (-s / 2, s / 2) for z in (-s / 2, s / 2))


PROGRAMS.update({"depthtofront": lambda sel: depthtofront_c(sel, "a"),
                 "depthtofront_a": lambda sel: depthtofront_c(sel, "a"),
                 "depthtofront_b": lambda sel: depthtofront_c(sel, "b"),
                 "depthtofront_c": lambda sel: depthtofront_c(sel, "c")})


CX_FONT = {"C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
           "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"]}


def exchange_c(sel, how):
    """CO11 Exchange (user picked "b" 2026-11-23; controls the commodities: on, off, show, quit): "a" = a glass panel with three
    toggle switches and green lights, selected: the middle switch flips, its light goes out; "b" = a glass
    dot display showing CX in green dots (as the stock icon), selected: the letters scroll one dot left;
    "c" = a glass list window, three commodity rows with green lights, selected: the middle row lit blue,
    its light out"""
    green = accent_glass("ex_green", GREEN_LIT, 2.6, 0.03)
    if how == "a":
        W, H = 1.45, 1.05

        def panel():
            p = box("ex_panel", 0, 0, H / 2, W, 0.14, H, m_glass, 0.04)
            wire(p, "ex_panel_wire")
            for k in range(3):
                z = H - 0.25 - k * 0.3
                slot = box(f"ex_slot{k}", 0.1, -0.075, z, 0.5, 0.02, 0.14, m_core, 0.02)
                on = not (sel and k == 1)
                box(f"ex_knob{k}", 0.1 + (0.13 if on else -0.13), -0.11, z, 0.2, 0.06, 0.18, m_hot, 0.03)
                if on:
                    sphere(f"ex_led{k}", -0.45, -0.09, z, 0.07, green)
                else:
                    sphere(f"ex_led{k}", -0.45, -0.08, z, 0.07, m_glass)
                torus(f"ex_ledring{k}", -0.45, -0.075, z, 0.09, 0.012, m_edge, axis="Y")
        turned(built(panel), TURN)
    elif how == "b":
        W, H, d = 1.5, 1.0, 0.11
        cols = CX_FONT["C"], CX_FONT["X"]
        shift = 1 if sel else 0

        def display():
            p = box("ex_disp", 0, 0, H / 2, W, 0.14, H, m_glass, 0.04)
            wire(p, "ex_disp_wire")
            lit = set()
            for li, g in enumerate(cols):
                for r, row in enumerate(g):
                    for c, ch in enumerate(row):
                        if ch == "1":
                            lit.add((li * 6 + c - shift + 1, r))
            for c in range(13):
                for r in range(7):
                    x, z = -W / 2 + 0.09 + c * d, H - 0.17 - r * d * 1.0
                    if (c, r) in lit:
                        sphere(f"ex_d{c}_{r}", x, -0.08, z, 0.037, green)
                    else:
                        sphere(f"ex_d{c}_{r}", x, -0.075, z, 0.013, m_core)
        turned(built(display), TURN)
    else:
        W, H = 1.3, 1.15
        blue = accent_glass("ex_blue", srgb((60, 120, 255)), 2.2, 0.03)

        def lst():
            tb_window("ex_win", W, H, True)
            for k in range(3):
                z = H - 0.42 - k * 0.24
                if sel and k == 1:
                    box("ex_row_lit", 0, -0.075, z, W - 0.14, 0.02, 0.2, blue, 0.01)
                box(f"ex_row{k}", 0.05, -0.09, z, 0.7, 0.01, 0.04, m_hot if sel and k == 1 else m_core, 0)
                on = not (sel and k == 1)
                sphere(f"ex_led{k}", -W / 2 + 0.17, -0.09, z, 0.06, green if on else m_glass)
            for o in objects:
                if o.name.startswith("ex_win_l"):
                    o.hide_render = True
        turned(built(lst), TURN)


PROGRAMS.update({"exchange": lambda sel: exchange_c(sel, "b"),
                 "exchange_a": lambda sel: exchange_c(sel, "a"),
                 "exchange_b": lambda sel: exchange_c(sel, "b"),
                 "exchange_c": lambda sel: exchange_c(sel, "c")})


SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def fkey(name, label, W=1.1, H=1.0, lit=False):
    """a glass function key standing up, its face to the viewer, the label glowing on the face; lit:
    the face blue glass and the label brighter; the face at y = -D/2"""
    D = 0.42
    k = box(name, 0, 0, H / 2, W, D, H, m_glass, 0.09)
    wire(k, name + "_wire")
    face = accent_glass("fk_face_lit", srgb((60, 120, 255)), 1.4, 0.05) if lit else glass_material("fk_face", ICE, 0.1)
    f = box(name + "_face", 0, -D / 2 - 0.01, H / 2 + 0.03, W - 0.2, 0.02, H - 0.26, face, 0.05)
    wire(f, name + "_face_wire", m_hot if lit else m_core, 0.006)
    mat = m_hot if lit else accent_glass("fk_label", srgb((60, 120, 255)), 2.8, 0.03)
    t = glow_text(name + "_label", label, 0, -D / 2 - 0.03, 0, H * 0.34, mat, SANS_BOLD)
    bpy.context.view_layer.update()
    t.location.x = -W / 2 + 0.17
    t.location.z = H - 0.32


def key_base(name, W, D=0.62, T=0.16):
    """the glass slab the keys stand in (its top at z = T)"""
    b = box(name, 0, 0, T / 2, W, D, T, m_glass, 0.03)
    wire(b, name + "_wire")


def fkey_c(sel, how):
    """CO12 FKey (user picked "a" 2026-11-23; keys that start programs and do other actions): "a" = a glass F1 key on a slab,
    selected: pressed down, its face blue; "b" = three keys F1 F2 F3, selected: the middle one pressed;
    "c" = the F1 key and a small window, selected: the key pressed, the window pops up"""
    T, dn = 0.16, 0.13
    up, down = at(0, 0, T), at(0, 0, T - dn)
    if how == "a":
        turned(built(lambda: key_base("fk_base", 1.35)), TURN)
        moving(lambda: fkey("fk_f1", "F1", lit=sel), TURN @ up, TURN @ down, sel)
    elif how == "b":
        turned(built(lambda: key_base("fk_base", 2.15, 0.55)), TURN)
        for k in range(3):
            P = TURN @ at(-0.68 + k * 0.68, 0, 0)
            if k == 1:
                moving(lambda: fkey("fk_f2", "F2", 0.6, 0.62, sel), P @ up, P @ down, sel)
            else:
                turned(built(lambda k=k: fkey(f"fk_f{k + 1}", f"F{k + 1}", 0.6, 0.62)), P @ up)
    else:
        P = TURN @ at(-0.25, 0, 0)
        turned(built(lambda: key_base("fk_base", 1.1)), P)
        moving(lambda: fkey("fk_f1", "F1", 0.9, 0.82, lit=sel), P @ up, P @ down, sel)
        Pw = TURN @ at(0.45, 0.3, 0.85)
        moving(lambda: tb_window("fk_win", 0.8, 0.65, True), Pw @ Matrix.Scale(0.02, 4), Pw, sel)


PROGRAMS.update({"fkey": lambda sel: fkey_c(sel, "a"),
                 "fkey_a": lambda sel: fkey_c(sel, "a"),
                 "fkey_b": lambda sel: fkey_c(sel, "b"),
                 "fkey_c": lambda sel: fkey_c(sel, "c")})


def mouseblanker_c(sel, how):
    """CO13 MouseBlanker (user picked "c" 2026-11-23; hides the pointer while you type): "a" = a window with the pointer on it,
    selected: the pointer fades to a faint outline; "b" = the pointer over a glass keyboard row, selected:
    a key pressed, the pointer faded; "c" = a window with text and a blue text cursor, the pointer on it,
    selected: more text typed, the pointer faded"""
    if how == "a":
        turned(built(lambda: tb_window("mb_win", 1.3, 1.1, True)), TURN @ at(0, 0.1, 0))
        turned(built(lambda: mouse_pointer("mb_ptr", 0.9, sel)), TURN @ at(-0.1, -0.12, 0.75))
    elif how == "b":
        T, dn = 0.16, 0.1
        turned(built(lambda: key_base("mb_base", 1.9, 0.55)), TURN)
        for k in range(4):
            def key(k=k):
                b = box(f"mb_key{k}", 0, 0, 0.17, 0.38, 0.36, 0.34, m_hot if sel and k == 2 else m_glass, 0.05)
                wire(b, f"mb_key{k}_wire", m_hot, 0.008)
            P = TURN @ at(-0.66 + k * 0.44, 0, T)
            if k == 2:
                moving(key, P, P @ at(0, 0, -dn), sel)
            else:
                turned(built(key), P)
        turned(built(lambda: mouse_pointer("mb_ptr", 1.0, sel)), TURN @ at(-0.05, -0.3, 1.45))
    else:
        W, H = 1.3, 1.1
        blue = accent_glass("mb_blue", srgb((60, 120, 255)), 2.6, 0.03)

        def win():
            tb_window("mb_win", W, H, True)
            for o in objects:
                if o.name.startswith("mb_win_l"):
                    o.hide_render = True
            lines = [0.8, 0.65, 0.55 if sel else 0.2]
            for k, L in enumerate(lines):
                z = H - 0.38 - k * 0.2
                box(f"mb_t{k}", -W / 2 + 0.12 + L / 2, -0.07, z, L, 0.01, 0.04, m_core, 0)
            box("mb_cursor", -W / 2 + 0.17 + lines[2], -0.075, H - 0.78, 0.04, 0.02, 0.15, blue, 0)
        turned(built(win), TURN @ at(0, 0.1, 0))
        turned(built(lambda: mouse_pointer("mb_ptr", 0.8, sel)), TURN @ at(0.15, -0.12, 0.6))


PROGRAMS.update({"mouseblanker": lambda sel: mouseblanker_c(sel, "c"),
                 "mouseblanker_a": lambda sel: mouseblanker_c(sel, "a"),
                 "mouseblanker_b": lambda sel: mouseblanker_c(sel, "b"),
                 "mouseblanker_c": lambda sel: mouseblanker_c(sel, "c")})


def caps_key(name, led=None, label=None, W=1.1, H=1.0):
    """a glass Caps Lock key (as fkey): the outlined arrow of the stock key on its face, or a glowing
    label; led: True green light, False dark light, None no light"""
    D = 0.42
    k = box(name, 0, 0, H / 2, W, D, H, m_glass, 0.09)
    wire(k, name + "_wire")
    f = box(name + "_face", 0, -D / 2 - 0.01, H / 2 + 0.03, W - 0.2, 0.02, H - 0.26, glass_material("fk_face", ICE, 0.1), 0.05)
    wire(f, name + "_face_wire", m_core, 0.006)
    yf = -D / 2 - 0.03
    if label:
        t = glow_text(name + "_label", label, 0, yf, 0, H * 0.58, accent_glass("ck_label", srgb((60, 120, 255)), 2.8, 0.03), SANS_BOLD)
        bpy.context.view_layer.update()
        t.location.x = -W / 2 + 0.2
        t.location.z = H - 0.45
    else:
        s, x0, z0 = 0.3, -W / 2 + 0.38, H - 0.3       # the stock key's arrow: pointing down, outlined
        pts = [(-0.35, 0.5), (0.35, 0.5), (0.35, 0.05), (0.7, 0.05), (0, -0.6), (-0.7, 0.05), (-0.35, 0.05)]
        outline_curve(name + "_arrow", [(x0 + x * s, yf, z0 + z * s) for x, z in pts], 0.022, m_hot, closed=True)
    if led is not None:
        x, z = W / 2 - 0.25, H - 0.27
        sphere(name + "_led", x, yf, z, 0.07, accent_glass("ck_green", GREEN_LIT, 2.8, 0.03) if led else m_glass)
        torus(name + "_ledring", x, yf + 0.01, z, 0.09, 0.012, m_edge, axis="Y")


def nocapslock_c(sel, how):
    """CO14 NoCapsLock (user picked "a" 2026-11-23; Caps Lock does nothing): "a" = the glass Caps Lock key with its light on,
    selected: pressed, the light goes out; "b" = the key with a red no-sign in front, selected: pressed,
    the sign lit; "c" = a key with a capital A, selected: pressed, the label becomes a small a"""
    T, dn = 0.16, 0.13
    up, down = at(0, 0, T), at(0, 0, T - dn)
    turned(built(lambda: key_base("nc_base", 1.35)), TURN)
    if how == "a":
        moving(lambda: caps_key("nc_key", led=not sel), TURN @ up, TURN @ down, sel)
    elif how == "b":
        moving(lambda: caps_key("nc_key"), TURN @ up, TURN @ down, sel)
        red = accent_glass(f"nc_red{sel}", RED_HOT, 3.2 if sel else 1.6, 0.03)

        def sign():
            torus("nc_ring", 0, 0, 0, 0.36, 0.05, red, axis="Y")
            b = box("nc_bar", 0, 0, 0, 0.7, 0.07, 0.09, red, 0.02)
            b.rotation_euler.y = math.radians(45)
        turned(built(sign), TURN @ at(-0.12, -0.45, 0.72) @ Matrix.Scale(0.85, 4))
    else:
        moving(lambda: caps_key("nc_key", label="a" if sel else "A"), TURN @ up, TURN @ down, sel)


PROGRAMS.update({"nocapslock": lambda sel: nocapslock_c(sel, "a"),
                 "nocapslock_a": lambda sel: nocapslock_c(sel, "a"),
                 "nocapslock_b": lambda sel: nocapslock_c(sel, "b"),
                 "nocapslock_c": lambda sel: nocapslock_c(sel, "c")})


def info_sign(name, glow=1.8):
    """the glass info sign (as AutoInfo "b"): a disc in a glowing ring, a blue i on it; bottom at z = 0.02"""
    blue = accent_glass(f"{name}_blue{glow}", srgb((60, 120, 255)), glow, 0.03)
    cylinder(name + "_disc", 0, 0, 0.62, 0.6, 0.12, m_glass, axis="Y")
    torus(name + "_ring", 0, -0.07, 0.62, 0.6, 0.035, m_edge, axis="Y")
    box(name + "_stem", 0, -0.08, 0.5, 0.15, 0.06, 0.48, blue, 0.03)
    box(name + "_foot", 0.0, -0.08, 0.29, 0.3, 0.06, 0.06, blue, 0.01)
    sphere(name + "_dot", 0, -0.09, 0.9, 0.1, blue)


def rawbinfo_c(sel, how):
    """CO15 RAWBInfo (user picked "c" 2026-11-23; Workbench's Information window, made with ReAction): "a" = a window with the glass
    info sign in front, selected: the sign comes forward and glows; "b" = a glass page icon, selected: its
    Information window pops up beside it; "c" = an Information window with the info sign and three
    fields, selected: the first field lit blue (being edited)"""
    if how == "a":
        turned(built(lambda: tb_window("rw_win", 1.3, 1.15, True)), TURN @ at(0, 0.15, 0))
        moving(lambda: info_sign("rw_sign", 3.0 if sel else 1.6), TURN @ at(-0.05, -0.15, 0.12) @ Matrix.Scale(0.75, 4),
               TURN @ at(-0.05, -0.55, 0.1) @ Matrix.Scale(0.85, 4), sel)
    elif how == "b":
        turned(built(lambda: glass_page("rw_page")), TURN @ at(-0.4, 0.0, 0))

        def win():
            tb_window("rw_win", 0.95, 0.85, True)
            for o in objects:
                if o.name.startswith("rw_win_l"):
                    o.hide_render = True
            turned(built(lambda: info_sign("rw_sign", 2.2)), at(-0.22, -0.07, 0.12) @ Matrix.Scale(0.42, 4))
            for k in range(3):
                box(f"rw_f{k}", 0.2, -0.075, 0.55 - k * 0.16, 0.38, 0.01, 0.04, m_core, 0)
        Pw = TURN @ at(0.3, -0.25, 0.5)
        moving(win, Pw @ Matrix.Scale(0.02, 4), Pw, sel)
    else:
        W, H = 1.35, 1.2
        blue = accent_glass("rw_blue", srgb((60, 120, 255)), 2.2, 0.03)

        def win():
            tb_window("rw_win", W, H, True)
            for o in objects:
                if o.name.startswith("rw_win_l"):
                    o.hide_render = True
            turned(built(lambda: info_sign("rw_sign", 2.2)), at(-W / 2 + 0.3, -0.07, H - 0.62) @ Matrix.Scale(0.4, 4))
            for k in range(3):
                z = H - 0.4 - k * 0.22
                if sel and k == 0:
                    box("rw_field_lit", 0.2, -0.07, z, 0.75, 0.02, 0.15, blue, 0.01)
                fb = box(f"rw_field{k}", 0.2, -0.065, z, 0.75, 0.02, 0.15, m_glass, 0.01)
                wire(fb, f"rw_field{k}_wire", m_core, 0.005)
                box(f"rw_text{k}", 0.1, -0.09, z, 0.4 - 0.08 * k, 0.01, 0.035, m_hot if sel and k == 0 else m_core, 0)
        turned(built(win), TURN)


PROGRAMS.update({"rawbinfo": lambda sel: rawbinfo_c(sel, "c"),
                 "rawbinfo_a": lambda sel: rawbinfo_c(sel, "a"),
                 "rawbinfo_b": lambda sel: rawbinfo_c(sel, "b"),
                 "rawbinfo_c": lambda sel: rawbinfo_c(sel, "c")})


AMBER = srgb((235, 150, 60))


def sbe_desktop(yf, W, H, z0):
    """a small window on the monitor's screen (the desktop in use)"""
    b = box("sbe_dwin", -0.15, yf - 0.012, z0 + H * 0.55, W * 0.5, 0.012, H * 0.5, glass_material("sbe_dwin_g", ICE, 0.1), 0.01)
    wire(b, "sbe_dwin_wire", m_core, 0.006)
    box("sbe_dwin_title", -0.15, yf - 0.024, z0 + H * 0.55 + H * 0.25 - 0.06, W * 0.5 - 0.04, 0.01, 0.07,
        accent_glass("sbe_title_g", srgb((60, 120, 255)), 1.8, 0.03), 0)


def sbe_stars(yf, W, H, z0):
    """the blanked screen: dark, a few stars"""
    import random
    box("sbe_dark", 0, yf + 0.004, z0 + H / 2, W - 0.2, 0.006, H - 0.2, lacquer_material("sbe_dark"), 0.01)
    rnd = random.Random(7)
    for k in range(14):
        x = rnd.uniform(-W / 2 + 0.2, W / 2 - 0.2)
        z = rnd.uniform(z0 + 0.18, z0 + H - 0.18)
        s = rnd.choice((0.018, 0.026, 0.034))
        cylinder(f"sbe_star{k}", x, yf - 0.002, z, s, 0.01, m_hot if s > 0.03 else m_core, axis="Y", verts=12)


def roller_blind(name, W, L):
    """an amber glass roller blind: the roller (top at z = 0) and L of blind hanging down, a pull ring"""
    amber = accent_glass(name + "_amber", AMBER, 0.9, 0.06)
    r = cylinder(name + "_roller", 0, 0, -0.07, 0.07, W + 0.1, m_glass)
    r.rotation_euler = (0, math.pi / 2, 0)
    for sgn in (-1, 1):
        cylinder(f"{name}_cap{sgn}", sgn * (W / 2 + 0.07), 0, -0.07, 0.085, 0.05, m_hot, axis="X")
    b = box(name + "_blind", 0, -0.03, -0.07 - L / 2, W, 0.02, L, amber, 0.01)
    wire(b, name + "_blind_wire", m_hot, 0.006)
    for k in range(int(L / 0.14)):
        box(f"{name}_slat{k}", 0, -0.045, -0.15 - k * 0.14, W - 0.08, 0.008, 0.012, m_core, 0)
    box(name + "_bar", 0, -0.04, -0.07 - L, W + 0.02, 0.05, 0.05, m_glass, 0.01)
    torus(name + "_ring", 0, -0.04, -0.07 - L - 0.1, 0.07, 0.014, m_hot, axis="Y")


def screenblankerengine_c(sel, how):
    """CO16 ScreenBlankerEngine (user picked "a" 2026-11-23; blanks the screen when the computer is left alone): "a" = a glass monitor
    with an amber roller blind half down (as the stock icon), selected: the blind pulled down over the
    screen; "b" = the monitor showing a window, selected: the screen blanked, stars on it; "c" = as "b",
    and selected a glowing Zz in front of the starry screen"""
    W, H, z0 = 1.8, 1.25, 0.38
    if how == "a":
        turned(built(lambda: monitor("sbe_mon", sbe_desktop, W, H, z0=z0)), TURN)
        L = H - 0.16 if sel else H * 0.45
        turned(built(lambda: roller_blind("sbe_rb", W - 0.1, L)), TURN @ at(0, -0.14, z0 + H + 0.02))
        FRAME_EXTRA.extend(TURN @ Vector((x, 0, z)) for x in (-W / 2, W / 2) for z in (z0 + H - 0.16 - (H - 0.16) - 0.2, z0 + H + 0.1))
    else:
        turned(built(lambda: monitor("sbe_mon", sbe_stars if sel else sbe_desktop, W, H, z0=z0)), TURN)
        if how == "c" and sel:
            t = glow_text("sbe_zz", "Zz", 0, 0, 0, 0.5, m_hot, SANS_BOLD)
            turned([t], TURN @ at(0.1, -0.2, z0 + H * 0.5))


PROGRAMS.update({"screenblankerengine": lambda sel: screenblankerengine_c(sel, "a"),
                 "screenblankerengine_a": lambda sel: screenblankerengine_c(sel, "a"),
                 "screenblankerengine_b": lambda sel: screenblankerengine_c(sel, "b"),
                 "screenblankerengine_c": lambda sel: screenblankerengine_c(sel, "c")})
