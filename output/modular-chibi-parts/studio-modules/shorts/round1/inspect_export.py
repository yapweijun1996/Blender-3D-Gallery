"""Audit signed rest clearance and intersections of the exported shorts shell."""
import sys
from pathlib import Path

import bpy
import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fit_shorts import BLEND, GLB, SHA, write_json
from render_shorts import setup


def main():
    scene, arm, body, garment, api = setup()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    body_points, body_faces = api["evaluated_arrays"](body, depsgraph)
    body_tree = api["tree_from"](body_points, body_faces)
    gp, gf = api["evaluated_arrays"](garment, depsgraph)
    d = api["nearest"](body_tree, gp)[0]
    corners = gp[gf]
    bary = np.array([[1/3, 1/3, 1/3], [.5, .5, 0], [.5, 0, .5], [0, .5, .5]])
    probes = np.einsum("sk,fkj->fsj", bary, corners).reshape(-1, 3)
    dp = api["nearest"](body_tree, probes)[0]
    xyz, inv = np.unique(gp, axis=0, return_inverse=True)
    faces = inv[gf]
    triangle_tree = api["tree_from"](xyz, faces)
    crossing = [(a, b) for a, b in triangle_tree.overlap(triangle_tree) if a < b and
                not np.isin(faces[a], faces[b]).any()]
    report = dict(glb_sha256=SHA(GLB), vertex_samples=len(d), vertex_min_signed_m=float(d.min()),
                  vertex_max_signed_m=float(d.max()), vertex_above_30mm=int((d > .030).sum()),
                  surface_samples=len(dp), surface_min_signed_m=float(dp.min()), surface_max_signed_m=float(dp.max()),
                  surface_above_30mm=int((dp > .030).sum()), garment_body_pairs=len(body_tree.overlap(triangle_tree)),
                  self_pairs=len(crossing))
    if crossing:
        report["self_pair_examples"] = [xyz[faces[a]].mean(axis=0).tolist() for a, _ in crossing[:25]]
    knees = [float((arm.matrix_world @ arm.data.bones["mixamorig:" + side + "Leg"].head_local).z)
             for side in ("Left", "Right")]
    report.update(garment_low_z_m=float(gp[:, 2].min()), garment_high_z_m=float(gp[:, 2].max()),
                  minimum_hem_above_knee_m=float(gp[:, 2].min()) - max(knees))
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False, use_scripts=False)
    rig, base, shorts = [bpy.context.scene.objects[name]
                         for name in ("Armature", "Base_Body", "Plain_Shorts")]
    bsdf = next(node for node in shorts.active_material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    image = bsdf.inputs["Base Color"].links[0].from_node.image
    assert len(rig.data.bones) == 65 and shorts.parent == rig and shorts.modifiers[0].object == rig
    assert base.hide_get() and base.hide_render and image.packed_file and len(shorts.data.polygons) == len(gf)
    report.update(blend_sha256=SHA(BLEND), blend_bytes=BLEND.stat().st_size,
                  editable_reference_hidden=True, editable_texture_packed=True)
    write_json("rest_check.json", report)
    print(report, flush=True)


if __name__ == "__main__":
    main()
