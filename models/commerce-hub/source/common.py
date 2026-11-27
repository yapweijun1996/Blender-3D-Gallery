"""Local Blender geometry, studio setup, and checked Commerce Hub delivery."""

import hashlib
import json
import math
import os
import struct
import tempfile
from pathlib import Path

import bpy
from mathutils import Vector


MODULE_DIR = Path(__file__).resolve().parents[1]
PLINTH_SIZE = 4.60
PLINTH_OUTER_RADIUS = 0.56
PLINTH_OUTER_HEIGHT = 0.34
PLINTH_INNER_SIZE = 3.94
PLINTH_INNER_HEIGHT = 0.17
PLINTH_HEIGHT = PLINTH_OUTER_HEIGHT + PLINTH_INNER_HEIGHT
TAU = 2 * math.pi
FX_COLOR = "Effect RGBA"
FLOOR_EFFECTS = ("Fx_ContactShadow", "Fx_FloorGlow")

PALETTE = {
    "Sage": "#8BB47D",
    "Inner Grey": "#D0D0D0",
    "Cream Backdrop": "#F8F0E7",
    "Bag Paper": "#FFBB54",
    "Bag Lining": "#F08A17",
    "Bag Lip": "#FFE3A7",
    "Bag Handle": "#FFCA72",
}


def linear_color(hex_color):
    srgb = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
                 for c in srgb)


def material(name, color=None, roughness=0.42, metallic=0.0, alpha=1.0,
             emission=None, strength=0.0, specular=0.5):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    rgba = (*linear_color(color or PALETTE[name]), alpha)
    mat.diffuse_color = rgba
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = rgba
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Specular IOR Level"].default_value = specular
    shader.inputs["Alpha"].default_value = alpha
    if alpha < 1:
        mat.surface_render_method = "BLENDED"
    if emission:
        shader.inputs["Emission Color"].default_value = (*linear_color(emission), 1)
        shader.inputs["Emission Strength"].default_value = strength
    return mat


def rounded_rect(width, depth, radius, steps):
    half_x, half_y = width / 2, depth / 2
    corners = (
        (half_x - radius, half_y - radius),
        (-half_x + radius, half_y - radius),
        (-half_x + radius, -half_y + radius),
        (half_x - radius, -half_y + radius),
    )
    if radius == 0:
        return list(corners)
    return [
        (x + radius * math.cos(angle), y + radius * math.sin(angle))
        for quarter, (x, y) in enumerate(corners)
        for angle in [math.pi / 2 * (quarter + i / steps)
                      for i in range(steps + 1)]
    ]


