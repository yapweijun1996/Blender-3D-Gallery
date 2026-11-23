"""Build and fit plain shorts from the Studio segmentation on the chibi master."""
import math
import hashlib
import runpy
import bpy
import bmesh
import numpy as np
import json
import sys
import struct
from pathlib import Path
from collections import Counter
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PARTS = HERE.parents[2]
SOURCE = HERE.parent / "source_studio_segmented.glb"
MASTER = PARTS / "master/GJH_Chibi_Master_rigged.blend"
STAGED = HERE / "shorts_studio_working.blend"

def neutral():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body = scene.objects["Armature"], scene.objects["Base_Body"]
    animation = arm.animation_data_create()
    animation.action = None
    animation.use_nla = False
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.view_layer.update()
    return scene, arm, body

def write_json(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2) + "\n")

def mesh_data(mesh):
    vertices = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", vertices)
    mesh.calc_loop_triangles()
    faces = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int32)
    mesh.loop_triangles.foreach_get("vertices", faces)
    return vertices.reshape(-1, 3), faces.reshape(-1, 3)

def active(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

def topology(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    seen = set()
    groups = []
    for start in bm.verts:
        if start in seen:
            continue
        todo, group = [start], []
        seen.add(start)
        while todo:
            vertex = todo.pop()
            group.append(vertex)
            for edge in vertex.link_edges:
                other = edge.other_vert(vertex)
                if other not in seen:
                    seen.add(other)
                    todo.append(other)
        edge_set = {edge for vertex in group for edge in vertex.link_edges}
        xyz = np.asarray([v.co[:] for v in group])
        groups.append(dict(vertices=len(group), edges=dict(Counter(len(e.link_faces) for e in edge_set)),
                           low=xyz.min(axis=0).tolist(), high=xyz.max(axis=0).tolist()))
    loops = []
    unseen = {edge for edge in bm.edges if edge.is_boundary}
    while unseen:
        todo = [unseen.pop()]
        group = set()
        while todo:
            edge = todo.pop()
            group.update(edge.verts)
            for vertex in edge.verts:
                neighbors = {e for e in vertex.link_edges if e in unseen}
                unseen.difference_update(neighbors)
                todo.extend(neighbors)
        xyz = np.asarray([v.co[:] for v in group])
        loops.append(dict(vertices=len(group), low=xyz.min(axis=0).tolist(),
                          high=xyz.max(axis=0).tolist(), center=xyz.mean(axis=0).tolist()))
    bm.free()
    return dict(components=sorted(groups, key=lambda group: -group["vertices"]),
                boundary=sorted(loops, key=lambda loop: -loop["vertices"]))

def stage():
    scene, arm, body = neutral()
    old = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE), merge_vertices=True)
    imported = set(scene.objects) - old
    obj = next(o for o in imported if o.name == "tripo_part_5")
    world = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = world
    for other in imported - {obj}:
        bpy.data.objects.remove(other, do_unlink=True)
    active(obj)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    source_triangles = len(obj.data.polygons)
    images = [node.image for node in obj.active_material.node_tree.nodes if node.type == "TEX_IMAGE"]
    image_info = {image.name: list(image.size) for image in images}
    decimate = obj.modifiers.new("Early decimation", "DECIMATE")
    decimate.ratio = 2100 / source_triangles
    decimate.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=decimate.name)
    obj.name = "Studio_Shorts"
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(STAGED), compress=True)
    body_bounds = [list(body.matrix_world @ Vector(v)) for v in body.bound_box]
    bones = {bone.name: [list(arm.matrix_world @ bone.head_local), list(arm.matrix_world @ bone.tail_local)]
             for bone in arm.data.bones if bone.name.split(":")[-1] in
             {"Hips", "Spine", "Spine1", "LeftUpLeg", "RightUpLeg", "LeftLeg", "RightLeg"}}
    write_json("source_inspection.json", dict(part="tripo_part_5", source_triangles=source_triangles,
               staged_triangles=len(obj.data.polygons), images=image_info, body_bounds=body_bounds,
               bones=bones, **topology(obj.data)))


