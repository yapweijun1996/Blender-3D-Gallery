"""Inspect the saved Blender source passed on the command line."""

import json

import bmesh
import bpy


def inspect_level(level):
    collection = bpy.data.collections[level]
    root = collection.objects["ASSET_EscalatorFloorTransition2m_" + level]
    profile = collection.objects["PROFILE_TerminalReturn_" + level]
    assert root.type == "EMPTY"
    assert profile.type == "MESH" and profile.parent == root
    assert len(collection.objects) == 2
    assert root.location.length < 1e-9
    assert root.scale.x == root.scale.y == root.scale.z == 1

    mesh = bmesh.new()
    mesh.from_mesh(profile.data)
    assert all(edge.is_contiguous and edge.is_manifold for edge in mesh.edges)
    assert all(face.calc_area() > 1e-12 for face in mesh.faces)
    euler_characteristic = len(mesh.verts) - len(mesh.edges) + len(mesh.faces)
    assert euler_characteristic == 2
    signed_volume = mesh.calc_volume(signed=True)
    slab_volume = 2 * 0.120 * 0.100
    recess_volume = 1.56 * 0.025 * 0.085
    assert abs(signed_volume - (slab_volume - recess_volume)) < 0.0000006
    result = {
        "level": level,
        "editableVertices": len(mesh.verts),
        "sourceFaces": len(mesh.faces),
        "closedOrientableShell": True,
        "signedVolume": signed_volume,
    }
    mesh.free()
    return result


levels = [inspect_level(f"LOD{index}") for index in range(3)]
assert not bpy.data.libraries
assert bpy.context.scene.unit_settings.system == "METRIC"
print("SOURCE_CHECK " + json.dumps({"levels": levels, "externalLibraries": 0}))
