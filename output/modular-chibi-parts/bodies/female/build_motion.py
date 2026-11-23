"""Retarget the neutral master's evaluated quaternion deltas and bake corrections."""
from collections import defaultdict, Counter
from copy import deepcopy
import hashlib
import json
import math
import os
from unittest.mock import patch

import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree
from io_scene_gltf2.blender.imp.animation_node import BlenderNodeAnim

import sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (BODY, HERE, MASTER, MOTION, NEUTRAL, PARTS, RUNTIME, SOURCES, STUDIO,
                    arguments, bind, dispose, load_glb, reset, set_frame)
from glb_io import Glb

sys.path.append(str(PARTS / "body-fix"))
from bodycheck import Checker, posed
from clearance import arms, bone, legs, slide, turn
from polish import hip as clear_hip, elbow as clear_elbow

FPS = 30
SIDES = ("Left", "Right")
IDENTITY = Quaternion((1, 0, 0, 0))
GESTURES = None


def sec_grid(glb, name):
    animation = next(a for a in glb.doc["animations"] if a["name"] == name)
    times = [glb.accessor(s["input"])[:, 0] for s in animation["samplers"]]
    first = min(float(t[0]) for t in times)
    last = max(float(t[-1]) for t in times)
    # The female master and all garment checker copies run at 30 fps.
    rate = 2 * FPS
    result = {first, last}
    result.update(i / rate for i in range(math.ceil(first * rate - .00001),
                                          math.floor(last * rate + .00001) + 1))
    return sorted({float(np.float32(min(last, max(first, t)))) for t in result})


def pose_references():
    bpy.ops.wm.open_mainfile(filepath=str(NEUTRAL), load_ui=False)
    scene = bpy.context.scene
    scene.render.fps = FPS
    arm, body = (scene.objects[name] for name in ("Armature", "Base_Body"))
    reference = Checker(body)
    rest = {b.name: b.matrix_local.to_quaternion() for b in arm.data.bones}
    results = {}
    selected = {a for a in arguments() if not a.startswith("--")}
    for path, names in SOURCES:
        names = [name for name in names if not selected or name in selected]
        if not names:
            continue
        glb = Glb(path)
        # The neutral checkers bind source actions directly to this master.
        objects = load_glb(path)
        dispose(objects)
        for name in names:
            bind(arm, bpy.data.actions[name])
            rows = []
            for seconds in sec_grid(glb, name):
                set_frame(scene, seconds * FPS)
                points = posed(body)
                floors = [float(points[reference.feet[s], 2].min()) for s in SIDES]
                transforms = {b.name: (b.location.copy(), b.rotation_quaternion.copy(), b.scale.copy())
                              for b in arm.pose.bones}
                rows.append((seconds, floors, transforms))
            results[name] = rows
            print("NEUTRAL", name, len(rows), [[round(1000 * v, 2) for v in z]
                                               for z in zip(*[tuple(fn(r[1][i] for r in rows) for i in range(2))
                                                              for fn in (min, max)])], flush=True)
    return results, rest


def attach(glb, name, times, tracks):
    animation = {"name": name, "channels": [], "samplers": []}
    keys = glb.floats(times, "SCALAR")
    constant = None
    for (idx, path), values in tracks.items():
        values = np.asarray(values, dtype=np.float32)
        if np.ptp(values, axis=0).max() < 1.e-7:
            if constant is None:
                constant = keys if len(times) == 1 else glb.floats(times[:1], "SCALAR")
            time_index = constant
            values = values[:1]
        else:
            time_index = keys
        kind = "VEC4" if path == "rotation" else "VEC3"
        sampler = len(animation["samplers"])
        animation["samplers"].append(dict(input=time_index, output=glb.floats(values, kind),
                                          interpolation="LINEAR"))
        animation["channels"].append(dict(sampler=sampler, target=dict(node=idx, path=path)))
    # Preserve the declared finish even if all animated channels are constant.
    if all(s["input"] != keys for s in animation["samplers"]):
        sampler = animation["samplers"][0]
        sampler.update(input=keys, output=glb.floats(np.repeat(next(iter(tracks.values()))[:1],
                                                               len(times), axis=0), "VEC4"))
    glb.doc["animations"].append(animation)


