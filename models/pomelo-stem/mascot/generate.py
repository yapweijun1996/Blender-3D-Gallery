"""Deterministic Pomelo STEM v8.2: original geometry, headless Blender only.

Generic mesh/export helpers adapted from the read-only BlenderChibi example.
All character geometry is authored here for the supplied Pomelo design board.
"""
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
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
TAU = math.tau
SCENE = None
M = {}
EXPRESSIONS = ("happy", "laugh", "surprised", "wink", "thinking", "sad")
PALETTE = {"pomelo": "CBE85A", "cream": "FFFBE6", "leaf": "2F8F3D", "blush": "FFB6B6", "eye": "293226"}

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
    data = ob.data.copy()
    data.name = ob.name + "_InvertedHullMesh"
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




def export_glb(path, objects):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objects:
        ob.hide_set(False)
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(
        filepath=str(path), export_format="GLB", use_selection=True,
        export_yup=True, export_apply=True, export_animations=False,
        export_cameras=False, export_lights=False, export_extras=True,
        export_texcoords=False, export_normals=True, export_materials="EXPORT",
        export_image_format="NONE", export_attributes=False,
    )
    return inspect_glb(path)


def inspect_glb(path):
    raw = path.read_bytes()
    length = struct.unpack_from("<I", raw, 12)[0]
    doc = json.loads(raw[20:20 + length])
    triangles = sum(doc["accessors"][p["indices"]]["count"] // 3 for m in doc.get("meshes", []) for p in m["primitives"])
    info = {"bytes": len(raw), "triangles": triangles, "meshes": len(doc.get("meshes", [])), "nodes": len(doc.get("nodes", [])),
            "materials": len(doc.get("materials", [])), "images": len(doc.get("images", [])), "animations": len(doc.get("animations", [])),
            "outline_nodes": sum(n.get("name", "").endswith("__Outline") for n in doc["nodes"]),
            "extensions_used": doc.get("extensionsUsed", [])}
    print("EXPORT_METRICS", path.name, json.dumps(info), flush=True)
    return info


def aim(ob, point):
    ob.rotation_euler = (Vector(point) - ob.location).to_track_quat("-Z", "Y").to_euler()



# The head is a pear-shaped superellipsoid with a continuous recessed face opening.
HEAD_A, HEAD_B, HEAD_C, HEAD_Z, HEAD_P = .377, .265, .325, .600, 2.30
FACE_Z = .535


def materials():
    for key, color in PALETTE.items():
        M[key] = material(key.title() + ' | #' + color, color,
                          .33 if key in ('pomelo', 'eye') else .45)
    M['eye'].node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value = .22
    M['eye'].node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value = .25
    M['white'] = material('Eye highlights | #FFFFFF', 'FFFFFF', .22)
    M['mouth'] = material('Mouth interior | warm burgundy', '713224', .48)
    M['tongue'] = material('Tongue | warm coral', 'F68077', .43)
    M['vein'] = material('Leaf midrib | soft green', '4D9B35', .55)
    M['edge'] = material('Dark olive outline | inverted hull', '3C542B', 1)
    M['mount'] = material('Kit pale green mounts', 'E2EECF', .72)
    p = M['edge'].node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (0, 0, 0, 1)
    p.inputs['Emission Color'].default_value = rgba('3C542B')
    p.inputs['Emission Strength'].default_value = 1
    # Reduce broad white reflections without changing the specified base colors.
    for key in ('pomelo', 'cream', 'leaf', 'blush'):
        M[key].node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value = .28


def head_q(x, z):
    t = (z - HEAD_Z) / HEAD_C
    return abs(t) ** HEAD_P + abs(x / (HEAD_A * (1 - .17 * t))) ** HEAD_P


def head_y(x, z, back=False):
    depth = HEAD_B * max(0, 1 - head_q(x, z)) ** (1 / HEAD_P)
    return depth if back else -depth


def face_y(x, z):
    return head_y(x, z) + .0015


def face_boundary(a):
    x = .336 * math.cos(a)
    sine = math.sin(a)
    z = FACE_Z + (.267 if sine > 0 else .235) * sine
    if sine > 0:
        z -= .090 * math.exp(-(x / .120) ** 2)
    return x, z


def head_boundary(x, z):
    dx, dz = x, z - FACE_Z
    low, high = 1.0, 4.0
    for _ in range(42):
        t = (low + high) / 2
        if head_q(t * dx, FACE_Z + t * dz) < 1:
            low = t
        else:
            high = t
    return low * dx, FACE_Z + low * dz


def orient_front(ob):
    if sum(p.normal.y * p.area for p in ob.data.polygons) > 0:
        bm = bmesh.new(); bm.from_mesh(ob.data)
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
        bm.to_mesh(ob.data); bm.free()
    return ob


def radial_patch(name, boundary, center, surface, mat, parent, rings=7, dome=0):
    n = len(boundary)
    cx, cz = center
    verts = [(cx, surface(cx, cz) - dome, cz)]
    for j in range(1, rings + 1):
        r = j / rings
        for bx, bz in boundary:
            x, z = cx + r * (bx - cx), cz + r * (bz - cz)
            y = surface(x, z) - dome * max(0, 1 - r * r) ** .65
            verts.append((x, y, z))
    faces = [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)]
    for j in range(rings - 1):
        a, b = 1 + j * n, 1 + (j + 1) * n
        for i in range(n):
            k = (i + 1) % n
            faces.append((a + i, b + i, b + k, a + k))
    return orient_front(mesh(name, verts, faces, mat, parent))


