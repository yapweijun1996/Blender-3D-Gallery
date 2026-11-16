"""Deterministic, texture-free GJH Chibi Visitor. Run in a separate background Blender."""
from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Euler, Matrix, Vector

ROOT = Path(__file__).resolve().parent
TAU = math.tau
PALETTE = {"white": "F4F2FA", "ink": "2A2838", "purple": "8B5CF6", "lavender": "D9CCF7"}
SCENE = None
M = {}
OUTLINE_SCALE = 1.80
SIDES = [(-1, "R"), (1, "L")]  # Anatomical sides: +X is the character's left.


def linear(v):
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def rgba(hex_color):
    return tuple(linear(int(hex_color[i:i + 2], 16) / 255) for i in (0, 2, 4)) + (1,)


def material(name, color, roughness=.55, metallic=0, emission=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = rgba(color)
    mat.use_nodes = True
    p = mat.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = rgba(color)
    p.inputs["Roughness"].default_value = roughness
    p.inputs["Metallic"].default_value = metallic
    if emission:
        p.inputs["Emission Color"].default_value = rgba(color)
        p.inputs["Emission Strength"].default_value = emission
    mat.use_backface_culling = True
    return mat


def materials():
    M.update({
        "white": material("Porcelain | #F4F2FA", PALETTE["white"], .46),
        "cloth": material("Hoodie cotton | #F4F2FA", PALETTE["white"], .82),
        "ink": material("Graphite | #2A2838", PALETTE["ink"], .52),
        "screen": material("Glossy face screen | #2A2838", PALETTE["ink"], .24, .12),
        "purple": material("Violet | #8B5CF6", PALETTE["purple"], .60),
        "lavender": material("Lavender | #D9CCF7", PALETTE["lavender"], .62),
        "hood": material("Purple hood lining", "65458D", .85),
        "hood_roll": material("Saturated violet hood roll", "8454C5", .85),
        "fin_inset": material("Soft lavender fin inset", "E7DFF5", .74),
        "edge": material("Ink outline | inverted hull", "242130", 1),
        "light": material("Violet emission | eyes and rings", "7940F2", .50, emission=1.5),
        "light_core": material("Lavender emission core", "B697FA", .60, emission=.75),
        "eye_core": material("Soft lavender eye emission core", "B697FA", .60, emission=.70),
        "heart": material("Heart emission", "C780FA", .45, emission=2.5),
        "seam": material("Lavender seam", "C2B5DB", .82),
    })
    # Unlit ink retains a consistent hand-drawn edge in both Eevee and glTF.
    p = M["edge"].node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (0, 0, 0, 1)
    p.inputs["Emission Color"].default_value = rgba("242130")
    p.inputs["Emission Strength"].default_value = 1
    M["fin_gradient"] = material("Porcelain with gradual lavender fin inset", "FFFFFF", .74)
    tint = M["fin_gradient"].node_tree.nodes.new("ShaderNodeVertexColor")
    tint.layer_name = "FinTint"
    M["fin_gradient"].node_tree.links.new(tint.outputs["Color"], M["fin_gradient"].node_tree.nodes.get("Principled BSDF").inputs["Base Color"])


def empty(name, parent=None, loc=(0, 0, 0)):
    ob = bpy.data.objects.new(name, None)
    SCENE.collection.objects.link(ob)
    ob.parent = parent
    ob.location = loc
    ob.empty_display_size = .035
    return ob


def mesh(name, vertices, faces, mat, parent=None, smooth=True, outline=0):
    data = bpy.data.meshes.new(name + "_Mesh")
    data.from_pydata(vertices, [], faces)
    data.update()
    ob = bpy.data.objects.new(name, data)
    SCENE.collection.objects.link(ob)
    ob.parent = parent
    data.materials.append(mat)
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    for p in data.polygons:
        p.use_smooth = smooth
    if outline:
        add_outline(ob, outline)
    return ob


def add_outline(ob, width=.0015):
    width *= OUTLINE_SCALE
    data = ob.data.copy()
    data.name = ob.name + "_InvertedHullMesh"
    # Ink must not inherit the fin's color channel or tint its exported shell.
    for attribute in list(data.color_attributes):
        data.color_attributes.remove(attribute)
    data.materials.clear()
    data.materials.append(M["edge"])
    bm = bmesh.new()
    bm.from_mesh(data)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * width
    bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    outline = bpy.data.objects.new(ob.name + "__Outline", data)
    SCENE.collection.objects.link(outline)
    outline.parent = ob
    outline["technique"] = "Inverted hull; inward winding; single-sided ink material"
    outline["width_m"] = width
    if hasattr(outline, "visible_shadow"):
        outline.visible_shadow = False
    return outline


def bevel_box(name, loc, size, bevel, mat, parent=None, outline=.0014, segments=3):
    bpy.ops.mesh.primitive_cube_add(size=1)
    ob = bpy.context.object
    ob.name = name
    ob.parent = parent
    ob.location = loc
    for v in ob.data.vertices:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
    ob.data.materials.append(mat)
    mod = ob.modifiers.new("Soft manufactured edge", "BEVEL")
    mod.width = bevel
    mod.segments = segments
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=mod.name)
    for p in ob.data.polygons:
        p.use_smooth = True
    mod = ob.modifiers.new("Weighted surface normals", "WEIGHTED_NORMAL")
    mod.keep_sharp = True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    if outline:
        add_outline(ob, outline)
    return ob


def spow(v, power):
    return math.copysign(abs(v) ** power, v)


def ellipsoid(name, loc, scale, mat, parent=None, segments=28, rings=16, power=2, outline=0):
    verts = [(0, -scale[1], 0)]
    for j in range(1, rings):
        phi = -math.pi / 2 + math.pi * j / rings
        radial = math.cos(phi) ** (2 / power)
        for i in range(segments):
            theta = TAU * i / segments
            verts.append((scale[0] * radial * spow(math.cos(theta), 2 / power),
                          scale[1] * spow(math.sin(phi), 2 / power),
                          scale[2] * radial * spow(math.sin(theta), 2 / power)))
    end = len(verts)
    verts.append((0, scale[1], 0))
    faces = []
    for i in range(segments):
        faces.append((0, 1 + (i + 1) % segments, 1 + i))
    for j in range(rings - 2):
        a = 1 + j * segments
        b = a + segments
        for i in range(segments):
            n = (i + 1) % segments
            faces.append((a + i, a + n, b + n, b + i))
    a = 1 + (rings - 2) * segments
    for i in range(segments):
        faces.append((a + i, a + (i + 1) % segments, end))
    ob = mesh(name, verts, faces, mat, parent, outline=outline)
    ob.location = loc
    return ob


def loft(name, rows, mat, parent=None, n=28, power=2.5, outline=.0014, soften=False):
    verts, faces = [], []
    for z, w, d, cy in rows:
        for i in range(n):
            a = TAU * i / n
            verts.append((w * spow(math.cos(a), 2 / power), cy + d * spow(math.sin(a), 2 / power), z))
    for j in range(len(rows) - 1):
        for i in range(n):
            a, b = j * n + i, j * n + (i + 1) % n
            faces.append((a, b, b + n, a + n))
    faces.extend([tuple(reversed(range(n))), tuple((len(rows) - 1) * n + i for i in range(n))])
    ob = mesh(name, verts, faces, mat, parent)
    if soften:
        bpy.context.view_layer.objects.active = ob
        mod = ob.modifiers.new("Soft fabric contours", "SUBSURF")
        mod.levels = 1
        bpy.ops.object.modifier_apply(modifier=mod.name)
    if outline:
        add_outline(ob, outline)
    return ob


