"""Rebake signed-clearance witnesses measured on the reimported GLB geometry."""
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
from common import MASTER, MOTION, SHARED, arguments, bind, dispose, load_glb, samples, set_frame
import fit_module as fit
from refit import preserve_images


def evaluated_points(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [evaluated.matrix_world @ v.co for v in evaluated.data.vertices]


def faces(mesh, triangular):
    if triangular:
        mesh.calc_loop_triangles()
        return [tuple(face.vertices) for face in mesh.loop_triangles]
    return [tuple(face.vertices) for face in mesh.polygons]


def clearance_trials(module, points, constraints, evidence, budget, origin, cap):
    """Use actual imported sample positions to guard against competing surface normals."""
    choices = np.asarray([(x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1)
                          for z in (-1, 0, 1) if (x, y, z) != (0, 0, 0)], dtype=np.float32)
    choices = fit.normalized(choices)
    probes = np.concatenate([choices * min(step, budget) for step in (.00075, .0015, .0026, .004,
                                                                    .006, .0085, .011)])
    chosen = sorted({key[0] for key in constraints})
    vertices = [int(np.flatnonzero(module.unweld == weld)[0]) for weld in chosen]
    movement = np.zeros_like(points)
    for weld, vertex in zip(chosen, vertices):
        directions = [required * direction for key, (required, direction) in constraints.items() if key[0] == weld]
        offsets = np.concatenate((np.zeros((1, 3)), np.asarray(directions), probes)).astype(np.float32)
        limit = fit.SOURCE["limit_delta"]
        offsets = origin[weld] + limit(points[weld] + offsets - origin[weld], cap) - points[weld]
        min_signed = np.full(len(offsets), 9.)
        loss = np.zeros(len(offsets))
        for tree, positions, skin in evidence:
            blend = np.einsum("j,jik->ik", module.weights[vertex], skin[:, :3, :3])
            candidates = positions[vertex] + offsets @ blend.T
            values = []
            nearest = tree.find_nearest
            near = tree.find_nearest_range
            for p in candidates:
                query = Vector(p)
                site, normal, _, distance = nearest(query)
                nearby = near(query, distance + .0000007)
                values.append(min(((query - q).dot(n) for q, n, _, _ in nearby),
                                  default=(query - site).dot(normal)))
            values = np.asarray(values)
            min_signed = np.minimum(min_signed, values)
            loss += 1200 * np.maximum(0., .00070 - values) + 40 * (values < 0.)
        cost = loss + 25000 * np.maximum(0., .00062 - min_signed) + 25 * np.linalg.norm(offsets, axis=1)
        for key, (required, direction) in constraints.items():
            if key[0] == weld and len(key) > 3:
                cost += 400. * np.maximum(0., required - offsets @ direction)
        i = int(cost.argmin())
        movement[weld] = offsets[i]
        print("REIMPORT DIRECTION", vertex, float(min_signed[0]), float(min_signed[i]),
              offsets[i].tolist(), flush=True)
    return movement


def repair(name):
    path = ROOT / f"female-{name}-v2.glb"
    gate = json.loads((ROOT / "checks" / name / "gate.json").read_text())
    assert gate["module_sha256"] == fit.sha(path)
    clips = [clip for clip, row in gate["clips"].items() if row["min_signed_m"] < .0005 or row["max_triangle_pairs"]]
    if not clips:
        return
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = 30, 1.
    arm, body = (scene.objects[label] for label in ("Armature", "Base_Body"))
    names = list(arm.data.bones.keys())
    module = fit.Module(path, names)
    def import_on_female(file):
        imported = load_glb(file)
        mesh, = [obj for obj in imported if obj.type == "MESH" and obj.vertex_groups]
        world = mesh.matrix_world.copy()
        mesh.parent = arm
        mesh.matrix_world = world
        mesh.modifiers.clear()
        mesh.modifiers.new("Female skin", "ARMATURE").object = arm
        dispose(imported - {mesh})
        return mesh

    garment = import_on_female(path)
    dispose(load_glb(MOTION))
    bind(arm, None)
    set_frame(scene, 0.)
    rest = np.asarray(evaluated_points(garment))
    assert len(rest) == len(module.source_points)
    assert np.allclose(rest, module.source_points, atol=2.e-7), "GLB vertex order differs from Blender's"
    rig_inverse = [arm.data.bones[label].matrix_local.inverted() for label in names]
    start = module.points.copy()
    current = start.copy()
    initial_shape = start.copy()
    record_path = path.with_suffix(".fit.json")
    bake_record = json.loads(record_path.read_text())
    budget = min(.012, fit.CAP - bake_record["max_baked_clearance_offset_m"])
    envelope = initial_shape.copy()
    if name == "tshirt":
        base = fit.Module(ROOT / ".runtime/female-tshirt.glb", names)
        assert np.array_equal(module.source_faces, base.source_faces)
        envelope = module.welded(base.source_points).astype(np.float32)
        budget = .010
    if budget <= 0:
        return
    cap = fit.CAP if name == "tshirt" else budget
    preserve_images(module)
    scratch = ROOT / ".runtime" / f"probe-{name}.glb"

    def put_points(points):
        nonlocal garment
        module.write(scratch, points, module.weights)
        dispose({garment})
        garment = import_on_female(scratch)
        bind(arm, None)
        set_frame(scene, 0.)
        exported = np.asarray(evaluated_points(garment))
        assert np.allclose(exported, points[module.unweld], atol=2.e-7)
        bpy.context.view_layer.update()

    def sweep(keep_frames=False):
        reports = []
        constraints = {}
        evidence = []
        for clip in clips:
            action = None if clip == "rest" else bpy.data.actions[clip]
            bind(arm, action)
            triangular = clip not in (*SHARED, "rest")
            body_faces, clothing_faces = faces(body.data, triangular), faces(garment.data, triangular)
            body_tris, cloth_tris = faces(body.data, True), faces(garment.data, True)
            body_faces_ar, cloth_faces_ar = np.array(body_tris), np.array(cloth_tris)
            count, overlap, minimum = 0, 0, 9.
            representative = []
            for index_frame, frame in enumerate(samples(*action.frame_range) if action else [0.]):
                set_frame(scene, frame)
                points = evaluated_points(garment)
                skin = np.asarray([arm.pose.bones[label].matrix @ m for label, m in zip(names, rig_inverse)])
                body_points = evaluated_points(body)
                tree = BVHTree.FromPolygons(body_points, body_faces, all_triangles=triangular)
                overlaps = tree.overlap(BVHTree.FromPolygons(points, clothing_faces, all_triangles=triangular))
                overlap = max(overlap, len(overlaps))
                inside = 0
                low = 9.
                for index, point in enumerate(points):
                    location, normal, _, _ = tree.find_nearest(point)
                    signed = (point - location).dot(normal)
                    minimum = min(minimum, signed)
                    low = min(low, signed)
                    inside += signed < 0.
                    if signed >= .00056:
                        continue
                    matrix = np.einsum("j,jik->ik", module.weights[index], skin[:, :3, :3])
                    direction = np.asarray(normal) @ matrix
                    magnitude = np.linalg.norm(direction)
                    if magnitude < .1:
                        continue
                    direction /= magnitude
                    req = min(fit.CAP, (fit.MARGIN - signed) / magnitude)
                    weld = module.unweld[index]
                    axis = np.abs(direction).argmax()
                    key = (weld, int(axis), bool(direction[axis] >= 0))
                    if key not in constraints or req > constraints[key][0]:
                        constraints[key] = (req, direction)
                if name == "tshirt" and overlaps:
                    if triangular:
                        tri_pairs = overlaps
                    else:
                        tri_body = BVHTree.FromPolygons(body_points, body_tris, all_triangles=True)
                        tri_cloth = BVHTree.FromPolygons(points, cloth_tris, all_triangles=True)
                        tri_pairs = tri_body.overlap(tri_cloth)
                    pairs = np.asarray(tri_pairs, dtype=np.int32).reshape(-1, 2)[:, ::-1]
                    xyz = np.asarray(points, dtype=np.float32)
                    strongest = []
                    if len(pairs):
                        face_ids, coefficients = fit.SOURCE["pair_witnesses"](
                            xyz, cloth_faces_ar, np.asarray(body_points, dtype=np.float32),
                            body_faces_ar, pairs, dense=False)
                        corners = cloth_faces_ar[face_ids]
                        positions = np.einsum("ij,ijk->ik", coefficients, xyz[corners])
                        distances, _, outward, _ = fit.nearest(tree, positions)
                        order = np.lexsort((distances, face_ids))
                        strongest = order[np.r_[True, np.diff(face_ids[order]) != 0]]
                    for hit in strongest:
                        for column, index in enumerate(corners[hit]):
                            if coefficients[hit, column] < .19:
                                continue
                            matrix = np.einsum("j,jik->ik", module.weights[index], skin[:, :3, :3])
                            direction = outward[hit] @ matrix
                            norm = np.linalg.norm(direction)
                            if norm < .1:
                                continue
                            direction /= norm
                            req = max(0., (fit.MARGIN - distances[hit]) * .64 / norm)
                            axis = int(np.abs(direction).argmax())
                            key = (module.unweld[index], axis, bool(direction[axis] >= 0), "face")
                            if key not in constraints or req > constraints[key][0]:
                                constraints[key] = (req, direction)
                if keep_frames:
                    snapshot = (tree, np.asarray(points, dtype=np.float32), skin)
                    priority = len(overlaps) + 5 * inside + max(0., .00062 - low) * 600.
                    if index_frame % 19 == 0:
                        evidence.append(snapshot)
                    representative.append((priority, snapshot))
                    representative.sort(key=lambda item: item[0], reverse=True)
                    del representative[7:]
                count = max(count, inside)
            evidence.extend(snapshot for _, snapshot in representative)
            reports.append(dict(clip=clip, min_signed_m=minimum, inside=count, pairs=overlap))
        score = sum(row["inside"] * 50 + row["pairs"] * 20 + max(0., .00053 - row["min_signed_m"]) * 1000
                    for row in reports)
        return score, reports, constraints, evidence

    score, reports, constraints, evidence = sweep(keep_frames=True)
    print("REIMPORT BEFORE", name, score, reports, flush=True)
    history = []
    for _ in range(3 if name == "tshirt" else 5):
        if score == 0 or not constraints:
            break
        change = clearance_trials(module, current, constraints, evidence, budget, envelope, cap)
        candidate = envelope + fit.SOURCE["limit_delta"](current + change - envelope, cap)
        put_points(candidate)
        value, after, witnesses, next_evidence = sweep(keep_frames=True)
        print("REIMPORT DIRECTION TRIAL", name, value, after, flush=True)
        if value >= score:
            break
        current, score, reports, constraints, evidence = candidate, value, after, witnesses, next_evidence
        history.append(dict(method="nearest face tie search", score=value, rows=after))
    if history:
        preserve_images(module)
        module.write(path, current, module.weights)
        bake_record.update(output_sha256=fit.sha(path), reimport_witness_repairs=history,
                           max_reimport_adjustment_m=float(np.linalg.norm(current-start, axis=1).max()))
        if name == "tshirt":
            bake_record["max_baked_clearance_offset_m"] = float(np.linalg.norm(current-envelope, axis=1).max())
        record_path.write_text(json.dumps(bake_record, indent=2) + "\n")


if __name__ == "__main__":
    for label in arguments():
        repair(label)
