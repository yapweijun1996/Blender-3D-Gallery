"""Build the selected jeans in Blender 5.1.

Use -- --verify, --checkers, or --renders for QA. Use -- --passes 12 to
retry the experimental full-motion offset bake starting from the selected fit.
"""
from contextlib import redirect_stdout
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
PARTS = HERE.parent.parent
MASTER = PARTS / "master/GJH_Chibi_Master_rigged.blend"
MOTION = PARTS.parent.parent / "models/tripo-chibi-motion/motion.glb"
SOURCE = HERE / "source_studio_retopo.glb"
OUTPUT = HERE
GLB = OUTPUT / "jeans_v1.glb"
BLEND = OUTPUT / "jeans_v1.blend"
CLIPS = ("walk", "run", "wave", "jump", "idle", "nod", "dance")
MARGIN = .00205
CAP = .030
MAX_TRIANGLES = 6000


def write_report(name, data):
    (OUTPUT / name).write_text(json.dumps(data, indent=2) + "\n")


def import_garment(path, merge=True):
    scene = bpy.context.scene
    before = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path), merge_vertices=merge)
    created = [o for o in scene.objects if o not in before]
    garment, = [o for o in bpy.context.selected_objects if o in created and o.type == "MESH"]
    world = garment.matrix_world.copy()
    garment.parent = None
    garment.data.transform(world)
    garment.matrix_world.identity()
    for obj in created:
        if obj != garment:
            bpy.data.objects.remove(obj, do_unlink=True)
    return garment


def setup(path):
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body = [scene.objects[name] for name in ("Armature", "Base_Body")]
    body.hide_set(False)
    garment = import_garment(path, merge=path == SOURCE)
    garment.modifiers.clear()
    modifier = garment.modifiers.new("Master Skin", "ARMATURE")
    modifier.object = arm
    garment.parent = arm
    bpy.ops.import_scene.gltf(filepath=str(MOTION))
    for obj in scene.objects:
        if obj not in (arm, body, garment):
            obj.hide_render = True
            obj.hide_viewport = True
    for name in CLIPS:
        assert bpy.data.actions.get(name) and len(bpy.data.actions[name].slots)
    arm.animation_data_create()
    set_pose(scene, arm, "rest", 1)
    return scene, arm, body, garment


def set_pose(scene, arm, clip, frame):
    action = None if clip == "rest" else bpy.data.actions[clip]
    animation = arm.animation_data
    if animation.action != action:
        animation.action = action
        if action:
            animation.action_slot = action.slots[0]
        else:
            for bone in arm.pose.bones:
                bone.matrix_basis.identity()
    scene.frame_set(math.floor(frame), subframe=frame % 1)
    bpy.context.view_layer.update()


def frames():
    yield "rest", 1.
    for clip in CLIPS:
        first, last = bpy.data.actions[clip].frame_range
        times = {first, last, *(f / 2 for f in range(math.ceil(2 * first), math.floor(2 * last) + 1))}
        times.update(int(first + (last - first) * k / 12) for k in range(12))
        times.update(range(int(first), int(last) + 1, 3))
        for frame in sorted(times):
            yield clip, frame


def mesh_arrays(mesh):
    coords = np.empty((len(mesh.vertices), 3), dtype=np.float32)
    mesh.vertices.foreach_get("co", coords.ravel())
    mesh.calc_loop_triangles()
    faces = np.empty((len(mesh.loop_triangles), 3), dtype=np.int32)
    mesh.loop_triangles.foreach_get("vertices", faces.ravel())
    return coords, faces


def evaluated_arrays(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        coords, faces = mesh_arrays(mesh)
        transform = np.asarray(evaluated.matrix_world)
        return coords @ transform[:3, :3].T + transform[:3, 3], faces
    finally:
        evaluated.to_mesh_clear()


def tree_from(coords, faces):
    return BVHTree.FromPolygons(coords.tolist(), faces.tolist(), all_triangles=True)


def cache_poses(scene, arm, body, garment=None):
    bones = tuple(arm.pose.bones)
    modes = tuple(b.rotation_mode for b in bones)
    inverse_bind = [bone.bone.matrix_local.inverted() for bone in bones]
    samples, matrices, garment_poses = [], [], []
    rest_vertices, rest_faces = mesh_arrays(body.data)
    body_panels = rest_vertices[rest_faces, 2].min(axis=1) < .475
    for clip, frame in frames():
        set_pose(scene, arm, clip, frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        points, faces = evaluated_arrays(body, depsgraph)
        full = tree_from(points, faces)
        if garment is None:
            own = full if clip == "rest" else tree_from(points, faces[body_panels])
            posed_panel = points[faces].min(axis=1)[:, 2] < np.asarray(bones[0].head)[2] + .13
            intruders = ~body_panels & posed_panel
            limbs = tree_from(points, faces[intruders]) if intruders.any() else None
        else:
            own, limbs = full, None
        samples.append((clip, frame, full, own, limbs))
        if garment is None:
            matrices.append(np.array([b.matrix @ inv for b, inv in zip(bones, inverse_bind)])[:, :3])
        else:
            garment_poses.append(evaluated_arrays(garment, depsgraph)[0])
    assert modes == tuple(b.rotation_mode for b in bones)
    print("Cached poses:", len(samples), flush=True)
    return samples, np.asarray(matrices if garment is None else garment_poses, dtype=np.float32)


def clean_source(garment):
    mesh = garment.data
    points, triangles = mesh_arrays(mesh)
    source = tree_from(points, triangles)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    hidden = []
    for face in bm.faces:
        p = face.calc_center_median()
        x, y, z = p
        if .11 < z < .755:
            continue
        if z <= .11:
            center = Vector((math.copysign(.144, x), -.020, z))
            minimum_radius, minimum_cosine, maximum_inset = .071, -.45, .020
        else:
            center = Vector((0, -.006, z))
            minimum_radius, minimum_cosine, maximum_inset = .104, -.45, .025
        radial = p - center
        radius = radial.length
        if radius < minimum_radius:
            hidden.append(face)
            continue
        radial.normalize()
        reach = .42
        if z <= .11 and radial.x * x < 0:
            reach = min(reach, abs(center.x / radial.x))
        outer, _, _, _ = source.ray_cast(center + reach * radial, -radial)
        inset = radius - (outer - center).length if outer else 0
        if -inset > maximum_inset or face.normal.dot(radial) < minimum_cosine:
            hidden.append(face)
    bmesh.ops.delete(bm, geom=hidden, context="FACES")
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
    bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=1e-7)
    islands = []
    pending = set(bm.faces)
    for seed in list(bm.faces):
        if seed not in pending:
            continue
        pending.remove(seed)
        island, stack = [seed], [seed]
        while stack:
            face = stack.pop()
            for edge in face.edges:
                for peer in edge.link_faces:
                    if peer in pending:
                        pending.remove(peer)
                        island.append(peer)
                        stack.append(peer)
        islands.append(island)
    exterior = max(islands, key=len)
    debris = [face for region in islands if region is not exterior and len(region) < 17 for face in region]
    bmesh.ops.delete(bm, geom=debris, context="FACES")
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) != 3])
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    print("Source faces:", len(triangles), "after hidden-face cleanup:", len(mesh.polygons),
          "removed hidden/debris:", len(hidden), len(debris), flush=True)


