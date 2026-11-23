"""Independently measure the reimported GLBs under Blender's Armature modifier."""

from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fit_shoes import (ACTIONS, ADDED, CARRY, CARRY_NAMES, EXPORT, GATE, HERE, MASTER,
                       MOTION, SHARED, SOURCE, bind, digest, frames, imported,
                       load_bank, load_master, mesh_faces, report, set_frame, world_coords)


def on_master(path, arm):
    objects, _ = imported(path)
    shoes, = [obj for obj in objects if obj.type == "MESH" and obj.vertex_groups]
    world = shoes.matrix_world.copy()
    shoes.parent = arm
    shoes.matrix_world = world
    shoes.modifiers.clear()
    shoes.modifiers.new("Master Armature", "ARMATURE").object = arm
    for obj in objects - {shoes}:
        bpy.data.objects.remove(obj, do_unlink=True)
    return shoes


def load_actions(scene):
    shared = load_bank(MOTION, SHARED)
    scene.render.fps, scene.render.fps_base = 30, 1
    others = load_bank(ACTIONS, ADDED) | load_bank(CARRY, CARRY_NAMES)
    return {"rest": None, **shared, **others}


def measure(positions, triangles, body):
    overlaps = len(body.overlap(BVHTree.FromPolygons(positions.tolist(), triangles, all_triangles=True)))
    values = []
    for xyz in positions:
        hit, normal, _, _ = body.find_nearest(xyz)
        values.append((Vector(xyz) - hit).dot(normal))
    index = int(np.argmin(values))
    return {"max_vertices_inside": sum(s < 0 for s in values), "triangle_pairs": overlaps,
            "min_signed_m": float(values[index]), "nearest_vertex_world_m": positions[index].tolist(),
            "export_vertex": index, "garment_min_z_m": float(positions[:, 2].min())}


def summarize(samples):
    deepest = min(samples, key=lambda row: row["min_signed_m"])
    return {"samples": len(samples), "max_vertices_inside": max(s["max_vertices_inside"] for s in samples),
            "max_triangle_pairs": max(s["triangle_pairs"] for s in samples),
            "min_signed_m": deepest["min_signed_m"], "deepest_frame": deepest["frame"]}


def main():
    scene, arm, body = load_master()
    fps = scene.render.fps
    candidate = on_master(EXPORT, arm)
    baseline = on_master(SOURCE, arm)
    triangles = {o: mesh_faces(o).tolist() for o in (body, candidate, baseline)}
    actions = load_actions(scene)
    data, before, summaries = {}, [], {}
    for name, action in actions.items():
        scene.render.fps = fps if name in ("rest", *SHARED) else 30
        bind(arm, action)
        timeline = [1] if action is None else frames(action, rate=4 if name == "run" else 2)
        data[name] = []
        for frame in timeline:
            set_frame(scene, frame)
            tree = BVHTree.FromPolygons(world_coords(body).tolist(), triangles[body], all_triangles=True)
            sample = measure(world_coords(candidate), triangles[candidate], tree)
            data[name].append({"frame": frame, **sample})
            if name == "run":
                sample = measure(world_coords(baseline), triangles[baseline], tree)
                before.append({"frame": frame, **sample})
        summaries[name] = summarize(data[name])
        print("DENSE", name, summaries[name], flush=True)
        if name == "run":
            path = HERE / ".runtime/run_render_data.json"
            report(path, {"glb_sha256": digest(EXPORT), "baseline_run": {"frames": before},
                          "frames": {"run": data["run"]}})
    result = {"glb_sha256": digest(EXPORT), "source_glb_sha256": digest(SOURCE),
              "inputs_sha256": {p.name: digest(p) for p in (MASTER, MOTION, ACTIONS, CARRY)},
              "method": "Full evaluated body and reimported shoe, both triangle BVHs and signed vertex distances",
              "sample_step_frames": {"default": .5, "run": .25},
              "baseline_run": {"summary": summarize(before), "frames": before},
              "results": summaries, "frames": data}
    output = HERE / "qa"
    output.mkdir(exist_ok=True)
    report(output / "motion_gate.json", result)
    assert len(summaries) == 15
    assert all(item["max_vertices_inside"] == item["max_triangle_pairs"] == 0
               and item["min_signed_m"] >= GATE for item in summaries.values())


if __name__ == "__main__":
    main()
