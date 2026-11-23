"""Inspect exported rest geometry, seams and source rig in a fresh Blender session."""
import json
from pathlib import Path
import runpy
import sys

import bmesh
import bpy
import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
FIT = runpy.run_path(str(HERE / "fit_pants_r6.py"))


def verify():
    glb = FIT["GLB"]
    scene, arm, body, garment, actions = FIT["setup"](glb, merge=False)
    coords = FIT["BASE"]["evaluated_coordinates"]
    faces_of = FIT["faces_of"]
    points = coords(garment)
    faces = faces_of(garment.data)
    body_tree = FIT["tree_for"](coords(body), faces_of(body.data).tolist())
    signed = FIT["signed_hits"]
    distances = signed(body_tree, points)[0]
    panels = points[faces]
    checks = {}
    for name, samples in (
        ("vertices", points),
        ("centroids", panels.mean(axis=1)),
        ("edge_midpoints", ((panels + np.roll(panels, 1, axis=1)) * .5).reshape(-1, 3)),
    ):
        values = signed(body_tree, samples)[0]
        checks[name] = {
            "count": len(values), "minimum_m": float(values.min()), "maximum_m": float(values.max()),
            "over_30_mm": int((values > .03).sum()),
        }
    mesh = bmesh.new()
    mesh.from_mesh(garment.data)
    vertices = len(mesh.verts)
    bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=.000002)
    mesh.edges.index_update()
    loops = []
    for edges in FIT["boundaries"](mesh):
        members = {v for edge in edges for v in edge.verts}
        center = np.array([tuple(v.co) for v in sorted(members, key=lambda v: tuple(v.co))]).mean(axis=0)
        degrees = [sum(v in edge.verts for edge in edges) for v in members]
        name = "waist" if center[2] > .398 else "cuff" if center[2] < .105 else "unexpected"
        loops.append({"edges": len(edges), "center_m": center.tolist(), "location": name,
                      "closed_ring": min(degrees) == max(degrees) == 2})
    irregular = sum(len(edge.link_faces) not in (1, 2) for edge in mesh.edges)
    seen = set()
    components = []
    for vert in mesh.verts:
        if vert in seen:
            continue
        seen.add(vert)
        queue = [vert]
        for current in queue:
            for edge in current.link_edges:
                other = edge.other_vert(current)
                if other not in seen:
                    seen.add(other)
                    queue.append(other)
        components.append(len(queue))
    mesh.free()
    exported = {"exported_vertices": vertices, "triangle_count": len(faces),
                "rest_clearance": checks, "boundary_loops": sorted(loops, key=lambda row: row["center_m"]),
                "irregular_edges": irregular, "connected_component_vertices": sorted(components, reverse=True)}
    del garment, body, arm, actions
    blend = glb.with_suffix(".blend")
    bpy.ops.wm.open_mainfile(filepath=str(blend), load_ui=False, use_scripts=False)
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    editable, = meshes
    armature, = armatures
    output = {
        "glb_sha256": FIT["digest"](glb), "blend_sha256": FIT["digest"](blend), "exported": exported,
        "source": {"objects": sorted(obj.type for obj in bpy.context.scene.objects),
                   "triangles": len(faces_of(editable.data)), "joints": len(armature.data.bones),
                   "skinned_to_armature": any(mod.type == "ARMATURE" and mod.object == armature
                                             for mod in editable.modifiers),
                   "textures_packed": [bool(node.image.packed_file)
                                       for material in editable.data.materials
                                       for node in material.node_tree.nodes if node.type == "TEX_IMAGE"]},
    }
    topology_pass = (irregular == 0 and len(components) == 1
                     and sorted(row["location"] for row in loops) == ["cuff", "cuff", "waist"]
                     and all(row["closed_ring"] for row in loops))
    output["topology_pass"] = topology_pass
    output["rest_vertices_pass"] = bool(distances.min() >= .0005 and distances.max() <= .03)
    FIT["write_json"]("mesh_check.json", output)
    print(json.dumps(output, indent=2), flush=True)


if __name__ == "__main__":
    verify()