def adjacency(mesh):
    links = np.empty((len(mesh.edges), 2), dtype=np.int32)
    mesh.edges.foreach_get("vertices", links.ravel())
    src, dst = np.concatenate((links, links[:, ::-1])).T
    return src, dst, np.bincount(src, minlength=len(mesh.vertices)).clip(1)


def average(values, graph):
    src, dst, counts = graph
    sums = np.zeros_like(values)
    np.add.at(sums, src, values[dst])
    return sums / counts.reshape((-1,) + (1,) * (values.ndim - 1))


def nearest(tree, coords):
    find = tree.find_nearest
    positions = coords.tolist()
    hits = [find(p, .042) for p in positions]
    for i, hit in enumerate(hits):
        if hit[0] is None:
            hits[i] = find(positions[i])
    surface = np.asarray([h[0][:] for h in hits], dtype=np.float32)
    normals = np.asarray([h[1][:] for h in hits], dtype=np.float32)
    faces = np.asarray([h[2] for h in hits], dtype=np.int32)
    signed = np.einsum("vi,vi->v", coords - surface, normals)
    return signed, surface, normals, faces


def smoothstep(lo, hi, t):
    u = np.clip((t - lo) / (hi - lo), 0, 1)
    return u * u * (3 - 2 * u)


def align(points, rest_tree, graph):
    """Match cuff, knee, saddle and waistband heights without changing the UVs."""
    x, y, z = points.T
    p = points.copy()
    p[:, 2] = np.interp(z, [0, .055, .405, .672, .76, .87, .978],
                        [.070, .084, .205, .293, .350, .400, .423])
    p[:, 2] += .0045 * smoothstep(.83, .965, z) * smoothstep(.045, .13, y)
    p[:, 0] = x * np.interp(z, [0, .4, .64, .76, .90, .978],
                           [.565, .567, .558, .589, .575, .548]) + .001
    p[:, 1] = (y * np.interp(z, [0, .085, .46, .65, .76, .88, .978],
                             [.55, .51, .49, .52, .57, .59, .55])
               + np.interp(z, [0, .15, .5, .68, .78, .978], [.019, .019, .004, -.010, -.017, -.014]))
    centers = p.copy()
    centers[:, 0] = (np.sign(x) * np.interp(z, [0, .48, .69], [.080, .075, .070])
                     * (1 - smoothstep(.65, .76, z))) + .001
    centers[:, 1] = np.interp(z, [0, .18, .57, .76, .98], [.017, .014, -.004, -.017, -.017])
    radial = p - centers
    radial[:, 2] = 0
    directions = radial / np.linalg.norm(radial, axis=1).clip(1e-8)[:, None]
    medial = np.maximum(0, -np.sign(x) * directions[:, 0])
    target = (.008 - .0037 * medial + .003 * (1 - smoothstep(.04, .22, z))
              + .0017 * smoothstep(.72, .84, z))
    for i, (center, direction) in enumerate(zip(centers, directions)):
        # Across the saddle, a horizontal ray can exit through the opposite thigh.
        if .645 < z[i] < .756 and abs(x[i]) < .085:
            continue
        v = Vector(direction)
        start = Vector(center)
        if z[i] < .68:
            surface, normal, _, _ = rest_tree.ray_cast(start, v, .100)
        else:
            surface, normal, _, _ = rest_tree.ray_cast(start + .195 * v, -v)
        if surface is None or (surface - Vector(p[i])).length > .04:
            continue
        need = target[i] / max(.73, normal.dot(v)) - (Vector(p[i]) - surface).dot(v)
        p[i] += direction * np.clip(need * .78, -.014, .022)

    fitted_z = p[:, 2]
    hem_overlap = np.exp(-((fitted_z - .298) / .027) ** 2)
    anterior = smoothstep(.032, .073, -p[:, 1])
    p[:, 1] -= .007 * hem_overlap * anterior
    for _ in range(4):
        d, _, normal, _ = nearest(rest_tree, p)
        low = np.where((z > .65) & (z < .77), .0050, .0045)
        change = normal * (np.maximum(0, low - d) - np.maximum(0, d - .026))[:, None]
        p += .7 * change + .30 * average(change, graph)
    return p


