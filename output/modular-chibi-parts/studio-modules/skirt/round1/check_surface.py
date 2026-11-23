"""Measure skirt wall self-contacts in the exported visual checkpoints."""
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fit_skirt import GLB, HERE, coords, digest, faces, import_exported, load_actions, make_tree, set_pose, write_json


def main():
    import json

    scene,arm,_,garment = import_exported(GLB)
    with np.load(HERE/"fit_offsets.npz") as checkpoint:
        outer_and_inner = checkpoint["points"]
    rest = coords(garment,evaluated=True)
    fit_distance = np.square(rest[:,None] - outer_and_inner[None]).sum(axis=2)
    source_ids = fit_distance.argmin(axis=1)
    is_cloth = fit_distance[np.arange(len(rest)),source_ids] < 1e-10
    triangles = faces(garment)
    triangles = triangles[is_cloth[triangles].all(axis=1)]
    assert len(triangles) == 2816
    positions = np.flatnonzero(is_cloth)
    unique_ids, first = np.unique(source_ids[positions],return_index=True)
    representatives = positions[first]
    welded = np.searchsorted(unique_ids,source_ids[triangles])
    actions = load_actions(scene)
    render_manifest = json.loads((HERE/"render_manifest.json").read_text())
    assert render_manifest["glb_sha256"] == digest(GLB)
    checkpoints = {"rest":1,**{view["clip"]:view["frame"] for view in render_manifest["views"]
                               if view["clip"]!="rest"}}
    report = {}
    for clip,frame in checkpoints.items():
        set_pose(scene,arm,actions.get(clip),frame)
        xyz = coords(garment,evaluated=True)[representatives]
        tree = make_tree(xyz,welded)
        pairs = [(i,j) for i,j in tree.overlap(tree)
                 if i<j and not set(welded[i]).intersection(welded[j])]
        report[clip] = {"frame":frame,"disjoint_face_pairs":len(pairs)}
        print(clip,frame,len(pairs),flush=True)
    write_json("surface_review.json",{"glb_sha256":digest(GLB),
                                    "scope":"Cloth wall and rim triangle pairs with no shared vertex. Buckle excluded.",
                                    "samples":report})


if __name__ == "__main__":
    main()