def tube(name, points, radius, mat, parent=None, sides=8, closed=False, outline=0):
    points = [Vector(p) for p in points]
    verts, faces = [], []
    tangents = []
    for j in range(len(points)):
        tangent = (points[(j + 1) % len(points)] - points[(j - 1) % len(points)]) if closed else (points[min(j + 1, len(points) - 1)] - points[max(j - 1, 0)])
        tangents.append(tangent.normalized())
    # A stable least-aligned reference avoids frame flips at the top and bottom of rings.
    axes = [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))]
    reference = min(axes, key=lambda axis: sum(abs(t.dot(axis)) for t in tangents))
    for j, point in enumerate(points):
        tangent = tangents[j]
        u = tangent.cross(reference)
        if u.length < .01:
            u = tangent.cross(Vector((1, 0, 0)))
        u.normalize()
        v = tangent.cross(u).normalized()
        for i in range(sides):
            a = TAU * i / sides
            verts.append(point + radius * (math.cos(a) * u + math.sin(a) * v))
    steps = len(points) if closed else len(points) - 1
    for j in range(steps):
        for i in range(sides):
            a = j * sides + i
            b = j * sides + (i + 1) % sides
            c = ((j + 1) % len(points)) * sides
            faces.append((a, b, c + (i + 1) % sides, c + i))
    if not closed:
        faces.extend([tuple(reversed(range(sides))), tuple((len(points) - 1) * sides + i for i in range(sides))])
    return mesh(name, verts, faces, mat, parent, outline=outline)


def rounded_stroke(name, points, radius, mat, parent, sides=8):
    ob = tube(name, points, radius, mat, parent, sides)
    for label, p in [("Start", points[0]), ("End", points[-1])]:
        ellipsoid(name + "_" + label, p, (radius,) * 3, mat, parent, 8, 6)
    return ob


HEAD_CENTER = .673
HEAD_A = .306
HEAD_B = .233
HEAD_C = .251
HEAD_P = 2.12


def shell_front(x, z):
    q = abs(x / HEAD_A) ** HEAD_P + abs((z - HEAD_CENTER) / HEAD_C) ** HEAD_P
    return -HEAD_B * max(.001, 1 - q) ** (1 / HEAD_P)


def screen_front(x, z):
    return shell_front(x, z) - .0045


def face_panel(parent, expression="happy", prefix="Face"):
    group = empty(prefix + "/Expression_" + expression.capitalize(), parent)
    group["module"] = "expression"
    group["option"] = expression
    segments, rings = 56, 8
    verts = [(0, screen_front(0, .621), .621)]
    for j in range(1, rings + 1):
        r = j / rings
        for i in range(segments):
            a = TAU * i / segments
            x = .248 * r * spow(math.cos(a), 2 / 2.45)
            z = .621 + .166 * r * spow(math.sin(a), 2 / 2.45)
            verts.append((x, screen_front(x, z), z))
    faces = [(0, 1 + i, 1 + (i + 1) % segments) for i in range(segments)]
    for j in range(rings - 1):
        a = 1 + j * segments
        b = a + segments
        for i in range(segments):
            k = (i + 1) % segments
            faces.append((a + i, b + i, b + k, a + k))
    # Surface normals explicitly face forward; this is a fitted patch, not a floating oval.
    ob = mesh(prefix + "/GlossyScreen", verts, faces, M["screen"], group)
    if ob.data.polygons[0].normal.y > 0:
        bm = bmesh.new(); bm.from_mesh(ob.data)
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces)); bm.to_mesh(ob.data); bm.free()
    edge = [verts[1 + (rings - 1) * segments + i] for i in range(segments)]
    tube(prefix + "/ScreenGasket", edge, .0024, M["ink"], group, 6, closed=True)
    for side, label in SIDES:
        cx = side * .113
        def surface(x, z):
            return (x, screen_front(x, z) - .0035, z)
        if expression == "happy":
            pts = [surface(cx + .065 * math.cos(t), .588 + .056 * math.sin(t)) for t in np.linspace(.12, math.pi - .12, 22)]
            rounded_stroke(prefix + "/HappyArc_" + label, pts, .0125, M["light"], group, sides=8)
            core = [(x, y - .0075, z) for x, y, z in pts]
            rounded_stroke(prefix + "/HappyArcCore_" + label, core, .006, M["eye_core"], group, sides=8)
        elif expression == "sleep":
            pts = [surface(cx + t, .618) for t in np.linspace(-.037, .037, 6)]
            rounded_stroke(prefix + "/SleepBar_" + label, pts, .008, M["light"], group)
        elif expression == "excited":
            pts = [surface(cx + side * .035, .649), surface(cx - side * .025, .617), surface(cx + side * .035, .585)]
            rounded_stroke(prefix + "/ExcitedChevron_" + label, pts, .008, M["light"], group)
        elif expression == "heart":
            vertices = [surface(cx, .623)]
            for t in np.linspace(0, TAU, 41)[:-1]:
                x = cx + .0032 * 16 * math.sin(t) ** 3
                z = .623 + .0033 * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
                vertices.append(surface(x, z))
            ob = mesh(prefix + "/Heart_" + label, vertices, [(0, i + 1, (i + 1) % 40 + 1) for i in range(40)], M["heart"], group)
            if ob.data.polygons[0].normal.y > 0:
                bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.reverse_faces(bm, faces=list(bm.faces)); bm.to_mesh(ob.data); bm.free()
        else:
            raise ValueError(expression)
    if expression == "happy":
        # Keep the wide strokes shallow against the curved screen, including at side angles.
        bpy.context.view_layer.update()
        for ob in group.children:
            if ob.type != "MESH" or "HappyArc" not in ob.name:
                continue
            inverse = ob.matrix_local.inverted()
            for vertex in ob.data.vertices:
                p = ob.matrix_local @ vertex.co
                surface_y = screen_front(p.x, p.z)
                p.y = surface_y - .0015 + .25 * (p.y - surface_y)
                vertex.co = inverse @ p
            ob.data.update()
    return group


def lathe_x(name, side, rows, z, mat, parent, n=40, outline=0):
    verts, faces = [], []
    for x, radius in rows:
        for i in range(n):
            a = TAU * i / n
            verts.append((side * x, radius * math.sin(a), z + radius * math.cos(a)))
    for j in range(len(rows) - 1):
        for i in range(n):
            a, b = j * n + i, j * n + (i + 1) % n
            faces.append((a, b, b + n, a + n))
    faces.extend([tuple(reversed(range(n))), tuple((len(rows) - 1) * n + i for i in range(n))])
    return mesh(name, verts, faces, mat, parent, outline=outline)


def headphones(parent, prefix="Ears/Headphones"):
    group = empty(prefix, parent)
    group["module"] = "headphones"
    for side, label in SIDES:
        base = prefix + "/" + label
        lathe_x(base + "_Cushion", side, [(.280, .085), (.289, .111), (.310, .118), (.323, .113)], .649, M["hood"], group, outline=.0015)
        lathe_x(base + "_WhiteCollar", side, [(.300, .113), (.307, .119), (.319, .119), (.325, .114)], .649, M["white"], group)
        lathe_x(base + "_DarkCup", side, [(.322, .108), (.328, .119), (.348, .122), (.370, .112), (.380, .098)], .649, M["ink"], group, outline=.0015)
        lathe_x(base + "_OuterDisc", side, [(.378, .093), (.383, .088)], .649, M["hood"], group)
        pts = [(side * .386, .080 * math.sin(a), .649 + .080 * math.cos(a)) for a in np.linspace(0, TAU, 48, endpoint=False)]
        tube(base + "_EmissionRing", pts, .0085, M["light"], group, 8, closed=True)
        core = [(x + side * .006, y, z) for x, y, z in pts]
        tube(base + "_EmissionRingCore", core, .0045, M["light_core"], group, 8, closed=True)
        lathe_x(base + "_InnerSpeaker", side, [(.382, .069), (.387, .063)], .649, M["ink"], group)
    return group