class MeshPart:
    """Collect geometry into one named object and one primitive per material."""

    def __init__(self, collection, name, origin=(0, 0, 0)):
        self.collection = collection
        self.name = name
        self.origin = Vector(origin)
        self.vertices = []
        self.faces = []
        self.materials = []
        self.face_settings = []

    def add(self, vertices, faces, mat, smooth=False):
        offset = len(self.vertices)
        self.vertices.extend(vertices)
        self.faces.extend(tuple(offset + index for index in face) for face in faces)
        if mat not in self.materials:
            self.materials.append(mat)
        self.face_settings.extend([(self.materials.index(mat), smooth)] * len(faces))

    def loft(self, rings, mat, caps=(True, True), smooth=True):
        count = len(rings[0])
        vertices = [vertex for ring in rings for vertex in ring]
        sides = [
            (start + i, start + (i + 1) % count,
             start + count + (i + 1) % count, start + count + i)
            for start in range(0, (len(rings) - 1) * count, count)
            for i in range(count)
        ]
        start = len(self.vertices)
        self.add(vertices, sides, mat, smooth)
        if caps[0]:
            self.faces.append(tuple(reversed(range(start, start + count))))
            self.face_settings.append((self.materials.index(mat), False))
        if caps[1]:
            end = start + len(vertices)
            self.faces.append(tuple(range(end - count, end)))
            self.face_settings.append((self.materials.index(mat), False))

    def box(self, center, size, mat, edge=0, corner=None, steps=2,
            bevel_steps=1, transform=None):
        x, y, z = center
        width, depth, height = size
        bottom, top = z - height / 2, z + height / 2
        if edge:
            # Separate the plan corner radius from the fillet of the top and bottom.
            edge = min(edge, min(size) * 0.32)
            corner = max(edge * 1.10, corner or edge * 1.55)
            corner = min(corner, min(width, depth) * 0.48)
            angles = [math.pi / 2 * i / bevel_steps for i in range(bevel_steps + 1)]
            profile = [(bottom + edge * (1 - math.cos(t)), edge * (1 - math.sin(t)))
                       for t in angles]
            profile += [(top - edge + edge * math.sin(t), edge * (1 - math.cos(t)))
                        for t in angles]
        else:
            corner = 0
            profile = [(bottom, 0), (top, 0)]
        rings = [
            [(x + rx, y + ry, level)
             for rx, ry in rounded_rect(width - 2 * inset, depth - 2 * inset,
                                        corner - inset, steps)]
            for level, inset in profile
        ]
        if transform:
            rings = [[transform(point) for point in ring] for ring in rings]
        self.loft(rings, mat, smooth=bool(edge))

    def lathe(self, center, profile, mat, sides=16, caps=(True, True)):
        x, y, z = center
        ring = [(math.cos(TAU * i / sides), math.sin(TAU * i / sides))
                for i in range(sides)]
        self.loft([[(x + r * u, y + r * v, z + h) for u, v in ring]
                   for r, h in profile], mat, caps=caps)

    def tube(self, points, radius, mat, sides=8, guide=(0, 1, 0), closed=False,
             end_radius=None):
        points = [Vector(p) for p in points]
        axis = Vector(guide)
        rings = []
        for i, point in enumerate(points):
            before = points[(i - 1) % len(points)] if closed or i else point
            after = points[(i + 1) % len(points)] if closed or i < len(points) - 1 else point
            tangent = (after - before).normalized()
            u = axis.cross(tangent).normalized()
            v = tangent.cross(u)
            ring_radius = radius
            if end_radius is not None and i in (0, len(points) - 1):
                ring_radius = end_radius
            rings.append([
                tuple(point + ring_radius * (math.cos(TAU * j / sides) * u
                                             + math.sin(TAU * j / sides) * v))
                for j in range(sides)
            ])
        if closed:
            vertices = [point for ring in rings for point in ring]
            faces = [
                (i * sides + j, i * sides + (j + 1) % sides,
                 ((i + 1) % len(rings)) * sides + (j + 1) % sides,
                 ((i + 1) % len(rings)) * sides + j)
                for i in range(len(rings))
                for j in range(sides)
            ]
            self.add(vertices, faces, mat, smooth=True)
        else:
            self.loft(rings, mat)

    def finish(self):
        mesh = bpy.data.meshes.new(self.name)
        mesh.from_pydata([Vector(vertex) - self.origin for vertex in self.vertices],
                         [], self.faces)
        if mesh.validate(verbose=False):
            raise ValueError(f"{self.name} required mesh repair")
        for mat in self.materials:
            mesh.materials.append(mat)
        for polygon, (index, smooth) in zip(mesh.polygons, self.face_settings, strict=True):
            polygon.material_index = index
            polygon.use_smooth = smooth
        mesh.update()
        obj = bpy.data.objects.new(self.name, mesh)
        obj.location = self.origin
        self.collection.objects.link(obj)
        return obj


def geometry_text(part, text, center, width, height, paint, place, *, weight=0, resolution=5):
    """Size the filled Blender font to the sign's face before merging its mesh."""
    curve = bpy.data.curves.new(f"Lettering {text}", "FONT")
    curve.body = text
    curve.resolution_u = resolution
    curve.offset = weight
    obj = bpy.data.objects.new(curve.name, curve)
    try:
        part.collection.objects.link(obj)
        bpy.context.view_layer.update()
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        try:
            xs = [vertex.co.x for vertex in mesh.vertices]
            ys = [vertex.co.y for vertex in mesh.vertices]
            left, bottom = min(xs), min(ys)
            sx, sy = width / (max(xs) - left), height / (max(ys) - bottom)
            u, v, relief = center
            part.add([place((u + (x - left) * sx - width / 2,
                             v + (y - bottom) * sy - height / 2, relief))
                      for x, y in zip(xs, ys, strict=True)],
                     [tuple(polygon.vertices) for polygon in mesh.polygons], paint)
        finally:
            evaluated.to_mesh_clear()
    finally:
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.curves.remove(curve)


