"""Reopen the saved source and re-import the exported GLB in Blender; write reports/sources.json."""
from pathlib import Path
import hashlib
import json

import bpy

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "sources" / "water-polo-ball.blend"
GLB = HERE / "exports" / "optimized.glb"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


before = sha(SOURCE)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
root = bpy.data.objects["ASSET_WaterPoloBall"]
ball = bpy.data.objects['BALL_Panels']
backing = bpy.data.objects['BALL_RecessedBacking']
assert ball.type == 'MESH' and backing.type == 'MESH'
assert len(ball.data.polygons) > 1000 and ball.data.uv_layers
image = next(i for i in bpy.data.images if i.name.startswith('T_Grip_Normal'))
assert list(image.size) == [1024, 512]
assert root['panel_count'] in (18,32)
source = {
    'editable_meshes': sorted(o.name for o in root.children_recursive if o.type=='MESH'),
    'panel_count': root['panel_count'], 'layout':root['layout'],
    'modifiers': 'None required: editable tessellated panels and recessed backing are explicit mesh geometry',
    'normal_map': {'size':list(image.size), 'filepath':image.filepath},
    'root_properties': {k:root[k] for k in root.keys()},
}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(GLB))
meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
depsgraph = bpy.context.evaluated_depsgraph_get()
triangles = 0
for obj in meshes:
    mesh = obj.evaluated_get(depsgraph).to_mesh()
    mesh.calc_loop_triangles()
    triangles += len(mesh.loop_triangles)
    obj.evaluated_get(depsgraph).to_mesh_clear()
imported = {
    "objects": sorted(obj.name for obj in bpy.context.scene.objects),
    "mesh_objects": len(meshes),
    "triangles": triangles,
    "materials": sorted(m.name for m in bpy.data.materials if m.users),
    "images": sorted(i.name for i in bpy.data.images if i.users),
    "dimensions_m": [round(v, 5) for v in meshes[0].dimensions],
}
assert "ASSET_WaterPoloBall" in imported["objects"] and imported["triangles"] > 0
assert imported["images"], "normal map survived glTF round trip"
assert sha(SOURCE) == before, 'inspection must not modify the source'
expected=json.loads((HERE/'reports/assets.json').read_text())
assert triangles == expected['triangles']
report = {
    "result": "PASS",
    "blender_version": bpy.app.version_string,
    "source_reopened": True,
    "source_sha256": before,
    "original_source_unchanged": sha(SOURCE) == before,
    "source": source,
    "glb_reimported": True,
    "glb_sha256": sha(GLB),
    "reimport": imported,
}
(HERE / "reports" / "sources.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))

# Avoid the workstation's PulseAudio shutdown hang after all checks and writes complete.
if bpy.app.background:
    import os, sys
    sys.stdout.flush(); sys.stderr.flush(); os._exit(0)
