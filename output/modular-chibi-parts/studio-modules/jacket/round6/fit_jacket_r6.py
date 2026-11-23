"""Blender 5.1 fitter for the Round 3 jacket and the three corrected action banks."""

import hashlib
import json
import math
from pathlib import Path
import runpy
import sys

import bmesh
import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PARTS = HERE.parents[2]
WORK = HERE / ".runtime"
SOURCE = HERE.parent / "round3/jacket_v3.glb"
MASTER = PARTS / "master/GJH_Chibi_Master_rigged.blend"
MOTION = PARTS / "body-fix/motion_fixed.glb"
BANKS = (
    (MOTION, ("walk","run","wave","jump","idle","nod","dance")),
    (PARTS / "actions-fix/actions_fixed.glb", ("sit_down","sit_idle","stand_up","hold_item")),
    (PARTS / "actions-hold2/hold_actions.glb", ("hold_box","hold_bag","take_item")),
)
CLIPS = tuple(clip for _, names in BANKS for clip in names)
GLB = HERE / "jacket_v6.glb"
BLEND = HERE / "jacket_v6.blend"
FLOOR, MARGIN, CAP = .0005, .0015, .03
LIMIT = 6000

R2 = runpy.run_path(str(HERE.parent / "round2/fit_jacket_r2.py"))
API = R2["API"]
API["CLIPS"] = CLIPS
R2["summary"].__globals__["CLIPS"] = CLIPS
mesh_points, mesh_faces = API["mesh_points"], API["mesh_faces"]
write_weights, update_points = API["write_weights"], API["update_points"]
read_weights = R2["read_weights"]
limit_weights, neighbors, average = API["limit_weights"], API["neighbors"], API["average"]
nearest = API["nearest"]
set_pose = API["set_pose"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    stage = path.with_suffix(".stage")
    stage.write_text(json.dumps(value, indent=2) + "\n")
    stage.replace(path)


def setup(source):
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body = scene.objects["Armature"], scene.objects["Base_Body"]
    jacket, imported = API["import_mesh"](source)
    world = jacket.matrix_world.copy()
    jacket.parent = arm
    jacket.matrix_world = world
    jacket.modifiers.clear()
    jacket.modifiers.new("Master skin", "ARMATURE").object = arm
    for obj in imported:
        if obj != jacket:
            bpy.data.objects.remove(obj, do_unlink=True)
    jacket.name = "Jacket_Bomber"
    assert np.allclose(jacket.matrix_world, np.eye(4), atol=1e-6)
    assert np.allclose(arm.matrix_world, np.eye(4), atol=1e-6)
    data = arm.animation_data_create()
    data.action = None
    data.use_nla = False
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    return scene, arm, body, jacket


def import_actions(scene):
    previous = set()
    for path, names in BANKS:
        if path != MOTION:
            scene.render.fps, scene.render.fps_base = 30, 1
        objects, actions = set(scene.objects), set(bpy.data.actions)
        bpy.ops.import_scene.gltf(filepath=str(path))
        added = {action.name: action for action in set(bpy.data.actions) - actions}
        assert set(added) == set(names), (path, sorted(added), names)
        for obj in set(scene.objects) - objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        previous |= set(added)
    assert previous == set(CLIPS)


def half_frames(first, last):
    first, last = round(float(first), 5), round(float(last), 5)
    return sorted({first, last, *(i / 2 for i in range(math.ceil(first * 2), math.floor(last * 2) + 1))})


def pose_frames():
    yield "rest", 1.
    for clip in CLIPS:
        for frame in half_frames(*bpy.data.actions[clip].frame_range):
            yield clip, frame


def evaluated_points(obj):
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mat = np.asarray(ev.matrix_world, dtype=np.float32)
    return mesh_points(ev.data) @ mat[:3, :3].T + mat[:3, 3]


def cache_motion(scene, arm, body):
    bones = tuple(arm.pose.bones)
    memo = WORK / ("poses_" + "".join(sha(path)[:8] for path in (MASTER, *(b[0] for b in BANKS))) + ".npz")
    if memo.is_file():
        with np.load(memo, allow_pickle=False) as data:
            frames = list(zip(data["clips"].tolist(), data["frames"].tolist()))
            xyz, faces, transforms = (data[key] for key in ("xyz", "faces", "transforms"))
        assert len(frames) > 824 and {clip for clip, _ in frames} == {"rest", *CLIPS}
    else:
        import_actions(scene)
        frames = list(pose_frames())
        modes = tuple(b.rotation_mode for b in bones)
        inverses = [bone.bone.matrix_local.inverted() for bone in bones]
        xyz, transforms = [], []
        for clip, frame in frames:
            set_pose(scene, arm, clip, frame)
            xyz.append(evaluated_points(body))
            transforms.append([np.asarray(bone.matrix @ inv)[:3] for bone, inv in zip(bones, inverses)])
        assert modes == tuple(b.rotation_mode for b in bones)
        faces, xyz, transforms = mesh_faces(body.data), np.asarray(xyz), np.asarray(transforms, dtype=np.float32)
        np.savez(memo, clips=[clip for clip, _ in frames], frames=[f for _, f in frames],
                 xyz=xyz, faces=faces, transforms=transforms)
        set_pose(scene, arm, "rest", 1.)
    polys = faces.tolist()
    poses = [API["Pose"](clip, frame, BVHTree.FromPolygons(vertices.tolist(), polys, all_triangles=True))
             for (clip, frame), vertices in zip(frames, xyz)]
    print("POSES", len(poses), flush=True)
    return poses, transforms


def boundary_components(mesh):
    open_edges = {edge for edge in mesh.edges if edge.is_boundary}
    components = []
    while open_edges:
        pending = [open_edges.pop()]
        component = set(pending)
        while pending:
            for vertex in pending.pop().verts:
                adjacent = {edge for edge in vertex.link_edges if edge in open_edges}
                open_edges.difference_update(adjacent)
                component.update(adjacent)
                pending.extend(adjacent)
        components.append(component)
    return components


def weld(jacket):
    mesh = bmesh.new()
    mesh.from_mesh(jacket.data)
    mesh.verts.ensure_lookup_table()
    bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=.000012)
    bmesh.ops.recalc_face_normals(mesh, faces=list(mesh.faces))
    print("WELD", len(mesh.verts), len(mesh.faces), flush=True)
    for component in sorted(boundary_components(mesh), key=len, reverse=True):
        coords = np.asarray([v.co[:] for v in {v for e in component for v in e.verts}])
        print("BOUNDARY", len(component), coords.min(axis=0).round(5).tolist(),
              coords.max(axis=0).round(5).tolist(), flush=True)
    print("EDGE USE", {k: sum(len(e.link_faces)==k for e in mesh.edges) for k in (0,1,2,3,4)}, flush=True)
    print("DEGENERATE", sum(face.calc_area()<1e-10 for face in mesh.faces), flush=True)
    mesh.to_mesh(jacket.data)
    mesh.free()
    jacket.data.update()
    if jacket.data.has_custom_normals:
        bpy.context.view_layer.objects.active = jacket
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    for face in jacket.data.polygons:
        face.use_smooth = True


