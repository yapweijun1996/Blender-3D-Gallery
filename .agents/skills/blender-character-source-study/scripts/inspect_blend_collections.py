"""Read a JSON request and print an inventory of selected collections in a .blend."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

MARKER = "BLEND_COLLECTION_INVENTORY="


def hash_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_scene(collections):
    import bpy
    from mathutils import Vector

    scene = bpy.context.scene
    groups = {c.name: c for c in (scene.collection, *scene.collection.children_recursive)}
    members = {}
    for name in collections:
        if name in groups:
            for obj in groups[name].all_objects:
                members.setdefault(obj.name, []).append(name)

    graph = bpy.context.evaluated_depsgraph_get()
    objects = []
    for name in sorted(members):
        obj = scene.objects[name]
        row = {"name": name, "type": obj.type, "collections": sorted(members[name])}
        if obj.type == "MESH":
            row["source_vertices"] = len(obj.data.vertices)
            evaluated = obj.evaluated_get(graph)
            corners = [evaluated.matrix_world @ Vector(v) for v in evaluated.bound_box]
            row["evaluated_world_aabb_size"] = [
                round(max(v[i] for v in corners) - min(v[i] for v in corners), 6)
                for i in range(3)
            ]
        objects.append(row)
    return {
        "blender_version": bpy.app.version_string, "file_version": list(bpy.data.version),
        "scene": scene.name, "objects": objects,
        "missing_collections": sorted(set(collections) - groups.keys()),
    }


def names(value, field):
    if not isinstance(value, list) or not all(isinstance(s, str) and s for s in value):
        raise ValueError(field + " must be an array of nonempty object or collection names")
    return sorted(set(value))


def inspect(request):
    path = Path(request["source_file"]).expanduser().resolve(strict=True)
    if path.suffix.lower() != ".blend" or not path.is_file():
        raise ValueError("source_file must name an existing .blend file")
    collections = names(request["collections"], "collections")
    if not collections:
        raise ValueError("supply at least one collection in the current scene")
    expected = names(request.get("expected_objects", []), "expected_objects")
    blender = shutil.which("blender")
    mac_binary = Path("/Applications/Blender.app/Contents/MacOS/Blender")
    if not blender and mac_binary.is_file():
        blender = str(mac_binary)
    if not blender:
        raise RuntimeError("Blender CLI must be installed on the host")

    before = hash_file(path)
    cmd = [blender, "--background", "--factory-startup", "--disable-autoexec",
           str(path), "--python-exit-code", "1", "--python", str(Path(__file__).resolve()),
           "--", json.dumps(collections, ensure_ascii=True)]
    result = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, timeout=120)
    if hash_file(path) != before:
        raise RuntimeError("source changed during inspection; discard this observation")
    rows = [line[len(MARKER):] for line in result.stdout.splitlines() if line.startswith(MARKER)]
    if result.returncode or len(rows) != 1:
        raise RuntimeError("Blender did not return a single inventory (exit %s)" % result.returncode)
    report = json.loads(rows[0])
    observed = {row["name"] for row in report["objects"]}
    report["missing_expected_objects"] = sorted(set(expected) - observed)
    report["matches_expectations"] = not (report["missing_collections"] or report["missing_expected_objects"])
    report["source_sha256"] = before
    return report


if __name__ == "__main__":
    if "--" in sys.argv and "bpy" in sys.modules:
        args = sys.argv[sys.argv.index("--") + 1:]
        print(MARKER + json.dumps(read_scene(names(json.loads(args[0]), "collections"))))
    else:
        try:
            payload = os.environ.get("KB_TOOL_INPUT_JSON")
            request = json.loads(payload) if payload is not None else json.load(sys.stdin)
            print(json.dumps(inspect(request), ensure_ascii=False))
        except (OSError, ValueError, TypeError, KeyError, RuntimeError, subprocess.TimeoutExpired) as error:
            sys.exit(str(error))