def female_coefficients(template):
    # Ask the actual importer for its conversion between joint TRS and the
    # Blender edit-bone basis. This includes terminal bone roll and axis flips.
    probe = deepcopy(template)
    channels = {}
    for index in probe.doc["skins"][0]["joints"]:
        channels[index, "rotation"] = [probe.doc["nodes"][index].get("rotation", [0, 0, 0, 1])]
    attach(probe, "_female_bind_probe", [0.], channels)
    path = RUNTIME / f"bind-probe-{os.getpid()}.glb"
    probe.write(path)
    frames = {}
    original = BlenderNodeAnim.anim

    def capture(gltf, anim_idx, node_idx):
        node = gltf.vnodes[node_idx]
        if node.type == node.Bone:
            frames[node_idx] = (node.blender_bone_name, node.editbone_trans.copy(), node.editbone_rot.copy(),
                                node.rotation_after.copy(), node.rotation_before.copy(),
                                Matrix([node.base_scales_to_final_scales(
                                    [gltf.scale_gltf_to_blender(axis)])[0] for axis in np.eye(3)]
                                       ).transposed().inverted())
        return original(gltf, anim_idx, node_idx)

    with patch.object(BlenderNodeAnim, "anim", staticmethod(capture)):
        incoming = load_glb(path)
    dispose(incoming)
    bpy.data.actions.remove(bpy.data.actions["_female_bind_probe"])
    path.unlink()
    assert len(frames) == 65
    return frames


def gltf_channels(arm, matrices, tracks):
    for index, (name, edit_translation, edit_rotation, after, before, scale_inv) in matrices.items():
        b = arm.pose.bones[name]
        t = after.inverted() @ (edit_rotation @ b.location + edit_translation)
        q = (after.inverted() @ edit_rotation @ b.rotation_quaternion @ before.inverted()).normalized()
        tracks[index, "translation"].append((t.x, t.z, -t.y))
        r = np.array((q.x, q.z, -q.y, q.w))
        if tracks[index, "rotation"] and np.dot(r, tracks[index, "rotation"][-1]) < 0:
            r = -r
        tracks[index, "rotation"].append(r)
        tracks[index, "scale"].append(tuple(scale_inv @ b.scale))


def pairs(checker):
    points = posed(checker.body)
    tree = BVHTree.FromPolygons(points.tolist(), checker.faces, all_triangles=True, epsilon=0)
    candidates = np.asarray(tree.overlap(tree), dtype=np.int32).reshape(-1, 2)
    candidates = candidates[candidates[:, 0] < candidates[:, 1]]
    a, b = checker.indices[candidates].transpose(1, 0, 2)
    hits = candidates[~(a[:, :, None] == b[:, None, :]).any(axis=(1, 2))]
    return hits.tolist(), points


def align_leg(arm, side, z_shift):
    """Split a large floor correction across the thigh and shin."""
    upper, shin, foot = [bone(arm, side + label) for label in ("UpLeg", "Leg", "Foot")]
    a, k, p = upper.head.copy(), shin.head.copy(), foot.head.copy()
    u, v = k - a, p - k
    target = p + Vector((0, 0, z_shift))
    travel = target - a
    d = min(max(travel.length, abs(u.length - v.length) + 1.e-5), u.length + v.length - 1.e-5)
    axis = travel.normalized()
    pole = u - u.dot(axis) * axis
    if pole.length < .002:
        return
    # Rotate both segments about their original joint origins, then restore the
    # foot's local shape in world space. The residual sole correction is exact.
    q = (d*d + u.length_squared - v.length_squared) / (2*d)
    knee = a + q * axis + math.sqrt(max(0, u.length_squared - q*q)) * pole.normalized()
    ankle = a + d * axis
    old_foot = foot.matrix.copy()
    angle = u.rotation_difference(knee - a)
    fixed = upper.matrix.copy()
    fixed = (angle.to_matrix() @ fixed.to_3x3()).to_4x4()
    fixed.translation = a
    upper.matrix = fixed
    bpy.context.view_layer.update()
    angle = (foot.head - shin.head).rotation_difference(ankle - shin.head)
    fixed = (angle.to_matrix() @ shin.matrix.to_3x3()).to_4x4()
    fixed.translation = shin.head
    shin.matrix = fixed
    bpy.context.view_layer.update()
    old_foot.translation = foot.head
    foot.matrix = old_foot
    bpy.context.view_layer.update()


