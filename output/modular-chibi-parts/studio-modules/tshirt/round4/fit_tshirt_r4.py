"""Refit the shipped Studio T-shirt against the two Blender 5 action banks."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import runpy
import sys
import time

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

OUT = Path(__file__).resolve().parent
R3 = OUT.parent / "round3"
PARTS = OUT.parents[2]
MASTER = PARTS / "master/GJH_Chibi_Master_rigged.blend"
FIXED = PARTS / "body-fix/motion_fixed.glb"
ACTIONS = PARTS / "actions-astra/actions.glb"
SOURCE = R3 / "tshirt_v3.glb"
EXPORT = OUT / "tshirt_v4.glb"
LEGACY = ("walk", "run", "wave", "jump", "idle", "nod", "dance")
ADDED = ("sit_down", "sit_idle", "stand_up", "hold_item")
CLIPS = LEGACY + ADDED
TARGET, MARGIN, CAP = .0005, .002, .030

PREVIOUS = runpy.run_path(str(R3 / "fit_tshirt_r3.py"))
R2, PRIOR, SHARED = (PREVIOUS[name] for name in ("ROUND2", "PRIOR", "SHARED"))
SHARED.update(OUT=OUT, NAME="tshirt_v4", GLB=EXPORT, TRIANGLE_LIMIT=8000, CLIPS=CLIPS)
R2["choose_rows"].__globals__["CLIPS"] = CLIPS
geometry, faces_of, coords = (PRIOR[name] for name in ("geometry", "triangles", "coordinates"))
skin, signed, report_scan = PRIOR["skin"], PRIOR["signed"], PREVIOUS["report_scan"]
stats, write_json, digest = PRIOR["stats"], PRIOR["write_json"], PREVIOUS["digest"]
limit_weights, mean = PRIOR["limit_weights"], PRIOR["mean_neighbors"]


def load_clips(scene):
    for path, names, fps in ((FIXED, LEGACY, 24), (ACTIONS, ADDED, 30)):
        scene.render.fps, scene.render.fps_base = fps, 1
        known = set(bpy.data.actions)
        for obj in PRIOR["import_one"](path):
            bpy.data.objects.remove(obj, do_unlink=True)
        imported = {act.name: act for act in set(bpy.data.actions) - known}
        for name in names:
            imported[name].use_fake_user = True
    scene.render.fps = 24


SHARED["load_motion"] = lambda: load_clips(bpy.context.scene)


def set_pose(scene, arm, name, frame):
    if name != "rest":
        scene.render.fps = 30 if name in ADDED else 24
    if name != getattr(set_pose, "active", None):
        arm.animation_data.action = None
        for bone in arm.pose.bones:
            bone.matrix_basis.identity()
        set_pose.active = name
    PRIOR["set_pose"](scene, arm, name, frame)


def sample_frames(action):
    first, last = map(round, action.frame_range)
    return (i / 2 for i in range(2 * first, 2 * last + 1))


def cache_motion(scene, arm, body, names):
    bones = [arm.pose.bones[name] for name in names]
    modes = tuple(b.rotation_mode for b in bones)
    inverse = [b.bone.matrix_local.inverted() for b in bones]
    samples, transforms = [], []
    set_pose.active = None
    frames = [("rest", 1.)]
    for name in CLIPS:
        frames.extend((name, frame) for frame in sample_frames(bpy.data.actions[name]))
    for name, frame in frames:
        set_pose(scene, arm, name, frame)
        p, f = geometry(body, bpy.context.evaluated_depsgraph_get())
        samples.append((name, frame, BVHTree.FromPolygons(p.tolist(), f.tolist(), all_triangles=True), p, f))
        transforms.append(np.asarray([bone.matrix @ inv for bone, inv in zip(bones, inverse)])[:, :3, :])
    assert modes == tuple(b.rotation_mode for b in bones)
    print("CACHED", len(samples), "poses", flush=True)
    return samples, np.asarray(transforms, dtype=np.float32)


def open_fit():
    SHARED["GLB"] = SOURCE
    scene, arm, body, garment, names = R2["start"]()
    SHARED["GLB"] = EXPORT
    return scene, arm, body, garment, names


def baseline():
    scene, arm, body, garment, names = open_fit()
    points, faces = coords(garment.data), faces_of(garment.data)
    weights = limit_weights(PRIOR["read_weights"](garment, names))
    samples, transforms = cache_motion(scene, arm, body, names)
    start = time.monotonic()
    d, pairs, _ = R2["scan"](points, weights, faces, samples, transforms)
    report_scan("v3", samples, d, pairs)
    print("SCAN SECONDS", time.monotonic() - start, flush=True)
    zone = PRIOR["region_faces"](points)
    body_zone = np.array(names)[PRIOR["read_weights"](body, names)[samples[0][4]].sum(axis=1).argmax(axis=1)]
    for clip in CLIPS:
        rows = np.array([i for i, sample in enumerate(samples) if sample[0] == clip])
        per_vertex = d[rows].argmin(axis=0)
        view = []
        for j in np.argsort(d[rows].min(axis=0))[:15]:
            row = rows[per_vertex[j]]
            pos, _ = skin(points[[j]], weights[[j]], transforms[[row]])
            nearest = samples[row][2].find_nearest(pos.ravel())[2]
            view.append((int(j), samples[row][1], round(float(d[row, j] * 1000), 3),
                         str(zone[j]), str(body_zone[nearest]), np.round(points[j], 4).tolist()))
        print("BASELINE", clip, view, flush=True)


def clearance_score(d, pairs):
    deficit = 1000 * np.maximum(.00085 - d, 0)
    return (float(1e7 * (pairs[0] + np.count_nonzero((d[0] < TARGET) | (d[0] > CAP))))
            + float(pairs.sum() + 4 * np.count_nonzero(d < 0)
                    + .7 * np.square(deficit).sum() + 100 * np.square(deficit.max())))


def guard(points, proposed, reference, faces, rest):
    delta = proposed - reference
    proposed = reference + delta * np.minimum(1, CAP / np.linalg.norm(delta, axis=1).clip(1e-9))[:, None]
    for _ in range(3):
        clearance, direction = signed(rest[2], proposed)
        correction = np.maximum(.0008 - clearance, 0) - np.maximum(clearance - CAP + .0001, 0)
        proposed += correction[:, None] * direction
    proposed = R2["prevent_flips"](points, proposed, faces)
    return R2["retain_clear_rest"](points, proposed, faces, rest)


def pose_rows(samples, d, pairs):
    rows = set(R2["choose_rows"](samples, d, pairs))
    per_vertex = d.argmin(axis=0)[d.min(axis=0) < .0015]
    frequent = np.bincount(per_vertex, minlength=len(samples))
    rows.update(np.flatnonzero(frequent >= 4))
    return np.array(sorted(rows))


def pack_contacts(contacts):
    frame, ids, bary, normal, distance = PREVIOUS["pack_contacts"](contacts)
    # Preserve the worst contact of each vertex in each short pose span.
    # This gives fast transients the same influence as repeated idle poses.
    anchors = ids[np.arange(len(ids)), bary.argmax(axis=1)]
    key = (frame // 6 * (ids.max() + 1) + anchors) * 2 + (bary[:, 0] != 1)
    ordering = np.lexsort((distance, key))
    keep = ordering[np.r_[True, np.diff(key[ordering]) != 0]]
    return frame[keep], ids[keep], bary[keep], normal[keep], distance[keep]


def bake_step(points, weights, support, links, matrices, transforms, contacts, margin, weight_scale):
    count = len(points)
    frame, ids, bary, normal, distance = pack_contacts(contacts)
    direction = np.einsum("ni,nkij->nkj", normal, matrices[frame[:, None], ids, :, :3])
    worst = PREVIOUS["worst_offset"](ids, bary, direction, distance, count, margin)
    floor = R2["laplacian_floor"](worst, links).astype(np.float32)
    focus = np.linalg.norm(floor, axis=1) > 0
    columns, active = PREVIOUS["local_skin_columns"](weights, support, focus)
    if weight_scale:
        joint = transforms[frame[:, None, None], columns[ids]]
        posed = np.einsum("nkjlm,nkm->nkjl", joint[..., :3], points[ids]) + joint[..., 3]
        influence = np.einsum("nl,nkjl->nkj", normal, posed)
        influence -= influence.mean(axis=2, keepdims=True)
        gradient = np.concatenate((direction, weight_scale * influence), axis=2)
    else:
        gradient = direction
    gradient *= bary[..., None]
    gram = np.square(gradient).sum(axis=(1, 2)).clip(.08)
    flat = ids.ravel()
    step = np.zeros((count, gradient.shape[-1]), dtype=np.float32)
    step[:, :3] = .6 * floor
    for _ in range(25):
        remaining = np.maximum(margin - distance - np.einsum("nkj,nkj->n", gradient, step[ids]), 0)
        importance = np.maximum(remaining, .00002) ** 1.5
        importance[frame == 0] *= 4
        impulse = importance * remaining / gram
        force = gradient * impulse[:, None, None]
        normalizer = np.bincount(flat, weights=(importance[:, None] * bary).ravel(),
                                 minlength=count).clip(1e-12)
        correction = np.column_stack([np.bincount(flat, weights=component.ravel(), minlength=count)
                                      for component in force.transpose(2, 0, 1)])
        step += (.93 * correction / normalizer[:, None]).astype(np.float32)
        step += .09 * (mean(step, links) - step)
        length = np.linalg.norm(step[:, :3], axis=1).clip(1e-10)
        step[:, :3] *= np.minimum(1, .019 / length)[:, None]
        if weight_scale:
            revised = R2["project_simplex"](active + weight_scale * step[:, 3:])
            step[:, 3:] = (revised - active) / weight_scale
    adjusted = weights.copy()
    if weight_scale:
        vertices = np.flatnonzero(np.linalg.norm(step[:, 3:], axis=1) > .00003)
        adjusted[vertices] = 0
        adjusted[vertices[:, None], columns[vertices]] = revised[vertices]
    return step[:, :3], adjusted, floor


def candidate_step(points, weights, reference, faces, links, samples, transforms, distances, pairs,
                   contacts, matrices, support, iteration):
    rows = pose_rows(samples, distances, pairs)
    current = clearance_score(distances[rows], pairs[rows])
    margin = MARGIN if distances.min() < -.0005 else .00115
    pure, _, floor = bake_step(points, weights, support, links, matrices, transforms, contacts, margin, 0)
    coupled, revised, _ = bake_step(points, weights, support, links, matrices, transforms, contacts,
                                     margin, 3.5)
    weight_delta = revised - weights
    weight_delta += .21 * (mean(weight_delta, links) - weight_delta)
    trials = [
        ("worst offset", .8 * floor, 0.),
        ("geometry", pure, 0.),
        ("combined", coupled, weight_delta),
        ("combined damped", .5 * coupled, .5 * weight_delta),
        ("averaged geometry", .8 * mean(pure, links), 0.),
    ]
    if iteration < 5:
        severity = np.maximum(0, margin - distances.min(axis=0))
        _, outward = signed(samples[0][2], points)
        radial = outward * severity[:, None]
        for _ in range(4):
            radial = .68 * radial + .32 * mean(radial, links)
        trials += [("rest normals", radial, 0.), ("normal and skin", .55 * (pure + radial), weight_delta)]
    best = (current, points, weights, "unchanged")
    for label, delta, dw in trials:
        p = guard(points, points + delta, reference, faces, samples[0])
        w = limit_weights(np.maximum(weights + dw, 0))
        d, o, _ = R2["scan"](p, w, faces, samples, transforms, rows)
        value = clearance_score(d, o)
        if value < best[0]:
            best = value, p, w, label
    print("STEP", best[3], round(current, 1), "->", round(best[0], 1), flush=True)
    return best[1:]


def fit(passes, resume):
    scene, arm, body, garment, names = open_fit()
    points = coords(garment.data)
    weights = limit_weights(PRIOR["read_weights"](garment, names))
    reference = points.copy()
    samples, transforms = cache_motion(scene, arm, body, names)
    (OUT / ".runtime").mkdir(exist_ok=True)
    checkpoint = OUT / ".runtime/fit_state.npz"
    history_path = OUT / "fit_history.json"
    history = json.loads(history_path.read_text())["passes"] if resume else []
    if resume:
        state = np.load(checkpoint)
        if len(state["reference"]) != len(reference):
            raise ValueError("Checkpoint requires the original topology")
        points, weights, reference = (state[key] for key in ("points", "weights", "reference"))
    faces = faces_of(garment.data)
    links = PRIOR["adjacency"](garment.data)
    reference_weights = weights.copy()
    support = R2["weight_support"](reference, body, names, samples[0][2], samples[0][4], links, weights)
    best = (float("inf"), points, weights)
    started = len(history)
    for iteration in range(started, started + passes + 1):
        tic = time.monotonic()
        d, pairs, (hits, long_hits, contacts, matrices) = R2["scan"](
            points, weights, faces, samples, transforms, collect=True)
        metrics = report_scan(iteration, samples, d, pairs)
        value = clearance_score(d, pairs)
        print("SCAN SECONDS", round(time.monotonic() - tic, 2), "score", round(value, 2), flush=True)
        entry = {"pass": iteration, "score": value, "triangles": len(faces), "clips": metrics}
        history.append(entry)
        if value < best[0]:
            best = value, points.copy(), weights.copy()
            np.savez(checkpoint, points=points, weights=weights, reference=reference)
        write_json("fit_history.json", {
            "source_glb_sha256": digest(SOURCE), "motion_sha256": digest(FIXED),
            "actions_sha256": digest(ACTIONS), "target_m": TARGET, "margin_m": MARGIN,
            "passes": history,
        })
        if (d.min() >= TARGET and not pairs.any() and d[0].max() <= CAP) or iteration == started + passes:
            break
        points, weights, entry["step"] = candidate_step(
            points, weights, reference, faces, links, samples, transforms, d, pairs, contacts, matrices,
            support, iteration)
    _, points, weights = best
    print("REST EDITS", stats(np.linalg.norm(points - reference, axis=1)),
          "weight edit", stats(np.abs(weights - reference_weights).sum(axis=1)), flush=True)
    PRIOR["export"](garment, arm, body, points, names, weights)
    print("REPAIRED TANGENTS", PREVIOUS["repair_tangents"](EXPORT), flush=True)


def search_rows(samples, distances, pairs):
    rows = {0}
    target = distances.argmin(axis=0)
    for name in CLIPS:
        ids = np.array([i for i in range(len(samples)) if samples[i][0] == name])
        rows.update(ids[np.linspace(0, len(ids)-1, 9 if name in ADDED else 5).astype(int)])
        rows.update(ids[np.argsort(distances[ids].min(axis=1))[:2]])
        rows.update(ids[np.argsort(pairs[ids])[-2:]])
    rows.update(np.flatnonzero(np.bincount(target, minlength=len(samples)) >= 8))
    return np.array(sorted(rows))


def nearest_values(trees, posed):
    return np.array([signed(tree, pos)[0] for tree, pos in zip(trees, posed)])


def spatial_mix(original, candidate, links, passes, mix):
    delta = candidate - original
    for _ in range(passes):
        delta = (1-mix) * delta + mix * mean(delta, links)
    return original + delta


def protected_search(points, weights, reference, faces, links, samples, transforms, distances, pairs, support,
           names, iteration):
    rows = search_rows(samples, distances, pairs)
    trees = [samples[row][2] for row in rows]
    transforms_thin = transforms[rows]
    worst = distances.min(axis=0)
    ranks = np.argsort(worst)
    target = ranks[:750]
    target = target[worst[target] < .00115]
    if not len(target):
        return points, weights
    p0, w0 = points[target].copy(), weights[target].copy()
    ref = reference[target]
    near = mean(points,links)[target]
    skin_near = mean(weights,links)[target]
    _, rest_normal = signed(trees[0], p0)
    posed, _ = skin(p0, w0, transforms_thin)
    baseline = nearest_values(trees, posed)
    legacy = np.array([samples[row][0] not in ADDED for row in rows])
    legacy_floor = np.minimum(baseline[legacy].min(axis=0) - .00004, .00072)
    best = np.full(len(target), np.inf)
    dest, binding = p0.copy(), w0.copy()
    scale = np.clip(.0016 + 1.2 * np.maximum(0, .001 - worst[target]), .0015, .012)[:, None]

    def evaluate(p, w):
        p = p.astype(np.float32)
        w = w.astype(np.float32)
        posed, _ = skin(p, w, transforms_thin)
        d = nearest_values(trees, posed)
        deficits = np.maximum(.001 - d, 0) * 1000
        dlt = np.linalg.norm(p - p0, axis=1)*1000
        change = np.abs(w-w0).sum(axis=1)
        score = (.9 * np.square(deficits.max(axis=0))
                 + 4*np.square(deficits).mean(axis=0) + 1.2*(d<0).mean(axis=0)
                 + .008*dlt*dlt + .40*change*change)
        valid = ((d[0] >= .0007) & (d[0] <= .0298) &
                 (np.linalg.norm(p - ref, axis=1) <= .0299) &
                 (d[legacy].min(axis=0) >= legacy_floor))
        update = valid & (score < best)
        best[update], dest[update], binding[update] = score[update], p[update], w[update]

    evaluate(p0, w0)
    offsets = [rest_normal, -rest_normal]
    vec = np.array([[x,y,z] for x in (-1,0,1) for y in (-1,0,1) for z in (-1,0,1)
                    if x or y or z], np.float32)
    vec /= np.linalg.norm(vec,axis=1,keepdims=True)
    offsets.extend(vec)
    for factor in (1., 1.8, .46):
        for axis in offsets:
            evaluate(p0 + factor * scale * axis, w0)
    evaluate(p0 + .65*(near-p0),w0)
    w_support = support[target]
    evaluate(dest, limit_weights(.45*w0+.55*w_support))
    evaluate(dest, limit_weights(.35*w0+.65*skin_near))
    x, y, z = ref.T
    applicable = {
        "Hips": np.ones(len(x), bool), "Spine": np.ones(len(x), bool),
        "Spine1": np.ones(len(x), bool), "Spine2": z>.448,
        "LeftShoulder": (x>0)&(z>.478), "RightShoulder": (x<0)&(z>.478),
        "LeftArm": (x>0)&(z>.465), "RightArm": (x<0)&(z>.465),
        "LeftUpLeg": (x>0)&(z<.474), "RightUpLeg": (x<0)&(z<.474),
    }
    for name, valid in applicable.items():
        for gain in (.19, .39, .68):
            blend = gain*valid
            revised = w0 * (1-blend[:,None])
            revised[:,names.index("mixamorig:"+name)] += blend
            evaluate(dest, limit_weights(revised))
    for f in (.37, .83):
        current = dest.copy()
        for axis in offsets:
            evaluate(current + f * scale * axis, binding)
    proposed = points.copy()
    updated = weights.copy()
    proposed[target], updated[target] = dest, binding
    print("VERTEX SEARCH", iteration, len(target), "start min mm", float(baseline.min()*1000),
          "moved", int(np.count_nonzero((np.linalg.norm(dest-p0,axis=1)>0))),
          "weight shifted", int(np.count_nonzero((np.abs(binding-w0).sum(axis=1)>.001))), flush=True)

    def cost(d, overlaps):
        return clearance_score(d, overlaps) + 8 * clearance_score(d[legacy], overlaps[legacy])

    best_fit = cost(distances[rows], pairs[rows]), points, weights
    delta = proposed-points
    weight_delta = updated-weights
    for smoothing, gain in ((4,.95), (2,.85), (1,.8), (0,.38), (5,1.3), (3,.53)):
        p = spatial_mix(points, points+gain*delta, links, smoothing, .52)
        w = spatial_mix(weights, weights+gain*weight_delta, links, smoothing, .63)
        p = guard(points,p,reference,faces,samples[0])
        w = limit_weights(w.clip(0))
        d,o,_ = R2["scan"](p,w,faces,samples,transforms,rows)
        candidate = cost(d,o)
        if candidate < best_fit[0]:
            best_fit = candidate,p,w
        print("SEARCH BLEND", smoothing, gain, "score", round(candidate,1), "pairs", int(o.sum()),
              "min mm", round(float(d.min()*1000),3), flush=True)
    return best_fit[1:]




def scan_pairs(points, weights, faces, samples, poses):
    posed, _ = skin(points, weights, poses)
    distances, hits = [], []
    polygons = faces.tolist()
    for positions, sample in zip(posed, samples):
        body_tree = sample[2]
        distances.append(signed(body_tree, positions)[0])
        garment_tree = BVHTree.FromPolygons(positions.tolist(), polygons, all_triangles=True)
        hits.append(set(body_tree.overlap(garment_tree)))
    return np.array(distances), hits


def preserve_legacy(reference, reference_weights, points, weights, faces, links, samples, transforms):
    # Test every frame against its original triangle pairs. Only faces with an
    # edited vertex can change, so the local patch can use the full sample bank.
    delta, binding = points - reference, weights - reference_weights
    edited = (np.abs(delta).max(axis=1) > 1e-9) | (np.abs(binding).max(axis=1) > 1e-7)
    touched = faces[edited[faces].any(axis=1)]
    if not len(touched):
        return points, weights, []
    local, patch = np.unique(touched, return_inverse=True)
    patch = patch.reshape(-1, 3)
    rows = [i for i, sample in enumerate(samples) if sample[0] not in ADDED]
    poses = transforms[rows]
    legacy = [samples[i] for i in rows]
    baseline, original_pairs = scan_pairs(reference[local], reference_weights[local], patch, legacy, poses)
    allowed = np.minimum(baseline - .000002, .00054)
    alpha = np.ones(len(points), dtype=np.float32)
    history = []
    for iteration in range(9):
        p = reference + alpha[:, None] * delta
        w = reference_weights.copy()
        w[edited] = limit_weights((reference_weights + alpha[:, None] * binding)[edited])
        d, pairs = scan_pairs(p[local], w[local], patch, legacy, poses)
        bad_vertices = np.any(d < allowed, axis=0)
        bad_faces = {face for candidate, known in zip(pairs, original_pairs)
                     for _, face in candidate - known}
        history.append({"pass": iteration, "vertices_over_legacy_limit": int(bad_vertices.sum()),
                        "new_overlapping_faces": len(bad_faces),
                        "pair_occurrences_on_edited_faces": sum(map(len, pairs))})
        print("PRESERVE", history[-1], flush=True)
        if not bad_vertices.any() and not bad_faces:
            return p, w, history
        if bad_faces:
            bad_vertices[patch[sorted(bad_faces)].ravel()] = True
        retain = np.ones_like(alpha)
        retain[local[bad_vertices]] = .19 if iteration < 2 else 0.
        retain = np.minimum(retain, .88 * mean(retain, links) + .12)
        alpha *= retain
    return p, w, history


def protected_fit(passes):
    """Test alternate directions in contact patches with a legacy clearance floor."""
    scene, arm, body, garment, names = open_fit()
    reference = coords(garment.data)
    weights = limit_weights(PRIOR["read_weights"](garment, names))
    reference_weights = weights.copy()
    points = reference.copy()
    faces = faces_of(garment.data)
    links = PRIOR["adjacency"](garment.data)
    samples, transforms = cache_motion(scene, arm, body, names)
    support = R2["weight_support"](reference, body, names, samples[0][2], samples[0][4], links, weights)
    legacy = np.array([sample[0] not in ADDED for sample in samples])
    history, best = [], None
    for iteration in range(passes + 1):
        d, pairs, _ = R2["scan"](points, weights, faces, samples, transforms)
        metrics = report_scan(iteration, samples, d, pairs)
        value = clearance_score(d, pairs) + 8 * clearance_score(d[legacy], pairs[legacy])
        history.append({"pass": iteration, "score": value, "clips": metrics})
        if best is None or value < best[0]:
            best = value, points.copy(), weights.copy(), iteration
        if iteration == passes or (d.min() >= TARGET and not pairs.any() and d[0].max() <= CAP):
            break
        points, weights = protected_search(points, weights, reference, faces, links, samples,
                                           transforms, d, pairs, support, names, iteration)
    _, points, weights, selected = best
    points, weights, guard_history = preserve_legacy(reference, reference_weights, points, weights,
                                                     faces, links, samples, transforms)
    d, pairs, _ = R2["scan"](points, weights, faces, samples, transforms)
    selected_metrics = report_scan("legacy guard", samples, d, pairs)
    export_result(garment, arm, body, names, points, weights)
    write_json("fit_history.json", {
        "source_glb_sha256": digest(SOURCE), "motion_sha256": digest(FIXED),
        "actions_sha256": digest(ACTIONS), "glb_sha256": digest(EXPORT),
        "method": "local alternate offsets and weights with legacy clearance guard",
        "target_m": TARGET, "margin_m": MARGIN, "selected_pass": selected, "passes": history,
        "legacy_guard": guard_history, "selected_clips": selected_metrics,
        "rest_displacement_m": stats(np.linalg.norm(points - reference, axis=1)),
        "vertices_moved_over_0_1mm": int(np.count_nonzero(np.linalg.norm(points - reference, axis=1) > .0001)),
        "edited_binding_vertices": int(np.count_nonzero(abs(weights - reference_weights).sum(axis=1) > .001)),
    })


def export_result(garment, arm, body, names, points, weights):
    PRIOR["export"](garment, arm, body, points, names, weights)
    print("REPAIRED TANGENTS", PREVIOUS["repair_tangents"](EXPORT), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument("--bake", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if args.baseline:
        baseline()
    elif args.bake:
        fit(args.passes, args.resume)
    else:
        protected_fit(args.passes)
