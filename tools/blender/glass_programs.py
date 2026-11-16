"""glass_programs.py: the programs of the glass icon set (group 4), loaded by glass_icons.py into its
own namespace (it uses that script's materials and helpers: box, wire, prism, cylinder, torus, ...).

Each program is a glass object of its own; its selected image moves one part (the user, 2026-11-16).
The moving part is placed by moving(), which frames both of its positions in both images, so the rest
of the object stays exactly still between them. Public domain.
"""
import math

import bpy
from mathutils import Matrix, Vector

TURN = Matrix.Rotation(math.radians(-24), 4, "Z")      # flat objects turned towards the camera


def turned(objs, m):
    """place already built objects by m (they were built around the origin)"""
    bpy.context.view_layer.update()
    for o in objs:
        o.matrix_world = m @ o.matrix_world
    return objs


def built(fn):
    """the objects fn() makes"""
    start = len(objects)
    fn()
    return objects[start:]


def moving(fn, m0, m1, selected):
    """the moving part made by fn() (around the origin), placed by m0 in the normal image and by m1 in
    the selected one; the framing includes both places"""
    part = built(fn)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    for o in part:
        if o.type != "MESH" or o.hide_render:
            continue
        for c in o.evaluated_get(deps).bound_box:
            p = o.matrix_world @ Vector(c)
            FRAME_EXTRA.extend((m0 @ p, m1 @ p))
    return turned(part, m1 if selected else m0)


def rot(axis, deg):
    return Matrix.Rotation(math.radians(deg), 4, axis)


def at(x, y, z):
    return Matrix.Translation((x, y, z))


def aim(d):
    """a turn that points +z along d"""
    return Vector(d).normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()


def sphere(name, x, y, z, r, mat, scale=(1, 1, 1), segs=64):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=segs // 2, radius=r, location=(x, y, z))
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    bpy.ops.object.shade_smooth()
    return register(o, mat)


def shell_part(o, wall):
    """make o a shell with walls wall thick"""
    so = o.modifiers.new("walls", "SOLIDIFY")
    so.thickness = wall
    so.offset = -1
    so.use_even_offset = True
    return o


def cut_faces(o, keep):
    """keep only the faces whose centre passes keep(centre)"""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not keep(f.calc_center_median())], context="FACES")
    bm.to_mesh(o.data)
    bm.free()
    return o


def line(name, pts, mat=None, thickness=0.018):
    return outline_curve(name, pts, thickness, mat or m_hot, closed=False)


def pen(name, length=1.25, r=0.065, sides=32):
    """a glass pen along +z, its glowing tip at the origin, a line of light inside"""
    bpy.ops.mesh.primitive_cone_add(vertices=sides, radius1=0.004, radius2=r, depth=0.2, location=(0, 0, 0.1))
    tip = bpy.context.object
    tip.name = name + "_tip"
    bpy.ops.object.shade_smooth()
    register(tip, m_hot)
    body = cylinder(name + "_body", 0, 0, 0.2 + length / 2, r, length, m_glass, verts=sides)
    if sides < 12:
        wire(body, name + "_wire", thickness=0.01)
    for k, z in enumerate((0.2, 0.2 + length * 0.78, 0.2 + length)):
        torus(f"{name}_ring{k}", 0, 0, z, r + 0.004, 0.011, m_edge)
    cylinder(name + "_core", 0, 0, 0.2 + length / 2, 0.016, length * 0.96, m_core, verts=16)