def barycentric(triangle, p):
    a, b, c = triangle.transpose(1, 0, 2)
    u, v, w = b - a, c - a, p - a
    uu = np.einsum("ij,ij->i", u, u)
    uv = np.einsum("ij,ij->i", u, v)
    vv = np.einsum("ij,ij->i", v, v)
    wu = np.einsum("ij,ij->i", w, u)
    wv = np.einsum("ij,ij->i", w, v)
    det = (uu * vv - uv * uv).clip(1e-18)
    s, t = (vv * wu - uv * wv) / det, (uu * wv - uv * wu) / det
    values = np.column_stack((1 - s - t, s, t)).clip(0, 1)
    return values / values.sum(axis=1, keepdims=True)


def read_weights(obj, names):
    columns = {group.index: names.index(group.name) for group in obj.vertex_groups if group.name in names}
    w = np.zeros((len(obj.data.vertices), len(names)), dtype=np.float32)
    for vertex in obj.data.vertices:
        for group in vertex.groups:
            if group.group in columns:
                w[vertex.index, columns[group.group]] = group.weight
    return w


def limit_weights(weights):
    order = np.argsort(-weights, axis=1, kind="stable")[:, :4]
    keep = np.zeros_like(weights)
    np.put_along_axis(keep, order, np.take_along_axis(weights, order, axis=1), axis=1)
    keep[keep < .0001] = 0
    return keep / keep.sum(axis=1, keepdims=True)


def bind(points, body, names, rest_tree, graph):
    body_points, triangles = mesh_arrays(body.data)
    w = read_weights(body, names)
    _, locations, _, faces = nearest(rest_tree, points)
    corners = triangles[faces]
    coefficients = barycentric(body_points[corners], locations)
    weights = np.einsum("vi,vib->vb", coefficients, w[corners])
    z = points[:, 2]
    hip = smoothstep(.255, .33, z)
    knee = np.exp(-((z - .209) / .038) ** 2)
    alpha = (.16 * hip + .15 * knee + .035)[:, None]
    for _ in range(3):
        weights += alpha * (average(weights, graph) - weights)
    return limit_weights(weights)


def write_weights(garment, names, weights):
    garment.vertex_groups.clear()
    for bone, values in zip(names, weights.T):
        vertices = np.flatnonzero(values > 0)
        if len(vertices):
            group = garment.vertex_groups.new(name=bone)
            for vertex in vertices:
                group.add([int(vertex)], float(values[vertex]), "REPLACE")


def summarize(distances, overlap_counts, samples):
    result = {}
    for clip in ("rest", *CLIPS):
        idx = [i for i, entry in enumerate(samples) if entry[0] == clip]
        d, overlaps = distances[idx], overlap_counts[idx]
        row, vertex = np.unravel_index(np.argmin(d), d.shape)
        result[clip] = {
            "poses": len(idx), "max_verts_inside": int((d < 0).sum(axis=1).max()),
            "min_signed_dist": float(d[row, vertex]), "vertex": int(vertex),
            "worst_vertex_frame": samples[idx[row]][1], "max_triangle_pairs": int(overlaps.max()),
            "worst_overlap_frame": samples[idx[overlaps.argmax()]][1],
            "sum_triangle_pairs": int(overlaps.sum()),
        }
    return result


def scan(poses, triangles, samples, skin=None, directions=None, contact_divisions=4, body_zones=None):
    distances = np.empty(poses.shape[:2], dtype=np.float32)
    overlap_counts = np.zeros(len(poses), dtype=np.int32)
    edge_contacts = np.zeros(len(triangles), dtype=np.int32)
    requirement = np.zeros(poses.shape[1], dtype=np.float32)
    worst_direction = np.zeros((poses.shape[1], 3), dtype=np.float32)
    fallback = np.zeros(poses.shape[1], dtype=np.float32)
    failed_triangles = []
    limb_requirements = np.zeros_like(distances)
    panel_overlaps = np.zeros(len(poses), dtype=np.int32)
    tri_list = triangles.tolist()
    grid = np.array([(a / contact_divisions, b / contact_divisions, 1 - (a + b) / contact_divisions)
                     for a in range(contact_divisions + 1)
                     for b in range(contact_divisions + 1 - a)], dtype=np.float32)
    for row, (clip, frame, _, panel, limb) in enumerate(samples):
        p = poses[row]
        d, _, n, _ = nearest(panel, p)
        surface = BVHTree.FromPolygons(p.tolist(), tri_list, all_triangles=True)
        panel_pairs = panel.overlap(surface)
        panel_overlaps[row] = len(panel_pairs)
        if limb:
            # Only vertices near extremities can be constrained by their surfaces.
            arm_pairs = limb.overlap(surface)
            close = np.unique(triangles[np.unique([g for _, g in arm_pairs])].ravel()) if arm_pairs else []
            if len(close):
                limb_d, _, _, _ = nearest(limb, p[close])
                limb_requirements[row, close] = np.maximum(0, MARGIN - limb_d)
            # The proof scan uses the complete BVH even where the extremity
            # contacts the body. Fitting considers the two surfaces independently.
            pairs = len(panel_pairs) + len(arm_pairs)
        else:
            pairs = len(panel_pairs)
        distances[row] = d
        overlap_counts[row] = pairs
        faces = np.unique([g for _, g in panel_pairs]).astype(np.int32)
        if len(faces):
            edge_contacts[faces] += 1
            corners = triangles[faces]
            contact_points = (grid @ p[corners]).reshape(-1, 3)
            contact_values, _, contact_normals, contact_faces = nearest(panel, contact_points)
            deepest = contact_values.reshape(-1, len(grid)).argmin(axis=1)
            finest = np.arange(len(faces)) * len(grid) + deepest
            triangle_values = contact_values[finest]
            triangle_normals = contact_normals[finest]
            worst = triangle_values.argmin()
            failed_triangles.append({"clip": clip, "frame": frame, "pairs": pairs,
                                     "sample_depth_m": float(min(0, triangle_values[worst])),
                                     "triangle": int(faces[worst])})
            if body_zones is not None:
                labels, counts = np.unique(body_zones[[b for b, _ in panel_pairs]], return_counts=True)
                failed_triangles[-1]["body_zones"] = dict(zip(labels.tolist(), counts.tolist()))
                failed_triangles[-1]["deepest_contact_body_zone"] = body_zones[contact_faces[finest[worst]]]
        if skin is None:
            continue
        fails = np.flatnonzero(d < MARGIN)
        grad = np.einsum("vi,vij->vj", n[fails], skin[row, fails, :, :3])
        projection = np.einsum("vi,vi->v", grad, directions[fails])
        deficit = MARGIN - d[fails]
        valid = projection > .30
        np.maximum.at(requirement, fails[valid], (deficit / projection.clip(.30))[valid])
        alt = fails[~valid]
        select = deficit[~valid] > fallback[alt]
        fallback[alt[select]] = deficit[~valid][select]
        worst_direction[alt[select]] = grad[~valid][select]
        if len(faces):
            coefficients = grid[deepest]
            gradients = np.einsum("fi,fcij->fcj", triangle_normals, skin[row, corners, :, :3])
            slopes = np.einsum("fci,fci->fc", gradients, directions[corners])
            slope = (slopes * coefficients).sum(axis=1)
            depth = MARGIN - np.minimum(0, triangle_values)
            for column in range(3):
                ids = corners[:, column]
                relevant = coefficients[:, column] > .12
                valid = relevant & (slope > .30) & (slopes[:, column] > .20)
                np.maximum.at(requirement, ids[valid], (depth / slope.clip(.30))[valid])
                for i in np.flatnonzero(relevant & ~valid):
                    vertex = ids[i]
                    if depth[i] > fallback[vertex]:
                        fallback[vertex] = depth[i]
                        worst_direction[vertex] = gradients[i, column]
    return distances, overlap_counts, edge_contacts, requirement, fallback, worst_direction, failed_triangles, limb_requirements, panel_overlaps