def plinth(collection):
    specs = (
        ("Plinth_Outer", PLINTH_SIZE, PLINTH_OUTER_HEIGHT, PLINTH_OUTER_RADIUS, 0.065, 0.0, "Sage"),
        ("Plinth_Inner", PLINTH_INNER_SIZE, PLINTH_INNER_HEIGHT, 0.49, 0.062,
         PLINTH_OUTER_HEIGHT, "Inner Grey"),
    )
    for name, size, height, radius, edge, base, paint in specs:
        slab = MeshPart(collection, name, origin=(0, 0, base))
        slab.box((0, 0, base + height / 2), (size, size, height),
                 material(paint, roughness=0.34), edge=edge, corner=radius,
                 steps=10, bevel_steps=4)
        slab.finish()


def gradient_material():
    mat = bpy.data.materials.new("Unlit Gradient Effects")
    mat.use_nodes = True
    mat.surface_render_method = "BLENDED"
    mat.use_backface_culling = False
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    colors = nodes.new("ShaderNodeVertexColor")
    colors.layer_name = FX_COLOR
    emission = nodes.new("ShaderNodeEmission")
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    camera = nodes.new("ShaderNodeLightPath")
    visible = nodes.new("ShaderNodeMixShader")
    blend = nodes.new("ShaderNodeMixShader")
    output = nodes.new("ShaderNodeOutputMaterial")
    # Match the glTF importer's unlit graph so export recovers both vertex channels.
    links.new(colors.outputs["Color"], emission.inputs["Color"])
    links.new(camera.outputs["Is Camera Ray"], visible.inputs[0])
    links.new(transparent.outputs[0], visible.inputs[1])
    links.new(emission.outputs[0], visible.inputs[2])
    links.new(colors.outputs["Alpha"], blend.inputs[0])
    links.new(transparent.outputs[0], blend.inputs[1])
    links.new(visible.outputs[0], blend.inputs[2])
    links.new(blend.outputs[0], output.inputs["Surface"])
    return mat


def gradient_surface(part, mat, vertices, faces, color, alphas):
    part.add(vertices, faces, mat)
    mesh = part.finish().data
    layer = mesh.color_attributes.new(name=FX_COLOR, type="FLOAT_COLOR", domain="POINT")
    rgb = linear_color(color)
    for datum, alpha in zip(layer.data, alphas, strict=True):
        datum.color = (*rgb, alpha)


def strip_faces(start, count, rings):
    return [
        (offset + i, offset + count + i, offset + count + (i + 1) % count,
         offset + (i + 1) % count)
        for offset in range(start, start + (rings - 1) * count, count)
        for i in range(count)
    ]


def perimeter_gradient(collection, name, mat, size, radius, z, color, stops, steps=10):
    """Follow the plinth profile with independently offset, feathered contours."""
    vertices = [
        (x + dx, y + dy, z)
        for spread, dx, dy, _ in stops
        for x, y in rounded_rect(size + 2 * spread, size + 2 * spread, radius + spread, steps)
    ]
    count = len(vertices) // len(stops)
    part = MeshPart(collection, name, origin=(0, 0, z))
    gradient_surface(part, mat, vertices, strip_faces(0, count, len(stops)), color,
                     [alpha for _, _, _, alpha in stops for _ in range(count)])


def floor_effects(collection, mat):
    shadow, glow = FLOOR_EFFECTS
    # In the three-quarter views, +X/-Y shifts the wider shadow down and right.
    perimeter_gradient(collection, shadow, mat, PLINTH_SIZE, PLINTH_OUTER_RADIUS, 0.002,
                       "#776256", (
                           (-0.18, 0, 0, 0), (-0.055, 0.024, -0.040, 0.40),
                           (0.045, 0.075, -0.115, 0.36), (0.16, 0.11, -0.16, 0.24),
                           (0.325, 0.12, -0.20, 0.085), (0.61, 0, 0, 0),
                       ))
    perimeter_gradient(collection, glow, mat, PLINTH_SIZE, PLINTH_OUTER_RADIUS, 0.006,
                       "#FFC052", [(spread, 0, 0, alpha) for spread, alpha in (
                           (-0.12, 0), (-0.047, 0.33), (-0.006, 0.72), (0.052, 0.56),
                           (0.112, 0.27), (0.180, 0.080), (0.275, 0),
                       )])


AO_EFFECT = "Fx_AmbientOcclusion"
AO_BUDGET = {"triangles": 3200, "bytes": 110000, "primitives": 1}