def polygon_solid(name, points, depth, mat, parent, bevel=.003, outline=.0015):
    # Input points follow the front face, with a rear face displaced in +Y.
    depths = depth if isinstance(depth, (tuple, list)) else [depth] * len(points)
    verts = list(points) + [(x, y + d, z) for (x, y, z), d in zip(points, depths)]
    n = len(points)
    faces = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    ob = mesh(name, verts, faces, mat, parent, smooth=False)
    if bevel:
        bpy.context.view_layer.objects.active = ob
        mod = ob.modifiers.new("Rounded panel perimeter", "BEVEL")
        mod.width = bevel; mod.segments = 3
        bpy.ops.object.modifier_apply(modifier=mod.name)
        for p in ob.data.polygons:
            p.use_smooth = True
        mod = ob.modifiers.new("Panel normals", "WEIGHTED_NORMAL")
        mod.keep_sharp = True
        bpy.ops.object.modifier_apply(modifier=mod.name)
    if outline:
        add_outline(ob, outline)
    return ob


def wing_fins(parent, prefix="Ears/WingFins"):
    group = empty(prefix, parent)
    group["module"] = "ear_fins"
    # Lofted lenticular sections: 30 mm maximum thickness, swept back in +Y.
    # Catmull-Rom interpolation rounds the silhouette without thick bevel slabs.
    rows = np.array([
        [.731, .265, -.025, .004, .004],
        [.768, .272, -.009, .028, .011],
        [.814, .272, .013, .043, .015],
        [.861, .254, .042, .044, .013],
        [.910, .228, .073, .032, .011],
        [.956, .201, .101, .019, .008],
        [.991, .183, .122, .008, .0045],
        [1.006, .177, .132, .0012, .0012],
    ])
    samples = []
    for j in range(len(rows) - 1):
        p0, p1, p2, p3 = rows[max(j - 1, 0)], rows[j], rows[j + 1], rows[min(j + 2, len(rows) - 1)]
        for t in (0, .5):
            samples.append(.5 * (2 * p1 + (-p0 + p2) * t + (2*p0 - 5*p1 + 4*p2 - p3) * t*t + (-p0 + 3*p1 - 3*p2 + p3) * t*t*t))
    samples.append(rows[-1])
    for side, label in SIDES:
        vertices, faces, colors = [], [], []
        n = 16
        white, lavender = np.array(rgba(PALETTE["white"])), np.array(rgba("D7C6F1"))
        for j, (z, cx, cy, width, depth) in enumerate(samples):
            for i in range(n):
                a = TAU * i / n
                vertices.append((side * (cx + width * math.cos(a)), cy + depth * math.sin(a), z))
                blend = max(0, -math.sin(a)) ** 2 * math.sin(math.pi * j / (len(samples)-1)) ** .45
                colors.append(white * (1 - blend) + lavender * blend)
        for j in range(len(samples)-1):
            for i in range(n):
                a, b = j*n+i, j*n+(i+1)%n
                faces.append((a, b, b+n, a+n))
        faces.extend([tuple(reversed(range(n))), tuple((len(samples)-1)*n+i for i in range(n))])
        ob = mesh(prefix + "/" + label + "_WhiteFin", vertices, faces, M["fin_gradient"], group)
        attribute = ob.data.color_attributes.new(name="FinTint", type="FLOAT_COLOR", domain="POINT")
        for item, color in zip(attribute.data, colors):
            item.color = color
        add_outline(ob, .0015)
        ob["max_section_thickness_m"] = .030
        ob["inset"] = "Continuous vertex-color gradient; no texture or raised inset plate"
    return group


def ball_antennas(parent, prefix="Ears/BallAntennas"):
    group = empty(prefix, parent)
    group["module"] = "antennas"
    for side, label in SIDES:
        pts = [(side * .168, .014, .858), (side * .192, .028, .944), (side * .220, .044, 1.013)]
        tube(prefix + "/" + label + "_Stem", pts, .009, M["ink"], group, 10, outline=.0012)
        ellipsoid(prefix + "/" + label + "_Ball", pts[-1], (.025,) * 3, M["purple"], group, 20, 12, outline=.0015)
        ellipsoid(prefix + "/" + label + "_Signal", (side * .220, .026, 1.019), (.011, .007, .011), M["light"], group, 12, 8)
    return group


def text_geometry(name, content, loc, size, mat, parent, extrude=.0005):
    data = bpy.data.curves.new(name + "_BundledBfont", "FONT")
    data.body = content; data.size = size; data.align_x = "CENTER"
    data.align_y = "CENTER"; data.extrude = extrude; data.bevel_depth = .0002
    if content == "GJH":
        data.offset = size * .027
    data.bevel_resolution = 1; data.resolution_u = 5
    ob = bpy.data.objects.new(name, data); SCENE.collection.objects.link(ob)
    ob.parent = parent; ob.location = loc; ob.rotation_euler.x = math.pi / 2
    data.materials.append(mat)
    bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True)
    bpy.context.view_layer.objects.active = ob; bpy.ops.object.convert(target="MESH")
    ob["font_source"] = "Blender bundled Bfont converted to mesh; no external font"
    return ob


def soft_sweep(name, points, widths, depths, mat, parent, outline=.0013, sides=14):
    """Closed, smoothly shaded cloth volume with tapered end sections."""
    vertices, faces = [], []
    points = [Vector(p) for p in points]
    for j, p in enumerate(points):
        tangent = (points[min(j+1, len(points)-1)] - points[max(0, j-1)]).normalized()
        u = tangent.cross(Vector((0, 0, 1))).normalized()
        v = tangent.cross(u).normalized()
        for i in range(sides):
            a = TAU * i / sides
            vertices.append(p + widths[j]*math.cos(a)*u + depths[j]*math.sin(a)*v)
    for j in range(len(points)-1):
        for i in range(sides):
            a, b = j*sides+i, j*sides+(i+1)%sides
            faces.append((a, b, b+sides, a+sides))
    faces.extend([tuple(reversed(range(sides))), tuple((len(points)-1)*sides+i for i in range(sides))])
    return mesh(name, vertices, faces, mat, parent, outline=outline)


def hood(parent, prefix):
    # Fabric covers the neck; the back roll is gathered, rounded and U-shaped.
    loft(prefix + "/SoftInnerCowl", [(.377,.069,.051,.009), (.391,.094,.064,.009),
         (.416,.093,.061,.008), (.434,.067,.045,.009)], M["hood"], parent, 16, 2, 0, soften=True)
    pts, widths, depths = [], [], []
    for t in np.linspace(0, 1, 25):
        a = -.23 + (math.pi + .46)*t
        fullness = math.sin(math.pi*t) ** .45
        pts.append((.121*math.cos(a), .078*math.sin(a)+.008, .397+.006*math.sin(a)))
        widths.append(.003 + .029*fullness)
        depths.append(.003 + .031*fullness*(1+.065*math.cos(6*a)))
    soft_sweep(prefix + "/BackHoodRoll", pts, widths, depths, M["hood_roll"], parent, .0015)
    for side, label in SIDES:
        controls = np.array([[side*.132,-.026,.405], [side*.106,-.082,.425], [side*.056,-.114,.404], [side*.005,-.119,.380]])
        pts, widths, depths = [], [], []
        for t in np.linspace(0, 1, 16):
            pts.append((1-t)**3*controls[0]+3*(1-t)**2*t*controls[1]+3*(1-t)*t*t*controls[2]+t**3*controls[3])
            widths.append(.002 + .015*math.sin(math.pi*t)**.65)
            depths.append(.002 + .013*math.sin(math.pi*t)**.65)
        soft_sweep(prefix + "/" + label + "_FoldedHood", pts, widths, depths, M["hood"], parent, .001)
        piping = [(p[0],p[1]-.009,p[2]+.008*math.sin(math.pi*j/15)) for j,p in enumerate(pts)]
        rounded_stroke(prefix + "/" + label + "_HoodPiping", piping, .0022, M["purple"], parent, 6)
        tube(prefix + "/" + label + "_Drawstring", [(side*.086,-.110,.387), (side*.089,-.119,.365), (side*.085,-.123,.338), (side*.088,-.122,.314)], .0032, M["ink"], parent, 6)
        bevel_box(prefix + "/" + label + "_Aglet", (side * .088, -.124, .316), (.008, .007, .015), .002, M["lavender"], parent, 0, 2)


