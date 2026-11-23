"""Fit the Tripo gamepad T-shirt and verify its GLB on the chibi master.

Run inside Blender 5.1. Use --verify, --checkers or --renders after "--"
to check or capture an existing export. All distances are in metres.
"""
import hashlib
import io
import json
import math
from contextlib import redirect_stdout
from pathlib import Path
import struct
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
import numpy as np


HERE = Path(__file__).resolve().parent
OUT = HERE
MASTER = HERE / "../../master/GJH_Chibi_Master_rigged.blend"
MOTION = HERE / "../../../../models/tripo-chibi-motion/motion.glb"
SOURCE = HERE / "source_studio_retopo.glb"
NAME = "tshirt_v1"
GLB = OUT / (NAME + ".glb")
CLIPS = ("walk", "run", "wave", "jump", "idle", "nod", "dance")
RENDER_CLIPS = ("walk", "run", "wave", "jump")
TARGET = .0005
MARGIN = .002
REST_CAP = .030
TRIANGLE_LIMIT = 6000
ITERATIONS = 12


def write_json(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2) + "\n")


def coordinates(mesh):
    points = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", points)
    return points.reshape(-1, 3)


def triangles(mesh):
    mesh.calc_loop_triangles()
    faces = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int32)
    mesh.loop_triangles.foreach_get("vertices", faces)
    return faces.reshape(-1, 3)


def normalize(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def ramp(values, start, stop):
    t = np.clip((values - start) / (stop - start), 0, 1)
    return t * t * (3 - 2 * t)


def geometry(obj, dg):
    posed = obj.evaluated_get(dg)
    mesh = posed.to_mesh()
    try:
        verts = coordinates(mesh)
        mw = np.asarray(posed.matrix_world, dtype=np.float32)
        return verts @ mw[:3, :3].T + mw[:3, 3], triangles(mesh)
    finally:
        posed.to_mesh_clear()


def signed(tree, coords, details=False):
    queries = [tree.find_nearest(p) for p in coords.tolist()]
    surface = np.array([q[0] for q in queries], dtype=np.float32)
    normal = np.array([q[1] for q in queries], dtype=np.float32)
    values = np.einsum("vi,vi->v", coords - surface, normal)
    if details:
        return values, normal, np.array([q[2] for q in queries], dtype=np.int32)
    return values, normal


def adjacency(mesh):
    edge = np.empty(len(mesh.edges) * 2, dtype=np.int32)
    mesh.edges.foreach_get("vertices", edge)
    p, q = edge.reshape(-1, 2).T.copy()
    row, col = np.r_[p, q], np.r_[q, p]
    counts = np.maximum(1, np.bincount(row, minlength=len(mesh.vertices)))
    return row, col, counts


def mean_neighbors(values, links):
    row, col, counts = links
    result = np.zeros_like(values)
    np.add.at(result, row, values[col])
    return result / counts.reshape((-1,) + (1,) * (values.ndim - 1))


def import_one(path):
    before = {o.as_pointer() for o in bpy.context.scene.objects}
    bpy.ops.import_scene.gltf(filepath=str(path.resolve()))
    return [o for o in bpy.context.scene.objects if o.as_pointer() not in before]


def open_master():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER.resolve()), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body = (scene.objects[name] for name in ("Armature", "Base_Body"))
    assert len(arm.data.bones) == 65
    assert np.allclose(arm.matrix_world, np.eye(4)) and np.allclose(body.matrix_world, np.eye(4))
    arm.animation_data_clear()
    arm.animation_data_create()
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    scene.frame_set(1)
    bpy.context.view_layer.update()
    return scene, arm, body


def archive_source_material(garment):
    used = {node.image for mat in garment.data.materials for node in mat.node_tree.nodes
            if node.type == "TEX_IMAGE" and node.image is not None}
    for img in sorted(used, key=lambda i: i.name):
        width, height = img.size
        factor = min(1, 1024 / max(width, height))
        if factor < 1:
            img.scale(round(width * factor), round(height * factor))
        img.pack()


def source_shell(garment):
    """Keep the exterior across the front relief and rolled opening rims."""
    bm = bmesh.new()
    bm.from_mesh(garment.data)
    bm.transform(garment.matrix_world)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
    bm.normal_update()
    bm.faces.index_update()
    tree = BVHTree.FromBMesh(bm)
    chosen = set()
    for face in bm.faces:
        c = face.calc_center_median()
        x, y, z = c
        sleeve = float(ramp(abs(x), .223, .347) * ramp(z, .328, .389))
        radial = Vector((x * (1 - sleeve), y - .043, (z - .479) * sleeve))
        opening = Vector((math.copysign(1, x) * float(ramp(abs(x), .440, .489)), 0,
                          float(ramp(z, .587, .661) * (1 - sleeve) - .7 * ramp(z, .090, .015))))
        directions = [radial.normalized(), (radial.normalized() + opening).normalized()]
        # End-facing rim facets are exterior only if they are also visible
        # from the outside and do not turn back into the lining.
        directions.extend((directions[-1] + face.normal * a).normalized() for a in (.48, .95))
        best = max(face.normal.dot(d) for d in directions[:2])
        hem = z < .12
        cuff = abs(x) > .397
        if (hem or cuff) and face.normal.dot(directions[0]) < .10:
            continue
        if best < -.10:
            continue
        for d in directions:
            if face.normal.dot(d) < .09:
                continue
            _, _, hit, travel = tree.ray_cast(c + 1.6 * d, -d, 1.601)
            if hit == face.index or (travel is not None and travel > 1.5985):
                chosen.add(face)
                break

    # The logo border and seam relief can occlude neighboring exterior faces.
    # Fill these enclosed patches using the original faces and their original UVs.
    skipped = set(bm.faces) - chosen
    islands = []
    while skipped:
        face = min(skipped, key=lambda f: f.index)
        skipped.remove(face)
        stack, island = [face], [face]
        while stack:
            for edge in stack.pop().edges:
                for neighbor in edge.link_faces:
                    if neighbor in skipped:
                        skipped.remove(neighbor)
                        stack.append(neighbor)
                        island.append(neighbor)
        islands.append(island)
    print("SOURCE FACE PATCHES", sorted(map(len, islands), reverse=True), flush=True)
    for island in islands:
        center = sum((f.calc_center_median() for f in island), Vector()) / len(island)
        if len(island) < 55 and .107 < center.z and abs(center.x) < .443:
            chosen.update(island)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f not in chosen], context="FACES")
    bm.normal_update()
    # Remove any detached scraps left by visibility at the four openings.
    pending = set(bm.faces)
    components = []
    while pending:
        face = min(pending, key=lambda f: f.index)
        pending.remove(face)
        stack, component = [face], [face]
        while stack:
            for edge in stack.pop().edges:
                for neighbor in edge.link_faces:
                    if neighbor in pending:
                        stack.append(neighbor)
                        component.append(neighbor)
                        pending.remove(neighbor)
        components.append(component)
    print("EXTERIOR COMPONENTS", sorted(map(len, components), reverse=True), flush=True)
    largest = set(max(components, key=len))
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f not in largest], context="FACES")
    for p, n in (((.470, 0, 0), (1, 0, 0)), ((-.470, 0, 0), (-1, 0, 0)),
                 ((0, 0, .027), (0, -.067, -1))):
        bmesh.ops.bisect_plane(bm, geom=[*bm.verts, *bm.edges, *bm.faces],
                              dist=.000001, plane_co=p, plane_no=n, clear_outer=True)
    fix_small_openings(bm)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.to_mesh(garment.data)
    bm.free()
    garment.matrix_world = Matrix.Identity(4)
    garment.data.update()
    canonicalize_source(garment)