def split_contacts(garment, triangles, contacts):
    """Bisect long edges on triangles the pose scan identifies as cutting the body."""
    budget = MAX_TRIANGLES - len(triangles)
    bm = bmesh.new()
    bm.from_mesh(garment.data)
    scores = {}
    for face, count in zip(triangles, contacts):
        if not count:
            continue
        for a, b in zip(face, np.roll(face, 1)):
            key = tuple(sorted((a, b)))
            scores[key] = scores.get(key, 0) + int(count)
    options = []
    for edge in bm.edges:
        key = tuple(sorted(v.index for v in edge.verts))
        length = edge.calc_length()
        if scores.get(key) and length >= .010:
            options.append((-length * (1 + math.log1p(scores[key])), key, edge))
    selected = []
    for _, _, edge in sorted(options, key=lambda item: item[:2]):
        if len(edge.link_faces) <= budget:
            selected.append(edge)
            budget -= len(edge.link_faces)
    if selected:
        bmesh.ops.subdivide_edges(bm, edges=selected, cuts=1, use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=[face for face in bm.faces if len(face.verts) != 3])
        bm.to_mesh(garment.data)
        garment.data.update()
    bm.free()
    print("Split contact edges:", len(selected), flush=True)
    return len(selected)


def set_vertices(mesh, points):
    mesh.vertices.foreach_set("co", np.asarray(points, dtype=np.float32).ravel())
    mesh.update()


def enforce_cap(points, tree):
    for _ in range(4):
        clear, _, normals, _ = nearest(tree, points)
        outside = np.maximum(0, clear - (CAP - .000075))
        points -= outside[:, None] * normals
    return points


def pose_matrices(transforms, weights):
    active = (weights > 0).any(axis=0)
    flat = np.ascontiguousarray(transforms[:, active].transpose(1, 0, 2, 3)).reshape(active.sum(), -1)
    blended = np.ascontiguousarray(weights[:, active]) @ flat
    return np.ascontiguousarray(blended.reshape(len(weights), len(transforms), 3, 4).transpose(1, 0, 2, 3))


def skin_positions(points, skin):
    return np.einsum("fvij,vj->fvi", skin[..., :3], points) + skin[..., 3]


def texture_limit(garment):
    for material in garment.data.materials:
        for node in material.node_tree.nodes:
            if node.type != "TEX_IMAGE" or not node.image:
                continue
            image = node.image
            height = max(image.size)
            if height > 1024:
                image.scale(*(max(1, round(d * 1024 / height)) for d in image.size))
                image.pack()



def export_glb(arm, garment):
    garment.parent = None
    bpy.ops.export_scene.gltf(filepath=str(GLB), export_format="GLB", use_selection=True,
                              export_animations=False, export_all_influences=False, export_tangents=True)
    garment.parent = arm

    # A collapsed source UV island gives a zero MikkTSpace tangent at some
    # export corners. Supply a perpendicular unit tangent for those corners
    # without moving any UV, vertex, or normal.
    content = bytearray(GLB.read_bytes())
    json_size = struct.unpack_from("<I", content, 12)[0]
    data = json.loads(content[20:20 + json_size])
    binary = 28 + json_size

    def accessor_rows(accessor_id, components):
        accessor = data["accessors"][accessor_id]
        view = data["bufferViews"][accessor["bufferView"]]
        assert accessor["componentType"] == 5126
        offset = binary + view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        return np.ndarray((accessor["count"], components), dtype="<f4", buffer=content,
                          offset=offset, strides=(view.get("byteStride", components * 4), 4))

    repairs = 0
    for mesh in data["meshes"]:
        for primitive in mesh["primitives"]:
            attributes = primitive["attributes"]
            tangent = accessor_rows(attributes["TANGENT"], 4)
            normal = accessor_rows(attributes["NORMAL"], 3)
            length = np.linalg.norm(tangent[:, :3], axis=1)
            bad = ~np.isfinite(tangent).all(axis=1) | (length < 1e-6)
            if bad.any():
                n = normal[bad]
                basis = np.eye(3)[np.abs(n).argmin(axis=1)]
                vec = np.cross(basis, n)
                tangent[bad, :3] = vec / np.linalg.norm(vec, axis=1)[:, None]
                tangent[bad, 3] = 1
                repairs += int(bad.sum())
            tangent[:, :3] /= np.linalg.norm(tangent[:, :3], axis=1)[:, None]
    GLB.write_bytes(content)
    print("Degenerate tangent repairs:", repairs, flush=True)

