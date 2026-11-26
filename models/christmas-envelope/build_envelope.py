"""Build the Christmas envelope hero model. Run inside Blender.

Envelope lies in the XZ plane and faces -Y (becomes +Z in glTF).
The flap pivots on the top edge: a negative X rotation opens it.
"""

import json
import math
import random
import struct

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
LINING = material("WarmLining", "9D3F2D", 0.85)
CREAM = material("Cream", "F6EEDC", 0.8)
GREEN = material("PineGreen", "14633A", 0.55)
SATIN = material("SatinRibbon", "2B8F66", 0.31)
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


def paper_uv(obj):
    mesh = obj.data
    uv = mesh.uv_layers.new(name="Paper")
    for loop in mesh.loops:
        point = mesh.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (point.x / W, point.z / H)


root = link(bpy.data.objects.new("Envelope", None))
bpy.context.view_layer.update()

# Back panel
paper_uv(prism("Back", [(-HW, -HH), (HW, -HH), (HW, HH), (-HW, HH)], 0.06, 0.025, RED_BACK, root, 0.01))

# Letter card tucked inside
letter = link(bpy.data.objects.new("Letter", None), root)
bpy.context.view_layer.update()
LW, LT, LB = 1.46, 0.93, -0.95
letter["paperBounds"] = [-LW, LB, LW, LT]
paper_uv(prism("LetterPaper", [(-LW, LB), (LW, LB), (LW, LT), (-LW, LT)], 0.0, 0.014, CREAM, letter, 0.004))
for inset, mat, radius in ((0.09, GREEN, 0.014), (0.14, GOLD, 0.008)):
    l, r, t, b = -LW + inset, LW - inset, LT - inset, LB + inset
    trim("LetterBorder", [(l, b), (r, b), (r, t), (l, t), (l, b)], -radius - 0.004, mat, letter, radius)
# Move the completed letter assembly behind the folds, without parent-inverse cancellation.
letter.location.y = 0.02
bpy.context.view_layer.update()

# Front pocket: two side folds and the bottom fold
paper_uv(prism("PocketLeft", [(-HW, -HH), (-0.02, -0.05), (-HW, HH)], -0.030, 0.012, RED_SIDE, root))
paper_uv(prism("PocketRight", [(HW, -HH), (HW, HH), (0.02, -0.05)], -0.030, 0.012, RED_SIDE, root))
paper_uv(prism("PocketBottom", [(-HW, -HH), (HW, -HH), (0.0, 0.17)], -0.044, 0.012, RED_BOTTOM, root))
trim("PocketTrim", [(-HW + 0.03, -HH + 0.02), (0.0, 0.15), (HW - 0.03, -HH + 0.02)], -0.058, GOLD, root, 0.010)

# A folded shoulder brings the flap over the pocket from a real pivot inside
# the back panel. The same mesh carries the lining on its reverse face.
hinge = Vector((0.0, 0.073, HH - 0.006))
crease_z = HH - 0.11
crease_x = HW + (0.12 - HW) * (HH - crease_z) / (HH + 0.2)
outline = [
    (-HW, hinge.y, hinge.z), (HW, hinge.y, hinge.z),
    (crease_x, -0.068, crease_z), (0.12, -0.068, -0.2),
    (0.0, -0.068, -0.245), (-0.12, -0.068, -0.2),
    (-crease_x, -0.068, crease_z),
]
count = len(outline)
vertices = [Vector((x, y + depth, z)) - hinge for depth in (0.0, 0.012) for x, y, z in outline]
panels = [(0, 1, 2, 6), (6, 2, 3, 4, 5)]
faces = panels + [tuple(i + count for i in panel) for panel in panels]
for i in range(count):
    j = (i + 1) % count
    faces.append((i, j, j + count, i + count))
mesh = bpy.data.meshes.new("Flap")
mesh.from_pydata(vertices, [], faces)
mesh.materials.append(RED)
mesh.materials.append(LINING)
for poly in mesh.polygons[2:4]:
    poly.material_index = 1
