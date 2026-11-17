"""Inspect saved topology, then exercise a real mesh/material edit on a copy."""
from pathlib import Path
import hashlib
import importlib.util
import json
import bmesh
import bpy

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "sources" / "restaurant-food-props.blend"
before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
root = bpy.data.objects["ASSET_RestaurantFoodProps"]
meshes = sorted((obj for obj in root.children_recursive if obj.type == "MESH"), key=lambda obj: obj.name)
assert len(meshes) == 11
assert tuple(root.location) == (0, 0, 0)
assert bpy.context.scene.unit_settings.system == "METRIC"
assert bpy.context.scene.unit_settings.scale_length == 1
assert not any(obj.type == "FONT" for obj in bpy.data.objects)
assert len({mat for obj in meshes for mat in obj.data.materials}) == 1
parts = {}
for obj in meshes:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    assert all(edge.is_manifold for edge in bm.edges), obj.name
    assert bm.calc_volume() > 0, obj.name
    assert all(face.calc_area() > 1e-12 for face in bm.faces), obj.name
    parts[obj.name] = {"vertices": len(bm.verts), "faces": len(bm.faces), "volume_m3": bm.calc_volume(), "manifold": True}
    bm.free()
target = bpy.data.objects["DISH_Sauce_Ramekin"]
target_name = target.name
for vertex in target.data.vertices:
    vertex.co.x *= .92
material = target.data.materials[0]
material.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = .77
out = HERE / "reports" / "source-edit"
out.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out / "restaurant-food-props-edited.blend"), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(out / "restaurant-food-props-edited.blend"))
assert bpy.data.objects[target_name].data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value > .769
spec = importlib.util.spec_from_file_location("restaurant_generator", HERE / "generate.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
generator.export(out / "edited.glb")
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == before
report = {"result": "PASS", "blender_version": bpy.app.version_string, "source_reopened": True,
          "editable_mesh_parts": len(meshes), "materials": 1, "text_objects": 0, "units": "metres",
          "source_sha256": before, "original_source_unchanged": True, "parts": parts,
          "edit": "Ramekin local mesh X scaled by 0.92; shared material roughness set to 0.77; saved, reopened and exported",
          "edited_glb_sha256": hashlib.sha256((out / "edited.glb").read_bytes()).hexdigest(),
          "scope": "Closed manifold solids per component; intentional food-layer contacts, no general self-intersection proof"}
(HERE / "reports" / "sources.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
