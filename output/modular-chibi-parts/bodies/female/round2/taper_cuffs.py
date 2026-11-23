"""Test a closer ankle cuff against the opposite sneaker in the running clip."""
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import fit_module as fit
from common import arguments
from refit import bake_offset, read_pose_bank, smoothstep, limit, preserve_images, scan_in_batches, trim_lower_edge
import verify


def affected_calf(module, shoes, rows, matrices):
    pose = fit.GEOMETRY
    jeans_poses = pose["skin_positions"](module.source_points, pose["pose_matrices"](matrices, module.weights))
    shoe_poses = pose["skin_positions"](shoes.source_points, pose["pose_matrices"](matrices, shoes.weights))
    hits = np.zeros(len(module.faces), dtype=np.int32)
    for frame, denim, sneakers in zip(rows, jeans_poses, shoe_poses, strict=True):
        a, b = fit.tree_from(denim, module.source_faces), fit.tree_from(sneakers, shoes.source_faces)
        edges = np.asarray(a.overlap(b), dtype=np.int32).reshape(-1, 2)
        if len(edges):
            np.add.at(hits, edges[:, 0], 1)
    risk = np.zeros(len(module.points), dtype=np.float32)
    risk[module.faces[hits > 0].ravel()] = 1
    for _ in range(8):
        risk = np.maximum(risk, .965 * fit.average(risk, module.graph))
    return risk


