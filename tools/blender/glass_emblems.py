"""glass_emblems.py: program emblems of the glass icon set, loaded by glass_icons.py into its namespace.

For a drawer that holds one program, the emblem is not a family tile but a small glass version of that
program's own icon, in its key colours as accents (the user, 2026-11-16: "use more colors on them so
they don't stray too much away from their original idea"). Rendered like the emblem tiles (ICON
emb_<name>: the tile camera and studio, no floor reflection, transparent). Public domain.
"""
import math

import bpy
from mathutils import Matrix, Vector

YELLOW = srgb((235, 190, 40))
RED_HOT = srgb((230, 30, 30))


def accent_glass(name, colour, glow, rough=0.04):
    """coloured glass that also glows a little from inside (the accent colours stay vivid on dark)"""
    m, nt = new_mat(name)
    n = nt.nodes
    g = n.new("ShaderNodeBsdfPrincipled")
    g.inputs["Base Color"].default_value = colour
    g.inputs["Transmission Weight"].default_value = 1.0
    g.inputs["Roughness"].default_value = rough
    g.inputs["IOR"].default_value = 1.45
    e = n.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = colour
    e.inputs["Strength"].default_value = glow
    add = n.new("ShaderNodeAddShader")
    nt.links.new(g.outputs[0], add.inputs[0])
    nt.links.new(e.outputs[0], add.inputs[1])
    finish(nt, add.outputs[0])
    return m


def boing_glass(name, red, white):
    """the Boing ball's 16 x 8 checker on a UV sphere, red and white glass"""
    m, nt = new_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    mp = n.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (8.0, 4.0, 1.0)
    ck = n.new("ShaderNodeTexChecker")
    ck.inputs["Scale"].default_value = 2.0
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], ck.inputs["Vector"])
    mix = n.new("ShaderNodeMixShader")
    nt.links.new(ck.outputs["Fac"], mix.inputs["Fac"])
    # copy the two accent shaders into this tree
    for src, slot in ((white, 1), (red, 2)):
        sn = src.node_tree.nodes
        g = n.new("ShaderNodeBsdfPrincipled")
        for key in ("Base Color", "Transmission Weight", "Roughness", "IOR"):
            g.inputs[key].default_value = sn["Principled BSDF"].inputs[key].default_value
        e = n.new("ShaderNodeEmission")
        e.inputs["Color"].default_value = sn["Emission"].inputs["Color"].default_value
        e.inputs["Strength"].default_value = sn["Emission"].inputs["Strength"].default_value
        ad = n.new("ShaderNodeAddShader")
        nt.links.new(g.outputs[0], ad.inputs[0])
        nt.links.new(e.outputs[0], ad.inputs[1])
        nt.links.new(ad.outputs[0], mix.inputs[slot])
    finish(nt, mix.outputs[0])
    return m


def boing_solid(name):
    """the Boing ball's 16 x 8 checker, opaque and glossy (the user: no transparency on the ball), red
    and white with a clear coat, a little light of their own so they stay bright on dark backdrops"""
    m, nt = new_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    mp = n.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (8.0, 4.0, 1.0)
    ck = n.new("ShaderNodeTexChecker")
    ck.inputs["Scale"].default_value = 2.0
    ck.inputs["Color1"].default_value = srgb((210, 10, 10))
    ck.inputs["Color2"].default_value = srgb((245, 245, 245))
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], ck.inputs["Vector"])
    b = n.new("ShaderNodeBsdfPrincipled")
    nt.links.new(ck.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.25
    b.inputs["Coat Weight"].default_value = 1.0
    b.inputs["Coat Roughness"].default_value = 0.03
    e = n.new("ShaderNodeEmission")
    nt.links.new(ck.outputs["Color"], e.inputs["Color"])
    e.inputs["Strength"].default_value = 0.25
    add = n.new("ShaderNodeAddShader")
    nt.links.new(b.outputs[0], add.inputs[0])
    nt.links.new(e.outputs[0], add.inputs[1])
    finish(nt, add.outputs[0])
    return m


def e_python():
    """Python: the red and white Boing ball (opaque and glossy, the user) with a yellow glass ring round
    it (the program's own icon), tilted"""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=0.6, location=(0, 0, 0.55))
    ball = bpy.context.object
    ball.name = "py_ball"
    ball.rotation_euler = (math.radians(20), math.radians(-25), math.radians(15))
    bpy.ops.object.shade_smooth()
    register(ball, boing_solid("py_boing"))                               # opaque, glossy (user)
    ring_m = accent_glass("py_ring", YELLOW, 0.6, 0.05)
    r = torus("py_ring", 0, 0, 0.55, 0.86, 0.07, ring_m)
    r.rotation_euler = (math.radians(16), math.radians(-24), 0)            # round its middle, tilted
    g = torus("py_ring_glow", 0, 0, 0.55, 0.86, 0.018, emission_material("py_ring_hot", srgb((255, 215, 70)), 3.0))
    g.rotation_euler = (math.radians(16), math.radians(-24), 0)