def restore_surface():
    """Weld exact source positions before collapse while preserving corner UVs."""
    bpy.ops.wm.open_mainfile(filepath=str(STAGED), load_ui=False, use_scripts=False)
    obj = bpy.context.scene.objects["Studio_Shorts"]
    raw = SOURCE.read_bytes()
    size, = struct.unpack_from("<I", raw, 12)
    document = json.loads(raw[20:20 + size])
    part = next(node for node in document["nodes"] if node["name"] == "tripo_part_5")
    primitive, = document["meshes"][part["mesh"]]["primitives"]

    def accessor(index, dtype, width):
        data = document["accessors"][index]
        view = document["bufferViews"][data["bufferView"]]
        offset = size + 28 + view.get("byteOffset", 0) + data.get("byteOffset", 0)
        return np.frombuffer(raw, dtype=dtype, count=data["count"] * width, offset=offset).reshape(-1, width)

    positions = accessor(primitive["attributes"]["POSITION"], "<f4", 3)
    coordinates, inverse = np.unique(positions, axis=0, return_inverse=True)
    coordinates += part["translation"]
    coordinates = coordinates[:, [0, 2, 1]]
    coordinates[:, 1] *= -1
    original_faces = accessor(primitive["indices"], "<u4", 1).reshape(-1, 3)
    faces = inverse[original_faces]
    uv = accessor(primitive["attributes"]["TEXCOORD_0"], "<f4", 2)[original_faces.ravel()].copy()
    uv[:, 1] = 1 - uv[:, 1]
    fresh = bpy.data.meshes.new("Welded Studio exterior")
    fresh.from_pydata(coordinates.tolist(), [], faces.tolist())
    layer = fresh.uv_layers.new(name="UVMap")
    layer.uv.foreach_set("vector", uv.ravel())
    fresh.materials.append(obj.active_material)
    obj.data = fresh
    active(obj)
    decimate = obj.modifiers.new("Exterior triangle budget", "DECIMATE")
    decimate.ratio = 1130 / len(faces)
    decimate.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=decimate.name)
    inspection = json.loads((HERE / "source_inspection.json").read_text())
    inspection.pop("components", None)
    inspection.pop("boundary", None)
    inspection.update(welded_source_vertices=len(coordinates),
                      exterior_triangles=len(obj.data.polygons), **topology(obj.data))
    write_json("source_inspection.json", inspection)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "shorts_exterior_working.blend"), compress=True)


EXTERIOR = HERE / "shorts_exterior_working.blend"
GLB = HERE / "shorts_v1.glb"
BLEND = HERE / "shorts_v1.blend"
BANKS = {
    "shared": (PARTS / "body-fix/motion_fixed.glb", ("walk", "run", "wave", "jump", "idle", "nod", "dance")),
    "sit": (PARTS / "actions-fix/actions_fixed.glb", ("sit_down", "sit_idle", "stand_up", "hold_item")),
    "carry": (PARTS / "actions-hold2/hold_actions.glb", ("hold_box", "hold_bag", "take_item")),
}
REFERENCE = PARTS / "generated3/bottom-03-shorts-tpose.png"
SHA = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
JEANS = HERE.parents[1] / "jeans"
THICKNESS = .00055
FLOOR, CAP = .0005, .030


def helpers():
    return (runpy.run_path(str(JEANS / "fit_jeans.py")),
            runpy.run_path(str(JEANS / "round2/fit_jeans_r2.py")))


def load_actions(scene):
    results = {}
    for key, (path, clips) in BANKS.items():
        if key != "shared":
            scene.render.fps, scene.render.fps_base = 30, 1
        objects, actions = set(scene.objects), set(bpy.data.actions)
        bpy.ops.import_scene.gltf(filepath=str(path))
        imported = set(bpy.data.actions) - actions
        for name in clips:
            action, = [a for a in imported if a.name == name or a.name.startswith(name + ".")]
            assert action.slots
            results[name] = action
        for obj in set(scene.objects) - objects:
            bpy.data.objects.remove(obj, do_unlink=True)
    return results


def half_frames(first, last):
    first, last = round(float(first), 5), round(float(last), 5)
    return sorted({first, last, *(i / 2 for i in range(math.ceil(2 * first), math.floor(2 * last) + 1))})


def set_pose(scene, arm, action, frame):
    data = arm.animation_data_create()
    data.use_nla = False
    if data.action != action or action is None:
        data.action = None
        for bone in arm.pose.bones:
            bone.matrix_basis.identity()
        if action is not None:
            data.action = action
            data.action_slot = action.slots[0]
    scene.frame_set(math.floor(frame), subframe=frame % 1)
    bpy.context.view_layer.update()