def seven(name, digit, x, z, w, h, y, mat):
    """a seven-segment digit centred at x, z on the plane y"""
    segs = {0: "abcdef", 1: "bc", 2: "abged", 3: "abgcd", 4: "fgbc", 5: "afgcd", 6: "afgedc", 7: "abc",
            8: "abcdefg", 9: "abcdfg"}[digit]
    t = w * 0.2
    pos = {"a": (x, z + h / 2, w, t), "g": (x, z, w, t), "d": (x, z - h / 2, w, t),
           "f": (x - w / 2, z + h / 4, t, h / 2), "b": (x + w / 2, z + h / 4, t, h / 2),
           "e": (x - w / 2, z - h / 4, t, h / 2), "c": (x + w / 2, z - h / 4, t, h / 2)}
    for s in segs:
        cx, cz, sx, sz = pos[s]
        box(f"{name}{s}", cx, y, cz, sx * 0.86 if s in "agd" else sx, 0.012, sz * 0.86 if s in "fbec" else sz,
            mat, 0)


# --- the programs ------------------------------------------------------------------------------

def shell(sel):
    """PR01 Shell: a glass terminal on a plinth, a glowing prompt; selected: a command typed, its output,
    the cursor on a new prompt line"""
    W, H, T, z0 = 1.9, 1.3, 0.16, 0.36
    yf = -T / 2 - 0.006

    def body():
        b = box("plinth", 0, 0.06, 0.08, 1.15, 0.72, 0.16, m_glass, 0.04)
        wire(b, "plinth_wire", thickness=0.012)
        box("neck", 0, 0.08, 0.26, 0.34, 0.14, 0.22, m_glass, 0.02)
        s = box("screen", 0, 0, z0 + H / 2, W, T, H, m_glass, 0.05)
        wire(s, "screen_wire")
        i = 0.1
        outline_curve("bezel", [(-W / 2 + i, yf, z0 + i), (W / 2 - i, yf, z0 + i), (W / 2 - i, yf, z0 + H - i),
                                (-W / 2 + i, yf, z0 + H - i)], 0.008, m_core)
        xl = -W / 2 + 0.26
        rows = [z0 + H - 0.32 - k * 0.25 for k in range(4)]

        def prompt(k):
            line(f"prompt{k}", [(xl, yf, rows[k] + 0.075), (xl + 0.1, yf, rows[k]), (xl, yf, rows[k] - 0.075)])

        def bar(name, x, k, ln, mat):
            box(name, x + ln / 2, yf, rows[k], ln, 0.012, 0.065, mat, 0)

        prompt(0)
        if not sel:
            bar("cursor", xl + 0.2, 0, 0.13, m_hot)
        else:
            bar("cmd0", xl + 0.2, 0, 0.36, m_core)
            bar("cmd1", xl + 0.64, 0, 0.24, m_core)
            bar("out0", xl, 1, 1.05, m_edge)
            bar("out1", xl, 2, 0.7, m_edge)
            prompt(3)
            bar("cursor", xl + 0.2, 3, 0.13, m_hot)
    turned(built(body), TURN)