def ellipse_patch(name, x, z, rx, rz, mat, parent, offset=.002, dome=.001, surface=face_y, segments=32, rings=5):
    boundary = [(x + rx * math.cos(a), z + rz * math.sin(a)) for a in np.linspace(0, TAU, segments, endpoint=False)]
    return radial_patch(name, boundary, (x, z), lambda xx, zz: surface(xx, zz) - offset, mat, parent, rings, dome)


def build_head(parent):
    n = 128
    boundary = [face_boundary(a) for a in np.linspace(0, TAU, n, endpoint=False)]
    outer = [head_boundary(x, z) for x, z in boundary]
    verts, faces = [], []
    # Cosine spacing concentrates samples at the silhouette for a smooth side view.
    for j in range(11):
        t = math.sin(math.pi * j / 20)
        for (ix, iz), (ox, oz) in zip(boundary, outer):
            x, z = ix * (1 - t) + ox * t, iz * (1 - t) + oz * t
            lip = .0015 * (1 - t) - .003 * math.sin(math.pi * min(1, t * 4)) if t < .25 else 0
            verts.append((x, head_y(x, z) + lip, z))
    for j in range(1, 20):
        t = 1 - math.cos(math.pi * j / 40)
        for ox, oz in outer:
            x, z = ox * (1 - t), FACE_Z + (oz - FACE_Z) * (1 - t)
            verts.append((x, head_y(x, z, True), z))
    for j in range(29):
        for i in range(n):
            k = (i + 1) % n
            faces.append((j * n + i, j * n + k, (j + 1) * n + k, (j + 1) * n + i))
    rear = len(verts); verts.append((0, head_y(0, FACE_Z, True), FACE_Z))
    for i in range(n):
        faces.append((29 * n + i, 29 * n + (i + 1) % n, rear))
    # A shallow crown dip gives the paired stems a soft seat.
    verts = [(x, y, z - .005 * math.exp(-(x / .032) ** 2 - (y / .038) ** 2) * max(0, min(1, (z - .87) / .04))) for x, y, z in verts]
    shell = mesh('Head/PomeloShell', verts, faces, M['pomelo'], parent, outline=.00085)
    shell['shape'] = 'Pear profile, broad cheeks, tapered crown; continuous green shell with recessed face opening'
    radial_patch('Head/CreamFaceMask', boundary, (0, FACE_Z), face_y, M['cream'], parent, 12)
    return shell


def surface_stroke(name, points, radius, mat, parent, offset=.003):
    return rounded_stroke(name, [(x, face_y(x, z) - offset, z) for x, z in points], radius, mat, parent, sides=8)