def outfit(parent, style="white_hoodie", prefix="Outfit"):
    group = empty(prefix + "/" + style, parent)
    group["module"] = "outfit"; group["option"] = style
    jacket = style == "black_jacket"
    plain = style == "plain_top"
    fabric = M["ink"] if jacket else M["cloth"]
    rows = [(.175, .142, .086, 0), (.182, .166, .101, 0), (.200, .175, .109, 0), (.239, .170, .112, 0), (.305, .155, .104, 0), (.350, .137, .088, 0), (.378, .100, .068, 0), (.387, .070, .054, 0)]
    loft(prefix + "/" + style + "_Torso", rows, fabric, group, n=28, power=3, outline=.0015, soften=True)
    loft(prefix + "/" + style + "_PurpleHem", [(.173, .144, .087, 0), (.180, .164, .102, 0), (.193, .173, .108, 0), (.200, .174, .109, 0)], M["purple"] if not plain else M["ink"], group, 32, 3, .001)
    if not plain:
        hood(group, prefix + "/" + style)
    else:
        pts = [(.077 * math.cos(a), .058 * math.sin(a), .382) for a in np.linspace(0, TAU, 32, endpoint=False)]
        tube(prefix + "/PlainCollar", pts, .007, M["lavender"], group, 8, closed=True)
    for side, label in SIDES:
        arm = empty(prefix + "/" + label + "_SleeveSocket", group, (side * .139, 0, .343))
        arm["pose_role"] = "arm"; arm["anatomical_side"] = label
        arm.rotation_euler.y = -side * .59
        sleeve_rows = [(-.162, .040, .048, 0), (-.156, .052, .056, 0), (-.131, .060, .063, 0), (-.075, .065, .064, 0), (-.025, .059, .059, 0), (.008, .036, .043, 0), (.014, .010, .014, 0)]
        loft(prefix + "/" + label + "_" + style + "Sleeve", sleeve_rows, fabric, arm, 16, 2.5, .0014, soften=True)
        loft(prefix + "/" + label + "_Cuff", [(-.164, .043, .050, 0), (-.157, .051, .056, 0), (-.144, .055, .059, 0)], M["lavender"], arm, 24, 2.4, .001)
        if not plain:
            for k in range(2):
                stripe = bevel_box(prefix + "/" + label + "_SleevePanel_" + str(k + 1), (0, -.0615, -.040 - k * .025), (.075, .003, .014), .003, M["purple"], arm, 0, 2)
    if jacket:
        # White center undershirt and two shaped dark jacket fronts.
        polygon_solid(prefix + "/Jacket_Undershirt", [(-.047, -.111, .193), (.047, -.111, .193), (.045, -.106, .351), (0, -.105, .372), (-.045, -.106, .351)], .005, M["cloth"], group, .002, 0)
        for side, label in SIDES:
            polygon_solid(prefix + "/Jacket_" + label + "_Front", [(side * .045, -.120, .189), (side * .146, -.100, .202), (side * .126, -.098, .335), (side * .063, -.113, .363)], .006, M["ink"], group, .004, .001)
            polygon_solid(prefix + "/Jacket_" + label + "_Pocket", [(side * .080, -.126, .221), (side * .122, -.113, .227), (side * .122, -.113, .255), (side * .080, -.126, .244)], .003, M["hood"], group, .002, .0008)
            tube(prefix + "/Jacket_" + label + "_Zipper", [(side * .045, -.125, .201), (side * .047, -.121, .343)], .0018, M["lavender"], group, 6)
        text_geometry(prefix + "/Jacket_GJH", "GJH", (0, -.122, .302), .027, M["purple"], group)
    elif not plain:
        text_geometry(prefix + "/Hoodie_GJH", "GJH", (0, -.113, .290), .078, M["purple"], group, .0015)
        # Subtle kangaroo pocket seam, kept below the wordmark.
        pts = [(-.091, -.108, .239), (-.068, -.114, .219), (0, -.115, .216), (.068, -.114, .219), (.091, -.108, .239)]
        tube(prefix + "/Hoodie_PocketSeam", pts, .0011, M["seam"], group, 6)
    return group


def body_base(parent, prefix="Body"):
    group = empty(prefix, parent)
    # The shared soft cowl covers this region; no exposed rigid neck connector.
    loft(prefix + "/BlackShorts", [(.134, .099, .073, .005), (.146, .140, .085, .005), (.178, .151, .090, .005), (.194, .143, .086, .005)], M["ink"], group, 28, 3, .0014)
    for side, label in SIDES:
        leg = empty(prefix + "/" + label + "_Leg", group, (side * .091, .005, 0))
        leg["pose_role"] = "leg"; leg["anatomical_side"] = label
        leg.rotation_euler.y = side * .035
        loft(prefix + "/" + label + "_WhiteLeg", [(.018, .053, .063, -.010), (.030, .061, .070, -.006), (.078, .066, .072, 0), (.133, .073, .078, 0), (.160, .070, .074, 0)], M["white"], leg, 20, 3, .0014, soften=True)
        bevel_box(prefix + "/" + label + "_PurpleSquarePatch", (0, -.0735, .066), (.046, .003, .037), .002, M["purple"], leg, 0, 2)
        bevel_box(prefix + "/" + label + "_BlackShoe", (0, -.013, .021), (.119, .150, .042), .019, M["ink"], leg, .0015, 4)
        arm = empty(prefix + "/" + label + "_HandSocket", group, (side * .139, 0, .343))
        arm["pose_role"] = "arm"; arm["anatomical_side"] = label
        arm.rotation_euler.y = -side * .59
        ellipsoid(prefix + "/" + label + "_BlackMitten", (0, -.002, -.169), (.049, .047, .037), M["ink"], arm, 24, 14, power=2.35, outline=.0014)
    return group


def accessory(parent, style, prefix="Accessory"):
    group = empty(prefix + "/" + style, parent)
    group["module"] = "accessory"; group["option"] = style
    if style == "backpack":
        bevel_box(prefix + "/Backpack_Main", (0, .137, .282), (.207, .112, .221), .032, M["purple"], group, .0015, 4)
        bevel_box(prefix + "/Backpack_FrontPocket", (0, .198, .232), (.165, .030, .086), .016, M["lavender"], group, .0012, 3)
        tube(prefix + "/Backpack_Handle", [(-.035, .142, .386), (-.030, .143, .420), (.030, .143, .420), (.035, .142, .386)], .009, M["ink"], group, 8)
        for side, label in SIDES:
            pts = [(side * .077, .153, .382), (side * .106, .033, .374), (side * .107, -.079, .339), (side * .127, -.101, .253), (side * .130, -.019, .208), (side * .080, .138, .196)]
            tube(prefix + "/Backpack_" + label + "_Strap", pts, .012, M["ink"], group, 8)
            bevel_box(prefix + "/Backpack_" + label + "_Clasp", (side * .054, .218, .258), (.020, .010, .030), .005, M["hood"], group, 0)
    elif style == "belt_bag":
        pts = [(.166 * math.cos(a), .111 * math.sin(a), .227) for a in np.linspace(0, TAU, 40, endpoint=False)]
        tube(prefix + "/BeltBag_Belt", pts, .009, M["ink"], group, 8, closed=True)
        bag = bevel_box(prefix + "/BeltBag_Pouch", (.055, -.130, .235), (.139, .049, .088), .021, M["purple"], group, .0015, 4)
        bag.rotation_euler.y = -.18
        tube(prefix + "/BeltBag_Zip", [(-.002, -.157, .250), (.106, -.157, .268)], .0024, M["ink"], group, 6)
        bevel_box(prefix + "/BeltBag_Pull", (.020, -.161, .242), (.010, .008, .020), .003, M["lavender"], group, 0)
    elif style == "id_badge":
        tube(prefix + "/ID_Lanyard", [(-.054, -.094, .375), (-.041, -.123, .300), (0, -.131, .266), (.041, -.123, .300), (.054, -.094, .375)], .0038, M["purple"], group, 6)
        bevel_box(prefix + "/ID_Frame", (0, -.139, .239), (.061, .011, .078), .006, M["ink"], group, .001, 3)
        bevel_box(prefix + "/ID_Card", (0, -.146, .239), (.049, .003, .063), .003, M["white"], group, 0, 2)
        ellipsoid(prefix + "/ID_AvatarHead", (0, -.149, .251), (.008, .002, .008), M["purple"], group, 12, 8)
        ellipsoid(prefix + "/ID_AvatarBody", (0, -.149, .236), (.013, .002, .009), M["purple"], group, 12, 8)
        bevel_box(prefix + "/ID_Line", (0, -.149, .218), (.029, .002, .003), .001, M["lavender"], group, 0, 1)
    else:
        raise ValueError(style)
    return group


