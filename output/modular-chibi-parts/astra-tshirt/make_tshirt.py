"""Build the Astra short-sleeve module from the adjacent read-only master."""
import json
import math
import struct
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform


HERE = Path(__file__).resolve().parent
MASTER = HERE.parent / "master" / "GJH_Chibi_Master_rigged.blend"
NAME = "top_tshirt_v1"
EASE = 0.008
THICKNESS = 0.004
MIN_CLEARANCE = 0.002
FOLD_SLOPE_WIDTH = 0.0018
COLOR = (0.075, 0.42, 0.38, 1.0)  # Linear RGB, sea-glass green.


def activate(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def welded_body(body):
    mesh = bmesh.new()
    mesh.from_mesh(body.data)
    mesh.transform(body.matrix_world)
    # The master's UV islands duplicate positions at their borders.
    bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=1.0e-7)
    mesh.normal_update()
    return mesh


def clip_polygon(polygon, field, level):
    """Split a convex source face on a garment pattern line, retaining both sides."""
    low, high = [], []
    values = [field(p) - level for p in polygon]
    for i, (p, value) in enumerate(zip(polygon, values)):
        previous = polygon[i - 1]
        old = values[i - 1]
        if value * old < 0:
            # Bisect the curved neckline too. Canonical edge ordering keeps
            # independently clipped neighbours coincident.
            a, b = (previous, p) if old < 0 else (p, previous)
            for _ in range(21):
                mid = (a + b) * 0.5
                if field(mid) < level:
                    a = mid
                else:
                    b = mid
            low.append(mid)
            high.append(mid)
        if value <= 0:
            low.append(p)
        if value >= 0:
            high.append(p)
    return low, high


def pattern(rig):
    def joint(name, fraction=0.0):
        bone = rig.data.bones["mixamorig:" + name]
        return rig.matrix_world @ bone.head_local.lerp(bone.tail_local, fraction)

    left = joint("LeftArm", 0.4).x
    right = joint("RightArm", 0.4).x
    hips = joint("Hips").z
    neck = joint("Neck")
    center = 0.5 * (left + right)

    def neckline(p):
        return (neck.z - 0.014 + 0.026 * ((p.x - center) / 0.065) ** 2
                + 0.095 * (p.y - neck.y) - p.z)

    # Below the armpits the sleeve cutting planes flare out past the torso.
    return [(lambda p: p.z - hips, 0.010),
            (lambda p: left - p.x + max(0.49 - p.z, 0.0), 0.006),
            (lambda p: p.x - right + max(0.49 - p.z, 0.0), 0.006),
            (neckline, 0.005)]


def drape_waist(mesh, skin):
    """Fair the copied waist faces and let the cloth bridge the sculpted waistband."""
    center = Vector((0.0007, -0.019, 0))
    low, high = 0.36, 0.49
    ring_count = 64
    angles = [i * math.tau / ring_count for i in range(ring_count)]
    directions = [Vector((math.cos(a), math.sin(a), 0)) for a in angles]

    def radius(direction, z):
        origin = center + direction * 0.25
        origin.z = z
        point, _, _, _ = skin.ray_cast(origin, -direction)
        if point is None:
            raise ValueError("Missing torso cross-section")
        return (point - center).dot(direction)

    # Use the shallowest straight taper that clears the waist at every sampled
    # height. A straight taper lets the hem hang past the sculpted waistband.
    sample_heights = [i / 24 for i in range(22)]
    bottom_radii, top_radii = [], []
    for direction in directions:
        top = radius(direction, high) + EASE
        bottom = max(top + (radius(direction, low + t * (high - low)) + EASE - top)
                     / (1.0 - t) for t in sample_heights)
        top_radii.append(top)
        bottom_radii.append(bottom)

    # Relax the copied triangulation over the old waistband's undercuts before
    # laying those faces onto the cloth. Leave the upper chest anchored.
    belt = [v for v in mesh.verts if low - 0.01 < v.co.z < high]
    for _ in range(24):
        positions = []
        for v in belt:
            mean = sum((e.other_vert(v).co for e in v.link_edges), Vector()) / len(v.link_edges)
            positions.append(v.co.lerp(mean, 0.45))
        for v, position in zip(belt, positions):
            v.co = position

    for v in mesh.verts:
        z = v.co.z
        if z >= high:
            continue
        delta = v.co - center
        angle = (math.atan2(delta.y, delta.x) % math.tau) * ring_count / math.tau
        i = int(angle) % ring_count
        j = (i + 1) % ring_count
        frac = angle % 1.0
        bottom = (1 - frac) * bottom_radii[i] + frac * bottom_radii[j]
        top = (1 - frac) * top_radii[i] + frac * top_radii[j]
        t = min(1.0, max(0.0, (z - low) / (high - low)))
        r = (1 - t) * bottom + t * top
        radial = Vector((delta.x, delta.y, 0)).normalized()
        v.co = Vector((center.x + r * radial.x, center.y + r * radial.y, z))