def mouth(parent, expression):
    name = 'Face/' + expression.title() + '/Mouth'
    if expression in ('thinking', 'sad'):
        rx = .029 if expression == 'sad' else .022
        pts = [(rx * t, .425 + .011 * (1 - t * t)) for t in np.linspace(-1, 1, 18)]
        surface_stroke(name + '_Frown', pts, .0034, M['eye'], parent)
    elif expression == 'surprised':
        ellipse_patch(name + '_OpenO', 0, .443, .024, .037, M['mouth'], parent, .0025, .001)
        ellipse_patch(name + '_Tongue', 0, .426, .017, .013, M['tongue'], parent, .005, .001)
    else:
        # Rounded smile boundary: nearly level upper lip and a generous U-shaped lower lip.
        boundary = []
        for a in np.linspace(0, TAU, 64, endpoint=False):
            x = .071 * math.cos(a)
            z = .455 + (.006 * math.sin(a) if math.sin(a) >= 0 else .084 * math.sin(a))
            boundary.append((x, z))
        radial_patch(name + '_OpenSmile', boundary, (0, .427), lambda x, z: face_y(x, z) - .003, M['mouth'], parent, 7, .001)
        # The tongue is clipped naturally inside the lower U, never a floating sphere.
        ellipse_patch(name + '_Tongue', 0, .400, .048, .025, M['tongue'], parent, .005, .003, segments=40)


def face_features(parent, expression):
    group = empty('Expression_' + expression.title(), parent)
    group['expression'] = expression
    for side, label in [(-1, 'L'), (1, 'R')]:
        cx, cz = side * .145, .552
        prefix = 'Face/' + expression.title() + '/' + label
        if expression == 'laugh':
            pts = [(cx + .041 * math.cos(a), cz - .006 + .041 * math.sin(a)) for a in np.linspace(.12, math.pi - .12, 24)]
            surface_stroke(prefix + '_LaughEye', pts, .008, M['eye'], group)
        elif expression == 'wink' and side == 1:
            surface_stroke(prefix + '_WinkEye', [(cx + .029, cz + .024), (cx - .026, cz), (cx + .029, cz - .024)], .007, M['eye'], group)
        else:
            rx, rz = (.049, .069) if expression != 'sad' else (.043, .060)
            ellipse_patch(prefix + '_Eye', cx, cz, rx, rz, M['eye'], group, .003, .009, segments=40, rings=7)
            def eye_surface(x, z, cx=cx, cz=cz, rx=rx, rz=rz):
                q = ((x - cx) / rx) ** 2 + ((z - cz) / rz) ** 2
                return face_y(x, z) - .003 - .009 * max(0, 1 - q) ** .65
            ellipse_patch(prefix + '_WhiteHighlight', cx + .010, cz + .028, .015, .020, M['white'], group, .0014, .001, eye_surface, 24, 4)
        ellipse_patch(prefix + '_Blush', side * .244, .461, .039, .029, M['blush'], group, .0022, .0007, segments=32)
        if expression == 'sad':
            pts = [(cx + side * t, .642 - .38 * t) for t in np.linspace(-.018, .021, 12)]
            surface_stroke(prefix + '_WorriedBrow', pts, .0032, M['eye'], group)
    mouth(group, expression)
    return group