def bake_ambient_occlusion(model, mat, cell=0.095, rays=64, reach=0.55, strength=0.78, limit=0.46):
    """Ray-cast soft contact darkening onto a vertex-alpha layer over the inner plinth.

    Only sky occlusion is baked. Directional shadows are left to the viewer, so they are not doubled.
    """
    from mathutils.bvhtree import BVHTree

    bpy.context.view_layer.update()
    vertices, polygons = [], []
    for obj in model.objects:
        if obj.type != "MESH" or obj.name.startswith(("Fx_", "Plinth_")) or "Glass" in obj.name:
            continue
        offset = len(vertices)
        vertices.extend(obj.matrix_world @ vertex.co for vertex in obj.data.vertices)
        polygons.extend(tuple(offset + index for index in polygon.vertices) for polygon in obj.data.polygons)
    tree = BVHTree.FromPolygons(vertices, polygons)

    # Fixed cosine-weighted spiral so a rebuild produces identical bytes.
    golden = math.pi * (3 - math.sqrt(5))
    directions = []
    for i in range(rays):
        radius = math.sqrt((i + 0.5) / rays)
        angle = i * golden
        directions.append(Vector((radius * math.cos(angle), radius * math.sin(angle),
                                  math.sqrt(1 - radius * radius))))

    size, corner = PLINTH_INNER_SIZE - 0.14, 0.42
    count = int(size / cell)
    step = size / count
    height = PLINTH_HEIGHT + 0.004

    def inside(x, y):
        dx, dy = abs(x) - (size / 2 - corner), abs(y) - (size / 2 - corner)
        return dx <= 0 or dy <= 0 or dx * dx + dy * dy <= corner * corner

    points, alphas = [], []
    for row in range(count + 1):
        for column in range(count + 1):
            x, y = -size / 2 + column * step, -size / 2 + row * step
            origin = Vector((x, y, height))
            occlusion = 0.0
            for direction in directions:
                hit = tree.ray_cast(origin, direction, reach)
                if hit[0] is not None:
                    occlusion += 1 - hit[3] / reach
            points.append((x, y, height))
            value = min(limit, strength * 2 * occlusion / rays) if inside(x, y) else 0.0
            # Snap faint values to zero so the layer always feathers out completely.
            alphas.append(value if value >= 0.035 else 0.0)

    used, faces = {}, []
    for row in range(count):
        for column in range(count):
            a = row * (count + 1) + column
            quad = (a, a + 1, a + count + 2, a + count + 1)
            if max(alphas[index] for index in quad) < 0.035:
                continue
            faces.append(tuple(used.setdefault(index, len(used)) for index in quad))
    order = sorted(used, key=used.get)
    part = MeshPart(model, AO_EFFECT)
    gradient_surface(part, mat, [points[index] for index in order], faces, "#5A4636",
                     [alphas[index] for index in order])


def carton(part, base, size, board, tape, ink):
    """Append a closed carton and thin geometry for the tape and barcode."""
    x, y, z = base
    width, depth, height = size
    part.box((x, y, z + height / 2), size, board)
    offset = 0.0007
    left, right = x - width * 0.09, x + width * 0.09
    front, back, top = y - depth / 2, y + depth / 2, z + height
    fold = top - height * 0.24
    part.add([(left, front, top + offset), (right, front, top + offset),
              (right, back, top + offset), (left, back, top + offset),
              (left, front - offset, fold), (right, front - offset, fold),
              (left, back + offset, fold), (right, back + offset, fold)],
             [(0, 1, 2, 3), (4, 5, 1, 0), (7, 6, 3, 2)], tape)

    def label(horizontal, dimension, place):
        half = min(dimension * 0.15, 0.052)
        bottom = z + height * 0.12
        tall = min(height * 0.24, half * 1.35)

        def block(start, end, low, high, relief, paint):
            part.add([place(u, v, relief) for u, v in
                      ((start, low), (end, low), (end, high), (start, high))],
                     [(0, 1, 2, 3)], paint)

        block(horizontal - half, horizontal + half, bottom, bottom + tall, offset, tape)
        for start, end in ((0.12, 0.17), (0.22, 0.34), (0.39, 0.44),
                           (0.52, 0.61), (0.68, 0.80), (0.85, 0.90)):
            block(horizontal + (2 * start - 1) * half, horizontal + (2 * end - 1) * half,
                  bottom + tall * 0.15, bottom + tall * 0.85, offset * 2, ink)

    label(x + width * 0.23, width, lambda u, v, relief: (u, front - relief, v))
    label(y - depth * 0.23, depth, lambda u, v, relief: (x + width / 2 + relief, u, v))


