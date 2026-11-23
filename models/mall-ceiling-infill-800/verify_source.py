"""Reopen the editable source and replay normal, fresh, and edited-source exports."""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent
SLUG = "mall-ceiling-infill-800"
NAME = "ASSET_MallCeilingInfill800"
FINISH = "Mineral fibre underside original seed 422"
source = ROOT / "sources" / (SLUG + ".blend")
export = Path("exports") / (SLUG + ".glb")
digest = lambda file: hashlib.sha256(file.read_bytes()).hexdigest()


def generate(output, *arguments):
    cmd = [bpy.app.binary_path, "-b", "--factory-startup", "-Y", "-t", "2", "--python-exit-code", "1",
           "-P", str(ROOT / "generate.py"), "--", "--output", str(output), "--skip-render", *arguments]
    completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if completed.returncode or "Traceback" in completed.stdout:
        raise RuntimeError(completed.stdout)


def verify(reference):
    bpy.ops.wm.open_mainfile(filepath=str(source))
    root = bpy.data.objects[NAME]
    meshes = [obj for obj in root.children if obj.type == "MESH"]
    assert len(meshes) == 25 and len(root.children) == 29
    for obj in meshes:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        assert all(e.is_manifold for e in bm.edges) and bm.calc_volume(signed=True) > 0, obj.name
        bm.free()
        assert tuple(obj.scale) == (1, 1, 1), obj.name
    assert all(not bpy.data.objects[f"HANGER_TopPlate_{i}"].data.uv_layers for i in range(1, 5))
    image, = [i for i in bpy.data.images if i.packed_file]
    original = reference.parents[1] / "textures" / "mineral-fibre-original.png"
    assert image.packed_file.data == original.read_bytes() == (ROOT / "textures" / image.name).read_bytes()
    assert image.filepath.startswith("//") and all(pack.filepath.startswith("//") for pack in image.packed_files)
    for name in ("PANEL_1", "PANEL_3"):
        panel = bpy.data.objects[name]
        face = next(poly for poly in panel.data.polygons if poly.normal.z < -0.9)
        coords = [panel.data.uv_layers.active.data[i].uv.y for i in face.loop_indices]
        assert abs((max(coords)-min(coords)) / panel.dimensions.y - 0.25 / 0.576) < 0.000002

    with tempfile.TemporaryDirectory(prefix=".edit-proof-", dir=ROOT) as temp:
        output = Path(temp)
        generate(output / "saved", "--export-source", "--source", str(source))
        generate(output / "fresh", "--reference", str(reference))
        expected = (ROOT / export).read_bytes()
        for name in ("saved", "fresh"):
            actual = output / name / export
            assert expected == actual.read_bytes(), f"{name} export {digest(actual)} differs from packaged {digest(ROOT / export)}"
        # Move only one underside down a millimetre. Its local bevel and all other panels stay editable.
        panel = bpy.data.objects["PANEL_1"]
        for vertex in panel.data.vertices:
            if vertex.co.z < 0:
                vertex.co.z -= 0.001
        material = bpy.data.materials[FINISH]
        material.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.71
        edited = output / "edited.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(edited), compress=True)
        generate(output / "edited", "--export-source", "--source", str(edited))
        modified = output / "edited" / export
        assert digest(modified) != digest(ROOT / export)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(modified))
        world = bpy.context.evaluated_depsgraph_get()
        hits = []
        for nx, ny in [(-0.3,-0.3), (0.3,-0.3)]:
            ok, point, _, _, obj, _ = bpy.context.scene.ray_cast(world, Vector((nx, ny, -0.2)), Vector((0, 0, 1)))
            assert ok
            hits.append([obj.name, point.z])
        assert abs(hits[0][1] - 0.007) < 1e-6 and abs(hits[1][1] - 0.008) < 1e-6
        assert abs(bpy.data.materials[FINISH].node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value-0.71) < 1e-5
        return {"blender_version": bpy.app.version_string, "source_sha256": digest(source),
                "reference_source_sha256": digest(reference), "packed_texture_sha256": digest(original),
                "closed_editable_meshes": len(meshes), "connector_empties": 4, "unchanged_panel_uv_density": True,
                "fresh_and_saved_source_glb_sha256": digest(ROOT / export), "edited_export_differs_from_canonical": True,
                "edited_underside_height_m": round(hits[0][1], 6), "other_cut_underside_height_m": round(hits[1][1], 6),
                "edited_material_roughness": 0.71}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, default=ROOT.parent / "mall-ceiling-panel/sources/mall-ceiling-panel-module.blend")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    result = verify(args.reference.resolve())
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports/source-reimport.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