def multiview(sel):
    """PR02 MultiView: a glass eye in a ring on a stand; selected: the smoked glass lids open wide"""
    R = 0.72
    zc = R + 0.46
    E = TURN @ at(0, 0, zc)

    def body():
        cylinder("eye_stand", 0, 0, 0.06, 0.55, 0.12, m_glass)
        torus("eye_stand_rim", 0, 0, 0.12, 0.55, 0.012, m_edge)
        cylinder("eye_neck", 0, 0, 0.27, 0.07, 0.3, m_glass)

    def eye():
        sphere("eyeball", 0, 0, 0, R, m_glass)
        ri = 0.46 * R
        yi = -math.sqrt(R * R - ri * ri)
        torus("iris", 0, yi - 0.004, 0, ri, 0.022, m_hot, axis="Y")
        torus("iris2", 0, yi * 0.97, 0, ri * 0.6, 0.012, m_edge, axis="Y")
        for k in range(12):
            a = k / 12 * 2 * math.pi
            r0, r1 = ri * 0.66, ri * 0.92
            p0 = Vector((r0 * math.cos(a), 0, r0 * math.sin(a)))
            p1 = Vector((r1 * math.cos(a), 0, r1 * math.sin(a)))
            p0.y = -math.sqrt(R * R - r0 * r0) - 0.006
            p1.y = -math.sqrt(R * R - r1 * r1) - 0.006
            line(f"iris_ray{k}", [tuple(p0), tuple(p1)], m_core, 0.007)
        cylinder("pupil", 0, -R + 0.03, 0, 0.17 * R, 0.05, lacquer_material("pupil"), axis="Y")
        torus("eye_ring", 0, 0.05, 0, R * 1.2, 0.05, m_glass, axis="Y")
        torus("eye_ring_glow", 0, -0.0, 0, R * 1.2, 0.014, m_edge, axis="Y")
        torus("eye_ring_glow2", 0, 0.1, 0, R * 1.2, 0.008, m_core, axis="Y")
    turned(built(body), TURN)
    turned(built(eye), E)

    smoke = glass_material("lid_black", srgb((8, 10, 15)), 0.03)       # black glass (user): the eye focuses

    def lid(upper):
        def fn():
            o = sphere("lid_up" if upper else "lid_down", 0, 0, 0, R * 1.07, smoke)
            cut_faces(o, (lambda c: c.z > 0.001) if upper else (lambda c: c.z < -0.001))
            shell_part(o, 0.035)
            torus("lid_rim_up" if upper else "lid_rim_down", 0, 0, 0, R * 1.07, 0.016, m_hot)
        return fn
    # the front edge of a lid sits at elevation -a (degrees) after a turn by a about x
    for upper, a0, a1 in ((True, -12, -62), (False, 12, 62)):
        moving(lid(upper), E @ rot("X", a0), E @ rot("X", a1), sel)


def notepad(sel):
    """PR03 NotePad: a glass note pad with a spiral, leaning back, a pen lying on it; selected: the pen
    stands up, writing"""
    W, H, T = 1.25, 1.6, 0.1
    P = TURN @ rot("X", -14)                          # the pad leans back

    def body():
        b = box("pad", 0, 0, H / 2, W, T, H, m_glass, 0.03)
        wire(b, "pad_wire")
        yf = -T / 2 - 0.006
        for k in range(6):
            z = 0.28 + k * 0.17
            box(f"pad_line{k}", 0, yf, z, W - 0.3, 0.01, 0.028, m_core, 0)
        box("pad_rule", -W / 2 + 0.22, yf - 0.002, 0.75, 0.018, 0.01, 1.05, m_edge, 0)
        for k in range(7):
            o = torus(f"spiral{k}", -W / 2 + 0.17 + k * 0.152, 0, H - 0.01, 0.075, 0.014, m_edge)
            o.rotation_euler = (0, math.pi / 2, 0)
    turned(built(body), P)
    lie = at(0.38, -T / 2 - 0.075, 0.3) @ rot("Y", -36)
    write = at(-0.37, -T / 2 - 0.004, 1.13) @ aim((0.55, -0.75, 0.3))    # starting the first line (user)
    moving(lambda: pen("pen"), P @ lie, P @ write, sel)


