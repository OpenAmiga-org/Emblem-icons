"""glass_icons.py: the glass icon set (glenz glass, glowing light-blue hairline edges), Cycles.

    blender -b --factory-startup --python tools/blender/glass_icons.py -- ICON OUT.png [SIZE] [SAMPLES] [ARGS]

ICON  drawer | drawer_open | file | file_open | device | archive | archive_open | prefs | tool | tool_open | ...
      programs (group 4, tools/blender/glass_programs.py): shell, multiview, notepad, clock, calculator,
      find, format, help, iconedit, unarc; Prefs editors (tools/blender/glass_prefs.py): ahi, amigainput,
      asl, compatibility, console, deficons, dos, fontprefs, gui, input, internet, locale, notifications,
      palette, picasso96, pointer, popupmenu, printer, printergfx, printerps, screenblanker,
      screenmode, screens, serial, sound, time, timezone, uboot, updates, url, usbprefs, wbpattern,
      wbstartup, workbench; Utilities/System (tools/blender/glass_utils.py): filecompare, graphicdump,
      initprinter, installer, keyshow, logviewer, memacs, partitionwizard, ...; each also <name>_open
      (<icon>_open: the selected image, the moving part moved: drawer pulled out, the page split in
      two and its front half opened (env FILE_OPEN degrees), the crate's lid opened (env ARCHIVE_LID))
      gem RRGGBB SYMBOL.png   (an emblem: a glass tile of that colour with the symbol glowing inside;
                               the arguments come before OUT.png)
OUT   a transparent PNG (SIZE x SIZE, default 512); bloom and scaling: tools/glass_sheet.py

The objects face down right: the camera looks from the front left. Base colours only: light blue
(hue 210: the glass tint and the emitted light), white (hot highlights), black (the studio). Base
icons stand on a mirror floor: mirrored copies below z = 0 fade out with depth.
Public domain.
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
ICON = argv[0]
GEM = ICON == "gem" or ICON.startswith("emb_")       # emb_<name>: a program emblem (glass_emblems.py)
# "<icon>_lit": the selected image of a device: the same object, framed alike, lit from inside
LIT = ICON.endswith("_lit")
if LIT:
    ICON = ICON[:-4]
GAIN = 1.55 if LIT else 1.0
if ICON == "gem":                           # gem RRGGBB SYMBOL.png OUT.png ...
    GEM_COLOUR, GEM_SYMBOL, OUT = argv[1], argv[2], argv[3]
    rest = argv[4:]
else:
    OUT = argv[1]
    rest = argv[2:]
SIZE = int(rest[0]) if len(rest) > 0 else 512
SAMPLES = int(rest[1]) if len(rest) > 1 else 160


def srgb(c):
    def ch(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return (ch(c[0]), ch(c[1]), ch(c[2]), 1.0)


LIGHTBLUE = srgb((148, 194, 240))
ICE = srgb((214, 232, 252))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# --- materials ------------------------------------------------------------------------------
REFLECT_FADE = 0.55
REFLECT_OPACITY = 0.38


def finish(nt, shader_out):
    """fade the mirrored copies (z < 0) out with depth; connect to the output"""
    n = nt.nodes
    out = n.new("ShaderNodeOutputMaterial")
    if GEM:
        nt.links.new(shader_out, out.inputs["Surface"])
        return
    geo = n.new("ShaderNodeNewGeometry")
    sep = n.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    rng = n.new("ShaderNodeMapRange")
    rng.inputs["From Min"].default_value = -REFLECT_FADE
    rng.inputs["From Max"].default_value = 0.0
    rng.inputs["To Min"].default_value = 0.0
    rng.inputs["To Max"].default_value = REFLECT_OPACITY
    nt.links.new(sep.outputs["Z"], rng.inputs["Value"])
    above = n.new("ShaderNodeMath")
    above.operation = "GREATER_THAN"
    above.inputs[1].default_value = -0.001
    nt.links.new(sep.outputs["Z"], above.inputs[0])
    vis = n.new("ShaderNodeMath")
    vis.operation = "MAXIMUM"
    nt.links.new(rng.outputs["Result"], vis.inputs[0])
    nt.links.new(above.outputs["Value"], vis.inputs[1])
    tr = n.new("ShaderNodeBsdfTransparent")
    mix = n.new("ShaderNodeMixShader")
    nt.links.new(vis.outputs["Value"], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(shader_out, mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])


def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    return m, m.node_tree


def glass_material(name, tint=LIGHTBLUE, rough=0.02):
    m, nt = new_mat(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = tint
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["Roughness"].default_value = rough
    b.inputs["IOR"].default_value = 1.45
    if "Dispersion" in b.inputs:
        b.inputs["Dispersion"].default_value = 0.4
    finish(nt, b.outputs[0])
    return m


def emission_material(name, colour, strength):
    m, nt = new_mat(name)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = colour
    e.inputs["Strength"].default_value = strength * GAIN
    finish(nt, e.outputs[0])
    return m


def image_emission_material(name, path, strength):
    """an emissive picture with alpha (the emblem symbol)"""
    m, nt = new_mat(name)
    n = nt.nodes
    tex = n.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path)
    tex.extension = "CLIP"
    e = n.new("ShaderNodeEmission")
    e.inputs["Strength"].default_value = strength
    nt.links.new(tex.outputs["Color"], e.inputs["Color"])
    tr = n.new("ShaderNodeBsdfTransparent")
    mix = n.new("ShaderNodeMixShader")
    nt.links.new(tex.outputs["Alpha"], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(e.outputs[0], mix.inputs[2])
    finish(nt, mix.outputs[0])
    return m


m_glass = glass_material("glass")
m_edge = emission_material("edge", LIGHTBLUE, 2.2)
m_hot = emission_material("hot", LIGHTBLUE, 5.0)
m_core = emission_material("core", LIGHTBLUE, 1.4)

# --- geometry helpers --------------------------------------------------------------------------
objects = []


def register(o, mat=None):
    if mat:
        o.data.materials.clear()
        o.data.materials.append(mat)
    objects.append(o)
    return o


def box(name, cx, cy, cz, sx, sy, sz, mat, bevel=0.05, rot_z=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    o = bpy.context.object
    o.name = name
    o.scale = (sx, sy, sz)
    o.rotation_euler = (0, 0, rot_z)
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        mod = o.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        mod.limit_method = "NONE"
    bpy.ops.object.shade_smooth()
    return register(o, mat)


def open_box(name, cx, cy, cz, sx, sy, sz, mat, wall=0.06, bevel=0.02):
    """a box without its top face, with glass walls wall thick (inwards)"""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    o = bpy.context.object
    o.name = name
    o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    top = [f for f in bm.faces if f.normal.z > 0.9]
    bmesh.ops.delete(bm, geom=top, context="FACES_ONLY")
    bm.to_mesh(o.data)
    bm.free()
    so = o.modifiers.new("walls", "SOLIDIFY")
    so.thickness = wall
    so.offset = -1
    so.use_even_offset = True
    if bevel:
        mod = o.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        mod.limit_method = "NONE"
    bpy.ops.object.shade_smooth()
    return register(o, mat)


def wire(src, name, mat=None, thickness=0.016):
    """glowing edges: a copy of src turned into a wire frame"""
    o = src.copy()
    o.data = src.data.copy()
    o.name = name
    o.modifiers.clear()
    w = o.modifiers.new("wire", "WIREFRAME")
    w.thickness = thickness
    w.use_even_offset = True
    w.use_replace = True
    bpy.context.collection.objects.link(o)
    return register(o, mat or m_edge)


def prism(name, outline, y0, y1, mat, rot_z=0.0, origin=(0, 0, 0)):
    """an outline in the x-z plane, extruded from y0 to y1"""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    front = [bm.verts.new((x, y0, z)) for x, z in outline]
    back = [bm.verts.new((x, y1, z)) for x, z in outline]
    bm.faces.new(front[::-1])
    bm.faces.new(back)
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((front[i], front[j], back[j], back[i]))
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    o.location = origin
    o.rotation_euler = (0, 0, rot_z)
    return register(o, mat)


def outline_curve(name, pts, thickness, mat, closed=True, origin=(0, 0, 0), rot_z=0.0):
    """a glowing line along points (a poly curve with a round bevel)"""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = thickness
    cu.bevel_resolution = 2
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, v in zip(sp.points, pts):
        p.co = (v[0], v[1], v[2], 1)
    sp.use_cyclic_u = closed
    o = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(o)
    o.location = origin
    o.rotation_euler = (0, 0, rot_z)
    o.data.materials.append(mat)
    objects.append(o)
    return o


def mesh_obj(name, verts, faces, mat, origin=(0, 0, 0), rot_z=0.0, scale=1.0):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v * scale for v in p) for p in verts], [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    o.location = origin
    o.rotation_euler = (0, 0, rot_z)
    return register(o, mat)


def cylinder(name, x, y, z, r, h, mat, axis="Z", verts=64):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=(x, y, z))
    o = bpy.context.object
    o.name = name
    if axis == "Y":
        o.rotation_euler = (math.pi / 2, 0, 0)
    bpy.ops.object.shade_smooth()
    return register(o, mat)


def torus(name, x, y, z, R, r, mat, axis="Z"):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=96, minor_segments=12,
                                     location=(x, y, z))
    o = bpy.context.object
    o.name = name
    if axis == "Y":
        o.rotation_euler = (math.pi / 2, 0, 0)
    bpy.ops.object.shade_smooth()
    return register(o, mat)


# --- the icons -----------------------------------------------------------------------------------

FRAME_EXTRA = []        # points the framing must include in both states of an icon (a still cabinet)
DRAWER_OUT = 0.55       # how far the drawer of the selected image comes out


def drawer(open_):
    W, D, H = 2.0, 1.4, 1.45
    front = -D / 2
    shell = box("cabinet", 0, 0, H / 2, W, D, H, m_glass, 0.06)
    wire(shell, "cabinet_wire")
    DW, DH = W - 0.26, H - 0.36
    out_by = DRAWER_OUT if open_ else 0.0
    # frame both states alike (the open drawer's room included): only the drawer moves between them
    FRAME_EXTRA.extend(Vector((x, y, z)) for x in (-W / 2, W / 2) for y in (front - DRAWER_OUT - 0.15, front)
                       for z in (0, H))
    dz = 0.18 + DH / 2
    plate = box("plate", 0, front - 0.035 - out_by, dz, DW, 0.07, DH, m_glass, 0.03)
    wire(plate, "plate_wire", thickness=0.014)
    box("handle", 0, front - 0.09 - out_by, dz + DH * 0.24, DW * 0.42, 0.06, 0.07, m_hot, 0.02)
    for i, x in enumerate((0.55, 0.35)):
        box(f"trace{i}", x, -0.05, H + 0.004, 0.03, D * 0.75, 0.01, m_edge, 0)
    if open_:
        tray = box("tray", 0, front - out_by + 0.6, 0.18 + DH * 0.4, DW - 0.1, 1.2, DH * 0.78, m_glass, 0.03)
        wire(tray, "tray_wire", thickness=0.014)
        for i in range(4):
            card = box(f"card{i}", -0.55 + i * 0.36, front - out_by + 0.45, 0.18 + DH * 0.62, 0.05, 0.75, DH * 0.62,
                       emission_material(f"card{i}", LIGHTBLUE, 0.9 if i % 2 else 1.3), 0.01)
            wire(card, f"card{i}_wire", thickness=0.012)


FILE_OPEN = float(os.environ.get("FILE_OPEN", "30"))      # selected: the page's front half opened, degrees
FILE_PAGE = float(os.environ.get("FILE_PAGE", "0.015"))   # selected: the front half's thickness (one thin page)
ARCHIVE_LID = float(os.environ.get("ARCHIVE_LID", "25"))  # selected: the crate's lid opened, degrees (user: 25)


def hinged(o, pivot, axis, angle, pre=None):
    """turn o (built around pivot) by angle about axis through pivot; pre: a turn applied after that"""
    bpy.context.view_layer.update()
    m = Matrix.Translation(pivot) @ Matrix.Rotation(angle, 4, axis) @ Matrix.Translation(-pivot)
    o.matrix_world = (pre or Matrix.Identity(4)) @ m @ o.matrix_world
    return o


def file(open_=False):
    """a glass page in two parts: the back part a plain sheet (no fold), the front part a single thin
    page (FILE_PAGE thick, its fold as thin) with the folded corner and glowing lines of text, lying on
    it; open_: the front page turned FILE_OPEN degrees towards the viewer on the left edge, where the
    two stay joined (both the user's design, 2026-11-16)"""
    w, h, t, fold = 1.15, 1.5, 0.09, 0.36
    RZ = Matrix.Rotation(math.radians(-24), 4, "Z")      # turned towards the camera
    y0 = -t / 2                                           # the front surface
    split = y0 + FILE_PAGE
    hinge = Vector((-w / 2, split, 0))
    TURN = Matrix.Translation(hinge) @ Matrix.Rotation(-math.radians(FILE_OPEN), 4, "Z") @ Matrix.Translation(-hinge)
    outline = [(-w / 2, 0), (w / 2, 0), (w / 2, h - fold), (w / 2 - fold, h), (-w / 2, h)]
    tri = [(w / 2 - fold, h), (w / 2, h - fold), (w / 2 - fold, h - fold)]
    rect = [(-w / 2, 0), (w / 2, 0), (w / 2, h), (-w / 2, h)]

    def placed(objs, m):
        bpy.context.view_layer.update()
        for o in objs:
            o.matrix_world = m @ o.matrix_world

    # the back part: a plain sheet without the fold, always in place
    placed([prism("back", rect, split, t / 2, m_glass),
            outline_curve("back_edge_f", [(x, split - 0.004, z) for x, z in rect], 0.008, m_edge),
            outline_curve("back_edge_b", [(x, t / 2 + 0.004, z) for x, z in rect], 0.008, m_edge)], RZ)
    # the front part: one thin page, one edge line round it, its fold as thin as the page; it lies on
    # the back part (normal) or is turned out on the left edge (selected)
    front = [prism("sheet", outline, y0, split, m_glass),
             outline_curve("sheet_edge", [(x, (y0 + split) / 2, z) for x, z in outline], 0.009, m_edge),
             prism("fold", tri, y0 - FILE_PAGE, y0, m_glass),
             outline_curve("fold_edge", [(x, y0 - FILE_PAGE / 2, z) for x, z in tri], 0.008, m_edge)]
    # text lines, glowing in the glass
    for k, (z, ln) in enumerate(((1.08, 0.62), (0.9, 0.8), (0.72, 0.8), (0.54, 0.8), (0.36, 0.5))):
        x0 = -w / 2 + 0.17
        front.append(box(f"line{k}", x0 + ln / 2, y0 - 0.006, z, ln, 0.012, 0.045, m_core if k else m_hot, 0))
    placed(front, RZ @ TURN if open_ else RZ)
    # frame both states alike: the opened front half's room included
    for m in (RZ, RZ @ TURN):
        FRAME_EXTRA.extend(m @ Vector((x, y, z)) for x, z in rect for y in (-t / 2 - 0.06, t / 2))


def device():
    """a glass drive: a flat box with a glowing platter inside, a slot and a light"""
    W, D, H = 2.0, 1.45, 0.62
    shell = box("drive", 0, 0, H / 2, W, D, H, m_glass, 0.07)
    wire(shell, "drive_wire")
    cylinder("platter", 0.25, 0.12, H * 0.45, 0.5, 0.025, glass_material("platter_glass", ICE, 0.05))
    torus("platter_ring", 0.25, 0.12, H * 0.45, 0.5, 0.018, m_edge)
    torus("platter_ring2", 0.25, 0.12, H * 0.45, 0.28, 0.012, m_core)
    cylinder("hub", 0.25, 0.12, H * 0.45, 0.08, 0.06, m_hot)
    box("slot", -0.3, -D / 2 - 0.005, H * 0.58, 0.9, 0.02, 0.05, m_hot, 0)
    cylinder("led", 0.72, -D / 2 - 0.01, H * 0.58, 0.05, 0.03, m_hot, axis="Y")
    box("vent0", -0.3, -D / 2 - 0.005, H * 0.32, 0.9, 0.01, 0.018, m_core, 0)


def archive(open_=False, lid=None, rise=0.0, rise_frame=0.0):
    """a glass crate (open at the top, under its lid) with straps and two small crates inside (glenz
    layering); open_: the lid opened on its back hinge, the small crates in view. lid: the lid's angle in
    both images (UnArc); rise: how far the top small crate has risen (rise_frame: the most it rises)"""
    S, H = 1.55, 1.2
    crate = open_box("crate", 0, 0, H / 2, S, S, H, m_glass, wall=0.03)
    wire(crate, "crate_wire")
    L = S + 0.12
    pivot = Vector((0, L / 2, H))                      # the hinge: the lid's back lower edge
    angle = -math.radians(ARCHIVE_LID if lid is None else lid)     # negative: the front comes up
    lid_o = box("lid", 0, 0, H + 0.1, L, L, 0.2, m_glass, 0.04)
    hinged(lid_o, pivot, "X", angle if open_ else 0.0)
    wire(lid_o, "lid_wire", thickness=0.014)
    m = Matrix.Translation(pivot) @ Matrix.Rotation(angle, 4, "X") @ Matrix.Translation(-pivot)
    FRAME_EXTRA.extend(m @ Vector((x, y, z)) for x in (-L / 2, L / 2) for y in (-L / 2, L / 2) for z in (H, H + 0.2))
    FRAME_EXTRA.extend(Vector((x, y, z)) for x in (-L / 2, L / 2) for y in (-L / 2, L / 2) for z in (0, H + 0.2))
    # the straps: bands on the outside of the crate, down the front and the back, and over the top
    # only while it is closed (opened: nothing crosses the opening, user 2026-11-16)
    tb = 0.08
    for i, x in enumerate((-0.42, 0.42)):
        sm = glass_material(f"strap{i}g", ICE, 0.1)
        parts = [("f", 0, -S / 2 - tb / 2, H / 2, tb, H), ("b", 0, S / 2 + tb / 2, H / 2, tb, H)]
        if not open_:
            parts.append(("t", 0, 0, H - 0.02, S + 2 * tb, 0.04))
        for tag, _, y, z, d, hh in parts:
            strap = box(f"strap{i}{tag}", x, y, z, 0.16, d, hh, sm, 0.015)
            wire(strap, f"strap{i}{tag}_wire", thickness=0.012)
    # two small crates on the floor and one stacked on them: its edges reach up into the opening
    for i, (x, y, z, s, rz) in enumerate(((-0.2, 0.15, 0.3, 0.55, 0), (0.25, -0.1, 0.25, 0.45, 0),
                                          (0.02, 0.05, 0.84, 0.5, 18))):
        if i == 2 and rise_frame:                    # UnArc: this one rises out of the crate
            def top(x=x, y=y, s=s, rz=rz):
                c = box("inner2", 0, 0, 0, s, s, s, m_glass, 0.02, math.radians(rz))
                wire(c, "inner2_wire", m_edge, 0.012)
            m0 = Matrix.Translation((x, y, z))
            m1 = Matrix.Translation((x, y, z + rise_frame)) @ Matrix.Rotation(math.radians(22), 4, "Z")
            moving(top, m0, m1, rise > 0)
            continue
        c = box(f"inner{i}", x, y, z, s, s, s, m_glass, 0.02, math.radians(rz))
        wire(c, f"inner{i}_wire", m_edge, 0.012)
    box("lock", 0, -S / 2 - 0.09, H * 0.62, 0.22, 0.05, 0.26, m_hot, 0.02)


def prefs():
    """a glass gear standing on the floor"""
    R, r, teeth, t = 0.95, 0.76, 10, 0.32
    rz = math.radians(10)
    pts = []
    for i in range(teeth * 4):
        a = (i / (teeth * 4)) * 2 * math.pi
        rr = R if (i % 4) in (1, 2) else r
        pts.append((rr * math.cos(a), R + rr * math.sin(a)))
    gear = prism("gear", pts, -t / 2, t / 2, m_glass, rz)
    hole = cylinder("hole", 0, 0, R, 0.3, t * 3, None, axis="Y")
    bpy.context.view_layer.objects.active = gear
    b = gear.modifiers.new("hole", "BOOLEAN")
    b.operation = "DIFFERENCE"
    b.object = hole
    hole.hide_render = True
    objects.remove(hole)
    for side, y in (("f", -t / 2 - 0.004), ("b", t / 2 + 0.004)):
        outline_curve(f"gear_edge_{side}", [(x, y, z) for x, z in pts], 0.009 if side == "f" else 0.007, m_edge, rot_z=rz)
    o = torus("hole_ring", 0, -t / 2 - 0.004, R, 0.3, 0.012, m_hot, axis="Y")
    o.rotation_euler = (math.pi / 2, 0, rz)
    o.location = Vector((0, -t / 2 - 0.004, R))
    o.location.rotate(o.rotation_euler.__class__((0, 0, rz)))
    o2 = torus("hole_ring_b", 0, t / 2 + 0.004, R, 0.3, 0.008, m_edge, axis="Y")
    o2.rotation_euler = (math.pi / 2, 0, rz)
    o2.location = Vector((0, t / 2 + 0.004, R))
    o2.location.rotate(o2.rotation_euler.__class__((0, 0, rz)))
    o3 = torus("inner_ring", 0, -t / 2 - 0.004, R, 0.6, 0.008, m_core, axis="Y")
    o3.rotation_euler = (math.pi / 2, 0, rz)
    o3.location = Vector((0, -t / 2 - 0.004, R))
    o3.location.rotate(o3.rotation_euler.__class__((0, 0, rz)))


TOOL_RISE = 0.32       # selected: how far the crystal rises


def tool(open_=False):
    """a glenz crystal floating over a glass pedestal; open_ (the selected image, the user 2026-11-16):
    the crystal risen and lit from within, the beam to its pedestal brighter"""
    h, r = 0.95, 0.6
    verts = [(0, 0, h), (r, 0, 0), (0, r, 0), (-r, 0, 0), (0, -r, 0), (0, 0, -h)]
    faces = [(0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 1), (5, 2, 1), (5, 3, 2), (5, 4, 3), (5, 1, 4)]
    z0 = 1.35
    zc = z0 + (TOOL_RISE if open_ else 0.0)
    # frame both states alike: the risen crystal's room included
    FRAME_EXTRA.extend(Vector((x, y, z)) for x in (-r, r) for y in (-r, r) for z in (z0 - h, z0 + TOOL_RISE + h))
    crystal = mesh_obj("crystal", verts, faces, m_glass, origin=(0, 0, zc), rot_z=math.radians(20))
    wire(crystal, "crystal_wire", emission_material("crystal_edge", LIGHTBLUE, 3.4) if open_ else None, thickness=0.014)
    mesh_obj("core", verts, faces, emission_material("crystal_core", LIGHTBLUE, 3.0) if open_ else m_core,
             origin=(0, 0, zc), rot_z=math.radians(20), scale=0.38)
    cylinder("pedestal", 0, 0, 0.07, 0.75, 0.14, m_glass)
    torus("pedestal_ring", 0, 0, 0.14, 0.75, 0.014, m_edge)
    torus("pedestal_ring2", 0, 0, 0.14, 0.45, 0.01, m_core)
    # a beam from the pedestal up to the crystal (brighter and reaching it when risen)
    top = zc - h + 0.05                         # up to the crystal's lower tip, as approved (G10)
    cylinder("beam", 0, 0, (0.15 + top) / 2, 0.2, top - 0.15,
             emission_material("beam", LIGHTBLUE, 0.9 if open_ else 0.35), verts=48)
    if open_:                                   # lit from within
        inner = bpy.data.objects.new("crystal_inner", bpy.data.lights.new("crystal_inner", "POINT"))
        inner.data.energy = 30
        inner.data.shadow_soft_size = 0.2
        inner.data.color = LIGHTBLUE[:3]
        inner.location = (0, 0, zc)
        bpy.context.collection.objects.link(inner)


def lacquer_material(name):
    """black lacquer (chips, slots)"""
    m, nt = new_mat(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.004, 0.005, 0.008, 1)
    b.inputs["Roughness"].default_value = 0.2
    b.inputs["Coat Weight"].default_value = 1.0
    b.inputs["Coat Roughness"].default_value = 0.03
    finish(nt, b.outputs[0])
    return m


def place(o, rz, origin=Vector((0, 0, 0))):
    """turn an object about the z axis through origin"""
    o.location = Vector(o.location) - origin
    o.location.rotate(__import__("mathutils").Euler((0, 0, rz)))
    o.location = Vector(o.location) + origin
    o.rotation_euler.z += rz


def floppy(open_=False):
    """a 3.5" floppy standing up: the magnetic disc inside, a shutter over the access hole (open_:
    slid sideways, its window over the hole, as on a real floppy), frosted label, cut corner,
    write protect hole"""
    w, t, c = 1.5, 0.1, 0.13
    rz = math.radians(-14)
    front = -t / 2
    outline = [(-w / 2, 0), (w / 2, 0), (w / 2, w - c), (w / 2 - c, w), (-w / 2, w)]
    prism("floppy", outline, -t / 2, t / 2, m_glass, rz)
    outline_curve("floppy_edge_f", [(x, front - 0.004, z) for x, z in outline], 0.009, m_edge, rot_z=rz)
    outline_curve("floppy_edge_b", [(x, t / 2 + 0.004, z) for x, z in outline], 0.007, m_edge, rot_z=rz)

    # the magnetic disc inside the case (seen through the glass, and through the hole when open)
    m_mag = lacquer_material("magnetic")
    disc_z = 0.84
    o = cylinder("magnetic", 0, 0, 0, 0.56, 0.012, m_mag, axis="Y")
    o.location = Vector((0, 0, disc_z))
    place(o, rz)
    for name, r, mat in (("track", 0.48, m_core), ("track2", 0.36, m_core), ("hub", 0.11, m_hot)):
        o = torus(name, 0, 0, 0, r, 0.008, mat, axis="Y")
        o.location = Vector((0, -0.009, disc_z))
        place(o, rz)

    # the access hole in the case, and the shutter with its window over it when slid
    hole_x, hole_z0, hole_z1, hole_w = 0.10, w - 0.53, w - 0.06, 0.2
    outline_curve("hole_edge", [(hole_x - hole_w / 2, front - 0.003, hole_z0), (hole_x + hole_w / 2, front - 0.003, hole_z0),
                                (hole_x + hole_w / 2, front - 0.003, hole_z1), (hole_x - hole_w / 2, front - 0.003, hole_z1)],
                  0.006, m_edge, rot_z=rz)
    # like a real 3.5" floppy (the user's reference GIF): the shutter slides left by about a fifth
    # of its width; its window, right of the hole when closed, then lies over the hole
    slide = -0.16
    sx = slide if open_ else 0.0
    win_rel = hole_x - slide                  # the shutter's window lines up with the hole when slid
    sy = 0.012
    shutter = box("shutter", 0, 0, 0, 0.8, sy, 0.56, glass_material("shutter_glass", ICE, 0.12), 0.01)
    shutter.location = Vector((sx, front - sy / 2 - 0.006, w - 0.29))
    cut = box("shutter_cut", 0, 0, 0, hole_w, 0.2, hole_z1 - hole_z0, None, 0)
    cut.location = Vector((sx + win_rel, front - sy / 2 - 0.006, (hole_z0 + hole_z1) / 2))
    objects.remove(cut)
    cut.hide_render = True
    bpy.context.view_layer.objects.active = shutter
    b = shutter.modifiers.new("window", "BOOLEAN")
    b.operation = "DIFFERENCE"
    b.object = cut
    place(shutter, rz)
    place(cut, rz)
    wire(shutter, "shutter_wire", thickness=0.008)
    wx = sx + win_rel
    yy = front - sy - 0.009
    outline_curve("shutter_window", [(wx - hole_w / 2, yy, hole_z0), (wx + hole_w / 2, yy, hole_z0),
                                     (wx + hole_w / 2, yy, hole_z1), (wx - hole_w / 2, yy, hole_z1)],
                  0.007, m_hot, rot_z=rz)

    # label, its lines, the write protect hole
    lab = box("label", 0, 0, 0, 1.12, 0.012, 0.66, glass_material("label_glass", ICE, 0.3), 0.01)
    lab.location = Vector((0, front - 0.008, 0.42))
    place(lab, rz)
    wire(lab, "label_wire", thickness=0.008)
    wp = box("wp", 0, 0, 0, 0.1, 0.014, 0.1, m_hot, 0)
    wp.location = Vector((-0.6, front - 0.009, 0.12))
    place(wp, rz)
    for k, z in enumerate((0.58, 0.46, 0.34)):
        o = box(f"labelline{k}", 0, 0, 0, 0.8 if k < 2 else 0.5, 0.01, 0.03, m_core, 0)
        o.location = Vector((-0.12 if k < 2 else -0.27, front - 0.02, z))
        place(o, rz)


def disc():
    """an optical disc standing on its edge; DISC_TURN (degrees, + = its face turns right) and
    DISC_LEAN (degrees it leans back on its own axis, top edge away) set the angle"""
    from mathutils import Euler
    R, t = 0.98, 0.05
    turn = float(os.environ.get("DISC_TURN", "8"))
    lean = float(os.environ.get("DISC_LEAN", "25"))
    tilt = (math.radians(90 - lean), 0, math.radians(turn))
    zc = R * math.cos(math.radians(lean)) + t / 2 * math.sin(math.radians(lean)) + 0.005   # the lowest edge on the floor
    # a disc bends little (thin polycarbonate): with glass's IOR its refraction looks like a horn
    dm = glass_material("disc_glass", ICE, 0.02)
    ior = float(os.environ.get("DISC_IOR", "1.12"))
    next(nd for nd in dm.node_tree.nodes if nd.type == "BSDF_PRINCIPLED").inputs["IOR"].default_value = ior
    d = cylinder("disc", 0, 0, zc, R, t, dm, verts=96)
    d.rotation_euler = tilt
    hole = cylinder("disc_hole", 0, 0, zc, 0.16, t * 4, None)
    hole.rotation_euler = tilt
    bpy.context.view_layer.objects.active = d
    b = d.modifiers.new("hole", "BOOLEAN")
    b.operation = "DIFFERENCE"
    b.object = hole
    hole.hide_render = True
    objects.remove(hole)
    # the data layer: a thin light-blue metal annulus inside the disc (the CD sheen)
    if os.environ.get("DISC_DATA", "0") == "1":      # (tried; the user chose the clear disc)
        m, nt = new_mat("data_layer")
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.inputs["Base Color"].default_value = ICE
        bsdf.inputs["Metallic"].default_value = 1.0
        bsdf.inputs["Roughness"].default_value = 0.18
        finish(nt, bsdf.outputs[0])
        layer = cylinder("data_layer", 0, 0, zc, R - 0.06, 0.006, m, verts=96)
        layer.rotation_euler = tilt
        cut = cylinder("data_cut", 0, 0, zc, 0.4, 0.05, None)
        cut.rotation_euler = tilt
        bpy.context.view_layer.objects.active = layer
        b2 = layer.modifiers.new("cut", "BOOLEAN")
        b2.operation = "DIFFERENCE"
        b2.object = cut
        cut.hide_render = True
        objects.remove(cut)
    # rings on the faces: local +z is the front face (towards the viewer), -z the back
    for name, r, w, mat, z in (("rim", R, 0.014, m_edge, t / 2), ("rim_b", R, 0.01, m_edge, -t / 2),
                               ("data", 0.42, 0.009, m_core, t / 2), ("hub", 0.24, 0.012, m_hot, t / 2),
                               ("hole_rim", 0.16, 0.01, m_edge, t / 2)):
        o = torus(name, 0, 0, 0, r, w, mat)
        o.rotation_euler = tilt
        o.location = Vector((0, 0, z + (0.002 if z > 0 else -0.002)))
        o.location.rotate(Euler(tilt))
        o.location += Vector((0, 0, zc))


def ram():
    """a glass memory module standing on its contacts"""
    L, H, t = 2.2, 0.68, 0.06
    rz = math.radians(-14)
    board = box("board", 0, 0, 0, L, t, H, m_glass, 0.02)
    board.location = Vector((0, 0, H / 2 + 0.04))
    place(board, rz)
    wire(board, "board_wire", thickness=0.012)
    m_chip = lacquer_material("chip")
    for k in range(4):
        x = -0.75 + k * 0.5
        ch = box(f"chip{k}", 0, 0, 0, 0.36, 0.05, 0.3, m_chip, 0.01)
        ch.location = Vector((x, -t / 2 - 0.025, H * 0.58 + 0.04))
        place(ch, rz)
        wire(ch, f"chip{k}_wire", m_core, 0.007)
    for k in range(26):
        x = -L / 2 + 0.1 + k * 0.077
        if 11 <= k <= 12:          # the notch
            continue
        ct = box(f"contact{k}", 0, 0, 0, 0.045, 0.012, 0.11, m_hot, 0)
        ct.location = Vector((x, -t / 2 - 0.006, 0.12))
        place(ct, rz)


def usb():
    """a glass USB stick lying on the floor, the connector pointing down right"""
    rz = math.radians(32)
    body = box("usb_body", 0, 0, 0, 0.62, 1.35, 0.3, m_glass, 0.1)
    body.location = Vector((0, 0.25, 0.15))
    place(body, rz)
    wire(body, "usb_wire", thickness=0.012)
    con = box("usb_con", 0, 0, 0, 0.48, 0.55, 0.18, glass_material("con_glass", ICE, 0.12), 0.015)
    con.location = Vector((0, -0.67, 0.15))
    place(con, rz)
    wire(con, "con_wire", m_hot, 0.01)
    for k, x in enumerate((-0.1, 0.1)):
        h = box(f"usb_hole{k}", 0, 0, 0, 0.09, 0.09, 0.012, m_core, 0)
        h.location = Vector((x, -0.75, 0.245))
        place(h, rz)
    led = cylinder("usb_led", 0, 0, 0, 0.05, 0.02, m_hot)
    led.location = Vector((0, 0.65, 0.305))
    place(led, rz)
    lab = box("usb_label", 0, 0, 0, 0.36, 0.6, 0.01, m_core, 0)
    lab.location = Vector((0, 0.2, 0.302))
    place(lab, rz)


def network():
    """a glass globe with glowing rings on a stand: a remote place"""
    zc, R = 1.12, 0.78
    cylinder("stand", 0, 0, 0.05, 0.5, 0.1, m_glass)
    torus("stand_rim", 0, 0, 0.1, 0.5, 0.012, m_edge)
    cylinder("neck", 0, 0, 0.2, 0.06, 0.22, m_glass)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=R, location=(0, 0, zc))
    sph = bpy.context.object
    bpy.ops.object.shade_smooth()
    register(sph, m_glass)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.22, location=(0, 0, zc))
    register(bpy.context.object, m_core)
    torus("equator", 0, 0, zc, R + 0.004, 0.012, m_edge)
    for k, zz in enumerate((0.45, -0.45)):
        r = math.sqrt(R * R - zz * zz)
        torus(f"parallel{k}", 0, 0, zc + zz, r + 0.004, 0.009, m_edge)
    for k, a in enumerate((0, 60, 120)):
        o = torus(f"meridian{k}", 0, 0, zc, R + 0.004, 0.009, m_hot if k == 0 else m_edge)
        o.rotation_euler = (math.pi / 2, 0, math.radians(a - 20))


