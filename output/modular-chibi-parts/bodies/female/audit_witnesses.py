"""Locate the exact supplied-checker clearance failures on the reimported modules."""
from collections import Counter
import json
from pathlib import Path
import sys

import bpy
from mathutils.bvhtree import BVHTree

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HERE, MASTER, MOTION, SHARED, arguments, bind, dispose, load_glb, samples, set_frame
from fit_module import joint_region


def faces(mesh, triangles):
    if triangles:
        mesh.calc_loop_triangles()
        return [tuple(p.vertices) for p in mesh.loop_triangles]
    return [tuple(p.vertices) for p in mesh.polygons]


def vertices(obj):
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [ev.matrix_world @ v.co for v in ev.data.vertices]


def audit(name):
    folder = HERE / "checks" / name
    record = json.loads((folder / "gate.json").read_text())
    failing = [k for k, v in record["clips"].items() if
               v["max_vertices_inside"] or v["max_triangle_pairs"] or v["min_signed_m"] < .0005]
    if not failing:
        return

    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False)
    scene = bpy.context.scene
    scene.render.fps = 30
    arm, body = (scene.objects[n] for n in ("Armature", "Base_Body"))
    imported = load_glb(HERE / f"female-{name}.glb")
    module, = [o for o in imported if o.type == "MESH" and len(o.vertex_groups)]
    world = module.matrix_world.copy()
    module.parent = arm
    module.matrix_world = world
    module.modifiers.clear()
    module.modifiers.new("Female Skin", "ARMATURE").object = arm
    dispose(imported - {module})
    source = load_glb(MOTION)
    dispose(source)
    base = vertices(module)
    weights = [[(v.group, v.weight) for v in pt.groups] for pt in body.data.vertices]
    region_names = [joint_region(group.name) for group in body.vertex_groups]
    report = {}
    for clip in failing:
        action = bpy.data.actions.get(clip)
        bind(arm, action)
        triangular = clip not in (*SHARED,"rest")
        bf = faces(body.data, triangular)
        mf = faces(module.data, triangular)
        zones = []
        for face in bf:
            total = Counter()
            for v in face:
                for group, w in weights[v]:
                    total[group] += w
            zones.append(region_names[total.most_common(1)[0][0]])
        row = {"min_signed_m": 1.0, "peak_pairs": 0, "peak_pair_zones": {}}
        for frame in samples(*action.frame_range) if action else [0]:
            set_frame(scene, frame)
            b = BVHTree.FromPolygons(vertices(body), bf, all_triangles=triangular)
            points = vertices(module)
            low = 1.
            for index, p in enumerate(points):
                q, n, face, _ = b.find_nearest(p)
                distance = (p-q).dot(n)
                if distance < row["min_signed_m"]:
                    row.update(min_signed_m=distance, frame=frame, vertex=index, zone=zones[face],
                               rest_vertex_m=list(base[index]), posed_vertex_m=list(p))
                low = min(low, distance)
            if record["clips"][clip]["max_triangle_pairs"]:
                pairs = b.overlap(BVHTree.FromPolygons(points, mf, all_triangles=triangular))
                if len(pairs) > row["peak_pairs"]:
                    row.update(peak_pairs=len(pairs), peak_pair_frame=frame,
                               peak_pair_zones=dict(Counter(zones[i] for i, _ in pairs)))
        report[clip] = row
        print("WITNESS", name, clip, row, flush=True)
    (folder / "witnesses.json").write_text(json.dumps({"module_sha256":record["module_sha256"],"clips":report},
                                                      indent=2)+"\n")


if __name__ == "__main__":
    for name in arguments():
        audit(name)