def summary(poses, distances, pairs):
    report = API["clip_results"](poses, distances, pairs)
    for name, row in report.items():
        print("RESULT", name, row, flush=True)
    return report


def diagnose(points, weights, faces, poses, transforms, label):
    result = R2["scan"](points, weights, transforms, poses, faces, collect=True)
    distances, _, pairs, contacts = result[:4]
    report = summary(poses, distances, pairs)
    worse = distances.min(axis=0)
    for v in np.argsort(worse)[:20]:
        frame = poses[distances[:, v].argmin()]
        print("VERTEX", int(v), frame.clip, frame.frame, float(worse[v]), points[v].tolist(), flush=True)
    print("FACES", len(np.unique(np.concatenate([pairs[:,1] for _, pairs in contacts]))) if contacts else 0,
          "PAIRS", int(pairs.sum()), flush=True)
    write_json(WORK / f"{label}.json", report)
    return result


def probe():
    scene, arm, body, jacket = setup(SOURCE)
    print("SOURCE", len(jacket.data.vertices), len(mesh_faces(jacket.data)), "FPS", scene.render.fps, flush=True)
    weld(jacket)
    names = tuple(b.name for b in arm.pose.bones)
    poses, transforms = cache_motion(scene, arm, body)
    diagnose(mesh_points(jacket.data), read_weights(jacket, names), mesh_faces(jacket.data),
             poses, transforms, "baseline")