bm = bmesh.new()
bm.from_mesh(mesh)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(mesh)
bm.free()
flap = link(bpy.data.objects.new("Flap", mesh), root)
flap.location = hinge
paper_uv(flap)
bevel = flap.modifiers.new("Fold edges", "BEVEL")
bevel.width = 0.004
bevel.segments = 2
bpy.context.view_layer.update()
trim("FlapTrim", [(-HW + 0.22, HH - 0.14), (-0.11, -0.14), (0.0, -0.18), (0.11, -0.14), (HW - 0.22, HH - 0.14)],
     -0.084, GOLD, flap, 0.012)

# A crowned cross section gives the satin its highlight as the flap turns.
def ribbon_strip(bm, center, widths, steps, crown):
    rows = []
    for i in range(steps + 1):
        t = i / steps
        tangent = center(min(t + 0.001, 1)) - center(max(t - 0.001, 0))
        cross = Vector((tangent.z, 0, -tangent.x)).normalized()
        width = widths[0] + (widths[1] - widths[0]) * math.sin(math.pi * t / 2)
        point = center(t)
        profile = ((-1, 0), (0, -crown), (1, 0), (1, 0.005), (0, 0.005 - crown), (-1, 0.005))
        rows.append([bm.verts.new(point + side * width * cross + Vector((0, depth, 0)))
                     for side, depth in profile])
    for a, b in zip(rows, rows[1:]):
        for k in range(len(a)):
            j = (k + 1) % len(a)
            bm.faces.new((a[k], a[j], b[j], b[k]))
    bm.faces.new(tuple(reversed(rows[0])))
    bm.faces.new(tuple(rows[-1]))


def finish_ribbon(name, bm, pivot):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.translate(bm, verts=list(bm.verts), vec=-Vector(pivot))
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(SATIN)
    for poly in mesh.polygons:
        poly.use_smooth = True
    ribbon = link(bpy.data.objects.new(name, mesh), root)
    ribbon.location = pivot
    return ribbon


bow_center = Vector((0.97, -0.175, 0.79))
bow_mesh = bmesh.new()


def bow_strip(points, widths, steps):
    a, b, c, d = points

    def center(t):
        u = 1.0 - t
        return bow_center + a * (u ** 3) + b * (3 * t * u ** 2) + c * (3 * u * t ** 2) + d * (t ** 3)

    ribbon_strip(bow_mesh, center, widths, steps, 0.019)


for sign in (-1, 1):
    bow_strip([Vector((sign * x, y, z)) for x, y, z in
               ((0.052, -0.014, 0.034), (0.51, -0.097, 0.28), (0.48, -0.076, -0.22), (0.051, -0.019, -0.043))],
              (0.032, 0.059), 17)
    bow_strip([Vector((sign * x, y, z)) for x, y, z in
               ((0.032, -0.006, -0.031), (0.040, -0.056, -0.120), (0.178, -0.041, -0.217), (0.154, -0.032, -0.300))],
              (0.031, 0.057), 10)

knot = bmesh.ops.create_uvsphere(bow_mesh, u_segments=16, v_segments=8, radius=1)["verts"]
for v in knot:
    v.co = bow_center + Vector((v.co.x * 0.082, v.co.y * 0.044, v.co.z * 0.072))

# The crossing band and upper end share the knot mesh. The loose lower end
# has its own pivot so it can lag behind the bow as the wrapping slips off.


def cross_band(t):
    x = 3.14 * (t - 0.5)
    edge = max(0, (abs(x) - 1.39) / 0.18)
    return Vector((x, -0.122 + 0.029 * edge ** 2, 0.804 + 0.012 * math.sin(math.pi * t)))


def upper_band(t):
    z = 0.438 + 0.522 * t
    lift = max(0, min(1, (z - 0.52) / 0.20, (0.96 - z) / 0.07))
    return Vector((bow_center.x, -0.108 - 0.043 * lift * lift * (3 - 2 * lift), z))