def descendants(root):
    return [root] + list(root.children_recursive)


def world_bounds(objects):
    bpy.context.view_layer.update()
    coords = [ob.matrix_world @ v.co for ob in objects if ob.type == "MESH" for v in ob.data.vertices]
    return ([min(p[i] for p in coords) for i in range(3)], [max(p[i] for p in coords) for i in range(3)])


def normalize_character(root):
    low, high = world_bounds(descendants(root))
    factor = 1 / (high[2] - low[2])
    # Bake uniform normalization into mesh vertices and node translations, retaining an identity root.
    for ob in descendants(root):
        if ob == root:
            continue
        ob.location *= factor
        if ob.type == "MESH":
            for v in ob.data.vertices:
                v.co *= factor
    for ob in root.children:
        ob.location.z -= low[2] * factor
    bpy.context.view_layer.update()
    root["height_m"] = 1.0
    root["normalization_scale"] = factor
    root["assembly_floor_offset"] = -low[2] * factor
    root["front_blender"] = "-Y"
    root["front_gltf"] = "+Z"
    root["up_gltf"] = "+Y"
    return factor


def rotate_about(ob, pivot, angles):
    pivot = Vector(pivot)
    ob.matrix_local = (Matrix.Translation(pivot) @ Euler(angles, "XYZ").to_matrix().to_4x4()
                       @ Matrix.Translation(-pivot) @ ob.matrix_local)


def bend_wave_sleeve(socket):
    """Bake a curved elbow into the mesh, including its cuff, stripes and outline."""
    # Uniform axial samples avoid stretching the neutral sleeve's sparse rings
    # into a visibly angular elbow, while costing less than another subdivision.
    sleeve = next(o for o in socket.children if o.name.endswith("Sleeve"))
    name, fabric = sleeve.name, sleeve.data.materials[0]
    for ob in list(sleeve.children_recursive) + [sleeve]:
        bpy.data.objects.remove(ob, do_unlink=True)
    controls = np.array([[-.162,.040,.048,0], [-.144,.055,.059,0], [-.100,.061,.063,0],
                         [-.055,.063,.062,0], [-.014,.050,.052,0], [.010,.030,.035,0], [.016,.002,.002,0]])
    rows = []
    for j in range(len(controls)-1):
        p0,p1,p2,p3 = controls[max(0,j-1)], controls[j], controls[j+1], controls[min(len(controls)-1,j+2)]
        for t in (0,.25,.5,.75):
            rows.append(.5*(2*p1+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t))
    rows.append(controls[-1])
    loft(name, rows, fabric, socket, 18, 2.5, .0014)
    # Give the cuff a real overlap, so its lip cannot intersect the sleeve hull.
    cuff = next(o for o in socket.children if "_Cuff" in o.name)
    for ob in [cuff] + list(cuff.children_recursive):
        for vertex in ob.data.vertices:
            vertex.co.x *= 1.075
            vertex.co.y *= 1.075
    # Printed stripes follow the new sleeve surface instead of clipping through it.
    rows = np.array(rows)
    for stripe in [o for o in socket.children if "_SleevePanel_" in o.name]:
        stripe_name = stripe.name
        center_z = stripe.location.z
        bpy.data.objects.remove(stripe, do_unlink=True)
        verts, faces = [], []
        for j in range(5):
            z = center_z - .007 + .014*j/4
            width = np.interp(z, rows[:,0], rows[:,1])
            depth = np.interp(z, rows[:,0], rows[:,2])
            for i in range(11):
                x = (-1+2*i/10)*(.035 if j in (0,4) else .0375)
                y = -depth*max(.001,1-abs(x/width)**2.5)**(1/2.5)-.0020
                verts.append((x,y,z))
        for j in range(4):
            for i in range(10):
                a = j*11+i
                faces.append((a,a+1,a+12,a+11))
        stripe = mesh(stripe_name, verts, faces, M["purple"], socket)
        if stripe.data.polygons[0].normal.y > 0:
            bm = bmesh.new(); bm.from_mesh(stripe.data)
            bmesh.ops.reverse_faces(bm, faces=list(bm.faces)); bm.to_mesh(stripe.data); bm.free()
    # Two cubic spans share a tangent at the elbow; the lower arm turns upward.
    spans = [np.array([[0,0,0], [.055,0,.006], [.120,-.004,.010], [.155,-.012,.053]]),
             np.array([[.155,-.012,.053], [.190,-.020,.096], [.231,-.052,.180], [.255,-.058,.220]])]
    def frame(t):
        j = 0 if t < .48 else 1
        u = t/.48 if j == 0 else (t-.48)/.52
        p = spans[j]
        center = (1-u)**3*p[0]+3*(1-u)**2*u*p[1]+3*(1-u)*u*u*p[2]+u**3*p[3]
        tangent = Vector(3*(1-u)**2*(p[1]-p[0])+6*(1-u)*u*(p[2]-p[1])+3*u*u*(p[3]-p[2])).normalized()
        across = Vector((0,1,0)).cross(-tangent).normalized()
        depth = (-tangent).cross(across).normalized()
        return Vector(center), across, depth
    bpy.context.view_layer.update()
    inverse_socket = socket.matrix_world.inverted()
    for ob in socket.children_recursive:
        if ob.type != "MESH":
            continue
        to_socket = inverse_socket @ ob.matrix_world
        inverse = to_socket.inverted()
        for vertex in ob.data.vertices:
            p = to_socket @ vertex.co
            c, across, depth = frame(-p.z/.160)
            vertex.co = inverse @ (c + p.x*across + p.y*depth)
        ob.data.update()
    socket.rotation_euler = (0,0,0)
    socket.location = (.155, 0, .343)
    upper = Vector(spans[0][-1]-spans[0][0])
    lower = Vector(spans[1][-1]-spans[1][0])
    socket["elbow_centerline_bend_degrees"] = math.degrees(upper.angle(lower))


def open_wave_mitten(socket):
    for ob in list(socket.children_recursive):
        bpy.data.objects.remove(ob, do_unlink=True)
    socket.rotation_euler = (0,0,0)
    socket.location = (.155, 0, .343)
    palm = ellipsoid("Body/L_BlackMitten", (.279,-.067,.263), (.047,.036,.065), M["ink"], socket, 24, 14, power=2.25, outline=.0016)
    palm.rotation_euler.y = .46
    thumb = ellipsoid("Body/L_OpenMittenThumb", (.240,-.076,.247), (.025,.031,.034), M["ink"], socket, 16, 10, outline=.0012)
    thumb.rotation_euler.y = -.45
    socket["gesture"] = "Open mitten palm, lifted fingers and separated thumb; static mesh"


