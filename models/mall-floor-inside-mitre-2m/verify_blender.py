"""Verify the editable mitre, three clean imports and an isolated saved-source edit."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

import bmesh
import bpy
from mathutils import Vector

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("inside_mitre_generator", BASE / "generate.py")
asset = importlib.util.module_from_spec(spec)
spec.loader.exec_module(asset)
EPS = 1e-7


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_source(path):
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False)
    bpy.context.view_layer.update()


def import_glb(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path), merge_vertices=True)
    bpy.context.view_layer.update()
    return list(bpy.context.scene.objects)


def components(mesh):
    unused = set(mesh.verts)
    count = 0
    while unused:
        todo = [unused.pop()]
        while todo:
            vertex = todo.pop()
            for edge in vertex.link_edges:
                other = edge.other_vert(vertex)
                if other in unused:
                    unused.remove(other)
                    todo.append(other)
        count += 1
    return count


def audit(objects, level, imported=False):
    shells = 0
    volume = 0
    seam_edges = 0
    bounds = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.transform(obj.matrix_world)
        if imported:
            # glTF uses separate indices for flat normals and material boundaries.
            bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=EPS)
        bm.normal_update()
        assert all(edge.is_manifold and edge.is_contiguous for edge in bm.edges), obj.name
        assert all(vertex.link_faces for vertex in bm.verts), obj.name
        assert all(face.calc_area() > 1e-12 for face in bm.faces), obj.name
        assert bm.calc_volume(signed=True) > 0, obj.name
        count = components(bm)
        shells += count
        volume += bm.calc_volume(signed=True)
        bounds.extend(vertex.co.copy() for vertex in bm.verts)
        if obj.name.startswith("Welded inside mitre"):
            assert count == 1

            def on_diagonal(vertex):
                return abs(vertex.co.x + vertex.co.y) < EPS

            diagonal = [vertex for vertex in bm.verts if on_diagonal(vertex)]
            assert len(diagonal) == 17
            seam_edges = sum(all(on_diagonal(vertex) for vertex in edge.verts) for edge in bm.edges)
            assert seam_edges == 17
            assert not any(all(on_diagonal(vertex) for vertex in face.verts) for face in bm.faces)
            if not imported:
                assert len(bm.verts) == 51 and len(bm.faces) == 36
                assert list(obj.vertex_groups.keys()) == ["East arm", "Diagonal seam", "Positive Z arm"]
        else:
            assert "fascia buttons" in obj.name and count == 2, obj.name
        bm.free()
    assert shells == (1 if level == "LOD2" else 5) and seam_edges == 17
    gltf_points = [(v.x, v.z, -v.y) for v in bounds]
    lo = [min(v[i] for v in gltf_points) for i in range(3)]
    hi = [max(v[i] for v in gltf_points) for i in range(3)]
    assert (Vector(lo) - Vector((0, -0.1, 0))).length < EPS
    assert (Vector(hi) - Vector((2, 0, 2))).length < EPS
    return {"closedComponents": shells, "weldedSectionEdges": seam_edges, "signedVolumeM3": volume}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    original = sha(asset.SOURCE)
    load_source(asset.SOURCE)
    assert not bpy.data.libraries
    report = {"blenderVersion": bpy.app.version_string, "sourceSha256": original, "levels": {}}
    for level in asset.LEVELS:
        collection = bpy.data.collections[level]
        report["levels"][level] = {"source": audit(collection.objects, level)}
        for arm, position in [("East", (2, -0.03, 0)), ("PositiveZ", (0.03, -2, 0))]:
            obj = collection.objects["CONNECTOR_InsideMitre_" + arm + "_" + level]
            assert (obj.matrix_world.translation - Vector(position)).length < EPS
    for level in asset.LEVELS:
        path = BASE / "exports" / asset.export_name(level)
        row = report["levels"][level]
        row["reimport"] = audit(import_glb(path), level, imported=True)
        assert abs(row["source"]["signedVolumeM3"] - row["reimport"]["signedVolumeM3"]) < EPS
        row["glbSha256"] = sha(path)
    with tempfile.TemporaryDirectory(dir=args.scratch) as tmp:
        location = Path(tmp)
        load_source(asset.SOURCE)
        obj = bpy.data.objects["Welded inside mitre LOD0"]
        moved = [v for v in obj.data.vertices if abs(v.co.x - 2) < EPS]
        assert len(moved) == 17
        for vertex in moved:
            vertex.co.x += 0.025
        bpy.data.objects["CONNECTOR_InsideMitre_East_LOD0"].location.x += 0.025
        edited = location / "edited.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(edited), compress=True)
        load_source(edited)
        asset.export_all(location)
        for level in asset.LEVELS:
            path = location / asset.export_name(level)
            assert (sha(path) != report["levels"][level]["glbSha256"]) == (level == "LOD0")
        objects = import_glb(location / asset.export_name("LOD0"))
        section = next(o for o in objects if o.name.startswith("Welded inside mitre"))
        maximum = max((section.matrix_world @ v.co).x for v in section.data.vertices)
        assert abs(maximum - 2.025) < EPS
        socket = next(o for o in objects if o.name == "CONNECTOR_InsideMitre_East_LOD0")
        assert abs(socket.matrix_world.translation.x - maximum) < EPS
        report["editableEastEnd"] = {
            "verticesEdited": len(moved),
            "originalX": 2,
            "reimportedX": maximum,
            "reimportedConnectorX": socket.matrix_world.translation.x,
            "unchangedExports": ["LOD1", "LOD2"],
        }
    assert sha(asset.SOURCE) == original
    report["result"] = "pass"
    print(json.dumps(report, indent=2))
    (BASE / "reports" / "source-reimport.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