def fill_seams(jacket):
    """Repair split zipper edges and small punctures; retain the four garment rims."""
    mesh = bmesh.new()
    mesh.from_mesh(jacket.data)
    uv = mesh.loops.layers.uv.active
    original = {face: [loop[uv].uv.copy() for loop in face.loops] for face in mesh.faces}
    # The zipper trim has several stacked faces sharing one edge. Retain the
    # opposing pair with the most continuous normals and remove the flap.
    for edge in list(mesh.edges):
        faces = list(edge.link_faces)
        if len(faces) <= 2:
            continue
        def continuity(pair):
            a, b = pair
            adjacent = [next(loop for loop in face.loops if loop.edge == edge) for face in pair]
            return 2 * (adjacent[0].vert != adjacent[1].vert) + a.normal.dot(b.normal)
        from itertools import combinations
        keep = max(combinations(faces, 2), key=continuity)
        for face in faces:
            if face not in keep:
                mesh.faces.remove(face)
    wire = [edge for edge in mesh.edges if not edge.link_faces]
    bmesh.ops.delete(mesh, geom=wire, context="EDGES")
    islands = sorted(boundary_components(mesh), key=len, reverse=True)
    assert len(islands) >= 4
    filled = []
    for component in islands[4:]:
        neighbors_uv = {}
        for edge in component:
            for loop in edge.link_loops:
                neighbors_uv.setdefault(loop.vert, []).append(loop[uv].uv.copy())
                nxt = loop.link_loop_next
                neighbors_uv.setdefault(nxt.vert, []).append(nxt[uv].uv.copy())
        if any(sum(edge in component for edge in vertex.link_edges) != 2 for vertex in neighbors_uv):
            # Split a boundary that touches itself at a single vertex into cycles.
            cycles, todo = [], set(component)
            while todo:
                edge = min(todo, key=lambda e: e.index)
                start, current = edge.verts
                path, stack = [edge], [start, current]
                todo.remove(edge)
                while True:
                    options = [edge for edge in stack[-1].link_edges if edge in todo]
                    if not options:
                        break
                    edge = min(options, key=lambda e: e.index)
                    todo.remove(edge)
                    end = edge.other_vert(stack[-1])
                    if end in stack:
                        start_index = stack.index(end)
                        cycles.append(path[start_index:] + [edge])
                        path, stack = path[:start_index], stack[:start_index + 1]
                    else:
                        path.append(edge)
                        stack.append(end)
        else:
            cycles = [list(component)]
        for cycle in cycles:
            faces = bmesh.ops.holes_fill(mesh, edges=cycle, sides=0)["faces"]
            for face in faces:
                for loop in face.loops:
                    candidates = neighbors_uv[loop.vert]
                    loop[uv].uv = min(candidates, key=lambda p: sum((p-q).length_squared for q in candidates))
            filled.extend(faces)
    bmesh.ops.triangulate(mesh, faces=filled)
    bmesh.ops.recalc_face_normals(mesh, faces=list(mesh.faces))
    for face in mesh.faces:
        face.smooth = True
    counts = [len(c) for c in sorted(boundary_components(mesh), key=len, reverse=True)]
    print("REPAIR", "boundary edges in components", counts,
          "edges with >2 faces", sum(len(e.link_faces) > 2 for e in mesh.edges), flush=True)
    mesh.to_mesh(jacket.data)
    mesh.free()
    jacket.data.update()
    return counts


def smooth_cut(points, jacket, tree):
    """Reduce the modeled pocket openings and jagged fabric at the wrist and hem."""
    graph = neighbors(jacket.data)
    x, y, z = points.T
    def ease(v):
        t = np.clip(v, 0, 1)
        return t*t*(3-2*t)
    pocket = (ease((abs(x)-.016)/.024) * ease((.134-abs(x))/.029) *
              ease((z-.404)/.031) * ease((.550-z)/.050) * ease((-.016-y)/.055))
    sleeve = ease((abs(x)-.13)/.055) * ease((.270-abs(x))/.02)
    ribs = np.maximum(ease((.425-z)/.05), ease((abs(x)-.234)/.022))
    amount = np.maximum.reduce((.82*pocket, .24*sleeve, .37*ribs, np.full(len(x), .14)))
    anchor = points.copy()
    for _ in range(13):
        points += (amount[:,None] * (average(points, graph) - points)).astype(np.float32)
    relaxed = anchor + (points - anchor) * (.56 + .44*pocket[:,None])
    relaxed = R2["cap_rest"](relaxed, tree, lower=.0015)
    return relaxed.astype(np.float32)