def e_amiupdate():
    """AmiUpdate: a glass gear with a glossy red glass button in its middle (the program's own icon)"""
    R, r, teeth, t = 0.72, 0.56, 8, 0.22                 # 8 teeth, as the AmiUpdate icon
    pts = []
    for i in range(teeth * 4):
        a = (i / (teeth * 4)) * 2 * math.pi
        rr = R if (i % 4) in (1, 2) else r
        pts.append((rr * math.cos(a), 0.55 + rr * math.sin(a)))
    prism("au_gear", pts, -t / 2, t / 2, m_glass)
    outline_curve("au_gear_edge_f", [(x, -t / 2 - 0.004, z) for x, z in pts], 0.012, m_edge)
    outline_curve("au_gear_edge_b", [(x, t / 2 + 0.004, z) for x, z in pts], 0.008, m_core)
    torus("au_seat", 0, -t / 2 - 0.02, 0.55, 0.3, 0.04, m_glass, axis="Y")
    torus("au_seat_glow", 0, -t / 2 - 0.05, 0.55, 0.31, 0.012, m_hot, axis="Y")
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=0.27, location=(0, -t / 2 - 0.02, 0.55))
    b = bpy.context.object
    b.name = "au_button"
    b.scale = (1, 0.55, 1)
    bpy.ops.object.shade_smooth()
    register(b, accent_glass("au_red", RED_HOT, 1.6, 0.03))


ORANGE = srgb((215, 120, 40))
GREEN_LIT = srgb((40, 210, 90))


def em_page(name, art):
    """a standing glass page with a folded corner (the program icons' page), turned to the viewer; art()
    draws on its front (y = -0.03, page bottom at z = 0.05)"""
    w, h, fold = 0.78, 0.98, 0.2
    outline = [(-w / 2, 0.05), (w / 2, 0.05), (w / 2, 0.05 + h - fold), (w / 2 - fold, 0.05 + h), (-w / 2, 0.05 + h)]
    paper = accent_glass(name + "_g", srgb((240, 244, 250)), 0.55, 0.18)       # frosted white: a white page
    parts = [prism(name, outline, -0.025, 0.025, paper),
             outline_curve(name + "_edge", [(x, -0.03, z) for x, z in outline], 0.01, m_edge)]
    tri = [(w / 2 - fold, 0.05 + h), (w / 2, 0.05 + h - fold), (w / 2 - fold, 0.05 + h - fold)]
    parts.append(prism(name + "_fold", tri, -0.05, -0.025, m_glass))
    parts += built(art)
    turned(parts, rot("Z", -18))


def em_magnifier(name):
    """a glass magnifier standing in front of the page, its handle (orange glass, as on the program
    icons) down to the right"""
    def fn():
        sphere(name + "_lens", 0, 0, 0, 0.22, glass_material(name + "_lens_g", LIGHTBLUE, 0.0), scale=(1, 0.2, 1))
        torus(name + "_rim", 0, 0, 0, 0.24, 0.035, m_glass, axis="Y")
        torus(name + "_rim_glow", 0, -0.04, 0, 0.24, 0.011, m_hot, axis="Y")
        h = cylinder(name + "_handle", 0, 0, 0, 0.05, 0.36, accent_glass(name + "_handle_g", ORANGE, 0.5))
        turned([h], rot("Y", 135) @ at(0, 0, 0.42))
    turned(built(fn), at(0.33, -0.25, 0.3) @ rot("Z", -18))


# the PDF swirl's centre line, traced from the user's reference picture (2026-11-16; 512 px picture
# coordinates, y down), in drawing order: the top tip, down its right side, through the crossings, round
# the lower left loop, along the band out to the right loop, back, and up the top loop's left side
SWIRL_PTS = [(246, 112), (256, 120), (260, 138), (257, 160), (251, 180), (245, 193), (237, 207), (230, 220),
       (224, 233), (218, 247), (208, 265), (193, 283), (177, 294), (166, 297), (159, 290), (162, 278),
       (174, 264), (193, 251), (213, 241), (230, 234), (246, 229), (264, 224), (282, 219), (302, 216),
       (322, 215), (339, 218), (349, 226), (351, 236), (343, 244), (328, 246), (311, 243), (295, 236),
       (282, 227), (270, 216), (259, 204), (250, 191), (242, 176), (236, 158), (233, 139), (235, 123), (240, 114)]