def fit_body_copy(body):
    mesh = welded_body(body)
    skin = BVHTree.FromBMesh(mesh)
    # Capture whole-body normals before discarding any neighbouring faces.
    normal = mesh.verts.layers.float_vector.new("fit_normal")
    for v in mesh.verts:
        v[normal] = v.normal
    unused = [f for f in mesh.faces if
              min(v.co.z for v in f.verts) > 0.608 or
              max(v.co.z for v in f.verts) < 0.35 or
              min(abs(v.co.x) for v in f.verts) > 0.16]
    bmesh.ops.delete(mesh, geom=unused, context="FACES")
    # Refine the long torso triangles while preserving the finer native topology.
    long_edges = [e for e in mesh.edges if e.calc_length() > 0.040]
    bmesh.ops.subdivide_edges(mesh, edges=long_edges, cuts=1, use_grid_fill=True)
    bmesh.ops.triangulate(mesh, faces=list(mesh.faces))
    for v in mesh.verts:
        v.co += EASE * Vector(v[normal]).normalized()

    # Relax the inward corner where the upper-arm and torso offsets meet.
    # Cloth bridges this crease when the character holds its arms out.
    pit = [(v, math.exp(-((abs(v.co.x) - 0.096) / 0.027)**2
                        - ((v.co.z - 0.520) / 0.022)**2))
           for v in mesh.verts if 0.47 < v.co.z < 0.575]
    for _ in range(8):
        relaxed = []
        for v, factor in pit:
            mean = sum((e.other_vert(v).co for e in v.link_edges), Vector()) / len(v.link_edges)
            position = v.co.lerp(mean, 0.55 * factor)
            near, n, _, _ = skin.find_nearest(position)
            gap = (position - near).dot(n)
            clearance = EASE + 0.0025 * factor
            if gap < clearance:
                position += (clearance - gap) * n
            relaxed.append(position)
        for (v, _), position in zip(pit, relaxed):
            v.co = position
    drape_waist(mesh, skin)
    mesh.normal_update()
    return mesh


def cut_fabric(body, rig):
    mesh = fit_body_copy(body)
    lines = pattern(rig)
    coords, faces, directions, indices = [], [], [], {}

    def index(p, corners):
        key = tuple(round(k, 7) for k in p)
        if key not in indices:
            indices[key] = len(coords)
            coords.append(p.copy())
            a, b, c = corners
            direction = barycentric_transform(p, a.co, b.co, c.co,
                                              a.normal, b.normal, c.normal)
            directions.append(direction.normalized())
        return indices[key]

    for face in mesh.faces:
        polygon = [v.co.copy() for v in face.verts]
        for field, _ in lines:
            _, polygon = clip_polygon(polygon, field, 0.0)
            if len(polygon) < 3:
                break
        if len(polygon) < 3:
            continue
        # Two loops form a shallow folded hem, cuff or neck binding in the
        # fabric itself. They share the same material as the body of the tee.
        patches = [polygon]
        for field, width in lines:
            for level in (width, width + FOLD_SLOPE_WIDTH):
                patches = [piece for patch in patches
                           for piece in clip_polygon(patch, field, level)
                           if len(piece) >= 3]
        for patch in patches:
            face_indices = list(dict.fromkeys(index(p, face.verts) for p in patch))
            if len(face_indices) >= 3:
                faces.append(face_indices)
    mesh.free()

    data = bpy.data.meshes.new(NAME)
    data.from_pydata(coords, [], faces)
    data.update()
    layer = data.attributes.new("fabric_direction", "FLOAT_VECTOR", "POINT")
    for item, direction in zip(layer.data, directions):
        item.vector = direction
    mesh = bmesh.new()
    mesh.from_mesh(data)
    bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=0.00004)
    # The chibi's chin overhangs the neck and can enter the rough cutting box.
    seed = min(mesh.verts, key=lambda v: v.co.z)
    connected, stack = {seed}, [seed]
    while stack:
        for edge in stack.pop().link_edges:
            for v in edge.verts:
                if v not in connected:
                    connected.add(v)
                    stack.append(v)
    bmesh.ops.delete(mesh, geom=[v for v in mesh.verts if v not in connected],
                     context="VERTS")
    direction = mesh.verts.layers.float_vector["fabric_direction"]
    for v in mesh.verts:
        relief = max(min(1.0, max(0.0, (width + FOLD_SLOPE_WIDTH - field(v.co)) / FOLD_SLOPE_WIDTH))
                     for field, width in lines)
        v.co += 0.0008 * relief * Vector(v[direction])
    bmesh.ops.triangulate(mesh, faces=list(mesh.faces))
    for edge in mesh.edges:
        if edge.is_boundary:
            edge.smooth = False
    check_openings(mesh)
    mesh.to_mesh(data)
    mesh.free()
    shirt = bpy.data.objects.new(NAME, data)
    bpy.context.collection.objects.link(shirt)
    for face in data.polygons:
        face.use_smooth = True
    return shirt