def split_crossings(jacket, faces, points, weights, contacts):
    """Bisect long edges of intersecting triangles, with UV and skin interpolation."""
    mesh = bmesh.new()
    mesh.from_mesh(jacket.data)
    mesh.verts.ensure_lookup_table()
    for vert, point in zip(mesh.verts, points):
        vert.co = point
    layer = mesh.verts.layers.deform.verify()
    indices = {group.name: group.index for group in jacket.vertex_groups}
    joints = tuple(b.name for b in jacket.parent.pose.bones)
    columns = [indices.get(name) for name in joints]
    for vert, row in zip(mesh.verts, weights):
        vg = vert[layer]
        vg.clear()
        for i in np.flatnonzero(row):
            vg[columns[i]] = row[i]
    touched = np.unique(np.concatenate([pp[:,1] for _, pp in contacts])) if contacts else []
    edges = mesh.edges
    edge_by_key = {tuple(sorted(v.index for v in e.verts)): e for e in edges}
    chosen = set()
    budget = min((LIMIT - len(faces)) // 2 - 4, 160)
    lengths = []
    for face in faces[touched]:
        for a, b in zip(face, np.roll(face, -1)):
            edge = edge_by_key[tuple(sorted((a, b)))]
            if edge.calc_length() >= .0105:
                lengths.append(edge)
    for edge in sorted(set(lengths), key=lambda e: (-e.calc_length(), e.index))[:max(0,budget)]:
        chosen.add(edge)
    if chosen:
        bmesh.ops.subdivide_edges(mesh, edges=sorted(chosen, key=lambda e: e.index), cuts=1, use_grid_fill=True)
        bmesh.ops.triangulate(mesh, faces=[f for f in mesh.faces if len(f.verts) > 3])
        mesh.to_mesh(jacket.data)
        jacket.data.update()
    mesh.free()
    print("SUBDIVISION", len(chosen), "edges", len(mesh_faces(jacket.data)), "triangles", flush=True)
    return len(chosen)


def offset_requirements(measure, graph):
    """Pull worst sampled corrections into bind space and smooth with a floor."""
    signed, normals, _, _, witnesses, skin, _ = measure
    size = signed.shape[1]
    worst = signed.argmin(axis=0)
    vertex = np.arange(size)
    normal = normals[worst, vertex]
    requirement = np.clip(MARGIN - signed[worst, vertex], 0, CAP)
    a = skin[worst, vertex, :, :3]
    gradient = np.einsum("vi,vij->vj", normal, a)
    raw = gradient * (requirement / np.square(gradient).sum(axis=1).clip(.085))[:, None]
    # A deep face-only contact gets distributed among the incident corners.
    extra = np.zeros_like(raw)
    strength = np.zeros(size, np.float32)
    for frame, corners, bary, normals, distances in witnesses:
        pull = np.einsum("wi,wcij->wcj", normals, skin[frame, corners, :, :3])
        eff = (np.clip(MARGIN - distances, 0, CAP)[:, None] * bary)
        for c in range(3):
            weight = eff[:, c] * 1.6
            idx = corners[:, c]
            np.add.at(extra, idx, pull[:,c] * weight[:,None])
            np.add.at(strength, idx, weight)
        # Keeping the deepest face witness gives a displacement floor for mesh edges.
    displacement = raw + extra / np.maximum(1, strength/.002)[:, None]
    displacement = R2["limit_length"](displacement, CAP)
    displacement = R2["smooth_floor"](displacement, graph, passes=3)
    norm2 = np.square(gradient).sum(axis=1).clip(.085)
    shortfall = np.maximum(requirement - np.einsum("vi,vi->v", displacement, gradient), 0)
    return R2["limit_length"](displacement + gradient * (shortfall/norm2)[:,None], CAP)


def score(measure):
    distances, _, pairs = measure[:3]
    deficit = np.maximum(FLOOR + .00003 - distances, 0) * 1000
    return float(pairs.sum() + 4 * (distances < 0).sum() + 1.8 * np.square(deficit).sum())


def compare(points, weights, triangles, poses, transforms, measurement, choices):
    distances, _, counts = measurement[:3]
    selected = set(range(0, len(poses), 31))
    selected.add(0)
    for name in CLIPS:
        ids = np.asarray([i for i, pose in enumerate(poses) if pose.clip == name])
        selected.update(ids[np.argsort(distances[ids].min(axis=1))[:5]])
        selected.update(ids[np.argsort(counts[ids])[-5:]])
    rows = sorted(selected)
    test_poses, test_transforms = [poses[i] for i in rows], transforms[rows]
    rank = lambda p,w: score(R2["scan"](p,w,test_transforms,test_poses,triangles))
    best_score, best = rank(points,weights), (points,weights)
    scores = [best_score]
    for p,w in choices:
        value = rank(p,w)
        scores.append(value)
        if value < best_score:
            best_score, best = value, (p,w)
    print("PROPOSALS", [round(s, 2) for s in scores], flush=True)
    return best


def fit(iterations="8"):
    scene, arm, body, jacket = setup(SOURCE)
    weld(jacket)
    counts = fill_seams(jacket)
    names = tuple(b.name for b in arm.pose.bones)
    poses, transforms = cache_motion(scene, arm, body)
    rest = poses[0].tree
    points = smooth_cut(mesh_points(jacket.data), jacket, rest)
    weights = read_weights(jacket, names)
    weights = R2["smooth_weights"](jacket.data, points, weights, .12)
    weights = R2["smooth_weights"](jacket.data, points, weights, .10)
    write_weights(jacket, names, weights)
    triangles = mesh_faces(jacket.data)
    graph = neighbors(jacket.data)
    history, best = [], float("inf")
    for step in range(int(iterations) + 1):
        measurement = diagnose(points, weights, triangles, poses, transforms, f"fit_{step:02d}")
        value = score(measurement)
        history.append(dict(pass_index=step, score=value, triangles=len(triangles),
                            minimum=float(measurement[0].min()), pair_sum=int(measurement[2].sum())))
        write_json(HERE / "fit_history.json", history)
        if value < best:
            best = value
            write_weights(jacket, names, weights)
            update_points(jacket, points)
            bpy.context.preferences.filepaths.save_version = 0
            bpy.ops.wm.save_as_mainfile(filepath=str(WORK / "best.blend"))
        if value == 0 or step == int(iterations):
            break
        if step == 1 and split_crossings(jacket, triangles, points, weights, measurement[3]):
            points = mesh_points(jacket.data)
            weights = read_weights(jacket, names)
            triangles = mesh_faces(jacket.data)
            graph = neighbors(jacket.data)
            continue
        displacement = offset_requirements(measurement, graph)
        choices = []
        for scale in (1, .55, 1.47):
            candidate = points + displacement * scale
            candidate = R2["position_guard"](points, candidate, points, triangles, rest)
            choices.append((candidate, weights))
        points, weights = compare(points, weights, triangles, poses, transforms, measurement, choices)


def raster_uv(jacket, width, height, attributes=None):
    """Mark texel centers inside a UV triangle and optionally interpolate a mask."""
    jacket.data.calc_loop_triangles()
    uv = jacket.data.uv_layers.active.data
    coordinates = np.asarray([corner.uv[:] for corner in uv]) * [width, height] - .5
    interior = np.zeros((height, width), bool)
    sampled = np.zeros((height,width), np.float32)
    for tri in jacket.data.loop_triangles:
        a,b,c = coordinates[list(tri.loops)]
        u,v = b-a,c-a
        det = u[0]*v[1] - u[1]*v[0]
        if abs(det) < 1e-9:
            continue
        coords = np.array([a,b,c])
        xmin,ymin = np.maximum(np.ceil(coords.min(axis=0)).astype(int),0)
        xmax,ymax = np.minimum(np.floor(coords.max(axis=0)).astype(int),[width-1,height-1])
        dx,dy = np.meshgrid(np.arange(xmin,xmax+1)-a[0], np.arange(ymin,ymax+1)-a[1])
        s,t = (dx*v[1]-dy*v[0])/det, (u[0]*dy-u[1]*dx)/det
        found = (s>=-1e-7) & (t>=-1e-7) & (s+t<=1+1e-7)
        tile = np.s_[ymin:ymax+1,xmin:xmax+1]
        interior[tile] |= found
        if attributes is not None:
            p,q,r = attributes[list(tri.vertices)]
            values = p+(q-p)*s+(r-p)*t
            sampled[tile] = np.maximum(sampled[tile], np.where(found, values, 0))
    return interior, sampled


def pad_texture(pixels, covered, distance=8):
    """Extend UV chart colors into unused gutters without moving covered texels."""
    shifted = ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1))
    grown = covered.copy()
    for _ in range(distance):
        valid = grown.copy()
        for x,y in shifted:
            dy = slice(max(y,0),grown.shape[0] + min(y,0))
            sy = slice(max(-y,0),grown.shape[0] - max(y,0))
            dx = slice(max(x,0),grown.shape[1] + min(x,0))
            sx = slice(max(-x,0),grown.shape[1] - max(x,0))
            eligible = valid[sy,sx] & ~grown[dy,dx]
            pixels[dy,dx][eligible] = pixels[sy,sx][eligible]
            grown[dy,dx] |= eligible
    return int((grown & ~covered).sum())