def export(scene, arm, body, garment, points, names, weights):
    set_pose(scene, arm, "rest", 1)
    set_vertices(garment.data, points)
    write_weights(garment, names, weights)
    texture_limit(garment)
    garment.name = garment.data.name = "Jeans"
    for obj in list(scene.objects):
        if obj not in (arm, body, garment):
            bpy.data.objects.remove(obj, do_unlink=True)
    arm.animation_data_clear()
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    bpy.ops.object.select_all(action="DESELECT")
    garment.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = garment
    export_glb(arm, garment)
    body.hide_render = True
    body.hide_set(True)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))



def refine_contact(points, proposed, outward, distances, pressure, weights, transforms, samples, graph, rest_tree):
    """Test alternative directions where a hand and the pants share a small gap."""
    torso_deficit = np.maximum(0, MARGIN - distances.min(axis=0))
    arm_deficit = pressure.max(axis=0)
    active = np.flatnonzero((arm_deficit > .0045) | (torso_deficit > .002))
    if not len(active):
        return proposed, weights
    strata = np.arange(12, dtype=np.float32) + .5
    height = 1 - 2 * strata / len(strata)
    angle = strata * np.pi * (3 - np.sqrt(5))
    radius = np.sqrt(1 - height * height)
    directions = np.column_stack((radius * np.cos(angle), radius * np.sin(angle), height))
    stencil = (np.array([.0025, .006], dtype=np.float32)[:, None, None] * directions).reshape(-1, 3)
    mean_move = average(proposed - points, graph)
    mean_weights = average(weights, graph)
    clip_rows = [np.array([i for i, sample in enumerate(samples) if sample[0] == clip])
                 for clip in CLIPS]
    best_points = proposed.copy()
    best_weights = weights.copy()
    for vertex in active:
        involved = [rows for rows in clip_rows if pressure[rows, vertex].max() > 0]
        danger = [rows[np.argsort(-pressure[rows, vertex], kind="stable")[:2]] for rows in involved]
        worst_body = np.argsort(distances[:, vertex], kind="stable")[:10]
        rows = np.unique(np.r_[0, worst_body, *danger])
        base = points[vertex]
        normal = outward[vertex]
        choices = np.vstack((base, proposed[vertex], base + mean_move[vertex],
                             base + np.array([-.008, -.005, -.003, .003, .006, .010])[:, None] * normal,
                             base + stencil))
        rest_d, _, _, _ = nearest(rest_tree, choices)
        valid = (rest_d >= .002) & (rest_d < CAP - .0001)
        if not valid[0] or not valid.any():
            continue
        choices = choices[valid]
        prior = weights[vertex]
        columns = np.argsort(-np.maximum(prior, mean_weights[vertex]), kind="stable")[:4]
        columns = columns[np.maximum(prior[columns], mean_weights[vertex, columns]) > .020]
        leading = np.eye(len(prior), dtype=np.float32)[columns]
        alternative = limit_weights(np.vstack((
            prior, .68 * prior + .32 * mean_weights[vertex], .79 * prior + .21 * leading,
        )))
        transforms_local = transforms[rows]
        material_weights = np.vstack((np.repeat(prior[None], len(choices), axis=0),
                                      np.repeat(alternative[1:], 3, axis=0)))
        choices = np.vstack((choices, np.tile(np.vstack((base, proposed[vertex], base + .003 * normal)),
                                              (len(alternative) - 1, 1))))
        blend = np.einsum("vb,rbij->rvij", material_weights, transforms_local)
        poses = np.einsum("rvij,vj->rvi", blend[..., :3], choices) + blend[..., 3]
        body_cost = np.zeros((len(rows), len(choices)), dtype=np.float32)
        arm_cost = np.zeros_like(body_cost)
        for k, row in enumerate(rows):
            _, _, _, panel, limb = samples[row]
            d, _, _, _ = nearest(panel, poses[k])
            body_cost[k] = np.maximum(0, MARGIN - d)
            if limb and pressure[row, vertex] > 0:
                d, _, _, _ = nearest(limb, poses[k])
                arm_cost[k] = np.maximum(0, MARGIN - d)
        quality = .10 * np.linalg.norm(choices - (base + mean_move[vertex]), axis=1)
        quality += .18 * np.linalg.norm(choices - base, axis=1)
        quality += .0015 * np.abs(material_weights - prior).sum(axis=1)
        score = (3.6 * body_cost.max(axis=0) + .90 * arm_cost.max(axis=0)
                 + .55 * np.sqrt(np.mean(arm_cost ** 2, axis=0)) + quality)
        winner = score.argmin()
        best_points[vertex] = choices[winner]
        best_weights[vertex] = material_weights[winner]
    delta = best_points - points
    for _ in range(2):
        delta = .70 * delta + .30 * average(delta, graph)
    return enforce_cap(points + delta, rest_tree), limit_weights(best_weights)


