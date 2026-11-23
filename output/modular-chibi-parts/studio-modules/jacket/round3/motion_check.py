"""Measure vertex clearance on a fresh GLB import at integer and half frames."""
import hashlib
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

CLIPS = ("walk", "run", "wave", "jump", "idle", "nod", "dance")
GATE = .0005


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(master, motion, garment):
    bpy.ops.wm.open_mainfile(filepath=str(master), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body = scene.objects["Armature"], scene.objects["Base_Body"]
    before = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(garment))
    objects = set(scene.objects) - before
    rig, = (obj for obj in objects if obj.type == "ARMATURE")
    mesh, = (obj for obj in objects if obj.type == "MESH" and
             any(mod.type == "ARMATURE" and mod.object == rig for mod in obj.modifiers))
    names = set(arm.data.bones.keys())
    assert len(names) == 65 and names == set(rig.data.bones.keys())
    world = mesh.matrix_world.copy()
    mesh.parent = arm
    mesh.matrix_world = world
    mesh.modifiers.clear()
    mesh.modifiers.new("Master skin", "ARMATURE").object = arm
    bpy.data.objects.remove(rig, do_unlink=True)
    before = set(scene.objects)
    actions_before = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=str(motion))
    incoming = set(scene.objects) - before
    rig, = (obj for obj in incoming if obj.type == "ARMATURE")
    assert set(rig.data.bones.keys()) == names
    actions = {action.name: action for action in set(bpy.data.actions) - actions_before}
    assert set(actions) == set(CLIPS)
    for obj in incoming:
        obj.hide_viewport = obj.hide_render = True
    arm.animation_data_clear()
    arm.animation_data_create()
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    return scene, arm, body, mesh, actions


def samples(scene, arm, actions):
    modes = [bone.rotation_mode for bone in arm.pose.bones]
    scene.frame_set(1)
    yield "rest", 1.
    for clip in CLIPS:
        action = actions[clip]
        arm.animation_data.action = action
        arm.animation_data.action_slot = action.slots[0]
        first, last = action.frame_range
        assert abs(first - round(first)) < 1e-4 and abs(last - round(last)) < 1e-4
        for at in range(round(first * 2), round(last * 2) + 1):
            scene.frame_set(at // 2, subframe=(at % 2) * .5)
            yield clip, at / 2
    assert modes == [bone.rotation_mode for bone in arm.pose.bones]


def geometry(obj, dg):
    evaluated = obj.evaluated_get(dg)
    data = evaluated.to_mesh()
    try:
        data.calc_loop_triangles()
        return ([evaluated.matrix_world @ v.co for v in data.vertices],
                [tuple(t.vertices) for t in data.loop_triangles])
    finally:
        evaluated.to_mesh_clear()


def signed(tree, points):
    values = []
    find = tree.find_nearest
    for x, y, z in points:
        (a, b, c), (u, v, w), _, _ = find((x, y, z))
        values.append((x - a) * u + (y - b) * v + (z - c) * w)
    return np.asarray(values)


def zones(points):
    x, _, z = np.asarray(points).T
    labels = np.full(len(z), "torso panels", dtype="<U32")
    labels[z < .414] = "ribbed hem"
    labels[(np.abs(x) > .098) & (z > .505)] = "shoulder/armpit"
    labels[np.abs(x) > .155] = "sleeves"
    labels[np.abs(x) > .234] = "ribbed cuffs"
    labels[(np.abs(x) < .075) & (z > .582)] = "stand collar"
    sides = np.where(x > .025, "left ", np.where(x < -.025, "right ", "center "))
    return labels, np.char.add(sides, labels)


def rest_stats(tree, points, dist, labels):
    euclidean = np.asarray([tree.find_nearest(point)[3] for point in points])
    result = {}
    for label in ("all", *sorted(set(labels))):
        use = np.ones(len(labels), bool) if label == "all" else labels == label
        row = dict(zip(("min", "p10", "median", "p90", "p95", "max"),
                       map(float, np.percentile(dist[use], (0, 10, 50, 90, 95, 100)))))
        row.update(vertices=int(use.sum()), max_euclidean=float(euclidean[use].max()),
                   vertices_over_30_mm=int((euclidean[use] > .030).sum()))
        result[label] = row
    return result


def summary(records, key):
    results = {}
    for clip in ("rest", *CLIPS):
        data = [r for r in records if r["clip"] == clip]
        assert data
        high = max(data, key=lambda r: r[key])
        low = min(data, key=lambda r: r["min_signed_m"])
        results[clip] = {"samples": len(data), key: high[key],
                         "peak_frame": high["frame"] if high[key] else None,
                         "sum": sum(r[key] for r in data),
                         "min_signed_m": low["min_signed_m"], "min_frame": low["frame"],
                         "min_zone": low["min_zone"]}
    return results


def emit(out, stem, key, report):
    results = summary(report["frames"], key)
    report["results"] = results
    lines = [f"RESULT {clip:5} {key} {row[key]} min_signed_dist {row['min_signed_m']:+.9f} "
             f"frame {row['min_frame']:g} poses {row['samples']}" for clip, row in results.items()]
    (out / f"{stem}.txt").write_text("\n".join(lines) + "\n")
    (out / f"{stem}.json").write_text(json.dumps(report, indent=2) + "\n")
    print("\n".join(lines), flush=True)


def main():
    master, motion, garment, out = map(Path, sys.argv[sys.argv.index("--") + 1:])
    scene, arm, body, mesh, actions = load(master, motion, garment)
    labels, by_side = zones([v.co for v in mesh.data.vertices])
    report = {"master_sha256": sha(master), "motion_sha256": sha(motion),
              "glb_sha256": sha(garment), "frames": []}
    for clip, frame in samples(scene, arm, actions):
        dg = bpy.context.evaluated_depsgraph_get()
        bp, bf = geometry(body, dg)
        gp, _ = geometry(mesh, dg)
        tree = BVHTree.FromPolygons(bp, bf, all_triangles=True, epsilon=0)
        sd = signed(tree, gp)
        index = int(sd.argmin())
        row = {"clip": clip, "frame": frame, "max_verts_inside": int((sd < 0).sum()),
               "min_signed_m": float(sd[index]), "min_zone": str(by_side[index])}
        if row["min_signed_m"] < GATE:
            row["violating_zones"] = {
                str(name): {"inside": int(((by_side == name) & (sd < 0)).sum()),
                            "min_signed_m": float(sd[by_side == name].min())}
                for name in sorted(set(by_side[sd < GATE]))}
        report["frames"].append(row)
        if clip == "rest":
            report["rest_clearance_m"] = rest_stats(tree, gp, sd, labels)
            report["rest_fit_m"] = {
                "wrist_x": [min(p.x for p in gp), max(p.x for p in gp)],
                "hem_z": [min(p.z for p, label in zip(gp, labels) if label == "ribbed hem"),
                          max(p.z for p, label in zip(gp, labels) if label == "ribbed hem")]}
    assert len(report["frames"]) == 824
    emit(out, "motion_check", "max_verts_inside", report)


if __name__ == "__main__":
    main()
