"""Refine the round-2 Studio bomber against the corrected master actions in Blender."""
from pathlib import Path
import json
import runpy
import sys

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
ROUND2 = HERE.parent / "round2"
PARTS = HERE.parents[2]
GLB = HERE / "jacket_v3.glb"
BLEND = HERE / "jacket_v3.blend"
MOTION = PARTS / "body-fix" / "motion_fixed.glb"
MASTER = PARTS / "master" / "GJH_Chibi_Master_rigged.blend"
R2 = runpy.run_path(str(ROUND2 / "fit_jacket_r2.py"))["export"].__globals__
API = R2["API"]
CLIPS = API["CLIPS"]
CAP = .030
MARGIN = .002
GATE = .0005
API.update(HERE=HERE, WORK=HERE, GLB=GLB, BLEND=BLEND, MOTION=MOTION, MASTER=MASTER,
           TRIANGLE_LIMIT=8000)
R2.update(HERE=HERE, GLB=GLB, BLEND=BLEND, MOTION=MOTION)
points_of, triangles_of = API["mesh_points"], API["mesh_faces"]
write_json = API["write_json"]


def frames():
    yield "rest", 1.
    for clip in CLIPS:
        first, last = bpy.data.actions[clip].frame_range
        assert abs(first - round(first)) < 1e-4 and abs(last - round(last)) < 1e-4
        yield from ((clip, frame / 2) for frame in range(round(2 * first), round(2 * last) + 1))


API["frames"] = frames


def load_export(path):
    API["GLB"] = path
    scene, arm, body, jacket = API["reimport"]()
    API["GLB"] = GLB
    return scene, arm, body, jacket


def baseline():
    (HERE / ".runtime").mkdir(exist_ok=True)
    scene, arm, body, jacket = load_export(ROUND2 / "jacket_v2.glb")
    distances, hits, records = [], [], []
    coords = points_of(jacket.data)
    faces = triangles_of(jacket.data)
    zones = R2["fit_regions"](coords)
    for clip, frame in frames():
        API["set_pose"](scene, arm, clip, frame)
        dg = bpy.context.evaluated_depsgraph_get()
        bp, bf = API["evaluated_surface"](body, dg)
        gp, gf = API["evaluated_surface"](jacket, dg)
        tree = BVHTree.FromPolygons(bp, bf.tolist(), all_triangles=True)
        sd = np.asarray(R2["nearest_signed"](tree, gp))
        pairs = tree.overlap(BVHTree.FromPolygons(gp, gf.tolist(), all_triangles=True))
        distances.append(sd)
        hits.append(len(pairs))
        if pairs or sd.min() < GATE or clip == "rest":
            inside = np.flatnonzero(sd < 0)
            touched = np.unique(faces[[pair[1] for pair in pairs]]) if pairs else []
            worst = int(sd.argmin())
            records.append(dict(clip=clip, frame=frame, pairs=len(pairs), inside=len(inside),
                                mm=float(sd[worst] * 1000), point=coords[worst].tolist(),
                                zone=str(zones[worst]),
                                zones={str(z): int(c) for z, c in zip(*np.unique(zones[touched], return_counts=True))}))
    poses = [API["Pose"](clip, frame, None) for clip, frame in frames()]
    report = API["clip_results"](poses, np.asarray(distances), np.asarray(hits))
    print("BASELINE", report, flush=True)
    write_json(HERE / ".runtime" / "baseline.json", {"summary": report, "frames": records})