def run(fade):
    names, _, female, rows, matrices = read_pose_bank()
    folder = ROOT / ".runtime"
    current = ROOT / "female-jeans-v2.glb"
    trace_path = current.with_suffix(".fit.json")
    record = json.loads(trace_path.read_text())
    original = fit.Module(folder / "jeans-before-cuff-134.glb", names)
    shoe = fit.Module(verify.asset_path("sneakers"), names)
    selected = [i for i in range(len(rows)) if rows[i][0] == "run"]
    motion = [rows[i] for i in selected]
    run_matrices = matrices[selected]
    risk = affected_calf(original, shoe, motion, run_matrices)
    z = original.points[:, 2]
    taper = risk * (1 - smoothstep(*fade, z))
    taper[(taper < .032) | (z > fade[1])] = 0
    print("CALF CONTACTS", int((taper > 0).sum()), "welded vertices", flush=True)

    vertices, triangles, body_weights, _, regions = female
    nearest_point = original.points.copy()
    nearest_normal = np.zeros_like(nearest_point)
    mapped = original.welded(original.weights).astype(np.float32)
    for side, sign in (("Left", 1), ("Right", -1)):
        ids = np.flatnonzero((taper > 0) & (sign * original.points[:, 0] >= 0))
        if not len(ids):
            continue
        calf = triangles[regions == f"{side} leg"]
        tree = fit.tree_from(vertices, calf)
        _, places, directions, index = fit.nearest(tree, original.points[ids])
        corners = calf[index]
        bary = fit.barycentric(vertices[corners], places)
        nearest_point[ids], nearest_normal[ids] = places, directions
        mapped[ids] = np.einsum("vi,vij->vj", bary, body_weights[corners])
    preserve_images(original)
    variant = folder / "tapered-cuff-trial.glb"
    lookup = verify.asset_path
    verify.asset_path = lambda name: variant if name == "jeans" else lookup(name)
    near_cuff = original.source_points[:, 2] < .232
    cuff_faces = near_cuff[original.source_faces].any(axis=1)
    cuff_vertices, cuff_indices = np.unique(original.source_faces[cuff_faces], return_inverse=True)
    compact = SimpleNamespace(points=original.points, graph=original.graph, unweld=original.unweld[cuff_vertices],
                              source_faces=cuff_indices.reshape(-1, 3))

    def calf_scan(shape, weights):
        return scan_in_batches(compact, shape, weights[cuff_vertices], rows, matrices)

    def good_at_cuff(result):
        d, overlaps, hits = result[:3]
        print("TAPER BODY CUFF", float(d.min()), int((d < 0).sum(axis=1).max()),
              "local pairs", int(hits.sum()), "peak", int(overlaps.max()), flush=True)
        return d.min() >= .00052 and not hits.any()

    def clears_shoe(shape, weights, strength, clearance):
        original.write(variant, shape, weights)
        evidence = verify.audit_layers("run")["clips"]["run"]
        pairs = evidence["pairings"]["jeans/sneakers"]["peak_pairs"]
        gap = min(v["min_axis_gap_mm"] for v in evidence["cuff_opening"].values())
        print("TAPER", strength, clearance, pairs, gap, flush=True)
        return pairs == 0 and gap > 0

    for strength, clearance in ((1., .0018), (1., .0016), (1., .0010)):
        blend = strength * taper
        relieved = nearest_point + clearance * nearest_normal
        movement = blend[:, None] * (relieved - original.points)
        shape = original.points + limit(movement, fit.CAP)
        mix = blend[original.unweld, None]
        weights = fit.limit_weights(((1 - mix) * original.weights + mix * mapped[original.unweld]).astype(np.float32))
        weights[mix[:, 0] == 0] = original.weights[mix[:, 0] == 0]
        if not clears_shoe(shape, weights, strength, clearance):
            continue
        body = calf_scan(shape, weights)
        hem_height = .134
        if not good_at_cuff(body):
            correction = bake_offset(compact, body, shape, original.points) - shape
            correction[z > .228] = 0
            smallest = (int(body[2].sum()), shape, body)
            for amount in (.24, .41):
                adjusted = shape + amount * limit(correction, .0025)
                if not clears_shoe(adjusted, weights, strength, clearance):
                    continue
                checked = calf_scan(adjusted, weights)
                if int(checked[2].sum()) < smallest[0]:
                    smallest = int(checked[2].sum()), adjusted, checked
                if good_at_cuff(checked):
                    shape = adjusted
                    break
            else:
                pairs, shape, checked = smallest
                if pairs > 15 or not pairs:
                    continue
                crossed = original.source_faces[cuff_faces][checked[2] > 0]
                highest = float(shape[original.unweld[crossed]][..., 2].max())
                hem_height = max(.140, highest + .0013)
                print("TAPER CONTACT HEIGHT", highest, "m, trial cut", hem_height, flush=True)
                if hem_height >= .178:
                    continue
                original.write(variant, shape, weights)
                shaped = fit.Module(variant, names)
                recut = folder / "tapered-cuff-recut.glb"
                segments = trim_lower_edge(shaped, recut, hem_height, .00075, .0012)
                recut.replace(variant)
                sampled = verify.audit_layers("run")["clips"]["run"]
                if sampled["pairings"]["jeans/sneakers"]["peak_pairs"]:
                    continue
                shaped = fit.Module(variant, names)
                under = shaped.source_points[:, 2] < .232
                triangles = shaped.source_faces[under[shaped.source_faces].any(axis=1)]
                selected_vertices, remap = np.unique(triangles, return_inverse=True)
                region = SimpleNamespace(unweld=shaped.unweld[selected_vertices], source_faces=remap.reshape(-1, 3))
                if not good_at_cuff(scan_in_batches(region, shaped.points, shaped.weights[selected_vertices], rows, matrices)):
                    continue
                record["turned_hem_boundary_edges"] = segments
        shutil.copyfile(current, folder / "jeans-cropped-verified.glb")
        variant.replace(current)
        record.update(output_sha256=fit.sha(current), hem_cut_height_m=hem_height,
                      triangles=len(fit.Module(current, names).faces), taper_offset_m=float(np.linalg.norm(shape-original.points, axis=1).max()),
                      opposite_sneaker_taper=dict(strength=strength, clearance_m=clearance,
                                                  fade_height_m=fade, tested_run_pair_peak=0))
        trace_path.write_text(json.dumps(record, indent=2) + "\n")
        return


if __name__ == "__main__":
    args = arguments()
    run(tuple(map(float, args)) if args else (.195, .226))
