"""drawer_probe.py: one Amiga drawer icon in the "glenz / Tron" direction, rendered with Cycles.

    blender -b --factory-startup --python tools/blender/drawer_probe.py -- STATE VARIANT OUT.png [SIZE] [SAMPLES]

STATE   closed | open
VARIANT blend  (depth blend: solid black lacquer in front -> glass -> wireframe at the back)
        glass  (all glenz glass with glowing edges)
        solid  (all black lacquer with glowing edges, Tron)
OUT     a transparent PNG (SIZE x SIZE, default 512); bloom and scaling are done afterwards
        (tools/drawer_probe_sheet.py).

Base colours only: black (lacquer), light blue (hue 210: emitted light, glass tint), white (hot
highlights). A mirrored copy below the floor, fading with depth, gives the floor reflection.
Public domain.
"""
import math
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
STATE, VARIANT, OUT = argv[0], argv[1], argv[2]
SIZE = int(argv[3]) if len(argv) > 3 else 512
SAMPLES = int(argv[4]) if len(argv) > 4 else 128


def srgb(c):
    """sRGB 0..255 -> linear 0..1"""
    def ch(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return (ch(c[0]), ch(c[1]), ch(c[2]), 1.0)


LIGHTBLUE = srgb((148, 194, 240))
ICE = srgb((214, 232, 252))

# --- clean scene --------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# --- materials ----------------------------------------------------------------------------
REFLECT_FADE = 0.55      # depth below the floor over which the reflection fades out
REFLECT_OPACITY = 0.38


def add_reflection_fade(nt, shader_out):
    """objects below the floor (z < 0) are the mirrored copies: fade them out with depth"""
    n = nt.nodes
    geo = n.new("ShaderNodeNewGeometry")
    sep = n.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    rng = n.new("ShaderNodeMapRange")       # z 0 -> REFLECT_OPACITY visible, z -FADE -> 0
    rng.inputs["From Min"].default_value = -REFLECT_FADE
    rng.inputs["From Max"].default_value = 0.0
    rng.inputs["To Min"].default_value = 0.0
    rng.inputs["To Max"].default_value = REFLECT_OPACITY
    nt.links.new(sep.outputs["Z"], rng.inputs["Value"])
    above = n.new("ShaderNodeMath")         # 1 above the floor
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
    return mix.outputs[0]


def depth_factor(nt, d0, d1):
    """0 at the nearest point of the object, 1 at the farthest (camera view depth)"""
    n = nt.nodes
    cam = n.new("ShaderNodeCameraData")
    rng = n.new("ShaderNodeMapRange")
    rng.inputs["From Min"].default_value = d0
    rng.inputs["From Max"].default_value = d1
    nt.links.new(cam.outputs["View Z Depth"], rng.inputs["Value"])
    return rng.outputs["Result"]


def smooth(nt, value, a, b):
    n = nt.nodes
    r = n.new("ShaderNodeMapRange")
    r.interpolation_type = "SMOOTHSTEP"
    r.inputs["From Min"].default_value = a
    r.inputs["From Max"].default_value = b
    nt.links.new(value, r.inputs["Value"])
    return r.outputs["Result"]


def lacquer(nt):
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.004, 0.005, 0.008, 1)
    b.inputs["Roughness"].default_value = 0.22
    b.inputs["Coat Weight"].default_value = 1.0
    b.inputs["Coat Roughness"].default_value = 0.02
    b.inputs["Specular IOR Level"].default_value = 0.6
    return b.outputs[0]


def glass(nt):
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = LIGHTBLUE
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["Roughness"].default_value = 0.02
    b.inputs["IOR"].default_value = 1.45
    if "Dispersion" in b.inputs:
        b.inputs["Dispersion"].default_value = 0.4
    return b.outputs[0]


def body_material(name, d0, d1):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    if VARIANT == "solid":
        sh = lacquer(nt)
    elif VARIANT == "glass":
        sh = glass(nt)
    else:
        f = depth_factor(nt, d0, d1)
        m1 = nt.nodes.new("ShaderNodeMixShader")       # lacquer -> glass
        nt.links.new(smooth(nt, f, 0.3, 0.5), m1.inputs["Fac"])
        nt.links.new(lacquer(nt), m1.inputs[1])
        nt.links.new(glass(nt), m1.inputs[2])
        m2 = nt.nodes.new("ShaderNodeMixShader")       # glass -> see-through (wireframe only)
        nt.links.new(smooth(nt, f, 0.6, 0.82), m2.inputs["Fac"])
        nt.links.new(m1.outputs[0], m2.inputs[1])
        nt.links.new(nt.nodes.new("ShaderNodeBsdfTransparent").outputs[0], m2.inputs[2])
        sh = m2.outputs[0]
    nt.links.new(add_reflection_fade(nt, sh), out.inputs["Surface"])
    return m