def guard_shape(points, proposed, triangles, rest_tree):
    """Keep local rest triangles facing out and preserve a clear rest shell."""
    base = points[triangles]
    n = np.cross(base[:, 1] - base[:, 0], base[:, 2] - base[:, 0])
    original_area = np.linalg.norm(n, axis=1)
    candidates = proposed.copy()
    for _ in range(7):
        current = candidates[triangles]
        p = np.cross(current[:, 1] - current[:, 0], current[:, 2] - current[:, 0])
        area = np.linalg.norm(p, axis=1)
        cosines = (p * n).sum(axis=1) / (area * original_area).clip(1e-13)
        folded = (original_area > 2e-8) & ((cosines < .55) | (area < .30 * original_area) | (area > 3 * original_area))
        overlaps = rest_tree.overlap(tree_from(candidates, triangles))
        collided = np.array([g for _, g in overlaps], dtype=np.int32)
        d, _, _, _ = nearest(rest_tree, candidates)
        ids = np.unique(np.r_[triangles[folded].ravel(), triangles[collided].ravel(),
                              np.flatnonzero((d < .0015) | (d > CAP))])
        if not len(ids):
            return candidates
        candidates[ids] = .45 * candidates[ids] + .55 * points[ids]
    return candidates



def tailored_fit(points, triangles, body, names, rest, graph):
    initial = align(points, rest, graph)
    x, y, z = initial.T
    side = smoothstep(.070, .105, abs(x)) * smoothstep(.260, .343, z)
    crease = smoothstep(.016, .048, y) * smoothstep(.126, .192, z) * (1 - smoothstep(.270, .319, z))
    rear_band = (1 - smoothstep(.014, .066, abs(x))) * smoothstep(.033, .066, y) * smoothstep(.360, .407, z)
    clearance, _, normal, _ = nearest(rest, initial)
    travel = np.maximum(clearance - .0034, 0) * (-.83 * side - .63 * crease) + .0065 * rear_band
    displacement = normal * travel[:, None]
    for _ in range(2):
        displacement = .80 * displacement + .20 * average(displacement, graph)
    points = guard_shape(initial, enforce_cap(initial + displacement, rest), triangles, rest)
    # The forward right thigh folds under the fly in run. Let this patch
    # follow the knee a little so it can clear the bend with a small offset.
    core = np.array([-.042, -.088, .304])
    density = np.exp(-np.square((points - core) / [.028, .034, .030]).sum(axis=1))
    patch = density[:, None] * np.array([.001, -.004, .0014])
    points = guard_shape(points, enforce_cap(points + patch, rest), triangles, rest)
    original_weights = bind(initial, body, names, rest, graph)
    refit_weights = bind(points, body, names, rest, graph)
    weights = limit_weights(.65 * original_weights + .35 * refit_weights)
    knee = np.zeros(len(names))
    knee[names.index("mixamorig:RightLeg")] = 1.
    weights += (density * .25)[:, None] * (knee - weights)
    return points, limit_weights(weights)


def build():
    scene, arm, body, garment = setup(SOURCE)
    clean_source(garment)
    body_coords, body_faces = evaluated_arrays(body, bpy.context.evaluated_depsgraph_get())
    rest_tree = tree_from(body_coords, body_faces)
    names = [bone.name for bone in arm.pose.bones]
    mesh = garment.data
    graph = adjacency(mesh)
    points, triangles = mesh_arrays(mesh)
    points, weights = tailored_fit(points, triangles, body, names, rest_tree, graph)
    max_passes = int(sys.argv[sys.argv.index("--passes") + 1]) if "--passes" in sys.argv else 0
    assert 0 <= max_passes <= 12
    if max_passes == 0:
        export(scene, arm, body, garment, points, names, weights)
        return
    samples, transforms = cache_poses(scene, arm, body)
    skin = pose_matrices(transforms, weights)
    fit_history = []
    best = None
    for iteration in range(max_passes + 1):
        clear, _, normals, _ = nearest(rest_tree, points)
        outward = .58 * normals + .42 * average(normals, graph)
        outward /= np.linalg.norm(outward, axis=1).clip(1e-7)[:, None]
        result = scan(skin_positions(points, skin), triangles, samples, skin, outward)
        distances, overlaps, hits, required, fallback, alternative, _, limbs, panel_pairs = result
        summary = summarize(distances, overlaps, samples)
        fit_history.append({"iteration": iteration, "triangles": len(triangles), "results": summary})
        print("FIT", iteration, "triangles", len(triangles), "rest range", distances[0].min(), distances[0].max(),
              "poses", [(c, v["max_verts_inside"], round(v["min_signed_dist"] * 1000, 2),
                         v["max_triangle_pairs"]) for c, v in summary.items()],
              "total pairs", int(overlaps.sum()), "lower-body pairs", int(panel_pairs.sum()),
              "negative lower-body vertices", int((distances < 0).sum()), flush=True)
        hard_failure = int((distances[0] < .00055).any() or (distances[0] > CAP).any() or overlaps[0] > 0)
        score = (hard_failure, int(3 * panel_pairs.sum() + (overlaps - panel_pairs).sum() + 4 * (distances < 0).sum()),
                 int((distances < .0005).sum()), float(-distances.min()))
        if best is None or score < best[0]:
            best = score, iteration, mesh.copy(), points.copy(), weights.copy()
        if distances.min() >= MARGIN and not overlaps.any() and distances[0].max() <= CAP:
            break
        if iteration == max_passes:
            break
        if iteration in (2, 6) and hits.any():
            set_vertices(mesh, points)
            write_weights(garment, names, weights)
            if split_contacts(garment, triangles, hits):
                points, triangles = mesh_arrays(mesh)
                graph = adjacency(mesh)
                interpolated = limit_weights(read_weights(garment, names))
                rebind = bind(points, body, names, rest_tree, graph)
                weights = limit_weights(.67 * interpolated + .33 * rebind)
                skin = pose_matrices(transforms, weights)
                continue

        smoothed = required.copy()
        for _ in range(3):
            smoothed += .46 * (average(smoothed, graph) - smoothed)
        increment = np.maximum(smoothed, required).clip(0, .009)
        displacement = outward * increment[:, None]
        active = (fallback > .0006) & (fallback > required * .6)
        alternative[~active] = 0
        alternate_step = alternative * np.minimum(fallback * .32, .0035)[:, None]
        displacement += alternate_step
        part = np.einsum("vi,vi->v", displacement, outward)
        correction = np.maximum(0, increment - part)
        displacement += outward * correction[:, None]
        proposed = enforce_cap(points + displacement, rest_tree)
        proposed, weights = refine_contact(points, proposed, outward, distances, limbs,
                                           weights, transforms, samples, graph, rest_tree)
        points = guard_shape(points, proposed, triangles, rest_tree)
        skin = pose_matrices(transforms, weights)
    _, iteration, mesh, points, weights = best
    garment.data = mesh
    write_report("fit_history.json", {"selected_iteration": iteration, "margin_m": MARGIN,
                                          "clearance_limit_m": CAP, "passes": fit_history})
    print("EXPORT iteration:", iteration, flush=True)
    export(scene, arm, body, garment, points, names, weights)