def textures(jacket):
    settings = {"basecolor": (1024, "JPEG"), "normal": (640, "PNG"), "rm": (640, "PNG")}
    nodes = [node for node in jacket.active_material.node_tree.nodes if node.type == "TEX_IMAGE"]
    assert len(nodes)==3
    result = {}
    for node in nodes:
        source = node.image
        role = source.name.split("_")[-1].split(".")[0]
        side, fmt = settings[role]
        source.scale(side,side)
        covered, _ = raster_uv(jacket, side, side)
        pixels = np.empty(side*side*4, np.float32)
        source.pixels.foreach_get(pixels)
        pixels = pixels.reshape(side,side,4)
        pad = pad_texture(pixels, covered)
        pixels[...,3] = 1
        source.pixels.foreach_set(pixels.ravel())
        source.update()
        destination = WORK / (role + (".jpg" if fmt == "JPEG" else ".png"))
        source.file_format = fmt
        source.save(filepath=str(destination), quality=93)
        replacement = bpy.data.images.load(str(destination), check_existing=False)
        name = source.name
        source.name = name + ".seed"
        replacement.name = name
        replacement.colorspace_settings.name = source.colorspace_settings.name
        replacement.pack()
        node.image = replacement
        result[role] = dict(resolution=[side,side], format=fmt, bytes=destination.stat().st_size,
                            covered_texels=int(covered.sum()), padded_texels=pad)
    return result


