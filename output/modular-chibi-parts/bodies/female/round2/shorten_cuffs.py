"""Adjust the ankle hem depth on the fitted jeans after the outfit pose check."""
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import fit_module as fit
from glb_io import Glb
from common import arguments
from refit import trim_lower_edge
import verify


def shorten(height):
    jeans = ROOT / "female-jeans-v2.glb"
    evidence = jeans.with_suffix(".fit.json")
    records = json.loads(evidence.read_text())
    previous = float(records.get("hem_cut_height_m") or .134)
    trials = [h for h in (.143, .151, .159, .167, .175, .183, .191, .199) if h > previous + .002] if height is None else [height]
    assert all(previous + .002 < h < .20 for h in trials)
    backup = ROOT / ".runtime" / f"jeans-before-cuff-{int(previous * 1000)}.glb"
    shutil.copyfile(jeans, backup)
    asset = Glb(backup)
    names = [asset.doc["nodes"][i]["name"] for i in asset.doc["skins"][0]["joints"]]
    module = fit.Module(backup, names)
    candidate = ROOT / ".runtime" / "jeans-cuff-trial.glb"
    lookup = verify.asset_path
    verify.asset_path = lambda name: candidate if name == "jeans" else lookup(name)
    for height in trials:
        segments = trim_lower_edge(module, candidate, height, .00075, .0012)
        layers = verify.audit_layers("run")["clips"]["run"]
        gap = min(row["min_axis_gap_mm"] for row in layers["cuff_opening"].values())
        pairs = layers["pairings"]["jeans/sneakers"]["peak_pairs"]
        print("HEM TRIAL", height, pairs, gap, flush=True)
        if pairs or gap <= 0:
            continue
        candidate.replace(jeans)
        primitive, = Glb(jeans).doc["meshes"][0]["primitives"]
        exported = Glb(jeans)
        records.update(output_sha256=fit.sha(jeans), hem_cut_height_m=height,
                       turned_hem_boundary_edges=segments, previous_cuff_sha256=fit.sha(backup),
                       triangles=exported.doc["accessors"][primitive["indices"]]["count"] // 3)
        evidence.write_text(json.dumps(records, indent=2) + "\n")
        print(f"HEM {previous:.3f} -> {height:.3f} m, {segments} finished segments", flush=True)
        return
    raise ValueError("The sampled cuff heights still intersect the opposite sneaker")


if __name__ == "__main__":
    args = arguments()
    shorten(float(args[0]) if args else None)