def leaf(parent, side):
    name = 'Leaves/' + ('L' if side < 0 else 'R')
    # A small solid lens with a gently swept central ridge and softly pointed ends.
    length = .176 if side < 0 else .167
    axis = Vector((side * .87, .05 if side < 0 else .14, .49)).normalized()
    cross = Vector((-side * .49, 0, .87)).normalized()
    normal = axis.cross(cross).normalized()
    if normal.y > 0:
        normal = -normal
    origin = Vector((side * .010, .004, .918))
    n, rows = 12, 16
    verts = [origin]
    for j in range(1, rows):
        t = j / rows
        width = .042 * math.sin(math.pi * t) ** .85
        thickness = .009 * math.sin(math.pi * t)
        center = origin + axis * (length * t) + Vector((0, -.014 * math.sin(math.pi * t), .003 * math.sin(math.pi * t)))
        for i in range(n):
            a = TAU * i / n
            verts.append(center + cross * (width * math.cos(a)) + normal * (thickness * math.sin(a)))
    end = len(verts); verts.append(origin + axis * length)
    faces = [(0, 1 + (i + 1) % n, 1 + i) for i in range(n)]
    for j in range(rows - 2):
        for i in range(n):
            a, b = 1 + j * n + i, 1 + j * n + (i + 1) % n
            faces.append((a, b, b + n, a + n))
    for i in range(n):
        faces.append((1 + (rows - 2) * n + i, 1 + (rows - 2) * n + (i + 1) % n, end))
    # Keep the complete blade height within the board's 7-9% target, including its width.
    verts = [(v[0], v[1], origin.z + .85 * (v[2] - origin.z)) for v in verts]
    mesh(name + '_Blade', verts, faces, M['leaf'], parent, outline=.00065)
    pts = []
    for t in np.linspace(.09, .93, 20):
        c = origin + axis * (length * t) + Vector((0, -.014 * math.sin(math.pi * t), .003 * math.sin(math.pi * t)))
        pts.append(c + normal * (.009 * math.sin(math.pi * t) + .0007))
    pts = [(v[0], v[1], origin.z + .85 * (v[2] - origin.z)) for v in pts]
    tube(name + '_Midrib', pts, .0012, M['vein'], parent, 6)


def body(parent, pose, expression):
    group = empty('Body', parent)
    ellipsoid('Body/Torso', (0, .065, .208), (.239, .157, .147), M['pomelo'], group, 40, 24, 2.4, .00085)
    def belly_surface(x, z):
        q = abs(x / .239) ** 2.4 + abs((z - .208) / .147) ** 2.4
        return .065 - .157 * max(.001, 1 - q) ** (1 / 2.4)
    ellipse_patch('Body/CreamBelly', 0, .169, .123, .077, M['cream'], group, .0018, .002, belly_surface, 48, 8)
    for side, label in [(-1, 'L'), (1, 'R')]:
        ellipsoid('Body/' + label + '_StubbyLeg', (side * .125, .004, .072), (.062, .068, .061), M['pomelo'], group, 20, 12, 2.4)
        foot = ellipsoid('Body/' + label + '_CreamFoot', (side * .125, -.038, .0435), (.094, .111, .042), M['cream'], group, 32, 16, 2.7, .00075)
        # The soles are broad and nearly flat; normalization places their hull at Y=0 in glTF.
        if expression in ('thinking', 'sad') and side == 1:
            loc, scale = (.195, -.245, .345), (.049, .048, .065)
            a, b, c, d = [Vector(v) for v in ((.222, -.04, .234), (.220, -.15, .240), (.213, -.21, .290), (.195, -.245, .340))]
            arm_points = [(1-t)**3*a + 3*(1-t)**2*t*b + 3*(1-t)*t*t*c + t**3*d for t in np.linspace(0, 1, 18)]
            tube('Body/R_RaisedForearm', arm_points, .028, M['cream'], group, 10)
            hand = ellipsoid('Body/R_ChinMitten', loc, scale, M['cream'], group, 28, 18, 2.25, .00065)
            hand.rotation_euler.y = -.25
        else:
            x, z = (.275, .237) if pose == 'hero' else (.252, .181)
            ellipsoid('Body/' + label + '_ArmConnector', (side * .223, -.005, z + .012), (.045, .052, .043), M['pomelo'], group, 20, 12)
            hand = ellipsoid('Body/' + label + '_CreamMitten', (side * x, -.041, z), (.056, .058, .070), M['cream'], group, 28, 18, 2.2, .00065)
            hand.rotation_euler.y = side * (.17 if pose == 'hero' else .08)
    return group


def build_character(name='PomeloStemMascot', expression='happy', pose='hero'):
    root = empty(name)
    root['expression'] = expression
    root['pose'] = pose
    root['palette'] = json.dumps(PALETTE, sort_keys=True)
    root['units'] = 'metres'
    head = empty('Head', root)
    build_head(head)
    face_features(head, expression)
    leaves = empty('Leaves', root)
    ellipsoid('Leaves/Stem', (0, .004, .918), (.010, .011, .022), M['leaf'], leaves, 16, 12, 2.3, .0006)
    leaf(leaves, -1); leaf(leaves, 1)
    body(root, pose, expression)
    normalize_character(root)
    return root