def pose_character(root, head, body, clothes, accessories, pose):
    """Author static transforms; no armature, skin, animation, or runtime posing needed."""
    if pose not in ("stand", "wave"):
        raise ValueError(pose)
    root["pose"] = pose
    legs = [o for o in body.children if o.get("pose_role") == "leg"]
    if pose == "wave":
        # The wave has its own baked sleeve curvature; standing meshes stay neutral.
        for ob in [o for o in descendants(body) + descendants(clothes) if o.get("pose_role") == "arm"]:
            if ob["anatomical_side"] == "L":
                if "SleeveSocket" in ob.name:
                    bend_wave_sleeve(ob)
                else:
                    open_wave_mitten(ob)
            else:
                ob.rotation_euler = (.18, .72, -.12)
        # Keep the short legs independent of the torso lean, then seat each sole.
        for leg in legs:
            leg.parent = root
            if leg["anatomical_side"] == "R":
                rotate_about(leg, (-.091, .005, .145), (-.10, .25, -.18))
                leg.location.y -= .110
                leg.location.x -= .024
            else:
                leg.rotation_euler.y = -.045
                leg.location.y += .035
        rotate_about(head, (0, 0, .405), (0, math.radians(4), math.radians(3)))
        tilt = empty("Pose/BodyTilt", root, (0, 0, .165))
        tilt["lean_degrees"] = 7.0
        for ob in [head, body, clothes] + accessories:
            ob.parent = tilt
            ob.location -= tilt.location
        tilt.rotation_euler.y = math.radians(7)
        root["raised_hand"] = "anatomical left (+X in the frontal view)"
        root["stepping_leg"] = "anatomical right, forward by 0.110 m before normalization; left back 0.035 m"
        root["head_turn_degrees"] = 3.0
        root["head_tilt_toward_hand_degrees"] = 11.0
    # A posed foot must contact the floor even when rotated or shifted forward.
    for leg in legs:
        low, _ = world_bounds(descendants(leg))
        leg.location.z -= low[2]
        bpy.context.view_layer.update()
        # Extend the physical sole within the existing outline down to its contact
        # plane. Hiding outlines must not leave a 2-3 mm floating shoe surface.
        for shoe in [o for o in leg.children if "_BlackShoe" in o.name]:
            floor, _ = world_bounds([shoe])
            gap = floor[2]
            inverse = shoe.matrix_world.inverted()
            for vertex in shoe.data.vertices:
                p = shoe.matrix_world @ vertex.co
                weight = max(0, 1-(p.z-gap)/.012)
                p.z -= gap*weight
                vertex.co = inverse @ p
            shoe.data.update()


def build_character(name="GJHChibiVisitor", expression="happy", ears="wing_fins", outfit_style="white_hoodie", accessories=(), pose="wave"):
    root = empty(name)
    root["expression"] = expression; root["ears"] = ears; root["outfit"] = outfit_style
    root["accessories"] = ",".join(accessories) or "none"
    head = empty("Head", root)
    ellipsoid("Head/WhiteHelmet", (0, 0, HEAD_CENTER), (HEAD_A, HEAD_B, HEAD_C), M["white"], head, 48, 24, HEAD_P, .002)
    rear_vertices, rear_faces = [], []
    for j in range(9):
        for i in range(33):
            a = math.pi * i / 32
            z = .425 + (.595 - .065 * math.cos(a) ** 2 - .425) * j / 8
            radial = max(0, 1 - abs((z - HEAD_CENTER) / HEAD_C) ** HEAD_P) ** (1 / HEAD_P)
            x = HEAD_A * radial * spow(math.cos(a), 2 / HEAD_P)
            y = HEAD_B * radial * spow(math.sin(a), 2 / HEAD_P)
            normal = Vector((spow(x / HEAD_A, HEAD_P - 1) / HEAD_A,
                             spow(y / HEAD_B, HEAD_P - 1) / HEAD_B,
                             spow((z - HEAD_CENTER) / HEAD_C, HEAD_P - 1) / HEAD_C)).normalized()
            rear_vertices.append(Vector((x, y, z)) + normal * .0032)
    for j in range(8):
        for i in range(32):
            k = j * 33 + i
            rear_faces.append((k, k + 1, k + 34, k + 33))
    panel = mesh("Head/RearLavenderPanel", rear_vertices, rear_faces, M["lavender"], head)
    if panel.data.polygons[16].normal.y < 0:
        bm = bmesh.new(); bm.from_mesh(panel.data); bmesh.ops.reverse_faces(bm, faces=list(bm.faces)); bm.to_mesh(panel.data); bm.free()
    face_panel(head, expression)
    headphones(head)
    if ears == "wing_fins":
        wing_fins(head)
    elif ears == "ball_antennas":
        ball_antennas(head)
    elif ears != "headphones":
        raise ValueError(ears)
    # Thin seams on the white forehead, derived from the actual helmet surface.
    for side, label in SIDES:
        pts = []
        for z in np.linspace(.795, .911, 18):
            x = side * (.106 - .027 * ((z - .795) / .116))
            q = abs(x / HEAD_A) ** HEAD_P + abs((z - HEAD_CENTER) / HEAD_C) ** HEAD_P
            if q < .997:
                pts.append((x, shell_front(x, z) - .001, z))
        tube("Head/" + label + "_PanelSeam", pts, .00085, M["seam"], head, 5)
    body = body_base(root)
    clothes = outfit(root, outfit_style)
    extra = [accessory(root, style) for style in accessories]
    pose_character(root, head, body, clothes, extra, pose)
    normalize_character(root)
    low, high = world_bounds(descendants(root))
    root["height_m"] = high[2] - low[2]
    hands = [o for o in descendants(root) if o.type == "MESH" and "L_BlackMitten" in o.name]
    root["raised_hand_exceeds_one_metre"] = world_bounds(hands)[1][2] > 1 if hands else False
    return root


def build_kit(default_root):
    row = empty("KIT_MountRow", default_root)
    row["description"] = "Visible swappable modules on one separate display row; character mount stays at origin"
    specs = [("Expression_" + s, "face", s) for s in ("happy", "sleep", "excited", "heart")]
    specs += [("HeadphoneCups", "ears", "headphones"), ("BallAntennas", "ears", "ball_antennas"), ("WingFins", "ears", "wing_fins")]
    specs += [("Outfit_" + s, "outfit", s) for s in ("white_hoodie", "black_jacket", "plain_top")]
    specs += [("Accessory_" + s, "accessory", s) for s in ("backpack", "belt_bag", "id_badge")]
    for i, (label, kind, style) in enumerate(specs):
        mount = empty(f"Mount_{i + 1:02d}_" + label, row, ((i - 6) * .76, 2.20, 0))
        module = empty("Module_" + label, mount)
        if kind == "face":
            face_panel(module, style, label)
        elif kind == "ears":
            {"headphones": headphones, "ball_antennas": ball_antennas, "wing_fins": wing_fins}[style](module, label)
        elif kind == "outfit":
            outfit(module, style, label)
        else:
            accessory(module, style, label)
            if style == "backpack":
                module.rotation_euler.z = math.pi
        module.scale = (default_root["normalization_scale"],) * 3
        module["assembly_floor_offset"] = default_root["assembly_floor_offset"]
        module["display_only_translation"] = True
        low, high = world_bounds(descendants(module))
        module.location.z += .090 - low[2]
        bevel_box("MountBase_" + label, (0, 0, .025), (.68, .39, .046), .015, M["lavender"], mount, .001, 3)
        text_geometry("MountLabel_" + label, f"{i + 1:02d}  " + label.replace("_", " ").upper(), (0, -.202, .023), .023, M["hood"], mount, .0002)
    return row


def export_glb(path, objects, canonical_root=True):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objects:
        ob.hide_set(False)
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    # Source roots are distinct, but every required GLB has the canonical root.
    root = objects[0]
    previous_name = root.name
    other = bpy.data.objects.get("GJHChibiVisitor") if canonical_root else None
    if other == root:
        other = None
    if other:
        other.name = "ExportInactiveRoot"
    if canonical_root:
        root.name = "GJHChibiVisitor"
    try:
        bpy.ops.export_scene.gltf(
            filepath=str(path), export_format="GLB", use_selection=True,
            export_yup=True, export_apply=True, export_animations=False,
            export_cameras=False, export_lights=False, export_extras=True,
            export_texcoords=False, export_normals=True, export_materials="EXPORT",
            export_image_format="NONE", export_attributes=False,
            export_vertex_color="NAME", export_vertex_color_name="FinTint",
            export_all_vertex_colors=False,
        )
    finally:
        root.name = previous_name
        if other:
            other.name = "GJHChibiVisitor"
    return inspect_glb(path)