def check_openings(mesh):
    boundary = {e for e in mesh.edges if e.is_boundary}
    if any(not e.is_manifold and e not in boundary for e in mesh.edges):
        raise ValueError("Non-manifold fabric surface")
    count = 0
    while boundary:
        count += 1
        stack = [boundary.pop()]
        while stack:
            for v in stack.pop().verts:
                edges = [e for e in v.link_edges if e.is_boundary]
                if len(edges) != 2:
                    raise ValueError("Broken garment opening")
                for e in edges:
                    if e in boundary:
                        boundary.remove(e)
                        stack.append(e)
    if count != 4:
        raise ValueError(f"Expected neck, two cuffs and hem, found {count} openings")


def add_thickness(shirt):
    activate(shirt)
    # Solidify supplies both fabric surfaces and all four rims. Transport its
    # thickness along the uncut cloth normals; clipped slivers and folded hems
    # would otherwise turn rim vertices sideways and pinch the inner surface.
    direction = shirt.data.attributes["fabric_direction"]
    midsurface = [v.co.copy() for v in shirt.data.vertices]
    basis = [v.normal.copy() for v in shirt.data.vertices]
    normals = [v.vector.copy() for v in direction.data]
    original = shirt.data.attributes.new("fabric_vertex", "INT", "POINT")
    for i, item in enumerate(original.data):
        item.value = i
    solid = shirt.modifiers.new("Fabric and finished edges", "SOLIDIFY")
    solid.thickness = THICKNESS
    solid.offset = 0.0
    bpy.ops.object.modifier_apply(modifier=solid.name)

    original = shirt.data.attributes["fabric_vertex"]
    for v, item in zip(shirt.data.vertices, original.data):
        i = item.value
        sign = 1 if (v.co - midsurface[i]).dot(basis[i]) > 0 else -1
        v.co = midsurface[i] + sign * THICKNESS * 0.5 * normals[i]
    shirt.data.attributes.remove(original)
    shirt.data.attributes.remove(shirt.data.attributes["fabric_direction"])
    shirt.data.update()


def bind_shirt(shirt, body, rig):
    for group in body.vertex_groups:
        shirt.vertex_groups.new(name=group.name)
    transfer = shirt.modifiers.new("Interpolate body skin", "DATA_TRANSFER")
    transfer.object = body
    transfer.use_vert_data = True
    transfer.data_types_verts = {"VGROUP_WEIGHTS"}
    transfer.vert_mapping = "POLYINTERP_NEAREST"
    transfer.layers_vgroup_select_src = "ALL"
    transfer.layers_vgroup_select_dst = "NAME"
    bpy.ops.object.modifier_apply(modifier=transfer.name)
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
    for v in shirt.data.vertices:
        weights = [g.weight for g in v.groups if g.weight > 0]
        if not 1 <= len(weights) <= 4 or abs(sum(weights) - 1) > 1e-5:
            raise ValueError(f"Invalid weights on vertex {v.index}: {weights}")

    shirt.parent = rig
    shirt.matrix_parent_inverse = rig.matrix_world.inverted()
    skin = shirt.modifiers.new("Armature", "ARMATURE")
    skin.object = rig