def foot_lock(arm, checker, floors, align=False):
    points = posed(checker.body)
    for side, source in zip(SIDES, floors, strict=True):
        # Negative reference drift is clamped. Airborne reference lift survives.
        goal = source if source > .001 else 0.
        z = points[checker.feet[side], 2]
        shift = max((goal - z) / checker.foot_weights[side])
        if align and abs(shift) > .005:
            align_leg(arm, side, float(shift))
            points = posed(checker.body)
            z = points[checker.feet[side], 2]
            shift = max((goal - z) / checker.foot_weights[side])
        if abs(shift) > 1.e-7:
            slide(bone(arm, side + "Foot"), Vector((0, 0, float(shift))))
    bpy.context.view_layer.update()


def pose_state(arm):
    return {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy(), pb.scale.copy()) for pb in arm.pose.bones}


def restore(arm, state):
    for name, values in state.items():
        b = arm.pose.bones[name]
        b.location, b.rotation_quaternion, b.scale = values
    bpy.context.view_layer.update()


def correction_score(checker, floors, arm):
    foot_lock(arm, checker, floors)
    return len(pairs(checker)[0])


def correct(arm, checker, floors, warm=None, seated=False):
    starting = pose_state(arm)
    foot_lock(arm, checker, floors)
    direct, _ = pairs(checker)
    score = len(direct)
    if not seated and any(any(checker.regions[id].endswith("Foot") for id in pair) for pair in direct):
        direct_state = pose_state(arm)
        restore(arm, starting)
        foot_lock(arm, checker, floors, align=True)
        aligned = len(pairs(checker)[0])
        if aligned < score:
            score = aligned
        else:
            restore(arm, direct_state)
    original = score
    if not score:
        return original, score
    if warm:
        state = pose_state(arm)
        for name, (movement, rotation, scale) in warm.items():
            pb = arm.pose.bones[name]
            pb.location += movement
            pb.rotation_quaternion = (rotation @ pb.rotation_quaternion).normalized()
            pb.scale = Vector(tuple(a*b for a,b in zip(pb.scale, scale, strict=True)))
        bpy.context.view_layer.update()
        candidate = correction_score(checker, floors, arm)
        if candidate < score:
            score = candidate
            if not score:
                return original, score
        else:
            restore(arm, state)
    if GESTURES:
        hits, _ = pairs(checker)
        zones = [tuple(checker.regions[i] for i in pair) for pair in hits]
        state = pose_state(arm)
        adjusted = False
        for side, letter in zip(SIDES, "LR", strict=True):
            if any(all(k.startswith(side + "Hand") for k in zone) for zone in zones):
                for name, rotation in GESTURES["hand_open_relaxed_" + letter].items():
                    arm.pose.bones[name].rotation_quaternion = rotation
                adjusted = True
        if adjusted:
            bpy.context.view_layer.update()
            result = len(pairs(checker)[0])
            if result < score:
                score = result
            else:
                restore(arm, state)
            if not score:
                return original, score
    # Resolve independent finger, limb and fold contacts with small pose-local
    # changes. Each accepted candidate must reduce the whole-body overlap count.
    for _ in range(2 if "--quick" in arguments() else 3):
        old_score = score
        hits, _ = pairs(checker)
        zones = [tuple(checker.regions[i] for i in pair) for pair in hits]
        for i, side in enumerate(SIDES):
            same_hand = any(all(k.startswith(side + "Hand") for k in zone) for zone in zones)
            if same_hand:
                fingers = [pb for pb in arm.pose.bones if pb.name.split(":")[-1].startswith(side + "Hand")
                           and pb.name != "mixamorig:" + side + "Hand"]
                state = pose_state(arm)
                chosen = None
                for blend in (.12, .25, .45, .65, .85, 1.):
                    for pb in fingers:
                        pb.rotation_quaternion = state[pb.name][1].slerp(IDENTITY, blend)
                    bpy.context.view_layer.update()
                    result = len(pairs(checker)[0])
                    if result < score:
                        chosen, score = pose_state(arm), result
                    if not result:
                        break
                restore(arm, chosen or state)
            elbow_zone = any(set(z) == {side + "Arm", side + "ForeArm"} or
                             z == (side + "ForeArm", side + "ForeArm") for z in zones)
            wrist_zone = any(side + "ForeArm" in z and any(k.startswith(side + "Hand") for k in z)
                             for z in zones)
            for active, joint in ((elbow_zone, "ForeArm"), (wrist_zone, "Hand")):
                if active and score:
                    state = pose_state(arm)
                    pb = bone(arm, side + joint)
                    chosen = None
                    for blend in (.06, .12, .20, .32, .50):
                        restore(arm, state)
                        if joint == "ForeArm":
                            clear_elbow(arm, side, blend * 56)
                        else:
                            pb.rotation_quaternion = state[pb.name][1].slerp(IDENTITY, blend)
                        bpy.context.view_layer.update()
                        result = correction_score(checker, floors, arm)
                        if result < score:
                            chosen, score = pose_state(arm), result
                        if not result:
                            break
                    restore(arm, chosen or state)
            arm_zone = any(any(k.startswith(side) and any(s in k for s in ("Arm", "Hand", "Shoulder"))
                               for k in zone) and not all(k.startswith(side + "Hand") for k in zone)
                           for zone in zones)
            if arm_zone and score:
                state = pose_state(arm)
                chosen = None
                for strength in (2., 4., 7., 11., 16., 24., 34.):
                    restore(arm, state)
                    v = [0., 0.]
                    v[i] = strength
                    arms(arm, v)
                    result = correction_score(checker, floors, arm)
                    if result < score:
                        chosen, score = pose_state(arm), result
                    if not result:
                        break
                restore(arm, chosen or state)
            knee_zone = any(set(z) <= {side + "Leg", side + "UpLeg"} for z in zones)
            ankle_zone = any(set(z) <= {side + "Leg", side + "Foot", side + "ToeBase"}
                             and side + "Foot" in z for z in zones)
            hip_zone = any(set(z) <= {"Hips", side + "UpLeg"} and side + "UpLeg" in z
                           for z in zones)
            if knee_zone and score:
                state = pose_state(arm)
                chosen = None
                for mm in (3., 6., 10., 16., 23., 30.):
                    restore(arm, state)
                    v = [0., 0.]
                    v[i] = mm
                    legs(arm, v)
                    result = correction_score(checker, floors, arm)
                    if result < score:
                        chosen, score = pose_state(arm), result
                    if not result:
                        break
                restore(arm, chosen or state)
            if ankle_zone and score:
                state = pose_state(arm)
                pb = bone(arm, side + "Foot")
                chosen = None
                for blend in (.07, .15, .28, .45, .62):
                    restore(arm, state)
                    pb.rotation_quaternion = state[pb.name][1].slerp(IDENTITY, blend)
                    bpy.context.view_layer.update()
                    foot_lock(arm, checker, floors, align=True)
                    result = len(pairs(checker)[0])
                    if result < score:
                        chosen, score = pose_state(arm), result
                    if not result:
                        break
                restore(arm, chosen or state)
            cross_leg = any(any(k.startswith(side) and ("Leg" in k or "Foot" in k) for k in z)
                            and any(k.startswith(SIDES[1-i]) and ("Leg" in k or "Foot" in k) for k in z)
                            for z in zones)
            if hip_zone and score:
                state = pose_state(arm)
                chosen = None
                for millimeters in (4, 8, 14, 21, 28):
                    restore(arm, state)
                    clear_hip(arm, side, millimeters)
                    result = correction_score(checker, floors, arm)
                    if result < score:
                        chosen, score = pose_state(arm), result
                    if not result:
                        break
                restore(arm, chosen or state)
            if cross_leg and score:
                state = pose_state(arm)
                chosen = None
                for deg in (2, 4, 7, 11, 16, 22):
                    restore(arm, state)
                    turn(bone(arm, side + "UpLeg"), Vector((0, -1 if i == 0 else 1, 0)), deg)
                    bpy.context.view_layer.update()
                    result = correction_score(checker, floors, arm)
                    if result < score:
                        chosen, score = pose_state(arm), result
                    if not result:
                        break
                restore(arm, chosen or state)
        if score == old_score or not score:
            break
    return original, score