ribbon_strip(bow_mesh, cross_band, (0.062, 0.062), 16, 0.006)
ribbon_strip(bow_mesh, upper_band, (0.068, 0.068), 9, 0.008)
bow = finish_ribbon("RibbonBow", bow_mesh, (0, -0.14, 0.8))

pocket_band = bmesh.new()
ribbon_strip(pocket_band, lambda t: Vector((bow_center.x, -0.083 - 0.021 * t, -1.056 + 1.473 * t)),
             (0.068, 0.068), 6, 0.009)
band = finish_ribbon("RibbonPocketBand", pocket_band, (bow_center.x, -0.104, 0.417))

# The medallion is assembled from five pieces with matching radial seams.
SZ = -0.17
seal = link(bpy.data.objects.new("Seal", None), flap)
seal.location = (0, 0, 0)
bpy.context.view_layer.update()
blob = []
for i in range(48):
    a = i / 48 * math.tau
    r = 0.30 + 0.014 * math.sin(a * 5 + 0.7) + 0.009 * math.sin(a * 11) + random.uniform(-0.004, 0.004)
    blob.append((r * math.cos(a), SZ + r * math.sin(a)))


def clip_seal_face(points, angle, side):
    """Clip the gold relief against one side of a radial seam."""
    def distance(point):
        return side * (math.cos(angle) * (point[1] - SZ) - math.sin(angle) * point[0])

    clipped = []
    for start, end in zip(points[-1:] + points[:-1], points):
        d0, d1 = distance(start), distance(end)
        if (d0 < 0) != (d1 < 0):
            t = d0 / (d0 - d1)
            clipped.append(tuple(a + (b - a) * t for a, b in zip(start, end)))
        if d1 >= 0:
            clipped.append(end)
    return [p for i, p in enumerate(clipped) if math.dist(p, clipped[i - 1]) > 1e-7]


cuts = [2, 11, 22, 32, 41]
shards = []
seal["crackRays"] = [coordinate for i in cuts for coordinate in blob[i]]
for index, (first, last) in enumerate(zip(cuts, cuts[1:] + [cuts[0] + len(blob)])):
    a0, a1 = (i * math.tau / len(blob) for i in (first, last))
    polygon = [(0, SZ)] + [blob[i % len(blob)] for i in range(first, last + 1)]
    pivot_x = sum(p[0] for p in polygon) / len(polygon)
    pivot_z = sum(p[1] for p in polygon) / len(polygon)
    piece = link(bpy.data.objects.new(f"SealShard{index + 1}", None), seal)
    piece.location = (pivot_x, -0.11, pivot_z)
    shards.append(piece)
    bpy.context.view_layer.update()
    prism(f"SealWax{index}", polygon, -0.135, 0.06, WAX, piece, 0.003)
    ring = [(0.215 * math.cos(a0 + (a1 - a0) * i / 14), SZ + 0.215 * math.sin(a0 + (a1 - a0) * i / 14))
            for i in range(15)]
    trim(f"SealRing{index}", ring, -0.150, GOLD, piece, 0.011)
    relief = clip_seal_face(clip_seal_face(star(0, SZ, 0.17, 0.074), a0, 1), a1, -1)
    prism(f"SealStar{index}", relief, -0.168, 0.023, GOLD, piece, 0.0025)


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
               0.36, shards[3], -0.162 - 0.004 * index)
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
    link(berry, shards[3])
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

# Reproducible opening animation. The burst starts on the flap's final
# swing, and the letter begins its eased lift while the burst is active.
scene.render.fps = 24
scene.frame_start, scene.frame_end = 1, 83
burst_frame = scene.timeline_markers.new("Burst", frame=40).frame
root["burstTime"] = (burst_frame - scene.frame_start) / scene.render.fps
break_frame = scene.timeline_markers.new("Seal break", frame=13).frame
root["sealBreakTime"] = (break_frame - scene.frame_start) / scene.render.fps
for frame, angle in ((1, 0), (12, 0), (19, -32), (34, -138), (49, -174), (scene.frame_end, -174)):
    flap.rotation_euler.x = math.radians(angle)
    flap.keyframe_insert(data_path="rotation_euler", frame=frame, group="Flap")