def area_light(collection, name, location, target, power, size, color):
    lamp = bpy.data.lights.new(name, "AREA")
    lamp.energy = power
    lamp.size = size
    lamp.color = linear_color(color)
    if hasattr(lamp, "use_shadow_jitter"):
        lamp.use_shadow_jitter = True
    obj = bpy.data.objects.new(name, lamp)
    collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    return obj


def studio(scene, collection, model, direction, frame):
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1536
    scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = -0.45
    scene.world = bpy.data.worlds.new("Commerce Hub Studio")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes.get("Background").inputs["Color"].default_value = (
        *linear_color("#FFEBDA"), 1)
    scene.world.node_tree.nodes.get("Background").inputs["Strength"].default_value = 0.22
    if hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 64

    cream = bpy.data.materials.new("Cream Backdrop")
    cream.use_nodes = True
    nodes = cream.node_tree.nodes
    nodes.remove(nodes.get("Principled BSDF"))
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (*linear_color(PALETTE["Cream Backdrop"]), 1)
    emission.inputs["Strength"].default_value = 2 ** -scene.view_settings.exposure
    cream.node_tree.links.new(emission.outputs[0], nodes.get("Material Output").inputs["Surface"])
    backdrop = MeshPart(collection, "Studio_Backdrop")
    backdrop.add([(-100, -100, -0.006), (100, -100, -0.006),
                  (100, 100, -0.006), (-100, 100, -0.006)], [(0, 1, 2, 3)], cream)
    backdrop.finish()

    area_light(collection, "Studio_Key", (-3.8, -3.3, 7.4), (0, 0, 0.6),
               1120, 4.0, "#FFF2DE")
    area_light(collection, "Studio_Fill", (4.5, -2.3, 4.6), (0, 0, 1.0),
               245, 4.5, "#FFFAF2")
    area_light(collection, "Studio_Rim", (0.0, 5.2, 6.8), (0, 0, 0.5),
               510, 4.0, "#FFF7EA")
    area_light(collection, "Studio_Front_Bounce", (-3.2, -4.5, 2.8), (0, 0, 1.0),
               70, 3.5, "#FFE6C6")

    camera_data = bpy.data.cameras.new("Studio_Camera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("Studio_Camera", camera_data)
    collection.objects.link(camera)
    scene.camera = camera
    forward = Vector(direction).normalized()
    rotation = (-forward).to_track_quat("-Z", "Y")
    right = rotation @ Vector((1, 0, 0))
    up = rotation @ Vector((0, 1, 0))
    # Frame the solid model without the fully transparent perimeter vertices.
    vertices = [vertex.co + obj.location for obj in model.objects
                if obj.name not in FLOOR_EFFECTS
                for vertex in obj.data.vertices]
    xs, ys = [v.dot(right) for v in vertices], [v.dot(up) for v in vertices]
    aspect = scene.render.resolution_x / scene.render.resolution_y
    left, top, right_edge, bottom = frame
    scale = max((max(xs) - min(xs)) / (right_edge - left),
                aspect * (max(ys) - min(ys)) / (bottom - top))
    center_x = (max(xs) + min(xs)) / 2 - ((left + right_edge) / 2 - 0.5) * scale
    center_y = (max(ys) + min(ys)) / 2 + ((top + bottom) / 2 - 0.5) * scale / aspect
    camera.location = right * center_x + up * center_y + forward * 13.5
    camera.rotation_euler = rotation.to_euler()
    camera_data.ortho_scale = scale


def fog_glow(scene):
    if hasattr(scene, "compositing_node_group"):
        tree = bpy.data.node_groups.new("Commerce Glow", "CompositorNodeTree")
        scene.compositing_node_group = tree
        tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        output = tree.nodes.new("NodeGroupOutput")
    else:
        scene.use_nodes = True
        tree = scene.node_tree
        tree.nodes.clear()
        output = tree.nodes.new("CompositorNodeComposite")
    layers = tree.nodes.new("CompositorNodeRLayers")
    layers.scene = scene
    glow = tree.nodes.new("CompositorNodeGlare")
    # Blender 5 exposes the glare mode and quality as menu sockets, not node properties.
    if hasattr(glow, "glare_type"):
        glow.glare_type = "FOG_GLOW"
        glow.quality = "HIGH"
    else:
        glow.inputs["Type"].default_value = "Fog Glow"
        glow.inputs["Quality"].default_value = "High"
    for name, value in {"Threshold": 1.40, "Strength": 0.48, "Size": 0.30}.items():
        if name in glow.inputs:
            glow.inputs[name].default_value = value
    tree.links.new(layers.outputs["Image"], glow.inputs["Image"])
    tree.links.new(glow.outputs["Image"], output.inputs["Image"])


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_vertex_alpha(node_name, primitive, document, payload):
    attributes = primitive["attributes"]
    if "COLOR_0" not in attributes:
        raise ValueError(f"{node_name} lost COLOR_0")
    accessors = document["accessors"]
    color = accessors[attributes["COLOR_0"]]
    component = {5121: "B", 5123: "H", 5126: "f"}.get(color["componentType"])
    if (color["type"] != "VEC4" or component is None or "sparse" in color
            or (component != "f" and not color.get("normalized", False))
            or color["count"] != accessors[attributes["POSITION"]]["count"]):
        raise ValueError(f"{node_name} needs one RGBA COLOR_0 value per vertex")
    view = document["bufferViews"][color["bufferView"]]
    unpacker = struct.Struct("<" + component)
    stride = view.get("byteStride", 4 * unpacker.size)
    start = view.get("byteOffset", 0) + color.get("byteOffset", 0) + 3 * unpacker.size
    alphas = {unpacker.unpack_from(payload, start + i * stride)[0]
              for i in range(color["count"])}
    maximum = {"B": 255, "H": 65535, "f": 1}[component]
    if (len(alphas) < 3 or 0 not in alphas or not all(0 <= a <= maximum for a in alphas)
            or not any(0 < a < maximum for a in alphas)):
        raise ValueError(f"{node_name} lost its feathered vertex alpha gradient")


def inspect_glb(path, part_names, limits, effect_names):
    blob = path.read_bytes()
    magic, version, length, chunk_length, chunk_type = struct.unpack_from("<4sIIII", blob)
    if (magic, version, length, chunk_type) != (b"glTF", 2, len(blob), 0x4E4F534A):
        raise ValueError("Invalid GLB header")
    json_end = 20 + chunk_length
    payload_length, payload_type = struct.unpack_from("<II", blob, json_end)
    if payload_type != 0x004E4942 or json_end + 8 + payload_length != len(blob):
        raise ValueError("Invalid GLB binary chunk")
    document = json.loads(blob[20:json_end])
    buffers = document["buffers"]
    if len(buffers) != 1 or not 0 <= payload_length - buffers[0]["byteLength"] <= 3:
        raise ValueError("GLB binary buffer length does not match its manifest")
    meshes = document["meshes"]
    nodes = document["nodes"]
    primitives = [primitive for mesh in meshes for primitive in mesh["primitives"]]
    accessors = document["accessors"]
    gltf_materials = document["materials"]
    extensions = document.get("extensionsUsed", [])
    if len(document["scenes"]) != 1 or sorted(n["name"] for n in nodes) != sorted(part_names):
        raise ValueError("GLB scene or named model-node inventory is incorrect")
    if any(key in document for key in ("cameras", "animations", "images", "textures")):
        raise ValueError("Unexpected camera, animation, or image in GLB")
    if "KHR_lights_punctual" in extensions:
        raise ValueError("Unexpected lights in GLB")
    if "KHR_materials_unlit" not in extensions:
        raise ValueError("GLB lost KHR_materials_unlit")
    if set(effect_names) - {node["name"] for node in nodes}:
        raise ValueError("GLB is missing a required gradient effect")
    total_triangles = 0
    for primitive in primitives:
        if primitive.get("mode", 4) != 4 or "NORMAL" not in primitive["attributes"]:
            raise ValueError("Expected indexed triangles with normals")
        index_count = accessors[primitive["indices"]]["count"]
        if index_count % 3:
            raise ValueError("GLB primitive has an incomplete triangle")
        total_triangles += index_count // 3

    bounds = [[], [], []]
    payload = memoryview(blob)[json_end + 8:]
    for node in nodes:
        translation = node.get("translation", (0, 0, 0))
        if any(key in node for key in ("matrix", "rotation", "scale", "children")):
            raise ValueError("Expected directly placed, translation-only model meshes")
        for primitive in meshes[node["mesh"]]["primitives"]:
            if node["name"] in effect_names:
                mat = gltf_materials[primitive["material"]]
                if (mat.get("alphaMode") != "BLEND"
                        or "KHR_materials_unlit" not in mat.get("extensions", {})):
                    raise ValueError(f"{node['name']} needs a blended unlit material")
                check_vertex_alpha(node["name"], primitive, document, payload)
            position = accessors[primitive["attributes"]["POSITION"]]
            for i, axis in enumerate(bounds):
                axis.extend((position["min"][i] + translation[i],
                             position["max"][i] + translation[i]))
    if abs(min(bounds[1])) > 0.00001:
        raise ValueError("Exported model base is not on the glTF ground plane")
    metrics = {
        "triangles": total_triangles,
        "bytes": len(blob),
        "primitives": len(primitives),
        "materials": len(gltf_materials),
        "material_names": [mat["name"] for mat in gltf_materials],
        "nodes": sorted(part_names),
        "bounds_gltf_y_up_m": {
            "min": [round(min(axis), 6) for axis in bounds],
            "max": [round(max(axis), 6) for axis in bounds],
        },
        "extensions_used": extensions,
        "validator_notes": {
            "external_resources": [b["uri"] for b in buffers if "uri" in b],
            "blended_materials": [m["name"] for m in gltf_materials
                                  if m.get("alphaMode") == "BLEND"],
            "emissive_materials": [m["name"] for m in gltf_materials
                                   if any(m.get("emissiveFactor", []))],
            "unlit_vertex_alpha_nodes": sorted(effect_names),
            "khronos_validator": "not run by the generator",
        },
        "hard_limits": limits,
    }
    for key, limit in limits.items():
        if metrics[key] > limit:
            raise ValueError(f"GLB {key}: {metrics[key]} exceeds {limit}")
    if metrics["validator_notes"]["external_resources"]:
        raise ValueError("GLB depends on externally referenced buffers")
    return metrics


def png_size(path):
    with path.open("rb") as image:
        header = image.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError("Expected a PNG render")
    return struct.unpack(">II", header[16:24])


def build(module, model_builder, limits, direction, frame, review_features, *,
          extra_effects=(), emissive_materials=(), blended_materials=(),
          required_parts=(), studio_lights=()):
    """Build in a disposable scene and save only that scene's data blocks."""
    outputs = {
        extension: MODULE_DIR / folder / f"{module}.{extension}"
        for extension, folder in (("blend", "blend"), ("glb", "exports"),
                                  ("png", "renders"), ("json", "reports"))
    }
    if any(path.parent.is_symlink() for path in outputs.values()):
        raise FileExistsError("Output folders must be local to the module directory")
    saved = bpy.data.filepath
    if saved and Path(saved).resolve() == outputs["blend"].resolve():
        raise FileExistsError("The target Blender file is open in this session")
    existing = [ext for ext, path in outputs.items() if path.exists() or path.is_symlink()]
    if existing:
        # Renders are not tracked, so a fresh checkout legitimately lacks the PNG.
        if set(outputs) - set(existing) - {"png"} or any(p.is_symlink() for p in outputs.values()):
            raise FileExistsError("Refusing to replace unrecognized module outputs")
        previous = json.loads(outputs["json"].read_text())
        for ext in (e for e in ("blend", "glb", "png") if e in existing):
            if sha256(outputs[ext]) != previous.get("sha256", {}).get(ext):
                raise FileExistsError(f"Refusing to replace modified file: {outputs[ext]}")

    # Object names are global in Blender: an open module file would force suffixes onto the export names.
    if "Plinth_Outer" in bpy.data.objects:
        raise RuntimeError("Run the build in a Blender session without another Commerce Hub module open")

    # Keep the live scene and its saved file separate from this build.
    inventories = (bpy.data.scenes, bpy.data.collections, bpy.data.objects, bpy.data.meshes,
                   bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights,
                   bpy.data.worlds, bpy.data.node_groups)
    before = {block.as_pointer() for inventory in inventories for block in inventory}
    window = bpy.context.window
    original_scene = window.scene
    scene = bpy.data.scenes.new(f"Commerce Hub – {module.title()}")
    try:
        window.scene = scene
        scene.unit_settings.system = "METRIC"
        scene.unit_settings.scale_length = 1.0
        model = bpy.data.collections.new(f"{module.title()} Model")
        presentation = bpy.data.collections.new(f"{module.title()} Studio")
        scene.collection.children.link(model)
        scene.collection.children.link(presentation)
        plinth(model)
        effects = gradient_material()
        floor_effects(model, effects)
        model_builder(model, effects)
        bake_ambient_occlusion(model, effects)
        limits = {key: value + AO_BUDGET.get(key, 0) for key, value in limits.items()}
        part_names = [obj.name for obj in model.objects]
        missing_parts = set(required_parts) - set(part_names)
        if missing_parts:
            raise ValueError(f"Missing model parts: {', '.join(sorted(missing_parts))}")
        studio(scene, presentation, model, direction, frame)
        for light in studio_lights:
            area_light(presentation, *light)
        fog_glow(scene)

        with tempfile.TemporaryDirectory(prefix=f".{module}-", dir=MODULE_DIR) as temp:
            staged = {ext: Path(temp) / path.name for ext, path in outputs.items()}
            bpy.context.view_layer.update()
            for obj in model.objects:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = model.objects["Plinth_Outer"]
            status = bpy.ops.export_scene.gltf(
                filepath=str(staged["glb"]), export_format="GLB", use_selection=True,
                use_active_scene=True, export_cameras=False, export_lights=False,
                export_animations=False, export_skins=False, export_yup=True,
                export_texcoords=False, export_normals=True,
                export_materials="EXPORT", export_image_format="NONE",
                export_vertex_color="MATERIAL", export_all_vertex_colors=False,
                export_draco_mesh_compression_enable=False,
            )
            if status != {"FINISHED"}:
                raise RuntimeError(f"glTF export returned {status}")
            sample_effects = {"bags": ("Fx_RingHalo",), "shop": ("Fx_PendantHalo",)}
            effect_names = (*FLOOR_EFFECTS, AO_EFFECT, *sample_effects.get(module, ()), *extra_effects)
            metrics = inspect_glb(staged["glb"], part_names, limits, effect_names)
            notes = metrics["validator_notes"]
            warm_surfaces = {
                "bags": ("Warm Light Ring",),
                "shop": ("Warm Ivory Tile", "Warm Tile Joints", "Honey Maple", "Warm Pendant Glass"),
            }.get(module, ()) + emissive_materials
            if not set(warm_surfaces).issubset(notes["emissive_materials"]):
                raise ValueError("GLB lost the emission from a warm surface")
            transparent_surfaces = (("Shop Glass",) if module == "shop" else ()) + blended_materials
            missing_alpha = set(transparent_surfaces) - set(notes["blended_materials"])
            if missing_alpha:
                raise ValueError(f"GLB lost alpha blending: {', '.join(sorted(missing_alpha))}")

            scene.render.filepath = str(staged["png"])
            status = bpy.ops.render.render(write_still=True, scene=scene.name)
            if status != {"FINISHED"} or png_size(staged["png"]) != (1536, 1024):
                raise RuntimeError("The 1536 × 1024 EEVEE render did not complete")
            scene.render.filepath = f"//../renders/{module}.png"
            bpy.data.libraries.write(str(staged["blend"]), {scene}, path_remap="NONE",
                                     fake_user=True, compress=True)

            report = {
                "module": module,
                "blender_version": bpy.app.version_string,
                "units": "metres, Blender +Z up, front -Y, origin at plinth base centre",
                "render": {
                    "engine": scene.render.engine,
                    "dimensions_px": [1536, 1024],
                    "projection": scene.camera.data.type,
                    "orthographic_width_m": scene.camera.data.ortho_scale,
                    "camera_location_m": list(scene.camera.location),
                    "camera_rotation_rad": list(scene.camera.rotation_euler),
                    "view_transform": scene.view_settings.view_transform,
                    "look": scene.view_settings.look,
                },
                **metrics,
                "sha256": {
                    **{ext: sha256(staged[ext]) for ext in ("blend", "glb", "png")},
                    "source": {name: sha256(MODULE_DIR / "source" / name)
                               for name in ("common.py", f"build_{module}.py")},
                    "anchors": {name: sha256(MODULE_DIR / "reference" / name) for name in
                                ("anchor-scene.webp", f"anchor-{module}.webp")
                                if (MODULE_DIR / "reference" / name).is_file()},
                },
                "visual_review": {
                    "status": "not reviewed",
                    "criteria": review_features,
                },
            }
            staged["json"].write_text(json.dumps(report, indent=2) + "\n")
            for ext, path in outputs.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                os.replace(staged[ext], path)
            return report
    finally:
        window.scene = original_scene
        created = [block for inventory in inventories for block in inventory
                   if block.as_pointer() not in before]
        if created:
            bpy.data.batch_remove(ids=created)