def visibility(root, visible):
    for ob in descendants(root):
        ob.hide_render = not visible
        ob.hide_set(not visible)


def text_geometry(name, content, loc, size, parent):
    data = bpy.data.curves.new(name + '_Bfont', 'FONT')
    data.body = content; data.size = size; data.align_x = 'CENTER'; data.align_y = 'CENTER'
    data.resolution_u = 3; data.extrude = .00025
    ob = bpy.data.objects.new(name, data); SCENE.collection.objects.link(ob)
    ob.parent = parent; ob.location = loc; ob.rotation_euler.x = math.pi / 2
    data.materials.append(M['edge'])
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
    bpy.context.view_layer.objects.active = ob; bpy.ops.object.convert(target='MESH')
    return ob


def build_kit(root):
    row = empty('KIT_ExpressionMountRow', root, (0, 1.55, 0))
    row['description'] = 'Six complete expression figures on a separate visible row; local character feet remain at zero'
    mounts = []
    for i, expression in enumerate(EXPRESSIONS):
        mount = empty(f'Mount_{i + 1:02d}_Expression_{expression.title()}', row, ((i - 2.5) * .93, 0, 0))
        figure = build_character('KitFigure_' + expression.title(), expression, 'hero')
        figure.parent = mount
        # Base and label sit behind the foot plane, preserving the contract floor.
        ellipsoid('MountBase_' + expression.title(), (0, .035, .0004), (.425, .185, .00035), M['mount'], mount, 32, 10, 3)
        mounts.append(mount)
    return row, mounts


def setup_studio():
    studio = empty('STUDIO_SourceOnly')
    world = bpy.data.worlds.new('Soft pale-green studio')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = rgba('E5EED8')
    world.node_tree.nodes['Background'].inputs[1].default_value = .42
    SCENE.world = world
    for name, loc, power, size, color in [
        ('Key', (-2.5, -3.8, 4), 140, 3.5, 'FFFAEB'),
        ('Fill', (3, -2, 2.5), 95, 3.0, 'F7FFF0'),
        ('Rim', (1.2, 2.7, 3), 110, 2.5, 'F4FFE3'),
        ('FrontSoftbox', (0, -4, .6), 85, 3.5, 'FFFBEF'),
        ('Bounce', (0, -2, -1.5), 65, 3.0, 'FFF8DF'),
    ]:
        bpy.ops.object.light_add(type='AREA', location=loc)
        ob = bpy.context.object; ob.name = 'Studio_' + name; ob.parent = studio
        ob.data.energy = power * .66; ob.data.shape = 'DISK'; ob.data.size = size
        ob['studio_base_location'] = loc
        ob.data.use_shadow = False; ob.data.color = rgba(color)[:3]; aim(ob, (0, 0, .5))
    bpy.ops.object.camera_add(location=(1.6, -3.3, 1.0))
    camera = bpy.context.object; camera.name = 'PreviewCamera'; camera.parent = studio
    camera.data.type = 'ORTHO'; camera.data.ortho_scale = 1.20
    SCENE.camera = camera
    SCENE.render.engine = 'BLENDER_EEVEE'
    if hasattr(SCENE, 'eevee') and hasattr(SCENE.eevee, 'taa_render_samples'):
        SCENE.eevee.taa_render_samples = 48
    SCENE.render.resolution_x = 1024; SCENE.render.resolution_y = 1024
    SCENE.render.resolution_percentage = 100
    SCENE.render.image_settings.file_format = 'PNG'; SCENE.render.image_settings.color_mode = 'RGBA'
    SCENE.render.film_transparent = True
    SCENE.view_settings.view_transform = 'Standard'; SCENE.view_settings.look = 'None'
    SCENE.view_settings.exposure = 0
    return studio