for frame, height in ((1, 0), (44, 0), (53, 0.19), (70, 1.55), (scene.frame_end, 2.12)):
    letter.location.z = height
    letter.keyframe_insert(data_path="location", frame=frame, group="Letter")

# Peel forward before twisting the bow inward. The lower band lags behind
# and lifts slightly to clear the pocket before dropping away.
for ribbon, fade_frames, poses in (
    (bow, (18, 23), (
        (1, (0, 0, 0), (0, 0, 0)),
        (12, (0, 0, 0), (0, 0, 0)),
        (17, (0.012, -0.49, 0.15), (9, 7, -2)),
        (24, (-0.11, -1.14, 0.055), (39, 36, -3)),
        (31, (0.03, -1.65, -0.77), (82, 57, -14)),
        (44, (-0.10, -1.45, -4.3), (251, 32, -82)),
        (55, (0.04, -1.85, -9.0), (332, 50, -108)),
    )),
    (band, (22, 28), (
        (1, (0, 0, 0), (0, 0, 0)),
        (14, (0, 0, 0), (0, 0, 0)),
        (19, (0.025, -0.18, 0.13), (-6, -5, 4)),
        (25, (0.14, -0.32, 0.17), (-7, -13, 13)),
        (32, (0.29, -0.44, 0.04), (-37, -29, 26)),
        (43, (0.45, -1.15, -4.3), (-167, -58, 44)),
        (55, (0.56, -1.35, -9.0), (-284, -85, 76)),
    )),
):
    ribbon["releaseFade"] = [(frame - scene.frame_start) / scene.render.fps for frame in fade_frames]
    pivot = ribbon.location.copy()
    for frame, offset, angles in poses:
        ribbon.location = pivot + Vector(offset)
        ribbon.rotation_euler = tuple(map(math.radians, angles))
        ribbon.keyframe_insert(data_path="location", frame=frame, group=ribbon.name)
        ribbon.keyframe_insert(data_path="rotation_euler", frame=frame, group=ribbon.name)

# One glTF clip, with an NLA track shared by all animated objects.
for obj in (flap, letter, bow, band):
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
bpy.context.preferences.filepaths.save_version = 0
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


def sort_exported_triangles(path):
    """Stabilize Blender's triangle ordering while preserving every face's winding."""
    data = bytearray(path.read_bytes())
    json_end = 20 + struct.unpack_from("<I", data, 12)[0]
    gltf = json.loads(data[20:json_end])
    bin_start = json_end + 8
    index_formats = {5121: "B", 5123: "H", 5125: "I"}
    for mesh in gltf["meshes"]:
        for primitive in mesh["primitives"]:
            if primitive.get("mode", 4) != 4 or "indices" not in primitive:
                continue
            accessor = gltf["accessors"][primitive["indices"]]
            view = gltf["bufferViews"][accessor["bufferView"]]
            offset = bin_start + view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
            triangle = struct.Struct("<" + index_formats[accessor["componentType"]] * 3)
            length = accessor["count"] // 3 * triangle.size
            ordered = sorted(
                min((a, b, c), (b, c, a), (c, a, b))
                for a, b, c in triangle.iter_unpack(data[offset:offset + length])
            )
            for i, indices in enumerate(ordered):
                triangle.pack_into(data, offset + i * triangle.size, *indices)
    path.write_bytes(data)


select_tree(root)
glb_path = out / "envelope.glb"
bpy.ops.export_scene.gltf(filepath=str(glb_path), export_format="GLB",
                          use_selection=True, export_animations=True, export_extras=True,
                          export_animation_mode="NLA_TRACKS")
sort_exported_triangles(glb_path)