def add_material(shirt):
    material = bpy.data.materials.new("Sea Glass Cotton")
    material.diffuse_color = COLOR
    if not material.node_tree:
        material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = COLOR
    shader.inputs["Roughness"].default_value = 0.9
    shirt.data.materials.append(material)


def surface(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj = obj.evaluated_get(depsgraph)
    mesh = obj.data
    mesh.calc_loop_triangles()
    vertices = [obj.matrix_world @ v.co for v in mesh.vertices]
    triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    return vertices, triangles, BVHTree.FromPolygons(vertices, triangles, all_triangles=True)


def check_fit(shirt, body):
    bpy.context.view_layer.update()
    _, _, skin = surface(body)
    vertices, faces, fabric = surface(shirt)
    distances = []
    for p in vertices:
        q, normal, _, distance = skin.find_nearest(p)
        # Unsigned proximity also passes inside the body. Check sidedness too.
        distances.append(distance if (p - q).dot(normal) >= 0 else -distance)
    minimum = min(distances)
    hits = fabric.overlap(skin)
    print(f"Triangles: {len(faces)} | evaluated garment vertices: {len(vertices)}")
    print(f"T-pose minimum signed clearance: {minimum:.8f} | "
          f"required: {MIN_CLEARANCE:.3f} | intersecting triangle pairs: {len(hits)}")
    crossing = [(i, j) for i, j in fabric.overlap(fabric)
                if i < j and set(faces[i]).isdisjoint(faces[j])]
    if crossing:
        raise ValueError(f"Cloth intersects itself in {len(crossing)} triangle pairs")
    if not 1500 <= len(faces) <= 4000:
        raise ValueError("Triangle budget failed")
    if minimum < MIN_CLEARANCE or hits:
        raise ValueError("Poke-through check failed")
    print("Poke-through check: PASS")
    return len(faces)


def check_export(path, triangle_count):
    with path.open("rb") as stream:
        magic, version, length, size, kind = struct.unpack("<4s4I", stream.read(20))
        if (magic, version, kind, length) != (b"glTF", 2, 0x4E4F534A, path.stat().st_size):
            raise ValueError("Invalid GLB header")
        gltf = json.loads(stream.read(size))
    (mesh,) = gltf["meshes"]
    (skin,) = gltf["skins"]
    (node,) = [n for n in gltf["nodes"] if "mesh" in n]
    if (node["name"] != NAME or node["skin"] != 0 or gltf.get("animations")
            or len(skin["joints"]) != 65):
        raise ValueError("Unexpected GLB scene or skeleton")
    count = 0
    for part in mesh["primitives"]:
        if not {"WEIGHTS_0", "JOINTS_0"} <= part["attributes"].keys():
            raise ValueError("Missing GLB skin attributes")
        count += gltf["accessors"][part["indices"]]["count"] // 3
    if count != triangle_count:
        raise ValueError(f"GLB contains {count} triangles, expected {triangle_count}")
    print(f"GLB verified: {node['name']}, {count} triangles, 65 joints, no animation")


def main():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False, use_scripts=False)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.context.preferences.filepaths.file_preview_type = "NONE"
    body = bpy.data.objects["Base_Body"]
    rig = bpy.data.objects["Armature"]
    shirt = cut_fabric(body, rig)
    add_thickness(shirt)
    bind_shirt(shirt, body, rig)
    add_material(shirt)
    triangle_count = check_fit(shirt, body)

    activate(shirt)
    rig.select_set(True)
    path = HERE / (NAME + ".glb")
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True,
                              export_animations=False, export_skins=True, export_yup=True)
    check_export(path, triangle_count)
    # The reference body has served its fitting and verification purposes.
    # Only the in-memory scene is changed; save exclusively to the module path.
    bpy.data.objects.remove(body, do_unlink=True)
    activate(shirt)
    rig.hide_set(True)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                view = area.spaces.active
                view.shading.color_type = "MATERIAL"
                view.overlay.show_overlays = False
                view.region_3d.view_distance = 0.54
                view.region_3d.view_location = (0.0, -0.01, 0.49)
                view.region_3d.view_rotation = Vector((-0.22, 1.0, -0.22)).to_track_quat("-Z", "Y")
                view.region_3d.view_perspective = "ORTHO"
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / (NAME + ".blend")), check_existing=False)


if __name__ == "__main__":
    main()