def canonicalize_source(garment):
    """Order welded positions and oriented corners independently of BMesh allocation."""
    mesh = garment.data
    p = np.round(coordinates(mesh).astype(np.float64), 7)
    order = np.lexsort(p[:, ::-1].T)
    index = np.argsort(order)
    uv_layer = mesh.uv_layers.active
    rows = []
    for face in mesh.polygons:
        ids = list(face.loop_indices)
        corners = index[np.asarray(face.vertices)]
        start = int(corners.argmin())
        ids = ids[start:] + ids[:start]
        key = tuple(np.roll(corners, -start))
        uv = [tuple(uv_layer.uv[loop].vector) for loop in ids]
        rows.append((key, face.material_index, uv))
    rows.sort()
    ordered = bpy.data.meshes.new("Tripo outer shell")
    ordered.from_pydata(p[order].tolist(), [], [row[0] for row in rows])
    layer = ordered.uv_layers.new(name=uv_layer.name)
    for material in mesh.materials:
        ordered.materials.append(material)
    for poly, (_, material, uv) in zip(ordered.polygons, rows):
        poly.material_index = material
        for loop, tex in zip(poly.loop_indices, uv):
            layer.uv[loop].vector = tex
    garment.data = ordered
    ordered.update()


def fix_small_openings(bm):
    bm.verts.index_update()
    bm.edges.index_update()
    uv = bm.loops.layers.uv.active
    edge_pool = {edge for edge in bm.edges if edge.is_boundary}
    while edge_pool:
        edge = min(edge_pool, key=lambda e: e.index)
        edge_pool.remove(edge)
        ring, stack = [edge], [edge]
        while stack:
            for v in stack.pop().verts:
                for neighbor in sorted(v.link_edges, key=lambda e: e.index):
                    if neighbor in edge_pool:
                        edge_pool.remove(neighbor)
                        ring.append(neighbor)
                        stack.append(neighbor)
        if len(ring) > 12:
            continue
        data = {v: v.link_loops[0][uv].uv.copy() for e in ring for v in e.verts}
        patched = bmesh.ops.holes_fill(bm, edges=ring, sides=12)["faces"]
        for patch in patched:
            patch.smooth = True
            for corner in patch.loops:
                corner[uv].uv = data[corner.vert]
    bm.normal_update()


def source_fit(garment):
    p = coordinates(garment.data)
    x, y, z = p.T
    ax = np.abs(x)
    sleeve = ramp(ax, .210, .330) * ramp(z, .312, .346)
    xx = np.interp(ax, [0, .15, .20, .25, .32, .49], [0, .058, .075, .091, .104, .120])
    torso_x = ax * np.interp(z, [0, .08, .24, .36, .51, .66],
                            [.405, .405, .384, .374, .386, .387])
    arm_y = -.006 + .45 * (y - .044)
    torso_y = -.030 + (y - .025) * np.interp(z, [0, .22, .36, .49, .57, .66],
                                            [.406, .382, .376, .345, .349, .327])
    arm_z = .562 + (z - .478) * .385
    torso_z = np.interp(z, [0, .075, .345, .475, .548, .610, .662],
                       [.384, .403, .518, .562, .582, .607, .625])
    # Reduce the original hanging hem's slant, preserving the embossed hem seam.
    torso_z = .389 + (torso_z - .389) * ramp(z, .008, .105)
    fit = np.column_stack((.001 + np.sign(x) * (torso_x * (1 - sleeve) + xx * sleeve),
                           torso_y * (1 - sleeve) + arm_y * sleeve,
                           torso_z * (1 - sleeve) + arm_z * sleeve))
    garment.data.vertices.foreach_set("co", fit.astype(np.float32).ravel())
    garment.data.update()
    return p, fit.astype(np.float32), sleeve


def assign_skin(garment, arm):
    garment.parent = arm
    modifier = garment.modifiers.new("Armature", "ARMATURE")
    modifier.object = arm


def read_weights(obj, names):
    cols = [names.index(g.name) if g.name in names else -1 for g in obj.vertex_groups]
    weights = np.zeros((len(obj.data.vertices), len(names)), dtype=np.float32)
    for vertex in obj.data.vertices:
        for group in vertex.groups:
            if cols[group.group] >= 0:
                weights[vertex.index, cols[group.group]] = group.weight
    return weights


def limit_weights(weights):
    order = np.argsort(-weights, axis=-1, kind="stable")[..., :4]
    limited = np.zeros_like(weights)
    np.put_along_axis(limited, order, np.take_along_axis(weights, order, axis=-1), axis=-1)
    limited[limited < .00002] = 0
    total = limited.sum(axis=-1, keepdims=True)
    assert (total > 0).all()
    return limited / total


def nearest_weights(points, body, body_faces, names, rest, links):
    weights = read_weights(body, names)
    b = coordinates(body.data)
    result = []
    for p in points:
        closest, _, face, _ = rest.find_nearest(p)
        corners = body_faces[face]
        tri = b[corners]
        uv = np.linalg.lstsq((tri[1:] - tri[0]).T, np.asarray(closest) - tri[0], rcond=None)[0]
        result.append(np.clip(np.r_[1 - uv.sum(), uv], 0, 1) @ weights[corners])
    result = np.array(result, dtype=np.float32)
    x, _, z = points.T
    for i, name in enumerate(names):
        short = name.split(":")[-1]
        if any(t in short for t in ("Leg", "Foot", "Toe")):
            result[:, names.index("mixamorig:Hips")] += .75 * result[:, i]
            result[:, i] *= .25
        if short in {"Head", "HeadTop_End"}:
            result[:, names.index("mixamorig:Neck")] += result[:, i]
            result[:, i] = 0
    mix = np.where((abs(x) > .065) | (z < .432), .43, .22)
    for _ in range(3):
        result += mix[:, None] * (mean_neighbors(result, links) - result)
    return limit_weights(result)