def trashcan(full):
    """a glass bin; full: the lid lifted, glowing scraps inside"""
    r0, r1, h = 0.58, 0.74, 1.3
    bpy.ops.mesh.primitive_cone_add(vertices=64, radius1=r0, radius2=r1, depth=h, location=(0, 0, h / 2))
    body = bpy.context.object
    body.name = "bin"
    bpy.ops.object.shade_smooth()
    register(body, m_glass)
    torus("bin_rim", 0, 0, h, r1, 0.016, m_edge)
    torus("bin_base", 0, 0, 0.01, r0, 0.012, m_edge)
    for k in range(12):
        a = k / 12 * 2 * math.pi
        outline_curve(f"rib{k}", [(r0 * math.cos(a) * 1.01, r0 * math.sin(a) * 1.01, 0.08),
                                  (r1 * math.cos(a) * 1.01, r1 * math.sin(a) * 1.01, h - 0.08)], 0.007, m_core,
                      closed=False)
    # the lid: closed, or lifted and tilted (the moving part between the two images)
    lid_z, tilt = (h + 0.06, 0.0) if not full else (h + 0.34, math.radians(-24))
    lid = cylinder("lid", 0, 0, lid_z, r1 + 0.05, 0.1, m_glass)
    lid.rotation_euler = (tilt, 0, 0)
    lr = torus("lid_rim", 0, 0, lid_z, r1 + 0.05, 0.014, m_edge)
    lr.rotation_euler = (tilt, 0, 0)
    hd = torus("lid_handle", 0, 0, lid_z + 0.1, 0.18, 0.03, m_hot)
    hd.rotation_euler = (math.pi / 2 + tilt, 0, math.radians(-30))
    if full:
        import random
        rnd = random.Random(3)
        for k in range(7):
            a = rnd.uniform(0, 2 * math.pi)
            rr = rnd.uniform(0.1, 0.45)
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=rnd.uniform(0.14, 0.24),
                                                  location=(rr * math.cos(a), rr * math.sin(a), h - rnd.uniform(0.02, 0.25)))
            sc = bpy.context.object
            sc.rotation_euler = (rnd.uniform(0, 3), rnd.uniform(0, 3), rnd.uniform(0, 3))
            register(sc, emission_material(f"scrap{k}", ICE if k % 2 else LIGHTBLUE, 0.8))
    # frame both states alike: the lifted lid's room included
    FRAME_EXTRA.extend(Vector((x, y, z)) for x in (-r1 - 0.1, r1 + 0.1) for y in (-r1 - 0.1, r1 + 0.1)
                       for z in (0, h + 0.75))