def cache_motion(scene, arm, body, actions, api):
    bones = tuple(arm.pose.bones)
    modes = tuple(bone.rotation_mode for bone in bones)
    inverse = [bone.bone.matrix_local.inverted() for bone in bones]
    samples, matrices = [], []
    sequence = [("rest", 1., None)]
    sequence.extend((name, frame, action) for name, action in actions.items()
                    for frame in half_frames(*action.frame_range))
    assert np.allclose(np.asarray(arm.matrix_world), np.eye(4), atol=1e-6)
    for name, frame, action in sequence:
        set_pose(scene, arm, action, frame)
        coords, faces = api["evaluated_arrays"](body, bpy.context.evaluated_depsgraph_get())
        samples.append((name, frame, api["tree_from"](coords, faces), coords, faces))
        matrices.append(np.array([b.matrix @ bind for b, bind in zip(bones, inverse)])[:, :3])
    assert tuple(bone.rotation_mode for bone in bones) == modes
    print("Cached", len(samples), "poses", flush=True)
    return samples, np.asarray(matrices, dtype=np.float32)


def prepare_exterior(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if e.is_wire], context="EDGES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_edges], context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    assert all(edge.is_manifold or edge.is_boundary for edge in bm.edges)
    assert all(sum(e.is_boundary for e in v.link_edges) in (0, 2) for v in bm.verts)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    points, faces = mesh_data(obj.data)
    assert len(faces) == len(obj.data.polygons)
    uv = np.empty(len(obj.data.loops) * 2, dtype=np.float32)
    obj.data.uv_layers.active.uv.foreach_get("vector", uv)
    uv = uv.reshape(-1, 3, 2)
    boundary = {}
    for face_id, face in enumerate(faces):
        for corner in range(3):
            nxt = (corner + 1) % 3
            key = tuple(sorted((face[corner], face[nxt])))
            if key in boundary:
                del boundary[key]
            else:
                boundary[key] = (face[corner], face[nxt], uv[face_id, corner], uv[face_id, nxt])
    return points, faces, uv, list(boundary.values())


def align(source, tree, graph, api):
    x, y, z = source.T
    points = source.copy()
    smooth = api["smoothstep"]
    points[:, 2] = np.interp(z, [.274, .282, .306, .324, .352, .385, .395],
                            [.258, .267, .292, .309, .361, .412, .420])
    points[:, 0] = 1.213 * (x + .00055) + .00073
    # Center independently between the leg sleeves and the waist. The
    # segmentation keeps a low, closed saddle just below the body crotch.
    points[:, 1] = y * np.interp(z, [.274, .303, .320, .357, .392], [1.27, 1.14, 1.13, 1.145, 1.15])
    points[:, 1] += np.interp(z, [.274, .310, .392], [.027, .019, .019])
    x, y, z = points.T
    leg = 1 - smooth(.29, .319, z)
    medial = 1 - smooth(.014, .060, abs(x - .00073))
    # Preserve enough space for both facing hem walls in the narrow thigh gap.
    points[:, 0] += np.sign(x - .00073) * .0055 * medial * leg
    for _ in range(10):
        d, _, n, _ = api["nearest"](tree, points)
        goal = .0068 + .0025 * leg * (1 - medial)
        displacement = n * (np.maximum(0, goal - d) - np.maximum(0, d - .022))[:, None]
        points += .75 * displacement + .25 * api["average"](displacement, graph)
    return points


def source_weights(points, body, bone_names, tree, graph, api, motion_api):
    weights = motion_api["body_weights"](points, body, bone_names, tree)
    z = points[:, 2]
    allowance = (.12 + .24 * np.exp(-((z - .321) / .032) ** 2))[:, None]
    for _ in range(4):
        weights += allowance * (api["average"](weights, graph) - weights)
    return api["limit_weights"](weights)


def shell_arrays(points, faces, boundary):
    n = len(points)
    tri = points[faces]
    weighted = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    normal = np.zeros_like(points)
    for corner in range(3):
        np.add.at(normal, faces[:, corner], weighted)
    normal /= np.linalg.norm(normal, axis=1, keepdims=True).clip(1e-9)
    inner = points - THICKNESS * normal
    rims = [(b, a, a + n, b + n) for a, b, *_ in boundary]
    rim_triangles = [(a, b, c) for a, b, c, _ in rims] + [(a, c, d) for a, _, c, d in rims]
    return np.vstack((points, inner)), np.vstack((faces, faces[:, ::-1] + n, rim_triangles)).astype(np.int32)


