"""Inspect the canonical native source without saving or changing it."""
import json

import bmesh
import bpy

levels = []
for name in ("LOD0", "LOD1", "LOD2"):
    collection = bpy.data.collections[name]
    root = collection.objects["ASSET_CartReturnBay_" + name]
    assert root.type == "EMPTY" and root.location.length < 1e-8
    meshes = [obj for obj in collection.objects if obj.type == "MESH"]
    assert all(obj.parent == root for obj in meshes)
    assert {obj["export_region"] for obj in meshes} == {"Left", "Right", "Rear", "Divider"}
    assert len([obj for obj in meshes if "_foot_" in obj.name]) == 6
    for obj in meshes:
        native = bmesh.new()
        native.from_mesh(obj.data)
        assert all(edge.is_manifold for edge in native.edges), obj.name
        assert all(face.calc_area() > 1e-12 for face in native.faces), obj.name
        assert native.calc_volume(signed=True) > 0, obj.name
        native.free()
    levels.append({"level": name, "editableClosedMeshes": len(meshes)})
assert levels[0]["editableClosedMeshes"] > levels[1]["editableClosedMeshes"] > levels[2]["editableClosedMeshes"]
print("SOURCE_CHECK " + json.dumps({"metres": bpy.context.scene.unit_settings.scale_length,
                                    "externalLibraries": len(bpy.data.libraries), "levels": levels}))