def open_editable(path):
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body, jacket = (scene.objects[n] for n in ("Armature","Base_Body","Jacket_Bomber"))
    body.hide_set(False)
    body.hide_viewport = False
    data = arm.animation_data_create()
    data.action = None
    data.use_nla = False
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    return scene, arm, body, jacket


def export(source=None):
    scene, arm, body, jacket = open_editable(Path(source) if source else WORK / "best.blend")
    assert len(mesh_faces(jacket.data))<=LIMIT
    info = textures(jacket)
    write_json(HERE / "texture_padding.json", info)
    names = tuple(bone.name for bone in arm.pose.bones)
    exporter = R2["export"]
    exporter.__globals__.update(GLB=GLB, BLEND=BLEND)
    exporter(scene, arm, body, jacket, mesh_points(jacket.data), names, read_weights(jacket, names))


def audit_rest():
    scene, arm, body, jacket = setup(GLB)
    set_pose(scene, arm, "rest", 1.)
    faces = mesh_faces(jacket.data)
    points = evaluated_points(jacket)
    tree = BVHTree.FromPolygons(evaluated_points(body).tolist(), mesh_faces(body.data).tolist(), all_triangles=True)
    grid = np.asarray([(i, j, 14-i-j) for i in range(15) for j in range(15-i)]) / 14
    counts = dict(samples=0, below_minimum=0, over_cap=0, min_signed_m=1., max_euclidean_m=0.)
    for start in range(0,len(faces),128):
        batch = np.einsum("gc,fci->fgi",grid,points[faces[start:start+128]]).reshape(-1,3)
        signed, _, _, loc = nearest(tree, batch.tolist())
        distance = np.linalg.norm(batch - loc, axis=1)
        counts["samples"] += len(batch)
        counts["below_minimum"] += int((signed < FLOOR).sum())
        counts["over_cap"] += int((distance > CAP).sum())
        counts["min_signed_m"] = min(counts["min_signed_m"], float(signed.min()))
        counts["max_euclidean_m"] = max(counts["max_euclidean_m"], float(distance.max()))
    mesh = bmesh.new()
    mesh.from_mesh(jacket.data)
    bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=.000001)
    boundaries = sorted(boundary_components(mesh), key=len, reverse=True)
    counts.update(boundary_lengths=[len(component) for component in boundaries],
                  closed_boundary_loops=[all(sum(e in component for e in v.link_edges)==2
                                             for v in {v for e in component for v in e.verts})
                                         for component in boundaries],
                  branching_edges=sum(len(e.link_faces)>2 for e in mesh.edges),
                  degenerate_faces=sum(f.calc_area()<1e-10 for f in mesh.faces),
                  garment_sha256=sha(GLB), master_sha256=sha(MASTER))
    mesh.free()
    write_json(HERE / "rest_clearance.json", counts)
    print("REST",counts,flush=True)