def mesh_with_shell(obj, points, faces, uv, boundary, coordinates=None):
    coords, topology_faces = shell_arrays(points, faces, boundary)
    if coordinates is not None:
        coords = coordinates
    mesh = bpy.data.meshes.new("Plain_Shorts_Shell")
    mesh.from_pydata(coords.tolist(), [], topology_faces.tolist())
    rim_uv_1 = [(v, u, u) for _, _, u, v in boundary]
    rim_uv_2 = [(v, u, v) for _, _, u, v in boundary]
    lining_uv = np.concatenate((uv[:, ::-1], rim_uv_1, rim_uv_2))
    lining_uv = np.array((.122, .925), dtype=np.float32) + .032 * (lining_uv - .5)
    mapped = np.concatenate((uv, lining_uv))
    layer = mesh.uv_layers.new(name="UVMap")
    layer.uv.foreach_set("vector", mapped.ravel())
    mesh.materials.append(obj.active_material)
    for face in mesh.polygons:
        face.use_smooth = True
    mesh.update()
    return mesh


def summarize(samples, distances, pairs):
    report = {}
    for clip in dict.fromkeys(s[0] for s in samples):
        idx = [i for i, s in enumerate(samples) if s[0] == clip]
        d = distances[idx]
        row, vertex = np.unravel_index(d.argmin(), d.shape)
        report[clip] = dict(samples=len(idx), inside=int((d < 0).sum(axis=1).max()),
                            pairs=int(pairs[idx].max()), min_m=float(d.min()),
                            frame=samples[idx[row]][1], vertex=int(vertex))
    return report


def skin_export(scene, arm, body, obj, points, faces, uv, edges, names, weights, api, coordinates=None):
    set_pose(scene, arm, None, 1)
    obj.data = mesh_with_shell(obj, points, faces, uv, edges, coordinates)
    obj.name = "Plain_Shorts"
    material = obj.active_material
    material.name = "Studio Plain Shorts"
    bsdf = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    base = bsdf.inputs["Base Color"].links[0].from_node
    for node in list(material.node_tree.nodes):
        if node.type in {"TEX_IMAGE", "NORMAL_MAP", "SEPARATE_COLOR"} and node != base:
            material.node_tree.nodes.remove(node)
    bsdf.inputs["Roughness"].default_value = .84
    bsdf.inputs["Metallic"].default_value = 0
    material.use_backface_culling = True
    api["write_weights"](obj, names, np.vstack((weights, weights)))
    assert len(obj.data.polygons) <= 3000
    arm.animation_data_clear()
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    for other in list(scene.objects):
        if other not in {arm, body, obj}:
            bpy.data.objects.remove(other, do_unlink=True)
    obj.modifiers.clear()
    obj.modifiers.new("Master Skin", "ARMATURE").object = arm
    obj.parent = arm
    body.hide_render = True
    body.hide_set(True)
    active(obj)
    arm.select_set(True)
    obj.parent = None
    bpy.ops.export_scene.gltf(filepath=str(GLB), export_format="GLB", use_selection=True,
                              export_animations=False, export_all_influences=False)
    obj.parent = arm
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True)