def write_weights(garment, names, weights):
    garment.vertex_groups.clear()
    groups = [garment.vertex_groups.new(name=name) for name in names]
    for vi, bi in zip(*np.nonzero(weights)):
        groups[bi].add([int(vi)], float(weights[vi, bi]), "REPLACE")


def load_motion():
    imported = import_one(MOTION)
    for o in imported:
        # Actions are retained by fake users. The imported geometry/rig
        # is irrelevant after the quaternion tracks have been read.
        bpy.data.objects.remove(o, do_unlink=True)
    assert all(bpy.data.actions.get(name) for name in CLIPS)
    for name in CLIPS:
        bpy.data.actions[name].use_fake_user = True


def set_pose(scene, arm, name, frame):
    action = None if name == "rest" else bpy.data.actions[name]
    arm.animation_data.action = action
    if action is not None:
        arm.animation_data.action_slot = action.slots[0]
    else:
        for bone in arm.pose.bones:
            bone.matrix_basis.identity()
    scene.frame_set(math.floor(frame), subframe=frame % 1)
    bpy.context.view_layer.update()


def times():
    yield "rest", 1.0
    for name in CLIPS:
        start, stop = bpy.data.actions[name].frame_range
        selected = {start, stop, *(i / 2 for i in range(math.ceil(2 * start), math.floor(2 * stop) + 1))}
        selected.update(int(start + (stop - start) * k / 12) for k in range(12))
        selected.update(range(int(start), int(stop) + 1, 3))
        yield from ((name, f) for f in sorted(selected))


def cache_motion(scene, arm, body, names):
    bones = [arm.pose.bones[name] for name in names]
    modes = tuple(b.rotation_mode for b in bones)
    inverse = [b.bone.matrix_local.inverted() for b in bones]
    samples, transforms = [], []
    for name, frame in times():
        set_pose(scene, arm, name, frame)
        p, f = geometry(body, bpy.context.evaluated_depsgraph_get())
        samples.append((name, frame, BVHTree.FromPolygons(p.tolist(), f.tolist(), all_triangles=True), p, f))
        transforms.append(np.asarray([bone.matrix @ inv for bone, inv in zip(bones, inverse)])[:, :3, :])
    assert modes == tuple(b.rotation_mode for b in bones)
    return samples, np.asarray(transforms, dtype=np.float32)


def rest_shape(mesh, initial, rest, sleeve):
    links = adjacency(mesh)
    points = initial.copy()
    # The Tripo relief stays on the surface. Apply broad, smoothly distributed
    # corrections where its initial body clearance needs changing.
    side = ramp(np.abs(initial[:, 0]), .041, .090)
    outer_cap = .021 - .014 * np.maximum(side, sleeve * .9)
    for _ in range(21):
        d, normals = signed(rest, points)
        upper = outer_cap
        normals[:, 0] *= 1 - .90 * sleeve
        normals[:, 2] *= ramp(initial[:, 2], .394, .425) * .92 + .08
        step = (np.maximum(.0052 - d, 0) - np.maximum(d - upper, 0))[:, None] * normals
        smoothed = .64 * step + .36 * mean_neighbors(step, links)
        points += smoothed
        points[:, 2] = np.maximum(points[:, 2], .383)
    d, normals = signed(rest, points)
    points += (np.maximum(.0035 - d, 0) - np.maximum(d - .028, 0))[:, None] * normals
    points[:, 2] = np.maximum(points[:, 2], .382)
    x, y, z = points.T.copy()
    lateral = ramp(abs(x), .04, .09) * (1 - ramp(z, .525, .554))
    for _ in range(10):
        d, n = signed(rest, points)
        step = n * ((np.maximum(.0028 - d, 0) - np.maximum(d - .0060, 0)) * lateral)[:, None]
        step[:, 2] *= .45
        points += .54 * step + .46 * mean_neighbors(step, links)
    points[:, 2] += .0075 * (1 - ramp(z, .391, .459))
    points[:, 1] += .007 * ramp(y, .012, .046) * (1 - ramp(z, .426, .451)) * ramp(z, .390, .413)
    points[:, 0] -= np.sign(x) * .001 * ramp(abs(x), .086, .118) * ramp(z, .482, .518)
    return rest_limit(points, rest, initial)


def skin(points, weights, transforms):
    matrices = (weights @ transforms.transpose(1, 0, 2, 3).reshape(weights.shape[1], -1))
    matrices = matrices.reshape(len(weights), len(transforms), 3, 4).transpose(1, 0, 2, 3)
    posed = np.einsum("fvij,vj->fvi", matrices[..., :3], points) + matrices[..., 3]
    return posed, matrices


def summarize(samples, values, overlaps):
    result = {}
    for name in ("rest", *CLIPS):
        idx = [i for i, sample in enumerate(samples) if sample[0] == name]
        d, ov = values[idx], overlaps[idx]
        row, vert = np.unravel_index(d.argmin(), d.shape)
        result[name] = {
            "samples": len(idx),
            "max_verts_inside": int((d < 0).sum(axis=1).max()),
            "min_signed_dist": float(d[row, vert]),
            "minimum_vertex_frame": samples[idx[row]][1],
            "vertex": int(vert),
            "max_triangle_pairs": int(ov.max()),
            "max_pair_frame": samples[idx[int(ov.argmax())]][1],
            "sum_triangle_pairs": int(ov.sum()),
        }
    return result


def reimport():
    scene, arm, body = open_master()
    imports = import_one(GLB)
    garment, = [obj for obj in imports if obj.type == "MESH" and obj in bpy.context.selected_objects]
    garment.parent = None
    for obj in imports:
        if obj.type == "ARMATURE":
            bpy.data.objects.remove(obj, do_unlink=True)
    for modifier in list(garment.modifiers):
        garment.modifiers.remove(modifier)
    assign_skin(garment, arm)
    load_motion()
    return scene, arm, body, garment