def inspect_glb(path):
    raw = path.read_bytes()
    length = struct.unpack_from("<I", raw, 12)[0]
    doc = json.loads(raw[20:20 + length])
    # Count each scene instance, including shared mesh data and outline hulls.
    def count_node(index):
        node = doc["nodes"][index]
        own = sum(doc["accessors"][p["indices"]]["count"] // 3 for p in doc["meshes"][node["mesh"]]["primitives"]) if "mesh" in node else 0
        return own + sum(count_node(child) for child in node.get("children", []))
    triangles = sum(count_node(i) for i in doc["scenes"][doc.get("scene", 0)]["nodes"])
    info = {"bytes": len(raw), "triangles": triangles, "meshes": len(doc.get("meshes", [])), "nodes": len(doc.get("nodes", [])),
            "materials": len(doc.get("materials", [])), "images": len(doc.get("images", [])), "animations": len(doc.get("animations", [])),
            "outline_nodes": sum(n.get("name", "").endswith("__Outline") for n in doc["nodes"]),
            "extensions_used": doc.get("extensionsUsed", [])}
    print("EXPORT_METRICS", path.name, json.dumps(info), flush=True)
    return info


def aim(ob, point):
    ob.rotation_euler = (Vector(point) - ob.location).to_track_quat("-Z", "Y").to_euler()


def setup_studio():
    studio = empty("STUDIO_SourceOnly")
    world = bpy.data.worlds.new("Soft lavender studio")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = rgba("D5CAE8")
    world.node_tree.nodes["Background"].inputs[1].default_value = .35
    SCENE.world = world
    floor_mat = material("Studio lavender", "DCD2ED", 1)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.003))
    floor = bpy.context.object; floor.name = "StudioFloor"; floor.parent = studio
    floor.data.materials.append(floor_mat)
    floor.hide_render = True
    for name, loc, power, size, color in [
        ("Key", (-2.4, -3.5, 4), 170, 3.5, "FFF8FF"),
        ("Fill", (3, -1.8, 2), 90, 3, "E1D8FF"),
        ("Rim", (1.2, 2.5, 3), 210, 2.5, "F6F0FF"),
    ]:
        bpy.ops.object.light_add(type="AREA", location=loc)
        ob = bpy.context.object; ob.name = "Studio_" + name; ob.parent = studio
        ob.data.energy = power; ob.data.shape = "DISK"; ob.data.size = size
        ob.data.use_shadow = False
        ob.data.color = rgba(color)[:3]; aim(ob, (0, 0, .5))
    bpy.ops.object.camera_add(location=(1.6, -3, 1.1))
    camera = bpy.context.object; camera.name = "PreviewCamera"; camera.parent = studio
    camera.data.type = "ORTHO"; camera.data.ortho_scale = 1.24
    SCENE.camera = camera
    SCENE.render.engine = "BLENDER_EEVEE"
    if hasattr(SCENE, "eevee") and hasattr(SCENE.eevee, "taa_render_samples"):
        SCENE.eevee.taa_render_samples = 64
    SCENE.render.resolution_x = 1024; SCENE.render.resolution_y = 1024
    SCENE.render.resolution_percentage = 100
    SCENE.render.image_settings.file_format = "PNG"
    SCENE.render.image_settings.color_mode = "RGBA"
    SCENE.render.film_transparent = True
    SCENE.view_layers[0].use_pass_emit = True
    SCENE.view_settings.view_transform = "Standard"
    SCENE.view_settings.look = "None"
    SCENE.view_settings.exposure = 0
    # Eevee supports backface culling, so the preview uses the same inverted hulls as glTF.
    return studio


def apply_compositing():
    # Blender 5 uses a compositor node group; support both APIs without downloading dependencies.
    if hasattr(SCENE, "compositing_node_group"):
        tree = bpy.data.node_groups.new("Gentle emissive glow", "CompositorNodeTree")
        SCENE.compositing_node_group = tree
        tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        out = tree.nodes.new("NodeGroupOutput")
    else:
        SCENE.use_nodes = True
        tree = SCENE.node_tree
        tree.nodes.clear()
        out = tree.nodes.new("CompositorNodeComposite")
    layer = tree.nodes.new("CompositorNodeRLayers")
    glare = tree.nodes.new("CompositorNodeGlare")
    if "Type" in glare.inputs:
        glare.inputs["Type"].default_value = "Fog Glow"
        glare.inputs["Quality"].default_value = "High"
        glare.inputs["Strength"].default_value = 1.4
        glare.inputs["Size"].default_value = .50
    else:
        glare.glare_type = "FOG_GLOW"; glare.quality = "HIGH"
    if "Threshold" in glare.inputs:
        glare.inputs["Threshold"].default_value = .6
    else:
        glare.threshold = .6
    # A generated studio-only gradient avoids a horizon in orthographic views.
    # It never belongs to the model and is created after both texture-free exports.
    yy, xx = np.mgrid[0:1024, 0:1024].astype(np.float32)
    xx = xx / 1023; yy = yy / 1023
    t = np.clip(.24 + .56 * yy + .23 * np.exp(-((xx - .38) ** 2 + (yy - .65) ** 2) / .20), 0, 1)
    lower = np.array(rgba("D4C4EF")[:3]); upper = np.array(rgba("F6F1FF")[:3])
    pixels = np.ones((1024, 1024, 4), dtype=np.float32)
    pixels[:, :, :3] = lower[None, None, :] * (1 - t[:, :, None]) + upper[None, None, :] * t[:, :, None]
    shadow = .20 * np.exp(-((xx - .5) / .20) ** 2 - ((yy - .091) / .014) ** 2)
    pixels[:, :, :3] *= 1 - shadow[:, :, None]
    backdrop = bpy.data.images.new("Studio procedural lavender gradient", width=1024, height=1024, alpha=True, float_buffer=True)
    backdrop.pixels.foreach_set(pixels.ravel()); backdrop.pack()
    image_node = tree.nodes.new("CompositorNodeImage"); image_node.image = backdrop
    over = tree.nodes.new("CompositorNodeAlphaOver")
    if "Factor" in over.inputs:
        over.inputs["Factor"].default_value = 1
        tree.links.new(image_node.outputs["Image"], over.inputs["Background"])
        tree.links.new(layer.outputs["Image"], over.inputs["Foreground"])
    else:
        over.inputs[0].default_value = 1
        tree.links.new(image_node.outputs["Image"], over.inputs[1])
        tree.links.new(layer.outputs["Image"], over.inputs[2])
    # Bloom the emission pass only: white porcelain and fabric should not glow.
    emission = layer.outputs.get("Emission") or layer.outputs.get("Emit")
    tree.links.new(emission, glare.inputs["Image"])
    glow = glare.outputs.get("Glare")
    if glow is None:
        glare.mix = 1
        glow = glare.outputs["Image"]
    if hasattr(SCENE, "compositing_node_group"):
        add = tree.nodes.new("ShaderNodeMix"); add.data_type = "RGBA"
        add.blend_type = "ADD"; add.clamp_result = False
        add.inputs[0].default_value = 1
        first = next(i for i in add.inputs if i.identifier == "A_Color")
        second = next(i for i in add.inputs if i.identifier == "B_Color")
        result = next(o for o in add.outputs if o.identifier == "Result_Color")
    else:
        add = tree.nodes.new("CompositorNodeMixRGB")
        add.blend_type = "ADD"; add.inputs[0].default_value = 1
        first, second, result = add.inputs[1], add.inputs[2], add.outputs["Image"]
    tree.links.new(over.outputs["Image"], first)
    tree.links.new(glow, second)
    tree.links.new(result, out.inputs["Image"])


