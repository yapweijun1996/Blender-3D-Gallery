"""Run the original round-one checking scripts and add outfit layering evidence."""
import json
from pathlib import Path
import sys

import numpy as np
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import audit_modules
import fit_module as fit
from common import HERE, CLIPS, MOTION, MODULES, arguments
from refit import GARMENTS, read_pose_bank


def asset_path(slug):
    stem = f"female-{slug}"
    return (ROOT / f"{stem}-v2.glb") if slug in GARMENTS else (HERE / f"{stem}.glb")


def staged_assets(labels):
    aliases = ROOT / ".runtime" / "modules"
    aliases.mkdir(exist_ok=True)
    for slug in labels:
        alias = aliases / f"female-{slug}.glb"
        if not alias.is_symlink():
            alias.symlink_to(asset_path(slug))
    return aliases


def run_checkers(labels):
    audit_modules.HERE, audit_modules.OUT = staged_assets(labels), ROOT / "checks"
    for slug in labels:
        audit_modules.audit(slug)
        report = json.loads((audit_modules.OUT / slug / "gate.json").read_text())
        assert set(report["clips"]) == set(("rest", *CLIPS))


def audit_layers(only=None):
    names, _, female, rows, matrices = read_pose_bank()
    if only:
        selected = [i for i, row in enumerate(rows) if row[0] == only]
        assert selected, only
        rows = [rows[i] for i in selected]
        matrices = matrices[selected]
    inputs = (*GARMENTS, "sneakers")
    modules = {name: fit.Module(asset_path(name), names) for name in inputs}
    geometry = fit.GEOMETRY
    faces = {key: module.source_faces.tolist() for key, module in modules.items()}
    pairings = (("tshirt", "jeans"), ("jeans", "sneakers"), ("dress", "sneakers"))
    shoe_asset = modules["sneakers"].glb.doc
    collar = next(primitive for primitive in shoe_asset["meshes"][0]["primitives"]
                  if shoe_asset["materials"][primitive["material"]]["name"] == "Purple collar piping")
    collar_index = collar["attributes"]["POSITION"]
    collar_slice = next(sl for attrs, sl in modules["sneakers"].parts if attrs["POSITION"] == collar_index)
    collar_ids = np.arange(collar_slice.start, collar_slice.stop)
    projection_axes = {}
    jeans = modules["jeans"].source_points
    shoes = modules["sneakers"].source_points
    for side, sign in (("Left", 1), ("Right", -1)):
        ankle = names.index(f"mixamorig:{side}Foot")
        knee = names.index(f"mixamorig:{side}Leg")
        up = fit.normalized(female[3][knee] - female[3][ankle])
        shin = fit.normalized(matrices[:, knee, :, :3] @ up)
        hem = (sign * jeans[:, 0] > 0) & (jeans[:, 2] < .20)
        rim = collar_ids[sign * shoes[collar_ids, 0] > 0]
        projection_axes[side] = shin, hem, rim

    by_clip = {}
    for start in range(0, len(rows), 32):
        batch = slice(start, start + 32)
        poses = {label: geometry["skin_positions"](module.source_points,
                    geometry["pose_matrices"](matrices[batch], module.weights))
                 for label, module in modules.items()}
        projections = {}
        for side, (shin, hem, rim) in projection_axes.items():
            floor = np.einsum("fvi,fi->fv", poses["jeans"][:, hem], shin[batch]).min(axis=1)
            opening = np.einsum("fvi,fi->fv", poses["sneakers"][:, rim], shin[batch]).max(axis=1)
            projections[side] = floor - opening
        for i, (clip, frame, *_) in enumerate(rows[batch]):
            trees = {label: BVHTree.FromPolygons(pos[i].tolist(), faces[label], all_triangles=True)
                     for label, pos in poses.items()}
            record = by_clip.setdefault(clip, dict(samples=0, pairings={}, cuff_opening={}))
            record["samples"] += 1
            for a, b in pairings:
                overlap = trees[a].overlap(trees[b])
                name = f"{a}/{b}"
                pair = record["pairings"].setdefault(name, dict(peak_pairs=0, affected_samples=0))
                if overlap:
                    pair["affected_samples"] += 1
                    ids = np.asarray(overlap, dtype=np.int32)
                    points_a = modules[a].source_points[modules[a].source_faces[ids[:, 0]]]
                    points_b = modules[b].source_points[modules[b].source_faces[ids[:, 1]]]
                    lowest, highest = float(points_a[..., 2].min()), float(points_a[..., 2].max())
                    bounds = pair.get("first_module_contact_rest_z_range_m", (lowest, highest))
                    pair["first_module_contact_rest_z_range_m"] = [min(bounds[0], lowest), max(bounds[1], highest)]
                    if name == "jeans/sneakers":
                        same_side = ((points_a[..., 0].mean(axis=1) >= 0) == (points_b[..., 0].mean(axis=1) >= 0)).sum()
                        pair["same_side_pair_peak"] = max(pair.get("same_side_pair_peak", 0), int(same_side))
                        pair["opposite_side_pair_peak"] = max(pair.get("opposite_side_pair_peak", 0), len(overlap) - int(same_side))
                    if len(overlap) > pair["peak_pairs"]:
                        pair.update(peak_pairs=len(overlap), frame=frame)
            for side, gaps in projections.items():
                mm = float(gaps[i] * 1000)
                current = record["cuff_opening"].get(side)
                if current is None or mm < current["min_axis_gap_mm"]:
                    record["cuff_opening"][side] = {"min_axis_gap_mm": mm, "frame": frame}
    evidence = dict(motion_sha256=fit.sha(MOTION), interval_frames=.5, fps=30,
                    asset_sha256={name: fit.sha(asset_path(name)) for name in modules}, clips=by_clip)
    output = ROOT / ".runtime" / f"layering-{only}.json" if only else ROOT / "layering.json"
    output.write_text(json.dumps(evidence, indent=2) + "\n")
    for name, row in by_clip.items():
        print("LAYERS", name, row, flush=True)
    return evidence


if __name__ == "__main__":
    args = arguments()
    if args and args[0] == "--layers":
        audit_layers(args[1] if len(args) > 1 else None)
    elif args and args[0] == "--witnesses":
        import audit_witnesses
        audit_witnesses.HERE = staged_assets(args[1:])
        check_link = audit_witnesses.HERE / "checks"
        if not check_link.is_symlink():
            check_link.symlink_to(ROOT / "checks", target_is_directory=True)
        for slug in args[1:]:
            audit_witnesses.audit(slug)
    else:
        run_checkers(args or MODULES)