def swirl_pts(cx, cz, size, y):
    """the PDF swirl as on the AmiPDF and AmiGS icons (a closed Catmull-Rom spline through SWIRL_PTS),
    size wide, centred on cx, cz, on the plane y"""
    P = [Vector((x, yy, 0)) for x, yy in SWIRL_PTS]
    xs, ys = [v.x for v in P], [v.y for v in P]
    mx, my = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    k = size / (max(xs) - min(xs))
    m = len(P)
    out = []
    for i in range(m):
        p0, p1, p2, p3 = P[(i - 1) % m], P[i], P[(i + 1) % m], P[(i + 2) % m]
        for j in range(8):
            t = j / 8
            q = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                       (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)
            out.append((cx + (q.x - mx) * k, y, cz - (q.y - my) * k))
    return out


def doc_viewer(prefix, label):
    """AmiPDF and AmiGS share their icon (the user): a white glass page with the red PDF swirl, a red
    label (PDF / PS), a magnifier in front"""
    def art():
        red = accent_glass(prefix + "_red", srgb((210, 10, 10)), 1.8)
        outline_curve(prefix + "_swirl", swirl_pts(-0.02, 0.66, 0.46, -0.034), 0.022, red, closed=True)
        t = glow_text(prefix + "_label", label, 0, -0.034, 0.25, 0.2, emission_material(prefix + "_label_m", srgb((220, 30, 30)), 2.0))
        t.location.x -= t.dimensions.x / 2 + 0.17
    em_page(prefix + "_page", art)
    em_magnifier(prefix + "_mag")


def e_amipdf():
    """AmiPDF: the page with the PDF swirl and a PDF label, a magnifier in front (the program's own icon)"""
    doc_viewer("pdf", "PDF")


def e_amigs():
    """AmiGS (Ghostscript's viewer): the same page and swirl with a PS label (the program's own icon)"""
    doc_viewer("ps", "PS")


def e_sgrab():
    """SGrab (screen grabber): a clear glass camera with a deep blue glass lens (the program's own icon)"""
    def fn():
        b = box("cam_body", 0, 0, 0.45, 1.25, 0.42, 0.72, glass_material("cam_body_g", srgb((225, 232, 242)), 0.06), 0.1)
        wire(b, "cam_body_wire")
        hm = box("cam_hump", -0.22, 0, 0.88, 0.42, 0.34, 0.16, m_glass, 0.05)
        wire(hm, "cam_hump_wire", m_edge, 0.008)
        cylinder("cam_button", 0.36, 0, 0.84, 0.07, 0.06, m_hot)
        box("cam_flash", 0.4, -0.215, 0.68, 0.2, 0.012, 0.1, emission_material("cam_flash_m", srgb((245, 250, 255)), 3.0), 0)
        cylinder("cam_lens", 0, -0.24, 0.42, 0.25, 0.14, glass_material("cam_lens_g", srgb((20, 40, 110)), 0.02), axis="Y")
        torus("cam_lens_ring", 0, -0.31, 0.42, 0.26, 0.035, m_glass, axis="Y")
        torus("cam_lens_glow", 0, -0.33, 0.42, 0.26, 0.01, m_hot, axis="Y")
        sphere("cam_glint", -0.07, -0.33, 0.49, 0.045, emission_material("cam_glint_m", srgb((120, 170, 255)), 4.0))
        torus("cam_lens_inner", 0, -0.32, 0.42, 0.13, 0.008, accent_glass("cam_blue", srgb((60, 110, 255)), 2.0))
    turned(built(fn), rot("Z", -18))


def e_ghostscript():
    """Ghostscript: a glass printer with green-lit paper (its drawer's own icon; there is no program icon)"""
    def fn():
        b = box("gs_body", 0, 0, 0.3, 1.25, 0.8, 0.5, m_glass, 0.06)
        wire(b, "gs_body_wire")
        p = box("gs_paper", 0, 0.12, 0.72, 0.72, 0.03, 0.5, accent_glass("gs_green", GREEN_LIT, 1.2), 0.01)
        wire(p, "gs_paper_wire", emission_material("gs_paper_edge", srgb((120, 255, 160)), 2.5), 0.008)
        box("gs_slot", 0, -0.405, 0.38, 0.8, 0.01, 0.04, m_hot, 0)
        box("gs_tray", 0, -0.5, 0.08, 0.8, 0.22, 0.03, m_glass, 0.01)
        for k in range(2):
            cylinder(f"gs_btn{k}", 0.42 + k * 0.12, -0.25, 0.555, 0.035, 0.02, m_hot if k == 0 else m_core)
    turned(built(fn), rot("Z", -18))


EMBLEMS = {"python": e_python, "amiupdate": e_amiupdate, "amipdf": e_amipdf, "amigs": e_amigs,
           "sgrab": e_sgrab, "ghostscript": e_ghostscript}