def render_views(row, quick=False):
    for ob in descendants(row):
        ob.hide_render = True
    views = [("front", (0, -4, .52)), ("side", (4, 0, .52)), ("back", (0, 4, .52)), ("3q", (1.65, -3.3, 1.18))]
    if quick:
        views = [views[0], views[3]]
    for view, loc in views:
        SCENE.camera.location = loc; aim(SCENE.camera, (0, 0, .505))
        SCENE.camera.data.ortho_scale = 1.22 if view != "3q" else 1.25
        SCENE.render.filepath = str(ROOT / "previews" / (view + ".png"))
        print("RENDER_VIEW", view, flush=True)
        bpy.ops.render.render(write_still=True)


def compare_with_sheet():
    # Image layout only: source reference and actual Blender output remain unmodified.
    front = bpy.data.images.load(str(ROOT / "previews/front.png"), check_existing=False)
    sheet = bpy.data.images.load(str(ROOT / "design-sheet.png"), check_existing=False)
    w, h = 2560, 1024
    canvas = np.ones((h, w, 4), dtype=np.float32)
    canvas[:, :, :3] = (.92, .89, .97)
    for image, x, target_w in [(front, 0, 1024), (sheet, 1024, 1536)]:
        iw, ih = image.size
        pixels = np.array(image.pixels[:], dtype=np.float32).reshape(ih, iw, 4)
        tw, th = target_w, round(ih * target_w / iw)
        ix = np.minimum((np.arange(tw) * iw / tw).astype(int), iw - 1)
        iy = np.minimum((np.arange(th) * ih / th).astype(int), ih - 1)
        y = (h - th) // 2
        canvas[y:y + th, x:x + tw] = pixels[iy[:, None], ix[None, :]]
    result = bpy.data.images.new("Front render beside supplied design sheet", width=w, height=h, alpha=True)
    result.pixels.foreach_set(canvas.ravel())
    result.filepath_raw = str(ROOT / "previews/compare-with-sheet.png")
    result.file_format = "PNG"; result.save()
    for im in (front, sheet, result):
        bpy.data.images.remove(im)


def compare_revisions():
    # Top: archived R2 front/side. Bottom: current R3 front/side.
    paths = [ROOT / f"{folder}/{view}.png" for folder in ("reports/r2/previews", "previews") for view in ("front", "side")]
    canvas = np.ones((2048, 2048, 4), dtype=np.float32)
    for i, path in enumerate(paths):
        im = bpy.data.images.load(str(path), check_existing=False)
        assert tuple(im.size) == (1024, 1024), (path, tuple(im.size))
        x, y = (i % 2) * 1024, (1 - i // 2) * 1024
        canvas[y:y+1024, x:x+1024] = np.array(im.pixels[:], dtype=np.float32).reshape(1024, 1024, 4)
        bpy.data.images.remove(im)
    result = bpy.data.images.new("R2 front and side above - R3 front and side below", width=2048, height=2048, alpha=True)
    result.pixels.foreach_set(canvas.ravel())
    result.filepath_raw = str(ROOT / "previews/compare-r2-r3.png")
    result.file_format = "PNG"; result.save()
    bpy.data.images.remove(result)


def run_optional_comparison(name, compare, input_paths):
    missing = [path for path in input_paths if not path.is_file()]
    if missing:
        missing_names = ", ".join(path.relative_to(ROOT).as_posix() for path in missing)
        print(f"OPTIONAL_COMPARISON_SKIPPED {name}: missing input image(s): {missing_names}", flush=True)
        return
    compare()


def gallery_preview():
    im = bpy.data.images.load(str(ROOT / "previews/front.png"), check_existing=False)
    im.scale(256, 256)
    im.filepath_raw = str(ROOT / "previews/gallery-size.png")
    im.file_format = "PNG"; im.save()
    bpy.data.images.remove(im)


def main():
    global SCENE
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Render front and three-quarter only for iteration")
    parser.add_argument("--no-render", action="store_true")
    parser.add_argument("--expression", choices=["happy", "sleep", "excited", "heart"], default="happy")
    parser.add_argument("--ears", choices=["wing_fins", "ball_antennas", "headphones"], default="wing_fins")
    parser.add_argument("--outfit", choices=["white_hoodie", "black_jacket", "plain_top"], default="white_hoodie")
    parser.add_argument("--accessories", nargs="*", choices=["backpack", "belt_bag", "id_badge"], default=[])
    parser.add_argument("--pose", choices=["wave", "stand"], default="wave", help="Pose for the optional custom export only")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    SCENE = bpy.context.scene
    SCENE.unit_settings.system = "METRIC"; SCENE.unit_settings.scale_length = 1
    SCENE.render.fps = 24
    for name in ("exports", "previews", "reports"):
        (ROOT / name).mkdir(exist_ok=True)
    materials()
    root = build_character()
    metrics = {"blender_version": bpy.app.version_string, "palette": PALETTE}
    metrics["default"] = export_glb(ROOT / "exports/gjh-chibi-visitor-blender.glb", descendants(root))
    metrics["default"]["blender_bounds"] = world_bounds(descendants(root))
    assert metrics["default"]["triangles"] < 40000, metrics["default"]
    assert metrics["default"]["bytes"] < 2 * 1024 ** 2, metrics["default"]
    stand = build_character("GJHChibiVisitor_Stand", pose="stand")
    metrics["stand"] = export_glb(ROOT / "exports/gjh-chibi-visitor-blender-stand.glb", descendants(stand))
    metrics["stand"]["blender_bounds"] = world_bounds(descendants(stand))
    assert metrics["stand"]["triangles"] < 40000 and metrics["stand"]["bytes"] < 2 * 1024 ** 2
    row = build_kit(stand)
    metrics["kit"] = export_glb(ROOT / "exports/gjh-chibi-visitor-blender-kit.glb", descendants(stand))
    assert metrics["kit"]["bytes"] < 5 * 1024 ** 2, metrics["kit"]
    if (args.expression, args.ears, args.outfit, args.accessories, args.pose) != ("happy", "wing_fins", "white_hoodie", [], "wave"):
        custom = build_character("GJHChibiVisitor_Custom", args.expression, args.ears, args.outfit, args.accessories, args.pose)
        metrics["custom"] = export_glb(ROOT / "exports/gjh-chibi-visitor-custom.glb", descendants(custom), canonical_root=False)
        for ob in descendants(custom):
            ob.hide_render = True; ob.hide_set(True)
    setup_studio()
    apply_compositing()
    for ob in descendants(stand):
        ob.hide_render = True; ob.hide_set(True)
    SCENE.camera.location = (1.65, -3.3, 1.18); aim(SCENE.camera, (0, 0, .505))
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True); bpy.context.view_layer.objects.active = root
    SCENE["asset_contract"] = "Native metres; glTF +Y up, +Z front, feet Y=0; no textures"
    SCENE["source_notes"] = "Wave visible; GJHChibiVisitor_Stand and KIT_MountRow hidden for studio only. Kit GLB stands with 13 visible mounts."
    SCENE["generator"] = "generate.py"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "gjh-chibi-visitor.blend"), compress=True)
    if not args.no_render:
        render_views(row, args.quick)
        run_optional_comparison(
            "compare_with_sheet",
            compare_with_sheet,
            [ROOT / "previews/front.png", ROOT / "design-sheet.png"],
        )
        if not args.quick:
            run_optional_comparison(
                "compare_revisions",
                compare_revisions,
                [ROOT / f"{folder}/{view}.png" for folder in ("reports/r2/previews", "previews") for view in ("front", "side")],
            )
        gallery_preview()
        if not args.quick:
            for ob in descendants(root):
                ob.hide_render = True
            for ob in descendants(stand):
                ob.hide_render = False
            for ob in descendants(row):
                ob.hide_render = True
            SCENE.camera.location = (0, -4, .52); aim(SCENE.camera, (0, 0, .505))
            SCENE.camera.data.ortho_scale = 1.22
            SCENE.render.filepath = str(ROOT / "previews/stand-front.png")
            bpy.ops.render.render(write_still=True)
    (ROOT / "reports/generation.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print("GENERATION_COMPLETE", json.dumps(metrics), flush=True)


if __name__ == "__main__":
    main()
