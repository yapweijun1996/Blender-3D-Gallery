"""Sample the supplied master with the authored motion bank."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import os

import bpy
import numpy as np

import fit_module as fit
from common import CLIPS, MASTER, MOTION, RUNTIME, bind, dispose, load_glb, samples, set_frame


def cache_path():
    return RUNTIME / ("poses-" + fit.sha(MASTER)[:12] + "-" + fit.sha(MOTION)[:12] + ".npz")


def build_cache(names):
    path = cache_path()
    if path.exists():
        return
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = 30, 1
    arm, body = [scene.objects[n] for n in ("Armature", "Base_Body")]
    assert set(names) == set(arm.data.bones.keys())
    dispose(load_glb(MOTION))
    inverses = [arm.data.bones[n].matrix_local.inverted() for n in names]
    labels, frames, points, matrices = [], [], [], []
    for clip in ("rest", *CLIPS):
        action = bpy.data.actions[clip] if clip != "rest" else None
        bind(arm, action)
        for frame in samples(*action.frame_range) if action else [0.]:
            set_frame(scene, frame)
            mesh = body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
            xyz = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
            mesh.vertices.foreach_get("co", xyz)
            labels.append(clip)
            frames.append(frame)
            points.append(xyz.reshape(-1, 3))
            matrices.append(np.asarray([arm.pose.bones[n].matrix @ inv
                                        for n, inv in zip(names, inverses)])[:, :3])
        print("POSE", clip, len(frames), flush=True)
    pending = path.with_suffix(f".{os.getpid()}.npz")
    np.savez(pending, labels=labels, frames=frames, points=np.asarray(points, np.float32),
             matrices=np.asarray(matrices, np.float32))
    pending.replace(path)


def load_scene():
    template = fit.Glb(fit.BODY)
    names = [template.doc["nodes"][i]["name"] for i in template.doc["skins"][0]["joints"]]
    build_cache(names)
    with np.load(cache_path(), allow_pickle=False) as cache:
        labels, frames, points, matrices = [cache[key] for key in ("labels", "frames", "points", "matrices")]
    if "Base_Body" not in bpy.context.scene.objects:
        bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False, use_scripts=False)
    body = bpy.context.scene.objects["Base_Body"]
    rest, faces = fit.GEOMETRY["mesh_arrays"](body.data)
    assert np.max(np.abs(rest - points[0])) < .000002
    polys = faces.tolist()
    from mathutils.bvhtree import BVHTree
    rows = [(str(clip), float(frame), BVHTree.FromPolygons(p.tolist(), polys, all_triangles=True), p, faces)
            for clip, frame, p in zip(labels, frames, points, strict=True)]
    return names, None, None, rows, matrices


if __name__ == "__main__":
    template = fit.Glb(fit.BODY)
    build_cache([template.doc["nodes"][i]["name"] for i in template.doc["skins"][0]["joints"]])