def source_scene():
    bpy.ops.wm.open_mainfile(filepath=str(ROUND2 / "jacket_v2.blend"), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body, jacket = (scene.objects[n] for n in ("Armature", "Base_Body", "Jacket_Bomber"))
    body.hide_set(False)
    body.hide_viewport = False
    assert np.allclose(arm.matrix_world, np.eye(4), atol=1e-6)
    assert np.allclose(jacket.matrix_world, np.eye(4), atol=1e-6)
    names = tuple(bone.name for bone in arm.pose.bones)
    assert len(names) == 65
    poses, transforms = API["cache_motion"](scene, arm, body)
    return scene, arm, body, jacket, names, poses, transforms


def merit(measure):
    distances, _, overlaps = measure[:3]
    under = np.maximum(GATE - distances, 0) * 1000
    return (int(overlaps.sum()) + 5 * int((distances < 0).sum()) +
            .5 * float(np.square(under).sum()) + 1500 * int(overlaps[0]))


def position_step(mesh, points, anchor, weights, poses, transforms, measurement, names, anatomical,
                  iteration):
    distance = measurement[0]
    adjacency = API["neighbors"](mesh)
    triangles = triangles_of(mesh)
    columns = R2["weight_columns"](anchor, weights, anatomical, adjacency, names)
    cuff = abs(anchor[:, 0]) > .241
    worst, mean, correction, depth = R2["deltas"](
        measurement, points, weights, transforms, poses, columns, cuff, adjacency)
    sample = R2["select_frames"](poses, distance, measurement[2], stride=21)
    sample_poses = [poses[i] for i in sample]
    sample_transforms = transforms[sample]
    rest = poses[0].tree
    score = lambda p, w: merit(R2["scan"](p, w, sample_transforms, sample_poses, triangles))
    proposals = [(score(points, weights), points, weights)]
    for shape, scale, weight_scale in ((worst, .80, 0), (mean, .77, 0), (mean, .66, .7),
                                        (mean, .33, 1.25)):
        delta = R2["limit_length"](shape * scale, .012)
        candidate = R2["position_guard"](points, points + delta, anchor, triangles, rest)
        w = weights.copy()
        local = np.take_along_axis(w, columns, axis=1)
        np.put_along_axis(w, columns, (local + np.clip(correction * weight_scale, -.13, .13)).clip(0, 1), axis=1)
        w = API["limit_weights"](w)
        proposals.append((score(candidate, w), candidate, w))
    if iteration >= 2:
        p, w = R2["local_step"](
            measurement, points, weights, anchor, anatomical, mesh, triangles, poses, transforms,
            columns, mean, worst, depth, iteration)
        p = R2["position_guard"](points, p, anchor, triangles, rest)
        proposals.append((score(p, w), p, w))
    ranks = [round(item[0], 2) for item in proposals]
    print("PROPOSALS", ranks, flush=True)
    return min(proposals, key=lambda item: item[0])[1:]


def build(last=6):
    (HERE / ".runtime").mkdir(exist_ok=True)
    scene, arm, body, jacket, names, poses, transforms = source_scene()
    points = points_of(jacket.data)
    anchor = points.copy()
    weights = R2["read_weights"](jacket, names)
    anatomical = R2["weights_near_body"](points, body, names, poses[0].tree, weights)
    for iteration in range(last + 1):
        triangles = triangles_of(jacket.data)
        measure = R2["scan"](points, weights, transforms, poses, triangles, collect=True)
        _, result = R2["summary"](f"ITERATION {iteration}", measure, poses)
        checkpoint = HERE / ".runtime" / f"fit_{iteration:02}.npz"
        np.savez(checkpoint, points=points, weights=weights, anchor=anchor, anatomical=anatomical)
        write_json(checkpoint.with_suffix(".json"), result)
        if iteration == last:
            return
        if iteration in (0, 3) and measure[3]:
            old = len(points)
            points, anchor, weights = R2["bind_contact_loft"](
                jacket, points, anchor, weights, triangles, measure[3], poses, transforms)
            if len(points) > old:
                API["update_points"](jacket, points)
                anatomical = R2["weights_near_body"](points, body, names, poses[0].tree, weights)
                continue
        points, weights = position_step(jacket.data, points, anchor, weights, poses, transforms,
                                         measure, names, anatomical, iteration)


def rebuild_checkpoint(jacket, poses, transforms, iteration):
    """Recreate the two contact subdivisions before loading a fit checkpoint."""
    for event in (0, 3):
        if event >= iteration:
            break
        with np.load(HERE / ".runtime" / f"fit_{event:02}.npz") as data:
            p, a, w = data["points"], data["anchor"], data["weights"]
        tri = triangles_of(jacket.data)
        m = R2["scan"](p, w, transforms, poses, tri)
        p, a, w = R2["bind_contact_loft"](jacket, p, a, w, tri, m[3], poses, transforms)
        API["update_points"](jacket, p)
    with np.load(HERE / ".runtime" / f"fit_{iteration:02}.npz") as data:
        p, a, w, anatomical = (data[k] for k in ("points", "anchor", "weights", "anatomical"))
    assert len(jacket.data.vertices) == len(p)
    return p, a, w, anatomical


def narrow_scan(points, weights, transforms, poses, triangles, body_geometry, pair_witnesses):
    """Use crossing segments and dense barycentrics for small face-only contacts."""
    measure = R2["scan"](points, weights, transforms, poses, triangles, collect=True)
    posed = measure[-1]
    exact = []
    for row, pairs in measure[3]:
        body_points, body_faces = body_geometry[row]
        f, bary = pair_witnesses(posed[row], triangles, body_points, body_faces, pairs[:, ::-1],
                                 dense=True)
        corners = triangles[f]
        candidates = np.einsum("nk,nki->ni", bary, posed[row, corners])
        sd, n = R2["signed_normals"](poses[row].tree, candidates.tolist())
        # Record the three deepest witnesses per face, in distinct
        # barycentric regions where a long triangle crosses twice.
        order = np.lexsort((sd, f))
        start = np.maximum.accumulate(np.where(np.r_[True, np.diff(f[order]) != 0],
                                                np.arange(len(order)), 0))
        keep = order[(np.arange(len(order)) - start < 3) & (sd[order] < MARGIN)]
        exact.append((row, corners[keep], bary[keep].astype(np.float32), n[keep], sd[keep]))
    return (*measure[:4], exact, *measure[5:])


def contact_options(points, weights, anchor, anatomical, mesh, triangles, measure, poses, transforms, names):
    """Optimize the implicated trajectories and face witnesses through coherent local edits."""
    d, normals, counts, _, contacts, skin, posed = measure
    rest = poses[0].tree
    links = API["neighbors"](mesh)
    mean_weight = API["average"](weights, links)
    mean_delta = API["average"](points - anchor, links)
    columns = R2["weight_columns"](anchor, weights, anatomical, links, names)
    incident = [[] for _ in points]
    for face in triangles:
        for v in face:
            incident[v].append(face)
    corner_patches = [[] for _ in points]
    severe = d.min(axis=0).copy()
    for k, (row, faces, bary, _, sd) in enumerate(contacts):
        rows, cols = np.where(bary > .08)
        for j, corner in zip(rows, cols):
            v = faces[j, corner]
            corner_patches[v].append((float(sd[j]), k, j, corner))
            severe[v] = min(severe[v], sd[j])
    active = np.flatnonzero(severe < MARGIN)
    active = active[np.argsort(severe[active])]
    newp, neww = points.copy(), weights.copy()
    groups = [np.asarray([i for i, pose in enumerate(poses) if pose.clip == name]) for name in CLIPS]
    axes = np.asarray([(x, y, z) for x in (-1., 0., 1.) for y in (-1., 0., 1.)
                      for z in (-1., 0., 1.) if x or y or z])
    axes /= np.linalg.norm(axes, axis=1)[:, None]
    changed = 0
    for v in active:
        vertex_d = d[:, v]
        witness = sorted(corner_patches[v])
        few = [witness[k] for k in np.linspace(0, len(witness) - 1, min(9, len(witness)), dtype=int)]
        few += witness[:12]
        for group in groups:
            relevant = [item for item in witness if group[0] <= contacts[item[1]][0] <= group[-1]]
            few += relevant[:3]
        focus = sorted(set(few))
        rows = sorted({0, *np.argsort(vertex_d)[:12],
                       *(i for group in groups for i in group[np.argsort(vertex_d[group])[:4]]),
                       *(contacts[k][0] for _, k, _, _ in focus)})
        rows = np.asarray(rows)
        p, w = newp[v], neww[v]
        n = int(vertex_d.argmin())
        world = normals[n, v] @ skin[n, v, :, :3]
        world /= max(1e-8, np.linalg.norm(world))
        rest_normal = np.asarray(rest.find_nearest(p)[1])
        scale = float(np.clip(MARGIN - severe[v], .002, .012))
        local_mean = anchor[v] + mean_delta[v]
        layout = np.vstack((np.zeros((1, 3)), axes * .0017, axes * (.55 * scale),
                            axes * scale, world * scale, -world * scale,
                            rest_normal * scale, -rest_normal * scale, (local_mean - p) * .4))
        pp = [p + move for move in layout]
        ww = [w] * len(pp)
        for target in (anatomical[v], mean_weight[v], *(np.eye(len(names))[bone] for bone in columns[v])):
            for amount in (.045, .14, .33, .64):
                alternate = (1 - amount) * w + amount * target
                for move in (np.zeros(3), .38 * scale * world, .38 * scale * rest_normal,
                             -.38 * scale * rest_normal):
                    pp.append(p + move)
                    ww.append(alternate)
        pp = np.asarray(pp, dtype=np.float32)
        ww = API["limit_weights"](np.asarray(ww, dtype=np.float32))
        if abs(anchor[v, 0]) > .241:
            pp[:, 0] = np.clip(pp[:, 0], anchor[v, 0] - .0017, anchor[v, 0] + .0017)
        valid = np.linalg.norm(pp - anchor[v], axis=1) < CAP
        candidates = np.flatnonzero(valid)
        p_test = pp[candidates]
        anchor_d = np.asarray([rest.find_nearest(q)[3] for q in p_test])
        keep = (anchor_d <= CAP - .000025) & (np.asarray(R2["nearest_signed"](rest, p_test)) >= .00055)
        candidates = np.unique(np.r_[0, candidates[keep]])
        pp, ww = pp[candidates], ww[candidates]
        tests = np.flatnonzero(ww.max(axis=0))
        motion = transforms[rows[:, None], tests]
        blend = ww[:, tests] @ motion.reshape(len(rows), len(tests), 12)
        blend = blend.reshape(len(rows), len(pp), 3, 4)
        xy = np.einsum("rkcj,kj->rkc", blend[..., :3], pp) + blend[..., 3]
        sd = np.array([R2["nearest_signed"](poses[row].tree, coords) for row, coords in zip(rows, xy)])
        vertex_gap = np.maximum(0, min(MARGIN, .0013) - sd) * 1000
        cost = .35 * np.square(vertex_gap).mean(axis=0) + 1.4 * np.square(vertex_gap).max(axis=0)
        if focus:
            witness_sd = []
            for _, k, j, corner in focus:
                frame, face, bary, _, _ = contacts[k]
                tri = face[j]
                b = bary[j]
                where = np.searchsorted(rows, frame)
                trajectory = posed[frame, tri]
                base = b @ trajectory
                surface = base + b[corner] * (xy[where] - trajectory[corner])
                witness_sd.append(R2["nearest_signed"](poses[frame].tree, surface))
            face_gap = np.maximum(0, .0014 - np.asarray(witness_sd)) * 1000
            cost += 2.4 * np.square(face_gap).mean(axis=0) + 1.8 * np.square(face_gap).max(axis=0)
        cost += .023 * np.square((pp - local_mean) * 1000).sum(axis=1)
        cost += .022 * np.square((pp - points[v]) * 1000).sum(axis=1)
        cost += 1.6 * np.square(ww - weights[v]).sum(axis=1) + 1.8 * np.square(ww - mean_weight[v]).sum(axis=1)
        adjacent = np.asarray(incident[v])
        original = newp[adjacent]
        old = np.cross(original[:, 1] - original[:, 0], original[:, 2] - original[:, 0])
        for k in np.argsort(cost, kind="stable")[:12]:
            if k == 0:
                break
            trial = original.copy()
            trial[adjacent == v] = pp[k]
            new = np.cross(trial[:, 1] - trial[:, 0], trial[:, 2] - trial[:, 0])
            if np.any(np.einsum("ij,ij->i", new, old) < .25 * np.square(old).sum(axis=1)):
                continue
            newp[v], neww[v] = pp[k], ww[k]
            used = np.flatnonzero(ww[k])
            mat = np.einsum("j,fjco->fco", ww[k, used], transforms[:, used])
            posed[:, v] = np.einsum("fcj,j->fc", mat[..., :3], pp[k]) + mat[..., 3]
            changed += 1
            break
    print("LOCAL CONTACT SOLVE", len(active), changed, flush=True)
    return newp, neww


def projected_patch(points, weights, anchor, anatomical, mesh, triangles, measure, poses, transforms, names):
    """Solve one shared displacement per vertex for the remaining face witnesses."""
    distances, normals, counts, _, contacts, skin, _ = measure
    coords, jacobians, gaps = [], [], []
    for row, corners, bary, normal, signed in contacts:
        gradient = np.einsum("ni,ncij->ncj", normal, skin[row, corners, :, :3])
        coords.append(corners)
        jacobians.append(bary[:, :, None] * gradient)
        gaps.append(np.full(len(corners), .0014, np.float32) - signed)
    for row in range(len(poses)):
        inside = np.flatnonzero(distances[row] < .0014)
        if not len(inside):
            continue
        gradient = np.einsum("ni,nij->nj", normals[row, inside], skin[row, inside, :, :3])
        coords.append(np.repeat(inside[:, None], 3, axis=1))
        jacobians.append(gradient[:, None, :] * np.array([1., 0., 0.])[None, :, None])
        gaps.append(np.minimum(.004, .0014 - distances[row, inside]))
    if not coords:
        return points, weights
    corners = np.concatenate(coords)
    gradient = np.concatenate(jacobians)
    need = np.concatenate(gaps)
    flat = corners.ravel()
    nearby = np.unique(flat)
    smooth = API["neighbors"](mesh)
    magnitude = np.bincount(flat, weights=np.linalg.norm(gradient, axis=2).ravel(), minlength=len(points))
    step = np.zeros_like(points)
    for _ in range(72):
        remaining = need - np.einsum("nci,nci->n", gradient, step[corners])
        update = gradient * np.maximum(remaining, 0)[:, None, None]
        pooled = np.column_stack([np.bincount(flat, weights=update[..., dim].ravel(), minlength=len(points))
                                  for dim in range(3)])
        step[nearby] += (.78 * pooled[nearby] / magnitude[nearby].clip(1)[:, None]).astype(step.dtype)
        average = API["average"](step, smooth)
        step[nearby] = .987 * step[nearby] + .013 * average[nearby]
        step = R2["limit_length"](step, .0048)
    trial_p, trial_w = contact_options(points, weights, anchor, anatomical, mesh, triangles,
                                       measure, poses, transforms, names)
    # Search the coupled patch and the per-vertex fit on the same evaluated poses.
    rows = R2["select_frames"](poses, distances, counts, stride=29)
    poses_subset = [poses[i] for i in rows]
    transforms_subset = transforms[rows]
    choices = [(points, weights), (trial_p, trial_w)]
    for blend in (.65, 1.25, 2.2):
        delta = R2["smooth_floor"](step * blend, smooth, passes=2)
        changed = R2["position_guard"](points, points + delta, anchor, triangles, poses[0].tree)
        choices.append((changed, weights))
        choices.append((changed + .45 * (trial_p - points),
                        API["limit_weights"](.55 * weights + .45 * trial_w)))
    ranks = [merit(R2["scan"](p, w, transforms_subset, poses_subset, triangles)) for p, w in choices]
    print("PROJECTED CONTACT", [round(k, 2) for k in ranks], flush=True)
    return choices[int(np.argmin(ranks))]


def refine():
    pair_witnesses = runpy.run_path(str(PARTS / "hoodie-fit-sol" / "round3" /
                                        "fit_hoodie_round3.py"))["pair_witnesses"]
    scene, arm, body, jacket, names, poses, transforms = source_scene()
    points, anchor, weights, anatomical = rebuild_checkpoint(jacket, poses, transforms, 6)
    body_geometry = []
    for pose in poses:
        API["set_pose"](scene, arm, pose.clip, pose.frame)
        xyz, faces = API["evaluated_surface"](body, bpy.context.evaluated_depsgraph_get())
        body_geometry.append((np.asarray(xyz, dtype=np.float32), faces))
    triangles = triangles_of(jacket.data)
    best = float("inf"), points, weights
    for iteration in range(6, 17):
        measure = narrow_scan(points, weights, transforms, poses, triangles, body_geometry, pair_witnesses)
        R2["summary"](f"REFINEMENT {iteration}", measure, poses)
        value = merit(measure)
        if value < best[0]:
            best = value, points.copy(), weights.copy()
        if iteration == 16 or (not measure[2].any() and measure[0].min() >= GATE):
            R2["export"](scene, arm, body, jacket, best[1], names, best[2])
            return
        process = contact_options if iteration < 13 else projected_patch
        points, weights = process(points, weights, anchor, anatomical, jacket.data, triangles,
                                  measure, poses, transforms, names)


def cap_surface(points, faces, tree):
    """Keep rest face interiors within the same clearance cap as vertices."""
    before = points.copy()
    grid = np.asarray([(i, j, 10 - i - j) for i in range(11) for j in range(11 - i)],
                      dtype=np.float32) / 10
    target = .02995
    for iteration in range(5):
        delta = np.zeros_like(points)
        count = np.zeros(len(points), dtype=np.float32)
        over = 0
        for offset in range(0, len(faces), 192):
            patch = faces[offset:offset + 192]
            xyz = np.einsum("kc,fci->fki", grid, points[patch])
            _, _, _, closest = API["nearest"](tree, xyz.reshape(-1, 3).tolist())
            difference = xyz - closest.reshape(xyz.shape)
            length = np.linalg.norm(difference, axis=2)
            sample = length.argmax(axis=1)
            row = np.arange(len(sample))
            excess = length[row, sample] - target
            active = excess > 0
            over += int((length > CAP).sum())
            bary = grid[sample[active]]
            correction = difference[row[active], sample[active]] * (
                excess[active] / length[row[active], sample[active]])[:, None]
            # Move all three corners along the local clearance gradient. A
            # corner near the inner clearance boundary receives less load.
            patch = patch[active]
            inner = np.asarray(R2["nearest_signed"](tree, points[patch].reshape(-1, 3))).reshape(-1, 3)
            distribute = bary * np.clip((inner - .001) / .008, 0, 1)
            distribute /= (distribute * bary).sum(axis=1).clip(.001)[:, None]
            for c in range(3):
                np.add.at(delta, patch[:, c], -distribute[:, c, None] * correction)
                np.add.at(count, patch[:, c], distribute[:, c] > 0)
        print("REST SURFACE", iteration, over, "grid samples over cap", flush=True)
        if not over:
            break
        points += .94 * delta / count.clip(1)[:, None]
    return points, float(np.linalg.norm(points - before, axis=1).max())


def finalize():
    """Bound the rest surface and keep the best collision candidate."""
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body, jacket = (scene.objects[n] for n in ("Armature", "Base_Body", "Jacket_Bomber"))
    body.hide_set(False)
    body.hide_viewport = False
    names = tuple(bone.name for bone in arm.pose.bones)
    poses, transforms = API["cache_motion"](scene, arm, body)
    points = points_of(jacket.data)
    weights = R2["read_weights"](jacket, names)
    faces = triangles_of(jacket.data)
    capped, change = cap_surface(points.copy(), faces, poses[0].tree)
    if change:
        before = R2["scan"](points, weights, transforms, poses, faces)
        after = R2["scan"](capped, weights, transforms, poses, faces)
        R2["summary"]("REST CAP BEFORE", before, poses)
        R2["summary"]("REST CAP AFTER", after, poses)
        if not after[2][0] and after[0][0].min() >= GATE and merit(after) <= merit(before) * 1.005:
            R2["export"](scene, arm, body, jacket, capped, names, weights)


def inspect():
    API["inspect_export"]()
    report_path = HERE / "export_check.json"
    report = json.loads(report_path.read_text())

    def material_payload(path):
        import struct
        data = path.read_bytes()
        length = struct.unpack_from("<I", data, 12)[0]
        document = json.loads(data[20:20 + length])
        payload = data[28 + length:]
        result = {}
        for image in document["images"]:
            view = document["bufferViews"][image["bufferView"]]
            start = view.get("byteOffset", 0)
            result[image["name"]] = payload[start:start + view["byteLength"]]
        return document["materials"], result

    previous = ROUND2 / "jacket_v2.glb"
    report["round2_glb_sha256"] = API["hash_file"](previous)
    prior_material, prior_images = material_payload(previous)
    new_material, new_images = material_payload(GLB)
    report["embedded_images_match_round2"] = prior_images == new_images
    report["material_definitions_match_round2"] = prior_material == new_material


    def uv_map(path):
        with bpy.data.libraries.load(str(path), link=False) as (source, target):
            assert "Jacket_Bomber" in source.objects
            target.objects = ["Jacket_Bomber"]
        garment, = target.objects
        layer = garment.data.uv_layers.active
        coordinates = {tuple(item.uv) for item in layer.data}
        return layer.name, len(layer.data), coordinates

    old_layer, old_loops, old_uv = uv_map(ROUND2 / "jacket_v2.blend")
    new_layer, new_loops, new_uv = uv_map(BLEND)
    report["uv"] = {"layer": new_layer, "same_layer_name": old_layer == new_layer,
                    "round2_loops": old_loops, "round3_loops": new_loops,
                    "round2_unique_coordinates": len(old_uv),
                    "round2_coordinates_retained": len(old_uv & new_uv)}
    triangle_path = HERE / "motion_check_tri.json"
    triangles = json.loads(triangle_path.read_text())
    assert triangles["glb_sha256"] == report["glb_sha256"]
    triangles["export"] = report
    write_json(triangle_path, triangles)
    report_path.unlink()


def render():
    report = json.loads((HERE / "motion_check.json").read_text())
    triangle = json.loads((HERE / "motion_check_tri.json").read_text())
    assert triangle["glb_sha256"] == report["glb_sha256"]
    source = {"glb_sha256": report["glb_sha256"], "clip_summary": {
        name: {"min_vertex_frame": triangle["results"][name]["peak_frame"] or entry["min_frame"]}
        for name, entry in report["results"].items()}}
    temporary = HERE / "dense_check.json"
    write_json(temporary, source)
    try:
        R2["render"]()
    finally:
        temporary.unlink()
    manifest = HERE / "_render_manifest.json"
    report["renders"] = json.loads(manifest.read_text())
    write_json(HERE / "motion_check.json", report)
    manifest.unlink()


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if args == ["--baseline"]:
        baseline()
    elif args == ["--finalize"]:
        finalize()
    elif args == ["--inspect"]:
        inspect()
    elif args == ["--renders"]:
        render()
    elif not args:
        build()
        refine()
        finalize()
    else:
        raise SystemExit("Use --baseline, --finalize, --inspect or --renders.")
