"""Verify that the cached master's tested triangles are the shipped GLB surface."""
from collections import Counter
import json
from pathlib import Path
import sys

import numpy as np
from mathutils.kdtree import KDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BODY, HERE, MASTER
import fit_module as fit


def oriented(faces):
    return Counter(min((a, b, c), (b, c, a), (c, a, b)) for a, b, c in faces.tolist())


def audit():
    names, _, female, *_ = fit.load_rest()
    master, triangles, weights = female[:3]
    exported = fit.Module(BODY, names)
    tree = KDTree(len(master))
    for i, coordinates in enumerate(master):
        tree.insert(coordinates, i)
    tree.balance()
    match = [tree.find(p) for p in exported.source_points]
    mapping = np.array([hit[1] for hit in match])
    errors = np.array([hit[2] for hit in match])
    weld_master = np.array([min(hit[1] for hit in tree.find_range(point, .000002)) for point in master])
    reference = oriented(weld_master[triangles])
    actual = oriented(weld_master[mapping[exported.source_faces]])
    surface = set(triangles.ravel().tolist())
    matched = set(weld_master[mapping].tolist())
    contract = dict(master_sha256=fit.sha(MASTER), body_sha256=fit.sha(BODY),
                    master_triangles=len(triangles), glb_triangles=len(exported.source_faces),
                    missing_triangle_copies=sum((reference - actual).values()),
                    extra_triangle_copies=sum((actual - reference).values()),
                    max_surface_vertex_delta_mm=float(errors.max() * 1000),
                    max_weight_delta=float(abs(weights[mapping] - exported.weights).max()),
                    loose_master_vertices=sorted(set(range(len(master))) - surface),
                    unmatched_surface_position_ids=sorted(set(weld_master[list(surface)]) - matched))
    print("SURFACE", contract, flush=True)
    (HERE / "surface-audit.json").write_text(json.dumps(contract, indent=2) + "\n")
    assert not contract["extra_triangle_copies"] and not contract["missing_triangle_copies"]
    assert contract["max_surface_vertex_delta_mm"] < .002
    assert contract["max_weight_delta"] < .00001


if __name__ == "__main__":
    audit()