def fit():
    api, motion = helpers()
    bpy.ops.wm.open_mainfile(filepath=str(EXTERIOR), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    body, arm, obj = (scene.objects[n] for n in ("Base_Body", "Armature", "Studio_Shorts"))
    body.hide_set(False)
    for other in scene.objects:
        if other not in {body, arm, obj}:
            other.hide_viewport = other.hide_render = True
    names = [bone.name for bone in arm.pose.bones]
    actions = load_actions(scene)
    geometry = runpy.run_path(str(HERE / "polish_geometry.py"))
    geometry["edge_cleanup"](obj)
    original, faces, uv, edges = prepare_exterior(obj)
    graph = api["adjacency"](obj.data)
    samples, transforms = cache_motion(scene, arm, body, actions, api)
    tree = samples[0][2]
    points = align(original, tree, graph, api)
    points = geometry["relax"](points, obj.data, tree, api)
    weights = source_weights(points, body, names, tree, graph, api, motion)
    origin = points.copy()
    resume = "--resume" in sys.argv
    if resume:
        state = np.load(HERE / ".fit_state.npz")
        points, weights, origin = (state[key] for key in ("points", "weights", "origin"))
        assert len(points) == len(obj.data.vertices)
    n = len(points)

    def evaluate(p, w, margin):
        shell, tris = shell_arrays(p, faces, edges)
        skin = api["pose_matrices"](transforms, w)
        posed = api["skin_positions"](shell, np.concatenate((skin, skin), axis=1))
        d, pairs, hits, planes = motion["scan"](posed, tris, samples, margin=margin)
        return d, pairs, [(row, ids % n, normals, values, factors)
                          for row, ids, normals, values, factors in planes], skin

    def grade(result):
        d, pairs = result[:2]
        return (float((np.maximum(0, .00065 - d) * 1000).sum()) * 2.5 + pairs.sum() +
                float(np.maximum(0, d[0] - .02985).sum()) * 10000,
                float(d.min()))

    def passed(result):
        d, pairs = result[:2]
        return d.min() >= .00063 and d[0].max() <= .02985 and not pairs.any()

    coupled = runpy.run_path(str(HERE / "contact_solve.py"))["proposal"]
    past = HERE / "fit_history.json"
    history = json.loads(past.read_text())["iterations"] if resume and past.exists() else []
    margin = .00145
    result = evaluate(points, weights, margin)

    def log(label, data):
        report = summarize(samples, data[0], data[1])
        print(label, grade(data), "rest max", float(data[0][0].max()), report, flush=True)
        history.append(dict(stage=label, score=grade(data), rest_max_m=float(data[0][0].max()), results=report))

    log("Resume" if resume else "Master transfer", result)
    for step in range(0 if resume else 8):
        if passed(result):
            break
        d, pairs, planes, skin = result
        columns = motion["skin_columns"](weights, names, points)
        if step < 5:
            p, w = motion["fit_step"](points, origin, weights, columns, skin, transforms, planes,
                                       graph, tree, margin, step > 0)
        else:
            shell, triangles = shell_arrays(points, faces, edges)
            posed = api["skin_positions"](shell, np.concatenate((skin, skin), axis=1))
            p, w = coupled(points, weights, shell, triangles, posed, skin, transforms,
                           samples, graph, d, pairs, api, motion, columns, margin,
                           weight_scale=.055 if step % 2 else .13)
            p = motion["correct_rest"](p, origin, tree, .0014)
        bounded = motion["rest_guard"](points, p, faces, tree) if not pairs[0] else p
        for scale in (1., .55, .25):
            pp = points + scale * (bounded - points)
            ww = api["limit_weights"](weights + scale * (w - weights))
            candidate = evaluate(pp, ww, margin)
            log(f"Bake {step + 1} x{scale}", candidate)
            if grade(candidate)[0] < grade(result)[0] or passed(candidate):
                points, weights, result = pp, ww, candidate
                np.savez_compressed(HERE / ".fit_state.npz", points=points, weights=weights, origin=origin)
                break
        else:
            if step >= 11:
                break
    if not passed(result) and "--contact" not in sys.argv:
        x, y, z = points.T
        front = api["smoothstep"](.045, .080, -y) * np.exp(-((z - .328) / .027) ** 2)
        front *= api["smoothstep"](.006, .030, abs(x))
        for offset in (.0025, .0045, .0065):
            p = points.copy()
            p[:, 1] -= offset * front
            candidate = evaluate(p, weights, margin)
            log(f"Anterior thigh room {1000 * offset:g} mm", candidate)
            if passed(candidate):
                points, result = p, candidate
                break
            if grade(candidate)[0] < grade(result)[0]:
                points, result = p, candidate
    if not passed(result):
        def region(center, inner, outer):
            distance = np.linalg.norm(points - np.asarray(center), axis=1)
            return (1 - api["smoothstep"](inner, outer, distance))[:, None]

        sweep = region((.120, -.061, .321), .044, .071)
        seat = region((.082, .064, .370), .025, .069)
        direction = sweep * (-.00140, .00080, -.00020) + seat * (.00080, .00210, 0)
        base_points = points.copy()
        for scale in (1., .60, 1.55):
            p = base_points + scale * direction
            candidate = evaluate(p, weights, margin)
            log(f"Left side contact polish x{scale:g}", candidate)
            if grade(candidate)[0] < grade(result)[0]:
                points, result = p, candidate
            if passed(candidate):
                break
    log("Selected", result)
    skin_export(scene, arm, body, obj, points, faces, uv, edges, names, weights, api)
    write_json("fit_history.json", dict(source_sha256=SHA(SOURCE), glb_sha256=SHA(GLB),
               shell_thickness_m=THICKNESS, iterations=history))
    np.savez_compressed(HERE / ".fit_state.npz", points=points, weights=weights, origin=origin)


if __name__ == "__main__":
    if "--stage" in sys.argv:
        stage()
    elif "--restore-surface" in sys.argv:
        restore_surface()
    else:
        fit()