def reexport():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, garment = (scene.objects[name] for name in ("Armature", "Jeans"))
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    garment.select_set(True)
    bpy.context.view_layer.objects.active = garment
    export_glb(arm, garment)

def statistics(values):
    quantiles = np.quantile(values, [0, .1, .5, .9, .95, 1])
    return {"count": len(values), **dict(zip(("min", "p10", "median", "p90", "p95", "max"),
                                           map(float, quantiles)))}


def zone(point):
    x, y, z = point
    if z >= .396:
        return "waistband"
    if z <= .094:
        return "cuff"
    if abs(x) < .044 and z >= .27:
        return "crotch"
    if z >= .338:
        return "seat" if y > -.014 else "front hips"
    if z >= .241:
        return "upper thigh"
    if z >= .173:
        return "knee"
    return "lower leg"


def inspect_export():
    glb = GLB.read_bytes()
    magic, version, total, json_size = struct.unpack_from("<4sIII", glb)
    assert (magic, version, total) == (b"glTF", 2, len(glb))
    data = json.loads(glb[20:20 + json_size])
    blob = glb[28 + json_size:]
    assert len(data["meshes"]) == len(data["skins"]) == 1 and not data.get("animations")
    joint_names = [data["nodes"][joint]["name"] for joint in data["skins"][0]["joints"]]
    assert len(joint_names) == 65 and len(set(joint_names)) == 65
    assert set(joint_names) == {bone.name for bone in bpy.context.scene.objects["Armature"].data.bones}
    counts, influences = 0, 0
    for primitive in data["meshes"][0]["primitives"]:
        attr = primitive["attributes"]
        assert primitive.get("mode", 4) == 4 and "WEIGHTS_1" not in attr
        counts += data["accessors"][primitive["indices"]]["count"] // 3
        accessor = data["accessors"][attr["WEIGHTS_0"]]
        assert accessor["type"] == "VEC4" and accessor["componentType"] == 5126
        view = data["bufferViews"][accessor["bufferView"]]
        start = accessor.get("byteOffset", 0) + view.get("byteOffset", 0)
        stride = view.get("byteStride", 16)
        for i in range(accessor["count"]):
            weights = struct.unpack_from("<4f", blob, start + i * stride)
            assert abs(sum(weights) - 1) < 1e-5 and min(weights) >= 0
            influences = max(influences, sum(weight > 0 for weight in weights))
    assert counts <= MAX_TRIANGLES and influences <= 4
    images = {}
    for material in bpy.context.scene.objects:
        if material.type != "MESH" or material.name in ("Base_Body",) or material.hide_viewport:
            continue
        for mat in material.data.materials:
            for node in mat.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image:
                    images[node.image.name] = node.image.size[:]
    assert images and max(max(size) for size in images.values()) <= 1024
    return {"triangles": counts, "max_influences": influences, "joints": joint_names,
            "textures": images, "mesh_count": 1, "animation_count": 0,
            "glb_bytes": len(glb), "blend_bytes": BLEND.stat().st_size,
            "glb_sha256": hashlib.sha256(glb).hexdigest(),
            "blend_sha256": hashlib.sha256(BLEND.read_bytes()).hexdigest()}