def export(garment, arm, body, points, names, weights):
    set_pose(bpy.context.scene, arm, "rest", 1)
    arm.animation_data_clear()
    garment.data.vertices.foreach_set("co", points.astype(np.float32).ravel())
    garment.data.update()
    for face in garment.data.polygons:
        face.use_smooth = True
    if garment.data.has_custom_normals:
        bpy.context.view_layer.objects.active = garment
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    write_weights(garment, names, weights)
    garment.name = garment.data.name = NAME
    assert len(triangles(garment.data)) <= TRIANGLE_LIMIT
    archive_source_material(garment)
    bpy.ops.object.select_all(action="DESELECT")
    garment.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = garment
    bpy.ops.export_scene.gltf(filepath=str(GLB), export_format="GLB", use_selection=True,
                             export_animations=False, export_yup=True, export_all_influences=False,
                             export_def_bones=False, export_tangents=True, export_armature_object_remove=True)
    garment.parent = arm
    for name in CLIPS:
        a = bpy.data.actions.get(name)
        if a:
            bpy.data.actions.remove(a)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / (NAME + ".blend")))


def setup():
    scene, arm, body = open_master()
    garment, = [obj for obj in import_one(SOURCE) if obj.type == "MESH"]
    source_shell(garment)
    _, initial, sleeve = source_fit(garment)
    assign_skin(garment, arm)
    names = tuple(b.name for b in arm.data.bones)
    return scene, arm, body, garment, initial, sleeve, names


def build():
    scene, arm, body, garment, initial, sleeve, names = setup()
    body_verts, body_faces = geometry(body, bpy.context.evaluated_depsgraph_get())
    rest = BVHTree.FromPolygons(body_verts.tolist(), body_faces.tolist(), all_triangles=True)
    points = rest_shape(garment.data, initial, rest, sleeve)
    weights = nearest_weights(points, body, body_faces, names, rest, adjacency(garment.data))
    if "--initial" not in sys.argv:
        load_motion()
        samples, transforms = cache_motion(scene, arm, body, names)
        points, weights, reference = fit(garment, points, weights, samples, transforms)
        set_pose(scene, arm, "rest", 1)
        points = preserve_source_relief(points, reference, garment, body)
        points = polish_front_hem(garment, body, points)
    export(garment, arm, body, points, names, weights)


def collect_fit(points, weights, faces, transforms, samples):
    posed, matrices = skin(points, weights, transforms)
    rows, ids, bary, normals, depth = [], [], [], [], []
    values = np.empty(posed.shape[:2], dtype=np.float32)
    overlaps = np.zeros(len(samples), dtype=np.int32)
    hits = np.zeros(len(faces), dtype=np.int32)
    for idx, sample in enumerate(samples):
        d, n, _, pair, witness = scan_frame(posed[idx], faces, sample, collect=True)
        values[idx], overlaps[idx] = d, len(pair)
        v = np.flatnonzero(d < MARGIN + .0015)
        raw = np.repeat(v[:, None], 3, axis=1)
        coef = np.zeros_like(raw, dtype=np.float32)
        coef[:, 0] = 1
        norm, sd = n[v], d[v]
        if len(pair):
            np.add.at(hits, pair[:, 0], 1)
            w_id, w_bary, w_sd, w_n, _ = witness
            raw = np.concatenate((raw, faces[w_id]))
            coef = np.concatenate((coef, w_bary))
            norm = np.concatenate((norm, w_n))
            sd = np.r_[sd, w_sd]
        rows.append(np.full(len(raw), idx, dtype=np.int32))
        ids.append(raw)
        bary.append(coef)
        normals.append(norm)
        depth.append(sd)
    data = tuple(np.concatenate(a) for a in (rows, ids, bary, normals, depth))
    return values, overlaps, data, matrices, hits


def project_simplex(weights):
    sorted_weights = np.sort(weights, axis=1)[:, ::-1]
    offset = ((sorted_weights.cumsum(axis=1) - 1) / np.arange(1, 5)).max(axis=1)
    return np.maximum(weights - offset[:, None], 0)


def rest_limit(points, tree, original):
    for _ in range(3):
        d, n = signed(tree, points)
        points += (np.maximum(.0021 - d, 0) - np.maximum(d - REST_CAP + .00008, 0))[:, None] * n
        points[:, 2] = np.maximum(points[:, 2], .378)
        # Sleeve ring positions remain anchored on the upper-arm axis.
        cuff = (np.abs(original[:, 0]) > .111) & (original[:, 2] > .515)
        points[cuff, 0] = np.clip(points[cuff, 0], original[cuff, 0] - .004, original[cuff, 0] + .004)
    return points


def split_contacts(garment, points, weights, faces, hits):
    """Bisect only long edges of intersecting faces, retaining UV seams."""
    mesh = garment.data
    edge_faces = {}
    for face_id, face in enumerate(faces):
        for u, v in zip(face, np.roll(face, -1)):
            edge_faces.setdefault(tuple(sorted((u, v))), []).append(face_id)
    candidates = []
    for edge, attached in edge_faces.items():
        length = np.linalg.norm(points[edge[0]] - points[edge[1]])
        score = int(hits[attached].sum())
        if score and length > .014:
            candidates.append((-length * math.log1p(score), edge, attached))

    split, taken = {}, {}
    limit = min(150, TRIANGLE_LIMIT - len(faces))
    for _, edge, adjacent in sorted(candidates):
        if len(adjacent) > limit or any(i in taken for i in adjacent):
            continue
        limit -= len(adjacent)
        split[edge] = len(points) + len(split)
        for i in adjacent:
            taken[i] = edge
    if not split:
        return points, weights, np.empty((0, 2), dtype=np.int32)

    layer = mesh.uv_layers.active
    new_faces, new_uv = [], []
    for i, face in enumerate(faces):
        uv = [tuple(layer.uv[j].vector) for j in mesh.polygons[i].loop_indices]
        if i not in taken:
            new_faces.append(face.tolist())
            new_uv.append(uv)
            continue
        edge = taken[i]
        j = next(j for j in range(3) if tuple(sorted((face[j], face[(j + 1) % 3]))) == edge)
        k, m = (j + 1) % 3, (j + 2) % 3
        mid = split[edge]
        uv_mid = tuple((a + b) * .5 for a, b in zip(uv[j], uv[k]))
        new_faces.extend(([face[j], mid, face[m]], [mid, face[k], face[m]]))
        new_uv.extend(([uv[j], uv_mid, uv[m]], [uv_mid, uv[k], uv[m]]))

    edge_array = np.array(list(split))
    extended = np.concatenate((points, points[edge_array].mean(axis=1)))
    weights = limit_weights(np.concatenate((weights, weights[edge_array].mean(axis=1))))
    new = bpy.data.meshes.new("T-shirt fitted skin")
    new.from_pydata(extended.tolist(), [], new_faces)
    for material in mesh.materials:
        new.materials.append(material)
    tex = new.uv_layers.new(name=layer.name)
    for f, uv in zip(new.polygons, new_uv):
        for loop, val in zip(f.loop_indices, uv):
            tex.uv[loop].vector = val
    garment.data = new
    new.update()
    return extended, weights, edge_array


