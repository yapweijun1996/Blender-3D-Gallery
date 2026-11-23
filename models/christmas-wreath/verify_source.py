"""Reopen the source in Blender, test an isolated edit and compare two GLB rebuilds."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory

import bmesh
import bpy

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
sys.dont_write_bytecode = True
import generate


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def gltf_json(path):
    data = path.read_bytes()
    length = struct.unpack_from("<I", data, 12)[0]
    return json.loads(data[20 : 20 + length]), data[28 + length :]


def check_hardware(mesh):
    topology = bmesh.new()
    topology.from_mesh(mesh)
    assert all(e.is_manifold and e.is_contiguous for e in topology.edges)
    remaining = set(topology.verts)
    components = 0
    while remaining:
        components += 1
        frontier = [remaining.pop()]
        while frontier:
            vertex = frontier.pop()
            neighbors = {e.other_vert(vertex) for e in vertex.link_edges} & remaining
            remaining.difference_update(neighbors)
            frontier.extend(neighbors)
    topology.free()
    assert components == 3
    return components


def check_source():
    scene = bpy.context.scene
    root = bpy.data.objects[generate.ROOT]
    meshes = list(root.children_recursive)
    assert scene.unit_settings.system == "METRIC" and scene.unit_settings.scale_length == 1
    assert list(root.scale) == [1, 1, 1] and list(root.location) == [0, 0, 0]
    assert {o.type for o in meshes} == {"MESH"} and not bpy.data.libraries
    assert all(not image.filepath for image in bpy.data.images)
    assert all(len(o.data.vertices) and len(o.data.polygons) for o in meshes)
    assert len({o.users_collection[0].name for o in meshes}) == 4
    for o in meshes:
        copy = o.data.copy()
        assert not copy.validate(clean_customdata=False), o.name
        bpy.data.meshes.remove(copy)
    sprigs = [
        g
        for o in meshes
        for g in o.vertex_groups
        if g.name.startswith(("Sprig ", "Flat cedar spray "))
    ]
    assert len(sprigs) == 75
    hardware = check_hardware(bpy.data.objects["Rear keyhole and twin wire lashings"].data)
    return {
        "source_mesh_objects": len(meshes),
        "editable_sprigs": len(sprigs),
        "closed_hanger_components": hardware,
    }


def run(scratch):
    source = generate.SOURCE
    original = BASE / "exports" / "christmas-wreath.glb"
    original_source_hash = digest(source)
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    findings = check_source()
    saved = scratch / "from-saved.glb"
    generate.export(saved)
    generated = scratch / "fresh.glb"
    fresh_source = scratch / "fresh.blend"
    generate.build(fresh_source)
    generate.export(generated)
    assert digest(saved) == digest(generated) == digest(original)
    try:
        generate.build(source)
    except FileExistsError:
        pass
    else:
        raise AssertionError("Fresh builds must protect an existing source.")
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    name = "Woodland pine cone 1"
    bpy.data.objects[name].location.z += 0.012
    edit = scratch / "artist-edit.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(edit), compress=True, relative_remap=False)
    bpy.ops.wm.open_mainfile(filepath=str(edit), load_ui=False)
    edited = scratch / "artist-edit.glb"
    generate.export(edited)
    original_doc, original_geometry = gltf_json(original)
    edited_doc, edited_geometry = gltf_json(edited)
    moved = next(n for n in edited_doc["nodes"] if n["name"] == name)
    offset = moved.pop("translation")
    assert abs(offset[1] - 0.012) < 1e-7 and abs(offset[0]) + abs(offset[2]) < 1e-7
    assert original_doc == edited_doc and original_geometry == edited_geometry
    assert digest(source) == original_source_hash
    return {
        **findings,
        "blender_version": bpy.app.version_string,
        "source_sha256": original_source_hash,
        "fresh_glb_sha256": digest(generated),
        "saved_source_glb_sha256": digest(saved),
        "edited_copy_glb_sha256": digest(edited),
        "edit": {"node": name, "translation_gltf_m": [round(v, 6) for v in offset]},
        "unchanged_geometry_buffer_after_edit": True,
        "existing_source_overwrite_refused": True,
        "source_untouched": True,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    with TemporaryDirectory(dir=args.scratch) as working:
        report = json.dumps(run(Path(working)), indent=2) + "\n"
    if args.report:
        args.report.write_text(report)
    print(report)