def main():
    global GESTURES
    angular = json.loads((STUDIO / "hand_gestures_female.json").read_text())["gestures"]
    GESTURES = {name: {k: Euler(tuple(map(math.radians, v)), "XYZ").to_quaternion()
                       for k, v in joints.items()} for name, joints in angular.items()}
    references, source_rest = pose_references()
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False)
    scene = bpy.context.scene
    scene.render.fps = FPS
    arm, body = (scene.objects[name] for name in ("Armature", "Base_Body"))
    template = Glb(BODY).skeleton()
    matrices = female_coefficients(template)
    reset(arm)
    checker = Checker(body)
    print("REST", checker.stats, "pairs", len(pairs(checker)[0]), flush=True)

    corrections = "--baseline" not in arguments()
    library = deepcopy(template)
    relative = {b.name: (b.matrix_local.to_quaternion().inverted() @ source_rest[b.name]).normalized()
                for b in arm.data.bones}
    shifts = {b.name: relative[b.name].inverted() for b in arm.data.bones}
    report = {}
    run_id = str(os.getpid())
    selected = {a for a in arguments() if not a.startswith("--")}
    for clip, rows in references.items():
        if selected and clip not in selected:
            continue
        tracks = defaultdict(list)
        frames = []
        warm = None
        for index, (seconds, floors, transforms) in enumerate(rows):
            for b in arm.pose.bones:
                loc, rot, scl = transforms[b.name]
                axis = relative[b.name]
                b.location = axis @ loc
                b.rotation_quaternion = (axis @ rot @ shifts[b.name]).normalized()
                b.scale = scl
            bpy.context.view_layer.update()
            if corrections:
                raw = pose_state(arm)
                seated = clip in {"sit_down", "sit_idle", "stand_up"}
                before, after = correct(arm, checker, floors, warm, seated=seated)
                warm = {}
                if before:
                    for name, (loc, rot, scl) in pose_state(arm).items():
                        base_l, base_q, base_s = raw[name]
                        if name.endswith("Foot") or (not seated and name.endswith(("UpLeg", "Leg"))):
                            movement = Vector()
                        else:
                            movement = loc - base_l
                        difference = (rot @ base_q.inverted()).normalized()
                        # Use the short unit-quaternion hemisphere for damping.
                        if difference.w < 0:
                            difference.negate()
                        scale = tuple(float(a / b) if seated else 1. for a,b in zip(scl, base_s, strict=True))
                        if movement.length > 1.e-6 or difference.angle > .0002 or max(abs(v-1) for v in scale) > .0001:
                            warm[name] = (movement, difference, scale)
            else:
                before = after = correction_score(checker, floors, arm)
            gltf_channels(arm, matrices, tracks)
            hits, points = pairs(checker)
            counts = {key: {"count": value["count"], "max_depth_mm": value["max_depth_mm"]}
                      for key, value in checker.pair_records(points, hits).items()}
            feet = [float(points[checker.feet[s], 2].min()) * 1000 for s in SIDES]
            frames.append(dict(seconds=seconds, before=before, pairs=after, regions=counts, floor_mm=feet,
                               neutral_floor_mm=[v*1000 for v in floors]))
            if index % 15 == 0:
                print("POSE", clip, index, "/", len(rows), "pairs", before, "->", after, flush=True)
        attach(library, clip, [r[0] for r in rows], dict(sorted(tracks.items(), key=lambda r: (r[0][1] != "rotation", r[0]))))
        zones = Counter(k for f in frames for k in f["regions"])
        depths = [d["max_depth_mm"] for f in frames for d in f["regions"].values()]
        print("RETARGET", clip, "total", sum(f["before"] for f in frames), "->",
              sum(f["pairs"] for f in frames), "depth", max(depths, default=0), "zones", zones, flush=True)
        report[clip] = frames
        # A checkpoint remains usable for diagnosis if a subsequent clip fails.
        library.write(RUNTIME / ("progress-" + run_id + ".glb"))
        (RUNTIME / ("progress-" + run_id + ".json")).write_text(json.dumps(report, separators=(",", ":")) + "\n")
    nickname = next((a[6:] for a in arguments() if a.startswith("--tag=")), "")
    stem = "baseline" if not corrections else "-".join(filter(None, ["-".join(sorted(selected)), nickname]))
    path = RUNTIME / f"motion-{stem}.glb" if stem else MOTION
    library.write(path)
    (path.with_name("motion_fit.json") if path == MOTION else path.with_suffix(".json")).write_text(
        json.dumps(report, separators=(",", ":")) + "\n")
    print("MOTION", path.name, hashlib.sha256(path.read_bytes()).hexdigest(), flush=True)


if __name__ == "__main__":
    main()