def guard_rest(points, faces, sample, origin, links):
    """Reduce active rest contacts using mesh outward normals and verify each move."""
    tree = sample[2]
    best = points
    for _ in range(5):
        d, n, _, pair, witness = scan_frame(best, faces, sample, collect=True, deep=True)
        if not len(pair) and d.min() >= TARGET:
            break
        initial_score = len(pair) + 15 * np.sum(d < TARGET)
        step = n * np.maximum(MARGIN - d, 0)[:, None]
        if witness is not None:
            ids = faces[witness[0]]
            tri = best[ids]
            normal = normalize(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]))
            # At the rear hip seam the body's closest surface can be the
            # near-horizontal top of the shorts. The shirt moves rearward.
            back = (tri.mean(axis=1)[:, 1] > .018) & (tri.mean(axis=1)[:, 2] < .45)
            normal[back] = (0, 1, 0)
            offset = normal * np.maximum(.0014, MARGIN - witness[2])[:, None]
            positive = np.zeros_like(step)
            negative = np.zeros_like(step)
            for col in range(3):
                np.maximum.at(positive, ids[:, col], offset.clip(0))
                np.minimum.at(negative, ids[:, col], offset.clip(None, 0))
            step += positive + negative
        step += .43 * mean_neighbors(step, links)
        accepted = False
        for factor in (1., 2., .5):
            candidate = rest_limit(best + factor * step, tree, origin)
            d, _, _, pair, _ = scan_frame(candidate, faces, sample)
            score = len(pair) + 15 * np.sum(d < TARGET)
            if score < initial_score:
                best = candidate
                accepted = True
                break
        if not accepted:
            break
    return best


def preserve_source_relief(points, reference, garment, body):
    """Restore the source's embossed logo and soften nearby shape corrections."""
    points = np.asarray(points, dtype=np.float32)
    links = adjacency(garment.data)
    x, y, z = reference.T
    abdomen = 1 - ramp(abs(x), .060, .080)
    front = ramp(-y, .092, .109)
    graphic = abdomen * front * ramp(z, .453, .474) * (1 - ramp(z, .547, .565))
    delta = points - reference
    correction = .78 * delta + .22 * mean_neighbors(delta, links)
    new = reference + correction * (.88 * (1 - graphic))[:, None]
    faces = triangles(garment.data)
    bv, bf = geometry(body, bpy.context.evaluated_depsgraph_get())
    tree = BVHTree.FromPolygons(bv.tolist(), bf.tolist(), all_triangles=True)
    sample = ("rest", 1.0, tree, bv, bf)
    new = guard_rest(new.astype(np.float32), faces, sample, reference, links)
    d, _, _, pairs, _ = scan_frame(new, faces, sample)
    return new if not len(pairs) and d.min() >= TARGET and d.max() <= REST_CAP else points


def polish_front_hem(garment, body, points):
    """Smooth the compressed front band while retaining its UV seams."""
    base = np.array(points, dtype=np.float32, copy=True)
    p = base.copy()
    _, y, z = base.T
    strength = (ramp(-y, .056, .093) * (1 - ramp(z, .429, .448)))[:, None]
    strength = strength * np.array((.21, .72, .31), dtype=np.float32)
    links = adjacency(garment.data)
    faces = triangles(garment.data)
    v, t = geometry(body, bpy.context.evaluated_depsgraph_get())
    rest = BVHTree.FromPolygons(v.tolist(), t.tolist(), all_triangles=True)
    sample = ("rest", 1.0, rest, v, t)
    for _ in range(12):
        p += strength * (mean_neighbors(p, links) - p)
        p -= .35 * strength * (mean_neighbors(p, links) - p)
    p[:, 2] = np.clip(p[:, 2], base[:, 2] - .005, base[:, 2] + .005)
    p = guard_rest(p, faces, sample, base, links)
    d, _, _, pairs, _ = scan_frame(p, faces, sample)
    return p if not len(pairs) and d.min() >= TARGET and d.max() <= REST_CAP else base


def solve_contacts(points, weights, matrices, transforms, contacts, links, rest, original,
                   iteration, faces):
    frame, ids, bary, normals, distance = contacts
    count = len(points)
    drest, rest_normal = signed(rest, points)
    inv_direction = np.einsum("ni,nkij->nkj", normals, matrices[frame[:, None], ids, :, :3])
    cuff = (np.abs(original[:, 0]) > .106) & (original[:, 2] > .510)
    stiffness = np.ones_like(points)
    stiffness[cuff, 0] = .15
    stiffness[original[:, 2] < .402, 2] = .20

    # Worst radial requirement accumulated across every sample. When posed
    # arms approach the torso from the opposite side, add independent local
    # contact constraints instead of amplifying an inward radial correction.
    radial_projection = np.einsum("nki,nki->nk", inv_direction, rest_normal[ids])
    required = np.maximum(MARGIN - distance, 0)[:, None] / radial_projection.clip(.30)
    use = (radial_projection > .32) & (bary >= .30)
    radial = np.zeros(count, dtype=np.float32)
    np.maximum.at(radial, ids[use], required[use])
    # Opposed contacts need tangent or weight changes. Reserve clearance for
    # them while making the full worst-case radial move on compatible points.
    opposed = ((radial_projection < -.30) & (bary > .30) & (distance[:, None] < MARGIN))
    blocked = np.unique(ids[opposed])
    radial[blocked] = 0
    smooth = radial.copy()
    for _ in range(3):
        smooth = np.maximum(radial, .42 * smooth + .58 * mean_neighbors(smooth, links))
    smooth = np.minimum(smooth, np.maximum(0, REST_CAP - drest - .0001))
    initial = np.minimum(smooth, .007 if iteration == 1 else .004)
    delta = np.zeros((count, 7), dtype=np.float32)
    delta[:, :3] = rest_normal * initial[:, None] * stiffness

    # Joint-coefficient adjustments use the nearest-body anatomical support.
    # They share each contact constraint with the local rest-position change.
    columns = np.argsort(-weights, axis=1, kind="stable")[:, :4]
    current = np.take_along_axis(weights, columns, axis=1)
    joint = transforms[frame[:, None, None], columns[ids]]
    joint_point = np.einsum("nkjlm,nkm->nkjl", joint[..., :3], points[ids]) + joint[..., 3]
    influence = np.einsum("nl,nkjl->nkj", normals, joint_point)
    influence -= influence.mean(axis=2, keepdims=True)
    weight_scale = .65 if iteration > 1 else .25
    gradient = np.concatenate((inv_direction * stiffness[ids], influence * weight_scale), axis=2)
    gradient *= bary[..., None]
    flat = ids.ravel()
    for _ in range(18):
        residual = np.maximum(MARGIN - distance - np.einsum("nkj,nkj->n", gradient, delta[ids]), 0)
        emphasis = residual ** 1.8
        denom = np.einsum("nkj,nkj->nk", gradient, gradient).clip(.035)
        strength = (emphasis[:, None] * bary).ravel()
        norm = np.bincount(flat, weights=strength, minlength=count).clip(1e-12)
        force = gradient * ((emphasis * residual)[:, None] / denom)[..., None] * bary[..., None]
        move = np.column_stack([np.bincount(flat, weights=f.ravel(), minlength=count)
                                for f in force.transpose(2, 0, 1)]) / norm[:, None]
        delta += (.71 * move).astype(np.float32)
        smooth_delta = mean_neighbors(delta[:, :3], links)
        delta[:, :3] += .115 * (smooth_delta - delta[:, :3])
        length = np.linalg.norm(delta[:, :3], axis=1)
        delta[:, :3] *= np.minimum(1, .012 / length.clip(1e-8))[:, None]
        new = project_simplex(current + delta[:, 3:] * weight_scale)
        delta[:, 3:] = (new - current) / weight_scale

    displacement = delta[:, :3] * stiffness
    next_weights = np.zeros_like(weights)
    np.put_along_axis(next_weights, columns, project_simplex(current + delta[:, 3:] * weight_scale), axis=1)
    next_weights = limit_weights(.88 * next_weights + .12 * mean_neighbors(next_weights, links))

    # Suppress triangle flips as the contact corrections accumulate.
    reference = points[faces]
    reference_normals = np.cross(reference[:, 1] - reference[:, 0], reference[:, 2] - reference[:, 0])
    for _ in range(3):
        proposal = (points + displacement)[faces]
        n = np.cross(proposal[:, 1] - proposal[:, 0], proposal[:, 2] - proposal[:, 0])
        bad = np.unique(faces[np.einsum("ni,ni->n", n, reference_normals) < 0])
        displacement[bad] *= .48
    return displacement, next_weights