def emission_material(name, colour, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = colour
    e.inputs["Strength"].default_value = strength
    nt.links.new(add_reflection_fade(nt, e.outputs[0]), out.inputs["Surface"])
    return m


# --- geometry --------------------------------------------------------------------------------
W, D, H = 2.0, 1.4, 1.45          # cabinet: x width, y depth (front at -D/2), z height
FRONT = -D / 2
objects = []


def box(name, cx, cy, cz, sx, sy, sz, mat, bevel=0.05):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    o = bpy.context.object
    o.name = name
    o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        mod = o.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        mod.limit_method = "NONE"
    o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    objects.append(o)
    return o


def wire(src, name, mat, thickness=0.018):
    """the glowing edges of a box: a copy turned into a wire frame"""
    o = src.copy()
    o.data = src.data.copy()
    o.name = name
    o.modifiers.clear()
    o.data.materials.clear()
    o.data.materials.append(mat)
    w = o.modifiers.new("wire", "WIREFRAME")
    w.thickness = thickness
    w.use_even_offset = True
    w.use_replace = True
    bpy.context.collection.objects.link(o)
    objects.append(o)
    return o


# camera first (the depth blend needs its distances)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
bpy.context.collection.objects.link(cam)
cam.location = (3.4, -5.0, 3.3)
target = Vector((0.05, -0.1, 0.55))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 50
scene.camera = cam

fwd = (target - cam.location).normalized()


def view_depth(p):
    return (Vector(p) - cam.location).dot(fwd)


corners = [(x, y, z) for x in (-W / 2, W / 2) for y in (FRONT, -FRONT) for z in (0, H)]
d0, d1 = min(map(view_depth, corners)), max(map(view_depth, corners))
if STATE == "open":
    d0 -= 0.9 * 0.55

m_body = body_material("body", d0, d1)
m_edge = emission_material("edge", LIGHTBLUE, 2.2)
m_hot = emission_material("hot", LIGHTBLUE, 5.0)

# the cabinet: a shell (open at the front, where the drawer sits)
shell = box("cabinet", 0, 0, H / 2, W, D, H, m_body, 0.06)
wire(shell, "cabinet_wire", m_edge, 0.016)

# the drawer: front plate + tray
DW, DH = W - 0.26, H - 0.36
out_by = 0.9 if STATE == "open" else 0.0
dz = 0.18 + DH / 2
plate = box("plate", 0, FRONT - 0.035 - out_by, dz, DW, 0.07, DH, m_body, 0.03)
wire(plate, "plate_wire", m_edge, 0.014)
handle = box("handle", 0, FRONT - 0.09 - out_by, dz + DH * 0.24, DW * 0.42, 0.06, 0.07, m_hot, 0.02)
# two light lines on the top (Tron circuit trace)
for i, x in enumerate((-0.55, -0.35)):
    t = box(f"trace{i}", x, -0.05, H + 0.004, 0.03, D * 0.75, 0.01, m_edge, 0)
if STATE == "open":
    tray = box("tray", 0, FRONT - out_by + 0.6, 0.18 + DH * 0.4, DW - 0.1, 1.2, DH * 0.78, m_body, 0.03)
    wire(tray, "tray_wire", m_edge, 0.014)
    for i in range(4):
        card = box(f"card{i}", -0.55 + i * 0.36, FRONT - out_by + 0.45, 0.18 + DH * 0.62, 0.05, 0.75, DH * 0.62,
                   emission_material(f"card{i}", LIGHTBLUE, 0.9 if i % 2 else 1.3), 0.01)
        wire(card, f"card{i}_wire", m_edge, 0.012)

# the floor reflection: mirrored copies below z = 0
for o in list(objects):
    r = o.copy()
    r.data = o.data
    r.name = o.name + "_mirror"
    r.scale = (1, 1, -1)
    r.location = (o.location.x, o.location.y, -o.location.z)
    bpy.context.collection.objects.link(r)

# --- the studio: black, with strip lights that the lacquer and glass reflect -------------------
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
    """1 near centre, 0 away from it (sharp-edged soft box)"""
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
for axis, centre, width, gain in (("Z", 0.55, 0.06, 1.0), ("Z", -0.25, 0.05, 0.7), ("X", -0.75, 0.05, 0.8),
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
key.location = (-1.5, -2.5, 4.5)
key.rotation_euler = (Vector((0, 0, 0.6)) - key.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.collection.objects.link(key)

# --- frame the drawer and its reflection -----------------------------------------------------
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402

pts = [Vector(c) for c in corners] + [Vector((x, y, -0.35)) for x in (-W / 2, W / 2) for y in (FRONT, -FRONT)]
if STATE == "open":
    pts += [Vector((x, FRONT - 0.95, z)) for x in (-W / 2, W / 2) for z in (-0.3, 0, H)]
scene.render.resolution_x = scene.render.resolution_y = SIZE
for _ in range(30):
    bpy.context.view_layer.update()
    vs = [world_to_camera_view(scene, cam, p) for p in pts]
    xs, ys = [v.x for v in vs], [v.y for v in vs]
    span = max(max(xs) - min(xs), max(ys) - min(ys))
    cam.data.lens *= 0.9 / span
    # shift so the content is centred
    cam.data.shift_x += ((min(xs) + max(xs)) / 2 - 0.5) * 0.9
    cam.data.shift_y += ((min(ys) + max(ys)) / 2 - 0.5) * 0.9

# --- render ----------------------------------------------------------------------------------
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