def mesh_boundaries(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
    marked = {e for e in bm.edges if e.is_boundary}
    groups = []
    for edge in bm.edges:
        if edge not in marked:
            continue
        marked.remove(edge)
        pending = [edge]
        nodes = set(edge.verts)
        while pending:
            for vertex in pending.pop().verts:
                for item in vertex.link_edges:
                    if item in marked:
                        marked.remove(item)
                        pending.append(item)
                        nodes.update(item.verts)
        coordinates = np.array([v.co[:] for v in nodes])
        groups.append({"vertices": len(nodes), "centroid": np.mean(coordinates, axis=0).tolist(),
                       "min": coordinates.min(axis=0).tolist(), "max": coordinates.max(axis=0).tolist()})
    bm.free()
    return sorted(groups, key=lambda group: (-group["vertices"], group["centroid"]))

def verify():
    scene, arm, body, garment = setup(GLB)
    points, triangles = mesh_arrays(garment.data)
    samples, poses = cache_poses(scene, arm, body, garment)
    joint_names = [bone.name for bone in arm.pose.bones]
    _, body_faces = mesh_arrays(body.data)
    body_weights = read_weights(body, joint_names)
    body_zones = np.array([joint_names[i].split(":")[-1] for i in body_weights[body_faces].sum(axis=1).argmax(axis=1)])
    distances, overlaps, _, _, _, _, failures, _, _ = scan(
        poses, triangles, samples, contact_divisions=8, body_zones=body_zones)
    results = summarize(distances, overlaps, samples)
    zones = np.array([zone(p) for p in points])
    for clip, entry in results.items():
        vertex = entry["vertex"]
        entry["zone"] = zones[vertex]
        entry["rest_vertex_xyz_m"] = points[vertex].tolist()
        row = next(i for i, sample in enumerate(samples) if sample[:2] == (clip, entry["worst_vertex_frame"]))
        _, _, _, body_face = nearest(samples[row][2], poses[row, [vertex]])
        entry["body_zone"] = body_zones[body_face[0]]
    for entry in failures:
        entry["zone"] = zone(points[triangles[entry["triangle"]]].mean(axis=0))
    base_points, _ = mesh_arrays(body.data)
    lower = base_points[body_faces, 2].min(axis=1) < .475
    hips = lower & (base_points[body_faces, 2].max(axis=1) < .435)
    master_contacts = {}
    for clip, entry in results.items():
        if entry["min_signed_dist"] >= .0005:
            continue
        frame = entry["worst_vertex_frame"]
        set_pose(scene, arm, clip, frame)
        body_posed, _ = evaluated_arrays(body, bpy.context.evaluated_depsgraph_get())
        count = len(tree_from(body_posed, body_faces[hips]).overlap(
            tree_from(body_posed, body_faces[~lower])))
        master_contacts[clip] = {"frame": frame, "upper_body_vs_hips_triangle_pairs": count}
    value = inspect_export()
    write_report("export_check.json", value)
    write_report("dense_check.json", {
        "glb_sha256": value["glb_sha256"], "poses": len(samples), "results": results,
        "gate_pass": bool(distances.min() >= .0005 and not overlaps.any() and distances[0].max() <= CAP),
        "rest_clearance_m": {"all": statistics(distances[0]), **{
            label: statistics(distances[0, zones == label]) for label in sorted(set(zones))
        }},
        "rest_vertices_over_30mm": int((distances[0] > CAP).sum()),
        "rest_bounds_xyz_m": [points.min(axis=0).tolist(), points.max(axis=0).tolist()],
        "mesh_boundaries_m": mesh_boundaries(garment.data),
        "triangle_residuals": failures,
        "master_self_contacts": master_contacts,
    })
    for clip, data in results.items():
        print("DENSE RESULT", clip, data, flush=True)


def run_checker(stem):
    path = HERE / "work" / f"{stem}.py"
    supplied = path.read_text()
    # Use the supplied geometry and frame samplers verbatim. Textured Cycles
    # renders are handled by render_qa so the metric reports can run headless.
    source = supplied.replace("bpy.ops.render.render(write_still=True)", "None")
    source = source.replace("sc.render.engine='BLENDER_WORKBENCH';", "")
    source = source.replace("{out}/motion_check.json", "{out}/" + stem + ".json")
    assert source != supplied
    output = io.StringIO()
    argv = sys.argv
    try:
        sys.argv = [str(path), "--", str(MASTER), str(MOTION), str(GLB), str(OUTPUT)]
        with redirect_stdout(output):
            exec(compile(source, str(path), "exec"), {})
    finally:
        sys.argv = argv
    lines = [line for line in output.getvalue().splitlines() if line.startswith("RESULT ")]
    assert len(lines) == 8
    report = "\n".join(lines) + "\n"
    (OUTPUT / f"{stem}.txt").write_text(report)
    print(report, end="", flush=True)


def render_qa():
    scene, arm, body, garment = setup(GLB)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_percentage = 100
    scene.render.resolution_x = scene.render.resolution_y = 640
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.view_settings.view_transform = "AgX"
    world = bpy.data.worlds.new("QA Studio")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (.70, .76, .85, 1)
    background.inputs[1].default_value = .5
    focus = Vector((0, -.01, .248))
    for name, location, energy, size in (
        ("Key", (-.65, -1.25, 1.35), 65, 1.55), ("Fill", (.8, -.3, .68), 26, 1.3),
        ("Rim", (.3, 1.1, 1.0), 49, 1.2),
    ):
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.shape, light.size = energy, "DISK", size
        lamp = bpy.data.objects.new(name, light)
        scene.collection.objects.link(lamp)
        lamp.location = location
        lamp.rotation_euler = (focus - lamp.location).to_track_quat("-Z", "Y").to_euler()
    camera_data = bpy.data.cameras.new("QA Orthographic")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    output = OUTPUT / "renders"
    output.mkdir(exist_ok=True)
    views = []

    def capture(name, focus, direction, width, clip, frame, show_body=True):
        body.hide_render = not show_body
        camera_data.ortho_scale = width
        camera.location = focus + Vector(direction).normalized() * 3
        camera.rotation_euler = (focus - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(output / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        views.append({"file": f"renders/{name}.png", "clip": clip, "frame": frame,
                      "focus": tuple(focus), "direction": direction, "width": width, "body": show_body,
                      "sha256": hashlib.sha256((output / f"{name}.png").read_bytes()).hexdigest()})

    if "--motion-only" not in sys.argv:
        for name, direction, show_body in (
            ("rest_front", (0, -1, 0), True), ("rest_back", (0, 1, 0), True),
            ("rest_left", (1, 0, 0), True), ("rest_right", (-1, 0, 0), True),
            ("rest_front_three_quarter", (.60, -1, .22), True),
            ("rest_rear_three_quarter", (-.62, 1, .40), False),
        ):
            capture(name, focus, direction, .49, "rest", 1, show_body)
    if "--rest-only" not in sys.argv:
        for clip in ("walk", "run", "wave", "jump"):
            first, last = bpy.data.actions[clip].frame_range
            frame = int(first + (last - first) * .4)
            set_pose(scene, arm, clip, frame)
            posed, _ = evaluated_arrays(garment, bpy.context.evaluated_depsgraph_get())
            center = Vector((posed.min(axis=0) + posed.max(axis=0)) / 2)
            capture(clip, center, (.55, -1, .07), .60, clip, frame)
    write_report("render_manifest.json", {"glb_sha256": hashlib.sha256(GLB.read_bytes()).hexdigest(),
                                             "engine": "Cycles CPU", "samples": 12, "views": views})


if __name__ == "__main__":
    if "--verify" in sys.argv:
        verify()
    elif "--checkers" in sys.argv:
        run_checker("motion_check")
        run_checker("motion_check_tri")
    elif "--renders" in sys.argv:
        render_qa()
    elif "--reexport" in sys.argv:
        reexport()
    else:
        build()