def fit(garment, points, weights, samples, transforms):
    rest = samples[0][2]
    history = []
    best = None
    original = points.copy()
    faces = triangles(garment.data)
    links = adjacency(garment.data)
    split_count = 0
    reference = points.copy()

    for iteration in range(ITERATIONS + 1):
        points = guard_rest(points, faces, samples[0], original, links)
        d, ov, contacts, matrices, hits = collect_fit(points, weights, faces, transforms, samples)
        measures = summarize(samples, d, ov)
        print("FIT", iteration, "rest pairs", int(ov[0]), "dense overlap pairs", int(ov.sum()),
              "dense inside vertices", int((d < 0).sum()), "min mm", round(float(d.min()) * 1000, 3),
              [(k, v["max_triangle_pairs"], round(v["min_signed_dist"] * 1000, 2))
               for k, v in measures.items()], flush=True)
        history.append(measures)
        # Rest acceptance, positive distance and the cut surface all matter.
        # Normalize pose counts for the denser topology after a local split.
        scale = 3750 / len(faces)
        score = (scale * (ov.sum() + 2.8 * (d < 0).sum()) +
                 19000 * float(np.maximum(0, -d.min()) * 1000) / 10 +
                 100000 * (int(ov[0]) + int((d[0] < TARGET).sum()) +
                           int((d[0] > REST_CAP + 1e-6).sum())))
        if best is None or score < best[0]:
            best = score, iteration, points.copy(), weights.copy(), garment.data, reference.copy()

        if iteration == ITERATIONS or (not ov.any() and (d >= TARGET).all() and d[0].max() <= REST_CAP):
            break
        if iteration == 2 and hits.any():
            points, weights, split_edges = split_contacts(garment, points, weights, faces, hits)
            split_count = len(split_edges)
            if split_count:
                reference = np.concatenate((reference, reference[split_edges].mean(axis=1)))
                original = points.copy()
                faces, links = triangles(garment.data), adjacency(garment.data)
                print("SUBDIVIDED CONTACT EDGES", split_count, flush=True)
                continue

        displacement, next_weights = solve_contacts(points, weights, matrices, transforms, contacts,
                                                     links, rest, original, iteration + 1, faces)
        # Small geometric steps reduce face inversions around the short
        # sleeves. Smooth the correction rather than the source relief.
        gain = .56 if iteration < 6 else .40
        total = points - original + gain * displacement
        total = .88 * total + .12 * mean_neighbors(total, links)
        limit = np.linalg.norm(total, axis=1).clip(1e-9)
        points = rest_limit(original + total * np.minimum(1, .016 / limit)[:, None],
                            rest, original)
        weights = limit_weights((1 - gain) * weights + gain * next_weights)

    _, chosen, points, weights, mesh, reference = best
    garment.data = mesh
    write_json("fit_history.json", {"margin_m": MARGIN, "rest_cap_m": REST_CAP,
                                    "selected_iteration": chosen, "trial_subdivided_edges": split_count,
                                    "iterations": history})
    return points, weights, reference


def region_faces(points):
    x, y, z = points.T
    region = np.where(z < .425, "hem", np.where(y < -.027, "front panel", "back panel")).astype("U24")
    region[(np.abs(x) > .073) & (z > .505)] = "shoulder / armpit"
    region[(np.abs(x) > .101) & (z > .510)] = "sleeve / cuff"
    region[(np.abs(x) < .063) & (z > .581)] = "collar"
    return region