def apply_compositing():
    tree = bpy.data.node_groups.new('Pale green studio background', 'CompositorNodeTree')
    SCENE.compositing_node_group = tree
    tree.interface.new_socket(name='Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    out = tree.nodes.new('NodeGroupOutput')
    layer = tree.nodes.new('CompositorNodeRLayers')
    yy, xx = np.mgrid[0:1024, 0:1024].astype(np.float32)
    xx /= 1023; yy /= 1023
    t = np.clip(.20 + .65 * yy + .24 * np.exp(-((xx - .38) ** 2 + (yy - .68) ** 2) / .20), 0, 1)
    lower, upper = np.array(rgba('DBEBCB')[:3]), np.array(rgba('FAFCF5')[:3])
    pixels = np.ones((1024, 1024, 4), dtype=np.float32)
    pixels[:, :, :3] = lower * (1 - t[:, :, None]) + upper * t[:, :, None]
    shadow = .19 * np.exp(-((xx - .5) / .24) ** 2 - ((yy - .083) / .018) ** 2)
    pixels[:, :, :3] *= 1 - shadow[:, :, None]
    backdrop = bpy.data.images.new('Studio pale-green gradient', width=1024, height=1024, alpha=True, float_buffer=True)
    backdrop.pixels.foreach_set(pixels.ravel()); backdrop.pack()
    im = tree.nodes.new('CompositorNodeImage'); im.image = backdrop
    over = tree.nodes.new('CompositorNodeAlphaOver')
    over.inputs['Factor'].default_value = 1
    tree.links.new(im.outputs['Image'], over.inputs['Background'])
    tree.links.new(layer.outputs['Image'], over.inputs['Foreground'])
    tree.links.new(over.outputs['Image'], out.inputs['Image'])


def render_one(name, loc, target=(0, 0, .5), scale=1.20):
    SCENE.camera.location = loc; aim(SCENE.camera, target); SCENE.camera.data.ortho_scale = scale
    angle = math.atan2(loc[0] - target[0], -(loc[1] - target[1]))
    for light in SCENE.objects:
        if light.type == 'LIGHT' and 'studio_base_location' in light:
            x, y, z = light['studio_base_location']
            light.location = (target[0] + x*math.cos(angle)-y*math.sin(angle), target[1] + x*math.sin(angle)+y*math.cos(angle), z + target[2] - .5)
            aim(light, target)
    SCENE.render.filepath = str(ROOT / 'previews' / (name + '.png'))
    print('RENDER_VIEW', name, flush=True)
    bpy.ops.render.render(write_still=True)


def image_canvas(name, items, width, height, background=(.96, .98, .93, 1)):
    canvas = np.empty((height, width, 4), dtype=np.float32); canvas[:] = background
    loaded = []
    for path, x, y, tw, th in items:
        im = bpy.data.images.load(str(path), check_existing=False); loaded.append(im)
        iw, ih = im.size
        pix = np.asarray(im.pixels[:], dtype=np.float32).reshape(ih, iw, 4)
        ix = np.minimum((np.arange(tw) * iw / tw).astype(int), iw - 1)
        iy = np.minimum((np.arange(th) * ih / th).astype(int), ih - 1)
        canvas[y:y + th, x:x + tw] = pix[iy[:, None], ix[None, :]]
    result = bpy.data.images.new(name, width=width, height=height, alpha=True)
    result.pixels.foreach_set(canvas.ravel()); result.filepath_raw = str(ROOT / 'previews' / (name + '.png'))
    result.file_format = 'PNG'; result.save()
    for im in loaded + [result]:
        bpy.data.images.remove(im)


def render_views(root, row, mounts, quick=False):
    visibility(row, False)
    render_one('front', (0, -4, .5))
    if not quick:
        render_one('side', (4, 0, .5))
        render_one('back', (0, 4, .5))
    render_one('3q', (1.6, -3.6, 1.10), scale=1.23)
    if not quick:
        # Render each real kit mount without moving it, then make a legible 3x2 atlas.
        for ob in descendants(root):
            if ob not in descendants(row):
                ob.hide_render = True
        for i, mount in enumerate(mounts):
            visibility(mount, True)
            bpy.context.view_layer.update()
            center = mount.matrix_world.translation
            name = 'expression-' + EXPRESSIONS[i]
            render_one(name, (center.x, center.y - 4, .5), (center.x, center.y, .5), 1.17)
            visibility(mount, False)
        # A temporary 3x2 render layout makes the atlas readable; the GLB remains one row.
        saved_locations = [m.location.copy() for m in mounts]
        saved_row = row.location.copy()
        row.location = (0, 0, 0)
        labels = []
        for i, mount in enumerate(mounts):
            visibility(mount, True)
            mount.location = ((i % 3 - 1) * .94, 0, .67 if i < 3 else -.67)
            for ob in descendants(mount):
                if ob.name.startswith('MountLabel_'):
                    ob.hide_render = True
            labels.append(text_geometry('AtlasLabel_' + EXPRESSIONS[i], EXPRESSIONS[i].title(), (0, -.32, -.080), .068, mount))
        render_one('expressions', (0, -6, .5), (0, 0, .5), 2.88)
        for label in labels:
            bpy.data.objects.remove(label, do_unlink=True)
        row.location = saved_row
        for mount, loc in zip(mounts, saved_locations):
            mount.location = loc
        visibility(root, True); visibility(row, False)
    optional_reference = ROOT / 'optional-reference.png'
    if optional_reference.is_file():
        image_canvas('optional-comparison', [(ROOT / 'previews/front.png', 0, 0, 1024, 1024), (optional_reference, 1024, 0, 1536, 1024)], 2560, 1024)
    else:
        print('OPTIONAL_COMPARISON_SKIPPED optional reference image is absent; all other previews were generated', flush=True)


def main():
    global SCENE
    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--no-render', action='store_true')
    parser.add_argument('--expression', choices=EXPRESSIONS, default='happy')
    parser.add_argument('--pose', choices=('hero', 'stand'), default='hero')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    SCENE = bpy.context.scene
    SCENE.unit_settings.system = 'METRIC'; SCENE.unit_settings.scale_length = 1
    for name in ('exports', 'previews', 'reports'):
        (ROOT / name).mkdir(exist_ok=True)
    materials()
    root = build_character()
    metrics = {'blender_version': bpy.app.version_string, 'blender_build': bpy.app.build_hash.decode(), 'palette': PALETTE}
    metrics['default'] = export_glb(ROOT / 'exports/pomelo-stem-mascot.glb', descendants(root))
    metrics['default']['blender_bounds'] = world_bounds(descendants(root))
    assert metrics['default']['triangles'] < 40000
    assert metrics['default']['bytes'] < 2 * 1024 ** 2
    # Every deliverable has exactly the same requested scene-root name.
    root.name = 'Source_Hero'
    stand = build_character('PomeloStemMascot', 'happy', 'stand')
    metrics['stand'] = export_glb(ROOT / 'exports/pomelo-stem-mascot-stand.glb', descendants(stand))
    stand.name = 'Alternative_Stand'; visibility(stand, False)
    root.name = 'PomeloStemMascot'
    row, mounts = build_kit(root)
    metrics['kit'] = export_glb(ROOT / 'exports/pomelo-stem-mascot-kit.glb', descendants(root))
    assert metrics['kit']['bytes'] < 5 * 1024 ** 2
    visibility(row, False)
    if args.expression != 'happy' or args.pose != 'hero':
        root.name = 'Source_Hero'
        custom = build_character('PomeloStemMascot', args.expression, args.pose)
        metrics['custom'] = export_glb(ROOT / 'exports/pomelo-stem-mascot-custom.glb', descendants(custom))
        custom.name = 'Alternative_Custom'; visibility(custom, False)
        root.name = 'PomeloStemMascot'
    setup_studio(); apply_compositing()
    SCENE['asset_contract'] = 'Native metres; glTF +Y up, front +Z; feet Y=0; real geometry; no textures'
    SCENE['source_notes'] = 'Alternative_Stand and KIT_ExpressionMountRow hidden only for studio; kit exports all mounts visible'
    SCENE['generator'] = 'generate.py'
    SCENE.camera.location = (1.6, -3.6, 1.1); aim(SCENE.camera, (0, 0, .5))
    bpy.ops.object.select_all(action='DESELECT'); root.select_set(True); bpy.context.view_layer.objects.active = root
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'pomelo-stem-mascot.blend'), compress=True)
    if not args.no_render:
        render_views(root, row, mounts, args.quick)
    (ROOT / 'reports/generation.json').write_text(json.dumps(metrics, indent=2) + '\n')
    print('GENERATION_COMPLETE', json.dumps(metrics), flush=True)


if __name__ == '__main__':
    main()