def glow_through_material(name, colour, strength):
    """light inside glass: emits, but lets the background through (not an opaque plate)"""
    m, nt = new_mat(name)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = colour
    e.inputs["Strength"].default_value = strength
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(nt.nodes.new("ShaderNodeBsdfTransparent").outputs[0], add.inputs[0])
    nt.links.new(e.outputs[0], add.inputs[1])
    finish(nt, add.outputs[0])
    return m


def rounded_rect(half, r, y, z0, steps=8):
    pts = []
    for cx, cz, a0 in ((half - r, half - r, 0), (-(half - r), half - r, 90), (-(half - r), -(half - r), 180),
                       (half - r, -(half - r), 270)):
        for k in range(steps + 1):
            a = math.radians(a0 + 90 * k / steps)
            pts.append((cx + r * math.cos(a), y, z0 + cz + r * math.sin(a)))
    return pts


def hammered_glass_material(name, tint, bump=0.35):
    """cathedral glass: tinted, see-through, with a hammered (dimpled) surface that catches light"""
    m, nt = new_mat(name)
    n = nt.nodes
    b = n.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = tint
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["Roughness"].default_value = 0.02
    b.inputs["IOR"].default_value = 1.5
    if "Dispersion" in b.inputs:
        b.inputs["Dispersion"].default_value = 0.3
    if bump > 0:
        tc = n.new("ShaderNodeTexCoord")
        vo = n.new("ShaderNodeTexVoronoi")
        vo.feature = "SMOOTH_F1"
        vo.inputs["Scale"].default_value = 22.0
        nt.links.new(tc.outputs["Object"], vo.inputs["Vector"])
        bp = n.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        bp.inputs["Distance"].default_value = 0.03
        nt.links.new(vo.outputs["Distance"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    finish(nt, b.outputs[0])
    return m


def gem(colour, symbol):
    """an emblem: a see-through tile of coloured glass, glowing edges (Tron), the symbol glowing on it"""
    rgb = tuple(int(colour[i:i + 2], 16) for i in (0, 2, 4))
    c = srgb(rgb)
    # the glow: the colour at full brightness (hue kept: mixing purple with white makes pink),
    # nudged a little towards cool blue light (Tron), with a touch of white for a hot core
    mx = max(rgb) or 1
    neon = tuple(v * 255 / mx for v in rgb)
    purple = rgb[0] > 0.3 * mx and rgb[2] > 0.3 * mx       # red + blue: its neon must lean to violet, not magenta
    neon = tuple(a + (b - a) * (0.4 if purple else 0.15) for a, b in zip(neon, (60, 100, 255)))
    lit = srgb(tuple(round(v + (255 - v) * 0.12) for v in neon))
    bump = float(os.environ.get("GEM_BUMP", "0"))          # hammered surface (0 = smooth)
    glow = float(os.environ.get("GEM_GLOW", "0.1"))        # light inside the glass (deep colours)
    absorb = float(os.environ.get("GEM_ABSORB", "0"))      # colour from absorption: thick edges deeper
    gm = hammered_glass_material("gem_glass", (0.95, 0.95, 0.95, 1) if absorb else c, bump)
    if absorb:
        va = gm.node_tree.nodes.new("ShaderNodeVolumeAbsorption")
        va.inputs["Color"].default_value = c
        va.inputs["Density"].default_value = absorb
        out = next(n for n in gm.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        gm.node_tree.links.new(va.outputs[0], out.inputs["Volume"])
    tile = box("tile", 0, 0, 0.5, 1.0, 0.3, 1.0, gm, 0.16)
    tile.modifiers["bevel"].segments = 6
    # light colours (yellow) need more inner light: see-through yellow over dark turns brown
    light = (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255 > 0.6
    box("core", 0, 0.0, 0.5, 0.84, 0.18, 0.84, glow_through_material("gem_core", c, max(0.32, glow) if light else glow), 0.1)
    # bright emission clips each channel at 1: a violet whose red channel clips as well turns magenta,
    # so the strength is capped where the second strongest channel would clip
    second = sorted(lit[:3])[1]
    edge = min(3.5, 0.6 / second) if second > 0 else 3.5
    outline_curve("edge_front", rounded_rect(0.43, 0.15, -0.153, 0.5), 0.011, emission_material("gem_edge", lit, edge))
    outline_curve("edge_back", rounded_rect(0.43, 0.15, 0.153, 0.5), 0.008, emission_material("gem_edge_b", lit, edge * 0.46))
    bpy.ops.mesh.primitive_plane_add(size=0.66, location=(0, -0.158, 0.5), rotation=(math.pi / 2, 0, 0))
    sym = bpy.context.object
    # deep colours: the symbol glows; light colours (yellow): a black symbol, which the yellow glass
    # around it makes readable (a light symbol vanishes in bright yellow)
    register(sym, image_emission_material("symbol", symbol, 0.0 if light else 4.0))
    # the symbol image is white: tint its glow with a pale shade of the colour
    tex_mat = sym.data.materials[0]
    em = next(n for n in tex_mat.node_tree.nodes if n.type == "EMISSION")
    tint = tex_mat.node_tree.nodes.new("ShaderNodeMix")
    tint.data_type = "RGBA"
    tint.blend_type = "MULTIPLY"
    tint.inputs["Factor"].default_value = 1.0
    tex = next(n for n in tex_mat.node_tree.nodes if n.type == "TEX_IMAGE")
    tex_mat.node_tree.links.new(tex.outputs["Color"], tint.inputs["A"])
    tint.inputs["B"].default_value = srgb(tuple(round(v + (255 - v) * 0.85) for v in neon))
    tex_mat.node_tree.links.new(tint.outputs["Result"], em.inputs["Color"])


# --- camera, light, world ------------------------------------------------------------------------
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
bpy.context.collection.objects.link(cam)
scene.camera = cam
cam.data.lens = 50
if GEM:
    cam.location = (-1.3, -4.6, 1.7)
    target = Vector((0, 0, 0.5))
else:
    cam.location = (-3.4, -5.0, 3.3)          # front left: the objects face down right
    target = Vector((0, 0, 0.6))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()

# group 4, the programs (tools/blender/glass_programs.py, run in this namespace)
for _f in ("glass_programs.py", "glass_prefs.py", "glass_utils.py", "glass_emblems.py"):
    _progs = os.path.join(os.path.dirname(os.path.abspath(__file__)), _f)
    exec(compile(open(_progs).read(), _progs, "exec"))
# the built-in icons below win over a program of the same name: never reuse one (PF32 USB was "usb")
BUILTIN = {"drawer", "file", "device", "archive", "prefs", "tool", "floppy", "disc", "ram", "usb", "network",
           "trashcan", "gem"}
assert not set(PROGRAMS) & BUILTIN, sorted(set(PROGRAMS) & BUILTIN)

if ICON in ("drawer", "drawer_open"):
    drawer(ICON == "drawer_open")
elif ICON in ("file", "file_open"):
    file(ICON == "file_open")
elif ICON == "device":
    device()
elif ICON in ("archive", "archive_open"):
    archive(ICON == "archive_open")
elif ICON == "prefs":
    prefs()
elif ICON in ("tool", "tool_open"):
    tool(ICON == "tool_open")
elif ICON == "floppy":
    floppy(LIT)                                # selected: the shutter slid open (and lit)
elif ICON == "disc":
    disc()
elif ICON == "ram":
    ram()
elif ICON == "usb":
    usb()
elif ICON == "network":
    network()
elif ICON in ("trashcan", "trashcan_full"):
    trashcan(ICON == "trashcan_full")
elif ICON == "gem":
    gem(GEM_COLOUR, GEM_SYMBOL)
elif ICON.startswith("emb_"):
    EMBLEMS[ICON[4:]]()
elif (ICON[:-5] if ICON.endswith("_open") else ICON) in PROGRAMS:
    _prog, _sel = PROGRAMS[ICON[:-5] if ICON.endswith("_open") else ICON], ICON.endswith("_open")
    # both images share one framing, so nothing that does not move can shift between them (the user:
    # "the monitor moves between the images when it should be still"): build the other image first,
    # keep only its extents, remove it, then build this one
    _n0, _before = len(objects), set(bpy.data.objects)
    _prog(not _sel)
    bpy.context.view_layer.update()
    _deps = bpy.context.evaluated_depsgraph_get()
    for _o in objects[_n0:]:
        if _o.type == "MESH" and not _o.hide_render:
            FRAME_EXTRA.extend(_o.matrix_world @ Vector(_c) for _c in _o.evaluated_get(_deps).bound_box)
    for _o in set(bpy.data.objects) - _before:
        bpy.data.objects.remove(_o, do_unlink=True)
    del objects[_n0:]
    _prog(_sel)
else:
    raise SystemExit(f"unknown icon {ICON}")

bpy.context.view_layer.update()

if LIT:
    deps0 = bpy.context.evaluated_depsgraph_get()
    cs = [o.matrix_world @ Vector(c) for o in objects if o.type == "MESH" and not o.hide_render
          for c in o.evaluated_get(deps0).bound_box]
    centre = sum(cs, Vector((0, 0, 0))) / max(len(cs), 1)
    inner = bpy.data.objects.new("inner", bpy.data.lights.new("inner", "POINT"))
    inner.data.energy = 45
    inner.data.shadow_soft_size = 0.35
    inner.data.color = LIGHTBLUE[:3]
    inner.location = centre
    bpy.context.collection.objects.link(inner)

# the floor reflection: mirrored copies below z = 0
if not GEM:
    MIRROR = Matrix.Scale(-1, 4, (0, 0, 1))
    for o in list(objects):
        r = o.copy()
        r.data = o.data
        r.name = o.name + "_mirror"
        bpy.context.collection.objects.link(r)
        r.matrix_world = MIRROR @ o.matrix_world
        for m in r.modifiers:
            if m.type == "BOOLEAN" and m.object:      # the cutter must be mirrored too
                cut = m.object.copy()
                bpy.context.collection.objects.link(cut)
                cut.matrix_world = MIRROR @ m.object.matrix_world
                cut.hide_render = True
                m.object = cut

world = bpy.data.worlds.new("world")
scene.world = world
world.use_nodes = True
wn = world.node_tree
wn.nodes.clear()
wout = wn.nodes.new("ShaderNodeOutputWorld")
tc = wn.nodes.new("ShaderNodeTexCoord")
sep = wn.nodes.new("ShaderNodeSeparateXYZ")
wn.links.new(tc.outputs["Generated"], sep.inputs[0])


def band(axis_out, centre, width):
    sub = wn.nodes.new("ShaderNodeMath")
    sub.operation = "SUBTRACT"
    sub.inputs[1].default_value = centre
    wn.links.new(axis_out, sub.inputs[0])
    ab = wn.nodes.new("ShaderNodeMath")
    ab.operation = "ABSOLUTE"
    wn.links.new(sub.outputs[0], ab.inputs[0])
    st = wn.nodes.new("ShaderNodeMapRange")
    st.interpolation_type = "SMOOTHSTEP"
    st.inputs["From Min"].default_value = width
    st.inputs["From Max"].default_value = width * 0.6
    wn.links.new(ab.outputs[0], st.inputs["Value"])
    return st.outputs["Result"]


acc = None
for axis, centre, width, gain in (("Z", 0.55, 0.06, 1.0), ("Z", -0.25, 0.05, 0.7), ("X", 0.75, 0.05, 0.8),
                                  ("Y", 0.8, 0.05, 0.6)):
    b = band(sep.outputs[axis], centre, width)
    g = wn.nodes.new("ShaderNodeMath")
    g.operation = "MULTIPLY"
    g.inputs[1].default_value = gain
    wn.links.new(b, g.inputs[0])
    if acc is None:
        acc = g.outputs[0]
    else:
        s = wn.nodes.new("ShaderNodeMath")
        s.operation = "ADD"
        wn.links.new(acc, s.inputs[0])
        wn.links.new(g.outputs[0], s.inputs[1])
        acc = s.outputs[0]
bg = wn.nodes.new("ShaderNodeBackground")
bg.inputs["Color"].default_value = (1, 1, 1, 1)
strength = wn.nodes.new("ShaderNodeMath")
strength.operation = "MULTIPLY_ADD"
strength.inputs[1].default_value = 3.0
strength.inputs[2].default_value = 0.004
wn.links.new(acc, strength.inputs[0])
wn.links.new(strength.outputs[0], bg.inputs["Strength"])
wn.links.new(bg.outputs[0], wout.inputs["Surface"])

key = bpy.data.objects.new("key", bpy.data.lights.new("key", "AREA"))
key.data.shape = "RECTANGLE"
key.data.size, key.data.size_y = 3.0, 0.4
key.data.energy = 120
key.data.color = (0.85, 0.92, 1.0)
key.location = (1.5, -2.5, 4.5)
key.rotation_euler = (Vector((0, 0, 0.6)) - key.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.collection.objects.link(key)

# --- frame everything (and the reflection) ------------------------------------------------------
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402

bpy.context.view_layer.update()
deps = bpy.context.evaluated_depsgraph_get()
pts = []
for o in objects:
    if o.hide_render or o.type != "MESH":      # (curves report a large default box; they follow meshes)
        continue
    ev = o.evaluated_get(deps)
    for c in ev.bound_box:
        p = o.matrix_world @ Vector(c)
        pts.append(p)
        if not GEM:
            pts.append(Vector((p.x, p.y, -min(0.32, p.z * 0.4))))
for p in FRAME_EXTRA:
    pts.append(p)
    pts.append(Vector((p.x, p.y, -min(0.32, p.z * 0.4))))
scene.render.resolution_x = scene.render.resolution_y = SIZE
for _ in range(30):
    bpy.context.view_layer.update()
    vs = [world_to_camera_view(scene, cam, p) for p in pts]
    xs, ys = [v.x for v in vs], [v.y for v in vs]
    span = max(max(xs) - min(xs), max(ys) - min(ys))
    cam.data.lens *= (0.86 if GEM else 0.9) / span
    cam.data.shift_x += ((min(xs) + max(xs)) / 2 - 0.5) * 0.9
    cam.data.shift_y += ((min(ys) + max(ys)) / 2 - 0.5) * 0.9
if os.environ.get("DEBUG_FRAME"):
    print("FRAME", len(pts), "x", min(xs), max(xs), "y", min(ys), max(ys), "lens", cam.data.lens)
    for p in FRAME_EXTRA:
        v = world_to_camera_view(scene, cam, p)
        print("  extra", [round(c, 2) for c in p], "->", round(v.x, 2), round(v.y, 2))
    for o in objects:
        if o.type == "CURVE":
            print("  curve", o.name, [round(c, 2) for c in o.matrix_world.translation], [round(c, 2) for c in o.matrix_world.to_euler()])
    for o in objects:
        if o.type == "MESH" and not o.hide_render:
            bb = [o.matrix_world @ Vector(c) for c in o.evaluated_get(deps).bound_box]
            print("  ", o.name, [round(min(v[i] for v in bb), 2) for i in range(3)], [round(max(v[i] for v in bb), 2) for i in range(3)])

# --- render ------------------------------------------------------------------------------------------
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 16
scene.cycles.transmission_bounces = 16
scene.cycles.transparent_max_bounces = 32
scene.render.film_transparent = True
scene.cycles.film_transparent_glass = True
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("rendered", OUT)
