"""Reopen the canonical source, re-export it, and prove a disposable artist edit survives."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import sys

import bmesh
import bpy

HERE = Path(__file__).resolve().parent
SLUG = "mall-bakery-serving-tongs"
SOURCE = HERE / "sources" / (SLUG + ".blend")
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("bake_tongs", HERE / "generate.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def exports(path):
    return {entry.name: digest(entry) for entry in sorted((path / "exports").glob("*.glb"))}


source_hash = digest(SOURCE)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
assert bpy.context.scene.unit_settings.system == "METRIC"
assert not bpy.data.libraries
assert not [image for image in bpy.data.images if image.filepath and image.source == "FILE"]
levels = {}
for level in range(3):
    objects = [obj for obj in bpy.data.collections["LOD" + str(level)].objects if obj.type == "MESH"]
    for obj in objects:
        mesh = bmesh.new()
        mesh.from_mesh(obj.data)
        assert all(e.is_manifold and e.is_contiguous for e in mesh.edges), obj.name
        assert all(face.calc_area() > 1e-12 for face in mesh.faces), obj.name
        assert mesh.calc_volume(signed=True) > 0, obj.name
        mesh.free()
    levels["LOD" + str(level)] = {"editableClosedMeshes": len(objects)}

released = exports(HERE)
assert len(released) == 3
with tempfile.TemporaryDirectory(prefix="bakery-source-") as tmp:
    scratch = Path(tmp)
    (scratch / "exports").mkdir()
    generator.HERE = scratch
    generator.export_levels()
    reopened = exports(scratch)
    assert reopened == released, (reopened, released)
    jaw = bpy.data.objects["Soft_scalloped_jaw_Near_LOD0"]
    changed = 0
    for vert in jaw.data.vertices:
        if vert.co.x > .085:
            vert.co.z += .0015
            changed += 1
    assert changed
    bpy.ops.wm.save_as_mainfile(filepath=str(scratch / "changed.blend"), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(scratch / "changed.blend"), load_ui=False)
    generator.export_levels()
    edited = exports(scratch)
    different = [name for name in released if edited[name] != released[name]]
    assert different == [SLUG + ".glb"], different
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(scratch / "exports" / (SLUG + ".glb")))
    vertices = [obj.matrix_world @ v.co for obj in bpy.context.scene.objects if obj.type == "MESH"
                for v in obj.data.vertices]
    assert max(v.z for v in vertices if v.x > .085 and v.y < 0) > .024
assert digest(SOURCE) == source_hash
report = {"result": "pass", "blender": bpy.app.version_string, "sourceSha256": source_hash,
          "levels": levels, "savedSourceByteIdenticalExports": released,
          "editedPositiveXNearJawVertices": changed, "editedLod0Only": different,
          "editedReimportedJawHeightAbove24mm": True, "canonicalSourceUnchanged": True}
(HERE / "reports/source.json").write_text(json.dumps(report, indent=2) + "\n")