def clock(sel):
    """PR04 Clock: a glass alarm clock with glowing hands; selected: the hands have moved on"""
    R, T = 0.82, 0.36
    zc = R + 0.2
    C = TURN @ at(0, 0, zc)
    yf = -T / 2 - 0.006

    def body():
        cylinder("clock_body", 0, 0, 0, R, T, m_glass, axis="Y")
        for k, (y, mat) in enumerate(((-T / 2, m_edge), (T / 2, m_core))):
            torus(f"clock_rim{k}", 0, y, 0, R, 0.014, mat, axis="Y")
        torus("clock_face", 0, yf, 0, R * 0.86, 0.008, m_core, axis="Y")
        for k in range(12):
            big = k % 3 == 0
            tk = box(f"tick{k}", 0, yf, 0, 0.045 if big else 0.03, 0.012, 0.15 if big else 0.08, m_hot if big else m_core, 0)
            turned([tk], rot("Y", k * 30) @ at(0, 0, R * 0.72))
        for s in (-1, 1):
            a = math.radians(38)
            sphere(f"foot{s}", s * 0.42, 0, -zc + 0.16, 0.16, m_glass)
            b = sphere(f"bell{s}", 0, 0, 0, 0.3, m_glass)
            cut_faces(b, lambda c: c.z > -0.02)
            shell_part(b, 0.04)
            turned([b], at(s * R * math.sin(a) * 1.02, 0, R * math.cos(a) * 1.02) @ rot("Y", s * 38))
            rim = torus(f"bell_rim{s}", 0, 0, 0, 0.3, 0.012, m_edge)
            turned([rim], at(s * R * math.sin(a) * 1.02, 0, R * math.cos(a) * 1.02) @ rot("Y", s * 38))
        cylinder("clock_hub", 0, yf - 0.01, 0, 0.06, 0.03, m_hot, axis="Y")
    turned(built(body), C)

    def hand(name, deg, length, width, mat):
        h = box(name, 0, yf - 0.012, length / 2 - 0.06, width, 0.012, length, mat, 0)
        turned([h], C @ rot("Y", deg))
    hh, mm, ss = (10, 10, 0) if not sel else (10, 40, 30)
    hand("hour", (hh + mm / 60) * 30, R * 0.5, 0.06, m_hot)
    hand("minute", mm * 6, R * 0.72, 0.042, m_hot)
    hand("second", ss * 6, R * 0.78, 0.014, m_edge)


def calculator(sel):
    """PR05 Calculator: a glass calculator leaning back, a display and a grid of keys; selected: the =
    key pressed down (and the display shows the result)"""
    W, H, T = 1.2, 1.7, 0.16
    P = TURN @ rot("X", -16)
    yf = -T / 2

    def body():
        b = box("calc", 0, 0, H / 2, W, T, H, m_glass, 0.05)
        wire(b, "calc_wire")
        d = box("display", 0, yf - 0.012, H - 0.3, W - 0.22, 0.024, 0.34, glass_material("display", ICE, 0.08), 0.01)
        wire(d, "display_wire", m_core, 0.008)
        digits = (3, 0) if not sel else (4, 2)
        for k, dg in enumerate(digits):
            seven(f"digit{k}_", dg, 0.14 + k * 0.26, H - 0.3, 0.16, 0.22, yf - 0.028, m_hot)
        for r in range(4):
            for c in range(4):
                if (r, c) == (3, 3):
                    continue
                k = box(f"key{r}{c}", -0.405 + c * 0.27, yf - 0.035, 0.27 + (3 - r) * 0.255, 0.2, 0.07, 0.17, m_glass, 0.02)
                wire(k, f"key{r}{c}_wire", m_core, 0.006)
    turned(built(body), P)

    def equals():
        k = box("key_eq", 0, 0, 0, 0.2, 0.07, 0.17, m_glass, 0.02)
        wire(k, "key_eq_wire", m_edge, 0.009)
        for dz in (-0.025, 0.025):
            box(f"eq_bar{dz}", 0, -0.04, dz, 0.1, 0.01, 0.022, m_hot, 0)
    up = at(-0.405 + 3 * 0.27, yf - 0.035, 0.27)
    moving(equals, P @ up, P @ at(0, 0.055, 0) @ up, sel)