def contact_witnesses(coords, faces, body, body_faces, pairs, deep):
    """Sample intersected garment triangles and the actual intersection lines."""
    garment_ids, body_ids = pairs.T
    chosen = np.unique(garment_ids)
    divisions = 8 if deep else 3
    grid = np.array([(i / divisions, j / divisions, (divisions - i - j) / divisions)
                     for i in range(divisions + 1) for j in range(divisions + 1 - i)])
    ids = [np.repeat(chosen, len(grid))]
    coeff = [np.tile(grid, (len(chosen), 1))]
    gt, bt = coords[faces[garment_ids]], body[body_faces[body_ids]]
    origin = gt[:, 0]
    u, v = gt[:, 1] - origin, gt[:, 2] - origin
    normal = np.cross(u, v)
    height = np.einsum("nkj,nj->nk", bt - origin[:, None], normal)
    uu, uv, vv = ((a * b).sum(axis=1) for a, b in ((u, u), (u, v), (v, v)))
    det = (uu * vv - uv * uv).clip(1e-19)
    for j in range(3):
        k = (j + 1) % 3
        active = np.flatnonzero((height[:, j] * height[:, k] <= 0) &
                                (np.abs(height[:, j] - height[:, k]) > 1e-15))
        alpha = height[active, j] / (height[active, j] - height[active, k])
        point = bt[active, j] + alpha[:, None] * (bt[active, k] - bt[active, j]) - origin[active]
        wu, wv = (point * u[active]).sum(axis=1), (point * v[active]).sum(axis=1)
        s = (vv[active] * wu - uv[active] * wv) / det[active]
        t = (uu[active] * wv - uv[active] * wu) / det[active]
        bary = np.column_stack((1 - s - t, s, t))
        keep = bary.min(axis=1) >= -.0001
        ids.append(garment_ids[active[keep]])
        coeff.append(bary[keep])
    return np.concatenate(ids), np.concatenate(coeff).astype(np.float32)


def scan_frame(coords, faces, geom, collect=False, deep=False):
    _, _, tree, bv, bf = geom
    dist, normals, nearest = signed(tree, coords, details=True)
    overlap = np.asarray(sorted(tree.overlap(BVHTree.FromPolygons(
        coords.tolist(), faces.tolist(), all_triangles=True))), dtype=np.int32).reshape(-1, 2)
    overlap = overlap[:, ::-1]
    witnesses = None
    if len(overlap) and (collect or deep):
        ids, bary = contact_witnesses(coords, faces, bv, bf, overlap, deep)
        ws = np.einsum("ni,nij->nj", bary, coords[faces[ids]])
        sd, normal, nearest_face = signed(tree, ws, details=True)
        order = np.lexsort((sd, ids))
        use = order[np.r_[True, np.diff(ids[order]) > 0]]
        witnesses = ids[use], bary[use], sd[use], normal[use], nearest_face[use]
    return dist, normals, nearest, overlap, witnesses


def stats(values):
    return dict(zip(("min", "p10", "median", "p90", "p95", "max"),
                    np.percentile(values, [0, 10, 50, 90, 95, 100]).tolist()))


def inspect_export():
    payload = GLB.read_bytes()
    magic, version, length, json_length = struct.unpack_from("<4sIII", payload)
    assert (magic, version, length) == (b"glTF", 2, len(payload))
    gltf = json.loads(payload[20:20 + json_length])
    binary = payload[28 + json_length:]
    assert len(gltf["meshes"]) == len(gltf["skins"]) == 1
    assert not gltf.get("animations")
    joints = [gltf["nodes"][j]["name"] for j in gltf["skins"][0]["joints"]]
    assert len(joints) == 65 and len(set(joints)) == 65
    triangles = vertices = max_influences = 0
    for primitive in gltf["meshes"][0]["primitives"]:
        attr = primitive["attributes"]
        assert primitive.get("mode", 4) == 4 and "WEIGHTS_1" not in attr
        assert all(a in attr for a in ("JOINTS_0", "TEXCOORD_0", "TANGENT"))
        triangles += gltf["accessors"][primitive["indices"]]["count"] // 3
        accessor = gltf["accessors"][attr["WEIGHTS_0"]]
        assert accessor["type"] == "VEC4" and accessor["componentType"] == 5126
        vertices += accessor["count"]
        view = gltf["bufferViews"][accessor["bufferView"]]
        start = accessor.get("byteOffset", 0) + view.get("byteOffset", 0)
        for i in range(accessor["count"]):
            weights = struct.unpack_from("<4f", binary, start + i * view.get("byteStride", 16))
            assert min(weights) >= 0 and abs(sum(weights) - 1) < 1e-5
            max_influences = max(max_influences, sum(w > 0 for w in weights))
    assert triangles <= TRIANGLE_LIMIT
    assert max_influences <= 4
    assert len(gltf["materials"]) == 1
    return {"glb_sha256": hashlib.sha256(payload).hexdigest(), "glb_bytes": len(payload),
            "blend_bytes": (OUT / (NAME + ".blend")).stat().st_size, "triangles": triangles,
            "glb_vertices": vertices, "joint_names": joints, "max_influences": max_influences,
            "garment_meshes": len(gltf["meshes"]), "animations": len(gltf.get("animations", []))}


def opening_measurements(garment, arm):
    """Weld UV splits for the geometric opening and fit measurements."""
    bm = bmesh.new()
    bm.from_mesh(garment.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=.0000003)
    bm.verts.index_update()
    boundary = {edge for edge in bm.edges if edge.is_boundary}
    result = {}
    while boundary:
        seed = min(boundary, key=lambda e: tuple(sorted(v.index for v in e.verts)))
        boundary.remove(seed)
        ring = set(seed.verts)
        stack = list(seed.verts)
        while stack:
            for edge in stack.pop().link_edges:
                if edge in boundary:
                    boundary.remove(edge)
                    for other in edge.verts:
                        if other not in ring:
                            ring.add(other)
                            stack.append(other)
        p = np.array([v.co for v in sorted(ring, key=lambda v: v.index)])
        center = p.mean(axis=0)
        if center[2] < .47:
            name = "hem"
        elif center[0] > .09:
            name = "left cuff"
        elif center[0] < -.09:
            name = "right cuff"
        else:
            name = "collar"
        data = {"vertices": len(p), "min_xyz_m": p.min(axis=0).tolist(),
                "max_xyz_m": p.max(axis=0).tolist(), "center_xyz_m": center.tolist()}
        if "cuff" in name:
            side = name.split()[0].title()
            bone = arm.data.bones["mixamorig:" + side + "Arm"]
            head, tail = np.asarray(bone.head_local), np.asarray(bone.tail_local)
            axis = tail - head
            data["upper_arm_fraction"] = float((center - head) @ axis / (axis @ axis))
        result.setdefault(name, []).append(data)
    nonmanifold = sum(len(e.link_faces) > 2 for e in bm.edges)
    bm.free()
    return result, nonmanifold


