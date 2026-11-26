"""Build the Christmas envelope hero model. Run inside Blender.

Envelope lies in the XZ plane and faces -Y (becomes +Z in glTF).
The flap pivots on the top edge: a negative X rotation opens it.
"""

import math
import random

import bmesh
import bpy
from mathutils import Vector

W, H = 3.2, 2.1
HW, HH = W / 2, H / 2

random.seed(7)

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for block in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras, bpy.data.curves):
    for item in list(block):
        if item.users == 0:
            block.remove(item)

scene = bpy.context.scene


def linear(hex_color):
    def channel(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return tuple(channel(int(hex_color[i:i + 2], 16) / 255) for i in (0, 2, 4)) + (1.0,)


def material(name, color, rough=0.6, metal=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = linear(color)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    return mat


RED = material("RedPaper", "A80C1A", 0.55)
RED_SIDE = material("RedPaperSide", "940A17", 0.55)
RED_BOTTOM = material("RedPaperBottom", "B20F1E", 0.55)
RED_BACK = material("RedPaperBack", "6E0A14", 0.7)
CREAM = material("Cream", "F6EEDC", 0.8)
GREEN = material("PineGreen", "14633A", 0.55)
GOLD = material("Gold", "FFE29A", 0.24, 1.0)
WAX = material("GoldWax", "B87A22", 0.42, 0.85)
BERRY = material("Berry", "D3172B", 0.25)


def link(obj, parent=None):
    scene.collection.objects.link(obj)
    if parent:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj


def prism(name, points, y, depth, mat, parent=None, bevel=0.006, origin=(0, 0, 0)):
    """Extrude an XZ polygon from y towards the back by depth."""
    origin = Vector(origin)
    bm = bmesh.new()
    front = [bm.verts.new(Vector((x, y, z)) - origin) for x, z in points]
    face = bm.faces.new(front)
    extruded = bmesh.ops.extrude_face_region(bm, geom=[face])
    back = [v for v in extruded["geom"] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=back, vec=(0, depth, 0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = origin
    if bevel:
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = "ANGLE"
    return link(obj, parent)


def trim(name, points, y, mat, parent=None, radius=0.012):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    # Closed borders must not have overlapping end caps at the same point.
    closed = math.dist(points[0], points[-1]) < 1e-6
    if closed:
        points = points[:-1]
    curve.use_fill_caps = not closed
    spline = curve.splines.new("POLY")
    spline.use_cyclic_u = closed
    spline.points.add(len(points) - 1)
    for point, (x, z) in zip(spline.points, points):
        point.co = (x, y, z, 1)
    curve.materials.append(mat)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.view_layer.update()
    return link(obj, parent)


def star(cx, cz, outer, inner, spikes=5):
    pts = []
    for i in range(spikes * 2):
        r = outer if i % 2 == 0 else inner
        a = math.pi / 2 + i * math.pi / spikes
        pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return pts


root = link(bpy.data.objects.new("Envelope", None))
bpy.context.view_layer.update()

# Back panel
prism("Back", [(-HW, -HH), (HW, -HH), (HW, HH), (-HW, HH)], 0.06, 0.025, RED_BACK, root, 0.01)

# Letter card tucked inside
letter = link(bpy.data.objects.new("Letter", None), root)
bpy.context.view_layer.update()
LW, LT, LB = 1.46, 0.93, -0.95
prism("LetterPaper", [(-LW, LB), (LW, LB), (LW, LT), (-LW, LT)], 0.0, 0.014, CREAM, letter, 0.004)
for inset, mat, radius in ((0.09, GREEN, 0.014), (0.14, GOLD, 0.008)):
    l, r, t, b = -LW + inset, LW - inset, LT - inset, LB + inset
    trim("LetterBorder", [(l, b), (r, b), (r, t), (l, t), (l, b)], -radius - 0.004, mat, letter, radius)
prism("LetterStar", star(0, 0.52, 0.17, 0.072), -0.016, 0.012, GOLD, letter, 0.003)
# Move the completed letter assembly behind the folds, without parent-inverse cancellation.
letter.location.y = 0.02
bpy.context.view_layer.update()

# Front pocket: two side folds and the bottom fold
prism("PocketLeft", [(-HW, -HH), (-0.02, -0.05), (-HW, HH)], -0.030, 0.012, RED_SIDE, root)
prism("PocketRight", [(HW, -HH), (HW, HH), (0.02, -0.05)], -0.030, 0.012, RED_SIDE, root)
prism("PocketBottom", [(-HW, -HH), (HW, -HH), (0.0, 0.17)], -0.044, 0.012, RED_BOTTOM, root)
trim("PocketTrim", [(-HW + 0.03, -HH + 0.02), (0.0, 0.15), (HW - 0.03, -HH + 0.02)], -0.058, GOLD, root, 0.010)

# Flap, pivoting on the top edge
hinge = (0.0, 0.015, HH)  # behind the letter, so the open flap clears it
flap = prism("Flap", [(-HW, HH), (HW, HH), (0.12, -0.2), (0.0, -0.245), (-0.12, -0.2)],
             -0.068, 0.012, RED, root, 0.006, hinge)
bpy.context.view_layer.update()
trim("FlapTrim", [(-HW + 0.09, HH - 0.02), (-0.11, -0.14), (0.0, -0.18), (0.11, -0.14), (HW - 0.09, HH - 0.02)],
     -0.084, GOLD, flap, 0.012)

# Wax seal, its own group so the web layer can break it before the flap opens
SZ = -0.17
seal = link(bpy.data.objects.new("Seal", None), flap)
seal.location = (0, 0, 0)
bpy.context.view_layer.update()
blob = []
for i in range(48):
    a = i / 48 * math.tau
    r = 0.30 + 0.014 * math.sin(a * 5 + 0.7) + 0.009 * math.sin(a * 11) + random.uniform(-0.004, 0.004)
    blob.append((r * math.cos(a), SZ + r * math.sin(a)))
prism("SealWax", blob, -0.135, 0.06, WAX, seal, 0.022)
trim("SealRing", [(0.215 * math.cos(i / 64 * math.tau), SZ + 0.215 * math.sin(i / 64 * math.tau)) for i in range(65)],
     -0.152, GOLD, seal, 0.013)
prism("SealStar", star(0, SZ, 0.17, 0.074), -0.168, 0.025, GOLD, seal, 0.006)


def holly_leaf(name, cx, cz, angle, length, parent, y):
    half = []
    for i in range(13):
        t = i / 12
        spike = 1.0 if i % 3 else 1.35
        half.append((t * length, math.sin(math.pi * t) * length * 0.23 * spike))
    outline = half + [(x, -z) for x, z in reversed(half[1:-1])]
    c, s = math.cos(angle), math.sin(angle)
    pts = [(cx + x * c - z * s, cz + x * s + z * c) for x, z in outline]
    prism(name, pts, y, 0.016, GREEN, parent, 0.004)
    trim(name + "Vein", [(cx, cz), (cx + 0.82 * length * c, cz + 0.82 * length * s)], y - 0.010, GOLD, parent, 0.005)


# Holly sprig on the seal
for index, degrees in enumerate((155, 25)):
    a = math.radians(degrees)
    holly_leaf(f"SealHolly{index}", 0.17 * math.cos(a), SZ - 0.19 + 0.02 * index, a if index else a + 0.35,
               0.36, seal, -0.162 - 0.004 * index)
for index, (bx, bz) in enumerate(((-0.055, SZ - 0.21), (0.055, SZ - 0.215), (0.0, SZ - 0.275))):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=0.056)
    mesh = bpy.data.meshes.new(f"Berry{index}")
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(BERRY)
    for poly in mesh.polygons:
        poly.use_smooth = True
    berry = bpy.data.objects.new(f"Berry{index}", mesh)
    berry.location = (bx, -0.19, bz)
    link(berry, seal)
    bpy.context.view_layer.update()


# Preview camera and lights (not part of the exported model)
def aim(obj, target=(0, 0, 0)):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


camera = bpy.data.objects.new("PreviewCamera", bpy.data.cameras.new("PreviewCamera"))
camera.data.lens = 70
camera.location = (1.5, -7.2, 0.9)
aim(camera)
link(camera)
scene.camera = camera

for name, location, energy, size, color in (
    ("Key", (-3.0, -3.5, 3.0), 180, 3.0, (1.0, 0.93, 0.82)),
    ("Fill", (3.8, -3.0, 0.3), 70, 4.0, (0.85, 0.92, 1.0)),
    ("Rim", (1.5, 1.8, 2.8), 140, 2.0, (1.0, 0.78, 0.45)),
):
    light = bpy.data.lights.new(name, "AREA")
    light.energy, light.size, light.color = energy, size, color
    obj = bpy.data.objects.new(name, light)
    obj.location = location
    aim(obj)
    link(obj)

world = scene.world or bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
# Camera sees deep pine green; reflections and bounce light see a warm studio tone
tree = world.node_tree
tree.nodes.clear()
studio = tree.nodes.new("ShaderNodeBackground")
studio.inputs["Color"].default_value = linear("8F7D66")
backdrop = tree.nodes.new("ShaderNodeBackground")
backdrop.inputs["Color"].default_value = linear("0B2A1E")
path = tree.nodes.new("ShaderNodeLightPath")
mix = tree.nodes.new("ShaderNodeMixShader")
output = tree.nodes.new("ShaderNodeOutputWorld")
tree.links.new(path.outputs["Is Camera Ray"], mix.inputs[0])
tree.links.new(studio.outputs[0], mix.inputs[1])
tree.links.new(backdrop.outputs[0], mix.inputs[2])
tree.links.new(mix.outputs[0], output.inputs["Surface"])

scene.view_settings.view_transform = "Standard"
scene.render.resolution_x, scene.render.resolution_y = 1200, 900

bpy.context.view_layer.update()
print("objects:", len(scene.objects), "flap origin:", tuple(round(v, 3) for v in flap.location))

# Reproducible opening animation. Frames 10–18 dissolve the seal; the flap
# clears the letter before it rises. glTF exports the three actions together.
scene.render.fps = 24
scene.frame_start, scene.frame_end = 1, 112
for frame, scale in ((1, 1.0), (10, 1.0), (18, 0.001)):
    seal.scale = (scale,) * 3
    seal.keyframe_insert(data_path="scale", frame=frame, group="Seal")
for frame, angle in ((1, 0), (18, 0), (62, -178), (112, -178)):
    flap.rotation_euler.x = math.radians(angle)
    flap.keyframe_insert(data_path="rotation_euler", frame=frame, group="Flap")
# The flap face starts 0.083 in front of its hinge. As it rotates that
# offset would lift the visible top edge away from the envelope. Compensate
# vertically for the rotated offset while preserving its depth through the fold.
face_offset = hinge[1] - (-0.068)
for frame in range(1, 113):
    scene.frame_set(frame)
    flap.location.z = hinge[2] + face_offset * math.sin(flap.rotation_euler.x)
    flap.keyframe_insert(data_path="location", index=2, frame=frame, group="Flap")
for frame, height in ((1, 0), (72, 0), (112, 1.25)):
    letter.location.z = height
    letter.keyframe_insert(data_path="location", frame=frame, group="Letter")
# One glTF clip, with an NLA track shared by all animated objects.
for obj in (seal, flap, letter):
    action = obj.animation_data.action
    action.name = "Open_" + obj.name
    track = obj.animation_data.nla_tracks.new()
    track.name = "Open"
    track.strips.new(action.name, 1, action)
    obj.animation_data.action = None
scene.frame_set(1)
from pathlib import Path
out = Path(__file__).resolve().parent
bpy.context.preferences.filepaths.file_preview_type = "NONE"
bpy.ops.wm.save_as_mainfile(filepath=str(out / "envelope.blend"))
# Curves are explicitly made meshes before export; retain the authored blend.
for obj in list(scene.objects):
    if obj.type == "CURVE":
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.convert(target="MESH")
bpy.ops.object.select_all(action="DESELECT")
def select_tree(obj):
    obj.select_set(True)
    for child in obj.children:
        select_tree(child)
select_tree(root)
bpy.ops.export_scene.gltf(filepath=str(out / "envelope.glb"), export_format="GLB",
                          use_selection=True, export_animations=True,
                          export_animation_mode="NLA_TRACKS")