def find(sel):
    """PR06 Find: a magnifying glass lying on a small page; selected: lifted and turned towards the
    viewer"""
    def page():
        p = box("find_page", 0, 0.85, 0.03, 1.3, 1.7, 0.05, m_glass, 0.02)
        wire(p, "find_page_wire", thickness=0.01)
        for k in range(6):
            box(f"find_line{k}", -0.08 if k % 2 else 0, 0.3 + k * 0.24, 0.062, 0.95 if k % 2 else 1.05, 0.11, 0.012, m_core, 0)
    turned(built(page), TURN @ at(0, -0.85, 0) @ rot("X", 16))

    def glass():
        sphere("lens", 0, 0, 0, 0.47, glass_material("lens", LIGHTBLUE, 0.0), scale=(1, 1, 0.16))
        torus("lens_rim", 0, 0, 0, 0.5, 0.05, m_glass)
        torus("lens_rim_glow", 0, 0, 0.0, 0.5, 0.014, m_hot)
        h = cylinder("handle", 0, 0, 0, 0.075, 0.8, m_glass)
        turned([h], at(0, -0.98, 0) @ rot("X", 90))
        c = torus("collar", 0, 0, 0, 0.085, 0.016, m_edge)
        turned([c], at(0, -0.6, 0) @ rot("X", 90))
        c = torus("handle_end", 0, 0, 0, 0.075, 0.014, m_edge)
        turned([c], at(0, -1.38, 0) @ rot("X", 90))
        cy = cylinder("handle_core", 0, 0, 0, 0.018, 0.74, m_core, verts=16)
        turned([cy], at(0, -0.98, 0) @ rot("X", 90))
    lie = TURN @ at(0, -0.85, 0) @ rot("X", 16) @ at(0, 0.9, 0.14) @ rot("Z", 35)   # flat on the sloping page
    lift = TURN @ at(0.0, -0.35, 1.05) @ rot("Z", 35) @ rot("X", 58)
    moving(glass, lie, lift, sel)


def format_(sel):
    """PR07 Format: a hollow glass drive with a floppy half inserted; selected: the floppy slid in"""
    W, D, H = 1.9, 1.5, 0.6
    zs = H * 0.55
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, H / 2))
    drv = bpy.context.object
    drv.name = "fdrive"
    drv.scale = (W, D, H)
    bpy.ops.object.transform_apply(scale=True)
    shell_part(drv, 0.04)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -D / 2, zs))
    cut = bpy.context.object
    cut.name = "slot_cutter"
    cut.scale = (1.26, 0.3, 0.1)
    bpy.ops.object.transform_apply(scale=True)
    cut.hide_render = True
    b = drv.modifiers.new("slot", "BOOLEAN")
    b.operation = "DIFFERENCE"
    b.object = cut
    bv = drv.modifiers.new("bevel", "BEVEL")
    bv.width = 0.02
    bv.segments = 3
    bv.limit_method = "NONE"
    for f in drv.data.polygons:
        f.use_smooth = True
    register(drv, m_glass)
    wire(drv, "fdrive_wire")
    yf = -D / 2 - 0.006
    outline_curve("slot_glow", [(-0.63, yf, zs - 0.05), (0.63, yf, zs - 0.05), (0.63, yf, zs + 0.05),
                                (-0.63, yf, zs + 0.05)], 0.008, m_hot)
    cylinder("fdrive_led", 0.75, yf - 0.005, 0.14, 0.045, 0.03, m_hot, axis="Y")
    box("fdrive_eject", 0.72, yf - 0.01, H * 0.82, 0.16, 0.03, 0.06, m_core, 0.01)

    def floppy_disk():
        p = box("disk", 0, 0, 0, 1.12, 1.18, 0.05, glass_material("disk_glass", ICE, 0.06), 0.015)
        wire(p, "disk_wire", thickness=0.009)
        box("disk_shutter", 0, 0.47, 0, 0.5, 0.22, 0.062, lacquer_material("disk_shutter"), 0.008)
        box("disk_label", 0, -0.32, 0.03, 0.8, 0.46, 0.008, m_core, 0)
        torus("disk_hub", 0, 0.05, 0.03, 0.14, 0.01, m_edge)
    moving(floppy_disk, at(0, -D / 2, zs), at(0, -D / 2 + 0.44, zs), sel)


