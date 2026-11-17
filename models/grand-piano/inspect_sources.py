"""Reopen, inspect and edit a disposable source copy; never overwrite the asset."""
from pathlib import Path
import hashlib
import importlib.util
import json
import tempfile
import sys

import bmesh
import bpy

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
source = HERE / "sources" / "grand-piano.blend"
before = hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
root = bpy.data.objects["ASSET_GrandPiano"]
assert tuple(root.location) == (0, 0, 0)
assert bpy.context.scene.unit_settings.system == "METRIC"
assert bpy.context.scene.unit_settings.scale_length == 1
meshes = [obj for obj in root.children_recursive if obj.type == "MESH"]
materials = {mat.name for obj in meshes for mat in obj.data.materials}
assert len(materials) == 2
assert len([obj for obj in meshes if obj.name.startswith("KEY_White_")]) == 52
assert len([obj for obj in meshes if obj.name.startswith("KEY_Black_")]) == 36
assert sorted(obj["midi_note"] for obj in meshes if obj.name.startswith("KEY_")) == list(range(21, 109))
assert not any(obj.type == "FONT" for obj in bpy.data.objects)
for prefix in ("CASE_", "KEY_", "LID_", "LEG_", "CASTER_", "LYRE_", "PEDAL_", "MUSIC_", "BENCH_", "HARP_"):
    assert any(obj.name.startswith(prefix) for obj in meshes), prefix
depsgraph = bpy.context.evaluated_depsgraph_get()
for obj in meshes:
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    assert all(edge.is_manifold for edge in bm.edges), obj.name
    assert bm.calc_volume() > 0, obj.name
    bm.free()
    evaluated.to_mesh_clear()
for name in ("collider_box", "collider_box_bench"):
    collider = bpy.data.objects[name]
    assert collider.type == "MESH" and not collider.data.materials
    assert collider.hide_get() and collider.hide_render

# Exercise a saved geometric and material edit through the same merged export path.
target = bpy.data.objects["PEDAL_Paddle_0"]
edited_name = target.name
for vertex in target.data.vertices:
    vertex.co.x *= 0.85
target.data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.62
out = Path(tempfile.gettempdir()) / "grand-piano-source-edit"
out.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out / "edited.blend"), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(out / "edited.blend"))
module_spec = importlib.util.spec_from_file_location("piano_generator", HERE / "generate.py")
generator = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(generator)
generator.export(out / "edited.glb")
assert hashlib.sha256(source.read_bytes()).hexdigest() == before
report = {
    "result": "PASS", "blender_version": bpy.app.version_string,
    "source_reopened": True, "editable_meshes": len(meshes),
    "closed_manifold_meshes": len(meshes), "intentional_flat_pattern_meshes": 0,
    "hidden_material_free_colliders": 2, "materials": len(materials),
    "source_sha256": before, "original_source_unchanged": True,
    "edited_mesh": edited_name, "edit": "Pedal mesh X scaled by 0.85; shared metal roughness set to 0.62",
    "edited_glb": str(out / "edited.glb"),
    "edited_glb_sha256": hashlib.sha256((out / "edited.glb").read_bytes()).hexdigest(),
}
(HERE / "reports" / "sources.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