def coupled_fit(points, weights, anatomy, graph, measure, transforms, strength):
    """Project averaged position and skin corrections across the contact constraints."""
    signed, normals, _, _, witnesses, skin, _ = measure
    count = len(points)
    # Keep the worst observations per vertex, including different pose directions.
    rows = np.argpartition(signed, min(len(signed)-1,23), axis=0)[:24]
    rr, vv = np.where(np.take_along_axis(signed,rows,axis=0)<MARGIN)
    rows = rows[rr,vv]
    cs = [np.repeat(vv[:,None],3,axis=1)]
    rr = [rows]
    bb = [np.broadcast_to([1.,0.,0.],(len(vv),3))]
    nn = [normals[rows,vv]]
    dd = [signed[rows,vv]]
    for row,corners,bary,normal,distance in witnesses:
        use = distance < MARGIN
        if use.any():
            cs.append(corners[use])
            rr.append(np.full(use.sum(),row))
            bb.append(bary[use])
            nn.append(normal[use])
            dd.append(distance[use])
    poly = np.concatenate(cs)
    if len(poly)==0:
        return points, weights
    rows = np.concatenate(rr)
    bary = np.concatenate(bb).astype(np.float32)
    normal = np.concatenate(nn)
    deficit = np.clip(MARGIN-np.concatenate(dd),0,CAP)
    # Thin temporal clusters so a long repeated idle does not overwhelm peaks.
    order = np.lexsort((-deficit,rows//4,poly[:,2],poly[:,1],poly[:,0]))
    lookup = np.column_stack((poly[order],rows[order]//4))
    take = order[np.r_[True,np.any(np.diff(lookup,axis=0),axis=1)]]
    rows,poly,bary,normal,deficit = (a[take] for a in (rows,poly,bary,normal,deficit))
    position_derivative = np.einsum("ki,kaji->kaj",normal,skin[rows[:,None],poly,:,:3].swapaxes(-1,-2))
    position_derivative *= bary[:,:,None]
    support = np.maximum(weights, .65 * anatomy)
    support = np.maximum(support,.42*average(weights,graph))
    indices = np.argsort(-support,axis=1,kind="stable")[:,:7]
    existing = np.take_along_axis(weights,indices,axis=1)
    weight_derivative = np.empty((*poly.shape,indices.shape[1]),dtype=np.float32)
    for corner in range(3):
        vert = poly[:,corner]
        matrix = transforms[rows[:,None],indices[vert]]
        world = np.einsum("nkij,nj->nki",matrix[:,:,:,:3],points[vert]) + matrix[:,:,:,3]
        direction = np.einsum("nki,ni->nk",world,normal)
        direction -= (direction*existing[vert]).sum(axis=1)[:,None]
        weight_derivative[:,corner] = direction*bary[:,corner,None]
    flat = poly.ravel()
    local = np.unique(poly)
    scale = .073 / max(strength,.01)
    gradients = np.concatenate((position_derivative,weight_derivative/scale),axis=2)
    gram = np.square(gradients).sum(axis=(1,2)).clip(.08)
    degree = np.bincount(flat,weights=bary.ravel(),minlength=count).clip(1)
    step = np.zeros((count, gradients.shape[2]), np.float32)
    raw = offset_requirements(measure,graph)
    step[:,:3] = raw*.72
    for i in range(48):
        residual = (deficit - np.einsum("nci,nci->n",gradients,step[poly])).clip(0)
        change = (residual / gram)[:,None,None] * gradients
        pooled = np.asarray([np.bincount(flat,weights=values.ravel(),minlength=count)
                             for values in change.transpose(2,0,1)]).T
        step[local] += (.80*pooled[local] / degree[local,None]).astype(np.float32)
        step[:,:3] = R2["limit_length"](step[:,:3],CAP)
        next_weights = (existing + step[:,3:]/scale).clip(0)
        next_weights /= next_weights.sum(axis=1,keepdims=True).clip(.0001)
        step[:,3:] = (next_weights-existing)*scale
        if i % 8 == 0:
            smooth = average(step[:,:3],graph)
            step[:,:3] += .045*(smooth-step[:,:3])
    out = np.zeros_like(weights)
    np.put_along_axis(out,indices,(existing+step[:,3:]/scale).clip(0),axis=1)
    out = limit_weights(out)
    return points + step[:,:3], out


def close_rifts(jacket):
    """Make a continuous fabric surface across the small non-manifold zipper gaps."""
    from itertools import combinations
    mesh = bmesh.new()
    mesh.from_mesh(jacket.data)
    mesh.verts.index_update()
    mesh.edges.index_update()
    uv = mesh.loops.layers.uv.active
    deform = mesh.verts.layers.deform.verify()
    removed, added = 0, 0
    for edge in list(mesh.edges):
        faces = list(edge.link_faces)
        if len(faces)<=2:
            continue
        def continuity(pair):
            a,b = pair
            la,lb = [next(loop for loop in f.loops if loop.edge==edge) for f in pair]
            return 8 * (la.vert != lb.vert) + a.normal.dot(b.normal)
        keep = max(combinations(faces,2),key=continuity)
        for face in faces:
            if face not in keep:
                mesh.faces.remove(face)
                removed += 1
    bmesh.ops.delete(mesh,geom=[e for e in mesh.edges if not e.link_faces],context="EDGES")
    bmesh.ops.delete(mesh,geom=[v for v in mesh.verts if not v.link_edges],context="VERTS")
    components = sorted(boundary_components(mesh), key=len,reverse=True)
    for component in components[4:]:
        pending = set(component)
        while pending:
            edge = min(pending,key=lambda e:e.index)
            start, end = edge.verts
            trail = [start,end]
            walked = [edge]
            pending.remove(edge)
            while True:
                options = [e for e in trail[-1].link_edges if e in pending]
                if not options:
                    break
                edge = min(options,key=lambda e:e.index)
                pending.remove(edge)
                end = edge.other_vert(trail[-1])
                if end in trail:
                    index = trail.index(end)
                    ring = trail[index:]
                    edges = walked[index:]+[edge]
                    trail,walked=trail[:index+1],walked[:index]
                    if len(ring)<3:
                        continue
                    from mathutils import Vector
                    middle = sum((v.co for v in ring),Vector())/len(ring)
                    center = mesh.verts.new(middle)
                    for v in ring:
                        for group,value in v[deform].items():
                            center[deform][group] = center[deform].get(group,0) + value/len(ring)
                    for e in edges:
                        prev,=e.link_loops
                        p,q = prev.vert, prev.link_loop_next.vert
                        face = mesh.faces.new((q,p,center))
                        source_edge = (prev[uv].uv + prev.link_loop_next[uv].uv)*.5
                        opposite = prev.link_loop_prev[uv].uv
                        for loop in face.loops:
                            loop[uv].uv = (prev[uv].uv if loop.vert==p else
                                           prev.link_loop_next[uv].uv if loop.vert==q else
                                           source_edge*.96 + opposite*.04)
                        face.smooth = True
                        added += 1
                    continue
                walked.append(edge)
                trail.append(end)
    bmesh.ops.recalc_face_normals(mesh,faces=list(mesh.faces))
    final = sorted(boundary_components(mesh),key=len,reverse=True)
    print("SEAM REPAIR",removed,added,[len(c) for c in final],
          sum(len(e.link_faces)>2 for e in mesh.edges),flush=True)
    mesh.to_mesh(jacket.data)
    mesh.free()
    jacket.data.update()


def fit_coupled(iterations="12", starting="source"):
    if starting=="source":
        scene,arm,body,jacket=setup(SOURCE)
        weld(jacket)
        close_rifts(jacket)
    else:
        scene,arm,body,jacket=open_editable(Path(starting))
    names = tuple(b.name for b in arm.pose.bones)
    poses, transforms = cache_motion(scene,arm,body)
    rest = poses[0].tree
    points = mesh_points(jacket.data)
    # Retain the proven Round 3 cut around the shoulders while softening the
    # sharp pocket and cuff features before motion fitting.
    if starting=="source":
        clean = smooth_cut(points.copy(),jacket,rest)
        x,y,z = points.T
        pocket = (z<.548)&(z>.411)&(abs(x)>.020)&(abs(x)<.131)&(y<-.033)
        amount = np.where(pocket,.80,.18)[:,None]
        points = R2["cap_rest"](points+amount*(clean-points),rest,lower=.0013)
    weights = read_weights(jacket,names)
    if starting=="source":
        weights = R2["smooth_weights"](jacket.data,points,weights,.045)
    write_weights(jacket,names,weights)
    anchor = points.copy()
    last = int(iterations)
    history=[]
    best=float("inf")
    for iteration in range(last+1):
        faces, graph = mesh_faces(jacket.data),neighbors(jacket.data)
        measure=diagnose(points,weights,faces,poses,transforms,f"coupled_{iteration:02}")
        value=score(measure)
        history.append(dict(iteration=iteration, score=value, triangles=len(faces),
                            minimum=float(measure[0].min()), pair_sum=int(measure[2].sum())))
        write_json(HERE/"coupled_history.json",history)
        if value<best:
            best=value
            write_weights(jacket,names,weights)
            update_points(jacket,points)
            bpy.context.preferences.filepaths.save_version=0
            bpy.ops.wm.save_as_mainfile(filepath=str(WORK/"coupled.blend"))
        if value==0 or iteration==last:
            break
        if iteration in (1,5) and split_crossings(jacket,faces,points,weights,measure[3]):
            points=mesh_points(jacket.data)
            weights=read_weights(jacket,names)
            anchor=points.copy()
            continue
        anatomy=R2["weights_near_body"](points,body,names,rest,weights)
        choices=[]
        raw=offset_requirements(measure,graph)
        for factor in (.65,1.):
            p=R2["cap_rest"](points+raw*factor,rest,lower=.00115)
            choices.append((p,weights))
        p,w=coupled_fit(points,weights,anatomy,graph,measure,transforms,1.8)
        p=R2["cap_rest"](p,rest,lower=.00115)
        options=[(p,w),((p+points)*.5,limit_weights((w+weights)*.5))]
        if iteration in (0,2):
            weight_mix = .35*np.clip((.22-abs(points[:,0]))/.115,0,1)[:,None]
            options.append((p,limit_weights(weights+weight_mix*(anatomy-weights))))
        points,weights=compare(points,weights,faces,poses,transforms,measure,choices+options)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    (globals()[args[0]] if args else probe)(*args[1:])