def help_(sel):
    """PR08 Help: a closed glass book with a glowing ? on its cover; selected: the cover opened"""
    W, H, T, c = 1.2, 1.6, 0.34, 0.05

    def body():
        b = box("book_back", 0, T / 2 - c / 2, H / 2, W, c, H, m_glass, 0.015)
        wire(b, "book_back_wire", thickness=0.01)
        p = box("book_pages", 0.02, 0, H / 2, W - 0.08, T - 2 * c, H - 0.08, glass_material("pages", ICE, 0.12), 0.01)
        wire(p, "book_pages_wire", m_core, 0.007)
        s = box("book_spine", -W / 2 - 0.035, 0, H / 2, 0.07, T, H, m_glass, 0.02)
        wire(s, "book_spine_wire", thickness=0.01)
        yp = -T / 2 + c - 0.006
        for k in range(6):
            box(f"page_line{k}", 0.05, yp, 0.35 + k * 0.17, W - 0.4 if k % 3 else W - 0.6, 0.01, 0.03, m_core, 0)
    turned(built(body), TURN)

    def cover():
        cv = box("book_cover", W / 2, 0, H / 2, W, c, H, m_glass, 0.015)
        wire(cv, "book_cover_wire", thickness=0.012)
        yf = -c / 2 - 0.006
        i = 0.12
        outline_curve("cover_frame", [(i, yf, i), (W - i, yf, i), (W - i, yf, H - i), (i, yf, H - i)], 0.008, m_core)
        cx, cz, r = W / 2, 1.0, 0.24
        hook = [(cx + r * math.cos(math.radians(a)), yf, cz + r * math.sin(math.radians(a))) for a in range(165, -91, -15)]
        hook += [(cx, yf, cz - r - 0.12), (cx, yf, 0.6)]
        line("question", hook, m_hot, 0.045)
        cylinder("question_dot", cx, yf, 0.44, 0.055, 0.03, m_hot, axis="Y")
    hinge = TURN @ at(-W / 2, -T / 2 + c / 2, 0)
    moving(cover, hinge, hinge @ rot("Z", -30), sel)           # opened 30 degrees (user)


def iconedit(sel):
    """PR09 IconEdit: a glass board of pixels, an arrow pointer drawn in light, a glowing pencil;
    selected: the pencil moved on and one more pixel lit"""
    N, s, g = 6, 0.22, 0.035
    P = TURN @ rot("X", -10)
    top = 1.78
    head = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (2, 0)]
    tail = [(2, 2), (3, 3), (4, 4)] + ([(5, 5)] if sel else [])
    lit = set(head + tail)

    def pos(r, c):
        return Vector((-(N * s + (N - 1) * g) / 2 + s / 2 + c * (s + g), -0.09, top - s / 2 - r * (s + g)))

    def body():
        b = box("board", 0, 0, 0.98, 1.75, 0.08, 1.85, m_glass, 0.03)
        wire(b, "board_wire")
        for r in range(N):
            for c in range(N):
                p = pos(r, c)
                if (r, c) in lit:
                    box(f"px{r}{c}", p.x, p.y, p.z, s, 0.1, s, m_core, 0.012)
                else:
                    q = box(f"px{r}{c}", p.x, p.y, p.z, s, 0.1, s, m_glass, 0.012)
                    wire(q, f"px{r}{c}_wire", m_edge, 0.005)
    turned(built(body), P)
    d = aim((0.45, -0.75, 0.5))
    m0 = at(*(pos(4, 4) + Vector((0, -0.05, 0)))) @ d
    m1 = at(*(pos(5, 5) + Vector((0, -0.05, 0)))) @ d
    moving(lambda: pen("pencil", 1.1, 0.07, sides=6), P @ m0, P @ m1, sel)


def unarc(sel):
    """PR10 UnArc: the open glass crate (lid thrown back); selected: the small crate on top risen out"""
    archive(True, lid=100, rise=(1.05 if sel else 0.0), rise_frame=1.05)


PROGRAMS = {"shell": shell, "multiview": multiview, "notepad": notepad, "clock": clock,
            "calculator": calculator, "find": find, "format": format_, "help": help_,
            "iconedit": iconedit, "unarc": unarc}