def verify():
    """Measure both gates on the evaluated, reimported GLB at all half frames."""
    scene, arm, body, garment = reimport()
    structure = inspect_export()
    gp = coordinates(garment.data)
    names = tuple(b.name for b in arm.data.bones)
    assert set(names) == set(structure["joint_names"])
    textures = {node.image for material in garment.data.materials for node in material.node_tree.nodes
                if node.type == "TEX_IMAGE" and node.image is not None}
    structure["textures"] = {img.name: list(img.size) for img in sorted(textures, key=lambda img: img.name)}
    assert len(textures) == 3 and all(max(i.size) <= 1024 for i in textures)
    structure["openings"], structure["nonmanifold_edges"] = opening_measurements(garment, arm)
    write_json("export_check.json", structure)
    body_zones = np.array(names)[read_weights(body, names)[triangles(body.data)].sum(axis=1).argmax(axis=1)]
    regions = region_faces(gp)
    failures = {}
    samples, values, overlaps = [], [], []
    for name, frame in times():
        set_pose(scene, arm, name, frame)
        dg = bpy.context.evaluated_depsgraph_get()
        bv, bf = geometry(body, dg)
        geom = (name, frame, BVHTree.FromPolygons(bv.tolist(), bf.tolist(), all_triangles=True), bv, bf)
        coords, faces = geometry(garment, dg)
        ds, _, nearest, pairs, witness = scan_frame(coords, faces, geom, deep=True)
        samples.append((name, frame))
        values.append(ds)
        overlaps.append(len(pairs))
        clip = failures.setdefault(name, {})
        for locus, dist, near in [("vertex", ds, nearest)] + (
                [("triangle witness", witness[2], witness[4])] if witness is not None else []):
            if locus == "vertex":
                zones = regions
            else:
                zones = region_faces(gp[faces[witness[0]]].mean(axis=1))
            for i in np.flatnonzero(dist < TARGET):
                zone = f"{zones[i]} / {body_zones[near[i]].split(':')[-1]}"
                record = clip.setdefault(locus, {}).setdefault(zone, {"min_signed_dist": 1})
                if dist[i] < record["min_signed_dist"]:
                    record.update(min_signed_dist=float(dist[i]), frame=frame)
    result = summarize(samples, np.array(values), np.array(overlaps))
    rest = values[0]
    write_json("dense_check.json", {
        "glb_sha256": hashlib.sha256(GLB.read_bytes()).hexdigest(),
        "samples": len(samples), "clips": result,
        "rest_clearance_m": {"overall": stats(rest), **{
            zone: stats(rest[regions == zone]) for zone in np.unique(regions)}},
        "residuals": failures,
    })
    print("DENSE", result, flush=True)


def configure_render(scene):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.world = bpy.data.worlds.new("T-shirt QA")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (.74, .77, .85, 1)
    background.inputs[1].default_value = .50
    focus = Vector((0, 0, .51))
    for name, position, energy, size in (
        ("Key", (-.9, -1.6, 2.1), 150, 1.8),
        ("Fill", (1.4, -1.1, 1.25), 75, 2.0),
        ("Rim", (.4, 1.4, 1.8), 100, 1.5),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.shape, data.size = energy, "DISK", size
        light = bpy.data.objects.new(name, data)
        scene.collection.objects.link(light)
        light.location = position
        light.rotation_euler = (focus - light.location).to_track_quat("-Z", "Y").to_euler()


def renders():
    scene, arm, body, garment = reimport()
    configure_render(scene)
    folder = OUT / "renders"
    folder.mkdir(exist_ok=True)
    camera = bpy.data.objects.new("Fit QA", bpy.data.cameras.new("Fit QA"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    scene.render.resolution_x, scene.render.resolution_y = 820, 640

    def shot(stem, focus, direction, scale, visible=True):
        body.hide_render = not visible
        focus = Vector(focus)
        camera.location = focus + 3 * Vector(direction)
        camera.rotation_euler = (focus - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.ortho_scale = scale
        scene.render.filepath = str(folder / (stem + ".png"))
        bpy.ops.render.render(write_still=True)

    set_pose(scene, arm, "rest", 1)
    focus = (0, -.015, .500)
    for stem, direction in (
        ("rest_front", (0, -1, 0)), ("rest_back", (0, 1, 0)), ("rest_right", (1, 0, 0)),
        ("rest_left", (-1, 0, 0)), ("rest_front_three_quarter", (.62, -1, .25)),
        ("rest_back_three_quarter", (-.62, 1, .25)),
    ):
        shot(stem, focus, direction, .56)
    if "--rest-only" in sys.argv:
        return
    scene.render.resolution_x = scene.render.resolution_y = 800
    for name in RENDER_CLIPS:
        start, end = bpy.data.actions[name].frame_range
        frame = int(start + .4 * (end - start))
        set_pose(scene, arm, name, frame)
        posed, _ = geometry(body, bpy.context.evaluated_depsgraph_get())
        bounds = posed.min(axis=0), posed.max(axis=0)
        center = .5 * (bounds[0] + bounds[1])
        scale = 1.15 * max(np.max(bounds[1] - bounds[0]), .96)
        shot(name, center, (.24, -1, .11), scale)
    write_json("render_info.json", {
        "png_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in sorted(folder.glob("*.png"))},
        "glb_sha256": hashlib.sha256(GLB.read_bytes()).hexdigest(),
        "engine": "Cycles CPU", "samples": scene.cycles.samples,
        "motion_frames": {name: int(a.frame_range[0] + .4 * (a.frame_range[1] - a.frame_range[0]))
                          for name in RENDER_CLIPS if (a := bpy.data.actions[name])},
    })


def checker(stem):
    # Preserve measurement and sampling from the supplied files. Their four
    # Workbench shots are captured as textured Cycles renders in --renders.
    path = HERE / "work" / (stem + ".py")
    source = path.read_text().replace("bpy.ops.render.render(write_still=True)", "None")
    source = source.replace("{out}/motion_check.json", "{out}/" + stem + ".json")
    output = io.StringIO()
    argv = sys.argv
    try:
        sys.argv = [str(path), "--", str(MASTER.resolve()), str(MOTION.resolve()), str(GLB), str(OUT)]
        with redirect_stdout(output):
            exec(compile(source, str(path), "exec"), {})
    finally:
        sys.argv = argv
    lines = [line for line in output.getvalue().splitlines() if line.startswith("RESULT ")]
    assert len(lines) == 8
    result = "\n".join(lines) + "\n"
    print(result, end="", flush=True)
    (OUT / (stem + ".txt")).write_text(result)


if __name__ == "__main__":
    if "--output" in sys.argv:
        local = (HERE / sys.argv[sys.argv.index("--output") + 1]).resolve()
        if not local.is_relative_to(HERE):
            raise ValueError("Output must stay within the T-shirt directory")
        local.mkdir(parents=True, exist_ok=True)
        OUT = local
        GLB = OUT / (NAME + ".glb")
    if "--verify" in sys.argv:
        verify()
    elif "--checkers" in sys.argv:
        checker("motion_check")
        checker("motion_check_tri")
    elif "--renders" in sys.argv:
        renders()
    else:
        build()
